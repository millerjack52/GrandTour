#pragma once

#include "CoreMinimal.h"
#include "Core/GTDriveTestGameMode.h"
#include "Core/GTM3TestRunner.h"
#include "Core/GTM4TestRunner.h"
#include "Core/GTM5TestRunner.h"
#include "Core/GTM6TestRunner.h"
#include "Core/GTProvingTestRunner.h"
#include "Core/GTFordDiagRunner.h"
#include "Core/GTProvingShotsRunner.h"
#include "Core/GTRunSubsystem.h"
#include "Dressing/GTBiomeTestRunner.h"
#include "Dressing/GTRouteClearanceTestRunner.h"
#include "Dressing/GTDressingTestRunner.h"
#include "Dressing/GTVegTestRunner.h"
#include "GTRunGameMode.generated.h"

class AGTRunGameState;
class UGTLegDefinition;

/**
 * The per-leg game mode (ARCHITECTURE 5): finds the leg (the run subsystem's pending leg, else
 * the map's AGTLegStart), hands it to AGTRunGameState with the map's checkpoints and extraction
 * zone, sets the starting weather, and when the extraction hold completes builds the result
 * (time, haul, the mission's verdict, the placing against the tour's simulated rivals, points and
 * prize), records it in the run subsystem and freezes the car under the results screen; Enter /
 * Start goes to the base. Maps without a leg (the test tracks) run exactly as before: the leg
 * phase stays None.
 *
 * Derives from the test game mode so every headless self-test keeps working on any map; the M3
 * ones run here (FGTM3TestRunner):
 *  -GTLegTest      timer starts on the first move, checkpoints clear in order, extraction refused
 *                  before the last checkpoint and completed after a 2 s stop, result recorded.
 *  -GTWeatherTest  subsystem blends to rain, wetness rises, the collection and the car's traction
 *                  follow, rain drops fall and none under a roof, exposure drains in the rain and
 *                  not under cover, snow accumulates below zero, a front pushes toward storm.
 *  -GTHazardTest   a weather front approaches and envelops the car, a radiation zone drains the
 *                  meter and the car; both damage parts slowly; dash lights follow.
 *  -GTLootTest     loot tables roll within their bounds and weights; a node pays from its table.
 *  -GTEnvTest      a conditions profile drives the environment stage: heat, dust and cold ramp
 *                  from performance to warning to damage with a readable window.
 *  -GTTourTest     M5 (FGTM5TestRunner): the tour's legs and rivals resolve, the standings draw
 *                  is deterministic and bounded, a photograph leg refuses the zone until the
 *                  picture (taken from range; the subject flees when approached), an endurance
 *                  leg over its limit is a did-not-finish, points and prize money accrue, the
 *                  tour ends with a final table and an ending line that survive the save.
 *  -GTTerrainTest  M6 (FGTM6TestRunner, on L_Leg03 after setup_m6_hide): a landscape under the
 *                  leg's actors, the surfaces where the spec paints them, a road with real grades
 *                  and no walls, relief off it, and the car drives the first stretch flat out.
 *  -GTHideShots    twelve off-screen pictures of The Hide (Saved/Screenshots/M6), the last the bog from
 *                  40 m above with the mud material's diagnostic ramp on, its sample pixels logged.
 *  -GTShotsFrom=N  with -GTHideShots: skip the leg's own pictures and start the shots run at step N
 *                  (12..17, the bog steps; Art/bog_shots.bat passes 12), the car teleported to the
 *                  route 10 m before the bog and settled first. The screenshot count expects the
 *                  pictures of the steps that ran.
 *  -GTDressingTest FGTDressingTestRunner, on L_OWToolkitTest (Art/dressing_toolkit_test.bat): the OW landscape
 *                  toolkit's roads, landscape material, 13 layers and 6 dressed biome volumes are present.
 *  -GTBiomeTest    FGTBiomeTestRunner, on L_DriveTest (Art/biome_test.bat): leg dressing LD1 + LD3 - the spec's
 *                  biome rules, the dressing exclusion boxes, the global wind, gt.Look.Dressing, no L3 cards.
 *  -GTVegTest      FGTVegTestRunner, on L_VegTest (Art/veg_test.bat): leg dressing LD5 - the car pushed through brush,
 *                  saplings and young trees (bend, resist, snap) and into a mature tree; -GTVegScratch with it on
 *                  L_GTDressScratch (veg_test.bat scratch): the index and a 100 m drive through the densest thicket.
 *  -GTRouteClearTest FGTRouteClearanceTestRunner, on L_Leg03 (Art/route_clear_test.bat): leg dressing LD7 - no dressing
 *                  in the swept 3 x 4 x 2 m corridor along the route and the alt routes, none within 5 m of the start,
 *                  the checkpoints, the zone or an interactable.
 */
UCLASS()
class GRANDTOUR_API AGTRunGameMode : public AGTDriveTestGameMode
{
	GENERATED_BODY()

public:
	AGTRunGameMode();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** Sets (or replaces) the leg; the start location is the player's car. Tests use it with a runtime leg. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void SetLeg(UGTLegDefinition* Leg);

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	AGTRunGameState* GetRunState() const;

	/** Enter / Start on the results screen: restarts the leg map for now. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void ContinueAfterLeg();

	/** Builds the result from the run state and both inventories, records it and freezes the car. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void FinishLeg();

	UPROPERTY(BlueprintReadOnly, Category = "GT|Run")
	int32 LegsFinished = 0;

private:
	void ResolveLeg();
	void ApplyStartWeather(const UGTLegDefinition* Leg);

	TUniquePtr<FGTM3TestRunner> M3Test;
	TUniquePtr<FGTM4TestRunner> M4Test;
	TUniquePtr<FGTM5TestRunner> M5Test;
	TUniquePtr<FGTM6TestRunner> M6Test;
	TUniquePtr<FGTProvingTestRunner> ProvingTest;
	TUniquePtr<FGTFordDiagRunner> FordDiag;   // diagnostic only (-GTFordDiag, Art/ford_diag.bat)
	TUniquePtr<FGTDressingTestRunner> DressingTest;   // OW landscape toolkit smoke test (-GTDressingTest)
	TUniquePtr<FGTBiomeTestRunner> BiomeTest;   // leg dressing LD1 + LD3 (-GTBiomeTest, Art/biome_test.bat)
	TUniquePtr<FGTVegTestRunner> VegTest;   // leg dressing LD5 (-GTVegTest, Art/veg_test.bat)
	TUniquePtr<FGTRouteClearanceTestRunner> RouteClearTest;   // leg dressing LD7 (-GTRouteClearTest, Art/route_clear_test.bat)
	TUniquePtr<FGTProvingShotsRunner> ProvingShots;   // L_Proving's pictures (-GTProvingShots, Art/proving_shots.bat), RIVERBED S2
	bool bLegResolved = false;
};
