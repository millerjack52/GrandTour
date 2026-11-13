#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Terrain/GTTerrainGenerator.h"
#include "GTReliefLibrary.generated.h"

/**
 * Ground relief GR1 (docs/GROUND_RELIEF_PLAN.md): the strips' setup scripts' helpers. VaryGrassTransforms passes a grass or
 * tussock placement through the spec's FGTGrassVariation (GTTerrain::VaryGrass); ReliefReportJson measures a spec's relief for
 * the setup report and the relief test (the route's grade and cross-slope, the hummock field's statistics). No timing.
 */
UCLASS()
class GRANDTOUR_API UGTReliefLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** The placement through Spec.Grass (world cm transforms); OutStatsJson: in, bare, out, crest companions, height-scale range, most lean. */
	UFUNCTION(BlueprintCallable, Category = "GT|Terrain|Relief")
	static TArray<FTransform> VaryGrassTransforms(const FGTTerrainSpec& Spec, const TArray<FTransform>& Transforms, bool bTussock, FString& OutStatsJson);

	/** The hummocks HeightM adds at a world point, cm (masked). */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain|Relief")
	static float HummockHeightCm(const FGTTerrainSpec& Spec, float XCm, float YCm);

	/**
	 * The spec's relief as JSON: the main route's longitudinal grade over 3 m and cross-slope over 1.6 m (p50, p95, max, per cent,
	 * every 0.5 m), and the hummock field over the grid (the stamped count, the mounds' nearest-neighbour CV, the radial
	 * pair-correlation's highest bin beyond the mean nearest-neighbour distance, the field's steepest slope alone at 0.25 m and
	 * the finished ground's at the landscape's own 1 m on hummock ground).
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Terrain|Relief")
	static FString ReliefReportJson(const FGTTerrainSpec& Spec);
};

/** GR1: the relief statistics behind ReliefReportJson (the relief test reads them directly). */
struct FGTReliefStats
{
	float GradeP50 = 0.f;
	float GradeP95 = 0.f;
	float GradeMax = 0.f;
	float CrossP50 = 0.f;
	float CrossP95 = 0.f;
	float CrossMax = 0.f;
	int32 RouteSamples = 0;
	float GradeP95OffFord = 0.f;  // the same away from Ford sections (3 m past their ends)
	float CrossP95OffFord = 0.f;
	int32 HummocksRaw = 0;        // every mound centre in the grid
	int32 HummocksStamped = 0;    // with the mask at its centre over 0.5
	float Density = 0.f;  // raw centres per 100 m^2 of the grid
	float NearestMeanM = 0.f;
	float NearestCV = 0.f;        // the raw process, the border cells left out as references
	float StampedNearestCV = 0.f;
	float PairPeak = 0.f;         // the highest g(r) bin beyond NearestMeanM
	float PairPeakAtM = 0.f;
	TArray<float> PairBins;       // g(r) per 0.5 m bin from 0 to 15 m
	float FieldSlopeMaxDeg = 0.f; // the hummock field alone, 0.25 m differences
	float GroundSlopeMaxDeg = 0.f;   // the finished ground at 1 m, where the hummock mask is over 0.5
	float GroundSlopeP99Deg = 0.f;
	float HummockMaxM = 0.f;
};

namespace GTRelief
{
	GRANDTOUR_API FGTReliefStats Measure(const FGTTerrainSpec& Spec);
	GRANDTOUR_API FString ToJson(const FGTReliefStats& Stats);
}
