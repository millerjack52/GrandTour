#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTVehicleAudioComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "Terrain/GTLandscapeSurface.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
    TAutoConsoleVariable<float> GroundAudioVolume(TEXT("gt.Audio.GroundVolume"),1.f,
        TEXT("Range Rover ground audio level, 0..1. Zero auditions the approved engine alone."),ECVF_Default);
}

UGTRangeRoverSoundWave::UGTRangeRoverSoundWave(const FObjectInitializer& Initializer) : Super(Initializer)
{
    SetSampleRate(48000); NumChannels=2; Duration=INDEFINITELY_LOOPING_DURATION;
    bLooping=false; NumSamplesToGeneratePerCallback=2048;
}
int32 UGTRangeRoverSoundWave::OnGeneratePCMAudio(TArray<uint8>& OutAudio, int32 NumSamples)
{
    // UE 5.8 expects interleaved sample count here, and byte count from GeneratePCMData.
    OutAudio.SetNumZeroed(NumSamples*sizeof(int16));
    if (Synth) Synth->Render(reinterpret_cast<int16*>(OutAudio.GetData()),NumSamples/2);
    if (Ground) Ground->MixInto(reinterpret_cast<int16*>(OutAudio.GetData()),NumSamples/2);
    return NumSamples;
}
UGTRangeRoverAudioComponent::UGTRangeRoverAudioComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
}
bool UGTRangeRoverAudioComponent::IsRangeRoverMeshPath(const FString& Path)
{
    return Path==TEXT("/Game/GrandTour/Vehicles/Bodies/RangeRover/SK_RangeRover.SK_RangeRover");
}
bool UGTRangeRoverAudioComponent::IsRangeRover(const AActor* Owner)
{
    const auto* Car=Cast<AGTCarPawn>(Owner);
    return Car && Car->GetMesh() && Car->GetMesh()->GetSkeletalMeshAsset() && IsRangeRoverMeshPath(Car->GetMesh()->GetSkeletalMeshAsset()->GetPathName());
}
bool UGTRangeRoverAudioComponent::ShouldBeAudible(bool bCorrectCar, bool bLocalDriver, float Rpm, bool bOutOfFuel, bool bFlooded)
{
    return bCorrectCar && bLocalDriver && FMath::IsFinite(Rpm) && Rpm>1 && !bOutOfFuel && !bFlooded;
}
void UGTRangeRoverAudioComponent::BeginPlay()
{
    Super::BeginPlay();
    if (!IsRangeRover(GetOwner())) { SetComponentTickEnabled(false); return; }
    AddTickPrerequisiteActor(GetOwner());
    for(TActorIterator<AGTLandscapeSurface> It(GetWorld());It;++It) GroundSurfaces.Add(*It);
    // Share immutable recording data among RR instances, with independent playback/filter state.
    static TWeakPtr<const FGTHybridBank, ESPMode::ThreadSafe> Cached;
    auto Bank=Cached.Pin(); if (!Bank) { Bank=FGTHybridBank::Load(); Cached=Bank; }
    if (!Bank) { UE_LOG(LogTemp,Error,TEXT("RangeRover H2: missing or invalid recording bank")); SetComponentTickEnabled(false); return; }
    Synth=MakeShared<FGTRangeRoverHybridSynth,ESPMode::ThreadSafe>(Bank);
    Ground=MakeShared<FGTGroundAudioSynth,ESPMode::ThreadSafe>();
    if(!Ground->IsReady()) { UE_LOG(LogTemp,Error,TEXT("RangeRover ground S3: recording bank missing or invalid; ground layer silent")); }
    else { UE_LOG(LogTemp,Display,TEXT("RangeRover ground S3: recorded gravel, grass Foley and body rumble ready")); }
    Wave=NewObject<UGTRangeRoverSoundWave>(this,TEXT("RangeRoverH2Wave")); Wave->Synth=Synth; Wave->Ground=Ground;
    if (GEngine && GEngine->UseSound())
    {
        Audio=NewObject<UAudioComponent>(GetOwner(),TEXT("RangeRoverH2Audio"));
        Audio->bAutoActivate=false; Audio->bAllowSpatialization=false;
        Audio->SetupAttachment(GetOwner()->GetRootComponent()); Audio->RegisterComponent(); Audio->SetSound(Wave);
    }
    UE_LOG(LogTemp,Display,TEXT("RangeRover H2: ready, four recorded banks, 48000 Hz stereo; device=%d"), Audio!=nullptr);
}
void UGTRangeRoverAudioComponent::TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(Dt,TickType,TickFunction);
    auto* Car=Cast<AGTCarPawn>(GetOwner()); if (!Car || !Synth) return;
    const auto* Driver=Cast<APlayerController>(Car->GetController());
    const auto* Drive=Car->GetDrivetrain(); const auto* Condition=Car->GetCondition();
    const float Rpm=Drive->GetEngineRpm(), Throttle=Drive->GetDriveInput();
    const bool DriverEnabled=!Car->GetAudio()->bMuted && IsRangeRover(Car) && Driver && Driver->IsLocalController();
    const bool EngineAudible=ShouldBeAudible(DriverEnabled,true,Rpm,Condition->bOutOfFuel,Condition->bFlooded);
    LastGroundMix=FGTGroundAudioMix();
    auto* Move=Car->GetChaosMovement();const auto& Wheels=Car->GetTraction()->Wheels;
    if(PreviousSuspension.Num()!=Wheels.Num())PreviousSuspension.Init(-1.f,Wheels.Num());
    GrassQueryTime+=Dt;
    const bool RefreshGrass=GrassQueryTime>=.08f || FirmGrass.Num()!=Wheels.Num();
    if(RefreshGrass){GrassQueryTime=0;FirmGrass.SetNumZeroed(Wheels.Num());}
    for(int32 I=0;I<Wheels.Num();++I)
    {
        const auto& W=Wheels[I];if(!W.bInContact){PreviousSuspension[I]=-1.f;continue;}
        FGTWheelTraction AudioWheel=W;
        // Firm painted grass is visual cover, so the physics query correctly has no authored
        // soil tag there. Read its mask at 12.5 Hz, validating the actual contact actor so a
        // bridge/rock above a grassy landscape cannot inherit grass audio from underneath.
        if(RefreshGrass)
        {
            FirmGrass[I]=0;
            if(W.AuthoredSurface.IsNone() && !W.bInMudPatch && !W.bInSnowPatch && !W.bInGravelPatch)
            {
                for(const auto& Weak : GroundSurfaces) if(const auto* Surface=Weak.Get())
                {
                    const float Cover=Surface->GrassAt(FVector2D(W.ContactPoint));
                    if(Cover<=.1f) continue;
                    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(GTGroundAudioGrass),false,Car);
                    if(GetWorld()->LineTraceSingleByChannel(Hit,W.ContactPoint+FVector(0,0,12),W.ContactPoint-FVector(0,0,12),ECC_Visibility,Query)
                        && Surface->OwnsGroundActor(Hit.GetActor())){FirmGrass[I]=Cover;break;}
                }
            }
        }
        if(W.AuthoredSurface.IsNone() && FirmGrass[I]>.1f) AudioWheel.AuthoredSurface=TEXT("Grass");
        bool Gravel=false;float Skid=0;
        if(Move->PhysicsVehicleOutput().IsValid() && I<Move->GetNumWheels())
        {
            const auto& Contact=Move->GetWheelState(I);
            const float Length=Contact.NormalizedSuspensionLength;
            if(FMath::IsFinite(Length) && Dt>.0001f && Dt<.15f)
            {
                if(PreviousSuspension[I]>=0 && Car->GetVelocity().Size2D()>10.f)
                {
                    const float CompressionRate=(PreviousSuspension[I]-Length)/Dt;
                    LastGroundMix.Bump=FMath::Max(LastGroundMix.Bump,FMath::Clamp((CompressionRate-.9f)/8.f,0.f,.8f));
                }
                PreviousSuspension[I]=Length;
            }
            else PreviousSuspension[I]=-1.f;
            const auto* Material=Cast<UGTSurfacePhysMaterial>(Contact.PhysMaterial.Get());
            Gravel=Material && Material->bGravelSpray;
            // Slip angle is radians. Convert lateral slip to cm/s, rather than guessing SkidMagnitude units.
            Skid=Contact.bIsSkidding?FMath::Abs(FMath::Sin(Contact.SlipAngle))*Car->GetVelocity().Size2D():0.f;
        }
        const float Side=FMath::Sign(Car->GetActorTransform().InverseTransformPosition(W.ContactPoint).Y);
        LastGroundMix.AddWheel(AudioWheel,Gravel,Side,Car->GetVelocity().Size2D(),Skid,Wheels.Num());
    }
    const float SurfaceGain=DriverEnabled?FMath::Clamp(GroundVolume*GroundAudioVolume.GetValueOnGameThread(),0.f,1.f):0.f;
    Ground->SetTargets(LastGroundMix,SurfaceGain);
    // A stopped/flooded engine must not silence tyres that are still coasting over the ground.
    const bool Audible=EngineAudible || (DriverEnabled && SurfaceGain>0 && LastGroundMix.Activity()>.0001f);
    Synth->TargetRpm.store(Rpm); Synth->TargetThrottle.store(Throttle);
    Synth->TargetGain.store(EngineAudible?FMath::Clamp(Volume,0.f,1.f)*(Condition->bMisfiring?.3f:1.f):0.f);
    SilentTime=Audible?0.f:SilentTime+Dt;
    if (Audio)
    {
        if (Audible && !Audio->IsPlaying()) Audio->Play();
        // Let the renderer's 25 ms gate finish before releasing the source.
        if (SilentTime>.35f && Audio->IsPlaying()) Audio->Stop();
    }
    DiagnosticTime+=Dt;
    if (DiagnosticTime>=2 && FParse::Param(FCommandLine::Get(),TEXT("GTRangeRoverAudioTest")))
    {
        DiagnosticTime=0;
        UE_LOG(LogTemp,Display,TEXT("RangeRover H2: rpm=%.0f throttle=%.3f audible=%d playing=%d rendered_frames=%llu"),Rpm,Throttle,Audible,Audio && Audio->IsPlaying(),Synth->RenderedFrames.load());
        UE_LOG(LogTemp,Display,TEXT("RangeRover ground: %s"),*GroundAudioReport());
    }
}
void UGTRangeRoverAudioComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Synth) Synth->TargetGain.store(0);
    if (Ground) Ground->SetTargets(FGTGroundAudioMix(),0);
    if (Audio) Audio->Stop();
    // Keep Wave->Synth alive until the wave itself is collected; pending callbacks retain valid data.
    Super::EndPlay(Reason);
}

FString UGTRangeRoverAudioComponent::GroundAudioReport() const
{
    FString Layers;
    for(int32 K=0;K<GTGroundSoundCount;++K)
    {
        if(K) Layers+=TEXT(",");
        Layers+=FString::Printf(TEXT("\"%s\":%.5f"),FGTGroundAudioMix::Name(EGTGroundSound(K)),
            .5f*(LastGroundMix.Roll[K][0]+LastGroundMix.Roll[K][1]+LastGroundMix.Scrub[K][0]+LastGroundMix.Scrub[K][1]));
    }
    return FString::Printf(TEXT("{\"contacts\":%d,\"activity\":%.5f,\"surface\":\"%s\",\"layers\":{%s},\"recorded_ready\":%s,\"body_speed\":%.5f,\"bump_target\":%.5f,\"bump_events\":%llu,\"skid_events\":%llu,\"rendered_frames\":%llu}"),
        LastGroundMix.Contacts,LastGroundMix.Activity(),LastGroundMix.Activity()>.0001f?FGTGroundAudioMix::Name(LastGroundMix.Dominant()):TEXT("Silent"),*Layers,
        Ground && Ground->IsReady()?TEXT("true"):TEXT("false"),LastGroundMix.BodySpeed,LastGroundMix.Bump,
        Ground?Ground->BumpEvents.load():0,Ground?Ground->SkidEvents.load():0,Ground?Ground->RenderedFrames.load():0);
}
