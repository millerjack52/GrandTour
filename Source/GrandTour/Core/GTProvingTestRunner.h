#pragma once

#include "CoreMinimal.h"

class AGTCarPawn;
class AGTPlayerController;
class UWorld;

/**
 * The Proving Ground's smoke test (-GTProvingTest on L_Proving after Art/setup_m6_proving.bat; Art/proving_test.bat).
 * Driven by AGTRunGameMode::Tick. Step 0: the map - a landscape, the spec asset from the level's builder, one water sheet
 * per Ford section, one mud patch per Mud section, the dressing's rocks, track stones and rally posts as the generator
 * places them, four winch posts per bog and per deep ford. Step 1: the car on the pad, at rest 3 s after it spawned.
 * Then every station of the spec: GTGoto it, 2 s, the car at rest, upright and on the ground, and the station's own
 * reading ahead (a ford's water, the bog's patch, a ramp's grade, the slope's cross slope, the section kind).
 */
class FGTProvingTestRunner
{
public:
	explicit FGTProvingTestRunner(UWorld* InWorld);

	/** True when finished; bOutPass and OutSummary are set then. */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	void Log(const FString& Line) const;
	bool CheckMap();
	bool CheckStation(int32 Index);
	bool CarAtRest(float& OutSpeedCmS, float& OutUpZ, float& OutAboveGroundCm) const;

	TWeakObjectPtr<UWorld> World;
	TWeakObjectPtr<AGTPlayerController> PC;
	TWeakObjectPtr<AGTCarPawn> Car;
	float Elapsed = 0.f;
	float StepTime = 0.f;
	int32 Step = 0;
	int32 Station = 0;
	bool bGone = false;
	TArray<FString> Failures;
	TArray<FString> Readings;
};
