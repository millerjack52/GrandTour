#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTRoadReliefTile.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Core/GTPerfProbe.h"

#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Terrain/GTMudRestMap.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "LandscapeProxy.h"
#include "LandscapeNaniteComponent.h"
#include "LandscapeComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Math/Float16Color.h"
#include "Misc/App.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "Terrain/GTTrackPaintSubsystem.h"
#include "Terrain/GTMudRunnerSubstance.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTVehicleTuningComponent.h"
#include "Terrain/GTLandscapeWheelEffects.h"
#include "Terrain/GTWaterSheet.h"

namespace GTLandscapeSurface
{
    TAutoConsoleVariable<int32> Quality(TEXT("gt.LandscapeMud.Quality"),1,
        TEXT("Mud cosmetics: 0 low, 1 balanced (default), 2 high. Physics is unchanged."),ECVF_Scalability);
    TAutoConsoleVariable<float> UploadBudget(TEXT("gt.LandscapeMud.UploadBudgetMs"),1.5f,
        TEXT("Soft game-thread packing budget per frame at balanced quality; low x0.5, high x2."));
    UTexture2D* MakeTexture()
    {
        constexpr int32 N = FGTLandscapeSurfaceField::WindowCells;
        TArray64<uint8> Zeroes;
        Zeroes.SetNumZeroed(int64(N) * N * sizeof(FFloat16Color));
        auto* T = UTexture2D::CreateTransient(N, N, PF_FloatRGBA, NAME_None, Zeroes);
        T->SRGB = false; T->Filter = TF_Bilinear;
        T->AddressX = TA_Clamp; T->AddressY = TA_Clamp;
        T->NeverStream = true; T->UpdateResource();
        return T;
    }
    void Update(UTexture2D* Texture, FIntPoint Dest, TArray<FFloat16Color>* Data,
        TSharedPtr<FThreadSafeCounter,ESPMode::ThreadSafe> Pending)
    {
        constexpr uint32 N = FGTLandscapeSurfaceField::UploadBlockCells;
        auto* Region = new FUpdateTextureRegion2D(Dest.X, Dest.Y, 0, 0, N, N);
        Pending->Increment();
        Texture->UpdateTextureRegions(0, 1, Region, N * sizeof(FFloat16Color), sizeof(FFloat16Color),
            reinterpret_cast<uint8*>(Data->GetData()), [Data,Pending](uint8*, const FUpdateTextureRegion2D* R) { delete Data; delete R; Pending->Decrement(); });
    }
}

AGTLandscapeSurface::AGTLandscapeSurface()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostPhysics;
    CreateDefaultSubobject<UGTLandscapeWheelEffects>(TEXT("SurfaceWheelEffects"));
}

bool AGTLandscapeSurface::HasRoadReliefAt(FVector2D XY) const
{
    if(RoadTileSpanCm<=0)return false;
    const FVector2D Q=(XY-RoadTileOrigin)/RoadTileSpanCm;
    const auto* Tile=RoadReliefTiles.Find(FIntPoint(FMath::FloorToInt(Q.X),FMath::FloorToInt(Q.Y)));
    return Tile&&IsValid(*Tile);
}
bool AGTLandscapeSurface::OwnsGroundActor(const AActor* Actor) const
{
    if(!Actor)return false;
    if(Actor==Landscape)return true;
    const auto* Tile=Cast<AGTRoadReliefTile>(Actor);
    return Tile && Tile->Surface==this;
}
TOptional<float> AGTLandscapeSurface::GroundHeightAt(FVector Position) const
{
    if(RoadTileSpanCm>0)
    {
        const FVector2D Q=(FVector2D(Position)-RoadTileOrigin)/RoadTileSpanCm;
        if(const auto* Tile=RoadReliefTiles.Find(FIntPoint(FMath::FloorToInt(Q.X),FMath::FloorToInt(Q.Y)));Tile&&IsValid(*Tile))return (*Tile)->HeightAt(FVector2D(Position));
    }
    return Landscape?Landscape->GetHeightAtLocation(Position):TOptional<float>();
}
FLinearColor AGTLandscapeSurface::PaintAt(FVector2D World) const
{
    if (PaintResolution < 2 || PaintSizeCm <= 0.f || PaintCells.Num() != PaintResolution * PaintResolution) return FLinearColor(0, -50, 0, 0);
    const FVector2D UV = (World - PaintOriginCm) / PaintSizeCm;
    if (UV.X < 0. || UV.Y < 0. || UV.X >= 1. || UV.Y >= 1.) return FLinearColor(0, -50, 0, 0);
    const FVector2D P = UV * PaintResolution - FVector2D(.5, .5);
    const int32 X = FMath::FloorToInt(P.X), Y = FMath::FloorToInt(P.Y);
    auto Read = [&](int32 A, int32 B) { return PaintCells[FMath::Clamp(B, 0, PaintResolution - 1) * PaintResolution + FMath::Clamp(A, 0, PaintResolution - 1)]; };
    FLinearColor Result=FMath::Lerp(FMath::Lerp(Read(X,Y), Read(X+1,Y), float(P.X-X)), FMath::Lerp(Read(X,Y+1), Read(X+1,Y+1), float(P.X-X)), float(P.Y-Y));
    if (bUseSoilShearResponse) Result.R=FMath::Clamp(Result.R*FMath::Clamp(LayerDepthScale,.1f,3.f),0.f,FMath::Clamp(MaximumLayerDepthCm,1.f,124.f));
    if(RoadTileSpanCm>0)
    {
        const FVector2D Q=(World-RoadTileOrigin)/RoadTileSpanCm;
        if(const auto* Tile=RoadReliefTiles.Find(FIntPoint(FMath::FloorToInt(Q.X),FMath::FloorToInt(Q.Y)));Tile&&IsValid(*Tile))
        {Result=(*Tile)->SoilAt(World,Result);Result.R=FMath::Clamp(Result.R,0.f,FMath::Clamp(MaximumLayerDepthCm,1.f,124.f));}
    }
    return Result;
}

void AGTLandscapeSurface::BeginPlay()
{
    Super::BeginPlay();
    Field.ShapeAt = [this](FVector2D P) { return ShapeAt(P); };
    Field.bNativeShaderUpdates=bUseNativeMudShaderUpdates;
    Field.bSliceDecay=true;   // PF1
    if(MaterialResolution>1)Field.NativeUpdateAt=[this](FVector2D P){return NativeMudAt(P);};
    // CL2: clay holds the cosmetic state of its ruts. Read by FGTLandscapeSurfaceField::Step on the game thread only (this actor's Tick).
    if(HasClay())Field.ClayAt=[this](FVector2D P){return ClayWeightAt(P);};
    Field.NativeBaseAlpha=[this](FVector2D P) { return FMath::Clamp(PaintAt(P).R/3.f,0.f,1.f); };
    if ((WorldRestResolution >= 2 && WorldRestResolution <= 1024 && WorldRestHeights.Num()==WorldRestResolution*WorldRestResolution)
        || (RestHeightResolution >= 2 && RestHeightResolution <= 512
        && MudRestHeights.Num() == RestHeightResolution*RestHeightResolution
        && ClayRestHeights.Num() == MudRestHeights.Num()))
        Field.AuthoredHeightAt = [this](FVector2D P, float Thickness) { return ScannedRestHeight(P, Thickness); };
    Field.Focus(FVector2D(GetActorLocation()), [this](FVector2D P) { return PaintAt(P); });
    if (!Landscape || !PaintTexture || PaintCells.Num() != PaintResolution * PaintResolution)
    {
        UE_LOG(LogTemp, Error, TEXT("Landscape surface prototype requires landscape and matching CPU/GPU paint"));
        SetActorTickEnabled(false); return;
    }
    if (FApp::CanEverRender())
    {
        FieldTexture = GTLandscapeSurface::MakeTexture();
        WaterTexture = GTLandscapeSurface::MakeTexture();
        StagingFieldTexture = GTLandscapeSurface::MakeTexture();
        StagingWaterTexture = GTLandscapeSurface::MakeTexture();
        // Landscape's parameter setters do not touch the Nanite components in UE 5.8.
        TArray<ULandscapeNaniteComponent*> Components;
        if(!bSeparateVisualMesh)Landscape->GetComponents(Components);
        bDisplacementScaleValid = !Components.IsEmpty();
        for (auto* C : Components)
        {
            // Texture-driven tessellation is invisible to Auto's WPO/transform tracking.
            // Cached shadows of the original flat ground otherwise black out new ruts.
            C->ShadowCacheInvalidationBehavior = GetVisualQuality()==2 ? EShadowCacheInvalidationBehavior::Always : EShadowCacheInvalidationBehavior::Rigid;
            C->MarkRenderStateDirty();
            const FVector Scale = C->GetComponentScale();
            const bool bUniform = Scale.X > 0. && FMath::IsNearlyEqual(Scale.X, Scale.Y, .001)
                && FMath::IsNearlyEqual(Scale.X, Scale.Z, .001);
            for (int32 I = 0; I < C->GetNumMaterials(); ++I)
                if (auto* MID = C->CreateDynamicMaterialInstance(I))
                {
                    NaniteMaterials.Add(MID);
                    const auto Displacement = MID->GetDisplacementScaling();
                    bDisplacementScaleValid &= bUniform && FMath::IsNearlyEqual(double(Displacement.Magnitude) * Scale.Z, 65., .01)
                        && FMath::IsNearlyEqual(Displacement.Center, 50.f / 65.f, .00001f);
                }
        }
        if (!bSeparateVisualMesh && NaniteMaterials.IsEmpty()) UE_LOG(LogTemp, Warning, TEXT("Landscape surface: no Nanite materials. Build the prototype landscape Nanite data before judging displacement."));
        if (!bSeparateVisualMesh && !bDisplacementScaleValid) UE_LOG(LogTemp, Error, TEXT("Landscape surface displacement DISABLED: require uniform positive Nanite component scale and magnitude * scale = 65 world cm. Repair the prototype material/landscape."));
        if (PuddleSurface && PuddleSurface->GetStaticMeshComponent())
            PuddleMaterial=PuddleSurface->GetStaticMeshComponent()->CreateDynamicMaterialInstance(0);
        Upload();
    }
}

FLinearColor AGTLandscapeSurface::ShapeAt(FVector2D World) const
{
    if(MaterialResolution>1)
    {
        const auto M=MaterialAt(World);
        return FLinearColor(M.B,FMath::Lerp(.5f,.12f,M.R),FMath::Lerp(1.f,.1f,FMath::Clamp(M.R+(bGrassIsVisualCover ? 0.f : M.G),0.f,1.f)),1.f);
    }
    for (const auto& R : MudRegions)
    {
        if (R.Contains(World))
            return FLinearColor(FMath::Clamp(R.Wetness,0.f,1.f), FMath::Clamp(R.Cohesion,0.f,1.f),
                FMath::Clamp(R.Relief,0.f,1.5f), FMath::Clamp(R.FragmentScale,.3f,2.f));
    }
    return FLinearColor(.35f,.5f,1.f,1.f);
}

float AGTLandscapeSurface::GrassAt(FVector2D World) const
{
    if(MaterialResolution>1)return MaterialAt(World).G;
    for (const auto& R : MudRegions)
        if (R.Contains(World))
            return FMath::Clamp(R.GrassCover,0.f,1.f);
    return 0.f;
}

float AGTLandscapeSurface::ScannedRestHeight(FVector2D World, float Thickness) const
{
    if(WorldRestResolution>=2 && WorldRestResolution<=1024 && WorldRestHeights.Num()==WorldRestResolution*WorldRestResolution)
    {
        const float Base=GTMudRestMap::Sample(WorldRestHeights,WorldRestResolution,PaintOriginCm,PaintSizeCm,World);
        const float Relief=GTMudRestMap::SamplePeriodic(MudReliefHeights,MudReliefResolution,MudReliefTileCm,World)
            *GTMudRestMap::ReliefWeight(MaterialAt(World),Thickness,bGrassIsVisualCover);
        return FMath::Clamp(Base+Relief,-FMath::Max(0.f,Thickness),FGTLandscapeSurfaceField::LipCapCm);
    }
    const int32 N=RestHeightResolution;
    auto Sample=[&](const TArray<float>& Data, float TileCm)
    {
        const FVector2D UV=World/TileCm;
        const FVector2D P((UV.X-FMath::FloorToDouble(UV.X))*N-.5,
                          (UV.Y-FMath::FloorToDouble(UV.Y))*N-.5);
        const int32 X=FMath::FloorToInt(P.X),Y=FMath::FloorToInt(P.Y);
        auto Read=[&](int32 A,int32 B) { return Data[((B+N)%N)*N+(A+N)%N]; };
        return FMath::Lerp(FMath::Lerp(Read(X,Y),Read(X+1,Y),float(P.X-X)),
                           FMath::Lerp(Read(X,Y+1),Read(X+1,Y+1),float(P.X-X)),float(P.Y-Y));
    };
    const FLinearColor Style=ShapeAt(World), Paint=PaintAt(World);
    const float Crust=(1.f-FMath::SmoothStep(.15f,.35f,Style.R))
        *(1.f-FMath::SmoothStep(.25f,.45f,Paint.A))*FMath::SmoothStep(20.f,28.f,Thickness);
    const float Mud=(Sample(MudRestHeights,260.f)-.62f)*45.f;
    const float Clay=(Sample(ClayRestHeights,180.f)-.55f)*8.f;
    float Height=FMath::Lerp(Mud,Clay,Crust)*Style.B;
    for(const auto& R : MudRegions)
    {
        const FVector2D D=(World-R.Centre).GetRotated(-R.YawDegrees);
        if(!R.Contains(World)) continue;
        const float Q=FMath::Square(D.X/FMath::Max(1.,R.HalfSize.X))+FMath::Square(D.Y/FMath::Max(1.,R.HalfSize.Y));
        Height-=FMath::Clamp(R.BasinDepthCm,0.f,12.f)*(1.f-FMath::SmoothStep(.45f,1.f,Q));
        break;
    }
    return FMath::Clamp(Height,-FMath::Min(Thickness,12.f),12.f)*FMath::SmoothStep(0.f,8.f,Thickness);
}

void AGTLandscapeSurface::EndPlay(const EEndPlayReason::Type Reason)
{
    NaniteMaterials.Reset();
    PuddleMaterial=nullptr;
    Super::EndPlay(Reason);
}

FGTLandscapeSurfaceSample AGTLandscapeSurface::SampleSurface(FVector2D XY) const
{
    FGTLandscapeSurfaceSample R;
    const FLinearColor P = PaintAt(XY);
    R.bAuthored = P.R > .01f || P.B > .01f;
    const auto C = Field.Sample(XY);
    const float Thickness = FMath::Clamp(P.R, 0.f, FMath::Clamp(MaximumLayerDepthCm,1.f,124.f));
    R.SinkageCapCm = Thickness;
    R.Softness = Thickness > 0.f ? FMath::Clamp(P.A, 0.f, 1.f) : 0.f;
    R.SinkageRateCmPerS = Thickness > 0.f ? FMath::Lerp(1.f, 8.f, R.Softness) : 0.f;
    R.SurfaceDeltaCm = Thickness > 0.f ? FMath::Clamp(C.DeltaCm, -Thickness, FGTLandscapeSurfaceField::LipCapCm) : 0.f;
    R.CompressionCm = FMath::Max(0.f,Field.RestHeight(XY,Thickness)-R.SurfaceDeltaCm);
    R.MudHeightAboveBaseCm = Thickness + R.SurfaceDeltaCm;
    R.WaterDepthCm = FGTLandscapeSurfaceField::WaterDepth(R.SurfaceDeltaCm, P);
    AGTWaterSheet* LocalWater=SimulatedWater;
    if(const auto* WaterSystem=GetWorld()->GetSubsystem<UGTWaterSubsystem>())
        if(auto* Covering=WaterSystem->SheetAt(XY))LocalWater=Covering;
    if (LocalWater)
    {
        R.WaterDepthCm = LocalWater->MudWaterDepthCmAt(XY);
        if(LocalWater->WaterDomain && Landscape && LocalWater->Covers(XY))
        {
            const auto H=GroundHeightAt(FVector(XY,0));
            if(H.IsSet())R.WaterDepthCm=FMath::Max(0.f,LocalWater->SurfaceCmAt(XY)-H.GetValue()-R.SurfaceDeltaCm);
        }
    }
    // XY coverage chooses the water force implementation even outside the Gaea
    // landscape (the lake backdrop). The wheel query below measures immersion
    // from its actual contact height, so a bridge still receives no water force.
    R.bAuthored |= bExtendWaterResponseToDomain && bUseNativeWaterResponse && SimulatedWater && SimulatedWater->Covers(XY);
    R.Wetness = ShapeAt(XY).R;
    R.Cohesion = ShapeAt(XY).G;
    R.GrassCover = GrassAt(XY);
    R.bGrassIsVisualCover = bGrassIsVisualCover;
    R.Disturbance = C.Track;
    R.bSoilShearResponse = bUseSoilShearResponse;
    R.bGranularResponse = bUseGranularResponse;
    for(const auto& Region:MudRegions)
        if(Region.Contains(XY))
        {R.bGranularResponse|=Region.bGranular;break;}
    if(MaterialResolution>1)R.bGranularResponse|=MaterialAt(XY).R>.5f;
    R.bNativeSubstanceResponse = NativeMudAt(XY);
    R.bNativeWaterResponse = bUseNativeWaterResponse || bUseNativeSubstanceResponse;
    if(bUseNativeSubstanceResponse && Thickness>.01f){R.NativeExtrudeCm=NativeQ(XY);R.NativeUpperCm=NativeUpper(XY);}
    // CL2 clay soil response. The weight (clay atlas R, or a mud region's ClayWeight) raises cohesion, turns the shear state on and the
    // granular law off over real clay, and gives the native substance its own friction / drag / push numbers: firm and grippy dry
    // (2.0, 16, 50), slick and softer wet (1.0, 14, 42), blended between wetness .45 and .6, and blended toward the mud defaults
    // (2.2, 10, 36) by the weight, so the edge of a clay corridor does not jump. Wet clay also scales the Chaos tyre grip down.
    const float Clay=ClayWeightAt(XY);
    R.ClayWeight=Clay;
    if(Clay>.05f)
    {
        R.Cohesion=FMath::Max(R.Cohesion,FMath::Lerp(.5f,.92f,Clay));
        if(Clay>.5f){R.bGranularResponse=false;R.bSoilShearResponse=true;}
        const float Wet=FMath::Clamp((R.Wetness-.45f)/.15f,0.f,1.f);
        R.NativeFriction=FMath::Lerp(R.NativeFriction,FMath::Lerp(2.0f,1.0f,Wet),Clay);
        R.NativeLinearResistance=FMath::Lerp(R.NativeLinearResistance,FMath::Lerp(16.f,14.f,Wet),Clay);
        R.NativePushResistance=FMath::Lerp(R.NativePushResistance,FMath::Lerp(50.f,42.f,Wet),Clay);
        R.ClayFrictionScale=FMath::Lerp(1.f,.55f,Clay*Wet);
    }
    R.BearingStrength = FMath::Clamp(BearingStrength,.35f,3.f);
    R.SettlementSpeedScale = bUseSoilShearResponse ? FMath::Clamp(SettlementSpeedScale,.25f,3.f) : 1.f;
    if (Thickness > .01f)
    {
        R.SurfaceTag = R.bGranularResponse ? TEXT("Sand") : R.GrassCover>.1f ? TEXT("Grass") : TEXT("Mud");
        R.FrictionScale = FMath::Lerp(.95f, .7f, R.Softness);
    }
    else if (P.B > .01f)
    {
        R.SurfaceTag = TEXT("Gravel");
        const auto* Paint = GetWorld() ? GetWorld()->GetSubsystem<UGTTrackPaintSubsystem>() : nullptr;
        const float Sweep = Paint ? FMath::Clamp(Paint->SampleDepth(FVector(XY, 0)), 0.f, 1.f) : 0.f;
        R.FrictionScale = FMath::Lerp(.9f, 1.f, Sweep);
    }
    R.FrictionScale*=R.ClayFrictionScale;
    return R;
}

float AGTLandscapeSurface::BedDeltaCm(FVector2D XY) const
{
    const float Thickness=FMath::Clamp(PaintAt(XY).R,0.f,FMath::Clamp(MaximumLayerDepthCm,1.f,124.f));
    return Thickness>0.f ? FMath::Clamp(Field.Sample(XY).DeltaCm,-Thickness,FGTLandscapeSurfaceField::LipCapCm) : 0.f;
}

float AGTLandscapeSurface::ContactHeightCm(FVector2D XY, bool bNative) const
{
    if(!bNative)return BedDeltaCm(XY);
    // Match the full sample, including its dry-edge sentinel. Physical native
    // height is separate from visible deformation and has no water dependency.
    const float Thickness=FMath::Clamp(PaintAt(XY).R,0.f,FMath::Clamp(MaximumLayerDepthCm,1.f,124.f));
    return bUseNativeSubstanceResponse && Thickness>.01f ? NativeUpper(XY)-5.f-NativeQ(XY) : -5.f;
}

void AGTLandscapeSurface::BindSimulatedWaterMaterial(UMaterialInstanceDynamic* Material)
{
    PuddleMaterial=Material;
    BindTextures();
}

void AGTLandscapeSurface::RegisterResearchMaterial(UMaterialInstanceDynamic* Material)
{
    if(Material && !ResearchMaterials.Contains(Material)) { ResearchMaterials.Add(Material);BindTextures(); }
}

FGTLandscapeSurfaceSample AGTLandscapeSurface::QuerySurface(UObject* Context, FVector2D XY)
{
    if (Context && Context->GetWorld())
        for (TActorIterator<AGTLandscapeSurface> It(Context->GetWorld()); It; ++It)
        {
            const auto S = It->SampleSurface(XY);
            if (S.bAuthored) return S;
        }
    return FGTLandscapeSurfaceSample();
}

void AGTLandscapeSurface::StampWheel(FVector2D Start, FVector2D End, FVector2D Heading, float Width, float Depth)
{
    Field.Stamp(Start, End, Heading, Width, Depth, [this](FVector2D P) { return PaintAt(P); });
}
void AGTLandscapeSurface::ApplyReviewSoilStroke(FVector2D Start,FVector2D End,float Width,float Depth,float Slip)
{
    if(!HasActorBegunPlay() || Width<1 || Width>200 || Depth<0 || Depth>MaximumLayerDepthCm || FVector2D::Distance(Start,End)>2000)return;
    const auto S=SampleSurface((Start+End)*.5);
    if(!S.bAuthored)return;
    Field.Focus((Start+End)*.5,[this](FVector2D P){return PaintAt(P);});
    // Split the fixture like real rolling contacts; the worker deliberately
    // rejects >200cm sweeps as teleports.
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(FVector2D::Distance(Start,End)/50.f));
    for(int32 I=0;I<Steps;++I)
    {
        const FVector2D A=FMath::Lerp(Start,End,double(I)/Steps),B=FMath::Lerp(Start,End,double(I+1)/Steps);
        const auto Local=SampleSurface((A+B)*.5);
        Field.StampWorked(A,B,(End-Start).GetSafeNormal(),Width,Depth,
            [this](FVector2D P){return PaintAt(P);},Field.RestHeight((A+B)*.5,Local.SinkageCapCm)-Depth,1.f,
            {bUseRutInteraction,FMath::Clamp(Slip,0.f,1.f),1.f,Local.bGranularResponse});
    }
}

FGTLandscapeSurfaceSample AGTLandscapeSurface::QueryWheelSurface(UObject* Context, FVector Contact, FVector2D Heading, float Width)
{
    UWorld* World=Context ? Context->GetWorld() : nullptr;
    if (!World) return {};
    for (TActorIterator<AGTLandscapeSurface> It(World);It;++It)
    {
        if (!It->bEnableWheelSupport || !It->Landscape || !It->HasActorBegunPlay()) continue;
        auto S=It->SampleSurface(FVector2D(Contact));
        if (!S.bAuthored || S.SinkageCapCm<=0.f) continue;
        // XY coverage alone must not apply mud to a bridge, car body or rock above it.
        FHitResult Hit;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(LandscapeMudSupport),false);
        if (const auto* Owner=Cast<AActor>(Context)) Params.AddIgnoredActor(Owner);
        const float Reach=FMath::Max(64.f,S.SinkageCapCm+16.f);
        if (!World->LineTraceSingleByChannel(Hit,Contact+FVector(0,0,Reach),Contact-FVector(0,0,64),ECC_Visibility,Params)
            || !It->OwnsGroundActor(Hit.GetActor()) || FMath::Abs(Hit.ImpactPoint.Z-Contact.Z)>FMath::Max(50.f,S.SinkageCapCm)) continue;
        Heading=Heading.GetSafeNormal();
        if (Heading.IsNearlyZero()) Heading=FVector2D(1,0);
        const FVector2D Side(-Heading.Y,Heading.X);
        // A tyre bridges sub-footprint cracks; average several support probes instead of
        // following each 6.25 cm texel. Broad shoulders and old ruts remain in the signal.
        float Height=S.SurfaceDeltaCm*2.f;
        float Rest=It->Field.RestHeight(FVector2D(Contact),S.SinkageCapCm)*2.f;
        for (const FVector2D Offset : {Heading*12.f,-Heading*12.f,Side*FMath::Clamp(Width*.3f,4.f,15.f),-Side*FMath::Clamp(Width*.3f,4.f,15.f)})
        {
            const FVector2D P=FVector2D(Contact)+Offset;
            const float Thickness=FMath::Clamp(It->PaintAt(P).R,0.f,FMath::Clamp(It->MaximumLayerDepthCm,1.f,124.f));
            Height+=It->BedDeltaCm(P);
            Rest+=It->Field.RestHeight(P,Thickness);
        }
        S.bWheelSupport=true;S.WheelSupportCm=Height/6.f;S.RestWheelSupportCm=Rest/6.f;
        return S;
    }
    // Water over firm terrain has no yielding mud support. Opted-in domains still
    // use the recovered wheel-water impulse, with bridge/rock height respected.
    for(TActorIterator<AGTLandscapeSurface> It(World);It;++It)
        if(It->bExtendWaterResponseToDomain && It->bUseNativeWaterResponse && It->SimulatedWater
            && It->SimulatedWater->Covers(FVector2D(Contact)))
        {
            const float Depth=It->SimulatedWater->SurfaceCmAt(FVector2D(Contact))-Contact.Z;
            if(Depth>.01f)
            {
                FGTLandscapeSurfaceSample Water;
                Water.bAuthored=true;Water.bNativeWaterResponse=true;Water.WaterDepthCm=Depth;
                Water.SurfaceTag=TEXT("Water");return Water;
            }
        }
    return {};
}

void AGTLandscapeSurface::ObserveWheels(float Dt)
{
    APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
    if (ObservedPawn != Pawn) { ObservedPawn = Pawn; LastContacts.Reset(); HadContact.Reset(); VisualDepthCm.Reset();NativeContactCarry.Reset(); }
    const auto* Traction = Pawn ? Pawn->FindComponentByClass<UGTTractionComponent>() : nullptr;
    const auto* Movement = Pawn ? Pawn->FindComponentByClass<UChaosWheeledVehicleMovementComponent>() : nullptr;
    const auto* Tuning = Pawn ? Pawn->FindComponentByClass<UGTVehicleTuningComponent>() : nullptr;
    if (!Traction || !Movement) return;
    const double ObserveStart=FPlatformTime::Seconds();
    const int32 N = Traction->Wheels.Num();
    LastContacts.SetNum(N); HadContact.SetNum(N); VisualDepthCm.SetNum(N);
    NativeContactCarry.SetNum(N);
    auto* Paint = GetWorld()->GetSubsystem<UGTTrackPaintSubsystem>();
    for (int32 I = 0; I < N; ++I)
    {
        const auto& W = Traction->Wheels[I];
        const FVector2D XY(W.ContactPoint);
        const bool bContinuous = HadContact[I] && FVector2D::Distance(LastContacts[I], XY) < 200.f;
        const FVector2D Start = bContinuous ? LastContacts[I] : XY;
        if (!W.bInContact) { HadContact[I] = false; VisualDepthCm[I] = 0.f;NativeContactCarry[I]=0; continue; }
        const float Width = Movement->Wheels.IsValidIndex(I) && Movement->Wheels[I] ? Movement->Wheels[I]->WheelWidth : 25.f;
        const FVector2D TyreHeading=bUseRutInteraction && Movement->UpdatedPrimitive && Movement->Wheels.IsValidIndex(I) && Movement->Wheels[I]
            ? FVector2D(Movement->UpdatedPrimitive->GetForwardVector()).GetSafeNormal().GetRotated(Movement->Wheels[I]->GetSteerAngle()) : W.TyreHeading;
        const auto S = SampleSurface(XY);
        if(S.bNativeSubstanceResponse && S.SinkageCapCm>0.f)
        {
            const float Radius=Movement->Wheels.IsValidIndex(I)&&Movement->Wheels[I]?Movement->Wheels[I]->WheelRadius:32.f;
            const float Speed=FVector2D::DotProduct(FVector2D(Pawn->GetVelocity()),TyreHeading)*.01f;
            const float P=GTMudRunnerSubstance::Excitation(Radius*.01,Width*.01,W.TreadCmPerS/FMath::Max(Radius,1.f),Speed,Movement->Mass/FMath::Max(N,1),.24);
            NativeContactCarry[I]+=Dt;
            while(NativeContactCarry[I]>=1.f/60.f){StampNativePhysical(XY,P);NativeContactCarry[I]-=1.f/60.f;}
        }
        const auto Support=bEnableWheelSupport && S.SinkageCapCm>0.f ? QueryWheelSurface(Pawn,W.ContactPoint,TyreHeading,Width) : FGTLandscapeSurfaceSample();
        if (bEnableWheelSupport && S.SinkageCapCm>0.f && !Support.bWheelSupport)
        {
            HadContact[I]=false;VisualDepthCm[I]=0.f;continue;
        }
        if (S.SinkageCapCm > 0.f)
        {
            const float Prior = bContinuous ? VisualDepthCm[I] : 0.f;
            // Static load settles once. Further excavation needs actual rolling or positive drive slip.
            const float Travel = bContinuous ? float(FVector2D::Distance(Start,XY)) : 0.f;
            const bool bTurning = FMath::Abs(W.TreadCmPerS)>10.f;
            const float Spin = bTurning && W.bSlipping ? FMath::Max(0.f,W.SlipMagnitude*FMath::Sign(W.TreadCmPerS)) : 0.f;
            const float Rolling=bTurning ? FMath::Clamp(Travel/FMath::Max(Dt,.001f)/80.f,0.f,1.f) : 0.f;
            const float Load=FMath::Clamp(W.Load/FMath::Max(1.f,Movement->Mass*980.f/N),0.f,1.6f);
            // Equilibrium under load, not a depth accumulator carried down the whole lane.
            // Firmed old tracks stop cutting; sustained positive spin works a few cm deeper.
            const float Settle=FMath::Lerp(.35f,Support.bWheelSupport ? 3.2f : 1.4f,S.Softness);
            const float Desired=FMath::Min(S.SinkageCapCm,(Settle+Rolling*FMath::Lerp(.5f,Support.bWheelSupport ? 6.f : 2.2f,S.Softness)
                +FMath::Clamp(Spin/220.f,0.f,1.f)*6.f*S.Softness)*Load*FMath::Lerp(1.f,.45f,bGrassIsVisualCover ? 0.f : S.GrassCover));
            // Leaving a soft pocket must not carry its larger cut target into firmer sod.
            VisualDepthCm[I]=FMath::FInterpConstantTo(FMath::Min(Prior,Desired),Desired,Dt,S.SinkageRateCmPerS);
            // Existing deeper hollows are followed, never counted as fresh excavation work.
            // Depth is a rest-relative target; old tracks need no additional cut at equilibrium.
            if (Support.bWheelSupport && Tuning && Tuning->GetCurrent().Wheels.IsValidIndex(I))
            {
                // Plastic flow and tyre support share one rest-relative equilibrium. Leave
                // some loaded penetration around the tyre instead of cutting all of it away.
                const float Settlement=Support.LoadedSettlementCm(Load);
                const float Plastic=S.bNativeSubstanceResponse ? 5.f+NativeQ(XY) : Settlement*FMath::Lerp(.6f,.78f,Rolling)
                    +FMath::Clamp(Spin/220.f,0.f,1.f)*2.f*S.Softness;
                const float Plane=(S.bNativeSubstanceResponse?NativeUpper(XY):Support.RestWheelSupportCm)-Plastic;
                const float CutRate=FMath::Lerp(12.f,40.f,S.Softness)*FMath::Sqrt(Load)*FMath::Lerp(1.f,.3f,bGrassIsVisualCover ? 0.f : S.GrassCover);
                // Allow crests above the footprint to collapse to the loaded plane. Low
                // hollows remain untouched; the mineral base bounds the pressure path.
                const float SignedMotion=bTurning ? W.TreadCmPerS : FVector2D::DotProduct(XY-Start,TyreHeading);
                const FVector2D WorkHeading=TyreHeading*(bUseRutInteraction && SignedMotion<0.f ? -1.f : 1.f);
                Field.StampWorked(Start,XY,WorkHeading,Width,Plastic+12.f,[this](FVector2D P) { return PaintAt(P); },Plane,CutRate*Dt,
                    {bUseRutInteraction,FMath::Clamp(Spin/220.f,0.f,1.f),Rolling,S.bGranularResponse});
            }
            else StampWheel(Start, XY, W.TyreHeading, Width, VisualDepthCm[I]);
        }
        else
        {
            VisualDepthCm[I] = 0.f;
            if (S.SurfaceTag == TEXT("Gravel") && Paint)
                Paint->AddWheelStamp(FVector(Start, W.ContactPoint.Z), W.ContactPoint, Width, .2f, Dt);
        }
        LastContacts[I] = XY; HadContact[I] = true;
    }
    const double ObserveMs=(FPlatformTime::Seconds()-ObserveStart)*1000;
    WheelObserveTotalMs+=ObserveMs;WheelObservePeakMs=FMath::Max(WheelObservePeakMs,ObserveMs);++WheelObserveCount;
}

void AGTLandscapeSurface::Tick(float Dt)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(LandscapeMud_Tick);
    Super::Tick(Dt);
    if (bFollowPlayer)
        if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0))
        {
            FVector2D Focus(Pawn->GetActorLocation());
            if(bClampFocusToPaint)
            {
                const double Inset=FMath::Min(1600.,PaintSizeCm*.5);
                Focus.X=FMath::Clamp(Focus.X,PaintOriginCm.X+Inset,PaintOriginCm.X+PaintSizeCm-Inset);
                Focus.Y=FMath::Clamp(Focus.Y,PaintOriginCm.Y+Inset,PaintOriginCm.Y+PaintSizeCm-Inset);
            }
            GT_PERF_SCOPE(PerfFocus,"LandscapeSurface.Focus");
            Field.Focus(Focus,[this](FVector2D P){return PaintAt(P);});
            {
                // PF1: the tiles one boundary crossing away are built ahead, a few rows per tick.
                GT_PERF_SCOPE(PerfPrefetch,"LandscapeSurface.Prefetch");
                Field.Prefetch(Focus,[this](FVector2D P){return PaintAt(P);},FPlatformTime::Seconds()+.0012);
            }
        }
    if (bObservePlayerWheels)
    {
        WheelObserveTime+=FMath::Clamp(Dt,0.f,.1f);
        // Swept footprints retain the travelled path at a bounded deformation rate.
        // Physics still samples support every step; visual quality never changes soil work.
        if(!bUseSoilShearResponse || WheelObserveTime>=1.f/30.f)
        {
            {GT_PERF_SCOPE(PerfObs,"LandscapeSurface.Observe");ObserveWheels(FMath::Min(WheelObserveTime,.1f));}
            WheelObserveTime=0.f;
        }
    }
    else WheelObserveTime=0.f;
    Field.Step(Dt);
    PumpLandscapeBind(FPlatformTime::Seconds()+.001);
    const int32 Quality=GetVisualQuality();
    if (AppliedQuality!=Quality) { AppliedQuality=Quality;BindTextures();ShadowTime=1.f;ShadowRevision=MAX_uint64; }
    UploadTime += Dt;
    const float Interval=Quality==0 ? .125f : Quality==1 ? 1.f/12.f : .05f;
    if (UploadTime>=Interval || RefreshCursor>=0 || UploadWindow!=Field.WindowTile)
    {
        if (UploadTime>=Interval) UploadTime=0;
        Upload();
    }
    ShadowTime+=Dt;
    if (bTexturesReady && ShadowTime>=(Quality==0 ? .5f : .25f) && ShadowRevision!=Field.GeometryRevision)
    {
        TArray<ULandscapeNaniteComponent*> Components;Landscape->GetComponents(Components);
        GT_PERF_SCOPE(PerfShadow,"LandscapeSurface.ShadowInvalidate");PerfShadow.Work=Components.Num();
        for (auto* C:Components)
        {
            C->ShadowCacheInvalidationBehavior=Quality==2 ? EShadowCacheInvalidationBehavior::Always : EShadowCacheInvalidationBehavior::Rigid;
            C->MarkRenderStateDirty();
        }
        ShadowRevision=Field.GeometryRevision;ShadowTime=0;
    }
}

int32 AGTLandscapeSurface::GetVisualQuality()
{
    return FMath::Clamp(GTLandscapeSurface::Quality.GetValueOnGameThread(),0,2);
}

void AGTLandscapeSurface::Upload()
{
    TRACE_CPUPROFILER_EVENT_SCOPE(LandscapeMud_Upload);
    if (!FieldTexture || !WaterTexture || !Landscape) return;
    GT_PERF_SCOPE(PerfUpload,"LandscapeSurface.Upload");
    const double Start=FPlatformTime::Seconds();
    const int32 Quality=GetVisualQuality();
    const int32 MaxBlocks=Quality==0 ? 8 : Quality==1 ? 16 : 32;
    const double BudgetMs=FMath::Clamp(GTLandscapeSurface::UploadBudget.GetValueOnGameThread(),.1f,8.f)*(Quality==0 ? .5 : Quality==1 ? 1. : 2.);
    constexpr int32 B=FGTLandscapeSurfaceField::UploadBlockCells;
    constexpr int32 Side=FGTLandscapeSurfaceField::BlocksPerSide;
    constexpr int32 PerTile=Side*Side, Total=9*PerTile;
    if (UploadWindow!=Field.WindowTile && !LandscapeBind.bActive) { UploadWindow=Field.WindowTile;RefreshCursor=0; }
    int32 Done=0;
    for (int32 Attempt=0;Attempt<Total*2 && Done<MaxBlocks;++Attempt)
    {
        // Backpressure: at most one quality-sized batch can wait on the render thread.
        if (PendingUploads->GetValue()>=MaxBlocks*2) break;
        if (Done>0 && (FPlatformTime::Seconds()-Start)*1000.>=BudgetMs) break;
        const bool Refresh=RefreshCursor>=0;
        const int32 Index=Refresh ? RefreshCursor++ : DirtyCursor;
        if (!Refresh) DirtyCursor=(DirtyCursor+1)%Total;
        const int32 TileIndex=Index/PerTile,Block=Index%PerTile;
        const FIntPoint TileOffset(TileIndex%3,TileIndex/3), BlockOffset(Block%Side,Block/Side);
        auto* Tile=Field.Tiles.Find(UploadWindow+TileOffset);
        const uint64 Bit=uint64(1)<<Block;
        // New tyre work gets first use of the budget; old wetness decay follows.
        if (!Refresh && Attempt<Total && (!Tile || !(Tile->ContactDirtyBlocks&Bit))) continue;
        if (Tile && (Refresh || (Tile->DirtyBlocks&Bit)))
        {
            const FIntPoint Dest=TileOffset*FGTLandscapeSurfaceField::TileCells+BlockOffset*B;
            const FIntPoint First=UploadWindow*FGTLandscapeSurfaceField::TileCells+Dest;
            auto* Data=new TArray<FFloat16Color>();auto* Water=new TArray<FFloat16Color>();
            Field.Pack(FIntRect(First,First+FIntPoint(B,B)),[this](FVector2D P) { return PaintAt(P); },
                [this](FVector2D P) { return FVector2f(ShapeAt(P).R,GrassAt(P)); },*Data,*Water);
            GTLandscapeSurface::Update(Refresh ? StagingFieldTexture.Get() : FieldTexture.Get(),Dest,Data,PendingUploads);
            GTLandscapeSurface::Update(Refresh ? StagingWaterTexture.Get() : WaterTexture.Get(),Dest,Water,PendingUploads);
            Tile->DirtyBlocks &= ~Bit;Tile->ContactDirtyBlocks &= ~Bit;UploadedCells+=B*B;++Done;
        }
        if (RefreshCursor==Total)
        {
            // Publish the new origin only after its entire texture has been queued. Render
            // commands preserve ordering; the previous window stays visible during the refresh.
            Swap(FieldTexture,StagingFieldTexture);Swap(WaterTexture,StagingWaterTexture);
            PublishedWindow=UploadWindow;RefreshCursor=-1;bTexturesReady=true;
            ShadowRevision=MAX_uint64;BindTextures(bBoundReady!=bTexturesReady);break;
        }
    }
    PerfUpload.Work=Done;
    PeakUploadMs=FMath::Max(PeakUploadMs,(FPlatformTime::Seconds()-Start)*1000.);
}

void AGTLandscapeSurface::BindTextures(bool bFull)
{
    if (!Landscape || !FieldTexture) return;
    GT_PERF_SCOPE(PerfBind,"LandscapeSurface.BindTextures");
    constexpr int32 N=FGTLandscapeSurfaceField::WindowCells;
    const FIntPoint First=PublishedWindow*FGTLandscapeSurfaceField::TileCells;
    const FLinearColor Window(float(First.X)*FGTLandscapeSurfaceField::CellCm, float(First.Y)*FGTLandscapeSurfaceField::CellCm, N*FGTLandscapeSurfaceField::CellCm, 1.f);
    const FLinearColor PaintWindow(PaintOriginCm.X, PaintOriginCm.Y, PaintSizeCm, 1.f);
    if (bFull)
    {
        // Everything at once (first bind, a quality change, a new research material): cancels a sliced pass in flight.
        LandscapeBind.bActive = false;
        Landscape->SetLandscapeMaterialTextureParameterValue(TEXT("GTLS_Field"), FieldTexture);
        Landscape->SetLandscapeMaterialTextureParameterValue(TEXT("GTLS_Water"), WaterTexture);
        Landscape->SetLandscapeMaterialVectorParameterValue(TEXT("GTLS_Window"), Window);
        Landscape->SetLandscapeMaterialTextureParameterValue(TEXT("GTLS_Paint"), PaintTexture);
        Landscape->SetLandscapeMaterialVectorParameterValue(TEXT("GTLS_PaintWindow"), PaintWindow);
        Landscape->SetLandscapeMaterialScalarParameterValue(TEXT("GTLS_Ready"), bTexturesReady ? 1.f : 0.f);
        Landscape->SetLandscapeMaterialScalarParameterValue(TEXT("GTLS_DepthScale"), bUseSoilShearResponse ? FMath::Clamp(LayerDepthScale,.1f,3.f) : 1.f);
        Landscape->SetLandscapeMaterialScalarParameterValue(TEXT("GTLS_POMEnabled"), GetVisualQuality()==0 ? 0.f : 1.f);
        if (!bDisplacementScaleValid) Landscape->SetLandscapeMaterialScalarParameterValue(TEXT("GTLS_DisplacementEnabled"), 0.f);
        bBoundReady = bTexturesReady;
    }
    else LandscapeBind = FLandscapeBind{true, 0, FieldTexture, WaterTexture, Window};
    TArray<UMaterialInstanceDynamic*,TInlineAllocator<8>> Materials;
    for (UMaterialInstanceDynamic* M : NaniteMaterials) Materials.Add(M);
    for (UMaterialInstanceDynamic* M : ResearchMaterials) Materials.Add(M);
    if(PuddleMaterial) Materials.Add(PuddleMaterial);
    for (UMaterialInstanceDynamic* M : Materials)
    {
        M->SetTextureParameterValue(TEXT("GTLS_Field"), FieldTexture);
        M->SetTextureParameterValue(TEXT("GTLS_Water"), WaterTexture);
        M->SetVectorParameterValue(TEXT("GTLS_Window"), Window);
        if (!bFull) continue;
        M->SetTextureParameterValue(TEXT("GTLS_Paint"), PaintTexture);
        M->SetVectorParameterValue(TEXT("GTLS_PaintWindow"), PaintWindow);
        M->SetScalarParameterValue(TEXT("GTLS_Ready"), bTexturesReady ? 1.f : 0.f);
        M->SetScalarParameterValue(TEXT("GTLS_DepthScale"), bUseSoilShearResponse ? FMath::Clamp(LayerDepthScale,.1f,3.f) : 1.f);
        M->SetScalarParameterValue(TEXT("GTLS_POMEnabled"), GetVisualQuality()==0 ? 0.f : 1.f);
        if (!bDisplacementScaleValid) M->SetScalarParameterValue(TEXT("GTLS_DisplacementEnabled"), 0.f);
    }
}

void AGTLandscapeSurface::PumpLandscapeBind(double Deadline)
{
    if (!LandscapeBind.bActive || !Landscape) return;
    GT_PERF_SCOPE(PerfBindSlice,"LandscapeSurface.BindSlice");
    const auto& Components = Landscape->LandscapeComponents;
    int32 Done = 0;
    for (; LandscapeBind.Cursor < Components.Num(); ++LandscapeBind.Cursor, ++Done)
    {
        if ((Done & 15) == 15 && FPlatformTime::Seconds() >= Deadline) break;
        const ULandscapeComponent* Component = Components[LandscapeBind.Cursor];
        if (!Component) continue;
        for (UMaterialInstanceDynamic* M : Component->MaterialInstancesDynamic)
            if (M)
            {
                M->SetTextureParameterValue(TEXT("GTLS_Field"), LandscapeBind.Field);
                M->SetTextureParameterValue(TEXT("GTLS_Water"), LandscapeBind.Water);
                M->SetVectorParameterValue(TEXT("GTLS_Window"), LandscapeBind.Window);
            }
    }
    PerfBindSlice.Work = Done;
    if (LandscapeBind.Cursor >= Components.Num()) LandscapeBind.bActive = false;
}

void AGTLandscapeSurface::ApplyReviewTracks()
{
    Field.Focus(FVector2D::ZeroVector, [this](FVector2D P) { return PaintAt(P); });
    for (int32 Pass = 0; Pass < 2; ++Pass)
        for (float X = -1200.f; X < 1200.f; X += 12.5f)
            for (float Y : {-85.f, 85.f}) StampWheel(FVector2D(X,Y), FVector2D(X+12.5f,Y), FVector2D(1,0), 28.f, Pass ? 18.f : 8.f);
    for (int32 I = 0; I < 120; ++I)
        StampWheel(FVector2D(0,85), FVector2D(0,85), FVector2D(1,0), 28.f, 50.f);
    Upload();
}

FString AGTLandscapeSurface::GetSurfaceReport() const
{
    return FString::Printf(TEXT("tiles=%d evictions=%d excavated_cm3=%.3f deposited_cm3=%.3f balance_cm3=%.6f nanite_materials=%d displacement_scale_valid=%d quality=%d decay_cells=%d uploaded_cells=%llu upload_peak_ms=%.3f upload_pending=%d textures_ready=%d observe_mean_ms=%.4f observe_peak_ms=%.4f native_shader=%d native_cells=%llu push_cells=%llu clay_atlas=%d clay_hold=%d"),
        Field.Tiles.Num(), Field.Evictions, Field.ExcavatedCm3, Field.DepositedCm3, Field.ExcavatedCm3-Field.DepositedCm3, NaniteMaterials.Num(), bDisplacementScaleValid,GetVisualQuality(),Field.LastDecayCells,UploadedCells,PeakUploadMs,PendingUploads->GetValue(),bTexturesReady,
        WheelObserveCount ? WheelObserveTotalMs/WheelObserveCount : 0.,WheelObservePeakMs,Field.bNativeShaderUpdates,Field.NativeUpdateCells,Field.NativePushCells,ClayResolution,Field.ClayAt ? 1 : 0);
}
