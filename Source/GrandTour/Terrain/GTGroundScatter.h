// Ground relief GR2 phase B item 3 (docs/GROUND_RELIEF_PLAN.md GR2): the ground scatter on the test strips - soil clods, pebbles,
// twigs, dead-grass litter mats near the tussocks and a root mound under each tussock (Art/Blender/bake_ground_detail_gr2.py's
// SM_GD_* meshes). Placed once at level setup (the strips' setup scripts call Build in the editor), deterministic, one hierarchical
// instance component per mesh, saved with the level. gt.Ground.Scatter 0/1 and gt.Ground.ScatterDensity 0-1 at run time.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTGroundScatter.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;
class UGTTerrainSpecAsset;
struct FGTTerrainSpec;
struct FGTTerrainProfiles;

/** One scatter mesh as the setup script passes it (from Art/Export/GroundDetailGR2/manifest.json). */
USTRUCT(BlueprintType)
struct FGTGroundScatterMesh
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	TObjectPtr<UStaticMesh> Mesh = nullptr;

	/** Clods, Pebbles, Twigs, Litter or TussockBases. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	FName Family;

	/** Its size across as built, cm (the manifest's size_cm, or across_cm for a tussock base). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float SizeCm = 5.f;

	/** 0: the mesh carries its own embed (its origin is the ground; A2's clods, litter and bases are modelled sunk). Otherwise its
	 *  bottom goes this share of its height under the ground (A1's pebbles and twigs). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float SinkShare = 0.f;
};

UCLASS(ClassGroup = (GrandTour))
class GRANDTOUR_API AGTGroundScatter : public AActor
{
	GENERATED_BODY()

public:
	AGTGroundScatter();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	// ---- The plan's numbers (proposed starting points the owner names) ----
	/** Per m^2 of open ground (scrub and grass, off every road, patch and ford), times the cluster multiplier. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float ClodsPerM2 = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float PebblesPerM2 = 1.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float TwigsPerM2 = 0.05f;
	/** Litter mats per m^2, only within LitterReachCm of a tussock. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float LitterPerM2 = 0.25f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float LitterReachCm = 150.f;
	/** A tussock base (root mound) under each tussock whose footprint is at least this, scaled to the footprint. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float BaseMinFootprintCm = 25.f;
	/** The cluster noise: hashed value noise at ClusterCm mapped to x ClusterMin..ClusterMax, renormalised over the area to mean 1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float ClusterCm = 300.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float ClusterMin = 0.1f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float ClusterMax = 2.5f;
	/** The noise sharpened by a smoothstep over 0.5 +- this before the mapping (DG1b's ClusterSharpen): a smoothstepped value noise
	 *  alone stays near its middle (renormalised x0.33-1.67 at p5-p95), sharpened it spans the plan's range (x0.08-1.93). 0: none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float ClusterSharpen = 0.25f;
	/** Open ground: the off-road layer's weight at least this (GTTerrain::OffRoadWeight; the road's paving and its fade are out). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float OffRoadMin = 0.9f;
	/** Every section's patch box (GTTerrain::DeformPatchBoxCm: mud, gravel, a ford's bed) grown by this, the apron's 3 m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float PatchMarginCm = 300.f;
	/** Clods, pebbles and bases cull (and fade, PerInstanceFadeAmount) between these; twigs and litter between the Small pair. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float CullStartCm = 3000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float CullEndCm = 4000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float SmallCullStartCm = 1800.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	float SmallCullEndCm = 2500.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Ground")
	int32 Seed = 0;

	/** One planned instance: where (world XY, cm), which of the meshes, its scale, its yaw. */
	struct FPoint
	{
		FVector2D XYCm = FVector2D::ZeroVector;
		int32 Mesh = 0;
		float Scale = 1.f;
		float YawDeg = 0.f;
	};

	struct FPlanStats
	{
		double OpenAreaM2 = 0.0;
		double LitterAreaM2 = 0.0;
		int32 Tussocks = 0;
		int32 TussocksUnderFootprint = 0;
		int32 Rejected = 0;
		TMap<FName, int32> PerFamily;
	};

	/**
	 * The placement without a world (the tests run it): over the spec's landscape, the open ground's points per family, clustered,
	 * deterministic. Tussocks: the strip's tussock instances (world cm) and each one's footprint across (cm).
	 */
	void Plan(const FGTTerrainSpec& Spec, const TArray<FGTGroundScatterMesh>& InMeshes, const TArray<FTransform>& Tussocks,
		const TArray<float>& TussockFootprintsCm, TArray<FPoint>& Out, FPlanStats& OutStats) const;

	/** The cluster multiplier at a world XY (cm), ClusterMin..ClusterMax before the area's renormalisation. */
	float ClusterMultiplier(const FVector2D& XYCm) const;

	/** Is a point open ground (off the road's paving, every patch box + margin and every channel)? Profiles from GTTerrain::BuildProfiles. */
	bool IsOpenGround(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, const TArray<FBox2D>& Boxes, const FVector2D& XYCm) const;

	/**
	 * Editor, at level setup: plans, drops each point onto the landscape (a trace; aligned to its normal, sunk by the mesh's embed),
	 * and rebuilds one hierarchical instance component per mesh (saved with the level). Returns a JSON report: instances per mesh
	 * and per family, the open area, the achieved densities.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Ground")
	FString Build(UGTTerrainSpecAsset* SpecAsset, const TArray<FGTGroundScatterMesh>& InMeshes, const TArray<FTransform>& Tussocks,
		const TArray<float>& TussockFootprintsCm);

	/** The instances each component holds now (in Build's mesh order). */
	UFUNCTION(BlueprintCallable, Category = "GT|Ground")
	TArray<int32> InstanceCounts() const;

	static bool IsEnabled();
	static float DensityScale();

private:
	UPROPERTY(VisibleAnywhere, Category = "GT|Ground")
	TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> Components;

	/** At play: every component's full instance list (the density switch keeps a stable hashed subset of it). */
	TArray<TArray<FTransform>> Full;
	int32 AppliedEnabled = -1;
	float AppliedDensity = -1.f;

	void ApplySwitches(bool bForce);
};
