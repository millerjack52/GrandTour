#include "Vehicle/GTGroundAudioSynth.h"
#include "Vehicle/GTTractionComponent.h"
#include "Core/GTGameplayTags.h"
#include <cmath>
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/MemoryReader.h"

namespace
{
    float Bounded(float Value,float Max=1.f) { return FMath::IsFinite(Value)?FMath::Clamp(Value,0.f,Max):0.f; }

}

const TCHAR* FGTGroundAudioMix::Name(EGTGroundSound Kind)
{
    static const TCHAR* Names[]={TEXT("Tarmac"),TEXT("Gravel"),TEXT("Dirt"),TEXT("Grass"),TEXT("Mud"),TEXT("Sand"),TEXT("Snow"),TEXT("Water")};
    return Names[FMath::Clamp(int32(Kind),0,GTGroundSoundCount-1)];
}
EGTGroundSound FGTGroundAudioMix::Classify(const FGTWheelTraction& W,bool bPhysicalGravel)
{
    // Active deformable patches override the ground underneath them; authored grass/gravel
    // then override broad legacy physics tags (which cannot distinguish those two).
    if (W.bInSnowPatch) return EGTGroundSound::Snow;
    if (W.bInMudPatch) return EGTGroundSound::Mud;
    const FName S=W.AuthoredSurface;
    if (S==TEXT("Gravel")) return EGTGroundSound::Gravel;
    if (S==TEXT("Grass")) return EGTGroundSound::Grass;
    if (S==TEXT("Mud") || S==TEXT("Bog")) return EGTGroundSound::Mud;
    if (S==TEXT("Sand")) return EGTGroundSound::Sand;
    if (S==TEXT("Snow")) return EGTGroundSound::Snow;
    if (S==TEXT("Dirt")) return EGTGroundSound::Dirt;
    if (S==TEXT("Tarmac") || S==TEXT("Rock")) return EGTGroundSound::Tarmac;
    if (S==TEXT("Water")) return EGTGroundSound::Water;
    if (W.bInGravelPatch || bPhysicalGravel) return EGTGroundSound::Gravel;
    if (W.SurfaceTag==GTTags::Surface_Mud.GetTag() || W.SurfaceTag==GTTags::Surface_Bog.GetTag()) return EGTGroundSound::Mud;
    if (W.SurfaceTag==GTTags::Surface_Dirt.GetTag()) return EGTGroundSound::Dirt;
    if (W.SurfaceTag==GTTags::Surface_Snow.GetTag()) return EGTGroundSound::Snow;
    if (W.SurfaceTag==GTTags::Surface_Sand.GetTag()) return EGTGroundSound::Sand;
    return EGTGroundSound::Tarmac;
}
void FGTGroundAudioMix::AddWheel(const FGTWheelTraction& W,bool bPhysicalGravel,float Side,float GroundSpeedCmS,float LateralSlipCmS,int32 WheelCount)
{
    if (!W.bInContact || WheelCount<=0) return;
    ++Contacts;
    const float Travel=Bounded(FMath::Abs(GroundSpeedCmS),6000);
    const float Tread=Bounded(FMath::Abs(W.TreadCmPerS),6000);
    const float Motion=FMath::Max(Travel,Tread*.65f);
    // Standstill suspension jitter must not sound like rolling. Wheelspin still disturbs the ground.
    const float Moving=FMath::Clamp((Motion-8.f)/70.f,0.f,1.f);
    // S4: retain contrast throughout the driving range, rather than saturating at 60 km/h.
    const float RollLevel=(.06f+1.22f*FMath::Pow(FMath::Clamp(Motion/4444.44f,0.f,1.f),.8f))*Moving;
    const float Slip=FMath::Max(W.bSlipping?Bounded(FMath::Abs(W.SlipMagnitude),6000):0.f,Bounded(FMath::Abs(LateralSlipCmS),6000));
    const float Ratio=Slip/FMath::Max(Travel,300.f);
    const float ScrubLevel=FMath::Clamp((Ratio-.12f)/.48f,0.f,1.f)*FMath::Clamp((Slip-60.f)/250.f,0.f,1.f)*Moving;
    Speed=FMath::Max(Speed,FMath::Clamp(Motion/4444.44f,0.f,1.f));
    BodySpeed=FMath::Max(BodySpeed,FMath::Clamp(Travel/4444.44f,0.f,1.f));
    const float Water=FMath::Max(Bounded(W.WaterDepthM*100.f,100),Bounded(W.GroundWaterDepthCm,100));
    const float Wetness=Bounded(W.GroundWetness);
    const float Wet=FMath::Clamp(Water/10.f,0.f,1.f);
    const EGTGroundSound Kind=Classify(W,bPhysicalGravel); const int32 K=int32(Kind);
    const float Damp=Kind==EGTGroundSound::Water?1.f:(1.f-.55f*Wet-.15f*Wetness);
    Side=FMath::IsFinite(Side)?FMath::Clamp(Side,-1.f,1.f):0.f;
    for (int32 C=0;C<2;++C)
    {
        const float Weight=(1.f+(C==0?-Side:Side)*.22f)/WheelCount;
        Roll[K][C]+=RollLevel*Weight*Damp;
        Scrub[K][C]+=ScrubLevel*Weight*Damp;
        if (Kind!=EGTGroundSound::Water)
        {
            const float Spray=FMath::Max(Wet,Wetness*(Kind==EGTGroundSound::Tarmac?.32f:.08f));
            Roll[int32(EGTGroundSound::Water)][C]+=RollLevel*Weight*Spray;
            Scrub[int32(EGTGroundSound::Water)][C]+=ScrubLevel*Weight*Wet;
        }
    }
}
float FGTGroundAudioMix::Activity() const
{
    float Result=0; for (int32 K=0;K<GTGroundSoundCount;++K) for(int32 C=0;C<2;++C) Result+=Roll[K][C]+Scrub[K][C];
    return Result*.5f;
}
EGTGroundSound FGTGroundAudioMix::Dominant() const
{
    int32 Best=0;float Level=-1;
    for (int32 K=0;K<GTGroundSoundCount;++K) { const float V=Roll[K][0]+Roll[K][1]+Scrub[K][0]+Scrub[K][1];if(V>Level){Level=V;Best=K;} }
    return EGTGroundSound(Best);
}

TSharedPtr<const FGTGroundRecordingBank,ESPMode::ThreadSafe> FGTGroundRecordingBank::Load()
{
    TArray<uint8> Bytes;
    if(!FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("Audio/RangeRoverGroundS3/recordings.gts3"))) || Bytes.Num()<16) return nullptr;
    FMemoryReader Reader(Bytes);uint32 Magic,Version,Rate,Count;
    Reader<<Magic<<Version<<Rate<<Count;
    if(Magic!=0x33535447 || Version!=1 || Rate!=48000 || Count!=13) return nullptr;
    auto Result=MakeShared<FGTGroundRecordingBank,ESPMode::ThreadSafe>();
    for(auto& Clip:Result->Clips)
    {
        if(Reader.TotalSize()-Reader.Tell()<4) return nullptr;
        uint32 Frames;Reader<<Frames;
        if(Frames<2 || Frames>48000*30 || Reader.TotalSize()-Reader.Tell()<int64(Frames)*8) return nullptr;
        Clip.SetNumUninitialized(Frames*2);Reader.Serialize(Clip.GetData(),Frames*8);
        for(float X:Clip) if(!FMath::IsFinite(X) || FMath::Abs(X)>.85f) return nullptr;
    }
    if(Reader.IsError() || Reader.Tell()!=Reader.TotalSize())return nullptr;
    return Result;
}

FGTGroundAudioSynth::FGTGroundAudioSynth()
{
    // Construction occurs on the game thread before audio starts. Callbacks never load files.
    static TWeakPtr<const FGTGroundRecordingBank,ESPMode::ThreadSafe> Cached;
    Bank=Cached.Pin();if(!Bank){Bank=FGTGroundRecordingBank::Load();Cached=Bank;}
    for(int32 K=0;K<GTGroundSoundCount;++K) for(int32 C=0;C<2;++C)
    {TargetRoll[K][C]=0;TargetScrub[K][C]=0;}
}
void FGTGroundAudioSynth::SetTargets(const FGTGroundAudioMix& Mix,float InVolume)
{
    for(int32 K=0;K<GTGroundSoundCount;++K) for(int32 C=0;C<2;++C)
    {TargetRoll[K][C].store(Bounded(Mix.Roll[K][C],1.3f));TargetScrub[K][C].store(Bounded(Mix.Scrub[K][C]));}
    TargetSpeed.store(Bounded(Mix.Speed));TargetBodySpeed.store(Bounded(Mix.BodySpeed));TargetVolume.store(Bounded(InVolume));
    // Retain brief physics impulses until the audio callback consumes them.
    float Previous=PendingBump.load();const float B=Bounded(Mix.Bump);
    while(B>Previous && !PendingBump.compare_exchange_weak(Previous,B)) {}
}
void FGTGroundAudioSynth::MixInto(int16* Out,int32 Frames)
{
    if(!Bank || Frames<=0) return;
    float Rolls[GTGroundSoundCount][2],Scrubs[GTGroundSoundCount][2];
    for(int32 K=0;K<GTGroundSoundCount;++K) for(int32 C=0;C<2;++C)
    {Rolls[K][C]=TargetRoll[K][C].load();Scrubs[K][C]=TargetScrub[K][C].load();}
    const float V=TargetVolume.load(),S=TargetSpeed.load(),BS=TargetBodySpeed.load();
    const float A=1-std::exp(-1.f/(.045f*48000)),Fade=1-std::exp(-1.f/(.025f*48000));
    const float Bump=PendingBump.exchange(0);
    if(Bump>.05f && BumpCooldown==0 && V>0 && BS>.002f)
    {BumpClip=5+(BumpClip-4)%8;BumpFrame=0;BumpGain=Bump;BumpCooldown=12000;BumpEvents.fetch_add(1);}
    // Other surfaces get subdued body motion only until suitable recordings are approved.
    constexpr float BodyWeight[GTGroundSoundCount]={.14f,1.f,.65f,.52f,.32f,.38f,.38f,.12f};
    for(int32 I=0;I<Frames;++I)
    {
        Volume+=Fade*(V-Volume);Speed+=A*(S-Speed);BodySpeed+=A*(BS-BodySpeed);
        if(BumpCooldown>0)--BumpCooldown;
        for(int32 K=0;K<GTGroundSoundCount;++K) for(int32 C=0;C<2;++C)
        {RollState[K][C]+=A*(Rolls[K][C]-RollState[K][C]);ScrubState[K][C]+=A*(Scrubs[K][C]-ScrubState[K][C]);}
        const float Slip=.5f*(ScrubState[1][0]+ScrubState[1][1]);
        if(Slip<.10f)bSkidArmed=true;
        if(Slip>.32f && bSkidArmed && SkidFrame<0 && Volume>.01f)
        {SkidFrame=0;SkidGain=FMath::Min(1.f,Slip*1.6f);bSkidArmed=false;SkidEvents.fetch_add(1);}
        const float Fast=FMath::Clamp((Speed*160-18)/65,0.f,1.f);
        const float W0=std::cos(Fast*PI*.5f),W1=std::sin(Fast*PI*.5f);
        const float RollingRate=.45f+1.35f*std::pow(Speed,.7f);
        const float BodyRate=.60f+.85f*std::sqrt(BodySpeed);
        const float ToneAlpha=1-std::exp(-2*PI*(1600+7000*std::pow(Speed,.75f))/48000);
        float Sample[4][2];
        for(int32 K=0;K<4;++K)
        {
            const auto& Clip=Bank->Clips[K];const int32 Length=Clip.Num()/2;
            const int32 Index=int32(Positions[K]),Next=(Index+1)%Length;
            const float Frac=float(Positions[K]-Index);
            for(int32 C=0;C<2;++C)Sample[K][C]=FMath::Lerp(Clip[Index*2+C],Clip[Next*2+C],Frac);
            Positions[K]+=K==3?BodyRate:RollingRate;
            while(Positions[K]>=Length)Positions[K]-=Length;
        }
        for(int32 C=0;C<2;++C)
        {
            float BodyGain=0;for(int32 K=0;K<GTGroundSoundCount;++K)BodyGain+=RollState[K][C]*BodyWeight[K];
            // Stationary wheelspin disturbs stones, but cannot create travelling body rumble.
            const float BodyGate=FMath::Clamp(BodySpeed/.01875f,0.f,1.f);
            const float Rolling=(Sample[0][C]*W0+Sample[1][C]*W1)*RollState[1][C]+Sample[2][C]*RollState[3][C];
            RollingTone[C]+=ToneAlpha*(Rolling-RollingTone[C]);
            // S5: bring the recorded low body vibration forward by 6 dB; retain
            // the S4 speed curve and leave gravel detail, impacts and engine alone.
            float X=RollingTone[C]+2.f*Sample[3][C]*BodyGain*BodyGate*(.45f+.9f*std::sqrt(BodySpeed));
            // Sustained slide adds recorded crunch; the recorded stop is onset-only.
            X+=Sample[1][C]*ScrubState[1][C]*.45f;
            if(SkidFrame>=0)X+=Bank->Clips[4][SkidFrame*2+C]*SkidGain*FMath::Min(1.f,Slip*5.f);
            if(BumpFrame>=0)X+=Bank->Clips[BumpClip][BumpFrame*2+C]*BumpGain*FMath::Min(1.f,BodyGain*3.f)*BodyGate;
            // Transparent at approved audition levels; only extreme sums use soft headroom.
            const float Abs=FMath::Abs(X);
            if(Abs>.32f)X=FMath::Sign(X)*(.32f+.06f*std::tanh((Abs-.32f)/.06f));
            const int32 Added=int32(X*Volume*32767);
            Out[I*2+C]=int16(FMath::Clamp(int32(Out[I*2+C])+Added,-32767,32767));
        }
        if(SkidFrame>=0 && ++SkidFrame>=Bank->Clips[4].Num()/2)SkidFrame=-1;
        if(BumpFrame>=0 && ++BumpFrame>=Bank->Clips[BumpClip].Num()/2)BumpFrame=-1;
    }
    RenderedFrames.fetch_add(Frames,std::memory_order_relaxed);
}
