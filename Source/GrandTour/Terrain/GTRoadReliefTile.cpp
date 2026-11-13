#include "Terrain/GTRoadReliefTile.h"
#include "Terrain/GTLandscapeSurface.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
AGTRoadReliefTile::AGTRoadReliefTile()
{
    Mesh=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("RoadRelief"));SetRootComponent(Mesh);
    Mesh->SetMobility(EComponentMobility::Static);Mesh->bUseComplexAsSimpleCollision=true;
    Mesh->bUseAsyncCooking=false;Mesh->SetCollisionProfileName(TEXT("BlockAll"));
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Mesh->SetCastShadow(true);
    MineralBase=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("MineralBase"));
    MineralBase->SetupAttachment(Mesh);MineralBase->SetMobility(EComponentMobility::Static);
    MineralBase->bUseComplexAsSimpleCollision=true;MineralBase->bUseAsyncCooking=false;
    MineralBase->SetCollisionProfileName(TEXT("BlockAll"));
    MineralBase->SetCollisionEnabled(ECollisionEnabled::PhysicsOnly);
    MineralBase->SetVisibility(false);MineralBase->SetHiddenInGame(true);MineralBase->SetCastShadow(false);
}
float AGTRoadReliefTile::VertexBase(int32 I) const
{
    if(!Surface||!Surface->bUseNativeSubstanceResponse)return Heights[I];
    // Finite soil layer, never an unbounded collision hole. Unpainted/fixed
    // vertices preserve their original surface and meet adjacent tiles exactly.
    const auto P=Soil.IsValidIndex(I)?Soil[I]:FLinearColor(0,0,1,0);
    const float Yield=FMath::Clamp(P.A,0.f,1.f)*(1.f-FMath::Clamp(P.B,0.f,1.f));
    return Heights[I]-FMath::Clamp(P.R,0.f,124.f)*Yield;
}
float AGTRoadReliefTile::MineralHeightAt(FVector2D XY) const
{
    if(Intervals<1||Heights.Num()!=FMath::Square(Intervals+1))return HeightAt(XY);
    const FVector2D Q=(XY-FVector2D(GetActorLocation()))*(Intervals/SpanCm);
    const int32 X=FMath::Clamp(FMath::FloorToInt(Q.X),0,Intervals-1),Y=FMath::Clamp(FMath::FloorToInt(Q.Y),0,Intervals-1),I=Y*(Intervals+1)+X;
    const float U=FMath::Clamp(float(Q.X-X),0.f,1.f),V=FMath::Clamp(float(Q.Y-Y),0.f,1.f);
    const float A=VertexBase(I),B=VertexBase(I+1),C=VertexBase(I+Intervals+1),D=VertexBase(I+Intervals+2);
    return U+V<=1?A+(B-A)*U+(C-A)*V:D+(C-D)*(1-U)+(B-D)*(1-V);
}
void AGTRoadReliefTile::BuildMineralBase()
{
    if(Intervals<1||Heights.Num()!=FMath::Square(Intervals+1))return;
    const int32 Row=Intervals+1;TArray<FVector> V,N;TArray<FVector2D> UV;TArray<int32> Indices;TArray<FLinearColor> C;TArray<FProcMeshTangent> T;
    for(int32 Y=0;Y<Row;++Y)for(int32 X=0;X<Row;++X)
        V.Add(FVector(double(X)*SpanCm/Intervals,double(Y)*SpanCm/Intervals,VertexBase(Y*Row+X)-GetActorLocation().Z));
    for(int32 Y=0;Y<Intervals;++Y)for(int32 X=0;X<Intervals;++X)
    {const int32 I=Y*Row+X;Indices.Append({I,I+Row,I+1,I+1,I+Row,I+Row+1});}
    MineralBase->CreateMeshSection_LinearColor(0,V,Indices,N,UV,C,T,true);
    const bool Yielding=Surface&&Surface->bUseNativeSubstanceResponse;
    Mesh->SetCollisionEnabled(Yielding?ECollisionEnabled::QueryOnly:ECollisionEnabled::QueryAndPhysics);
    MineralBase->SetCollisionEnabled(Yielding?ECollisionEnabled::PhysicsOnly:ECollisionEnabled::NoCollision);
}
float AGTRoadReliefTile::HeightAt(FVector2D XY) const
{
    if(Intervals<1||Heights.Num()!=FMath::Square(Intervals+1))return GetActorLocation().Z;
    const FVector2D Q=(XY-FVector2D(GetActorLocation()))*(Intervals/SpanCm);
    const int32 X=FMath::Clamp(FMath::FloorToInt(Q.X),0,Intervals-1),Y=FMath::Clamp(FMath::FloorToInt(Q.Y),0,Intervals-1);
    const float U=FMath::Clamp(float(Q.X-X),0.f,1.f),V=FMath::Clamp(float(Q.Y-Y),0.f,1.f);const int32 I=Y*(Intervals+1)+X;
    const float A=Heights[I],B=Heights[I+1],C=Heights[I+Intervals+1],D=Heights[I+Intervals+2];
    return U+V<=1?A+(B-A)*U+(C-A)*V:D+(C-D)*(1-U)+(B-D)*(1-V);
}
void AGTRoadReliefTile::BuildMesh()
{
    if(Intervals<1||Heights.Num()!=FMath::Square(Intervals+1))return;
    const int32 Row=Intervals+1;TArray<FVector> V;TArray<FVector2D> UV;TArray<int32> Indices;
    TArray<FLinearColor> C;TArray<FProcMeshTangent> T;
    for(int32 Y=0;Y<Row;++Y)for(int32 X=0;X<Row;++X)
    {V.Add(FVector(double(X)*SpanCm/Intervals,double(Y)*SpanCm/Intervals,Heights[Y*Row+X]-GetActorLocation().Z));UV.Add(FVector2D(double(X)/Intervals,double(Y)/Intervals));}
    for(int32 Y=0;Y<Intervals;++Y)for(int32 X=0;X<Intervals;++X)
    {const int32 I=Y*Row+X;Indices.Append({I,I+Row,I+1,I+1,I+Row,I+Row+1});}
    Mesh->CreateMeshSection_LinearColor(0,V,Indices,Normals,UV,C,T,true);Mesh->MarkRenderStateDirty();
    BuildMineralBase();
}
FLinearColor AGTRoadReliefTile::SoilAt(FVector2D XY,FLinearColor Fallback) const
{
    if(Soil.Num()!=Heights.Num()||Intervals<1)return Fallback;
    const FVector2D Q=(XY-FVector2D(GetActorLocation()))*(Intervals/SpanCm);
    const int32 X=FMath::Clamp(FMath::FloorToInt(Q.X),0,Intervals-1),Y=FMath::Clamp(FMath::FloorToInt(Q.Y),0,Intervals-1);
    const float U=FMath::Clamp(float(Q.X-X),0.f,1.f),V=FMath::Clamp(float(Q.Y-Y),0.f,1.f);const int32 I=Y*(Intervals+1)+X;
    auto Read=[&](int32 J){return Soil[J].R<0?Fallback:Soil[J];};
    return FMath::Lerp(FMath::Lerp(Read(I),Read(I+1),U),FMath::Lerp(Read(I+Intervals+1),Read(I+Intervals+2),U),V);
}
void AGTRoadReliefTile::BeginPlay()
{
    Super::BeginPlay();
    // Migrates already-saved maps too; no road regeneration is required.
    BuildMineralBase();
    if(Mesh->GetMaterial(0)){Dynamic=Mesh->CreateDynamicMaterialInstance(0);Dynamic->SetScalarParameterValue(TEXT("MR_ActiveGrid"),1);if(bHaveWindow)Dynamic->SetVectorParameterValue(TEXT("MR_VisualWindow"),LastWindow);}
}
void AGTRoadReliefTile::BindWindow(FLinearColor Window)
{LastWindow=Window;bHaveWindow=true;if(Dynamic)Dynamic->SetVectorParameterValue(TEXT("MR_VisualWindow"),Window);}
