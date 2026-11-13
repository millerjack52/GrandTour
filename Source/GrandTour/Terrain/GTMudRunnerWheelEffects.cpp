#include "Terrain/GTMudRunnerWheelEffects.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTLandscapeWheelEffects.h"
#include "Terrain/GTMudRunnerSubstance.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTVehicleTuningComponent.h"
#include "Vehicle/GTSoilVehicleMovement.h"
#include "Vehicle/GTSprayComponent.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "ChaosVehicleWheel.h"
#include "ProceduralMeshComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"
#include "EngineUtils.h"
#include "Engine/World.h"

using namespace GTMudRunnerWheelFX;
namespace
{
struct FBrand { double Life,LifeRandom,Air,Gravity,Aspect; FVector Size; double Median,Scale,ScaleRandom; };
// Direct values from classes/particles/*.xml. Native source uses Y-up metres.
const FBrand Brands[Count]={
    {1.5,0,1.6,-4,.8,{.4,.8,1.8},.4,1,0},
    {2,0,1.2,-4,.8,{.5,2.5,5},.5,1,0},
    {.6,.1,4,-6,.6,{.6,.8,1.2},.5,1,0},
    {2.5,0,1,-2.6,.7,{.4,2,4},.5,.8,.2},
    {2.5,0,1,-2.6,.7,{.4,2,4},.5,.8,.2},
    {1.5,0,2,-4,1,{.4,.8,1.4},.5,1,.4},
    {0,0,1.8,-2.5,1,{.032,.028,0},.6,1.4,.8},
    {0,0,1.5,-2,.5,{.06,.04,.02},.3,1,.6},
    {0,0,4,-6,.4,{.02,.02,.01},.3,2.4,.8}
};
double Alpha(EKind K,double T)
{
    const FVector2D MudS[]={{0,0},{.1,220},{.7,160},{1,80}};
    const FVector2D MudL[]={{0,455},{.2,255},{.4,240},{1,140}};
    const FVector2D WaterS[]={{0,0},{.1,140},{.4,100},{1,100}};
    const FVector2D* Keys=K==MudSmall?MudS:K==MudLarge?MudL:WaterS;
    if(K>WaterSmall)return 1;
    for(int I=1;I<4;++I)if(T<=Keys[I].X)return FMath::Lerp(Keys[I-1].Y,Keys[I].Y,(T-Keys[I-1].X)/(Keys[I].X-Keys[I-1].X))/255.;
    return Keys[3].Y/255.;
}
FVector Swap(FVector V){return GTMudRunnerSubstance::PolarToUnreal(V);}
}
AGTMudRunnerWheelEffects::AGTMudRunnerWheelEffects()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostPhysics;
    Mesh=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("NativeSprites"));SetRootComponent(Mesh);
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);
}
bool AGTMudRunnerWheelEffects::IsActive(const UObject* Context)
{
    if(!Context || !Context->GetWorld())return false;
    return bool(TActorIterator<AGTMudRunnerWheelEffects>(Context->GetWorld()));
}
void AGTMudRunnerWheelEffects::BeginPlay()
{
    Super::BeginPlay();
    for(TActorIterator<AGTLandscapeSurface> It(GetWorld());It;++It)
        if(auto* Effects=It->FindComponentByClass<UGTLandscapeWheelEffects>())Effects->bEnabled=false;
}
void AGTMudRunnerWheelEffects::Emit(const FWheel& Wheel,float Dt)
{
    GTMudRunnerWheelFX::Emit(Wheel,Dt,[&](){return double(Random.FRand());},[&](const FSpawn& S)
    {
        if(Particles.Num()>=4096)Particles.RemoveAtSwap(0);
        const FBrand& B=Brands[S.Kind];FParticle P;P.Spawn=S;
        P.Life=B.Life+B.LifeRandom*(Random.FRand()*2-1);P.Scale=S.Scale*(B.Scale+B.ScaleRandom*(Random.FRand()*2-1));
        P.Frame=Random.RandRange(0,3);P.Parent=S.Kind;Particles.Add(P);++Spawned[S.Kind];
        // Recovered child allocation / divergence, 0x14088b8a0 and 0x14088bd20.
        const double Density[]={4,64,24,64,64,32},Offset[]={.1,.1,.1,0,0,0},Divergence[]={1,.75,1,.5,.5,.8};
        const double ExtraLife[]={2,2,.8,.5,.5,0},ExtraRandom[]={0,0,0,.5,.5,0};
        const EKind CK=S.Kind<=MudLarge?MudBits:S.Kind==WaterSmall?WaterBits:WaterDrops;
        const FBrand& CB=Brands[CK];const double Mean=(B.Size.X+B.Size.Y+B.Size.Z)/3*P.Scale;
        double Plane=-1.e10;
        if(auto* Water=GetWorld()->GetSubsystem<UGTWaterSubsystem>())
        {
            const auto Sample=Water->Sample(Swap(S.Org-FVector(0,10,0))*100);
            if(Sample.Kind!=EGTWaterKind::None)Plane=Sample.SurfaceZCm*.01;
        }
        FHitResult Hit;FCollisionQueryParams Params(SCENE_QUERY_STAT(NativeParticleBed),false);
        if(auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0))Params.AddIgnoredActor(Pawn);
        if(GetWorld()->LineTraceSingleByChannel(Hit,Swap(S.Org)*100+FVector(0,0,100),Swap(S.Org)*100-FVector(0,0,500),ECC_Visibility,Params))Plane=FMath::Max(Plane,Hit.ImpactPoint.Z*.01);
        const int32 Children=ChildCount(Mean,Density[S.Kind],Mean>0?(S.Org.Y+.5*Mean-Plane)/Mean:0,Random.FRand());
        for(int J=0;J<Children && Particles.Num()<4096;++J)
        {
            FParticle C;C.Parent=S.Kind;C.Spawn=S;C.Spawn.Kind=CK;
            const FVector R(Random.FRand()*2-1,Random.FRand()*2-1,Random.FRand()*2-1);
            C.Spawn.Org+=R*(.1*Mean+Offset[S.Kind]);
            C.Scale=(CB.Scale+(Random.FRand()*2-1)*CB.ScaleRandom)*(1.5-(FMath::Abs(R.X)+FMath::Abs(R.Y)+FMath::Abs(R.Z))/3);
            C.Scale=FMath::Max(1.,FMath::TruncToDouble(C.Scale*255/8))*8/255;
            C.Life=FMath::Max(.1,B.Life+ExtraLife[S.Kind]+(B.LifeRandom+ExtraRandom[S.Kind])*(Random.FRand()*2-1));
            const double Spread=(2*Offset[S.Kind]+Mean)/C.Life*Divergence[S.Kind];
            C.Spawn.Velocity=S.Velocity*(1+(Random.FRand()-.5)*Divergence[S.Kind]/16);
            C.Spawn.Velocity+=FVector(Random.FRand()*2-1,Random.FRand()*2-1,Random.FRand()*2-1)*Spread;
            C.Frame=Random.RandRange(0,3);C.PlaneY=Plane;Particles.Add(C);++Spawned[CK];
        }
    });
}
void AGTMudRunnerWheelEffects::Tick(float Dt)
{
    Super::Tick(Dt);
    for(int I=Particles.Num()-1;I>=0;--I)
    {
        auto& P=Particles[I];P.Age+=Dt;const auto& B=Brands[P.Spawn.Kind];
        // Source child collisions are GPU/world queries. The host uses the local
        // bed/water plane captured at emission; no imaginary solid droplet meshes.
        const bool Land=P.Spawn.Kind>=MudBits && P.Age>.05 && Position(P.Spawn.Org,P.Spawn.Velocity,P.Age,B.Air,B.Gravity).Y<P.PlaneY;
        if(P.Age>=P.Life || Land)Particles.RemoveAtSwap(I);
    }
    if(ReviewRemaining>0){Emit(Fixture,FMath::Min(Dt,ReviewRemaining));ReviewRemaining-=Dt;}
    else if(APawn* Car=UGameplayStatics::GetPlayerPawn(this,0))
    {
        auto* T=Car->FindComponentByClass<UGTTractionComponent>();
        auto* M=Car->FindComponentByClass<UGTSoilVehicleMovement>();
        auto* Tune=Car->FindComponentByClass<UGTVehicleTuningComponent>();
        auto* Water=GetWorld()->GetSubsystem<UGTWaterSubsystem>();
        // The older procedural chunks deliberately bypass suspension rays.
        // This study uses the source's solid fixed-root clods instead.
        if(M)M->SetWheelTraceResponseToChannel(ECC_Destructible,ECR_Block);
        if(T)WheelFilters.SetNum(T->Wheels.Num());
        if(T&&M&&M->UpdatedPrimitive)for(int I=0;I<T->Wheels.Num();++I)
        {
            if(!M->Wheels.IsValidIndex(I)||!M->Wheels[I])continue;
            const auto& W=T->Wheels[I];auto* Wheel=M->Wheels[I].Get();
            const FVector Centre=M->SoilWheelCentre(I);
            const auto S=AGTLandscapeSurface::QuerySurface(this,FVector2D(Centre));
            if(!S.bAuthored)continue;
            FWheel Input;Input.Radius=Wheel->WheelRadius*.01;Input.Width=Wheel->WheelWidth*.01;
            Input.Org=Swap(Centre*.01);
            const FVector F=Car->GetActorForwardVector().RotateAngleAxis(Wheel->GetSteerAngle(),Car->GetActorUpVector());
            Input.Forward=Swap(F);Input.Up=Swap(Car->GetActorUpVector());Input.Axle=Swap(FVector::CrossProduct(Car->GetActorUpVector(),F));
            Input.Right=FVector::DotProduct(Centre-Car->GetActorLocation(),Car->GetActorRightVector())>0;
            Input.Velocity=Swap(M->UpdatedPrimitive->GetPhysicsLinearVelocityAtPoint(Centre)*.01);
            Input.Speed=FVector::DotProduct(Input.Velocity,Input.Forward);Input.Omega=W.TreadCmPerS/FMath::Max(1.f,Wheel->WheelRadius);
            // 0x14091c0d3..0x14091c1c2: original per-update filters. Reversal
            // snaps angular speed; raw signed longitudinal speed stays separate.
            auto& Filter=WheelFilters[I];
            Filter.Omega=Filter.Omega*Input.Omega<0 ? Input.Omega : .9*Filter.Omega+.1*Input.Omega;
            Filter.Velocity=.8*Filter.Velocity+.2*Input.Velocity;
            Input.Omega=Filter.Omega;Input.Velocity=Filter.Velocity;
            // Query at the tyre bottom even while airborne: immersion is not a contact flag.
            if(Water)Input.WaterDepth=Water->Sample(Centre-FVector(0,0,Wheel->WheelRadius)).DepthCm*.01;
            if(!S.bGranularResponse && W.bInContact && Tune && Tune->GetCurrent().Wheels.IsValidIndex(I))
                Input.MudDepth=FMath::Max(0.f,Tune->GetCurrent().Wheels[I].SinkageCm)*.01;
            Input.WheelCount=T->Wheels.Num();Emit(Input,Dt);
        }
    }
    Draw();
}
void AGTMudRunnerWheelEffects::Draw()
{
    auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);if(!Camera)return;
    const FVector CameraPos=Camera->GetCameraLocation(),CameraRight=Camera->GetCameraRotation().RotateVector(FVector::RightVector);
    for(int K=0;K<Count;++K)
    {
        TArray<FVector> V,N;TArray<int32> Tri;TArray<FVector2D> UV,Data;TArray<FLinearColor> C;TArray<FProcMeshTangent> Tangent;
        const FBrand& B=Brands[K];
        // Transparent sprites are sorted back to front within each source brand.
        TArray<const FParticle*> Visible;for(const auto& P:Particles)if(P.Spawn.Kind==K)Visible.Add(&P);
        Visible.Sort([&](const FParticle& A,const FParticle& D){return FVector::DistSquared(Swap(A.Spawn.Org)*100,CameraPos)>FVector::DistSquared(Swap(D.Spawn.Org)*100,CameraPos);});
        for(const auto* PP:Visible)
        {
            const auto& P=*PP;const double T=FMath::Min(P.Age/P.Life,.999);
            const FVector Pos=Swap(Position(P.Spawn.Org,P.Spawn.Velocity,P.Age,B.Air,B.Gravity))*100;
            FVector Normal=(CameraPos-Pos).GetSafeNormal();
            FVector Up=FVector::VectorPlaneProject(Swap(P.Spawn.Velocity),Normal).GetSafeNormal();
            if(Up.IsNearlyZero()||K==WaterFluid)Up=Camera->GetCameraRotation().RotateVector(FVector::UpVector);
            FVector Right=FVector::CrossProduct(Up,Normal).GetSafeNormal();if(Right.IsNearlyZero())Right=CameraRight;
            Up=FVector::CrossProduct(Normal,Right).GetSafeNormal();
            const double Size=Curve(B.Size,B.Median,T)*P.Scale*100;
            FLinearColor Color=P.Parent<=MudLarge?FLinearColor(FMath::Pow(146/255.f,2.2f),FMath::Pow(132/255.f,2.2f),FMath::Pow(109/255.f,2.2f))*(P.Parent==MudSmall?.42f:.4f):FLinearColor(.6f,.64f,.65f);
            Color.A=P.Spawn.Opacity*Alpha(P.Parent,T);
            const int Base=V.Num();const FVector2D Corners[]={{0,0},{1,0},{0,1},{1,1}};
            for(auto Q:Corners)
            {
                V.Add(Pos+Right*((Q.X-.5)*2*Size*B.Aspect)+Up*((.5-Q.Y)*2*Size));N.Add(Normal);
                UV.Add(K>=MudBits?FVector2D(Q.X,(Q.Y+P.Frame)*.25):K==WaterFluid?(Q+FVector2D(P.Frame%2,P.Frame/2))*.5:Q);
                Data.Add(FVector2D(T,P.Age));C.Add(Color);Tangent.Add(FProcMeshTangent(Right,false));
            }
            Tri.Append({Base,Base+2,Base+1,Base+1,Base+2,Base+3});
        }
        Mesh->CreateMeshSection_LinearColor(K,V,Tri,N,UV,Data,{}, {},C,Tangent,false);
        if(Materials.IsValidIndex(K))Mesh->SetMaterial(K,Materials[K]);
    }
}
void AGTMudRunnerWheelEffects::ReviewWheel(FVector CentreCm,float SpeedMps,float Omega,float MudDepthM,float WaterDepthM,float Seconds)
{
    Fixture={};Fixture.Org=Swap(CentreCm*.01);Fixture.Velocity=FVector(SpeedMps,0,0);Fixture.Speed=SpeedMps;
    Fixture.Omega=Omega;Fixture.MudDepth=MudDepthM;Fixture.WaterDepth=WaterDepthM;ReviewRemaining=FMath::Clamp(Seconds,0.f,10.f);
}
void AGTMudRunnerWheelEffects::ClearReview(){ReviewRemaining=0;Particles.Reset();Mesh->ClearAllMeshSections();}
FString AGTMudRunnerWheelEffects::EffectReport()const
{
    return FString::Printf(TEXT("alive=%d mud_small=%d mud_impact=%d water_small=%d water_medium=%d water_large=%d water_fluid=%d"),Particles.Num(),Spawned[0],Spawned[1],Spawned[2],Spawned[3],Spawned[4],Spawned[5]);
}
FString AGTMudRunnerWheelEffects::PlacementReport()const
{
    FString Result;
    auto* Water=GetWorld()->GetSubsystem<UGTWaterSubsystem>();
    if(auto* Car=UGameplayStatics::GetPlayerPawn(this,0))
        if(auto* M=Car->FindComponentByClass<UGTSoilVehicleMovement>())
            for(int I=0;I<M->Wheels.Num();++I)if(M->Wheels[I])
            {
                const FVector P=M->SoilWheelCentre(I);
                const auto S=Water->Sample(P-FVector(0,0,M->Wheels[I]->WheelRadius));
                Result+=FString::Printf(TEXT("wheel%d centre=%s radius=%.2f surface=%.2f depth=%.2f omega=%.2f; "),I,*P.ToString(),M->Wheels[I]->WheelRadius,S.SurfaceZCm,S.DepthCm,WheelFilters.IsValidIndex(I)?WheelFilters[I].Omega:0.);
            }
    int32 CountSmall=0,Above=0;double MaxAbove=-1.e10,MeanAlpha=0,MeanVz=0;
    for(const auto& P:Particles)if(P.Spawn.Kind==WaterSmall)
    {
        const auto& B=Brands[WaterSmall];const FVector Pos=Swap(Position(P.Spawn.Org,P.Spawn.Velocity,P.Age,B.Air,B.Gravity))*100;
        const auto S=Water->Sample(Pos-FVector(0,0,1000));
        const double Height=Pos.Z-S.SurfaceZCm;
        ++CountSmall;Above+=Height>0;MaxAbove=FMath::Max(MaxAbove,Height);
        MeanAlpha+=P.Spawn.Opacity*Alpha(WaterSmall,P.Age/P.Life);MeanVz+=P.Spawn.Velocity.Y;
    }
    return Result+FString::Printf(TEXT("small_alive=%d above_water=%d max_above_cm=%.2f mean_alpha=%.4f mean_launch_vz=%.2f"),CountSmall,Above,MaxAbove,CountSmall?MeanAlpha/CountSmall:0.,CountSmall?MeanVz/CountSmall:0.);
}
