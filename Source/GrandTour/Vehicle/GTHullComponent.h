#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GTHullComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;
class UGTTractionComponent;

/**
 * The car's body in water (docs/WATER_PLAN.md, stage W1): a box the current pushes on.
 *
 * Chaos knows nothing about water, so the body is treated as a box HullLengthM x HullWidthM standing on the wheels'
 * contact plane, HullRoofM tall, with the sill at HullFloorM: under the sill the side is wheels, axles and engine, so
 * only UnderbodyFill of it catches the water; over it the side is body and catches all of it. Five points (the four
 * corners and the centre) are sampled through UGTWaterSubsystem every tick, each carrying a fifth of the projected
 * area, so a pitched or rolled car takes the push where it is actually in the water. At each the force is
 * 0.5 x rho x Cd x A x |v_rel| x v_rel with v_rel the flow minus that point's own velocity, applied at the middle of
 * the submerged part; the sum is capped at MaxWaterForceG x the weight, as the wheels' drag is capped for mud.
 *
 * Stage W2 adds the lift. The same five samples each carry a fifth of HullVolumeM3 (the volume the body displaces at
 * full immersion, the flooding of a real car already taken out of it); a sample's share is submerged in proportion to
 * how far the water stands over its keel - HullKeelM above the wheels' bottoms, the axle line, where displacement
 * starts - through to HullRoofM, and rho x g x that volume pushes straight up at the sample's own point, so a pitched
 * or rolled car takes more lift on its deeper corners and that is the righting moment (no extra torque is applied).
 * The sum is capped at FloatCapG x the weight. LiftDampingRatio damps the bob: the drag above has its vertical
 * component zeroed, so without it the float is an undamped spring and the car never settles.
 *
 * The traction's WaterBuoyancyGripLoss stand-in is off (0) since W2: the lift takes the weight off the springs and
 * the load the traction reads follows. The cvar gt.Water.Hull 0 switches the whole body's water off (drag and lift),
 * gt.Water.Buoyancy 0 only the lift.
 *
 * Stage WS2 makes the car a source of the water's own motion. Every tick the hull's footprint is stamped on the
 * water field as a lid - the metres of each cell's column the body holds - and so is each wheel in contact, and the
 * solver pushes the water out from under them until the effective surface equalises again (FGTWaterField). Nothing
 * here changes what the car feels: the field hands back the effective surface, which where nothing moves is the same
 * level W1 and W2 read. gt.Water.Lids 0 takes the stamps off.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTHullComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTHullComponent();

	virtual void BeginPlay() override;

	/** Called by AGTCarPawn::Tick after the traction (it reads the wheels' contact points for the hull's base plane). */
	void Update(float DeltaSeconds, const UChaosWheeledVehicleMovementComponent& Movement, const UGTTractionComponent& Traction);

	/** The hull box, metres. Lengths are the body's; the heights are over the wheels' bottoms (the contact plane). */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float HullLengthM = 4.4f;

	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float HullWidthM = 1.9f;

	/** The sill: under it the side is wheels, axles and engine (UnderbodyFill of it), over it solid body. */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float HullFloorM = 0.45f;

	/** The roof: water deeper than this over a corner adds no more area there. */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float HullRoofM = 1.9f;

	/** How much of the box's side below the sill is solid enough to push on. */
	UPROPERTY(EditAnywhere, Category = "GT|Hull", meta = (ClampMin = 0, ClampMax = 1))
	float UnderbodyFill = 0.45f;

	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float DragCd = 1.f;

	/** kg/m3. */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float WaterDensity = 1000.f;

	/** The sim guard: the whole water push on the chassis, as a multiple of the car's weight. */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float MaxWaterForceG = 1.5f;

	// ---- stage W2: the lift -------------------------------------------------------------------------------------
	/**
	 * The volume the body displaces at full immersion, m3, the sealed fraction already inside it: a car floods, so
	 * this is not the box's 12 m3. 3.4 (the plan's starting point was 3.0): at the test's raised ford the water stands
	 * 1.14 m over the keel, and a 2100 kg car needs 3.13 m3 to float there at all, so 3.0 would have left it resting
	 * on the bed at 0.97 of neutral - and the traction's load correction reads a light spring back up to the full
	 * weight until the springs fall under a fifth of it, so "nearly floating" is the one state whose wheel load cannot
	 * be measured. 3.4 lifts the car 9 cm clear instead.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float HullVolumeM3 = 3.4f;

	/** A multiplier on the displaced volume: lower it and the car floods more and floats less. */
	UPROPERTY(EditAnywhere, Category = "GT|Hull", meta = (ClampMin = 0, ClampMax = 1))
	float SealedFraction = 1.f;

	/** The sim guard on the lift: it never pushes up harder than this many times the car's weight. */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float FloatCapG = 1.5f;

	/** Where the displacement starts over the wheels' bottoms, m (the axle line, so the underbody displaces). */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float HullKeelM = 0.2f;

	/**
	 * Damping on the lift as a fraction of critical for the float's own spring (rho x g x V / (roof - keel) against
	 * the car's mass), 0 for none. The drag above zeroes its vertical component, so the lift on its own is an
	 * undamped spring: a car dropped into deep water would bob at its natural period for ever.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Hull", meta = (ClampMin = 0, ClampMax = 2))
	float LiftDampingRatio = 0.5f;

	// ---- stage WS2: the car as a lid on the water field --------------------------------------------------------
	/**
	 * How much of the hull's box is solid, for the water it pushes aside. A car is not a brick: the box is
	 * length x width x (roof - keel) = 14.2 m3 where the lift displaces HullVolumeM3 3.4, so 0.24 = 3.4 / 14.2 makes
	 * the water the field moves out of the way exactly the water W2's lift stands on, at any immersion (both are
	 * linear in it). 1 would treat the body as solid and push four times as much.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Hull", meta = (ClampMin = 0, ClampMax = 1))
	float LidFill = 0.24f;

	/**
	 * How far upstream of the hull the drag reads the current, metres. A drag coefficient is defined against the
	 * FREE stream, and since WS2 the water at the car is not free: its own lid pushes the river around it and piles a
	 * crest against its upstream side, so the cells the five samples sit in run slower than the river does. Read
	 * there, the hull took 1,777 N in the raised ford against W2's 2,398 and the carried car drifted 2.23 m in ten
	 * seconds against 4.52. Four metres is one hull length clear of the box; if the point is dry or outside the
	 * sheet, the local reading stands.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Hull")
	float FreeStreamM = 4.f;

	/** The volume the hull and the wheels stamped on the field this tick, m3 (0 out of the water). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	float LidVolumeM3 = 0.f;

	/** The car's mass, kg, read once at BeginPlay from the mesh's body instance (0 until then). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	float BodyMassKg = 0.f;

	/** The lift applied this tick, newtons up (after the cap, damping not in it). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	float LiftN = 0.f;

	/** The water over the keel at the centre sample, metres; negative when the keel stands above the water. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	float KeelDepthM = 0.f;

	/** Where the keel floats when the lift equals the weight: (mass / (rho x V x sealed)) x (roof - keel), metres. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	float PredictedNeutralKeelDepthM = 0.f;

	/** True when FloatCapG bit this tick. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	bool bLiftCapped = false;

	/** The deepest of the five samples this tick, metres of water over the hull's bottom there. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	float SubmergedHeightM = 0.f;

	/** The force applied to the chassis this tick, newtons (world). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	FVector LastWaterForce = FVector::ZeroVector;

	/** |LastWaterForce|, newtons. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	float LastWaterForceN = 0.f;

	/** The projected area the five samples added up to this tick, m2 (0 out of the water). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	float LastAreaM2 = 0.f;

	/** The flow at the hull's centre this tick, m/s. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	FVector2D LastFlowMps = FVector2D::ZeroVector;

	/** True when the cap bit this tick (the sum wanted more than MaxWaterForceG x the weight). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Hull")
	bool bCapped = false;
};
