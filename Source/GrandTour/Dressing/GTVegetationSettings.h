#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "GTVegetationSettings.generated.h"

/** LD5: the soft vegetation classes UGTVegetationSubsystem pushes (the LD4 spawner classes' GTVeg.Soft.* tags). */
UENUM(BlueprintType)
enum class EGTVegClass : uint8
{
	Brush,     // GTVeg.Soft.Brush: bushes, cover plants
	Sapling,   // GTVeg.Soft.Sapling: tree variants at size class Sapling
	Young,     // GTVeg.Soft.Young: tree variants at size class Young
};

/**
 * One soft class's dials (docs/LEG_DRESSING_PLAN.md LD5 table and LD5 v2). A break tilt of 0: never snaps. A snap is the
 * impact rule (tilt >= BreakTiltDeg with the car at BreakSpeedMs or faster) or a sustained push (tilt >= BreakTiltDeg
 * with p >= UGTVegetationSettings::SustainPush held for SustainHoldS).
 */
USTRUCT(BlueprintType)
struct FGTVegClassDials
{
	GENERATED_BODY()

	/** Full-push tilt: the target tilt is this x the push fraction p. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Vegetation", meta = (ClampMin = 0, ClampMax = 89))
	float MaxTiltDeg = 75.f;

	/** Snaps once the tilt reaches this (with the car at BreakSpeedMs or faster). 0: never. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Vegetation", meta = (ClampMin = 0, ClampMax = 89))
	float BreakTiltDeg = 0.f;

	/** The impact rule's car speed (horizontal), m/s. 0: no impact snap. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Vegetation", meta = (ClampMin = 0))
	float BreakSpeedMs = 0.f;

	/** The sustained push's hold: tilt at the break and p at SustainPush or more for this long, s. 0: no sustained snap. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Vegetation", meta = (ClampMin = 0))
	float SustainHoldS = 0.f;

	/** K: the resist force at full push and full speed factor, N (per instance, against the car's horizontal velocity). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Vegetation", meta = (ClampMin = 0))
	float StiffnessN = 1500.f;

	/** The cap on this class's summed resist, x the car's weight (m g); the total then has UGTVegetationSettings::ForceCapG. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Vegetation", meta = (ClampMin = 0))
	float CapG = 0.35f;

	/** m_debris: the snapped debris' mass, kg (0 for a class that never snaps). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Vegetation", meta = (ClampMin = 0))
	float DebrisMassKg = 0.f;

	bool CanSnap() const { return BreakTiltDeg > 0.f && DebrisMassKg > 0.f && (BreakSpeedMs > 0.f || SustainHoldS > 0.f); }
};

/**
 * Leg dressing LD5 (docs/LEG_DRESSING_PLAN.md): every number of the vegetation physics model in one place. Project
 * Settings > Game > GT Vegetation, saved to DefaultGame.ini [/Script/GrandTour.GTVegetationSettings]. The defaults are
 * the plan's; they are the owner's feel dials (the feel pass tunes them), not fitted to any test.
 */
UCLASS(Config = Game, DefaultConfig, meta = (DisplayName = "GT Vegetation"))
class GRANDTOUR_API UGTVegetationSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	UGTVegetationSettings();

	virtual FName GetCategoryName() const override { return TEXT("Game"); }

	const FGTVegClassDials& ForClass(EGTVegClass Class) const;

	// ---- the per-class table -----------------------------------------------------------------------------------
	/** Brush: 75 deg, never snaps, K 1500 N, capped at 0.15 mg. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Classes")
	FGTVegClassDials Brush;

	/** Sapling: 70 deg, snaps at 40 deg from 2.5 m/s or pushed (p >= 0.9) for 0.5 s, K 2500 N, capped at 0.20 mg, 30 kg of debris. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Classes")
	FGTVegClassDials Sapling;

	/** Young: 45 deg, snaps at 35 deg from 7 m/s (25 km/h) or pushed (p >= 0.9) for 2.0 s, K 16000 N, capped at 0.35 mg, 150 kg of debris. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Classes")
	FGTVegClassDials Young;

	// ---- contact ------------------------------------------------------------------------------------------------
	/** The car's footprint OBB is its body bounds plus this on every side (XY), cm. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Contact", meta = (ClampMin = 0))
	float FootprintPadCm = 30.f;

	/** Push fraction p = saturate(intrusion depth / this), cm. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Contact", meta = (ClampMin = 1))
	float PushDepthCm = 50.f;

	/** Contact radius, brush (v2): this x max(the mesh's bounds extent X, Y) x the instance's XY scale - the canopy's inner half. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Contact", meta = (ClampMin = 0))
	float BrushRadiusScale = 0.5f;

	/** Contact radius, trees (v2): the mesh's trunk capsule radius x the instance's XY scale, at least this, cm. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Contact", meta = (ClampMin = 0))
	float MinTrunkRadiusCm = 5.f;

	/** A tree mesh with no trunk capsule (none today; LD4 gives every variant one): radius = this x the instance's height. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Contact", meta = (ClampMin = 0))
	float TrunkRadiusPerHeight = 0.05f;

	/** An instance whose base is more than this below the car's body box (a different level of ground) is not touched, cm. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Contact", meta = (ClampMin = 0))
	float BelowBodyCm = 150.f;

	/** The spatial hash's cell, cm (2D). */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Contact", meta = (ClampMin = 50))
	float HashCellCm = 400.f;

	/** The proxy casts a shadow while bending (v2: no; the restored instance keeps its own). */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Bend")
	bool bProxyCastsShadow = false;

	// ---- bend ---------------------------------------------------------------------------------------------------
	/** The tilt rises toward its target with this time constant, s. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Bend", meta = (ClampMin = 0.001))
	float RiseTauS = 0.05f;

	/** After contact (or toward a lower target) the tilt springs back with this time constant, s. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Bend", meta = (ClampMin = 0.001))
	float RecoverTauS = 1.5f;

	/** Below this tilt after contact the instance is restored and its proxy goes back to the pool, deg. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Bend", meta = (ClampMin = 0))
	float RecoveredDeg = 1.f;

	/** Below this car speed the bend points away from the car's centreline instead of along its velocity, m/s. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Bend", meta = (ClampMin = 0))
	float LowSpeedBendMs = 0.5f;

	/** The proxy pool, which is also the active set: at most this many instances bend at once; the oldest recover first. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Bend", meta = (ClampMin = 1, ClampMax = 1024))
	int32 PoolSize = 128;

	// ---- resist -------------------------------------------------------------------------------------------------
	/** The total resist (after the per-class caps) is capped at this x the car's weight (0.35 x 2100 kg x g = about 7.2 kN). */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Resist", meta = (ClampMin = 0))
	float ForceCapG = 0.35f;

	/** v2 speed factor s(v) = SpeedFloor + (1 - SpeedFloor) x saturate(|v| / FullSpeedMs): crawling through is easier than ramming. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Resist", meta = (ClampMin = 0, ClampMax = 1))
	float ResistSpeedFloor = 0.3f;

	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Resist", meta = (ClampMin = 0.1))
	float ResistFullSpeedMs = 10.f;

	// ---- snap ---------------------------------------------------------------------------------------------------
	/** The sustained push's p (v2): the tilt at the break and p at least this, held for the class's SustainHoldS. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Snap", meta = (ClampMin = 0, ClampMax = 1))
	float SustainPush = 0.9f;

	/** The debris' impulse = m_debris x the car's speed x this; the car gets the opposite. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Snap", meta = (ClampMin = 0))
	float DebrisImpulseScale = 0.8f;

	/** Debris freezes when its body sleeps or after this many seconds. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Snap", meta = (ClampMin = 0.1))
	float DebrisFreezeS = 20.f;

	/** At most this many debris actors exist; past it the oldest frozen one becomes a no-collision ISM instance. */
	UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Snap", meta = (ClampMin = 1, ClampMax = 256))
	int32 MaxDebris = 24;
};
