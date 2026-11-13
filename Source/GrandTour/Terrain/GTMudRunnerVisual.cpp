#include "Terrain/GTMudRunnerVisual.h"
#include "Terrain/GTRoadReliefTile.h"
#include "Core/GTPerfProbe.h"
#include "Terrain/GTLandscapeSurface.h"
#include "ProceduralMeshComponent.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Terrain/GTWaterSheet.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "Vehicle/GTTractionComponent.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "ChaosVehicleWheel.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "EngineUtils.h"

namespace
{
struct FTreadClipVertex { FVector2D P,UV; };
TArray<FTreadClipVertex> ClipTread(const TArray<FTreadClipVertex>& Input,FVector2D A,FVector2D B)
{
    TArray<FTreadClipVertex> Out;
    if(Input.IsEmpty())return Out;
    auto Distance=[&](FVector2D P){return FVector2D::CrossProduct(B-A,P-A);};
    auto Previous=Input.Last();double DP=Distance(Previous.P);
    for(const auto& Current:Input)
    {
        const double DC=Distance(Current.P);
        if((DP>=0)!=(DC>=0))
        {
            const double T=DP/(DP-DC);
            Out.Add({FMath::Lerp(Previous.P,Current.P,T),FMath::Lerp(Previous.UV,Current.UV,T)});
        }
        if(DC>=0)Out.Add(Current);
        Previous=Current;DP=DC;
    }
    return Out;
}
}

AGTMudRunnerVisual::AGTMudRunnerVisual()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostPhysics;
    Mesh=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("NativeVisualGrid"));SetRootComponent(Mesh);
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(true);
    Mesh->SetBoundsScale(1.1f);
    Tracks=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("NativeTreadRibbons"));Tracks->SetupAttachment(Mesh);
    Tracks->SetCollisionEnabled(ECollisionEnabled::NoCollision);Tracks->SetCastShadow(false);Tracks->SetBoundsScale(1.1f);
}
void AGTMudRunnerVisual::BeginPlay()
{
    Super::BeginPlay();
    if(!Surface || !Surface->Landscape || !Material) { SetActorTickEnabled(false);return; }
    AddTickPrerequisiteActor(Surface);
    if(WaterSheet)AddTickPrerequisiteActor(WaterSheet);
    bTiled=UseTiledGrid();
    if(!bTiled)BuildGrid();
    Dynamic=UMaterialInstanceDynamic::Create(Material,this);
    Dynamic->SetScalarParameterValue(TEXT("MR_VisualGrid"),1);
    Mesh->SetMaterial(0,Dynamic);
    Surface->RegisterResearchMaterial(Dynamic);
    if(TrackMaterial)
    {
        TrackDynamic=UMaterialInstanceDynamic::Create(TrackMaterial,this);
        TrackDynamic->SetScalarParameterValue(TEXT("MR_VisualGrid"),1);
        Tracks->SetMaterial(0,TrackDynamic);Surface->RegisterResearchMaterial(TrackDynamic);
    }
    // PF1: the tread ribbons are built in world coordinates, so a window move never rebuilds them.
    Tracks->SetUsingAbsoluteLocation(true);Tracks->SetUsingAbsoluteRotation(true);Tracks->SetUsingAbsoluteScale(true);Tracks->SetWorldTransform(FTransform::Identity);
    if(bTiled)InitTiledGrid();
    if(bHideWholeLandscape)Surface->Landscape->SetActorHiddenInGame(true);
    else Surface->Landscape->SetLandscapeMaterialScalarParameterValue(TEXT("MR_BenmoreActive"),1.f);
    BindGridWindow();
    if(WaterSimulationMaterial && SedimentSimulationMaterial && WaveMaterial && WaterSheet)
    {
        WaterDynamic=UMaterialInstanceDynamic::Create(WaterSimulationMaterial,this);
        SedimentDynamic=UMaterialInstanceDynamic::Create(SedimentSimulationMaterial,this);
        Surface->RegisterResearchMaterial(WaterDynamic);Surface->RegisterResearchMaterial(SedimentDynamic);
        const int32 Side=FMath::Clamp(FMath::CeilToInt(2*WaterSheet->MudHalfSizeCm/FMath::Max(10.f,WaterSheet->MudCellCm)),8,128);
        for(int32 I=0;I<2;++I)
        {
            StateTargets.Add(UKismetRenderingLibrary::CreateRenderTarget2D(this,Side,Side,RTF_RGBA16f,FLinearColor(.5f,128.f/255.f,128.f/255.f,1)));
            SedimentTargets.Add(UKismetRenderingLibrary::CreateRenderTarget2D(this,Side,Side,RTF_RGBA16f,FLinearColor(0,0,0,1)));
        }
        Waves=UKismetRenderingLibrary::CreateRenderTarget2D(this,512,512,RTF_RGBA16f,FLinearColor(.5f,.5f,1,1));
    }
}

void AGTMudRunnerVisual::BuildGrid()
{
    GT_PERF_SCOPE(PerfVisGrid,"MudVisual.BuildGrid");
    const int32 N=FMath::Clamp(FMath::RoundToInt(2*HalfSizeCm/12.5f),8,512),Row=N+1;
    PerfVisGrid.Work=Row*Row;
    const float Step=2*HalfSizeCm/N;
    TArray<FVector> Vertices,Normals;TArray<FVector2D> UV;TArray<int32> Indices;
    TArray<FLinearColor> Colours;TArray<FProcMeshTangent> Tangents;
    Vertices.Reserve(Row*Row);Normals.Reserve(Row*Row);UV.Reserve(Row*Row);
    const FVector Centre=GetActorLocation();
    for(int32 Y=0;Y<Row;++Y)for(int32 X=0;X<Row;++X)
    {
        FVector P(-HalfSizeCm+X*Step,-HalfSizeCm+Y*Step,0);
        // Landscape's component lookup is half-open: the exact maximum edge
        // selects a nonexistent next component. Query just inside that edge so
        // adjoining visual tiles don't fall to world Z=0 on their final row.
        FVector Query=P+Centre;
        Query.X=FMath::Min(Query.X,Centre.X+HalfSizeCm-.01);
        Query.Y=FMath::Min(Query.Y,Centre.Y+HalfSizeCm-.01);
        const auto H=Surface->GroundHeightAt(Query);
        P.Z=H.IsSet()?H.GetValue()-Centre.Z:0;
        Vertices.Add(P);Normals.Add(FVector::UpVector);UV.Add(FVector2D(double(X)/N,double(Y)/N));
    }
    // Reuse the sampled grid: four extra landscape queries per vertex would
    // cause unnecessary work whenever the player window advances.
    if(!Surface->RoadReliefTiles.IsEmpty())for(int32 Y=0;Y<Row;++Y)for(int32 X=0;X<Row;++X)
    {
        const int32 L=FMath::Max(0,X-1),R=FMath::Min(N,X+1),B=FMath::Max(0,Y-1),T=FMath::Min(N,Y+1);
        Normals[Y*Row+X]=FVector(-(Vertices[Y*Row+R].Z-Vertices[Y*Row+L].Z)/((R-L)*Step),-(Vertices[T*Row+X].Z-Vertices[B*Row+X].Z)/((T-B)*Step),1).GetSafeNormal();
    }
    Indices.Reserve(N*N*6);
    for(int32 Y=0;Y<N;++Y)for(int32 X=0;X<N;++X)
    {
        const int32 I=Y*Row+X;
        Indices.Append({I,I+Row,I+1,I+1,I+Row,I+Row+1});
    }
    {
        GT_PERF_SCOPE(PerfVisSection,"MudVisual.BuildGrid.CreateSection");PerfVisSection.Work=Vertices.Num();
        Mesh->CreateMeshSection_LinearColor(0,Vertices,Indices,Normals,UV,Colours,Tangents,false);
    }
    if(Dynamic)Mesh->SetMaterial(0,Dynamic);
    UE_LOG(LogTemp,Display,TEXT("MudRunner visual grid: %d vertices, %.3f cm spacing"),Vertices.Num(),Step);
}
void AGTMudRunnerVisual::BindGridWindow()
{
    if(!bFollowPlayerGrid || !Surface || !Surface->Landscape)return;
    GT_PERF_SCOPE(PerfVisBind,"MudVisual.BindGridWindow");PerfVisBind.Work=Surface->RoadReliefTiles.Num();
    const FVector P=GetActorLocation();const FLinearColor Window(P.X,P.Y,HalfSizeCm,600.f);
    Surface->Landscape->SetLandscapeMaterialVectorParameterValue(TEXT("MR_VisualWindow"),Window);
    Surface->Landscape->SetLandscapeMaterialScalarParameterValue(TEXT("MR_ActiveGrid"),1.f);
    for(auto& Pair:Surface->RoadReliefTiles)if(IsValid(Pair.Value))Pair.Value->BindWindow(Window);
    for(auto* M:{Dynamic.Get(),TrackDynamic.Get()})if(M)M->SetVectorParameterValue(TEXT("MR_VisualWindow"),Window);
}
void AGTMudRunnerVisual::Tick(float Dt)
{
    Super::Tick(Dt);
    GT_PERF_SCOPE(PerfVisTick,"MudVisual.Tick");
    bFlippedThisTick=false;
    if(bFollowPlayerGrid && Surface && Surface->Landscape)
        if(const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0))
        {
            if(bTiled)PumpTiledGrid(Pawn->GetActorLocation(),FPlatformTime::Seconds()+.001);
            else
            {
                FVector P=Pawn->GetActorLocation();P.X=FMath::GridSnap(P.X,800.);P.Y=FMath::GridSnap(P.Y,800.);P.Z=0;
                P.X=FMath::Clamp(P.X,Surface->PaintOriginCm.X+HalfSizeCm,Surface->PaintOriginCm.X+Surface->PaintSizeCm-HalfSizeCm-.01);
                P.Y=FMath::Clamp(P.Y,Surface->PaintOriginCm.Y+HalfSizeCm,Surface->PaintOriginCm.Y+Surface->PaintSizeCm-HalfSizeCm-.01);
                if(FVector2D::Distance(FVector2D(P),FVector2D(GetActorLocation()))>1.)
                {
                    GT_PERF_SCOPE(PerfVisMove,"MudVisual.WindowMove");
                    SetActorLocation(P);BuildGrid();BindGridWindow();
                }
            }
        }
    if(Dynamic && Surface)Surface->RegisterResearchMaterial(Dynamic);
    if(TrackDynamic && Surface)Surface->RegisterResearchMaterial(TrackDynamic);
    if(!bFlippedThisTick)UpdateDetails(Dt);   // PF1: the flip tick (the window re-bind) does nothing else; the tread update catches up on the next one
    for(auto* Target:{Dynamic.Get(),TrackDynamic.Get()}) if(Target)
        if(const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0))
        {
            const FVector P=Pawn->GetActorLocation(),F=Pawn->GetActorForwardVector(),R=Pawn->GetActorRightVector();
            FVector Origin,Extent;Pawn->GetActorBounds(true,Origin,Extent);
            // Native interest-occlusion math consumes a footprint and four heights.
            // The existing vehicle supplies these host bounds, in metres/Y-up.
            Target->SetVectorParameterValue(TEXT("MR_InterestCenter"),FLinearColor(P.X*.01,P.Y*.01,0,0));
            Target->SetVectorParameterValue(TEXT("MR_InterestForward"),FLinearColor(F.X,F.Y,4.7f,0));
            Target->SetVectorParameterValue(TEXT("MR_InterestRight"),FLinearColor(R.X,R.Y,1.9f,0));
            const float H=(Origin.Z+Extent.Z)*.01;
            Target->SetVectorParameterValue(TEXT("MR_InterestHeight"),FLinearColor(H,H,H,H));
        }
    if(!WaterDynamic || !WaterSheet || !WaterSheet->BindResearchSimulation(WaterDynamic) || !WaterSheet->BindResearchSimulation(SedimentDynamic))return;
    Carry+=FMath::Min(Dt,.1f);if(Carry<1.f/30.f)return;
    Carry=FMath::Fmod(Carry,1.f/30.f);
    const int32 Next=1-Previous;
    for(auto* M:{WaterDynamic.Get(),SedimentDynamic.Get()})
    {
        M->SetTextureParameterValue(TEXT("MRWaterState"),StateTargets[Previous]);
        M->SetTextureParameterValue(TEXT("MRWaterSediment"),SedimentTargets[Previous]);
    }
    // Both native MRT outputs read the same previous generation. UE packs the
    // foam alpha into sediment G so opaque canvas draws preserve every channel.
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(this,StateTargets[Next],WaterDynamic);
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(this,SedimentTargets[Next],SedimentDynamic);
    if(!WaterSheet->AmbientWaveMaterial)
        UKismetRenderingLibrary::DrawMaterialToRenderTarget(this,Waves,WaveMaterial);
    Previous=Next;++WaterSteps;
    WaterSheet->SetResearchWaterTextures(StateTargets[Previous],SedimentTargets[Previous],Waves);
}
// PF1: tiled follow grid. See the declaration in the header.
namespace
{
    constexpr int32 TileCells=64,TileVerts=TileCells+1,TileApron=TileVerts+2;
    constexpr double TileWidthCm=800.,TileCellCm=12.5;
    double TileClock(){return FPlatformTime::Seconds();}
}

bool AGTMudRunnerVisual::UseTiledGrid() const
{
    if(!bFollowPlayerGrid)return false;
    const int32 N=FMath::Clamp(FMath::RoundToInt(2*HalfSizeCm/12.5f),8,512);
    return N%TileCells==0 && (N/TileCells)%2==0 && N/TileCells>=2 && N/TileCells<=8 && FMath::IsNearlyEqual(2*HalfSizeCm/N,12.5f,1.e-3f);
}

FVector AGTMudRunnerVisual::SnapWindowCentre(const FVector& Pawn) const
{
    // The single mesh snap and paint clamp, with the clamp rounded inwards onto the 800 cm lattice so the tiles stay aligned.
    auto Axis=[&](double V,double Origin)
    {
        const double Snapped=FMath::GridSnap(V,TileWidthCm);
        const double Lo=FMath::CeilToDouble((Origin+HalfSizeCm)/TileWidthCm)*TileWidthCm,Hi=FMath::FloorToDouble((Origin+Surface->PaintSizeCm-HalfSizeCm-.01)/TileWidthCm)*TileWidthCm;
        return Hi>=Lo ? FMath::Clamp(Snapped,Lo,Hi) : Snapped;
    };
    return FVector(Axis(Pawn.X,Surface->PaintOriginCm.X),Axis(Pawn.Y,Surface->PaintOriginCm.Y),0);
}

void AGTMudRunnerVisual::InitTiledGrid()
{
    TilesPerSide=FMath::Clamp(FMath::RoundToInt(2*HalfSizeCm/12.5f),8,512)/TileCells;
    const int32 Pool=TilesPerSide*TilesPerSide+2*TilesPerSide;
    TileIndices.Reset();TileUV.Reset();
    for(int32 Y=0;Y<TileCells;++Y)for(int32 X=0;X<TileCells;++X)
    {
        const int32 I=Y*TileVerts+X;
        TileIndices.Append({I,I+TileVerts,I+1,I+1,I+TileVerts,I+TileVerts+1});
    }
    for(int32 Y=0;Y<TileVerts;++Y)for(int32 X=0;X<TileVerts;++X)TileUV.Add(FVector2D(double(X)/TileCells,double(Y)/TileCells));
    for(int32 I=0;I<Pool;++I)
    {
        auto* C=NewObject<UProceduralMeshComponent>(this,*FString::Printf(TEXT("NativeVisualTile_%d"),I));
        C->SetupAttachment(Mesh);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCastShadow(true);C->SetBoundsScale(1.1f);
        C->SetUsingAbsoluteLocation(true);C->SetUsingAbsoluteRotation(true);C->SetUsingAbsoluteScale(true);
        C->RegisterComponent();AddInstanceComponent(C);
        C->SetMaterial(0,Dynamic);
        TilePool.Add(C);TileHasSection.Add(false);FreeTiles.Add(Pool-1-I);
    }
    // The first window is built whole, here, before the first frame: centre on the snapped spawn.
    const FVector C=SnapWindowCentre(GetActorLocation());
    SetActorLocation(C);
    WindowMinTile=FIntPoint(FMath::RoundToInt((C.X-HalfSizeCm)/TileWidthCm),FMath::RoundToInt((C.Y-HalfSizeCm)/TileWidthCm));
    for(int32 Y=0;Y<TilesPerSide;++Y)for(int32 X=0;X<TilesPerSide;++X)
    {
        BuildingTile=WindowMinTile+FIntPoint(X,Y);BuildingSlot=FreeTiles.Pop();BuildingRow=0;
        BuildTileHeights(DBL_MAX);FinishTile();
        TileSlot.Add(BuildingTile,BuildingSlot);BuildingSlot=-1;
    }
    UE_LOG(LogTemp,Display,TEXT("MudRunner visual grid: %d tiles of %d vertices (tiled follow grid, %d pooled)"),TilesPerSide*TilesPerSide,TileVerts*TileVerts,Pool);
}

bool AGTMudRunnerVisual::BuildTileHeights(double Deadline)
{
    GT_PERF_SCOPE(PerfVisTileHeights,"MudVisual.TileHeights");
    TileHeights.SetNumUninitialized(TileApron*TileApron,EAllowShrinking::No);
    const double X0=BuildingTile.X*TileWidthCm,Y0=BuildingTile.Y*TileWidthCm;
    // Heights over the tile plus a one-vertex apron (the normals need the neighbours); the query is held inside the painted area, as the single mesh holds its last row just inside the edge.
    const double MinX=Surface->PaintOriginCm.X,MinY=Surface->PaintOriginCm.Y,MaxX=MinX+Surface->PaintSizeCm-.01,MaxY=MinY+Surface->PaintSizeCm-.01;
    for(;BuildingRow<TileApron;++BuildingRow)
    {
        if(BuildingRow>0 && TileClock()>=Deadline)return false;
        for(int32 I=0;I<TileApron;++I)
        {
            const FVector Query(FMath::Clamp(X0+(I-1)*TileCellCm,MinX,MaxX),FMath::Clamp(Y0+(BuildingRow-1)*TileCellCm,MinY,MaxY),0);
            const auto H=Surface->GroundHeightAt(Query);
            TileHeights[BuildingRow*TileApron+I]=H.IsSet() ? H.GetValue() : 0.;
        }
        PerfVisTileHeights.Work+=TileApron;
    }
    return true;
}

void AGTMudRunnerVisual::FinishTile()
{
    GT_PERF_SCOPE(PerfVisTileFinish,"MudVisual.TileFinish");
    UProceduralMeshComponent* C=TilePool[BuildingSlot];
    // Normals from the sampled grid only where road relief exists (as the single mesh); central differences throughout, the apron makes them seamless across tiles.
    const bool bNormals=!Surface->RoadReliefTiles.IsEmpty();
    TileVertices.SetNumUninitialized(TileVerts*TileVerts,EAllowShrinking::No);TileNormals.SetNumUninitialized(TileVerts*TileVerts,EAllowShrinking::No);
    auto H=[&](int32 I,int32 J){return TileHeights[(J+1)*TileApron+(I+1)];};
    for(int32 J=0;J<TileVerts;++J)for(int32 I=0;I<TileVerts;++I)
    {
        TileVertices[J*TileVerts+I]=FVector(I*TileCellCm,J*TileCellCm,H(I,J));
        TileNormals[J*TileVerts+I]=bNormals ? FVector(-(H(I+1,J)-H(I-1,J))/(2*TileCellCm),-(H(I,J+1)-H(I,J-1))/(2*TileCellCm),1).GetSafeNormal() : FVector::UpVector;
    }
    C->SetWorldLocation(FVector(BuildingTile.X*TileWidthCm,BuildingTile.Y*TileWidthCm,0));
    const TArray<FLinearColor> NoColours;const TArray<FProcMeshTangent> NoTangents;
    if(!TileHasSection[BuildingSlot])
    {
        C->CreateMeshSection_LinearColor(0,TileVertices,TileIndices,TileNormals,TileUV,NoColours,NoTangents,false);
        TileHasSection[BuildingSlot]=true;
    }
    else C->UpdateMeshSection_LinearColor(0,TileVertices,TileNormals,TileUV,NoColours,NoTangents);
    PerfVisTileFinish.Work=TileVertices.Num();
}

void AGTMudRunnerVisual::PumpTiledGrid(const FVector& Pawn,double Deadline)
{
    if(!bMoving)
    {
        const FVector C=SnapWindowCentre(Pawn);
        if(FVector2D::Distance(FVector2D(C),FVector2D(GetActorLocation()))<=1.)return;
        // A move starts: list the tiles of the new window that are not already built. Tiles in both windows are never touched.
        GT_PERF_SCOPE(PerfVisMoveStart,"MudVisual.WindowMoveStart");
        PendingCentre=C;
        PendingMinTile=FIntPoint(FMath::RoundToInt((C.X-HalfSizeCm)/TileWidthCm),FMath::RoundToInt((C.Y-HalfSizeCm)/TileWidthCm));
        PendingTiles.Reset();
        for(int32 Y=0;Y<TilesPerSide;++Y)for(int32 X=0;X<TilesPerSide;++X)
            if(!TileSlot.Contains(PendingMinTile+FIntPoint(X,Y)))PendingTiles.Add(PendingMinTile+FIntPoint(X,Y));
        auto InNew=[&](FIntPoint T){return T.X>=PendingMinTile.X && T.X<PendingMinTile.X+TilesPerSide && T.Y>=PendingMinTile.Y && T.Y<PendingMinTile.Y+TilesPerSide;};
        // A jump of several tiles needs more spare components than the pool holds: reuse tiles of the old window that are not in the new one (their area stays empty until the flip).
        for(auto It=TileSlot.CreateIterator();It && FreeTiles.Num()<PendingTiles.Num();++It)
            if(!InNew(It.Key())){FreeTiles.Add(It.Value());It.RemoveCurrent();}
        PendingNext=0;BuildingSlot=-1;PerfVisMoveStart.Work=PendingTiles.Num();
        bMoving=true;
    }
    if(PendingNext<PendingTiles.Num())
    {
        // Entering tiles, nearest the pawn first, under the tick budget; a tile is atomic from its first height to its section update.
        for(;PendingNext<PendingTiles.Num();)
        {
            if(BuildingSlot<0)
            {
                int32 Best=PendingNext;double BestD=DBL_MAX;
                for(int32 I=PendingNext;I<PendingTiles.Num();++I)
                {
                    const double D=FVector2D::DistSquared(FVector2D((PendingTiles[I].X+.5)*TileWidthCm,(PendingTiles[I].Y+.5)*TileWidthCm),FVector2D(Pawn));
                    if(D<BestD){BestD=D;Best=I;}
                }
                PendingTiles.Swap(PendingNext,Best);
                BuildingTile=PendingTiles[PendingNext];BuildingSlot=FreeTiles.Pop();BuildingRow=0;
            }
            if(!BuildTileHeights(Deadline))return;
            FinishTile();
            TileSlot.Add(BuildingTile,BuildingSlot);BuildingSlot=-1;++PendingNext;
            if(PendingNext>=PendingTiles.Num() || TileClock()>=Deadline)return;   // the flip gets its own tick
        }
        return;
    }
    // Every tile of the new window is built: flip. The window moves, the material is re-bound, and the old window tiles that are left become spare (the material window test masks them until they are reused).
    GT_PERF_SCOPE(PerfVisFlip,"MudVisual.WindowFlip");
    SetActorLocation(PendingCentre);BindGridWindow();
    for(auto It=TileSlot.CreateIterator();It;++It)
        if(It.Key().X<PendingMinTile.X || It.Key().X>=PendingMinTile.X+TilesPerSide || It.Key().Y<PendingMinTile.Y || It.Key().Y>=PendingMinTile.Y+TilesPerSide)
        {FreeTiles.Add(It.Value());It.RemoveCurrent();}
    WindowMinTile=PendingMinTile;bMoving=false;bFlippedThisTick=true;
}

FString AGTMudRunnerVisual::GetResearchReport() const
{
    int32 Sections=0;for(const auto& C:TreadSections)if(C)Sections+=C->GetNumSections();
    return FString::Printf(TEXT("visual_spacing_cm=12.5 water_shader_steps=%d water_state_side=%d wave_side=%d cadence_adapter_hz=30 tread_segments=%d tread_sections=%d"),WaterSteps,
        StateTargets.Num()?StateTargets[0]->SizeX:0,Waves?Waves->SizeX:0,TrackSegments.Num(),Sections);
}

void AGTMudRunnerVisual::UpdateDetails(float Dt)
{
    if(!TrackDynamic || !Surface || !Surface->Landscape)return;
    GT_PERF_SCOPE(PerfVisDetails,"MudVisual.UpdateDetails");
    auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);
    if(TrackPawn.Get()!=Pawn){TrackPawn=Pawn;TrackLast.Reset();TrackPhase.Reset();TrackContact.Reset();}
    const auto* Traction=Pawn?Pawn->FindComponentByClass<UGTTractionComponent>():nullptr;
    const auto* Move=Pawn?Pawn->FindComponentByClass<UChaosWheeledVehicleMovementComponent>():nullptr;
    constexpr int32 SegmentsPerSection=256;
    TSet<int32> DirtySections;
    if(bTracksDirty)for(int32 I=0;I<TrackSegments.Num();I+=SegmentsPerSection)DirtySections.Add(I/SegmentsPerSection);
    bTracksDirty=false;
    if(Traction && Move)
    {
        const int32 N=Traction->Wheels.Num();TrackLast.SetNum(N);TrackPhase.SetNum(N);TrackContact.SetNum(N);
        for(int32 I=0;I<N;++I)
        {
            const auto& W=Traction->Wheels[I];const FVector P=W.ContactPoint;
            const float Width=Move->Wheels.IsValidIndex(I)&&Move->Wheels[I]?Move->Wheels[I]->WheelWidth:25.f;
            const float Distance=FVector2D::Distance(FVector2D(P),FVector2D(TrackLast[I]));
            if(!W.bInContact || !TrackContact[I] || Distance>200)
            {TrackLast[I]=P;TrackContact[I]=W.bInContact;continue;}
            if(Distance<5)continue;
            const auto S=Surface->SampleSurface(FVector2D(P));
            if(S.SinkageCapCm>0)
            {
                // World ribbons replace the native screen-depth projector. Texture phase
                // follows travelled distance; source alpha/height/slip equations live in the material.
                const int32 Steps=FMath::Clamp(FMath::CeilToInt(Distance/12.5f),1,16);
                for(int32 J=0;J<Steps;++J)
                {
                    FTrackSegment Seg;Seg.A=FMath::Lerp(TrackLast[I],P,double(J)/Steps);Seg.B=FMath::Lerp(TrackLast[I],P,double(J+1)/Steps);
                    Seg.Heading=W.TyreHeading.GetSafeNormal();Seg.Width=Width;Seg.Phase=TrackPhase[I];
                    Seg.Strength=FMath::Clamp(S.Softness,.2f,1.f);Seg.Slip=FMath::Clamp(FMath::Abs(W.SlipMagnitude)/FMath::Max(100.f,FMath::Abs(W.TreadCmPerS)),0.f,1.f);
                    TrackPhase[I]+=Distance/Steps/FMath::Max(Width,1.f);
                    if(TrackSegments.Num()<4096){DirtySections.Add(TrackSegments.Num()/SegmentsPerSection);TrackSegments.Add(Seg);TrackMeshes.AddDefaulted();}
                    else{DirtySections.Add(NextTrack/SegmentsPerSection);TrackSegments[NextTrack]=Seg;TrackMeshes[NextTrack]=FTrackMesh();NextTrack=(NextTrack+1)%4096;}
                }
            }
            TrackLast[I]=P;
        }
    }
    // Each section owns a separate component. ProceduralMesh CreateMeshSection
    // recreates its ENTIRE scene proxy, including untouched sections; keeping
    // all sixteen in one component made render uploads grow with track history.
    {
    GT_PERF_SCOPE(PerfVisTracks,"MudVisual.TrackSections");PerfVisTracks.Work=DirtySections.Num();
    for(int32 Section:DirtySections)
    {
        TArray<FVector> V,N;TArray<FVector2D> UV;TArray<int32> Indices;TArray<FLinearColor>C;TArray<FProcMeshTangent>T;
        for(int32 Segment=Section*SegmentsPerSection;Segment<FMath::Min((Section+1)*SegmentsPerSection,TrackSegments.Num());++Segment)
        {
            const auto& S=TrackSegments[Segment];
            FTrackMesh& M=TrackMeshes[Segment];
            if(!M.bValid)
            {
            const FVector Side(-S.Heading.Y,S.Heading.X,0);
            const float Length=FVector2D::Distance(FVector2D(S.A),FVector2D(S.B));
            TArray<FTreadClipVertex> Rectangle;
            FVector2D Min(DBL_MAX,DBL_MAX),Max(-DBL_MAX,-DBL_MAX);
            for(int32 J : {0,1,3,2})
            {
                const FVector2D P((J<2?S.A:S.B)+Side*((J%2?1:-1)*S.Width*.5f));
                Rectangle.Add({P,FVector2D(S.Phase+(J<2?0:Length/FMath::Max(S.Width,1.f)),J%2)});
                Min.X=FMath::Min(Min.X,P.X);Min.Y=FMath::Min(Min.Y,P.Y);
                Max.X=FMath::Max(Max.X,P.X);Max.Y=FMath::Max(Max.Y,P.Y);
            }
            // Clip each ribbon against the exact 12.5-cm visual triangles. The
            // material interpolates their displaced corners, avoiding buried
            // strips when independent vertex samples disagree across a fold.
            for(int32 Y=FMath::FloorToInt(Min.Y/12.5);Y<=FMath::FloorToInt(Max.Y/12.5);++Y)
            for(int32 X=FMath::FloorToInt(Min.X/12.5);X<=FMath::FloorToInt(Max.X/12.5);++X)
            for(int32 Upper=0;Upper<2;++Upper)
            {
                const FVector2D O(X*12.5,Y*12.5);
                const FVector2D A=O+FVector2D(Upper?12.5:0,0),B=O+FVector2D(12.5,Upper?12.5:0),D=O+FVector2D(0,12.5);
                auto Poly=ClipTread(ClipTread(ClipTread(Rectangle,A,B),B,D),D,A);
                if(Poly.Num()<3)continue;
                const int32 Base=M.V.Num();
                for(const auto& Q:Poly)
                {
                    FVector P(Q.P,0);FVector Query=P;
                    Query.X=FMath::Clamp(Query.X,Surface->PaintOriginCm.X,Surface->PaintOriginCm.X+Surface->PaintSizeCm-.01);
                    Query.Y=FMath::Clamp(Query.Y,Surface->PaintOriginCm.Y,Surface->PaintOriginCm.Y+Surface->PaintSizeCm-.01);
                    const auto H=Surface->GroundHeightAt(Query);
                    P.Z=(H.IsSet()?H.GetValue():0)+.15f;
                    M.V.Add(P);M.UV.Add(Q.UV);
                }
                for(int32 J=1;J+1<Poly.Num();++J)M.Idx.Append({Base,Base+J,Base+J+1});
            }
            M.bValid=true;
            }
            // The section is the concatenation of its segments cached pieces.
            const int32 Base=V.Num();
            V.Append(M.V);UV.Append(M.UV);
            for(int32 K=0;K<M.V.Num();++K){N.Add(FVector::UpVector);C.Add(FLinearColor(S.Strength,S.Slip,S.Width*.01f,1));T.Add(FProcMeshTangent(FVector(S.Heading,0),false));}
            for(const int32 K:M.Idx)Indices.Add(Base+K);
        }
        {
            GT_PERF_SCOPE(PerfVisTrackCreate,"MudVisual.TrackSections.Create");PerfVisTrackCreate.Work=V.Num();
            if(TreadSections.Num()<=Section)TreadSections.SetNum(Section+1);
            if(!TreadSections[Section])
            {
                UProceduralMeshComponent* Component=Section==0 ? Tracks.Get() : NewObject<UProceduralMeshComponent>(this,*FString::Printf(TEXT("NativeTreadSection_%d"),Section));
                if(Section!=0)
                {
                    Component->SetupAttachment(Tracks);Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                    Component->SetCastShadow(false);Component->SetBoundsScale(1.1f);
                    Component->SetUsingAbsoluteLocation(true);Component->SetUsingAbsoluteRotation(true);Component->SetUsingAbsoluteScale(true);
                    Component->SetWorldTransform(FTransform::Identity);Component->RegisterComponent();
                }
                Component->SetMaterial(0,TrackDynamic);TreadSections[Section]=Component;
            }
            TreadSections[Section]->CreateMeshSection_LinearColor(0,V,Indices,N,UV,C,T,false);
        }
    }
    }
    // Host placement adapter: source plant roots follow the same changed surface.
    DetailCarry+=Dt;if(DetailCarry<.25f)return;DetailCarry=0;
    GT_PERF_SCOPE(PerfVisClod,"MudVisual.ClodSweep");
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        ++PerfVisClod.Work;
        TArray<UInstancedStaticMeshComponent*> Components;It->GetComponents(Components);
        for(auto* C:Components) if(C->ComponentHasTag(TEXT("NativeMudClod")))
        {
            const bool Large=C->GetStaticMesh()&&C->GetStaticMesh()->GetName().EndsWith(TEXT("_b"));
            bool bChanged=false;
            for(int32 I=0;I<C->GetInstanceCount();++I)
            {
                FTransform X;C->GetInstanceTransform(I,X,true);FVector P=X.GetLocation();
                const auto Sample=Surface->SampleSurface(FVector2D(P));
                if(!Sample.bAuthored)continue;
                const auto H=Surface->GroundHeightAt(P);
                const double Z=(H.IsSet()?H.GetValue():0)+Sample.SurfaceDeltaCm+(Large?1.8f:2.4f);
                if(P.Z==Z)continue;
                P.Z=Z;X.SetLocation(P);C->UpdateInstanceTransform(I,X,true,false,true);bChanged=true;
            }
            if(bChanged)C->MarkRenderInstancesDirty();
        }
    }
}

void AGTMudRunnerVisual::AddReviewTread(FVector Start,FVector End,float WidthCm,float Slip,float Phase)
{
    const FVector2D Direction=FVector2D(End-Start).GetSafeNormal();
    const float Length=FVector2D(End-Start).Size();
    if(Direction.IsNearlyZero() || Length>2000 || WidthCm<1 || WidthCm>200)return;
    const int32 N=FMath::CeilToInt(Length/12.5f);
    for(int32 I=0;I<N;++I)
    {
        FTrackSegment S;S.A=FMath::Lerp(Start,End,double(I)/N);S.B=FMath::Lerp(Start,End,double(I+1)/N);
        S.Heading=Direction;S.Width=WidthCm;S.Phase=Phase+Length*I/N/WidthCm;S.Strength=1;S.Slip=FMath::Clamp(Slip,0.f,1.f);
        if(TrackSegments.Num()<4096){TrackSegments.Add(S);TrackMeshes.AddDefaulted();}else{TrackSegments[NextTrack]=S;TrackMeshes[NextTrack]=FTrackMesh();NextTrack=(NextTrack+1)%4096;}
    }
    bTracksDirty=true;
}
UTextureRenderTarget2D* AGTMudRunnerVisual::GetResearchWaterState() const
{
    return StateTargets.IsValidIndex(Previous)?StateTargets[Previous].Get():nullptr;
}
UTextureRenderTarget2D* AGTMudRunnerVisual::GetResearchWaterSediment() const
{
    return SedimentTargets.IsValidIndex(Previous)?SedimentTargets[Previous].Get():nullptr;
}
