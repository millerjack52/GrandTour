#pragma once

#include "CoreMinimal.h"

class AGTCarPawn;
class UGTVegetationSubsystem;
class UWorld;

/**
 * Leg dressing LD5 (docs/LEG_DRESSING_PLAN.md, the LD5 v2 pass list): the vegetation physics test. -GTVegTest on
 * /Game/GrandTour/Test/L_VegTest (Art/veg_test.bat, built by Art/dressing/setup_veg_test.bat). Driven by
 * AGTRunGameMode::Tick. The lanes come from the map: the brush patch, the sapling row and the young-tree row from
 * UGTVegetationSubsystem's index, the mature tree from the GTVeg.Solid ISM on the GTBiome.Test actor (its trunk capsule).
 * Each case teleports the car onto its lane at least 15 m (4.5 s) before the vegetation with the case's speed already on
 * the wheels. The driver holds that speed on the approach (a PI on the throttle, the steering on the lane line); at the
 * first contact the pedal locks at the hold's mean over the 2 s before it (the "steady pedal"), unless the case says
 * full throttle. Each soft case starts on fresh plants (UGTVegetationSubsystem::Reindex restores every snapped one):
 *  1. brush (the 30 x 20 m thicket-core patch) at 40 km/h, steady pedal: at least 50 % of the instances the car touched
 *     bend beyond 20 deg in contact; all back under 5 deg within 6 s of their last contact; the speed 20 m after the
 *     first contact 15-60 % below the speed at it (never 20 m on: 100 %);
 *  1b. (information) the same patch at full throttle from the first contact;
 *  2. saplings (a row across the lane) at 8 km/h, steady pedal: never held (lowest speed from the first contact to the row's end >= 2 km/h) and
 *     reaches the row's end; at 30 km/h, steady pedal: at least one impact snap;
 *  3. young trees at 10 km/h, steady pedal: held (under 1 m/s within 3 s of the first contact, no snap before); then
 *     full throttle, and a tree snaps within 4 s; at 45 km/h, steady pedal: an impact snap;
 *  4. the mature tree at 20 km/h (the hold throughout): under 1 m/s within 1 s of contact (the front of the car's body
 *     box within 10 cm of the trunk capsule), the car's centre of mass never nearer the trunk axis than the trunk radius;
 *  5. clean-up: 10 s after the last contact the active set is 0 and at most 24 debris actors exist;
 *  6. with a GPU only (veg_test.bat gpu): 3 s parked 5 m short of the patch looking at it and the frame over the patch at
 *     30 km/h (the hold), gt.Look.Dressing 1 and then 0, each with the game / render / GPU thread times; tentative bands
 *     (reported, never failed): pushing at most +3.0 ms GPU over dressing 0, parked and viewing at most +2.0 ms. A GPU
 *     run first parks the car 15 m before each lane until no shader job is left and 30 frames in a row take under 50 ms
 *     (the first frames compile shaders at a few fps, and the physics, capped per step, then crawls against world time).
 * Every number is logged beside its band (GTDRIVETEST veg lines).
 * -GTVegScratch (veg_test.bat scratch, on L_GTDressScratch): information only - the soft instances indexed per class,
 * the component classes and the hash cells; then the car driven 100 m in a straight line at 30 km/h through the
 * densest soft vegetation with no solid instance within 3.5 m of the line (the hold throughout, a 3.5 s run-up), and
 * the distance made in 40 s, the contacts, bends, snaps and the subsystem's per-frame work logged.
 * -GTVegHide with -GTVegScratch (Art/dressing/veg_hide_drive.bat, on L_Leg03, leg dressing LD7): the same drive through the
 * dense soft vegetation nearest the route (4 m cells whose 3 x 3 block holds at least half the densest block's soft
 * pivots, taken in order of their distance to the route), gt.Look.Dressing 1 and then 0 over the same line, each pass's
 * frame and GPU mean over the 100 m and the subsystem's per-frame work (information; the LD7 budget is 0.3 ms). A GPU
 * run parks the car at the line's start until no shader job is left and 30 frames in a row take under 50 ms first.
 */
class FGTVegTestRunner
{
public:
	explicit FGTVegTestRunner(UWorld* InWorld);

	/** True when finished; bOutPass and OutSummary carry the verdict. */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	enum class EStep : uint8
	{
		Wait,
		Warmup,
		Settle,
		Brush40,
		Brush40Full,
		Sapling8,
		Sapling30,
		Young10,
		Young45,
		Mature20,
		Cleanup,
		GpuView,
		GpuOn,
		GpuView0,
		GpuOff,
		ScratchSettle,
		ScratchDrive,
		Done,
	};

	struct FLine
	{
		FVector2D Origin = FVector2D::ZeroVector;   // cm
		FVector2D Dir = FVector2D(1.0, 0.0);
	};

	bool FindLanes();
	bool PickScratchLine();
	void Log(const FString& Text) const;
	void Next(EStep Step);
	float GroundZ(const FVector2D& At) const;
	void Teleport(const FVector2D& At, const FVector2D& Dir, float SpeedMs);
	void Park();
	void HoldSpeed(float TargetMs, const FLine& Line, float DeltaSeconds);
	float SpeedMs() const;
	float AlongLine(const FLine& Line) const;
	/** The pedal: the speed hold (the approach, cases 4 and 6, the scratch drive), locked at the first contact, or floored. */
	enum class EPedal : uint8
	{
		Hold,
		Steady,
		Full,
	};

	/**
	 * Starts a driving case: the car TargetMs-fast on Line, RunUpS (at least 15 m) ahead of the vegetation that starts at
	 * ObstacleAlongCm, held at that speed until the first contact and then driven with AtContact.
	 */
	void BeginCase(const FLine& Line, float ObstacleAlongCm, float TargetMs, EPedal AtContact, float RunUpS = 4.5f);
	/** Per-frame sampling of a soft-vegetation case: contact, entry speed, speed 20 m on, lowest speed, held time. */
	void SampleSoft();
	bool CaseDone(float EndAlongCm, float SecondsAfterContact, float Timeout) const;
	void EndCase();
	void TickCase(float DeltaSeconds);
	void Finish(bool& bOutPass, FString& OutSummary);

	TWeakObjectPtr<UWorld> World;
	TWeakObjectPtr<AGTCarPawn> Car;
	TWeakObjectPtr<UGTVegetationSubsystem> Veg;
	bool bScratch = false;
	bool bGpu = false;
	// The driver.
	EPedal Pedal = EPedal::Hold;
	EPedal PedalAtContact = EPedal::Hold;
	float LastThrottle = 0.f;
	float PedalLock = -1.f;                    // the steady pedal (the hold's mean over the 2 s before the first contact)
	TArray<TPair<double, float>> ThrottleLog;   // the approach: world time, the hold's throttle
	EStep Step = EStep::Wait;
	float StepTime = 0.f;
	float Elapsed = 0.f;
	int32 Ticks = 0;
	bool bStepStarted = false;
	TArray<FString> Failures;
	TArray<FString> Results;

	// The lanes (cm): the line each runs along and where its vegetation starts and ends along it.
	FLine BrushLane, SaplingLane, YoungLane, MatureLane;
	float BrushStart = 0.f, BrushEnd = 0.f, SaplingStart = 0.f, SaplingEnd = 0.f, YoungStart = 0.f, YoungEnd = 0.f;
	FVector2D TrunkAxis = FVector2D::ZeroVector;
	float TrunkRadiusCm = 0.f;
	float RestOffsetCm = 60.f;   // the car's origin above the ground at rest (measured in Settle)
	FVector2D ParkAt = FVector2D::ZeroVector;

	// The case in progress.
	FLine Lane;
	float TargetSpeedMs = 0.f;
	float HoldIntegral = 0.f;
	double CaseStart = 0.0;
	bool bContact = false;
	double ContactTime = -1.0;
	float EntrySpeedMs = 0.f;
	float EntryAlongCm = 0.f;
	float SpeedAt20Ms = -1.f;
	float MinSpeedInContactMs = 1.e9f;
	double HeldTime = -1.0;
	float MinAxisDistanceCm = 1.e9f;
	bool bParked = false;
	double ParkedTime = -1.0;
	double LastContactAll = -1.0;
	bool bRecoveryChecked = false;
	int32 TiltedAt6s = -1;
	float MinSpeedToEndMs = 1.e9f;     // case 2: from the first contact to the row's end
	bool bReachedEnd = false;
	double ReachedEndTime = -1.0;
	double FullThrottleTime = -1.0;    // case 3: when the pedal went down after the hold
	int32 SnapsBeforeFull = 0;
	double FirstSnapAfterFull = -1.0;

	// GPU runs: a warm-up at each lane (shader jobs done, frames steady) before case 1.
	int32 WarmSpot = 0;
	double WarmSpotStartReal = 0.0;
	int32 FastFrames = 0;
	void WarmTeleport();

	// Case 6 (GPU): frame ms over the patch.
	double FrameMsSum = 0.0;
	float FrameMsMax = 0.f;
	int32 FrameCount = 0;
	double GameMsSum = 0.0, RenderMsSum = 0.0, GpuMsSum = 0.0;   // the engine's own per-thread times over the same frames
	void SampleFrame();
	FString FrameLine() const;
	float ViewFrameMs[2] = { -1.f, -1.f }, ViewGpuMs[2] = { -1.f, -1.f };   // [dressing 0, dressing 1]
	float PushFrameMs[2] = { -1.f, -1.f }, PushGpuMs[2] = { -1.f, -1.f };

	// Scratch probe.
	FLine ScratchLine;
	float ScratchStartAlong = 0.f;
	int32 ScratchScore = 0;
	float ScratchMinSpeed = 1.e9f;
	FVector ScratchLastPos = FVector::ZeroVector;
	float ScratchPathCm = 0.f;
	// LD7: the Hide's thicket drive (-GTVegHide).
	bool bHide = false;
	int32 HidePass = 1;               // gt.Look.Dressing of the pass being driven: 1, then 0
	float HideRouteDistM = -1.f;      // the chosen block's centre from the route
	float HideFrameMs[2] = { -1.f, -1.f }, HideGpuMs[2] = { -1.f, -1.f }, HideMadeM[2] = { -1.f, -1.f };
	FString HideWork[2];
	bool bHideWarm = false;
};
