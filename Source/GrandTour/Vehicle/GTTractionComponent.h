#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "GTTractionComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;
class UGTHullComponent;
class UGTMudSubsystem;
class UGTSurfacePhysMaterial;
struct FGTVehicleTuning;

USTRUCT(BlueprintType)
struct FGTWheelTraction
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bInContact = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	FGameplayTag SurfaceTag;

	/** Cached authored terrain sample for cosmetic effects; NAME_None off authored terrain.
	 * Reuses the traction query without changing the physical-material tag or driving response. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	FName AuthoredSurface = NAME_None;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float GroundWetness = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float GroundWaterDepthCm = 0.f;

	/** Metres the wheel has sunk into soft ground. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float Sinkage = 0.f;

	/** RIVERBED S2 (2026-09-23): the metres the Chaos radius is shrunk by (what the eye sees sink): Sinkage inside a mud patch's box, at most OutsidePatchSinkCapM outside every box, rising back at VisibleSinkRiseRate per metre of ground on the way out. Drag, grip and the belly read Sinkage. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float VisibleSinkage = 0.f;

	/** RIVERBED S2: the contact is inside a mud patch's box (UGTMudSubsystem::PatchAt), whatever the surface's tag; kept from the last tick in contact. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bInPatchBox = false;

	/** RIVERBED S4: the contact is inside the box of a patch with a deformation profile (a ford's bed) on ground that sinks at all: the profile's SinkageRate and MaxSinkage stand in for the row's, and the field is read and stamped whatever the tag. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bInProfiledPatch = false;

	/** Sinkage / the surface's MaxSinkage, 0..1. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float SinkageFraction = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float FrictionScale = 1.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float RollingResistance = 0.012f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float TrackDepth = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bSlipping = false;

	/** Chaos longitudinal slip magnitude for this wheel (cm/s). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float SlipMagnitude = 0.f;

	/** The suspension's spring force (Chaos units, kg cm/s^2), smoothed at LoadFilterRate. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float SpringForce = 0.f;

	/** The true load on the tyre: the spring force scaled so the wheels in contact carry the car's weight (Chaos units). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float Load = 0.f;

	/** The ground's own Friction coefficient under the wheel (1 where it has no physical material). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float SurfaceFriction = 1.f;

	/** Water over the contact point, metres (UGTWaterSubsystem::Sample). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float WaterDepthM = 0.f;

	/** MudRunner MR2: that water is a bog's rut water (EGTWaterKind::Rut, muddy slurry), which coats rather than washes. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bRutWater = false;

	/** Water stage W1: the current at the contact, cm/s in world XY. Zero in still water, and then every water number below is exactly what it was. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	FVector2D FlowCmPerS = FVector2D::ZeroVector;

	/** Water stage W1: the sideways part of this wheel's water drag, applied at the contact as a force on the chassis (newtons, positive to the car's right). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float WaterLateralN = 0.f;

	/** Signed flowing-water force at this contact, world XY newtons; excludes hull force. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	FVector2D WaterForceN = FVector2D::ZeroVector;

	/** The rut just ahead of the wheel, 0..1: its depth against the surface's MaxSinkage from the mud field inside a mud patch, the track paint elsewhere. An old track of yours eases the ploughing. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float RutDepth = 0.f;

	/** Inside a mud patch (docs/MUD_DEFORMATION_PLAN.md stage C): the field's slope the tyre is rolling up where it is heading, 0..RutHoldMaxSlope, weighted by the tracks there. Zero down a rut and on untouched mud; the wall of a rut or a ridge when the tyre is steered out. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float RutClimb = 0.f;

	/** The field's slope across the tyre's heading at the same point, positive rising to the car's right (clamped, weighted by the tracks). The hold pushes the tyre downhill, into its rut. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float RutCrossSlope = 0.f;

	/** The contact is on mud or bog inside a mud patch: the field is the record, not the paint. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bInMudPatch = false;

	/** LM3a: the contact is inside a snow patch's box (a profiled patch whose medium is snow): it stamps whatever its sinkage, and its plough drag is the snow ahead's. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bInSnowPatch = false;

	/** Wheel spray P2: the contact is inside a gravel patch's box (a profiled patch whose medium is Gravel), as bInSnowPatch is for snow. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bInGravelPatch = false;

	/** Wheel spray P2: the variant slice (EGTMudVariant) of the patch at the contact, 0 (Standard) outside every patch: the spray's mud colour and its clumps' slice. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	uint8 PatchVariant = 0;

	/** LM3a: the uncut snow ahead of the tyre, cm over its bottom (the mean of the three rut probes of max(0, the snow surface there - the tyre's bottom)); 0 down its own cut. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float SnowAheadCm = 0.f;

	/** The tyre's contact point (world), kept from the last tick in contact. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	FVector ContactPoint = FVector::ZeroVector;

	/** Mud this wheel has lowered in the mud fields, cm^3, accumulated (a wheel in another's rut lowers little). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float MudLoweredCm3 = 0.f;

	/**
	 * LM2a, the throw (docs/LIVING_MUD_PLAN.md LM2a): the share of this tick's bank deposit the wheel throws instead of
	 * banking, from its wheelspin. SlipMagnitude is Chaos's (the tyre's surface speed less the ground's speed at the
	 * contact, cm/s, positive spinning forward); the spin is SlipMagnitude in the drive's direction (negated in reverse,
	 * so a locked wheel braking never throws), and the share rises linearly from 0 at the wheel's own SlipThreshold (the
	 * one bIsSlipping is decided by, 20 cm/s) to the patch's ThrowMax at UGTTractionComponent::SlipSaturation (300 cm/s,
	 * the traction's "full wheelspin").
	 */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float ThrowShare = 0.f;

	/** LM2a: the mud this wheel's stamps returned for the throw, cm^3, accumulated; UGTSprayComponent spends it on blobs that carry it. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	double ThrownCm3 = 0.0;

	/** LM2a diagnostic (the standstill crawl): the rut hold's sideways push this tick, newtons (positive to the car's right), and its drag, newtons. Nothing reads them. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float RutHoldLateralN = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float RutHoldDragN = 0.f;

	/** How far the tyre's contact patch has travelled over the ground in all, cm (its ground-plane velocity along the tyre's heading per tick, 0 while the wheel is not turning). The tread's lug phase runs with this, so the lugs are one LugPeriodCm apart on the ground and the pattern is continuous from cell to cell. It was the wheel's own rolled distance (|angular speed| x radius) until stage H, and under wheelspin that advanced metres per centimetre of ground: neighbouring cells held unrelated phases (docs/MUD_ONE_SURFACE_PLAN.md stages F and H0). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float RolledCm = 0.f;

	/** MudRunner MR2b: the tread's own speed, cm/s (Chaos's wheel angular velocity x the wheel radius; positive rolling forward, 0 braked or locked, 0 off the ground). The way it throws mud: the body's spray fans read it. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float TreadCmPerS = 0.f;

	/** Where the tyre is heading (unit, world XY): the chassis heading turned by the wheel's steer inside a mud patch, the way the car travels elsewhere. The tread is stamped along it. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	FVector2D TyreHeading = FVector2D(1.f, 0.f);

	/**
	 * MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md): the mud this tyre carries, 0..1 (UGTTractionComponent::StepMudLoad).
	 * It rises in a mud patch, sheds by distance on firm ground and washes off in water; outside every patch the car lays it
	 * into the track paint as broken muddy tracks. Nothing in the physics reads it.
	 */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float MudLoad = 0.f;

	// Diagnostic only (2026-09-22, Vehicle/GTWaterDiag.cpp, gt.Water.Diag): the terms of RollingResistance's sum,
	// uncapped, and the surface's sinkage row as the wheel used it this tick. Written by Update, read by nothing else.
	// LM3a: the first three readable from Python (the snow check's drag terms); still written only by Update.
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction|Diag")
	float DiagSurfaceDrag = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction|Diag")
	float DiagPloughDrag = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction|Diag")
	float DiagBellyDrag = 0.f;
	float DiagRutDrag = 0.f;
	float DiagWaterDrag = 0.f;
	float DiagSinkRate = 0.f;
	float DiagMaxSink = 0.f;
};

/** MR1: what one tick of a wheel's mud load reads (UGTTractionComponent::StepMudLoad), so the tests can drive it without a car. */
struct FGTMudLoadStep
{
	bool bInContact = false;
	/** The contact is on the Mud or Bog row inside a mud patch's box (a patch of medium Mud). */
	bool bInMudPatch = false;
	/** The contact is inside a snow patch's box. */
	bool bInSnowPatch = false;
	float SinkageFraction = 0.f;
	/** The wheelspin's share, 0..1 (the slip over SlipSaturation while slipping). */
	float SlipShare = 0.f;
	float WaterDepthM = 0.f;
	/** MR2: the water is a bog's rut water (it never washes; a ford's water over a riverbed patch does). */
	bool bRutWater = false;
	/** Ground the contact covered this tick, cm. */
	float DistanceCm = 0.f;
	float DeltaSeconds = 0.f;
};

/**
 * Per-wheel surface state (ARCHITECTURE 6a): reads the physical material under each Chaos wheel,
 * keeps a sinkage value and derives grip and rolling drag from it, and flags the bogged state.
 *
 * Sinkage grows from three things on soft ground: settling while in contact (slow), ploughing
 * while moving slowly (full surface rate), and wheelspin (fastest). It recovers on firm ground.
 * Stage 3: past AxleClearanceM the axles ride on the mud (Chaos has no unsprung parts to put there), which
 * drags and takes load off the tyres; water over the contact drags, lightens the tyre and is reported for
 * the engine's intake; a rut of your own ahead of the wheel is mud already pushed aside.
 * Mud deformation stage C (docs/MUD_DEFORMATION_PLAN.md): inside a mud patch the rut ahead is read from the
 * mud field where the tyre is heading (the chassis heading turned by the wheel's steer), and the field's slope
 * there holds the tyre: rolling up the wall of a rut or over a ridge adds drag (RutHoldDrag), the wall pushes
 * the tyre back down into the rut (RutHoldLateral), so following your own line is the easy way through. The
 * belly's drag eases by the channel already cut ahead of it (BellyChannelEase). Outside patches the track paint
 * is the record as before. The wheels and the belly stamp the field every tick (StampMud).
 * Bogged means the wheels are sunk, the car is nearly stopped and the driver is spinning them:
 * throttle then digs instead of moving. Ease off and the flag clears, so a bogged car can still
 * be crawled out with gentle throttle; the winch is for when that fails.
 * Also reads each wheel's load and the ground's friction coefficient: the tuning scales the tyre's
 * lateral slip graph by them (driving feel stage 1), so the graph's 1.0 is the grip available.
 * Driven by the pawn's tick through Update(); contributes to the tuning through ModifyTuning().
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTTractionComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTTractionComponent();

	void Update(float DeltaSeconds, const UChaosWheeledVehicleMovementComponent& Movement, float ForwardSpeed);
	void ModifyTuning(FGTVehicleTuning& Tuning) const;

	/** 0 dry .. 1 soaked; the weather subsystem will drive this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 1))
	float Wetness = 0.f;

	/** Smoothing rate (per second) for the wheel load that scales the slip graph: the raw suspension force lags a physics step and carries the damper's spikes. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float LoadFilterRate = 16.f;

	/** Sinkage recovery on firm ground, metres per second. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float SinkageRecoveryRate = 0.08f;

	/**
	 * RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52), proposed, unmeasured by the owner: outside every mud patch box
	 * the Chaos radius shrinks by at most this, m (Dirt's MaxSinkage). Only a patch deforms, so deeper than this outside
	 * one was a wheel buried in ground that never moved (wet Dirt 15 cm, L_TestTrack's Mud 22 and Snow 25 cm lanes).
	 * The raw Sinkage (drag, grip, belly, the F2 decay) is not capped. gt.Mud.SinkCap 0 takes the cap off.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float OutsidePatchSinkCapM = 0.05f;

	/**
	 * RIVERBED S2 (2026-09-23), proposed, unmeasured by the owner: leaving a box the visible sinkage falls to the cap at
	 * no more than this many metres per metre of ground the contact travels (no limit sinking in), so the box's edge is a
	 * ramp (a 17 cm shrink comes back over about 0.6 m), not the one-tick ledge section 49 took off the Mud/Dirt edge.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float VisibleSinkRiseRate = 0.3f;

	/** Sinkage at which the axles and diffs meet the mud (a 38 cm wheel with 19 cm under the diffs). */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float AxleClearanceM = 0.19f;

	/** Drag from the axles ploughing, as a fraction of the wheel's load per metre sunk past the clearance. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float BellyDragPerMetre = 0.3f;

	/**
	 * LM3b (docs/LIVING_MUD_PLAN.md LM3b housekeeping 1): inside a snow patch a tyre's own sinkage (its few cm in the packed
	 * base) rolls at this row's rate, RollingResistance x (1 + SinkageDragScale x the sinkage fraction), in place of its
	 * contact's row (the Snow row, whose sinkage drag counted the snow the plough and the belly carry a second time). The
	 * Dirt row; unset or missing, the contact's own row as before. The surfaces table is untouched.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	TSoftObjectPtr<UGTSurfacePhysMaterial> SnowBaseRow = TSoftObjectPtr<UGTSurfacePhysMaterial>(FSoftObjectPath(TEXT("/Game/GrandTour/Terrain/Surfaces/PM_Dirt.PM_Dirt")));

	/** Grip lost when the axles carry the car, at AxleClearanceM past the clearance (0.25 until the second bog: with the
	 *  bog's own grip loss it left 0.18 of the load against 0.16 of drag, a car that stopped on any hummock and could not move). */
	UPROPERTY(EditAnywhere, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 1))
	float BellyGripLoss = 0.15f;

	/** Water drag as a fraction of the wheel's load, per metre of depth at 10 m/s (grows with speed squared). */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float WaterDragPerMetre = 2.4f;

	/**
	 * Grip lost to buoyancy at WaterBuoyancyDepthM of water. **0 since water stage W2** (docs/WATER_PLAN.md): the
	 * field is kept, but UGTHullComponent's real lift replaced this stand-in - it takes the weight off the springs, so
	 * the load this component reads, and the grip that follows the load, fall on their own. Raise it again only to
	 * compare with the old behaviour.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 1))
	float WaterBuoyancyGripLoss = 0.f;

	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float WaterBuoyancyDepthM = 0.8f;

	/** How much a full rut of your own eases the ploughing (growth and plough drag) and how far ahead of the wheel it is read. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 1))
	float RutEase = 0.6f;

	/** Under this speed (cm/s) the rut is read along the car's heading, backward when the drivetrain is in reverse, instead of along the velocity; the rut hold's push fades in over it. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float RutReadSpeed = 20.f;

	/** Stage C: extra rolling drag, as a fraction of the wheel's load per unit of RutClimb, when the tyre is steered up the wall of a rut or over a ridge (0.3 x a wall clamped to 0.5 = 0.15 of the load at most). */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float RutHoldDrag = 0.3f;

	/** Stage C: the wall's push on the tyre back down into its rut, as a fraction of the wheel's load per unit of cross-slope, applied at the contact point. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float RutHoldLateral = 0.3f;

	/** The field's slopes are clamped to this (cm per cm) before either hold term: a stamp's wall reads 1.5 or more over one cell, steeper than any real bank. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float RutHoldMaxSlope = 0.5f;

	/** Stage C: how much a channel already cut to the belly's depth ahead of it eases the belly drag inside a mud patch (outside, the wheel's rut does it). */
	UPROPERTY(EditAnywhere, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 1))
	float BellyChannelEase = 0.6f;

	/** Draw the wheels and the belly into the mud field under them on mud or bog (docs/MUD_DEFORMATION_PLAN.md, stage A). */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	bool bStampMud = true;

	/** The belly's box stops this far short of the tyres' contacts at each end and side so it does not flatten the ruts. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float BellyStampInsetCm = 40.f;

	/** This tick's wheel and belly primitives into the mud patches (called by Update). */
	void StampMud(UGTMudSubsystem& Mud, const UChaosWheeledVehicleMovementComponent& Movement);

	// ---- MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md): the mud each tyre carries out of a patch ----------------------
	/** In a mud patch the load rises at this x (0.5 + sinkage fraction) x (1 + slip share), per second. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Traction|Mud")
	float MudLoadRate = 0.6f;

	/** On firm ground it halves every this many metres of ground covered. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Traction|Mud")
	float MudShedHalfM = 15.f;

	/** In water deeper than MudWashDepthM it halves every this many metres. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Traction|Mud")
	float MudWashHalfM = 2.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Traction|Mud")
	float MudWashDepthM = 0.05f;

	/**
	 * One tick of a wheel's mud load. Out of contact it keeps; in a snow patch it is 0 (snow carries nothing in MR1); in a mud
	 * patch it rises (to 1); in water deeper than WashDepthM it halves every WashHalfM of ground; elsewhere every ShedHalfM.
	 */
	static float StepMudLoad(float Load, const FGTMudLoadStep& Step, float Rate, float ShedHalfM, float WashHalfM, float WashDepthM);

	/**
	 * MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4): the sinkage's rate (m/s) and cap (m) a wheel takes - the row's (or a
	 * profiled patch's) two numbers times the rain's WetSink, the variant's scales (LM5b) and the soft spot's SinkScale
	 * (AGTMudPatch::SoftScalesAt X; 1 off a soft-spot patch), in that order, so scales of 1 leave the product exactly as before.
	 * Every cap on the sinkage after it still applies. Update and GrandTour.Mud.SoftSpots's strokes call it.
	 */
	static void PatchSinkage(float BaseRate, float BaseCap, float WetSink, float RateScale, float CapScale, float SoftSinkScale, float& OutRate, float& OutCap);

	/** LM3a + wheel spray P2: what a contact in a profiled patch of this medium is in: snow, gravel (or neither: mud). The rule the
	 *  wheels' bInSnowPatch and bInGravelPatch are set by (GrandTour.Spray.Art checks it). */
	static void PatchMediumFlags(bool bInContact, bool bInProfiledPatch, uint8 Medium, bool& bOutSnow, bool& bOutGravel);
	TArray<FVector2D> LastStampXY;
	TArray<bool> LastStampValid;
	/** MR5: each wheel was in contact last frame (its LastStampXY then starts this frame's chunk-break capsule). */
	TArray<bool> LastChunkContact;

	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float RutLookAheadCm = 60.f;

	/** Growth while sitting still without wheelspin, as a fraction of the surface's SinkageRate. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 1))
	float SettleFraction = 0.3f;

	/** Sinkage grows at the full surface rate once the wheel rolls faster than this (cm/s). */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float PloughSpeed = 100.f;

	/** Cap on a wheel's rolling + ploughing + water drag as a fraction of its load, so deep mud at speed cannot explode the sim. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 2))
	float MaxRollingResistance = 0.9f;

	/** Extra growth at full wheelspin, as a multiple of the surface rate: spinning digs. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float WheelspinSinkageScale = 3.f;

	/** Slip magnitude (cm/s) at which wheelspin counts as full. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float SlipSaturation = 300.f;

	/** Bogged when this many wheels are past BogSinkageFraction, spinning, and the car is nearly stopped. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	int32 BogWheelCount = 2;

	UPROPERTY(EditAnywhere, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 1))
	float BogSinkageFraction = 0.9f;

	UPROPERTY(EditAnywhere, Category = "GT|Traction")
	float BogSpeedThreshold = 60.f;

	/** Torque left while bogged and spinning: throttle digs instead of moving. */
	UPROPERTY(EditAnywhere, Category = "GT|Traction", meta = (ClampMin = 0, ClampMax = 1))
	float BoggedTorqueScale = 0.35f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	TArray<FGTWheelTraction> Wheels;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bBogged = false;

	/** Weight / the sum of the spring forces in contact: what Chaos's tyre load must be multiplied by to be the true load (about 1.45 at rest). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float LoadCorrection = 1.f;

	/** Water over the front wheels' contact points, metres: what reaches the engine's intake. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float FrontWaterDepthM = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float MaxWaterDepthM = 0.f;

	/** Stage C: the channel in the mud field just ahead of the belly's box, 0..1 of the depth the belly would flatten to (the car's three sample points across the box's inner width). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float BellyChannel = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bBellyInMudPatch = false;

	/** LM3a: the snow standing over the belly's underside (AxleClearanceM over the deepest tyre's bottom) just ahead of its box, cm (the mean of the three points across it); 0 outside snow and down a ploughed channel. Every wheel in a snow patch drags BellyDragPerMetre x this. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	float BellySnowCm = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	bool bBellyInSnow = false;

	/** LM3a: the belly's plough this tick and in all, cm^3 (the field's PloughBelly). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Traction")
	double BellyPloughedCm3 = 0.0;

	UFUNCTION(BlueprintPure, Category = "GT|Traction")
	float GetMaxSinkageFraction() const;

private:
	/** The hull on the same pawn, looked up once (null: no lift); its LiftN comes off the load target (section 49). */
	UPROPERTY(Transient)
	TObjectPtr<UGTHullComponent> Hull = nullptr;

	bool bHullLooked = false;

	/** LM3b: SnowBaseRow, loaded once on the first update. */
	UPROPERTY(Transient)
	TObjectPtr<UGTSurfacePhysMaterial> SnowBase = nullptr;

	bool bSnowBaseLooked = false;

	/** The channel ahead of the belly from the field (BellyChannel), from the tyres in contact and last tick's sinkage. */
	void ReadBellyChannel(const UGTMudSubsystem* Mud, const UChaosWheeledVehicleMovementComponent& Movement, const FVector2D& Ahead, const FVector2D& Forward, const FVector2D& Right);
};
