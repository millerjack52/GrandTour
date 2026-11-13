#pragma once

#include "CoreMinimal.h"

class AActor;
class AGTPlayerController;
class UGTTerrainSpecAsset;
class UWorld;
struct FGTTerrainSpec;
struct FGTTerrainStation;

/**
 * The Proving Ground (L_Proving, 2026-09-19): the named stations of a map's terrain spec (FGTTerrainSpec::Stations),
 * what GTGoto does with them, and the help printed at BeginPlay. A map whose spec has no stations (every leg) gets
 * none of it. The spec is the level's AGTTerrainBuilder's asset, the one UGTMudSubsystem builds its patches from.
 */
namespace GTProving
{
	/** The level's terrain spec asset (its AGTTerrainBuilder's), or null. */
	GRANDTOUR_API const UGTTerrainSpecAsset* FindSpecAsset(UWorld* World);

	/** "pad forda fordb ..." */
	GRANDTOUR_API FString StationNames(const FGTTerrainSpec& Spec);

	/** The world ground (WorldStatic) under an XY, cm, the car and every pawn ignored. */
	GRANDTOUR_API bool GroundZ(UWorld* World, float XCm, float YCm, float& OutZ, const AActor* Ignore = nullptr);

	/** Puts the car on the station's landing point, upright, at rest, handbrake on; the player with it (seated, or on foot beside it). */
	GRANDTOUR_API bool Goto(AGTPlayerController* PC, const FString& Name, FString& OutMessage);

	/** The station names and the water / weather test cvars, on screen for Seconds and in the log, when the map has stations. */
	GRANDTOUR_API void ShowHelp(UWorld* World, float Seconds);

	/**
	 * RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): what the wheels read off the landscape, every StepCm over the
	 * spec's grid, inside and outside the mud patches' boxes. One trace down per point (WorldStatic, the physical material
	 * the wheels get); a stone, a post or a sheet in the way is ignored and the trace repeated, so every count is the
	 * landscape's own. Run by the ford diagnostic (L_Proving, 1 m) and the terrain test (the Hide, 2 m).
	 */
	struct FGTMudSurvey
	{
		float StepCm = 100.f;
		int32 Patches = 0;
		int32 Samples = 0;
		int32 Landscape = 0;
		int32 InBoxes = 0;
		int32 MudInside = 0;
		int32 BogInside = 0;
		int32 MudOutside = 0;
		int32 BogOutside = 0;
		FBox2D OutsideCm = FBox2D(ForceInit);
		float Seconds = 0.f;
		/** Where the soft samples outside the boxes lie: each Channel feature's line + its radius + 5 m, each box + 10 m, the rest. */
		TArray<FString> RegionNames;
		TArray<int32> RegionCounts;
		int32 Elsewhere = 0;
	};
	GRANDTOUR_API FGTMudSurvey SurveyMud(UWorld* World, const FGTTerrainSpec& Spec, float StepCm, const AActor* Ignore = nullptr);
	GRANDTOUR_API FString DescribeMudSurvey(const FGTMudSurvey& Survey);
}
