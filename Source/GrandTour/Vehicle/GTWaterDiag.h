#pragma once

#include "CoreMinimal.h"

class AGTCarPawn;

/**
 * Diagnostic only (2026-09-22, the "slow in water" and "ledge on exit" reports): one read-only snapshot of the car's
 * water, traction, hull and drivetrain state. Nothing here writes to the car. The console variable gt.Water.Diag logs it
 * as a GTWATERDIAG line (1: every 0.1 s, 2: every tick); FGTFordDiagRunner (-GTFordDiag, Art/ford_diag.bat) drives the
 * fords with it on and Art/tools/ford_diag.py turns the log into tables. Forces in newtons, lengths in metres unless
 * the name says cm.
 */
struct FGTWaterDiagWheel
{
	bool bContact = false;
	FVector ContactCm = FVector::ZeroVector;
	float ArcM = 0.f;            // along the level's route (0 with no spec)
	float DepthM = 0.f;          // the water the traction read (the field's surface over the contact)
	float StillDepthM = 0.f;     // the covering sheet's still level over the contact (0 with no sheet)
	float LoadN = 0.f;           // the traction's true load
	float SpringN = 0.f;         // the filtered spring force
	float SlipRatio = 0.f;       // (omega r - v along the car) / max(|v|, 0.5 m/s)
	float ChaosSlip = 0.f;       // Chaos's SlipMagnitude
	bool bChaosSlipping = false;
	float SinkM = 0.f;
	float VisSinkM = 0.f;        // RIVERBED S2: the sinkage the Chaos radius is shrunk by (UGTTractionComponent VisibleSinkage)
	bool bInPatchBox = false;    // RIVERBED S2: the contact inside a mud patch's box
	float RadiusCm = 0.f;        // the Chaos wheel radius as applied (base minus the sinkage shrink)
	float SuspNorm = 0.f;        // Chaos NormalizedSuspensionLength
	float SuspOffsetCm = 0.f;    // Chaos GetSuspensionOffset
	float RollingResistance = 0.f;   // the capped coefficient the tuning applies
	float WaterShare = 0.f;      // RollingResistance minus the capped sum without the water term
	float SurfaceDrag = 0.f, PloughDrag = 0.f, BellyDrag = 0.f, RutDrag = 0.f, WaterDrag = 0.f;   // uncapped terms
	float SinkRate = 0.f, MaxSink = 0.f;
	float FrictionScale = 1.f;
	FString Tag;
	float DriveNm = 0.f, CapNm = 0.f, OmegaRadS = 0.f;
};

struct FGTWaterDiagSample
{
	bool bValid = false;
	float TimeS = 0.f;
	FVector LocationCm = FVector::ZeroVector;
	bool bHaveArc = false;
	float ArcM = 0.f, OffM = 0.f;
	float PitchDeg = 0.f, RollDeg = 0.f;
	float SpeedMps = 0.f;        // along the car's forward axis
	float Speed2DMps = 0.f;
	float VerticalMps = 0.f;
	float Throttle = 0.f;
	int32 Gear = 0;
	bool bLow = false, bLock = false;
	float Rpm = 0.f, EngineNm = 0.f, TorqueScale = 1.f, MaxEngineNm = 0.f;
	bool bFlooded = false, bBogged = false;
	float LoadCorrection = 1.f, SpringSumN = 0.f, LoadSumN = 0.f, WeightN = 0.f;
	float HullDragN = 0.f, HullDragAlongN = 0.f, HullLiftN = 0.f, SubmergedM = 0.f, KeelDepthM = 0.f;
	bool bLiftCapped = false, bDragCapped = false;
	float RollingForceN = 0.f;   // the whole rolling-resistance push the tuning applies (all terms)
	float WaterForceN = 0.f;     // its water share
	float WaterForceRawN = 0.f;  // the uncapped water terms at the same scale
	float TractiveN = 0.f;       // sum of the drivetrain's wheel torque / radius
	float TractiveCapN = 0.f;    // sum of the drivetrain's grip cap / radius
	float SheetLevelCm = 0.f;    // the still level of the sheet under the car's centre (0 with none)
	float FrontDepthM = 0.f;
	int32 NumWheels = 0;
	FGTWaterDiagWheel Wheels[4];
};

namespace GTWaterDiag
{
	/** The snapshot. Read-only. */
	GRANDTOUR_API FGTWaterDiagSample Measure(const AGTCarPawn& Car);

	/** The GTWATERDIAG line (without the prefix): globals, then " | wN ..." per wheel. */
	GRANDTOUR_API FString Format(const FGTWaterDiagSample& Sample);

	/** Called by AGTCarPawn::Tick last; logs when gt.Water.Diag is 1 (every 0.1 s) or 2 (every tick), else returns at once. */
	GRANDTOUR_API void TickCar(const AGTCarPawn& Car);

	/** The cvar's value (the runner sets it through the console manager). */
	GRANDTOUR_API int32 GetMode();
}
