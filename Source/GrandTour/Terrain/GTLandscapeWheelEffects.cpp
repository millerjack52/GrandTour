#include "Terrain/GTLandscapeWheelEffects.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTMudRunnerWheelEffects.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTVehicleTuningComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Materials/MaterialInterface.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

UGTLandscapeWheelEffects::UGTLandscapeWheelEffects()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
}

void UGTLandscapeWheelEffects::BeginPlay()
{
    Super::BeginPlay();
    Surface=Cast<AGTLandscapeSurface>(GetOwner());
    if (!Surface) {SetComponentTickEnabled(false);return;}
    // Regional integrations have one recovered emitter for the possessed vehicle.
    // Do not also allocate/emit the older per-surface mud particle system.
    if (Surface->bSeparateVisualMesh && AGTMudRunnerWheelEffects::IsActive(this)) {SetComponentTickEnabled(false);return;}
    // Sand uses the existing dry-dust coordinator, not cohesive mud chunks or wet flicks.
    if (Surface->bUseGranularResponse) {SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteActor(Surface);
    FineSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/GrandTour/FX/VehicleSurface/Benmore_20261012_162504/NS_MudFlick.NS_MudFlick"));
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/GrandTour/ArtTests/MudResponse/M_ResponseClod.M_ResponseClod"));
    for (int32 I=0;I<4;++I)
    {
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,*FString::Printf(TEXT("/Game/GrandTour/Mud/Clods/SM_GT_Clod_%d.SM_GT_Clod_%d"),I,I));
        if (!Mesh) continue;
        auto* C=NewObject<UInstancedStaticMeshComponent>(Surface);
        C->SetStaticMesh(Mesh); C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        C->SetCanEverAffectNavigation(false); C->SetCastShadow(Surface->GetVisualQuality()==2);
        C->PreAllocateInstancesMemory(256);
        if (Material) C->SetMaterial(0,Material);
        C->RegisterComponent(); Meshes.Add(C);
    }
}

void UGTLandscapeWheelEffects::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Function)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(LandscapeMud_Effects);
    Super::TickComponent(Dt,Type,Function);
    const int32 Quality=AGTLandscapeSurface::GetVisualQuality();
    const int32 MaxClods=Quality==0 ? 64 : Quality==1 ? 128 : 256;
    const float Density=Quality==0 ? .35f : Quality==1 ? .65f : 1.f;
    if (AppliedQuality!=Quality)
    {
        AppliedQuality=Quality;SetComponentTickInterval(Quality==0 ? .05f : Quality==1 ? 1.f/30.f : 0.f);
        for (UInstancedStaticMeshComponent* M:Meshes) M->SetCastShadow(Quality==2);
        if (Clods.Num()>MaxClods) Clods.SetNum(MaxClods);
    }
    Dt=FMath::Clamp(Dt,0.f,.05f); Rate=0;
    AActor* Pawn=UGameplayStatics::GetPlayerPawn(this,0);
    if (Car.Get()!=Pawn)
    {
        for (UNiagaraComponent* N:Fines) if(N)N->DestroyComponent();
        Fines.Reset(); Carry.Reset(); Last.Reset(); Clods.Reset(); Car=Pawn;
    }
    const auto* T=Pawn?Pawn->FindComponentByClass<UGTTractionComponent>():nullptr;
    const auto* Tuning=Pawn?Pawn->FindComponentByClass<UGTVehicleTuningComponent>():nullptr;
    if (T)
    {
        const int32 Count=T->Wheels.Num();
        Fines.SetNum(Count); Carry.SetNumZeroed(Count); Last.SetNum(Count);
        for(int32 I=0;I<Count;++I)
        {
            const auto& W=T->Wheels[I];
            const auto S=Surface->SampleSurface(FVector2D(W.ContactPoint));
            const bool Teleport=!Last[I].IsNearlyZero() && FVector::DistSquared(Last[I],W.ContactPoint)>FMath::Square(300.f);
            Last[I]=W.ContactPoint;
            const float Tread=FMath::Abs(W.TreadCmPerS);
            const float Slip=W.bSlipping?FMath::Max(0.f,W.SlipMagnitude*FMath::Sign(W.TreadCmPerS)):0.f;
            const float Exposed=FMath::Lerp(1.f,FMath::SmoothStep(.12f,.75f,S.Disturbance),S.GrassCover);
            const float Supply=FMath::SmoothStep(.2f,12.f,S.SinkageCapCm)*FMath::Lerp(.2f,1.f,S.Wetness)*Exposed;
            const float Work=FMath::Clamp(Tread/1000.f+Slip/500.f,0.f,1.8f);
            const bool bProving=Surface->bUseSoilShearResponse;
            const float Activity=bEnabled && !S.bGranularResponse && W.bInContact && !Teleport && W.WaterDepthM<.35f
                ? FMath::SmoothStep(15.f,100.f,Tread)*(bProving ? FMath::Sqrt(Work) : Work)*Supply : 0.f;
            // Cohesive mud releases in groups; liquid fines fill the space between the heavier clods.
            const float Burst=FMath::Lerp(.3f,1.7f,FMath::SmoothStep(-.3f,.55f,FMath::PerlinNoise1D(GetWorld()->TimeSeconds*8.f+I*13.71f)));
            const float Pooled=FMath::SmoothStep(1.f,12.f,S.WaterDepthCm);
            const float ClodRate=Activity*FMath::Lerp(14.f,32.f,S.Cohesion)*Burst*Density*FMath::Lerp(1.f,.3f,Pooled);
            Rate+=ClodRate;
            FVector Heading(W.TyreHeading,0); if(!Heading.Normalize())Heading=Pawn->GetActorForwardVector();
            const FVector Back=-Heading*FMath::Sign(W.TreadCmPerS);
            const FVector Side=Pawn->GetActorRightVector()*(I%2?-1.f:1.f);
            const auto* Tuned=Tuning && Tuning->GetCurrent().Wheels.IsValidIndex(I) ? &Tuning->GetCurrent().Wheels[I] : nullptr;
            // Soil contacts already contain the displaced height and loaded penetration.
            // Adding SurfaceDelta again buries the emitter below the new ruts.
            const float SurfaceOffset=Tuned && Tuned->bLandscapeSupport ? Tuned->SinkageCm : S.SurfaceDeltaCm;
            // Release from the rear shoulder of the rotating tread, above the rut's
            // surface. Small cohesive flecks need a visible arc even at crawling speed.
            const FVector Outward=bProving ? Pawn->GetActorRightVector()*(I%2 ? 9.f : -9.f) : FVector::ZeroVector;
            const FVector Origin=W.ContactPoint+Back*25.f+Outward+FVector(0,0,(bProving?30.f:25.f)+SurfaceOffset+S.WaterDepthCm);
            const float Up=bProving ? 140.f+Tread*.5f : 100.f+Tread*.36f;
            const FVector Velocity=Pawn->GetVelocity()*.65f+Back*FMath::Min(Tread*.65f,1300.f)+FVector(0,0,FMath::Min(Up,bProving?480.f:700.f));
            if (!Meshes.IsEmpty())
            {
                if(Teleport)Carry[I]=0;
                Carry[I]+=ClodRate*Dt;
                while(Carry[I]>=1.f)
                {
                    Carry[I]-=1.f;
                    if(Clods.Num()>=MaxClods){Carry[I]=0;break;}
                    FClod C; C.Mesh=Random.RandRange(0,Meshes.Num()-1);
                    const float Size=FMath::Lerp(2.f,11.f,FMath::Pow(Random.FRand(),2.f))*FMath::Lerp(.6f,1.f,S.Cohesion);
                    const FVector Extent=Meshes[C.Mesh]->GetStaticMesh()->GetBoundingBox().GetSize();
                    C.Scale=FVector(Size,Size*Random.FRandRange(.55f,.95f),Size*Random.FRandRange(.35f,.85f))/FMath::Max(Extent.GetMax(),1.);
                    C.P=Origin+Side*Random.FRandRange(-8.f,8.f);
                    C.V=Velocity*Random.FRandRange(.65f,1.2f)+Side*Random.FRandRange(-100.f,100.f);
                    C.R=FRotator(Random.FRandRange(0,360),Random.FRandRange(0,360),0);
                    C.Spin=FRotator(Random.FRandRange(-420,420),Random.FRandRange(-300,300),Random.FRandRange(-400,400));
                    C.Life=Random.FRandRange(1.4f,2.2f); Clods.Add(C); ++Emitted;
                }
            }
            UNiagaraComponent* N=Fines[I];
            if(!N && Activity>0 && FineSystem && Quality>0)
            {
                N=NewObject<UNiagaraComponent>(Surface);N->SetAsset(FineSystem);N->SetAutoActivate(false);
                N->SetAbsolute(true,true,true);N->SetCastShadow(false);N->RegisterComponent();Fines[I]=N;
            }
            if(N)
            {
                if(Teleport)N->ReinitializeSystem();
                N->SetWorldLocation(Origin);
                N->SetVariableVec3(TEXT("User.BaseVelocity"),Velocity);
                const FLinearColor Tint=bProving
                    ? FMath::Lerp(FLinearColor(.055f,.039f,.024f),FLinearColor(.09f,.075f,.05f),Pooled)
                    : FMath::Lerp(FLinearColor(.13f,.105f,.075f),FLinearColor(.22f,.20f,.15f),Pooled);
                N->SetVariableLinearColor(TEXT("User.MudTint"),Tint);
                N->SetVariableFloat(TEXT("User.MudRate"),(Quality>0 ? Activity*Burst*120.f*FMath::Lerp(.3f,1.f,S.Wetness)*Density*FMath::Lerp(1.f,1.6f,Pooled) : 0.f));
                if(Activity>0 && !N->IsActive())N->Activate(true);
            }
        }
    }
    if (!T) for (UNiagaraComponent* N:Fines) if (N) N->SetVariableFloat(TEXT("User.MudRate"),0.f);
    InstanceTransforms.SetNum(Meshes.Num());
    for (auto& Transforms:InstanceTransforms) Transforms.Reset();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(LandscapeMudClods),false,Pawn);
    for(int32 I=Clods.Num()-1;I>=0;--I)
    {
        auto& C=Clods[I]; C.Age+=Dt;
        if(C.Age>C.Life){Clods.RemoveAtSwap(I);continue;}
        if(!C.Landed)
        {
            const FVector Old=C.P;C.V.Z-=980.f*Dt;C.V*=FMath::Exp(-.2f*Dt);C.P+=C.V*Dt;C.R+=C.Spin*Dt;
            FHitResult Hit;
            bool HitGround=C.V.Z<0 && GetWorld()->LineTraceSingleByChannel(Hit,Old+FVector(0,0,20),C.P-FVector(0,0,20),ECC_Visibility,Params);
            if(HitGround && C.V.Z<0)
            {
                const auto S=Surface->SampleSurface(FVector2D(C.P));
                C.P.Z=Hit.ImpactPoint.Z+(S.bAuthored?S.SurfaceDeltaCm:0.f)+.5f;
                C.Landed=true;C.Scale.Z*=.25;C.Scale.X*=1.4;C.Scale.Y*=1.4;C.R.Pitch=C.R.Roll=0;
                C.Life=C.Age+.65f;++Landed;
            }
        }
        InstanceTransforms[C.Mesh].Add(FTransform(C.R,C.P,C.Scale));
    }
    for (int32 I=0;I<Meshes.Num();++I)
    {
        auto* M=Meshes[I].Get();const auto& Transforms=InstanceTransforms[I];
        const int32 OldCount=M->GetInstanceCount(),NewCount=Transforms.Num();
        if (OldCount>NewCount)
        {
            TArray<int32> Remove;
            for (int32 J=OldCount-1;J>=NewCount;--J) Remove.Add(J);
            M->RemoveInstances(Remove,true);
        }
        if (OldCount<NewCount)
        {
            TArray<FTransform> Added;
            Added.Append(Transforms.GetData()+OldCount,NewCount-OldCount);
            M->AddInstances(Added,false,true,false);
        }
        // Keep the instance buffers alive. One batched update replaces ClearInstances
        // and hundreds of individual AddInstance/render-state updates every frame.
        if (NewCount>0) M->BatchUpdateInstancesTransforms(0,Transforms,true,true,true);
    }
}

FString UGTLandscapeWheelEffects::GetEffectReport() const
{
    return FString::Printf(TEXT("emitted=%d landed=%d live=%d rate=%.3f"),Emitted,Landed,Clods.Num(),Rate);
}
