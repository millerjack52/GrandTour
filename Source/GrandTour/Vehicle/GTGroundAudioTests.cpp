#include "Vehicle/GTGroundAudioSynth.h"
#include "Vehicle/GTRangeRoverHybridSynth.h"
#include "Vehicle/GTTractionComponent.h"
#include "Core/GTGameplayTags.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Audio.h"

namespace
{
    FGTGroundAudioMix SurfaceMix(EGTGroundSound Kind,float Speed=1600,float Slip=0)
    {
        FGTGroundAudioMix Mix;FGTWheelTraction W;W.bInContact=true;
        W.AuthoredSurface=FGTGroundAudioMix::Name(Kind);W.TreadCmPerS=Speed;
        W.bSlipping=Slip>0;W.SlipMagnitude=Slip;
        for(int32 I=0;I<4;++I) Mix.AddWheel(W,false,I%2?1.f:-1.f,Speed,0,4);
        return Mix;
    }
    double Energy(const TArray<int16>& Samples,int32 Start=0)
    {
        double Sum=0;for(int32 I=Start;I<Samples.Num();++I) Sum+=FMath::Square(double(Samples[I])/32767);
        return FMath::Sqrt(Sum/FMath::Max(1,Samples.Num()-Start));
    }
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTGroundAudioTest,"GrandTour.Vehicle.GroundAudio",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTGroundAudioTest::RunTest(const FString& Parameters)
{
    FGTWheelTraction W;W.bInContact=true;W.AuthoredSurface=TEXT("Grass");W.SurfaceTag=GTTags::Surface_Dirt.GetTag();
    TestEqual(TEXT("authored grass overrides broad dirt and physical gravel"),int32(FGTGroundAudioMix::Classify(W,true)),int32(EGTGroundSound::Grass));
    W.bInMudPatch=true;
    TestEqual(TEXT("live mud overrides grass"),int32(FGTGroundAudioMix::Classify(W,true)),int32(EGTGroundSound::Mud));
    W.bInMudPatch=false;W.bInSnowPatch=true;
    TestEqual(TEXT("snow patch overrides ground underneath"),int32(FGTGroundAudioMix::Classify(W,true)),int32(EGTGroundSound::Snow));
    W.bInSnowPatch=false;W.AuthoredSurface=NAME_None;
    TestEqual(TEXT("legacy gravel material"),int32(FGTGroundAudioMix::Classify(W,true)),int32(EGTGroundSound::Gravel));
    TestEqual(TEXT("legacy dirt tag"),int32(FGTGroundAudioMix::Classify(W,false)),int32(EGTGroundSound::Dirt));
    W.AuthoredSurface=TEXT("Gravel");W.TreadCmPerS=1500;
    FGTGroundAudioMix Split;Split.AddWheel(W,false,-1,1500,0,2);
    W.AuthoredSurface=TEXT("Grass");Split.AddWheel(W,false,1,1500,0,2);
    TestTrue(TEXT("mixed contacts retain both surfaces"),Split.Roll[1][0]>0 && Split.Roll[3][1]>0);
    TestTrue(TEXT("left and right retain subtle stereo placement"),Split.Roll[1][0]>Split.Roll[1][1] && Split.Roll[3][1]>Split.Roll[3][0]);
    W.bInContact=false;FGTGroundAudioMix Air;Air.AddWheel(W,true,0,3000,900,4);
    TestEqual(TEXT("airborne tyres silent even at high spin"),Air.Activity(),0.f);
    W.bInContact=true;W.TreadCmPerS=0;FGTGroundAudioMix Park;Park.AddWheel(W,false,0,3,0,4);
    TestEqual(TEXT("parked jitter silent"),Park.Activity(),0.f);
    W.TreadCmPerS=2000;W.bSlipping=true;W.SlipMagnitude=1800;FGTGroundAudioMix Spin;Spin.AddWheel(W,false,0,0,0,4);
    TestTrue(TEXT("stationary wheelspin audible"),Spin.Activity()>.1f);
    W.TreadCmPerS=0;W.bSlipping=false;FGTGroundAudioMix Lock;Lock.AddWheel(W,false,0,1500,700,4);
    TestTrue(TEXT("locked or lateral sliding wheel audible"),Lock.Scrub[3][0]>0 && Lock.Roll[3][0]>0);
    TestEqual(TEXT("forward/reverse rolling level"),SurfaceMix(EGTGroundSound::Gravel,-1500).Activity(),SurfaceMix(EGTGroundSound::Gravel,1500).Activity());
    W.AuthoredSurface=TEXT("Gravel");W.WaterDepthM=.1f;FGTGroundAudioMix Wet;Wet.AddWheel(W,false,0,1200,0,4);
    TestTrue(TEXT("water overlays and damps gravel"),Wet.Roll[7][0]>0 && Wet.Roll[1][0]>0 && Wet.Roll[1][0]<Wet.Roll[7][0]);

    FGTGroundAudioSynth Whole,Chunks;Whole.SetTargets(Split,1);Chunks.SetTargets(Split,1);
    if(!TestTrue(TEXT("S3 recording bank loads"),Whole.IsReady()))return false;
    TArray<int16> A,B;A.SetNumZeroed(24000);B.SetNumZeroed(24000);
    Whole.MixInto(A.GetData(),12000);Chunks.MixInto(B.GetData(),4567);Chunks.MixInto(B.GetData()+9134,7433);
    TestTrue(TEXT("recorded cursors and fades continuous across audio callbacks"),A==B);
    FGTGroundAudioSynth Silent;TArray<int16> Engine;Engine.Init(1234,4096);auto Original=Engine;Silent.MixInto(Engine.GetData(),2048);
    TestTrue(TEXT("inactive ground leaves engine PCM untouched"),Original==Engine);
    Whole.SetTargets(FGTGroundAudioMix(),0);A.Init(0,96000);Whole.MixInto(A.GetData(),48000);
    TestEqual(TEXT("contact loss/mute fade reaches silence"),Energy(A,48000),0.0);

    const auto Bank=FGTHybridBank::Load();if(!TestTrue(TEXT("approved engine bank available for mix headroom check"),Bank.IsValid())) return false;
    FGTRangeRoverHybridSynth V8(Bank);V8.TargetRpm=2400;V8.TargetThrottle=.4f;V8.TargetGain=1;
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("GroundAudioQA");IFileManager::Get().MakeDirectory(*Dir,true);
    TArray<int16> Pack,Mixed;FString Rows;double Started=FPlatformTime::Seconds();
    for(int32 K=0;K<GTGroundSoundCount;++K)
    {
        FGTGroundAudioSynth Ground;Ground.SetTargets(SurfaceMix(EGTGroundSound(K)),1);
        TArray<int16> Clip;Clip.SetNumZeroed(48000*3*2);Ground.MixInto(Clip.GetData(),48000*3);
        const double Rms=Energy(Clip,48000);TestTrue(TEXT("material rolling bed audible and balanced"),Rms>.0015 && Rms<.06);
        int32 Peak=0;for(int16 X:Clip) Peak=FMath::Max(Peak,FMath::Abs(int32(X)));
        TestTrue(TEXT("surface layer leaves engine headroom"),Peak<12500);
        if(K) Rows+=TEXT(",");Rows+=FString::Printf(TEXT("{\"material\":\"%s\",\"rms\":%.7f,\"peak\":%d}"),FGTGroundAudioMix::Name(EGTGroundSound(K)),Rms,Peak);
        Pack.Append(Clip);Pack.AddZeroed(24000*2);
        TArray<int16> Combined;Combined.SetNumZeroed(Clip.Num());V8.Render(Combined.GetData(),48000*3);
        for(int32 I=0;I<Clip.Num();++I)
        {
            const int32 Sum=int32(Combined[I])+Clip[I];
            if(FMath::Abs(Sum)>=32767){AddError(TEXT("Engine plus surface clips"));return false;}
            Combined[I]=int16(Sum);
        }
        Mixed.Append(Combined);Mixed.AddZeroed(24000*2);
    }
    FGTGroundAudioSynth Slow,Fast,Scrub;
    Slow.SetTargets(SurfaceMix(EGTGroundSound::Gravel,250),1);Fast.SetTargets(SurfaceMix(EGTGroundSound::Gravel,1800),1);
    Scrub.SetTargets(SurfaceMix(EGTGroundSound::Gravel,1800,900),1);
    A.Init(0,96000);B.Init(0,96000);TArray<int16> C;C.Init(0,96000);
    Slow.MixInto(A.GetData(),48000);Fast.MixInto(B.GetData(),48000);Scrub.MixInto(C.GetData(),48000);
    TestTrue(TEXT("speed increases ground energy"),Energy(B)>Energy(A)*1.3);
    TestTrue(TEXT("wheel slip increases recorded gravel disturbance"),Energy(C)>Energy(B)*1.05);
    TestEqual(TEXT("ordinary rolling does not trigger stop sample"),Fast.SkidEvents.load(),uint64(0));
    TestEqual(TEXT("large slip triggers one recorded stop onset"),Scrub.SkidEvents.load(),uint64(1));
    C.Init(0,96000);Scrub.MixInto(C.GetData(),48000);
    TestEqual(TEXT("held slip does not repeatedly replay a stop"),Scrub.SkidEvents.load(),uint64(1));
    auto Mild=SurfaceMix(EGTGroundSound::Gravel,1600,100);
    TestEqual(TEXT("small ordinary tyre slip stays below scrub threshold"),Mild.Scrub[1][0],0.f);
    auto Hit=SurfaceMix(EGTGroundSound::Gravel,1600);Hit.Bump=.7f;
    FGTGroundAudioSynth Bumpy;Bumpy.SetTargets(Hit,1);C.Init(0,96000);Bumpy.MixInto(C.GetData(),48000);
    TestEqual(TEXT("suspension impulse produces one body thump"),Bumpy.BumpEvents.load(),uint64(1));
    Bumpy.SetTargets(SurfaceMix(EGTGroundSound::Gravel,1600),1);Bumpy.MixInto(C.GetData(),48000);
    TestEqual(TEXT("constant motion cannot invent bump events"),Bumpy.BumpEvents.load(),uint64(1));
    FGTGroundAudioSynth ParkedBump;Hit=FGTGroundAudioMix();Hit.Bump=1;ParkedBump.SetTargets(Hit,1);
    C.Init(0,96000);ParkedBump.MixInto(C.GetData(),48000);
    TestEqual(TEXT("parked suspension jitter cannot trigger body thumps"),Energy(C),0.0);
    auto Save=[&](const TCHAR* File,const TArray<int16>& Data)
    {TArray<uint8> Wav;SerializeWaveFile(Wav,reinterpret_cast<const uint8*>(Data.GetData()),Data.Num()*2,2,48000);return FFileHelper::SaveArrayToFile(Wav,*(Dir/File));};
    // Explicit coverage above the old 60 km/h ceiling. Measure the actual rendered
    // signal, including tone/rate/body changes, rather than just checking target gains.
    constexpr float Speeds[]={5,20,40,60,80,100,120,160};
    double Levels[8]={},Texture[8]={};TArray<int16> SpeedPack,SpeedMixed;FString SpeedRows;
    for(int32 N=0;N<8;++N)
    {
        FGTGroundAudioSynth Ground;Ground.SetTargets(SurfaceMix(EGTGroundSound::Gravel,Speeds[N]/.036f),1);
        TArray<int16> Clip;Clip.SetNumZeroed(48000*4*2);Ground.MixInto(Clip.GetData(),48000*4);
        Levels[N]=Energy(Clip,48000*2);
        double Delta=0,Power=0;int32 Peak=0;
        for(int32 I=48000*2+2;I<Clip.Num();++I)
        {Delta+=FMath::Square(double(Clip[I])-Clip[I-2]);Power+=FMath::Square(double(Clip[I]));Peak=FMath::Max(Peak,FMath::Abs(int32(Clip[I])));}
        Texture[N]=FMath::Sqrt(Delta/FMath::Max(1.0,Power));
        SpeedPack.Append(Clip);SpeedPack.AddZeroed(24000*2);
        FGTRangeRoverHybridSynth EngineAtLoad(Bank);EngineAtLoad.TargetRpm=4200;EngineAtLoad.TargetThrottle=.85f;EngineAtLoad.TargetGain=1;
        TArray<int16> Combined;Combined.SetNumZeroed(Clip.Num());EngineAtLoad.Render(Combined.GetData(),48000*4);
        for(int32 I=0;I<Clip.Num();++I)
        {const int32 Sum=int32(Combined[I])+Clip[I];if(FMath::Abs(Sum)>=32767){AddError(TEXT("High-speed ground plus loaded V8 clips"));return false;}Combined[I]=int16(Sum);}
        SpeedMixed.Append(Combined);SpeedMixed.AddZeroed(24000*2);
        if(N)SpeedRows+=TEXT(",");SpeedRows+=FString::Printf(TEXT("{\"kmh\":%.0f,\"rms\":%.7f,\"peak\":%d,\"normalized_sample_difference\":%.7f}"),Speeds[N],Levels[N],Peak,Texture[N]);
    }
    TestTrue(TEXT("20 km/h clearly stronger than crawling"),Levels[1]>Levels[0]*1.7);
    TestTrue(TEXT("100 km/h keeps rising beyond old 60 km/h cap"),Levels[5]>Levels[3]*1.25);
    TestTrue(TEXT("160 km/h keeps rising beyond 100 km/h"),Levels[7]>Levels[5]*1.2);
    TestTrue(TEXT("high-speed texture changes beyond just amplitude"),Texture[5]>Texture[1]*1.25);
    TestTrue(TEXT("speed ground comparison exported"),Save(TEXT("s4_speed_ground.wav"),SpeedPack));
    TestTrue(TEXT("speed engine comparison exported"),Save(TEXT("s4_speed_with_v8.wav"),SpeedMixed));
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"seconds_per_speed\":4,\"gap_seconds\":0.5,\"speeds\":[%s]}"),*SpeedRows),*(Dir/TEXT("s4_speed_response.json")));
    TestTrue(TEXT("ground audition exported"),Save(TEXT("01_ground_materials.wav"),Pack));
    TestTrue(TEXT("engine and ground audition exported"),Save(TEXT("02_engine_and_ground.wav"),Mixed));
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"seconds_per_material\":3,\"gap_seconds\":0.5,\"materials\":[%s]}"),*Rows),*(Dir/TEXT("materials.json")));
    AddInfo(FString::Printf(TEXT("Ground audio mapping, callbacks, motion and headroom verified; render/export tests %.3f seconds"),FPlatformTime::Seconds()-Started));
    return true;
}
#endif
