#pragma once

#include "CoreMinimal.h"
#include "Terrain/GTTerrainGenerator.h"

class ACameraActor;
class AGTCarPawn;
class AGTTerrainDressing;
class AGTPlayerCharacter;
class AGTPlayerController;
class AGTRunGameState;
class UWorld;

enum class EGTM6Test : uint8
{
	/** The Hide's ground on L_Leg03: a landscape under everything, the leg actors on it, the surfaces where the spec paints them, a road with real grades, the car drives it. */
	Terrain,
	/** Pictures of The Hide for the user (L_Leg03, -RenderOffScreen): the valley from the start, the climb, the dell with the bear, the crossing, an overview. */
	HideShots,
	/** Water stage WS1 (docs/WATER_PLAN.md): the ford's simulated surface on its own - the current, a ring and its reflection, the solver's cost, the mesh and the texture. */
	Water
};

/**
 * Scripted headless checks and pictures for M6's first terrain (The Hide), driven from
 * AGTRunGameMode::Tick on L_Leg03 after Art/setup_m6_hide.bat has built it. Every step logs a
 * GTDRIVETEST m6 line. The terrain test reads the ground with traces (the landscape's collision
 * and its per-layer physical materials are what the wheels see) and compares with the spec the
 * map was generated from; the pictures step waits for the shaders and frames five views.
 */
class FGTM6TestRunner
{
public:
	FGTM6TestRunner(UWorld* InWorld, EGTM6Test InKind);

	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	bool Setup();
	void TickTerrain(float DeltaSeconds);
	void TickShots(float DeltaSeconds);
	/** Water stage WS1: the ford's field on its own (Art/water_test.bat). WS2 adds the sources to it. */
	void TickWater(float DeltaSeconds);
	/** WS2: the sd of the field's surface over the middle 10 x 10 m, cm, about that patch's own mean (so a head gradient is not read as roughness). */
	float WaterMiddleSdCm(const class AGTWaterSheet& Sheet, float HalfSpanCm = 500.f) const;
	/** WS2: sets gt.Water.Wind (the wind source) and reports what it was. */
	void SetWaterWind(float Scale);
	/** WS1: what the field says about the water at a world XY, against the ground the traces and the spec give (a log line). */
	FString WaterAt(const FVector2D& XY) const;
	/** The sheet over the spec's first Ford section, or the first registered sheet. */
	class AGTWaterSheet* FordSheet() const;
	void Next();
	void Finish(bool bPass, const FString& Summary);
	void Fail(const FString& Why) { Finish(false, Why); }
	void Log(const FString& Line) const;
	bool StepTimedOut(float Seconds, const TCHAR* What);
	/** Traces straight down through a world XY: the ground's Z, the actor hit and the surface tag there. */
	bool Ground(float XCm, float YCm, float& OutZ, AActor*& OutActor, FName& OutSurface) const;
	void TeleportCar(const FVector& Location, float Yaw);
	void Throttle(bool bOn);
	/** Throttle without the handbrake (the bend runs hold a speed with it). */
	void Drive(float ThrottleIn);
	/** Logs, per material slot of the car's skeletal mesh, whether the triangles wind outward and whether the stored normals agree (the wheels against the body). */
	void ReportWinding();
	/** Driving feel stage 1: the rally stretch's sharpest bend, entered flat out or held at a sane speed, the car following the route. */
	void TickBend(bool bFast);
	/** Steers at the route point about a second ahead, LateralM to its left (positive) or right, at the given throttle. */
	void Follow(float LateralM, float ThrottleIn);
	/** Stage 3: the bog at 30 km/h down its middle (the car stops in it, sunk), or crawled along its edge in low range with the lock (gets through). */
	void TickBog(bool bShallow, float DeltaSeconds);
	/** The second bog (2026-09-15): stopped dead in the deep band, a locked low-range crawl pulls out forward, then reverses into its own ruts. */
	void TickBogEscape(float DeltaSeconds);
	/** Stage A of the mud plan: the field under the escape's forward pass has ruts to the sinkage, ridges beside them and tracks; the reverse pass down them lowered less. */
	void TickMudField();
	void SampleMud();
	/** Stage C of the mud plan (the physics reads the field): back at the escape's start, a second locked low-range pass down the first pass's ruts (to 6 m sooner than the first), then an exit steered 30 degrees left of the ruts (to 6 m later than the pass down them, but at least 3 m), then the same exit from 8 m along with the rut hold off, logged beside it. */
	void TickRutPasses(float DeltaSeconds);
	/** Steers at the escape's recorded path point about 4 m ahead (behind, in reverse: the rear goes the way the wheel is turned). */
	void SteerAlongEscapePath(bool bBackward);
	/** The wheels' sinkage, rut read, climb, cross-slope, drag and grip, and the belly channel, for a log line. */
	FString TractionLine() const;
	struct FPassStats
	{
		float DistM = 0.f;        // 2D metres from where the pass began
		float Time = 0.f;
		float TimeTo6M = -1.f;
		float MaxSpeed = 0.f;
		float RutSum = 0.f;       // time-weighted sums (divide by Time): the mean rut read, the mean climb, the mean belly channel
		float ClimbSum = 0.f;
		float ChannelSum = 0.f;
		float HeadingSum = 0.f;   // the mean unsigned heading off the pass's start yaw, degrees (the ruts' line)
		float PeakClimb = 0.f;
	};
	void AccumulatePass(FPassStats& Pass, float DeltaSeconds, float Speed, const FVector& From);
	/** Stage 3: the ford at 20 km/h in low range (through, slowed by the water), or with the water raised 70 cm (the engine floods and the car stops in it). */
	void TickFord(bool bRaised, float DeltaSeconds);
	/** Water stage W1: the car parked in the ford with the engine idling, as built (the current must not move it) or raised 70 cm (the current must carry it downstream). W2 adds the wheel load and, raised, the float. */
	void TickFordCurrent(bool bRaised, float DeltaSeconds);
	/** Water stage W2: from the floating car of step 16, the winch attached to Post_Ford and reeled in until the car is at the post or out of the water. */
	void TickFordWinch(float DeltaSeconds);
	/** The first Ford section of the spec. */
	bool FindFord(float& OutStartM, float& OutEndM) const;
	/** W1's pictures: the screen box of a set of world points, logged as a fordbox line for Art/tools/sample_ford.ps1. */
	void LogFordBox(const TCHAR* Picture, const TCHAR* Name, const TArray<FVector>& Points);
	/** WS1's picture: a line across the water logged as a fordline for the sampler's crest count. */
	void LogFordLine(const TCHAR* Picture, const TCHAR* Name, const FVector& From, const FVector& To);
	/** Stage 2: the rally stretch's first crest taken at 90 km/h flat out: all four wheels leave the ground for a while. */
	void TickCrest(float DeltaSeconds);
	/** Stage 2: the track held at 40 km/h: its bumps, ruts, water bars and stones shake the car (RMS vertical g over 50 ms windows). */
	void TickTrackRun(float DeltaSeconds);
	/** Stage 2: the car dropped straddling the rally road's edge on the ditch side: the verge pulls it in, rolled, the outer wheels lower. */
	void TickVerge(float DeltaSeconds);
	void ShowFromCamera(const FVector& Location, const FRotator& Rotation);
	void ShowFromGround(float XCm, float YCm, float EyeCm, const FVector& LookAt);
	void RequestShot(const TCHAR* Name);
	int32 PendingCompileJobs() const;

	TWeakObjectPtr<UWorld> World;
	EGTM6Test Kind;
	bool bDone = false;
	bool bPass = false;
	FString Summary;
	int32 Step = -1;
	float StepTime = 0.f;
	float Elapsed = 0.f;
	bool bStepStarted = false;

	TWeakObjectPtr<AGTPlayerController> PC;
	TWeakObjectPtr<AGTCarPawn> Car;
	TWeakObjectPtr<AGTRunGameState> State;
	TWeakObjectPtr<AGTTerrainDressing> Dressing;
	FGTTerrainSpec Spec;

	// stage 2 runs: the crest, the track, the verge
	float CrestArcM = 0.f;
	float AirTime = 0.f;
	float LongestAirTime = 0.f;
	float CrestSpeed = 0.f;
	bool bCrestFlies = false;
	FString CrestLine;
	float WindowTime = 0.f;
	float WindowStartVz = 0.f;
	float SumG2Time = 0.f;
	float RunTime = 0.f;
	float PeakG = 0.f;
	float TrackFromM = 0.f;
	float TrackRmsG = 0.f;
	bool bTrackRough = false;
	FString TrackLine;
	float VergeSide = 1.f;
	float VergeArcM = 0.f;
	bool bVergePulls = false;
	FString VergeLine;

	// terrain
	bool bLandscape = false;
	bool bActorsOnGround = false;
	bool bSurfacesOk = false;
	bool bMudSurveyOk = false;   // RIVERBED S2 (2026-09-23): no Mud or Bog on the landscape outside the mud patches' boxes
	bool bGradesOk = false;
	bool bRelief = false;
	float MaxGradeSeen = 0.f;
	float RiseSeen = 0.f;
	float ReliefSeen = 0.f;
	FString SurfaceLine;
	FString SectionsLine;
	// bend runs
	float BendArcM = 0.f;
	float BendEntrySpeed = 0.f;
	float BendMaxBeyondM = -1000.f;   // furthest past the road's half width (negative: stayed on it)
	float BendMaxOffM = 0.f;
	float BendPeakLatG = 0.f;
	float BendMaxSlipDeg = 0.f;
	bool bBendFastOff = false;
	bool bBendSlowOn = false;
	FString BendLine;
	// bog and ford runs
	float SectionStartM = 0.f;
	float SectionEndM = 0.f;
	float RunStoppedTime = 0.f;
	float RunFirmClearanceCm = -1.f;
	float RunMaxSink = 0.f;
	float RunMaxWaterM = 0.f;
	float RunMinSpeed = 1.e9f;
	bool bBogStops = false;
	bool bBogSinks = false;
	bool bBogEscapes = false;
	bool bBogReverses = false;
	// the mud field (docs/MUD_DEFORMATION_PLAN.md stage A): wheel contacts sampled during the escape's forward pass
	struct FMudSample
	{
		FVector2D Contact = FVector2D::ZeroVector;
		float SinkCm = 0.f;
		float WidthCm = 25.f;
		FVector2D Outward = FVector2D::ZeroVector;
		float RidgeCm = -1.e9f;   // the highest point 5 cm outward of the tyre's edge to the far side of the ridge band (stage I: 90 cm, 40 before) when the forward pass ended (later passes cut ridges)
	};
	TArray<FMudSample> MudSamples;
	float MudSampleTime = 0.f;
	double MudLoweredAtForward = 0.0;
	double MudLoweredAtReverse = 0.0;
	float MudLoweredForwardPerM = -1.f;
	float MudLoweredReversePerM = -1.f;
	float MudFrontAtForward = 0.f;
	float MudRearAtForward = 0.f;
	float MudLoweredFrontPerM = -1.f;
	float MudLoweredRearPerM = -1.f;
	TArray<FVector2D> EscapePath;   // the car's XY every half second of the forward pass, retraced in reverse
	bool bMudFieldOk = false;
	FString MudLine;
	/** Stage F: the tread's phase read back along the synthetic crawl line of step 10, its wraps counted against the line's length over LugPeriodCm. */
	bool bTreadOk = false;
	/** Stage H: the along-crest profile of step 10 (a 6 m crest beside a stroked line at a clean spot): its cell-to-cell difference sd and its mean. */
	bool bRidgeCrestOk = false;
	/** Stage I: the ridge's own shape on that profile - the width at half height, the crest's height and the coefficient of variation along it, plus the rut floor. */
	bool bStageIShapeOk = false;
	/** Stage G: the water depth the patch reports at the deepest cell of that stamped line against the table over the rut floor, and the water grid itself. Read through UGTWaterSubsystem::Sample since water stage W3. */
	bool bRutWaterOk = false;
	/** Water stage W3: the one water query's kinds - Ford mid-ford, Rut in step 10's rut, None on the dry road at 100 m - and the hull reading no submerged height in a rut (it skips rut water). */
	bool bWaterSourcesOk = false;
	float RunSlowTime = 0.f;
	int32 EscapePhase = 0;
	float EscapePhaseTime = 0.f;
	float EscapeArcM = 0.f;
	float EscapeMaxSpeed = 0.f;
	float EscapeGainM = 0.f;
	// MudRunner MR4: the bog run and the escape's gates test the tuned bog, so steps 8-9 run with gt.Mud.SoftSpots 0 (the value before
	// step 8 restored at step 9's end); the static S under the forward pass's wheel cells (distinct cells, keyed section << 32 | cell) is reported.
	int32 EscapeSoftSpotsWas = 1;
	TMap<int64, float> EscapeSoftCells;
	/** MR4: gt.Mud.SoftSpots set (by console priority, so a run's own -ExecCmds value is overridden) and applied to every patch at once. */
	void SetSoftSpotsForTest(int32 Value);
	// MudRunner MR5: and with gt.Mud.Chunks 0 (the value before step 8 restored at step 9's end; at 1 again the chunks are placed
	// anew on untouched ground); the chunks the bog's patches had at 1 are reported.
	int32 EscapeChunksWas = 1;
	/** MR5: gt.Mud.Chunks set (console priority) and applied to every patch at once. */
	void SetChunksForTest(int32 Value);
	// stage C: the passes (the escape's forward pass, the pass down its ruts, the held exit at 30 degrees, the same exit unheld from 8 m along)
	FPassStats Passes[4];
	FVector EscapeStart = FVector::ZeroVector;   // where the escape's forward pass began, and the car's yaw there
	float EscapeStartYaw = 0.f;
	FVector PassStart = FVector::ZeroVector;     // where the current rut pass began
	float PassStartYaw = 0.f;
	int32 RutPhase = 0;
	float RutPhaseTime = 0.f;
	float ExitAngleDeg = 30.f;
	float SavedRutHoldDrag = 0.f;
	float SavedRutHoldLateral = 0.f;
	bool bRutPassFaster = false;
	bool bExitSlower = false;
	FString RutLine;
	bool bShallowThrough = false;
	bool bFordThrough = false;
	bool bFordFloods = false;
	/** W1 step 15: parked in the ford as built, the current does not take the car (drift under half a metre in 6 s). */
	bool bFordHeld = false;
	/** W1 step 16: raised 70 cm, it does (over 5 m in 10 s since W2, within cos 0.9 of the flow). */
	bool bFordCarried = false;
	/** W2 step 16: and it floats while it goes (the wheels under 15 % of the weight, the keel on its predicted line). */
	bool bFordFloats = false;
	/** W2 step 17: the winch brings the floating car back to the post. */
	bool bFordWinched = false;
	/**
	 * WS1: the field fills from its two ends, so a step that changes the rise has to let it. The raise was asked for
	 * and the field is settling; the step's own work starts once this many seconds have passed. Measured by
	 * Art/water_test.bat's fill step and set from it.
	 */
	bool bFordRiseArmed = false;
	static constexpr float FordRiseSettleSeconds = 3.f;
	FVector2D FordStartXY = FVector2D::ZeroVector;   // where the car stood when the settle ended
	FVector2D FordFlowDir = FVector2D::ZeroVector;   // the current under it there, unit
	float FordMaxForceN = 0.f;                       // the biggest water force on the hull during the measurement
	float FordMaxSubmergedM = 0.f;
	float FordMaxOffRouteM = 0.f;                    // step 13: how far off the route the crossing wandered (information)
	// Water stage W4: the spray's water state seen while crossing (information; the spray test's own map has no water
	// sheet on it, so this is where the splash and the bow spray are read).
	int32 FordSprayWheels = 0;
	float FordSprayDeepestM = 0.f;
	float FordSprayRate = 0.f;
	int32 FordSprayLive = 0;
	float FordBowSubmergedM = 0.f;
	float FordBowRate = 0.f;
	bool bFordSprayWheelSeen = false;
	bool bFordSprayBowSeen = false;
	// LM1 housekeeping: the ford run's flood, latched over the run, and how many times the flag came on.
	bool bFordFloodLatched = false;
	bool bFordWasFlooded = false;
	int32 FordFloodCount = 0;
	// W2: the wheel load and the keel over the measured window (the last 5 s of it for the float's steady state)
	float FordLoadShareSum = 0.f;
	int32 FordLoadShareTicks = 0;
	float FordLateLoadSum = 0.f;
	int32 FordLateLoadTicks = 0;
	float FordLateKeelSum = 0.f;
	int32 FordLateKeelTicks = 0;
	float FordMaxKeelM = -1.e9f;
	float FordMaxLiftN = 0.f;
	// W2 step 17: the winch out
	TWeakObjectPtr<AActor> FordPost;
	float FordWinchAttachCm = 0.f;
	bool bFordWinchFloodedAtStart = false;
	bool bFordWinchFloodSet = false;   // the runner had to set the flood flag (a floating car's wheels read no water)
	float FordWinchDrainedAt = -1.f;
	FString BogLine;
	FString FordLine;
	bool bBogShotFramed = false;
	bool bWheelShotFramed = false;
	// the diagnostic mud picture (mud plan stage B): the bog drive's extent and the wheels where it stopped
	FVector BogDriveStart = FVector::ZeroVector;
	FVector BogDriveEnd = FVector::ZeroVector;
	float BogDriveYaw = 0.f;
	TArray<FMudSample> DiagWheels;
	bool bDiagFramed = false;
	int32 RutLowShot = 0;   // the eye-level pictures of the rut band: which of the three has been taken
	int32 BorderShot = 0;   // stage D: the two pictures of the mud patch box's border, near and from 40 m
	int32 TreadShot = 0;    // stage F: the picture straight down from 3 m over one of the crawl's ruts
	int32 SideShot = 0;     // stage I: the picture from beside one rut, 1.5 m up and 2 m to the side, along the ridge line
	int32 WetShot = 0;      // stage G: the picture of the same band with the water table lifted by a wetness of 1
	int32 FordShot = 0;     // water stage W1: which phase of a ford picture step (22 the bank, 23 the crossing, 24 the deep one) has been done
	float FordShotAt = 0.f; // water stage WS2: when the wake step's crossing ended, so its two frames are a second apart whenever the car got out
	float SavedWetness = 0.f;   // the weather's own wetness while that picture is taken, put back after it
	/** Logs, for the diagnostic picture, the screen pixel of the ruts, ridges and clear mud beside each wheel and of a line across the bog, with the field and the ground there. */
	void LogDiagPixels();
	// stage B: the mesh over the bog's patch
	bool bMeshOk = false;
	FString MeshLine;
	FVector DriveStart = FVector::ZeroVector;
	float DriveDistance = 0.f;
	float DriveOffRoute = 0.f;
	float DriveMinUp = 1.f;
	bool bDriveOk = false;

	// ---- water stage WS1: the field's own test (Art/water_test.bat) --------------------------------------
	/** W4: what the field texture's B/A carried at the crossing at step 1, and the cell's own flow there, cm/s. */
	float WaterTexelFlowCmPerS = -1.f;
	float WaterCellFlowCmPerS = -1.f;
	int32 WaterTexelCell = INDEX_NONE;
	bool bWaterCurrentOk = false;
	bool bWaterRingOk = false;
	bool bWaterStepOk = false;
	bool bWaterMeshOk = false;
	FString WaterCurrentLine;
	FString WaterRingLine;
	FString WaterStepLine;
	FString WaterMeshLine;
	double WaterVolumeAtFirst = 0.0;
	double WaterVolumeAt10 = 0.0;
	double WaterVolumeAt20 = 0.0;
	bool bWaterVolume10Taken = false;
	int32 WaterSettleLogs = 0;
	/** The fill: the level before the 70 cm raise, when it was asked for, and how long the middle took to come within 5 cm of it. */
	int32 WaterFillPhase = 0;
	float WaterFillAskedAt = 0.f;
	float WaterFillSeconds = -1.f;
	float WaterDrainSeconds = -1.f;
	float WaterFillTargetCm = 0.f;
	float WaterFillLowCm = 1.e9f;
	float WaterFillHighCm = -1.e9f;
	float WaterShiftErrorCm = -1.f;
	/** The ring: where it was fired, the crest at 1 m and 5 m, the front's time to 5 m, the volumes and the reflection off the nearest bank. */
	FVector2D WaterRingCentre = FVector2D::ZeroVector;
	float WaterRingFiredAt = -1.f;
	float WaterRingLevelCm = 0.f;
	float WaterCrest1Cm = 0.f;
	float WaterCrest5Cm = 0.f;
	float WaterFrontTo5M = -1.f;
	double WaterVolumeBeforeRing = 0.0;
	double WaterVolumeAdded = 0.0;
	double WaterVolumeAfterRing = -1.0;
	float WaterStillSpeed = -1.f;
	/** The nearest wall along the ring's cross axis (the first dry cell or the field's edge), and the two crests read a metre inside it. */
	float WaterWallM = -1.f;
	float WaterWallIncidentCm = 0.f;
	float WaterWallReflectCm = 0.f;
	/** WS1's ring against WS2's absorbing ends: what a crest sent at a flow-wise end sends back. */
	float WaterEndIncidentCm = 0.f;
	float WaterEndReflectCm = 0.f;
	float WaterEndIncidentAt = -1.f;
	float WaterEndM = -1.f;

	// ---- water stage R1: the rocks in the ford's bed --------------------------------------------------------
	bool bWaterRocksOk = false;
	FString WaterRocksLine;
	int32 WaterRocksPlaced = 0;
	int32 WaterRocksProud = 0;
	int32 WaterRockPhase = 0;
	float WaterRockPhaseAt = 0.f;
	float WaterRockLevelCm = 0.f;
	/** The tallest rock (the bed check) and the proudest one (the flow and the ring checks). */
	FVector2D WaterRockTallXY = FVector2D::ZeroVector;
	float WaterRockTallestM = 0.f;
	float WaterRockExposedCm = 0.f;
	float WaterRockBedCm = 0.f;
	float WaterRockRingCm = 0.f;
	/** The surface-breaking rocks, and what the water does 2.5 m upstream of the one the flow is read at. */
	TArray<FGTTerrainStone> WaterProudRocks;
	float WaterRockUpstreamMps = -1.f;
	FVector2D WaterRockProudXY = FVector2D::ZeroVector;
	float WaterRockProudM = 0.f;
	float WaterRockProudYawDeg = 0.f;
	float WaterRockProudOverLevelCm = 0.f;
	float WaterRockCrossMps = -1.f;
	float WaterRockFlankMps = -1.f;
	float WaterRockWakeMps = -1.f;
	float WaterRockWakeAtCm = -1.f;
	/** R1: when the ford winch step last logged what the tow was up against. */
	float FordWinchLogAt = -1.e9f;
	FVector2D WaterRockImpulseXY = FVector2D::ZeroVector;
	FVector2D WaterRockProbeXY = FVector2D::ZeroVector;
	float WaterRockFiredAt = -1.f;
	float WaterRockFrontAt = -1.f;
	float WaterRockIncidentAt = -1.f;
	float WaterRockIncidentCm = 0.f;
	float WaterRockReturnCm = 0.f;

	// ---- water stage WS2: the sources (the car's lids, wind, rain, the sponge at the ends) ------------------
	bool bWaterBowOk = false;
	bool bWaterStandOk = false;
	bool bWaterWindOk = false;
	bool bWaterRainOk = false;
	bool bWaterRaiseOk = false;
	FString WaterBowLine;
	FString WaterStandLine;
	FString WaterWindLine;
	FString WaterRainLine;
	FString WaterRaiseLine;
	int32 WaterCrossPhase = 0;
	float WaterCrossPhaseAt = 0.f;
	float WaterCrossLevelCm = 0.f;
	float WaterBowCrestCm = 0.f;
	float WaterBowTroughCm = 0.f;
	float WaterBowMidCrestCm = 0.f;
	float WaterBowMidTroughCm = 0.f;
	float WaterCrossMaxLidM3 = 0.f;
	float WaterCrossMaxKeelM = -1.e9f;
	float WaterCrossSpeedKph = 0.f;
	// Section 50: the speed hold over the crossing's middle 20 m (a PI on the throttle) and what it held.
	float WaterHoldIntegral = 0.f;
	float WaterHoldSeconds = 0.f;
	float WaterHoldMinCms = 1.e9f;
	float WaterHoldMaxCms = 0.f;
	float WaterHoldBandSeconds = 0.f;
	double WaterVolumeBeforeCar = 0.0;
	double WaterVolumeAfterCar = 0.0;
	float WaterAfterFlatCm = -1.f;
	int32 WaterSettleReads = 0;
	float WaterSettleCm[3] = { 0.f, 0.f, 0.f };
	float WaterMovedCm[3] = { 0.f, 0.f, 0.f };
	float WaterAfterMovedCm = -1.f;
	TArray<float> WaterFlatBaseCm;
	float WaterStandCrestCm = 0.f;
	TArray<float> WaterStandBaseCm;
	float WaterStandDownCm = 0.f;
	float WaterWindSdOnCm = -1.f;
	float WaterWindSdOffCm = -1.f;
	float WaterRainSdCm = -1.f;
	double WaterRainVolumeBefore = 0.0;
	double WaterRainVolumeAfter = 0.0;
	float WaterRaiseTo5Cm = -1.f;
	float WaterRaiseSwingCm = -1.f;
	float WaterRaiseSeriesAt = 0.f;
	FString WaterRaiseSeries;

	// ---- water stage W5: the river stage, the rain's rise with a lag --------------------------------------
	bool bWaterRiverOk = false;
	FString WaterRiverLine;
	/** The test's lag scale: 0.05 turns the game's 180 / 600 s into 9 / 30 s, which is what the two gates below are of. */
	static constexpr float WaterRiverLagScale = 0.05f;
	int32 WaterRiverPhase = 0;
	float WaterRiverPhaseAt = 0.f;
	float WaterRiverSampleAt = 0.f;
	float WaterRiverStageRiseCm = -1.f;
	float WaterRiverStageFallCm = -1.f;
	float WaterRiverWorstCm = 0.f;     // the worst |surface - (base + stage)| over the rise, cm
	float WaterRiverLowCm = 1.e9f;     // and the swing of that difference about its own moving line
	float WaterRiverHighCm = -1.e9f;
	float WaterRiverFallWorstCm = 0.f;
	int32 WaterRiverSamples = 0;
	FString WaterRiverSeries;
	float WaterWallIncidentAt = -1.f;

	// shots
	/** -GTShotsFrom=N ("cut 2", 2026-09-16): 0 for the whole leg, otherwise the shots step the run starts at (12..17, the bog steps). */
	int32 ShotsFrom = 0;
	/** How many pictures the steps that will run ask for: 28 for the whole leg, 17 from step 12 (the bog's), 7 from step 22 (the ford's three and the motion probe's four). */
	int32 ExpectedShots = 33;   // R1 adds hide_31_ford_rock at step 30, so a full run writes 33 (the default said 32 and every full shots run failed its own count gate)
	/** The step that teleports the car to the bog and settles it before jumping to ShotsFrom; out of the way of the real steps. */
	static constexpr int32 ShotsJumpStep = 100;
	/** The pictures asked for by the shots steps from FromStep to the last one. */
	static int32 ShotsAtOrAfter(int32 FromStep);
	FString ShotFolder = TEXT("M6");
	TArray<FString> ShotFiles;
	TWeakObjectPtr<ACameraActor> ShotCamera;
	float SettleLogTimer = 0.f;

	// ---- look stage L6 (VEHICLE_BUILD_SYSTEM 57): the dressing pictures, -GTShotsFrom=40 (Art/dressing_shots.bat) --------
	/** Steps 40, 41, 42: a track stone near 1322 m, the rally post nearest 640 m, the proudest ford rock. Entered only by -GTShotsFrom=40; a full run never reaches them. */
	static constexpr int32 DressFirstStep = 40;
	static constexpr int32 DressSpots = 3;
	/** Per object: gt.Look.Surface 0, 1, then 1 and 0 again under gt.Look.Debug 1 (BaseColor), then the plain MI_Env_* put back. */
	static constexpr int32 DressShotsPerSpot = 5;
	/** And at the stone, a non-instanced twin cube in the Surface 0 instance and in MI_Env_Greybox (the switch's 0 against the plain graph). */
	static constexpr int32 DressTwinShots = 2;
	/** The dressing pictures' field of view, degrees (7 m off, so a 0.4 m stone fills a box). */
	static constexpr float DressFovDeg = 25.f;
	/** Spot 0 stone, 1 post, 2 rock. */
	void TickDressing(int32 Spot);
	int32 DressPhase = 0;
	int32 DressSurfaceBefore = 1;
	FTransform DressInstance;
	float DressLevelCm = -1.e9f;
	TWeakObjectPtr<class UHierarchicalInstancedStaticMeshComponent> DressComponent;
	TWeakObjectPtr<class UMaterialInterface> DressSavedMaterial;
	TWeakObjectPtr<class AStaticMeshActor> DressTwin;

	// ---- look stage L3 (VEHICLE_BUILD_SYSTEM 58): the sky pictures, -GTShotsFrom=50 (Art/sky_shots.bat) --------------
	/** Steps 50, 51, 52: the sky behind the car at the rally posts (640 m) pitched up, hide_10's far ridge, a foliage clump. Entered only by -GTShotsFrom=50. */
	static constexpr int32 SkyFirstStep = 50;
	/** Clear: all on, Sky 0, Haze 0, Foliage 0, Dressing 0 (LD3), all on again; the sky spot adds Debug 6 with Sky 1 and 0, the clump spot DabNormal 1; Overcast: all on, Sky 0, Haze 0, Foliage 0, Dressing 0. 36 since LD3 (30 before). */
	static constexpr int32 SkyShotsTotal = 36;
	/**
	 * Leg dressing LD7: steps 53-56, four views of the biome dressing - inside the forest, at a thicket edge, on a scree /
	 * alpine hilltop, at the ford - each in Clear with gt.Look.Dressing 1 and 0 (view_<name>_on / _dress0). A sky run
	 * (-GTShotsFrom=50) goes on into them; -GTShotsFrom=53 takes them alone.
	 */
	static constexpr int32 ViewsFirstStep = 53;
	static constexpr int32 ViewSpots = 4;
	static constexpr int32 ViewShotsPerSpot = 2;
	/** Spot 0 the sky, 1 the ridge, 2 the clump. */
	void TickSky(int32 Spot);
	/** The screen box of world points (all of them, and its middle 60 %), logged as "borderbox <picture>/<name>". */
	void LogScreenBox(const FString& Picture, const FString& Name, const TArray<FVector>& Points);
	int32 SkyPhase = 0;
	int32 SkyIndex = 0;
	bool bSkyApplied = false;
	float SkyNextAt = 0.f;
	FString SkyWeatherNow;
	FTransform SkyClump;
	TArray<FTransform> SkyClumpCards;
	/** LD7: with biomes the spec has no L3 cards, so spot 2 aims at the nearest biome dressing plant; its bounds' corners. */
	TArray<FVector> SkyPlantPoints;
	/** LD7: the frame and GPU time over the step that is ending (hide shots), logged as a GTPERF line in Next(). */
	int32 PerfFrames = 0;
	double PerfFrameMsSum = 0.0;
	double PerfGpuMsSum = 0.0;
	float PerfFrameMsMax = 0.f;
	int32 PerfStep = -1000;
	/** LD7 views (steps 53-56): the eye and the aim for view Spot (3 forest, 4 thicket, 5 hilltop, 6 ford); false when the spec has no such place. */
	bool FindViewSpot(int32 Spot, FVector& OutEye, FRotator& OutLook, FString& OutWhat) const;
	TWeakObjectPtr<class UMaterialInterface> SkySavedFoliageMaterial;

	// ---- leg dressing LD8a (docs/LEG_DRESSING_PLAN.md): -GTProfileGPU, the per-pass GPU profile of the dressing ----------
	/**
	 * After each profiled picture (IsProfileView) the run holds: the steps, their clocks and the GTPERF sums stop until
	 * the shader and asset compilers are empty and 1.5 s more has passed with the picture's camera and state, then
	 * ProfileGPU runs -GTProfileCaptures=N times (default 1), 30 frames apart. Each capture is framed in the log by a
	 * "GTPROFILE capture" line (the view, gt.Look.Dressing, the resolution, r.ScreenPercentage, the GPU temperature from
	 * nvidia-smi, the dressing's instances per class and the landscape grass instances); Art/dressing/ld8_profile.py
	 * parses the pass tree that follows it.
	 */
	bool bProfileGPU = false;
	/** LD8c: -GTShotsThenViews - a full shots run goes on into the four biome views (steps 53-56), 8 more pictures. */
	bool bShotsThenViews = false;
	int32 ProfileCaptures = 1;
	FString ProfilePending;
	int32 ProfilePhase = 0;
	int32 ProfileFrames = 0;
	float ProfileWait = 0.f;
	int32 ProfileDone = 0;
	static bool IsProfileView(const FString& Picture);
	void TickProfile(float DeltaSeconds);
	FString ProfileSceneLine() const;
};
