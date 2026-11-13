#pragma once

#include "CoreMinimal.h"
#include "Terrain/GTTerrainGenerator.h"

class AGTCarPawn;
class AGTPlayerController;
class ALandscapeProxy;
class UGTSurfacePhysMaterial;
class UWorld;

/**
 * Diagnostic only (2026-09-22): the fords of L_Proving measured for the "slow in water" and "ledge on exit" reports.
 * -GTFordDiag on L_Proving (Art/ford_diag.bat, log Saved/Logs/ford_diag.log); Art/tools/ford_diag.py makes the tables.
 * Never fails: it is off every gate. Driven by AGTRunGameMode::Tick.
 *
 * The survey: each ford's still level and its waterlines along the route's centre line (landscape heightfield and the
 * WorldStatic trace the wheels see), a 25 cm profile from 6 m before the entry waterline to 6 m past the exit on the
 * centre line and both wheel lines (GTFORDPROF lines), where the surface under each line changes (GTFORDDIAG tag lines),
 * the surface rows met, and the ford rocks relative to the crossing line. Then the runs: a dry 30 m on the pad, and for
 * each ford a standing start 15 m before the entry waterline at full throttle along the route to 15 m past the exit (high
 * range, diffs open, the car's own state otherwise), with gt.Water.Hull 0 and gt.Water.Buoyancy 0 variants and a repeat
 * of the first ford run. gt.Water.Diag is 1 during a run and 2 within 6 m of a waterline, so the log carries the car's
 * state every 0.1 s and every tick at the banks. t.MaxFPS is set to 60 (the owner's frame rate).
 */
class FGTFordDiagRunner
{
public:
	explicit FGTFordDiagRunner(UWorld* InWorld);

	/** True when finished; bOutPass is always true (a diagnostic), OutSummary the per-run digest. */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	struct FFord
	{
		FString Name;
		int32 Section = INDEX_NONE;
		float StartM = 0.f, EndM = 0.f, DepthM = 0.f;
		float LevelCm = 0.f;
		float EntryM = 0.f, ExitM = 0.f;   // waterlines along the centre line (landscape heightfield)
		bool bValid = false;
	};
	struct FRunDef
	{
		FString Name;
		int32 Ford = INDEX_NONE;   // INDEX_NONE: the dry pad run (or a bog run)
		int32 Hull = 1;
		int32 Buoyancy = 1;
		int32 Bog = 0;             // RIVERBED S2: 1 out of the bog's box to the right (Mud up to the box's side), 3 to the left, 2 along the route past the section's end
		float RiseRate = -1.f;     // RIVERBED S2: gt.Mud.SinkRiseRate for the run (-1 the property)
	};
	struct FBankStats
	{
		float MaxContactStepCm = 0.f; int32 StepWheel = -1; float StepRelM = 0.f;
		float MaxRadiusStepCm = 0.f; int32 RadiusWheel = -1; float RadiusRelM = 0.f;
		float MaxLoadN = 0.f; int32 LoadWheel = -1; float LoadRelM = 0.f;
		float MaxLoadStepN = 0.f; int32 LoadStepWheel = -1; float LoadStepRelM = 0.f;
	};

	void Log(const FString& Line) const;
	void SetCvar(const TCHAR* Name, float Value) const;
	float LandscapeZ(float XCm, float YCm, bool& bOk) const;
	bool TraceZ(float XCm, float YCm, float& OutZ, const UGTSurfacePhysMaterial*& OutSurface, FString& OutWhat) const;
	FVector2D RoutePoint(float ArcM, FVector2D& OutLeft) const;
	void Survey();
	void SurveyFord(FFord& Ford);
	void SurveyRocks();
	void BeginRun();
	bool TickRun(float DeltaSeconds);
	void EndRun(const FString& Why);
	void Steer(float SpeedMps);
	void TrackBank(FBankStats& Stats, float BankArcM, const struct FGTWaterDiagSample& S, float WindowM = 4.f) const;
	/** RIVERBED S4 (VEHICLE_BUILD_SYSTEM 54): GTFORDRUT - the depth the car reads across the ford's middle (the sheet's surface over the landscape contact) against the field there, and the bed patch's field under the water (the cells a wheel touched). */
	void LogFordRuts(const TCHAR* When, int32 FordIndex) const;
	// RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): the box-edge runs.
	bool BeginBogRun(FVector& OutLocation, float& OutYaw);
	bool TickBogRun(float DeltaSeconds);
	FString EndBogRun(const FString& Why, float MeanDtMs);
	float PastEdgeM(const FVector& XY) const;

	TWeakObjectPtr<UWorld> World;
	TWeakObjectPtr<AGTPlayerController> PC;
	TWeakObjectPtr<AGTCarPawn> Car;
	TArray<TWeakObjectPtr<ALandscapeProxy>> Landscapes;
	TSet<const UGTSurfacePhysMaterial*> RowsSeen;
	FGTTerrainSpec Spec;
	TArray<FFord> Fords;
	TArray<FRunDef> Runs;
	TArray<FString> Digest;
	float HalfTrackM = 0.8f;
	float HalfBaseM = 1.4f;

	int32 Phase = 0;
	float Elapsed = 0.f;
	float PhaseTime = 0.f;
	int32 RunIndex = 0;

	// The run in progress.
	float StartArcM = 0.f;
	FVector2D DryStart = FVector2D::ZeroVector;
	FVector2D DryDir = FVector2D(1.f, 0.f);
	float DriveTime = 0.f;
	float StuckTime = 0.f;
	float DtSum = 0.f;
	int32 Ticks = 0;
	float TEntry = -1.f, VEntry = 0.f, TFrontEntry = -1.f, TExit = -1.f, VExit = 0.f, TFrontExit = -1.f;
	float T15 = -1.f, V15 = 0.f, T30 = -1.f, V30 = 0.f;
	float VMin = 1.e9f, ArcMin = 0.f;
	FString BudgetAtMin;
	float PeakSlip = 0.f; int32 PeakSlipWheel = -1; float PeakSlipArc = 0.f;
	int32 SlippingTicks = 0, WaterTicks = 0;
	float MaxFront = 0.f;
	float FloodArc = -1.f;
	float VEnd = 0.f;
	FBankStats EntryBank, ExitBank;
	// RIVERBED S4: the ford's bed patch. A ford run ends at EndArcM (past the exit by BeforeM, or 5 m past the bed patch's
	// box when that reaches further); RunWide is the biggest per-tick step anywhere in the run; the sinkage in the water.
	float EndArcM = 0.f;
	float BoxExitArcM = -1.f;
	FBankStats RunWide;
	float MaxSinkInWaterCm[4] = { 0.f, 0.f, 0.f, 0.f };
	float MaxVisInWaterCm[4] = { 0.f, 0.f, 0.f, 0.f };
	float MaxRowSinkCm = 0.f;
	float MinRadiusInWaterCm = 1.e9f;
	int32 ProfiledTicks = 0;
	int32 InWaterWheelTicks = 0;
	bool bHavePrev = false;
	float PrevCz[4] = { 0.f, 0.f, 0.f, 0.f };
	float PrevR[4] = { 0.f, 0.f, 0.f, 0.f };
	float PrevL[4] = { 0.f, 0.f, 0.f, 0.f };
	bool PrevContact[4] = { false, false, false, false };

	// RIVERBED S2: the bog runs (low range, locked, full throttle out of the Mud section's patch box onto Dirt).
	int32 BogSection = INDEX_NONE;
	FVector2D BoxMin = FVector2D::ZeroVector;
	FVector2D BoxMax = FVector2D::ZeroVector;
	float CapM = 0.05f;
	bool EdgeCrossed[4] = { false, false, false, false };
	float VisAtEdgeCm[4] = { 0.f, 0.f, 0.f, 0.f };
	float RawAtEdgeCm[4] = { 0.f, 0.f, 0.f, 0.f };
	float SpeedAtEdge[4] = { 0.f, 0.f, 0.f, 0.f };
	float CapPastM[4] = { -1.f, -1.f, -1.f, -1.f };
	float MaxVisPastCm[4] = { 0.f, 0.f, 0.f, 0.f };   // the deepest visible sinkage seen outside the box
	float EdgeMaxRiseCm = 0.f, EdgeRisePastM = 0.f, EdgeRiseDtMs = 0.f, EdgeRiseSpeed = 0.f;
	float RunMaxRiseCm = 0.f;
	float EdgeMaxRadiusRiseCm = 0.f; int32 EdgeRadiusWheel = -1;
	float PrevChassisZ = 0.f;
	bool bPrevChassis = false;
	int32 EdgeTicks = 0;
};
