#include "Terrain/GTForestGroundDetails.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"

static TAutoConsoleVariable<int32> CVarForestGround(TEXT("gt.ForestGround"),1,TEXT("Camera-local forest floor geometry; material coverage is independent."),ECVF_Default);
static TAutoConsoleVariable<int32> CVarForestGroundReport(TEXT("gt.ForestGround.Report"),0,TEXT("Log completed forest-floor streaming windows for validation."),ECVF_Default);
namespace ForestFloor
{
    static uint32 Hash(int32 X,int32 Y,uint32 Seed)
    {
        // A 25.6m pattern matches the authored moss mask; negatives wrap identically.
        uint32 H=uint32(X&15)*1597334677u ^ uint32(Y&15)*3812015801u ^ Seed;
        H=(H^(H>>16))*2246822519u;H=(H^(H>>13))*3266489917u;return H^(H>>16);
    }
    static float Unit(int32 X,int32 Y,uint32 Seed){return float(Hash(X,Y,Seed)&65535u)/65535.f;}
    static FVector2D Anchor(FIntPoint K){return FVector2D((K.X+.22+.56*Unit(K.X,K.Y,11))*160.,(K.Y+.22+.56*Unit(K.X,K.Y,17))*160.);}
}
AGTForestGroundDetails::AGTForestGroundDetails()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostPhysics;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("ForestFloorRoot")));
    for(int32 I=0;I<3;++I)
    {
        auto* C=CreateDefaultSubobject<UInstancedStaticMeshComponent>(*FString::Printf(TEXT("Floor%d"),I));
        C->SetupAttachment(RootComponent);C->SetMobility(EComponentMobility::Movable);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        C->SetGenerateOverlapEvents(false);C->SetCastShadow(true);C->bCastShadowAsTwoSided=true;
        C->bAffectDistanceFieldLighting=false;C->SetVisibleInRayTracing(false);C->SetBoundsScale(2.f);
        C->NumCustomDataFloats=4;C->SetCullDistances(2300,3000);FloorComponents.Add(C);
    }
}
bool AGTForestGroundDetails::ImportCoverage(const FString& File)
{
    TArray<uint8> Data;if(!FFileHelper::LoadFileToArray(Data,*File)||Data.Num()<4)return false;
    uint32 Size=0;FMemory::Memcpy(&Size,Data.GetData(),4);
    if(Size<2||Size>4096||int64(Size)*Size+4!=Data.Num())return false;
    Modify();CoverageSize=int32(Size);Coverage.SetNumUninitialized(Size*Size);
    FMemory::Memcpy(Coverage.GetData(),Data.GetData()+4,Coverage.Num());return true;
}
void AGTForestGroundDetails::BeginPlay()
{
    Super::BeginPlay();bConfigured=Surface&&Meshes.Num()==3&&Material&&Coverage.Num()==CoverageSize*CoverageSize&&CoverageSize>1;
    for(int32 I=0;I<3&&bConfigured;++I)bConfigured&=bool(Meshes[I]);
    if(!bConfigured){SetActorTickEnabled(false);return;}
    for(int32 I=0;I<3;++I){FloorComponents[I]->SetStaticMesh(Meshes[I]);FloorComponents[I]->SetMaterial(0,Material);FloorComponents[I]->SetNumCustomDataFloats(4);}
}
float AGTForestGroundDetails::Weight(FVector2D P) const
{
    const FVector2D UV=(P-CoverageOrigin)/CoverageSpan;
    if(UV.X<0||UV.Y<0||UV.X>=1||UV.Y>=1)return 0;
    const FVector2D Q=UV*CoverageSize-FVector2D(.5,.5);const int32 X=FMath::FloorToInt(Q.X),Y=FMath::FloorToInt(Q.Y);
    auto Read=[&](int32 A,int32 B){return Coverage[FMath::Clamp(B,0,CoverageSize-1)*CoverageSize+FMath::Clamp(A,0,CoverageSize-1)]/255.f;};
    return FMath::Lerp(FMath::Lerp(Read(X,Y),Read(X+1,Y),float(Q.X-X)),FMath::Lerp(Read(X,Y+1),Read(X+1,Y+1),float(Q.X-X)),float(Q.Y-Y));
}
void AGTForestGroundDetails::Refresh(FVector2D View)
{
    Centre=FVector2D(FMath::GridSnap(View.X,400.),FMath::GridSnap(View.Y,400.));
    const double Radius=FMath::Clamp(double(RadiusCm),3400.,5000.);
    for(auto It=Active.CreateIterator();It;++It)
    {
        if(FVector2D::DistSquared(ForestFloor::Anchor(It.Key()),Centre)<=Radius*Radius)continue;
        const FSlot S=It.Value();FloorComponents[S.Layer]->UpdateInstanceTransform(S.Index,FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),true,false,true);
        Free[S.Layer].Add(S.Index);It.RemoveCurrent();
    }
    Pending.Reset();Cursor=0;bReported=false;
    for(int32 Y=FMath::FloorToInt((Centre.Y-Radius)/160);Y<=FMath::CeilToInt((Centre.Y+Radius)/160);++Y)
        for(int32 X=FMath::FloorToInt((Centre.X-Radius)/160);X<=FMath::CeilToInt((Centre.X+Radius)/160);++X)
        {
            const FIntPoint K(X,Y);const FVector2D P=ForestFloor::Anchor(K);const double D=FVector2D::DistSquared(P,Centre);
            if(D<=Radius*Radius&&!Active.Contains(K)&&Weight(P)>.75f)Pending.Add({K,D});
        }
    Pending.Sort([](const FPending& A,const FPending& B){return A.Distance<B.Distance;});
    for(auto& C:FloorComponents)C->MarkRenderInstancesDirty();
}
bool AGTForestGroundDetails::Evaluate(FIntPoint K,int32& Layer,FTransform& T,FVector4& Fit)
{
    const FVector2D P=ForestFloor::Anchor(K);const auto H=Surface->GroundHeightAt(FVector(P,0));if(!H.IsSet())return false;
    const float RX=30+32*ForestFloor::Unit(K.X,K.Y,23),RY=RX*(.45f+.85f*ForestFloor::Unit(K.X,K.Y,29));
    const float Angle=360*ForestFloor::Unit(K.X,K.Y,31);Layer=int32(ForestFloor::Hash(K.X,K.Y,37)%3);
    const float R=FMath::Max(RX,RY)*1.45f;
    auto Height=[&](double X,double Y){return Surface->GroundHeightAt(FVector(X,Y,H.GetValue()));};
    const auto XP=Height(P.X+R,P.Y),XM=Height(P.X-R,P.Y),YP=Height(P.X,P.Y+R),YM=Height(P.X,P.Y-R);
    if(!XP.IsSet()||!XM.IsSet()||!YP.IsSet()||!YM.IsSet())return false;
    const float GX=(XP.GetValue()-XM.GetValue())/(2*R),GY=(YP.GetValue()-YM.GetValue())/(2*R);
    if(GX*GX+GY*GY>1.0f){++RejectedSupport;return false;}
    float Low=0,High=0;
    for(int32 I=0;I<8;++I)
    {
        const double A=I*UE_PI/4,DX=R*FMath::Cos(A),DY=R*FMath::Sin(A);const auto HH=Height(P.X+DX,P.Y+DY);
        if(!HH.IsSet()||Weight(P+FVector2D(DX,DY))<.65f)return false;
        const float Error=HH.GetValue()-H.GetValue()-GX*DX-GY*DY;Low=FMath::Min(Low,Error);High=FMath::Max(High,Error);
    }
    // Thin mat, conservative seating. Curved cliffs get material only.
    if(High-Low>8){++RejectedSupport;return false;}
    T=FTransform(FRotator(0,Angle,0),FVector(P,H.GetValue()+Low-1.0f),FVector(RX/50,RY/50,.65+.65*ForestFloor::Unit(K.X,K.Y,41)));
    Fit=FVector4(P.X,P.Y,GX,GY);return true;
}
void AGTForestGroundDetails::Tick(float Dt)
{
    Super::Tick(Dt);if(!bConfigured)return;
    const bool Enabled=CVarForestGround.GetValueOnGameThread()!=0;
    for(auto& C:FloorComponents)C->SetVisibility(Enabled);
    if(!Enabled)return;
    const auto* PC=UGameplayStatics::GetPlayerController(this,0);if(!PC)return;
    FVector View;FRotator Rot;PC->GetPlayerViewPoint(View,Rot);
    if(Centre.X==DBL_MAX||FVector2D::DistSquared(FVector2D(View),Centre)>400.*400.)Refresh(FVector2D(View));
    const double Start=FPlatformTime::Seconds(),Deadline=Start+FMath::Clamp(BudgetMs,.1f,2.f)*.001;
    bool Dirty[3]={false,false,false};
    while(Cursor<Pending.Num()&&FPlatformTime::Seconds()<Deadline)
    {
        const FIntPoint K=Pending[Cursor++].Key;int32 Layer;FTransform T;FVector4 Fit;
        if(!Evaluate(K,Layer,T,Fit))continue;
        auto* C=FloorComponents[Layer].Get();int32 Index;
        if(!Free[Layer].IsEmpty()){Index=Free[Layer].Pop(EAllowShrinking::No);C->UpdateInstanceTransform(Index,T,true,false,true);}
        else Index=C->AddInstance(T,true);
        for(int32 J=0;J<4;++J)C->SetCustomDataValue(Index,J,float(Fit[J]),false);
        Active.Add(K,{Layer,Index});Dirty[Layer]=true;
    }
    for(int32 I=0;I<3;++I)if(Dirty[I])FloorComponents[I]->MarkRenderInstancesDirty();
    PeakPumpMs=FMath::Max(PeakPumpMs,float((FPlatformTime::Seconds()-Start)*1000));
    if(Cursor==Pending.Num()&&!bReported){bReported=true;if(CVarForestGroundReport.GetValueOnGameThread())UE_LOG(LogTemp,Display,TEXT("FOREST_GROUND %s centre=%.0f,%.0f"),*ForestGroundReport(),Centre.X,Centre.Y);}
}
FString AGTForestGroundDetails::ForestGroundReport() const
{
    return FString::Printf(TEXT("active=%d pending=%d slots=%d rejected_support=%d peak_pump_ms=%.3f configured=%d"),Active.Num(),Pending.Num()-Cursor,FloorComponents[0]->GetInstanceCount()+FloorComponents[1]->GetInstanceCount()+FloorComponents[2]->GetInstanceCount(),RejectedSupport,PeakPumpMs,bConfigured);
}
