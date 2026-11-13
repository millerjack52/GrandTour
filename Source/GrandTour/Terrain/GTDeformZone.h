#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Terrain/GTTerrainGenerator.h"
#include "GTDeformZone.generated.h"

class USplineComponent;
class UGTSurfacePhysMaterial;

/** Benmore B2: a deform zone's outline. */
UENUM(BlueprintType)
enum class EGTDeformZoneShape : uint8
{
	/** A stretch of road: the polyline LineCm, WidthCm wide, from StartCm to EndCm along it (each end a gently waved cut shared with the next stretch). */
	Road,
	/** A bog: an irregular rounded outline inside the box BlobHalfCm about the actor (turned by its yaw). */
	Blob
};

/**
 * Benmore integration B2 (docs/BENMORE_INTEGRATION_PLAN.md B2): deformable ground placed in any level without a route builder.
 * A zone carries a route section's worth of deformation (Section: its kind, mud variant, water table and FGTDeformProfile, the same
 * struct the strips' sections carry, so AGTMudPatch::ApplySection takes it unchanged) and an outline. UGTMudSubsystem streams its
 * patches: a tiled zone (gravel) onto a world grid of 24 x 24 m tiles at 12.5 cm cells; a mud zone (bTiled false) as one patch over
 * its box, because a bog's pre-churn (GR1c pairs, MRD1's braided tracks, debris, clod fields, chunks) is laid out per patch box.
 * Cells outside the outline stay inert and undrawn; the landscape draws there.
 */
UCLASS()
class GRANDTOUR_API AGTDeformZone : public AActor
{
	GENERATED_BODY()

public:
	AGTDeformZone();

	/** The road's centreline in the editor (a view of LineCm; LineCm is what counts). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|DeformZone")
	TObjectPtr<USplineComponent> Spline;

	/** A stable id (the placement script numbers the zones 1..N): the patches' seeds and the cache's keys. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	int32 ZoneId = 0;
	/** For the reports: "Terrace loop 120-180 m", "Bog 3". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	FString Label;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	EGTDeformZoneShape Shape = EGTDeformZoneShape::Road;

	/** Road: the centreline, world cm (the road's own vertices, the stretch plus a lead-in and lead-out of the neighbouring road). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Road")
	TArray<FVector2D> LineCm;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Road")
	float WidthCm = 640.f;
	/** Benmore B2c: the road the pre-churn lays its tracks on, cm (0: WidthCm). A mud road's zone is wider than its road (the mud spills
	 *  onto the verges and thins out there), its tracks stay on the running surface. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Road")
	float TrackWidthCm = 0.f;
	/** The stretch along LineCm, cm of its arc (EndCm 0: the line's end). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Road")
	float StartCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Road")
	float EndCm = 0.f;
	/** Each end's cut wanders +- this along the road across its width (two sines), so a joint is no straight line. 0: straight. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Road")
	float CutWaveCm = 60.f;
	/** The cuts' keys: the neighbouring stretch carries the same key on its other end, so both draw the same cut (0: straight). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Road")
	int32 StartCutKey = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Road")
	int32 EndCutKey = 0;

	/** Blob: the outline's half sizes along the actor's X and Y (its yaw turns them), cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Blob")
	FVector2D BlobHalfCm = FVector2D(1000.f, 700.f);
	/** The outline's radial wobble, a share of the radius (three low lobes), so a bog is no ellipse. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone|Blob")
	float BlobEdgeNoise = 0.16f;

	/** What deforms: Kind Mud (a bog's field: the Mud and Bog rows, its MudVariant, Deform's pre-churn), or any kind with Deform Mode On (a profiled field: gravel). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	FGTRouteSection Section;
	/** True: 24 m world tiles (gravel). False: one patch over the zone's box (a bog's or a mud road's pre-churn is laid out per box). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	bool bTiled = true;
	/** A mud zone's pre-churn fades to the flat ground over this many cm in from its outline (the strips' PreChurnRimCm), so the mud meets the landscape level. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	float EdgeFadeCm = 150.f;
	/** The field material's tint (M_GT_Gravel_Zone's GravelTint: the TA_GV gravel toward the review landscape's road colour). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	FLinearColor SurfaceTint = FLinearColor::White;
	/** A mud zone's rows: the traction reads these in place of the landscape's physical material inside it (Benmore has no Mud or Bog layer). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	TSoftObjectPtr<UGTSurfacePhysMaterial> MudRow;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	TSoftObjectPtr<UGTSurfacePhysMaterial> BogRow;
	/** Benmore B2c: the patch's surface material in place of the medium's (a mud zone's M_GT_Mud_Zone; empty: as before). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	FString PatchMaterialPath;
	/** Benmore B2c: a mud zone's wet mud colour, linear (the soil round it, wetter): the far map's colour beyond the live patches. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	FLinearColor MudColour = FLinearColor(0.12f, 0.09f, 0.06f, 1.f);
	/** Benmore B2c: a mud zone thins out over this feather in from its outline, cm (min, max: a 9 m noise picks between). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|DeformZone")
	FVector2D FeatherCm = FVector2D(150.f, 300.f);

	/** Caches the outline (the subsystem calls it at BeginPlay; the editor's construction calls it too). */
	void Prepare();
	virtual void OnConstruction(const FTransform& Transform) override;
	/** Inside the outline; OutInsideCm the distance in from its edge (negative outside, roughly). Benmore B2c: every zone's outline is
	 *  tested at the point moved by OutlineWarpCm (one field for all zones, so neighbouring stretches still partition the road). */
	bool IsMember(const FVector2D& XYCm, float* OutInsideCm = nullptr) const;
	/** Benmore B2c: the outline warp, +-100-250 cm at 8 and 15 m wavelengths (the same for every zone). */
	static FVector2D OutlineWarpCm(const FVector2D& XYCm);
	static constexpr float OutlineWarpMaxCm = 260.f;
	/** Benmore B2c: how much of the patch draws, 0..1: a mud zone thins out over FeatherCm in from its outline; a gravel zone is whole. */
	float OpacityAt(const FVector2D& XYCm) const;
	/** Benmore B2c: the opacity from a known inside distance (OpacityAt without a second outline test). */
	float OpacityFromInside(const FVector2D& XYCm, float InsideCm) const;
	float GetTrackHalfWidthCm() const;
	/**
	 * Benmore B2c: the far maps of the world's mud zones (the review material shows them beyond the live patches): MaskPng RGBA8,
	 * MaskSize texels over SizeCm from OriginCm (R the mud's opacity, G the apron ApronCm out from the outline); ColourPng RGBA8 sRGB,
	 * ColourSize texels over the same square (each mud zone's MudColour out to its apron and 4 m more). Returns a JSON summary.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|DeformZone", meta = (WorldContext = "WorldContext"))
	static FString BakeMudMaps(UObject* WorldContext, FVector2D OriginCm, float SizeCm, int32 MaskSize, int32 ColourSize, float ApronCm, const FString& MaskPng, const FString& ColourPng);
	/** The deep core of a mud zone, 0..1 (the generator's rule: BogCoreFraction + BogPocketFraction x a 25 m noise of the half width), 0 off it. */
	float BogWeightAt(const FVector2D& XYCm) const;
	/** The outline's bounds, world cm (a little loose). */
	FBox2D GetBoundsCm() const { return BoundsCm; }
	/** The road line a patch follows (Road: LineCm; Blob: its long axis through the centre). */
	void GetRouteLine(TArray<FVector2D>& Out) const;
	float GetHalfWidthCm() const;
	bool IsMud() const { return Section.Kind == EGTRouteSectionKind::Mud; }
	/** The length of the stretch (Road) or the outline's area (Blob), for the reports. */
	UFUNCTION(BlueprintPure, Category = "GT|DeformZone")
	float StretchLengthM() const;
	UFUNCTION(BlueprintPure, Category = "GT|DeformZone")
	float AreaM2() const;

	/** The cut line's offset along the road at a lateral position, cm (shared by the two stretches either side of a key). */
	static float CutOffsetCm(int32 Key, float LateralCm, float AmpCm);

private:
	TArray<float> ArcCm;
	FBox2D BoundsCm = FBox2D(ForceInit);
	float EndArcCm = 0.f;
	bool bPrepared = false;
	void Project(const FVector2D& XY, float& OutS, float& OutT, float& OutDist) const;
	float BlobEdge(float Angle) const;
};
