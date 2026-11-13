// Deformable gravel DG1 item 3 (docs/DEFORMABLE_GRAVEL_PLAN.md DG1): the loose 3D stones the Blender study shows and the game
// lacked. A gravel patch (EGTDeformMedium::Gravel with a stone density on its profile) owns one of these: the study's
// SM_GR_Stone1..4 as one hierarchical instance component per mesh, placed deterministically per section, pushed aside by the
// wheels on the same per-wheel path that stamps the field (UGTTractionComponent::StampMud), visual only (the field's windrow
// carries the volume). gt.Gravel.Stones 0/1, gt.Gravel.StoneDensity 0-1.
#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "GTGravelStones.generated.h"

class AGTMudPatch;
class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;

UCLASS(ClassGroup = (GrandTour))
class GRANDTOUR_API UGTGravelStones : public USceneComponent
{
	GENERATED_BODY()

public:
	UGTGravelStones();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** One stone: where it rests (world XY, cm), its size across (cm), its yaw (deg), its random tilt axis and angle, its mesh,
	 *  how deep it sits (a share of its height), and its instance in that mesh's component. */
	struct FStone
	{
		FVector2D XY = FVector2D::ZeroVector;
		float SizeCm = 3.f;
		float YawDeg = 0.f;
		FVector2D TiltAxis = FVector2D(1.f, 0.f);
		float TiltDeg = 0.f;
		FVector Stretch = FVector(1.f, 1.f, 1.f);
		float Sink = 0.25f;
		int32 Mesh = 0;
		int32 Instance = INDEX_NONE;
		uint8 State = 0;   // 0 rest, 1 pushed, 2 pressed in, 3 flicked
	};

	/** What one wheel stroke did (PushUnderWheel). */
	struct FPushResult
	{
		int32 Inside = 0;
		int32 Pushed = 0;
		int32 Pressed = 0;
		int32 Flicked = 0;
		TArray<int32> Moved;    // the pushed stones
		TArray<int32> Thrown;   // the flicked stones
	};

	// ---- Placement (the plan's numbers; proposed starting points the owner names) ----
	/** The section's target, stones per m^2 of road (FGTDeformProfile::GravelStonesPerM2: 30 Loose, 12 Firm), times gt.Gravel.StoneDensity. */
	float DensityPerM2 = 0.f;
	/** DG1b: two octaves of hashed value noise (ClusterCm and ClusterCm2, the second weighted ClusterOctave2), sharpened by a
	 *  smoothstep over 0.5 +- ClusterSharpen (0: none), mapped to x ClusterMin..ClusterMax; the total is renormalised to the target.
	 *  (DG1: one octave of 150 cm at x0.3-1.8, no sharpening.) */
	float ClusterCm = 150.f;
	float ClusterCm2 = 400.f;
	float ClusterOctave2 = 0.45f;
	float ClusterSharpen = 0.1f;
	float ClusterMin = 0.1f;
	float ClusterMax = 2.5f;
	/** As in the study: this much denser within EdgeBandCm of the road's edges and on the crown (CrownHalfCm either side of the route line). */
	float EdgeCrownBoost = 1.6f;
	float EdgeBandCm = 100.f;
	float CrownHalfCm = 45.f;
	/** The road the stones lie on, either side of the route line (the spec's road half width, AGTMudPatch::SetRouteLine). */
	float RoadHalfCm = 350.f;
	/** The density fades to 0 over this at the patch's two ends along the road, so the patch's box draws no line. */
	float EndTaperCm = 300.f;
	/** Sizes across, cm: a truncated power law (Pareto, SizeAlpha), so most are small. */
	float SizeMinCm = 1.5f;
	float SizeMaxCm = 5.f;
	float SizeAlpha = 1.5f;
	/** Tilted to the field's normal plus up to this, deg; sunk SinkMin..SinkMax of their height. */
	float TiltDeg = 15.f;
	float SinkMin = 0.2f;
	float SinkMax = 0.35f;
	/** The instances cull and fade (PerInstanceFadeAmount in M_GT_GravelStone) between these, cm. */
	float CullStartCm = 2500.f;
	float CullEndCm = 3500.f;

	// ---- The wheel (PushUnderWheel) ----
	/** A pushed stone lands PushMin..PushMax half-widths past the capsule's edge, jittered by +-PushJitter half-widths along the stroke. */
	float PushMin = 0.5f;
	float PushMax = 1.f;
	float PushJitter = 0.3f;
	/** This share stays where it is, sunk to PressedSink of its height (and stays pressed under later strokes). */
	float PressedShare = 0.12f;
	float PressedSink = 0.7f;
	/** Wheel slip (0-1) over FlickSlipMin flicks a share equal to the slip, at most FlickShareMax, FlickMinCm..FlickMaxCm back
	 *  along the stroke within +-FlickSpreadDeg; they land at the field's surface. */
	float FlickSlipMin = 0.3f;
	float FlickShareMax = 0.6f;
	float FlickMinCm = 50.f;
	float FlickMaxCm = 300.f;
	float FlickSpreadDeg = 25.f;

	/** The meshes and their material (M_GT_GravelStone: the study's vertex-colour palette, PBR, the cull fade). */
	static const TCHAR* const MeshPaths[4];
	static const TCHAR* const MaterialPath;

	/** Places the stones over the patch (deterministic: the section's index seeds it); with gt.Gravel.Stones 0 or no mesh, none.
	 *  Returns the stones placed. */
	int32 Build(AGTMudPatch& Patch, int32 Seed, float InDensityPerM2, float InRoadHalfCm);
	/** Removes every stone and instance. */
	void Clear();
	/** A wheel's stroke: a capsule from FromCm to ToCm, HalfWidthCm across each side, travelling along Travel (unit), with its
	 *  wheelspin share Slip (0-1). Every stone whose centre is inside is pushed out sideways, pressed in or flicked back. */
	FPushResult PushUnderWheel(const FVector2D& FromCm, const FVector2D& ToCm, float HalfWidthCm, const FVector2D& Travel, float Slip);

	int32 NumStones() const { return Stones.Num(); }
	int32 NumInstances() const;
	const TArray<FStone>& GetStones() const { return Stones; }
	/** The road area the density was spread over, m^2 (the taper weighted in), and the target count it asked. */
	float GetPlacedAreaM2() const { return PlacedAreaM2; }
	int32 GetTargetCount() const { return TargetCount; }
	/** Where a flicked stone started (index in GetStones), for the tests. */
	const TMap<int32, FVector2D>& GetFlickStarts() const { return FlickStarts; }

	static bool IsEnabled();
	static float DensityScale();

private:
	TWeakObjectPtr<AGTMudPatch> Patch;
	int32 BuiltSeed = 0;
	float BuiltProfileDensity = 0.f;
	int32 BuiltEnabled = -1;
	float BuiltScale = -1.f;
	float PlacedAreaM2 = 0.f;
	int32 TargetCount = 0;
	float PressDebt = 0.f;
	float FlickDebt = 0.f;
	uint32 PushCount = 0;

	TArray<FStone> Stones;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> Meshes;
	TArray<float> MeshAcrossCm;
	TArray<float> MeshMinZ;
	TArray<float> MeshHeight;

	/** A 50 cm grid of stone indices, for the wheel's queries. */
	float GridCm = 50.f;
	FVector2D GridOrigin = FVector2D::ZeroVector;
	int32 GridX = 0;
	int32 GridY = 0;
	TArray<TArray<int32>> Grid;

	/** A flicked stone in the air: its index, where it left (world), how long it flies and has flown. */
	struct FFlight
	{
		int32 Stone = 0;
		FVector From = FVector::ZeroVector;
		float Duration = 0.4f;
		float Age = 0.f;
		float ArcCm = 20.f;
	};
	TArray<FFlight> Flights;
	TMap<int32, FVector2D> FlickStarts;
	TArray<FVector2D> RouteCm;
	FVector2D RouteDir = FVector2D(1.0, 0.0);
	float AlongMin = 0.f;
	float AlongMax = 0.f;

	bool EnsureMeshes();
	float SurfaceZ(const FVector2D& XY) const;
	FVector SurfaceNormal(const FVector2D& XY) const;
	float LateralCm(const FVector2D& XY) const;
	float Weight(const FVector2D& XY, int32 Seed) const;
	FTransform StoneTransform(const FStone& Stone) const;
	int32 GridCellAt(const FVector2D& XY) const;
	void GridAdd(int32 Index);
	void GridRemove(int32 Index);
	void Apply(int32 Index, bool bMarkDirty);
};
