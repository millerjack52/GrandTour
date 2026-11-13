#include "Vehicle/GTDustLab.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTSprayComponent.h"
#include "Core/GTGameplayTags.h"
#include "Weather/GTWeatherSubsystem.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Terrain/GTSurfacePhysMaterial.h"

static TAutoConsoleVariable<int32> CVarDustLab(TEXT("gt.DustLab"), 1,
    TEXT("Opt-in GTDustLab actors only: 0 stops new dust, existing trails fade naturally."), ECVF_Default);

AGTDustLab::AGTDustLab()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostPhysics;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
}

void AGTDustLab::BeginPlay()
{
    Super::BeginPlay();
    if (TargetCar) AddTickPrerequisiteActor(TargetCar);
}

float AGTDustLab::EmissionStrength(bool bContact, bool bDusty, float SpeedCmS, float SlipCmS, float Wetness)
{
    if (!bContact || !bDusty) return 0.f;
    const float Dry = FMath::Clamp(1.f - Wetness / 0.6f, 0.f, 1.f);
    const float Roll = FMath::Clamp((FMath::Abs(SpeedCmS) - 35.f) / 1600.f, 0.f, 1.f);
    const float Scrub = FMath::Clamp((FMath::Abs(SlipCmS) - 20.f) / 900.f, 0.f, 1.f);
    return Dry * Dry * FMath::Clamp(Roll + 0.65f * Scrub, 0.f, 1.5f);
}

void AGTDustLab::ZeroRates()
{
    TotalRate = 0.f;
    EmittingWheels = 0;
    for (UNiagaraComponent* Nc : Wheels)
        if (Nc) for (const TCHAR* Name : {TEXT("User.ContactRate"), TEXT("User.WakeRate"), TEXT("User.TrailRate")})
            Nc->SetVariableFloat(FName(Name), 0.f);
}

void AGTDustLab::ResetDust()
{
    for (UNiagaraComponent* Nc : Wheels) if (Nc) Nc->DestroyComponent();
    Wheels.Reset();
    PreviousContacts.Reset();
    TotalRate = 0.f;
    EmittingWheels = 0;
}

int32 AGTDustLab::GetLiveParticles() const
{
    int32 Count = 0;
    for (UNiagaraComponent* Nc : Wheels) if (Nc)
        for (int32 E = 0; E < 3; ++E) Count += UGTSprayComponent::GetNiagaraLiveCount(Nc, E);
    return Count;
}

void AGTDustLab::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!IsValid(TargetCar))
    {
        TargetCar = nullptr;
        ZeroRates();
        if (GetOwner()) return; // Coordinator-owned effects never jump to another car.
        SearchDelay -= DeltaSeconds;
        if (SearchDelay > 0.f) return;
        SearchDelay = 1.f;
        for (TActorIterator<AGTCarPawn> It(GetWorld()); It; ++It)
        {
            TargetCar = *It;
            AddTickPrerequisiteActor(TargetCar);
            break;
        }
        if (!TargetCar) return;
        ResetDust();
    }
    const UGTTractionComponent* Traction = TargetCar->GetTraction();
    if (!Traction || !DustSystem) { ZeroRates(); return; }
    if (Wheels.Num() != Traction->Wheels.Num())
    {
        ResetDust();
        Wheels.SetNum(Traction->Wheels.Num());
        PreviousContacts.Init(TargetCar->GetActorLocation(), Wheels.Num());
    }
    const UGTWeatherSubsystem* Weather = GetWorld()->GetSubsystem<UGTWeatherSubsystem>();
    const float Wet = WetnessOverride >= 0.f ? WetnessOverride : Weather ? Weather->GetWetness() : 0.f;
    const FVector Wind = Weather ? Weather->GetWindVector() * FMath::Clamp(WindScale, 0.f, 2.f) : FVector::ZeroVector;
    const FVector Velocity = TargetCar->GetVelocity();
    const UChaosWheeledVehicleMovementComponent* Move = TargetCar->GetChaosMovement();
    TotalRate = 0.f;
    EmittingWheels = 0;
    for (int32 I = 0; I < Wheels.Num(); ++I)
    {
        const FGTWheelTraction& W = Traction->Wheels[I];
        const UGTSurfacePhysMaterial* Gravel = Move && I < Move->GetNumWheels() ? UGTSprayComponent::GravelSpraySurface(Move->GetWheelState(I)) : nullptr;
        const bool Dusty = (W.bInGravelPatch || Gravel || W.SurfaceTag == GTTags::Surface_Dirt.GetTag() || W.SurfaceTag == GTTags::Surface_Sand.GetTag())
            && !W.bInMudPatch && !W.bInSnowPatch && W.WaterDepthM <= 0.025f;
        const bool On = bEnabled && CVarDustLab.GetValueOnGameThread() != 0;
        float Strength = On ? EmissionStrength(W.bInContact, Dusty, Velocity.Size2D(), W.bSlipping ? W.SlipMagnitude : 0.f, Wet) : 0.f;
        // Bounded, independent wheel bursts. No accumulation while wet, stopped or airborne.
        const float Noise = FMath::PerlinNoise1D(GetWorld()->GetTimeSeconds() * 2.1f + I * 17.73f);
        Strength *= FMath::Clamp(Intensity, 0.f, 3.f) * FMath::Clamp(1.f + Noise, 0.45f, 1.55f);
        UNiagaraComponent* Nc = Wheels[I];
        if (!Nc && Strength > 0.f)
        {
            Nc = NewObject<UNiagaraComponent>(this);
            Nc->SetAsset(DustSystem);
            Nc->SetAutoActivate(false);
            Nc->SetupAttachment(GetRootComponent());
            Nc->SetAbsolute(true, true, true);
            Nc->SetCastShadow(false);
            Nc->RegisterComponent();
            Wheels[I] = Nc;
            PreviousContacts[I] = W.ContactPoint;
        }
        if (!Nc) continue;
        // Reset only a teleport; ordinary travel and turns leave their particles in world space.
        if (W.bInContact && FVector::DistSquared(W.ContactPoint, PreviousContacts[I]) > FMath::Square(3000.f)) Nc->ReinitializeSystem();
        if (W.bInContact) PreviousContacts[I] = W.ContactPoint;
        FVector Heading(W.TyreHeading.X, W.TyreHeading.Y, 0.f);
        if (!Heading.Normalize()) Heading = TargetCar->GetActorForwardVector();
        const float Direction = FMath::Abs(W.TreadCmPerS) > 10.f ? FMath::Sign(W.TreadCmPerS) : FMath::Sign(FVector::DotProduct(Velocity, Heading));
        const FVector Back = Heading * -Direction;
        const FVector Side = TargetCar->GetActorRightVector() * (I % 2 == 0 ? -1.f : 1.f);
        Nc->SetWorldLocation(PreviousContacts[I] + FVector(0, 0, 22) + Back * 18.f);
        Nc->SetVariableVec3(TEXT("User.BaseVelocity"), Velocity * 0.12f + Back * (80.f + FMath::Min(400.f, FMath::Abs(W.SlipMagnitude) * 0.15f)) + Side * 50.f + FVector(0, 0, 180));
        Nc->SetVariableVec3(TEXT("User.Wind"), Wind);
        // Tint is stored at particle spawn, so old dirt puffs don't recolour on entering gravel.
        FLinearColor Tint = W.bInGravelPatch || Gravel ? FLinearColor(0.29f, 0.27f, 0.22f) : FLinearColor(0.34f, 0.235f, 0.14f);
        if (Gravel && (Gravel->DustTint.R > 0.f || Gravel->DustTint.G > 0.f || Gravel->DustTint.B > 0.f)) Tint = Gravel->DustTint;
        Nc->SetVariableLinearColor(TEXT("User.DustTint"), Tint);
        Nc->SetVariableFloat(TEXT("User.ContactRate"), 18.f * Strength);
        Nc->SetVariableFloat(TEXT("User.WakeRate"), 12.f * Strength);
        Nc->SetVariableFloat(TEXT("User.TrailRate"), 5.f * Strength);
        TotalRate += 35.f * Strength;
        if (Strength > 0.f) ++EmittingWheels;
        if (!Nc->IsActive() && Strength > 0.f) Nc->Activate(true);
        if (Nc->IsActive() && Strength <= 0.f)
        {
            int32 Alive = 0;
            for (int32 E = 0; E < 3; ++E) Alive += UGTSprayComponent::GetNiagaraLiveCount(Nc, E);
            if (Alive == 0) Nc->Deactivate();
        }
    }
}
