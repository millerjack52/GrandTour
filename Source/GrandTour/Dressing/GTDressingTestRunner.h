#pragma once

#include "CoreMinimal.h"

class UWorld;

/**
 * Smoke test for the OW landscape toolkit test map (docs/LandscapeMigrationManifest.md 9.A step 7, checks 9.C.5).
 * -GTDressingTest on /Game/GrandTour/Test/L_OWToolkitTest (Art/dressing_toolkit_test.bat). Driven by AGTRunGameMode::Tick.
 * Waits a few seconds after BeginPlay, then judges once:
 *  - 3 road actors whose class name starts with BP_OWRoad, each with a UOWRoadBedComponent;
 *  - the landscape material's path ends in MI_OWDressingLab_Style;
 *  - the unique layer infos in the landscape components' weightmap allocations are exactly the 13 non-water
 *    OW_<X>_LayerInfo assets (by asset name), none named Bed or RiverWet;
 *  - each of the 6 actors tagged OWBiome.Forest / Meadow / Scree / Alpine / Cliff / Road owns
 *    UInstancedStaticMeshComponents with more than 0 instances in total (saved by the ticking pass).
 * No PCG dependency: it reads only actors, tags, components and landscape allocations.
 */
class FGTDressingTestRunner
{
public:
	explicit FGTDressingTestRunner(UWorld* InWorld);

	/** True when finished; bOutPass and OutSummary carry the verdict (the failing checks on FAIL). */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	void Judge(bool& bOutPass, FString& OutSummary) const;

	TWeakObjectPtr<UWorld> World;
	float Elapsed = 0.f;
	int32 Ticks = 0;
};
