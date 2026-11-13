#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTMudRunnerVisual.generated.h"
class AGTLandscapeSurface;
class UProceduralMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UTextureRenderTarget2D;
class AGTWaterSheet;

/** Research fixture: native 12.5 cm visual grid, separate from collision. */
UCLASS()
class GRANDTOUR_API AGTMudRunnerVisual : public AActor
{
    GENERATED_BODY()
public:
    AGTMudRunnerVisual();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<AGTLandscapeSurface> Surface;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> Material;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float HalfSizeCm=3150;
    /** Regional overlay: its material and the landscape use complementary coverage. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bHideWholeLandscape=true;
    /** Bounded high-detail drawing over a full-size heightmap. Off keeps fixed study tiles. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bFollowPlayerGrid=false;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<AGTWaterSheet> WaterSheet;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> WaterSimulationMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> SedimentSimulationMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> WaveMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> TrackMaterial;
    UFUNCTION(BlueprintPure) FString GetResearchReport() const;
    UFUNCTION(BlueprintPure) UTextureRenderTarget2D* GetResearchWaterState() const;
    UFUNCTION(BlueprintPure) UTextureRenderTarget2D* GetResearchWaterSediment() const;
    /** Places a review footprint without moving the vehicle. Cleared with the level. */
    UFUNCTION(BlueprintCallable) void AddReviewTread(FVector Start,FVector End,float WidthCm=25.f,float Slip=0.f,float Phase=0.f);
private:
    UPROPERTY(Transient) TObjectPtr<UProceduralMeshComponent> Mesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Dynamic;
    UPROPERTY(Transient) TObjectPtr<UProceduralMeshComponent> Tracks;
    /** One component per 256-segment section: changing a ribbon must not recreate every older section's render buffers. */
    UPROPERTY(Transient) TArray<TObjectPtr<UProceduralMeshComponent>> TreadSections;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> TrackDynamic;
    struct FTrackSegment { FVector A,B; FVector2D Heading; float Width=25,Phase=0,Strength=0,Slip=0; };
    TArray<FTrackSegment> TrackSegments;
    /** PF1: the clipped ribbon geometry of one segment (world coordinates), computed once when the segment first needs drawing; a section rebuild concatenates the cached pieces instead of re-clipping and re-sampling the ground. Parallel to TrackSegments. */
    struct FTrackMesh { TArray<FVector> V; TArray<FVector2D> UV; TArray<int32> Idx; bool bValid=false; };
    TArray<FTrackMesh> TrackMeshes;
    TArray<FVector> TrackLast;
    TArray<float> TrackPhase;
    TArray<bool> TrackContact;
    TWeakObjectPtr<APawn> TrackPawn;
    int32 NextTrack=0;
    bool bTracksDirty=false;
    float DetailCarry=0;
    void UpdateDetails(float Dt);
    void BuildGrid();
    void BindGridWindow();
    /** PF1: the follow-player grid as a pool of 800 cm world-anchored tiles (65 x 65 vertices at 12.5 cm) instead of one 148k-vertex mesh rebuilt on every 8 m window move. A move builds only the tiles that enter the
     * window (heights under a per-tick time budget, one UpdateMeshSection per tile), then flips the window in its own tick; tiles that stay are never touched, and tiles that left stay in place, masked by the
     * material's window test, until they are reused. Used when the grid is 12.5 cm and exactly n x 800 cm wide (the LiDAR and Benmore levels: 4800 cm); other sizes keep the single mesh. */
    bool UseTiledGrid() const;
    void InitTiledGrid();
    FVector SnapWindowCentre(const FVector& Pawn) const;
    void PumpTiledGrid(const FVector& Pawn,double Deadline);
    bool BuildTileHeights(double Deadline);
    void FinishTile();
    UPROPERTY(Transient) TArray<TObjectPtr<UProceduralMeshComponent>> TilePool;
    TArray<bool> TileHasSection;
    TMap<FIntPoint,int32> TileSlot;
    TArray<int32> FreeTiles;
    TArray<FIntPoint> PendingTiles;
    TArray<double> TileHeights;
    TArray<FVector> TileVertices,TileNormals;
    TArray<FVector2D> TileUV;
    TArray<int32> TileIndices;
    FIntPoint WindowMinTile=FIntPoint::ZeroValue,PendingMinTile=FIntPoint::ZeroValue,BuildingTile=FIntPoint::ZeroValue;
    FVector PendingCentre=FVector::ZeroVector;
    int32 TilesPerSide=0,PendingNext=0,BuildingSlot=-1,BuildingRow=0;
    bool bTiled=false,bMoving=false,bFlippedThisTick=false;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WaterDynamic;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SedimentDynamic;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextureRenderTarget2D>> StateTargets;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextureRenderTarget2D>> SedimentTargets;
    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> Waves;
    float Carry=0;
    int32 Previous=0,WaterSteps=0;
};
