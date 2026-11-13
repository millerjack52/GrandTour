#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GTWaterSubsystem.generated.h"

class AGTWaterSheet;
class AGTMudPatch;

/** What kind of water a sample stands in (docs/WATER_PLAN.md W1; W3 added Rut for the mud patches' water). */
UENUM(BlueprintType)
enum class EGTWaterKind : uint8
{
	None,
	Ford,
	/** Water standing in a bog's ruts: the patch's own table over its mud field, no flow, no waves (W3). */
	Rut
};

/** One answer of the one water query: how deep, where the surface is, which way it runs. */
USTRUCT(BlueprintType)
struct FGTWaterSample
{
	GENERATED_BODY()

	/** Water over the ground point, cm (0 outside water or where the ground is above the surface). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Water")
	float DepthCm = 0.f;

	/** The water surface's world Z there, cm (the ground point's own Z when there is no water). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Water")
	float SurfaceZCm = 0.f;

	/** The current at that point, cm/s in world XY (zero in still water and outside a sheet). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Water")
	FVector2D FlowCmPerS = FVector2D::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Water")
	EGTWaterKind Kind = EGTWaterKind::None;

	/** A finite water column over deforming soil; permits hull interaction without treating soil as water. */
	UPROPERTY(BlueprintReadOnly, Category="GT|Water")
	bool bSimulatedMudWater = false;
};

/**
 * The one water query (docs/WATER_PLAN.md, stages W1 and W3). Every AGTWaterSheet registers at BeginPlay and
 * unregisters at EndPlay, and every AGTMudPatch registers at UGTMudSubsystem::BuildPatches; Sample(GroundPoint)
 * returns the deepest water covering that point - its depth, its surface height and its current. The traction reads it
 * per wheel and UGTHullComponent at five points on the body, so nothing in the game asks two different things what the
 * water does: stage W3 folded the mud's rut water in here and removed UGTMudSubsystem::bRutWaterPhysics.
 */
UCLASS()
class GRANDTOUR_API UGTWaterSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	/** Reads -GTRutWater=0/1 off the command line into gt.Water.RutWater once, so a headless run can take the pre-W3 answer. */
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	/** W3's follow-up switch: gt.Water.RutWater (1 the patches are in the query, 0 Sample skips them). */
	static bool IsRutWaterOn();

	void RegisterSheet(AGTWaterSheet* Sheet);
	void UnregisterSheet(AGTWaterSheet* Sheet);

	/** W3: the mud patches, whose ruts hold the patch's own water table (UGTMudSubsystem owns their lifetime). */
	void RegisterPatch(AGTMudPatch* Patch);
	void UnregisterPatch(AGTMudPatch* Patch);

	/**
	 * The deepest water over a ground point. Kind is Ford wherever a sheet covers the XY and Rut wherever a mud patch's
	 * box does, in both cases even at zero depth; where both answer, the deeper wins and the two are never summed (a
	 * ford and a bog are different stretches of route and their water is different water).
	 */
	FGTWaterSample Sample(const FVector& GroundPoint) const;

	/**
	 * Water stage W5: the river stage, cm - how far over its base every sheet's level stands because it has been
	 * raining in the catchment. The target is RiverRiseCmAtFullRain x the weather's GLOBAL rain intensity (a river
	 * answers its catchment, not the cover over the ford, so this is GetRainIntensity and not GetRainAt), relaxed
	 * toward with a first-order lag: RiseLagS while the target is above the stage, FallLagS while it is below
	 * (rivers rise fast and fall slow). A sheet adds it to its level, so the rise reaches the field the way every
	 * level change does since WS2's follow-up - carried whole - and at 180 s that is a few hundredths of a
	 * millimetre a tick, not a step.
	 */
	float GetRiverStageCm() const { return RiverStageCm; }

	/**
	 * Advanced once a frame by the first AGTWaterSheet that ticks: a UWorldSubsystem does not tick, and every sheet
	 * in a world shares one river. Later calls in the same frame do nothing.
	 */
	void AdvanceRiverStage(float DeltaSeconds);

	/** Tests only: multiplies both lags (0.05 turns 180 / 600 s into 9 / 30 s). 1 is the game's own pace. */
	void SetLagScaleForTest(float InScale) { LagScaleForTest = FMath::Max(0.001f, InScale); }
	float GetLagScaleForTest() const { return LagScaleForTest; }

	/** Tests only: the stage back to zero at once, so the next step starts from a river at its base. */
	void ResetRiverStageForTest() { RiverStageCm = 0.f; }

	/**
	 * Tests only: holds the stage where it stands. WS2's rain step and the rain picture rain on a ford to stir its
	 * surface, not to raise its river, and their gates are on a volume that must not move; W5's own step is the one
	 * that lets the rain through.
	 */
	void SetRiverFrozenForTest(bool bFrozen) { bRiverFrozenForTest = bFrozen; }

	/** W5's numbers (docs/VEHICLE_BUILD_SYSTEM.md section 44). */
	float RiverRiseCmAtFullRain = 80.f;
	float RiseLagS = 180.f;
	float FallLagS = 600.f;

	/** The sheets registered in this world (the test and the pictures walk them). */
	const TArray<TWeakObjectPtr<AGTWaterSheet>>& GetSheets() const { return Sheets; }

	/** Select nearby mud ponds once per frame, rather than a quadratic scan by every pond. */
	bool ShouldSimulateMudSheet(const AGTWaterSheet* Sheet, int32 Budget);

	/** The sheet covering a world XY (the deepest is not known without a Z, so this is the first that covers it), or null. */
	AGTWaterSheet* SheetAt(const FVector2D& WorldXY) const;

private:
	TArray<TWeakObjectPtr<AGTWaterSheet>> Sheets;
	TArray<TWeakObjectPtr<AGTMudPatch>> Patches;
	TArray<TWeakObjectPtr<AGTWaterSheet>> ActiveMudSheets;
	uint64 MudSelectionFrame = MAX_uint64;

	/** W5: the stage, its test scale and the frame it was last advanced on (one advance a frame, whoever asks). */
	float RiverStageCm = 0.f;
	float LagScaleForTest = 1.f;
	bool bRiverFrozenForTest = false;
	uint64 RiverStageFrame = 0;
};
