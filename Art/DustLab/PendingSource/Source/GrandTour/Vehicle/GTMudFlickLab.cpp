#include "Vehicle/GTMudFlickLab.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTSprayComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Core/GTGameplayTags.h"

bool AGTMudFlickLab::CoversWheel(const FGTWheelTraction& W)
{
    return !W.bInSnowPatch && !W.bInGravelPatch && (W.bInMudPatch
        || W.SurfaceTag == GTTags::Surface_Mud.GetTag() || W.SurfaceTag == GTTags::Surface_Bog.GetTag());
}

AGTMudFlickLab::AGTMudFlickLab()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostPhysics;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
}

float AGTMudFlickLab::Activity(bool Contact, bool Mud, float TreadCmS, float SlipCmS, float ThrownCm3S)
{
    if (!Contact || !Mud || FMath::Abs(TreadCmS) <= 25.f) return 0.f;
    const float Rolling = FMath::Clamp((FMath::Abs(TreadCmS)-25.f)/900.f, 0.f, 1.f);
    // Locked braking wheels must not create a reverse rooster tail.
    const float DriveSlip = FMath::Max(0.f, SlipCmS * FMath::Sign(TreadCmS));
    const float Spin = FMath::Clamp((DriveSlip-20.f)/800.f, 0.f, 1.f);
    const float Churn = FMath::Sqrt(FMath::Clamp(ThrownCm3S/20000.f, 0.f, 1.f));
    return FMath::Clamp(0.55f*Rolling + 0.55f*Spin + 0.4f*Churn, 0.f, 1.5f);
}

void AGTMudFlickLab::ResetSpray()
{
    for (UNiagaraComponent* Nc : Wheels) if (Nc) Nc->DestroyComponent();
    Wheels.Reset(); PreviousThrown.Reset(); PreviousContacts.Reset();
    TotalRate = 0.f; EmittingWheels = 0;
}

int32 AGTMudFlickLab::GetLiveParticles() const
{
    int32 Count = 0;
    for (UNiagaraComponent* Nc : Wheels) if (Nc)
        for (int32 E=0; E<2; ++E) Count += UGTSprayComponent::GetNiagaraLiveCount(Nc,E);
    return Count;
}

void AGTMudFlickLab::Tick(float Dt)
{
    Super::Tick(Dt);
    TotalRate = 0.f; EmittingWheels = 0;
    if (!IsValid(TargetCar))
    {
        for (UNiagaraComponent* Nc : Wheels) if (Nc) Nc->SetVariableFloat(TEXT("User.MudRate"),0.f);
        if (GetOwner()) return; // Coordinator retires this binding; do not attach to a different car.
        SearchDelay -= Dt;
        if (SearchDelay > 0.f) return;
        SearchDelay = 1.f;
        TargetCar = nullptr;
        for (TActorIterator<AGTCarPawn> It(GetWorld()); It; ++It) {TargetCar=*It; break;}
        if (!TargetCar) return;
    }
    if (BoundCar.Get() != TargetCar)
    {
        if (BoundCar.IsValid()) RemoveTickPrerequisiteActor(BoundCar.Get());
        ResetSpray(); BoundCar=TargetCar;
        AddTickPrerequisiteActor(TargetCar);
    }
    const UGTTractionComponent* T = TargetCar->GetTraction();
    if (!T || !MudSystem)
    {
        for (UNiagaraComponent* Nc : Wheels) if (Nc) Nc->SetVariableFloat(TEXT("User.MudRate"),0.f);
        return;
    }
    if (Wheels.Num() != T->Wheels.Num())
    {
        ResetSpray(); Wheels.SetNum(T->Wheels.Num());
        PreviousThrown.SetNum(T->Wheels.Num()); PreviousContacts.SetNum(T->Wheels.Num());
        for (int32 I=0; I<Wheels.Num(); ++I)
        {PreviousThrown[I]=T->Wheels[I].ThrownCm3; PreviousContacts[I]=T->Wheels[I].ContactPoint;}
    }
    for (int32 I=0; I<Wheels.Num(); ++I)
    {
        const FGTWheelTraction& W = T->Wheels[I];
        const bool Teleport = W.bInContact && FVector::DistSquared(W.ContactPoint,PreviousContacts[I])>FMath::Square(3000.f);
        const float VolumeRate = Teleport ? 0.f : static_cast<float>(FMath::Max(0.0,W.ThrownCm3-PreviousThrown[I])/FMath::Max(Dt,0.001f));
        PreviousThrown[I]=W.ThrownCm3;
        if (W.bInContact) PreviousContacts[I]=W.ContactPoint;
        const bool Mud = CoversWheel(W);
        const float A = bEnabled ? Activity(W.bInContact,Mud,W.TreadCmPerS,W.bSlipping?W.SlipMagnitude:0.f,VolumeRate) : 0.f;
        const float Burst = FMath::Clamp(1.f+FMath::PerlinNoise1D(GetWorld()->GetTimeSeconds()*7.f+I*19.37f),0.5f,1.5f);
        const float Rate = 150.f*A*FMath::Clamp(Intensity,0.f,3.f)*Burst;
        UNiagaraComponent* Nc=Wheels[I];
        if (!Nc && Rate>0.f)
        {
            Nc=NewObject<UNiagaraComponent>(this); Nc->SetAsset(MudSystem); Nc->SetAutoActivate(false);
            Nc->SetupAttachment(GetRootComponent()); Nc->SetAbsolute(true,true,true);
            Nc->SetCastShadow(false); Nc->RegisterComponent(); Wheels[I]=Nc;
        }
        if (!Nc) continue;
        if (Teleport) Nc->ReinitializeSystem();
        FVector Heading(W.TyreHeading.X,W.TyreHeading.Y,0.f);
        if (!Heading.Normalize()) Heading=TargetCar->GetActorForwardVector();
        const FVector Back=-Heading*FMath::Sign(W.TreadCmPerS);
        const float Speed=FMath::Min(FMath::Abs(W.TreadCmPerS),2000.f);
        const FVector Side=TargetCar->GetActorRightVector()*(I%2==0?-1.f:1.f);
        Nc->SetWorldLocation(PreviousContacts[I]+Back*45.f+Side*18.f+FVector(0,0,42));
        Nc->SetVariableVec3(TEXT("User.BaseVelocity"),Back*(120.f+Speed*.55f)+Side*60.f+FVector(0,0,280.f+Speed*.3f)+TargetCar->GetVelocity()*.15f);
        Nc->SetVariableLinearColor(TEXT("User.MudTint"),UGTSprayComponent::MudTintFor(W.PatchVariant));
        Nc->SetVariableFloat(TEXT("User.MudRate"),Rate);
        TotalRate += Rate*1.65f;
        if (Rate>0.f) {++EmittingWheels; if (!Nc->IsActive()) Nc->Activate(true);}
        else if (Nc->IsActive() && UGTSprayComponent::GetNiagaraLiveCount(Nc,0)+UGTSprayComponent::GetNiagaraLiveCount(Nc,1)==0) Nc->Deactivate();
    }
}
