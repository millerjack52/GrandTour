#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Terrain/GTLandscapeSurfaceField.h"
#include "HAL/ThreadSafeCounter.h"
#include "GTLandscapeSurface.generated.h"

class ALandscapeProxy;
class UMaterialInstanceDynamic;
class UTexture2D;
class AStaticMeshActor;
class UMaterialInterface;
class AGTWaterSheet;

/** Authored mud character within a world-space rectangle; paint still controls coverage and depth. */
USTRUCT(BlueprintType)
struct FGTLandscapeMudRegion
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName Name = TEXT("Mud");
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector2D Centre = FVector2D::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector2D HalfSize = FVector2D(450,550);
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Wetness = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Cohesion = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Relief = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float FragmentScale = 1.f;
    /** Broad elliptical bowl within this region; zero preserves the scanned rest shape. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float BasinDepthCm = 0.f;
    /** Intact sod cover. Paint R still specifies the finite yielding layer, usually 2-8 cm. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float GrassCover = 0.f;
    /** Authored material choice; source beach is extrudable, but the granular law is a host adapter. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bGranular = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bElliptical = false;
    /** CL2: clay weight 0-1 inside this region, the same quantity as the clay atlas value on atlas maps. Zero is no clay. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ClayWeight = 0.f;
    /** Rotate authored shore strips into the river's frame; legacy regions stay axis-aligned. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float YawDegrees = 0.f;
    bool Contains(FVector2D P) const
    {
        const FVector2D D=(P-Centre).GetRotated(-YawDegrees);
        if(FMath::Abs(D.X)>HalfSize.X || FMath::Abs(D.Y)>HalfSize.Y)return false;
        return !bElliptical || FMath::Square(D.X/FMath::Max(1.,HalfSize.X))+FMath::Square(D.Y/FMath::Max(1.,HalfSize.Y))<=1.;
    }
};

/** The physics seam. Units are explicit; this actor never changes suspension, friction or wheel radii. */
USTRUCT(BlueprintType)
struct GRANDTOUR_API FGTLandscapeSurfaceSample
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) bool bAuthored = false;
    UPROPERTY(BlueprintReadOnly) float SinkageCapCm = 0.f;
    UPROPERTY(BlueprintReadOnly) float SinkageRateCmPerS = 0.f;
    UPROPERTY(BlueprintReadOnly) float FrictionScale = 1.f;
    UPROPERTY(BlueprintReadOnly) float Softness = 0.f;
    UPROPERTY(BlueprintReadOnly) float WaterDepthCm = 0.f;
    UPROPERTY(BlueprintReadOnly) float MudHeightAboveBaseCm = 0.f;
    UPROPERTY(BlueprintReadOnly) float SurfaceDeltaCm = 0.f;
    /** Removed height relative to the authored bog, excluding its natural hollows. */
    UPROPERTY(BlueprintReadOnly) float CompressionCm = 0.f;
    UPROPERTY(BlueprintReadOnly) bool bWheelSupport = false;
    UPROPERTY(BlueprintReadOnly) float WheelSupportCm = 0.f;
    /** Undisturbed height over the same footprint as WheelSupportCm. */
    UPROPERTY(BlueprintReadOnly) float RestWheelSupportCm = 0.f;
    UPROPERTY(BlueprintReadOnly) float Wetness = 0.f;
    UPROPERTY(BlueprintReadOnly) float Cohesion = 0.f;
    UPROPERTY(BlueprintReadOnly) float GrassCover = 0.f;
    /** Vegetation is appearance, not a reinforcement multiplier, on opted-in woodland. */
    UPROPERTY(BlueprintReadOnly) bool bGrassIsVisualCover = false;
    UPROPERTY(BlueprintReadOnly) float Disturbance = 0.f;
    UPROPERTY(BlueprintReadOnly) bool bSoilShearResponse = false;
    UPROPERTY(BlueprintReadOnly) bool bGranularResponse = false;
    UPROPERTY(BlueprintReadOnly) bool bNativeSubstanceResponse = false;
    UPROPERTY(BlueprintReadOnly) bool bNativeWaterResponse = false;
    UPROPERTY(BlueprintReadOnly) float NativeExtrudeCm = 0.f;
    UPROPERTY(BlueprintReadOnly) float NativeUpperCm = 0.f;
    /** CL2 clay: weight 0-1 from the clay atlas or region, the native substance numbers for this ground
     * (defaults are the substance struct's mud numbers 2.2 / 10 / 36), and the extra Chaos tyre grip scale
     * for wet clay (1 on anything else). FrictionScale above already includes ClayFrictionScale. */
    UPROPERTY(BlueprintReadOnly) float ClayWeight = 0.f;
    UPROPERTY(BlueprintReadOnly) float NativeFriction = 2.2f;
    UPROPERTY(BlueprintReadOnly) float NativeLinearResistance = 10.f;
    UPROPERTY(BlueprintReadOnly) float NativePushResistance = 36.f;
    UPROPERTY(BlueprintReadOnly) float ClayFrictionScale = 1.f;
    UPROPERTY(BlueprintReadOnly) float BearingStrength = 1.f;
    UPROPERTY(BlueprintReadOnly) float SettlementSpeedScale = 1.f;
    UPROPERTY(BlueprintReadOnly) FName SurfaceTag = TEXT("FirmGround");

    // Shared equilibrium for both physical support and plastic soil displacement.
    // Reference the original footprint, never last frame's lowered surface (which ratchets).
    float MaximumSettlementCm() const
    {
        const float Strength = bSoilShearResponse ? FMath::Clamp(BearingStrength,.35f,3.f) : 1.f;
        return FMath::Min(40.f,19.f*FMath::Lerp(1.f,1.25f,FMath::SmoothStep(32.f,48.f,SinkageCapCm))/Strength);
    }
    float LoadedSettlementCm(float NormalizedLoad) const
    {
        const float DeepYield=FMath::Lerp(1.f,1.25f,FMath::SmoothStep(32.f,48.f,SinkageCapCm));
        const float Strength = bSoilShearResponse ? FMath::Clamp(BearingStrength,.35f,3.f) : 1.f;
        const float Yield = 18.f * DeepYield * Softness * FMath::Sqrt(FMath::Clamp(NormalizedLoad,0.f,1.6f))
            * FMath::Lerp(1.f,.3f,bGrassIsVisualCover ? 0.f : GrassCover) / Strength;
        return FMath::Min(FMath::Min(Yield,MaximumSettlementCm()),FMath::Max(0.f,SinkageCapCm+RestWheelSupportCm));
    }
};

/** Opt-in small-area landscape prototype. No mesh, holes, scatter, or modifications to legacy mud patches. */
UCLASS()
class GRANDTOUR_API AGTLandscapeSurface : public AActor
{
    GENERATED_BODY()
public:
    AGTLandscapeSurface();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    TObjectPtr<ALandscapeProxy> Landscape;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    FVector2D PaintOriginCm = FVector2D(-1600, -1600);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    float PaintSizeCm = 3200.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    int32 PaintResolution = 256;
    /** Serialized CPU paint, identical to PaintTexture. Import through the editor helper. */
    UPROPERTY() TArray<FLinearColor> PaintCells;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    TObjectPtr<UTexture2D> PaintTexture;
    /** Optional world-wide material atlas: sand, sod, wetness, exposed rock. */
    UPROPERTY() TArray<FLinearColor> MaterialCells;
    UPROPERTY() int32 MaterialResolution = 0;
    FLinearColor MaterialAt(FVector2D World) const;
    bool NativeMudAt(FVector2D World) const;
    /** CL2 clay atlas, same origin and span as the material atlas: R clay weight, G orange cut face, B bush slurry.
     * Stored as the source's 8-bit colours (a quarter of the memory of the material atlas's floats; every value
     * is the same 8-bit number the texture holds). Import through UGTLandscapeSurfaceSetupLibrary::ImportClayAtlas. */
    UPROPERTY() TArray<FColor> ClayCells;
    UPROPERTY() int32 ClayResolution = 0;
    FLinearColor ClayAt(FVector2D World) const;
    /** Clay weight at a point: the atlas, or the largest ClayWeight of the mud regions containing it, whichever is larger. */
    float ClayWeightAt(FVector2D World) const;
    bool HasClay() const;
    /** Optional linear, box-filtered scan data; serialized so runtime never reads editor texture source. */
    UPROPERTY() TArray<float> MudRestHeights;
    UPROPERTY() TArray<float> ClayRestHeights;
    UPROPERTY() int32 RestHeightResolution = 0;
    /** Optional unique height map in PaintOriginCm/PaintSizeCm coordinates; centimetres, no wrapping. */
    UPROPERTY() TArray<float> WorldRestHeights;
    UPROPERTY() int32 WorldRestResolution = 0;
    /** Optional periodic, centimetre-valued starting relief shared with the visual shader. */
    UPROPERTY() TArray<float> MudReliefHeights;
    UPROPERTY() int32 MudReliefResolution = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    float MudReliefTileCm = 12800.f;
    /** Independent non-colliding water surface, driven by the same ground/contact field. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    TObjectPtr<AStaticMeshActor> PuddleSurface;
    /** Optional shared water solver. Null keeps the static prototype pools. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Landscape Surface")
    TObjectPtr<AGTWaterSheet> SimulatedWater;
    /** Optional scene-specific tyre shader; receives existing per-wheel pickup/washing state. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    TObjectPtr<UMaterialInterface> TyreCoatingMaterial;
    /** Reads contact positions only. Disable when physics starts calling StampWheel directly. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    bool bObservePlayerWheels = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    bool bFollowPlayer = true;
    /** Regional native grid supplies drawing; retain the large landscape collision and background. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    bool bSeparateVisualMesh = false;
    /** Keep a regional field near its paint when the player travels across a large map. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    bool bClampFocusToPaint = false;
    /** Water-only coverage over the linked domain, including outside this region's ground paint. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    bool bExtendWaterResponseToDomain = false;
    /** Opt-in driving bridge: filtered displacement feeds the existing Chaos radius support path. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    bool bEnableWheelSupport = false;
    /** Proving-ground response uses saturation and soil history for shear strength. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    bool bUseSoilShearResponse = false;
    /** Experimental directional soil flow and yielding rut-wall resistance. Off preserves accepted maps. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface|Soil Properties")
    bool bUseRutInteraction = false;
    /** Loose granular soil: dry spreading shoulders and pressure-dependent friction. Opt-in. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface|Soil Properties")
    bool bUseGranularResponse = false;
    /** Recovered MudCompute_002 height/mask update; lab-only, off in existing maps.
     * Chaos still supplies the footprint and loaded contact plane. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface|Research")
    bool bUseNativeMudShaderUpdates = false;
    /** Recovered wheel substance impulses; Chaos contacts/cadence remain explicit host adapters. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface|Research")
    bool bUseNativeSubstanceResponse = false;
    /** Grass/forest material definitions are extrudable. Keep legacy maps unchanged. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface|Research")
    bool bGrassIsVisualCover = false;
    /** Recovered wheel water impulses, independent of this surface's mud model. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface|Research")
    bool bUseNativeWaterResponse = false;
    /** Set before Play. Scales the painted finite layer beneath the reference plane.
     * Does not enlarge the authored clods. 1 preserves the proving-ground baseline. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Landscape Surface|Soil Properties", meta=(ClampMin="0.1", ClampMax="3"))
    float LayerDepthScale = 1.f;
    /** Authored depth ceiling. The recovered physical byte spans 124 cm; old maps retain 50. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface|Soil Properties", meta=(ClampMin="1", ClampMax="124"))
    float MaximumLayerDepthCm = 50.f;
    /** Set before Play. Lower values yield farther under the same wheel load.
     * 1 baseline, .6 soft bog, 1.6 firm soil. Separate from water level and soil depth. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Landscape Surface|Soil Properties", meta=(ClampMin="0.35", ClampMax="3"))
    float BearingStrength = 1.f;
    /** Set before Play. Changes time to settle, not the final depth. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Landscape Surface|Soil Properties", meta=(ClampMin="0.25", ClampMax="3"))
    float SettlementSpeedScale = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Landscape Surface")
    TArray<FGTLandscapeMudRegion> MudRegions;

    UFUNCTION(BlueprintPure, Category="Landscape Surface")
    FGTLandscapeSurfaceSample SampleSurface(FVector2D WorldXY) const;
    UFUNCTION(BlueprintCallable, Category="Landscape Surface", meta=(WorldContext="WorldContext"))
    static FGTLandscapeSurfaceSample QuerySurface(UObject* WorldContext, FVector2D WorldXY);
    UFUNCTION(BlueprintCallable, Category="Landscape Surface", meta=(WorldContext="WorldContext"))
    static FGTLandscapeSurfaceSample QueryWheelSurface(UObject* WorldContext, FVector Contact, FVector2D Heading, float WidthCm);
    UFUNCTION(BlueprintCallable, Category="Landscape Surface")
    void StampWheel(FVector2D Start, FVector2D End, FVector2D Heading, float WidthCm, float DepthCm);
    /** Explicit owner review fixture: one pass, repeated pass and stationary spin, across the tile boundary. */
    UFUNCTION(BlueprintCallable, Category="Landscape Surface")
    void ApplyReviewTracks();
    UFUNCTION(BlueprintCallable, Category="Landscape Surface|Research")
    void ApplyReviewNativeContact(FVector2D Point,float Excitation);
    /** Body contact adapter; finite, motion-driven physical and visual yielding. */
    void ApplyBodySoilContact(FVector Point,FVector Velocity,float MassKg,float WidthCm,float Dt);
    /** Stationary/swept field fixture using the same worked-soil path as wheel observations. */
    UFUNCTION(BlueprintCallable, Category="Landscape Surface|Research")
    void ApplyReviewSoilStroke(FVector2D Start,FVector2D End,float WidthCm,float DepthCm,float Slip=0.f);
    UFUNCTION(BlueprintPure, Category="Landscape Surface")
    FString GetSurfaceReport() const;

    /** Authored solid ground, before live mud displacement. Empty tiles preserve legacy maps. */
    UPROPERTY() TMap<FIntPoint,TObjectPtr<class AGTRoadReliefTile>> RoadReliefTiles;
    UPROPERTY() FVector2D RoadTileOrigin=FVector2D::ZeroVector;
    UPROPERTY() float RoadTileSpanCm=0;
    TOptional<float> GroundHeightAt(FVector Position) const;
    /** Both the landscape and this surface's generated road tiles feed soil contacts. */
    bool OwnsGroundActor(const AActor* Actor) const;
    UFUNCTION(BlueprintPure) bool HasRoadReliefAt(FVector2D XY) const;
    FLinearColor PaintAt(FVector2D World) const;
    FLinearColor ShapeAt(FVector2D World) const;
    float GrassAt(FVector2D World) const;
    float BedDeltaCm(FVector2D World) const;
    /** Height-only equivalent of SampleSurface for the wheel contact grid. */
    UFUNCTION(BlueprintPure, Category="Landscape Surface|Research")
    float ContactHeightCm(FVector2D World, bool bNative) const;
    uint64 BedRevision() const { return Field.GeometryRevision; }
    void BedChangesSince(uint64 Revision,TArray<FBox2D>& Regions) const { Field.BedChangesSince(Revision,Regions); }
    void BindSimulatedWaterMaterial(UMaterialInstanceDynamic* Material);
    void RegisterResearchMaterial(UMaterialInstanceDynamic* Material);
    /** Cosmetic budget only: 0 low, 1 balanced, 2 high. Never changes physics or stamping. */
    static int32 GetVisualQuality();
private:
    void Upload();
    /** bFull false (a window publish after the first) rebinds only what changed: the two field textures and the window. */
    void BindTextures(bool bFull = true);
    bool bBoundReady = false;
    /** PF1: the landscape side of a window publish (the two field textures and the window on every landscape component's material instance) runs a slice per tick. A component not yet reached keeps a complete, valid older binding; no new refresh starts until the pass is done. */
    struct FLandscapeBind { bool bActive = false; int32 Cursor = 0; UTexture2D* Field = nullptr; UTexture2D* Water = nullptr; FLinearColor Window = FLinearColor::Black; };
    FLandscapeBind LandscapeBind;
    void PumpLandscapeBind(double Deadline);
    float ScannedRestHeight(FVector2D World, float Thickness) const;
    void ObserveWheels(float Dt);
    FGTLandscapeSurfaceField Field;
    // Native CPU physical mud is independent of the fine visual field.
    TMap<FIntPoint,uint8> NativeExtrudes;
    TArray<float> NativeContactCarry;
    uint8 NativeByte(FIntPoint Cell) const;
    float NativeQ(FVector2D XY) const;
    float NativeUpper(FVector2D XY) const;
    void StampNativePhysical(FVector2D XY,float Excitation);
    UPROPERTY(Transient) TObjectPtr<UTexture2D> FieldTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> WaterTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> StagingFieldTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> StagingWaterTexture;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> NaniteMaterials;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> PuddleMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> ResearchMaterials;
    TWeakObjectPtr<APawn> ObservedPawn;
    TArray<FVector2D> LastContacts;
    TArray<bool> HadContact;
    TArray<float> VisualDepthCm;
    float WheelObserveTime = 0.f;
    float UploadTime = 0.f;
    bool bDisplacementScaleValid = false;
    FIntPoint UploadWindow = FIntPoint(MAX_int32,MAX_int32);
    FIntPoint PublishedWindow = FIntPoint::ZeroValue;
    int32 RefreshCursor = -1, DirtyCursor = 0, AppliedQuality = -1;
    bool bTexturesReady = false;
    TSharedPtr<FThreadSafeCounter,ESPMode::ThreadSafe> PendingUploads = MakeShared<FThreadSafeCounter,ESPMode::ThreadSafe>();
    uint64 UploadedCells = 0, ShadowRevision = 0;
    double PeakUploadMs = 0;
    float ShadowTime = 0;
    double WheelObserveTotalMs=0,WheelObservePeakMs=0;
    uint64 WheelObserveCount=0;
};
