#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTProceduralGround.generated.h"

class USplineComponent;
class UBoxComponent;
class ALandscape;
class AGTLandscapeSurface;
class UTexture2D;
class UStaticMesh;
class UMaterialInterface;
class AGTProceduralGround;
class AGTRoadReliefTile;
class UGTWaterDomain;
class AGTRoadWaterMesh;

/** Metres along the reconstructed road. Host controls generate the independent
 * relief/soil/water layers found in Island; not native procedural presets. */
USTRUCT(BlueprintType)
struct FGTRoadCondition
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FString Name="Muddy stretch";
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0")) float StartMetres=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0")) float EndMetres=40;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="1")) float BlendMetres=5;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="100")) float MudDepthCm=25;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="70")) float RutDepthCm=20;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="1")) float Wetness=.8f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="1")) float Firmness=.1f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="1")) float GrassCover=0;
    /** Maximum fill above the lowest bed, limited by the basin's spill point. Zero is dry. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="40")) float WaterFillCm=0;
    /** Broad bog hollow, independent of wheel ruts and yielding soil depth. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="100")) float BasinDepthCm=0;
    /** Additional traffic lines split/merge within the road width. Host authoring, not native constants. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="300")) float TrackSpreadCm=0;
    /** Blend narrow wheel channels into broad broken, worked soil. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="1")) float Churn=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="1")) float CrossingTracks=0;
    /** Irregular centimetre-scale crowns and hollows, separate from sinkable depth. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="20")) float BreakupCm=0;
};

/** Editable control polygon. Generated centreline uses recovered natural cubics,
 * not Unreal's Hermite interpolation. Point scale Y controls local width. */
UCLASS()
class GRANDTOUREDITOR_API AGTProceduralRoad : public AActor
{
    GENERATED_BODY()
public:
    AGTProceduralRoad();
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Conditions") TArray<FGTRoadCondition> Conditions;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Conditions") int32 DetailSeed=71;
    UFUNCTION(CallInEditor,BlueprintCallable,Category="Road|Conditions") void AddExampleConditions();
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Road") TObjectPtr<USplineComponent> ControlPoints;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road") TObjectPtr<AGTProceduralGround> Author;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road",meta=(ClampMin="200",ClampMax="2000")) float WidthCm=800;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road",meta=(ClampMin="0",ClampMax="100")) float BedDepthCm=12;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road",meta=(ClampMin="0",ClampMax="50")) float MudDepthCm=18;
    /** Compacted road: no yielding layer or authored ruts/bogs. Does not change vehicle tuning. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road") bool bFirmGravel=false;
    /** Physical, nondeforming surface undulations; zero preserves existing roads. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Fine relief",meta=(ClampMin="0",ClampMax="6")) float FirmRoughnessCm=0;
    /** Full length of the distance-weighted elevation filter, metres. Zero preserves the authored profile. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road",meta=(ClampMin="0",ClampMax="40")) float ProfileSmoothingMetres=0;
    /** Retain the legacy geometric profile at an established building/junction; soil remains firm. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road",meta=(ClampMin="0")) float FirmProfileEndPreserveMetres=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road",meta=(ClampMin="0",ClampMax="200")) float FirmMaximumCutFillCm=120;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road",meta=(ClampMin="0",ClampMax="1")) float Wetness=.45f;
    /** Host vegetation masks; physical mud remains independent of visual cover. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Cover",meta=(ClampMin="0",ClampMax="1")) float CentreGrassCover=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Cover",meta=(ClampMin="0",ClampMax="1")) float VergeGrassCover=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road",meta=(ClampMin="0",ClampMax="200")) float MaximumCutFillCm=120;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Fine relief") bool bApplyRelief=true;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Fine relief") TObjectPtr<UTexture2D> ReliefTexture;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Fine relief",meta=(ClampMin="100",ClampMax="2000")) float ReliefDefaultWidthCm=700;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Fine relief",meta=(ClampMin="0.1",ClampMax="8")) float ReliefDiffuseAspect=2;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Road|Fine relief",meta=(ClampMin="0",ClampMax="2")) float ReliefStrength=1;
    UFUNCTION(CallInEditor,BlueprintCallable,Category="Road") void Rebuild();
    UFUNCTION(CallInEditor,BlueprintCallable,Category="Road") void ProjectPointsToBase();
};

UENUM(BlueprintType)
enum class EGTGroundRegionKind : uint8 { Woodland, WetGround, Clearing, Exclusion };

/** Move/scale/rotate the box in the viewport. The footprint fades elliptically;
 * broken edges and terrain-dependent moisture are host authoring rules. */
UCLASS()
class GRANDTOUREDITOR_API AGTProceduralGroundRegion : public AActor
{
    GENERATED_BODY()
public:
    AGTProceduralGroundRegion();
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Ground region") TObjectPtr<UBoxComponent> Bounds;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Ground region") TObjectPtr<AGTProceduralGround> Author;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Ground region") EGTGroundRegionKind Kind=EGTGroundRegionKind::Woodland;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Ground region",meta=(ClampMin="0",ClampMax="1")) float Strength=1;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Ground region",meta=(ClampMin="0",ClampMax="1")) float GrassCover=.8f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Ground region",meta=(ClampMin="0",ClampMax="50")) float MudDepthCm=28;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Ground region",meta=(ClampMin="0",ClampMax="1")) float Wetness=.85f;
    UFUNCTION(CallInEditor,BlueprintCallable,Category="Ground region") void Rebuild();
};

UENUM(BlueprintType)
enum class EGTScatterHabitat : uint8 { Woodland, OpenGround, Verge, Road };

/** Native ordinary-plant eligibility and size fields. Empty rule array retains
 * the legacy shared size limits. One entry per mesh when used. */
USTRUCT(BlueprintType)
struct FGTGroundPlantVariant
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float MinMapScale=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float MaxMapScale=1;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float MinSize=.7f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float MaxSize=1.3f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float ScaleRandom=.3f;
};

USTRUCT(BlueprintType)
struct FGTGroundScatterRule
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FName Name="Shrubs";
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TArray<TObjectPtr<UStaticMesh>> Meshes;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TArray<FGTGroundPlantVariant> Variants;
    /** Optional per-slot overrides, shared by variants with the same slot layout. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TArray<TObjectPtr<UMaterialInterface>> MaterialOverrides;
    /** Host mesh-size adapter. Zero uses the mesh's imported size. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="5000")) float MeshHeightCm=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="4",ClampMax="800")) int32 CandidateBudget=26;
    /** Separate generated density/scale channels, replacing hand-painted native maps. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) EGTScatterHabitat Habitat=EGTScatterHabitat::Woodland;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) int32 SeedOffset=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="100",ClampMax="20000")) float ClusterScaleCm=1800;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="1")) float ClusterStrength=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="1",ClampMax="4")) float ScaleMapContrast=1;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="100",ClampMax="5000")) float VergeWidthCm=1200;
    /** Horizontal size adapter for twigs; mutually exclusive with MeshHeightCm. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="5000")) float MeshFootprintCm=0;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bAlignToGround=false;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bCastShadow=true;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="1")) float Density=.35f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0.01",ClampMax="0.99")) float MinMapDensity=.01f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0.25",ClampMax="4")) float MinimumScale=.7f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0.25",ClampMax="4")) float MaximumScale=1.3f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="2")) float ScaleRandom=.3f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="500")) float RoadClearanceCm=200;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="60")) float MaximumSlopeDegrees=35;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bSolid=false;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bRoadDebris=false;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="1000",ClampMax="100000")) float CullDistanceCm=22000;
};

USTRUCT()
struct FGTGeneratedGroundCell
{
    GENERATED_BODY()
    UPROPERTY() FIntPoint Key=FIntPoint::ZeroValue;
    UPROPERTY() uint32 Signature=0;
    UPROPERTY() TObjectPtr<AActor> Output;
    UPROPERTY() int32 Instances=0;
};

/** Explicit, reversible editor authoring. Only its captured landscape/mask assets
 * and owned output actors are changed; it never imports native STG placements. */
UCLASS()
class GRANDTOUREDITOR_API AGTProceduralGround : public AActor
{
    GENERATED_BODY()
public:
    AGTProceduralGround();
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring|Road water") TObjectPtr<UMaterialInterface> RoadWaterMaterial;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") int32 RoadPoolWetSamples=0;
    UPROPERTY() TObjectPtr<UGTWaterDomain> BaseWaterDomain;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") TObjectPtr<UGTWaterDomain> GeneratedWaterDomain;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") TObjectPtr<AGTRoadWaterMesh> RoadWaterMesh;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring") TObjectPtr<UBoxComponent> GenerationBounds;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring") TObjectPtr<ALandscape> Landscape;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring") TObjectPtr<AGTLandscapeSurface> Surface;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring") int32 Seed=962;
    /** Opt-in large map road corridors. Scatter/regions remain bounded; all fine-mesh and water budgets still apply. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring") bool bAllowLargeSparseRoadBounds=false;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring") TArray<FGTGroundScatterRule> ScatterRules;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring|Fine relief") TObjectPtr<UMaterialInterface> ReliefMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring|Fine relief",meta=(ClampMin="12.5",ClampMax="50")) float ReliefSpacingCm=25;
    /** Clearance beneath overlays. Keep 400 for deformable roads; fixed gravel can use a shallow recess. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring|Fine relief",meta=(ClampMin="0",ClampMax="400")) float LandscapeRecessDepthCm=400;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") int32 ReliefTriangles=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") int32 ChangedReliefTiles=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") int32 RetainedReliefTiles=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") TMap<FIntPoint,TObjectPtr<AGTRoadReliefTile>> ReliefTiles;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring|Owned assets") FString OutputAssetRoot="/Game/GrandTour/ArtTests/ProceduralGround/";
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring|Owned assets") TObjectPtr<UTexture2D> PaintTexture;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring|Owned assets") TObjectPtr<UTexture2D> StyleTexture;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Authoring|Owned assets") TObjectPtr<UTexture2D> MacroTexture;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") FString LastMessage;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") bool bHasBase=false;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") int32 ChangedCells=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") int32 RetainedCells=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") int32 InstanceCount=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Authoring|Status") FString OutputDigest;
    UFUNCTION(CallInEditor,BlueprintCallable,Category="Authoring") bool CaptureBase();
    UFUNCTION(CallInEditor,BlueprintCallable,Category="Authoring") bool Rebuild();
    UFUNCTION(CallInEditor,BlueprintCallable,Category="Authoring") bool ClearGenerated();
    UFUNCTION(CallInEditor,BlueprintCallable,Category="Authoring") void ShowGeneratedRoads();
    UFUNCTION(BlueprintPure,Category="Authoring") float BaseHeightAt(FVector2D XY) const;
    UFUNCTION(BlueprintPure,Category="Authoring") FString CurrentTerrainDigest() const;
    UFUNCTION(BlueprintPure,Category="Authoring") FString BaseTerrainDigest() const;
    UFUNCTION(BlueprintPure,Category="Authoring") int32 GeneratedCellCount() const { return GeneratedCells.Num(); }
    UPROPERTY() TArray<FGTGeneratedGroundCell> GeneratedCells;
private:
    UPROPERTY() TArray<uint16> BaseHeights;
    UPROPERTY() FIntRect HeightBounds;
    UPROPERTY() FTransform BaseTransform;
    UPROPERTY() TObjectPtr<ALandscape> CapturedLandscape;
    UPROPERTY() TArray<uint8> BasePaint;
    UPROPERTY() TArray<uint8> BaseStyle;
    UPROPERTY() TArray<uint8> BaseMacro;
    UPROPERTY() int32 AtlasSize=0;
    UPROPERTY() FVector2D AtlasOrigin;
    UPROPERTY() float AtlasSpan=0;
    UPROPERTY() TArray<FString> CapturedTexturePaths;
    UPROPERTY() FBox2D PreviousBounds=FBox2D(ForceInit);
    bool Validate(bool RequireBase);
    bool Report(const FString& Message,bool Success);
    void WriteTextures(const TArray<uint8>& Paint,const TArray<uint8>& Style,const TArray<uint8>& Macro);
};
