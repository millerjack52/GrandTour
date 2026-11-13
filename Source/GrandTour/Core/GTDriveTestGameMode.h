#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "Core/GTM2TestRunner.h"
#include "GTDriveTestGameMode.generated.h"

class AGTCarPawn;
class UChaosWheeledVehicleMovementComponent;

/**
 * Test game mode: spawns the player in a GTCarPawn. Two headless self-tests, picked by command
 * line, hold full throttle, log GTDRIVETEST lines and quit:
 *  -GTDriveTest    8 s on the flat map; pass = moved more than 5 m and stayed on the ground, and the chase camera
 *                  toggled at 4 s puts the view behind and above the car, toggled back it is at the driver's eye.
 *  -GTSurfaceTest  30 s on L_TestTrack's surface lanes (tarmac, dirt, mud, snow, then a wall);
 *                  pass = reached the snow lane, mud slowed the car, the wall registered damage,
 *                  fuel was burned.
 *  -GTMudTest      teleports the car onto the mud lane, sits 4 s, then full throttle for 8 s;
 *                  pass = pulls away to at least 400 cm/s and 8 m without staying bogged.
 *  -GTDrivetrainTest  L_DriveTest (driving feel stage 4): the left wheels on ice, open diffs barely move the car
 *                  and the lock drives it; a standing start on a 35 % slope high range cannot make and low range
 *                  does; the brake held at a stop reverses; the gearbox changes up.
 *  -GTGripTest     skid pad on L_DriveTest (driving feel stage 1): a tarmac pad and a dirt pad, the car run up
 *                  to 65 km/h then held at full lock; pass = the mean lateral g on tarmac ~0.95 and on dirt
 *                  ~0.62 with the front tyres past their peak slip.
 *  -GTRoughTest    teleports the car before the rough patch and drives it at full throttle,
 *                  sampling the chassis' vertical acceleration every frame; reports the peak in g
 *                  (jolt) and, after the last ridge, how long the body keeps bouncing (float).
 *  -GTTrackTest    16 s down the surface lanes; pass = no track cells while on tarmac, ruts under
 *                  both wheel paths in mud and snow and none beside them, the window followed the
 *                  car, and (with a GPU) the render target agrees with the CPU grid.
 *  -GTBodyTest     teleports the car 35 m before the wall and drives into it; pass = the panels
 *                  replaced the skeletal body, the hit filled the dent texture, the front region
 *                  died and its panels came off as physics props while the rest stayed on.
 *  -GTBodyStateTest 16 s down the surface lanes; pass = clean on tarmac, after mud the arches are
 *                  dirtier than the sides and the sides than the roof and the body is wet, the
 *                  windscreen caught some, and the snow lane put snow on the body.
 *  -GTSprayTest    16 s down the surface lanes; pass = no spray on tarmac, dust in the dirt lane,
 *                  mud blobs in the mud lane, snow in the snow lane, pools never exceeded; the
 *                  synth's tyre cutoff drops from tarmac to mud and a rendered block has signal.
 *  -GTOnFootTest   M2: get out, walk (head bob on/off), harvest, field repair, boot transfer,
 *                  exposure in a hazard, get back in (FGTM2TestRunner).
 *  -GTWinchTest    M2: hook, tether, attach, reel, snap against a wall, weak anchor tears out.
 * The controller is AGTPlayerController (possession swap) and the HUD the greybox AGTHUD.
 */
UCLASS()
class GRANDTOUR_API AGTDriveTestGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AGTDriveTestGameMode();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	struct FSegment
	{
		FString Name;
		float XStart = 0.f;
		float XEnd = 0.f;
		double Time = 0.0;
		float EntrySpeed = -1.f;
		float ExitSpeed = -1.f;
		float MaxSinkage = 0.f;
		bool bBogged = false;
	};

	struct FGripRun
	{
		FString Name;
		FVector PadCentre = FVector::ZeroVector;
		float EntrySpeed = 0.f;
		float SumLatG = 0.f;
		float SumSpeed = 0.f;
		float SumTime = 0.f;
		float MeanLatG = 0.f;
		float MeanSpeed = 0.f;
		float MinSpeed = 1.e9f;
		float PeakLatG = 0.f;
		float MaxSlipDeg = 0.f;
	};

	void SelfTestTick();
	FSegment* FindSegment(float X);
	void GripSelfTestTick(AGTCarPawn& Car, UChaosWheeledVehicleMovementComponent& Move);
	void GripFrameTick(float DeltaSeconds);

protected:
	void FinishTest(bool bPass, const FString& Summary);

private:

	TUniquePtr<FGTM2TestRunner> M2Test;
	FTimerHandle SelfTestTimer;
	TArray<FSegment> Segments;
	bool bSurfaceTest = false;
	bool bMudTest = false;
	bool bRoughTest = false;
	bool bTrackTest = false;
	bool bBodyTest = false;
	bool bBodyStateTest = false;
	bool bSprayTest = false;
	bool bGripTest = false;
	bool bFlatTest = false;
	bool bDrivetrainTest = false;
	int32 DrivetrainPhase = 0;
	float DrivetrainPhaseTime = 0.f;
	FVector DrivetrainStart = FVector::ZeroVector;
	float SplitOpenCm = -1.f;
	float SplitLockedCm = -1.f;
	float RampHighM = -1.f;
	float RampLowM = -1.f;
	float RampPeakM = 0.f;
	float ReverseSpeed = 0.f;
	int32 GearsSeen = 0;
	void DrivetrainSelfTestTick(AGTCarPawn& Car, UChaosWheeledVehicleMovementComponent& Move);
	float ChaseBehind = 0.f;
	float ChaseAbove = 0.f;
	bool bChaseOk = false;
	float DriverBack = -1.f;
	bool bDriverBackOk = false;
	TArray<FGripRun> GripRuns;
	int32 GripRun = -1;
	int32 GripPhase = 0;         // 0 settle on the pad, 1 straight to speed, 2 the turn settles, 3 measure, 4 done
	float GripPhaseTime = 0.f;
	float GripEntrySpeed = 1650.f;   // cm/s: 60 km/h, where the curve leaves 12 deg of lock and full lock asks ~2 g
	bool bSprayCleanOnTarmac = true;
	bool bPoolExceeded = false;
	int32 MaxDustInDirt = 0;
	int32 MaxMudInMud = 0;
	int32 MaxSnowInSnow = 0;
	float TarmacCutoff = -1.f;
	float MudCutoff = -1.f;
	float TarmacRms = -1.f;
	float MudRms = -1.f;
	bool bStateCleanOnTarmac = true;
	float MudExitArchFL = -1.f;
	float MudExitSideL = -1.f;
	float MudExitRoof = -1.f;
	float MudExitWetness = -1.f;
	float WallStopTime = -1.f;
	bool bTarmacClean = true;
	float SelfTestDuration = 8.f;
	float MudSettleSeconds = 4.f;
	bool bBoggedEver = false;
	float MudMaxSinkage = 0.f;
	float PeakVerticalG = 0.f;        // over a 50 ms window, what a body feels
	float PeakPitchRate = 0.f;
	float PeakStepDeltaVz = 0.f;      // largest single-frame vertical velocity change, cm/s
	float SumG2Time = 0.f;            // integral of g^2 over the patch, for the RMS
	float PatchTime = 0.f;
	float PostPatchTime = -1.f;       // seconds since the car cleared the last ridge; -1 before
	float SettleTime = -1.f;          // seconds after the patch until the body stopped bouncing
	float QuietTime = 0.f;
	float PeakVzSinceCrossing = 0.f;
	float LastVzSign = 0.f;
	int32 BouncesAfterPatch = 0;
	float LastVerticalVelocity = 0.f;
	float LastPitch = 0.f;
	float WindowStartVz = 0.f;
	float WindowStartPitch = 0.f;
	float WindowTime = 0.f;
	bool bHaveLastSample = false;
	float SelfTestElapsed = 0.f;
	float SelfTestMaxSpeed = 0.f;
	FVector SelfTestStart = FVector::ZeroVector;
	bool bSelfTestStarted = false;
	int32 CurrentSegment = -1;
};
