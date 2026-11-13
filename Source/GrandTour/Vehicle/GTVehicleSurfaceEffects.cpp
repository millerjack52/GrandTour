#include "Vehicle/GTVehicleSurfaceEffects.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTDustLab.h"
#include "Vehicle/GTMudFlickLab.h"
#include "Vehicle/GTSprayComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "NiagaraSystem.h"

static TAutoConsoleVariable<int32> CVarSurfaceEffects(TEXT("gt.SurfaceEffects"),1,
    TEXT("Placed vehicle surface effects: 0 restores legacy spray, 1 enables dust and mud flicks."),ECVF_Default);

AGTVehicleSurfaceEffects::AGTVehicleSurfaceEffects()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=0.25f;
    PrimaryActorTick.TickGroup=TG_PrePhysics;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
}

void AGTVehicleSurfaceEffects::Release(FBinding& B)
{
    if (AGTCarPawn* Car=B.Car.Get()) if (UGTSprayComponent* S=Car->GetSpray())
    {S->bExternalDustEffects=false; S->bExternalMudEffects=false;}
    if (B.Dust.IsValid()) B.Dust->Destroy();
    if (B.Mud.IsValid()) B.Mud->Destroy();
}

void AGTVehicleSurfaceEffects::EndPlay(const EEndPlayReason::Type Reason)
{
    for (FBinding& B : Bindings) Release(B);
    Bindings.Reset();
    Super::EndPlay(Reason);
}

void AGTVehicleSurfaceEffects::Tick(float Dt)
{
    Super::Tick(Dt);
    const bool On=bEnabled && CVarSurfaceEffects.GetValueOnGameThread()!=0;
    for (int32 I=Bindings.Num()-1; I>=0; --I)
    {
        if (!On || !Bindings[I].Car.IsValid()) {Release(Bindings[I]); Bindings.RemoveAtSwap(I);}
    }
    if (!On) return;
    for (TActorIterator<AGTCarPawn> It(GetWorld()); It; ++It)
    {
        AGTCarPawn* Car=*It;
        FBinding* B=Bindings.FindByPredicate([Car](const FBinding& Row){return Row.Car.Get()==Car;});
        if (!B) {B=&Bindings.AddDefaulted_GetRef(); B->Car=Car;}
        FActorSpawnParameters Params; Params.Owner=this; Params.ObjectFlags|=RF_Transient;
        Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if (DustSystem && !B->Dust.IsValid())
        {
            AGTDustLab* D=GetWorld()->SpawnActor<AGTDustLab>(AGTDustLab::StaticClass(),Car->GetActorTransform(),Params);
            if (D) {D->TargetCar=Car; D->DustSystem=DustSystem; D->AddTickPrerequisiteActor(Car); B->Dust=D;}
        }
        if (MudSystem && !B->Mud.IsValid())
        {
            AGTMudFlickLab* M=GetWorld()->SpawnActor<AGTMudFlickLab>(AGTMudFlickLab::StaticClass(),Car->GetActorTransform(),Params);
            if (M) {M->TargetCar=Car; M->MudSystem=MudSystem; B->Mud=M;}
        }
        if (!DustSystem && B->Dust.IsValid()) {B->Dust->Destroy(); B->Dust.Reset();}
        if (!MudSystem && B->Mud.IsValid()) {B->Mud->Destroy(); B->Mud.Reset();}
        if (B->Dust.IsValid()) B->Dust->Intensity=FMath::Clamp(DustIntensity,0.f,3.f);
        if (B->Mud.IsValid()) B->Mud->Intensity=FMath::Clamp(MudIntensity,0.f,3.f);
        if (UGTSprayComponent* S=Car->GetSpray())
        {
            S->bExternalDustEffects=B->Dust.IsValid();
            S->bExternalMudEffects=B->Mud.IsValid();
        }
    }
}
