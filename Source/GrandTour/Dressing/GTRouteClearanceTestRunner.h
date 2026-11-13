#pragma once

#include "CoreMinimal.h"

class UWorld;

/**
 * Leg dressing LD7 (docs/LEG_DRESSING_PLAN.md LD7, "Route clearance"): -GTRouteClearTest on /Game/GrandTour/Legs/L_Leg03
 * (Art/route_clear_test.bat, in the suite). Driven by AGTRunGameMode::Tick; waits a few seconds after BeginPlay (the
 * vegetation subsystem indexes the soft instances there), then judges once, headless (-NullRHI):
 *  - the corridor: every 2 m along the main route and each alt route (the spec's polylines, the spec's ground), a
 *    3 m wide x 4 m long x 2 m tall box (its bottom 10 cm over the ground) swept to the next station. Solid: the physics
 *    sweep (object query WorldStatic + WorldDynamic, every actor but the GTBiome.* dressing ignored) must hit 0
 *    GTVeg.Solid instances, and no Solid or unclassed dressing instance may stand inside the swept boxes by position
 *    either (a solid mesh without simple collision is invisible to the sweep). Soft: the vegetation subsystem's hash -
 *    each indexed instance's contact circle (its pivot, its index radius) - must hold 0 instances inside the swept boxes;
 *  - the gameplay points: no dressing instance of any class (its position; soft ones their pivot) within 5 m of the
 *    bounds of the start (AGTLegStart), the checkpoints, the extraction zone or any interactable (IGTInteractable or a
 *    UGTInteractionComponent; loaded with the map, pawns left out) - the exclusion's own selection;
 *  - information: the nearest Solid, Soft and unclassed instance to the route centrelines (soft: the pivot less its
 *    radius), and how many sit within 2 m of the corridor's edge and within 2 m of the road's edge.
 * Fails when the map holds no dressing (run Art/dressing/setup_dress_hide.bat and the tick harness first).
 */
class FGTRouteClearanceTestRunner
{
public:
	explicit FGTRouteClearanceTestRunner(UWorld* InWorld);

	/** True when finished; bOutPass and OutSummary carry the verdict (the failing checks on FAIL). */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	void Judge();
	void Line(const FString& Text) const;

	TWeakObjectPtr<UWorld> World;
	float Elapsed = 0.f;
	int32 Ticks = 0;
	TArray<FString> Failures;
	TArray<FString> Notes;
};
