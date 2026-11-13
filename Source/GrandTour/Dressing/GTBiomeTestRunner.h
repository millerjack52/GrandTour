#pragma once

#include "CoreMinimal.h"

class AActor;
class UWorld;
struct FGTTerrainSpec;

/**
 * Leg dressing LD1 + LD3 (docs/LEG_DRESSING_PLAN.md): the headless biome check. -GTBiomeTest on any small test map
 * (Art/biome_test.bat runs it on /Game/GrandTour/Test/L_DriveTest, -game -NullRHI). Driven by AGTRunGameMode::Tick,
 * one phase a tick so the log shows each one's time:
 *  1. the no-biome hashes: GTTerrain::GenerateHash of HideSpec() and ProvingSpec() equal the constants recorded before
 *     the biome rules went in, so a spec without biomes generates exactly what it did;
 *  2. the Hide spec with the D2 palette (section 5; built here, not pushed to DA_Terrain_Hide - LD6 does that): the heights
 *     and layers 0-3 and 5 byte-identical to the no-biome grid, the biome bytes adding up to the old Scrub byte at every
 *     vertex (+-1), every biome layer on more than 0 vertices (the counts logged), every vertex summing to 255; LD1b: the
 *     dominant shares of the off-road land in range (Forest + ForestFir 22-38 %, Thicket 1-9 %) and Thicket's ring /
 *     riparian split logged (the grid again with the section rule's layer renamed), the riparian rule dominant on >= 1000
 *     vertices (it runs before the forest rules, the rule order revised after LD1b);
 *  3. LayerAt still 0-5 and unchanged by the biomes at 4000 points, BiomeAt agreeing with the grid's dominant biome;
 *  4. AGTTerrainDressing places its L3 cards on the Proving spec and none on it with the palette;
 *  5. AGTDressingExclusion::RebuildFromSpec(DA_Terrain_Hide): the box count and the route length covered, every box
 *     QueryOnly, ignoring all channels, hidden in game, the actor editor-only and tagged OWDressing.Exclude;
 *  6. the weather writes MPC_GlobalWind: Clear's WindStrength maps to the collection's default WindIntensity;
 *  7. gt.Look.Dressing 0 hides a GTBiome.* probe with its collision off and sets grass.Enable 0, 1 puts back each probe's
 *     own state (a probe hidden by design stays hidden).
 */
class FGTBiomeTestRunner
{
public:
	explicit FGTBiomeTestRunner(UWorld* InWorld);

	/** True when finished; bOutPass and OutSummary carry the verdict (the failing checks on FAIL). */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

	/** The D2 palette (LEG_DRESSING_PLAN section 5) as biome rules on a spec: Scree, Alpine, Thicket (riparian), ForestFir, Forest, Thicket (ring), MeadowLush, MeadowDry, fallback Meadow. */
	static void AddD2Palette(FGTTerrainSpec& Spec);
	/** GTTerrain::HideSpec() with its biome rules and fallback cleared (LD6: HideSpec() carries the D2 palette). */
	static FGTTerrainSpec HideSpecNoBiomes();

private:
	void PhaseHashes();
	void PhaseBiomes();
	void PhaseLayerAt();
	void PhaseCards();
	void PhaseExclusion();
	void PhaseWind();
	void PhaseDressingOff();
	void PhaseDressingOn();
	void PhaseDressingRestored();

	TWeakObjectPtr<UWorld> World;
	float Elapsed = 0.f;
	int32 Ticks = 0;
	int32 Phase = 0;
	int32 WaitTicks = 0;
	TArray<FString> Failures;
	TArray<FString> Notes;

	// The Hide grid without biomes (phase 1) and with the palette (phase 2), kept for the comparisons.
	TArray<uint16> PlainHeights;
	TArray<TArray<uint8>> PlainWeights;
	TArray<TArray<uint8>> BiomeWeights;
	TArray<FName> BiomeNames;

	TWeakObjectPtr<AActor> ProbeShown;
	TWeakObjectPtr<AActor> ProbeHidden;
};
