#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Vehicle/GTConditionComponent.h"
#include "GTBodyStateComponent.generated.h"

class UGTTractionComponent;

/**
 * Surface state of the body (ARCHITECTURE 6b): dirt per damage region from wheel spray by
 * surface tag (mud fast and wet, dirt and sand as dust, snow as snow, tarmac nothing), wetness
 * that dries over time, and snow that melts. Spray needs the wheel to roll (or spin): a wheel's
 * own arch takes the most, its side half, its end of the car less, the roof only at speed, the
 * windscreen a little from the front wheels. UGTBodyComponent writes the values into the vehicle
 * and glass materials every tick. Rain (M3) and the base wash (M4) add sources and sinks here.
 *
 * MudRunner MR2 (docs/MUDRUNNER_LESSONS_PLAN.md MR2, VEHICLE_BUILD_SYSTEM 80): a muddy vehicle, behind gt.Mud.CarMud (1 by
 * default; 0 is the rule above exactly). The per-region Dirt carries the mud coat (MudCoat: dust still adds to it and reads as
 * dried mud). Sources: a wheel on the Mud / Bog surface (a bog's patch or a mud lane; not a ford's riverbed, a profiled patch
 * on Dirt) cakes its tyre (TyreCoat, about 0.9 in 2 s;
 * MR1's MudLoad keeps it at least that), coats its side's sill and its end's bumper by speed x sinkage and its arch by speed x
 * sinkage plus spin; spin flings mud onto the wheel's end and arch (the front axle the front bumper and front wings, the rear
 * the rear and rear arches); the belly dragging (sinkage past the axles) coats the sills; a thrown blob hitting the body
 * (UGTSprayComponent's own traces) coats the region it hits, the windscreen only this way. The mud line (MudLineCm, above the
 * wheel bottoms) is the most over the last 10 s of the deeper of the sinkage and the water (measured over the sunk contact, so
 * it holds the sinkage) + 20 cm, plus 30 cm while spinning; the coat's own line
 * (CoatLineCm, what the material draws) rises to it while mud is laid and falls only to a wash, so dried mud stays. MudWet is 1
 * with fresh mud and dries to 0 over MudDrySeconds (90 s), never under the weather's wetness. Removal: a ford's water (not a
 * bog's rut water) over WashDepthCm at the wheels washes below its waterline (WashCm, WashAmount: the material's clean band; a region wholly under the water loses
 * its coat) at 0.3/s moving and 0.1/s still, a tyre in it at 0.5/s; rain at 0.01/s x rain; nothing else.
 *
 * MR2b (docs/MUDRUNNER_LESSONS_PLAN.md MR2b, VEHICLE_BUILD_SYSTEM 82): per wheel a spray fan. FanCoat (0..1) rises with the
 * wheel's spin (its tread's speed over the ground's, either way) and its speed x sinkage through mud, and is washed like the coat
 * (its arch wholly under a ford's water, rain, Wash()); FanDir is the way the tread has been throwing mud (the car's speed plus
 * the slip, weighted by how much it threw: FanSide): +1 forward, so the fan opens behind the arch, -1 backward. M_GT_Vehicle draws each arch's fan of droplets from them
 * (FanCoat / FanDir, FL FR RL RR).
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTBodyStateComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTBodyStateComponent();

	void Update(float DeltaSeconds, const UGTTractionComponent& Traction, float ForwardSpeed);

	/** Dirt 0..1 on a region; structural parts (None) get half the average. */
	UFUNCTION(BlueprintPure, Category = "GT|BodyState")
	float GetDirt(EGTDamageRegion Region) const;

	UFUNCTION(BlueprintPure, Category = "GT|BodyState")
	float GetAverageDirt() const;

	/** The base wash: dirt and snow gone, body dry. */
	UFUNCTION(BlueprintCallable, Category = "GT|BodyState")
	void Wash();

	UFUNCTION(BlueprintPure, Category = "GT|BodyState")
	FString Describe() const;

	// ---- MudRunner MR2 ----------------------------------------------------------------------------------------------------
	/** gt.Mud.CarMud (1 by default). */
	static bool IsCarMudEnabled();

	/** A thrown mud blob of VolumeCm3 hit the body at LocalPoint (car space) on a face whose outward normal is LocalNormal. */
	void AddThrowHit(const FVector& LocalPoint, const FVector& LocalNormal, double VolumeCm3);

	/** The coat the material lays at HeightCm above the wheel bottoms on Region, before its splatter breakup (the tests' mirror). */
	UFUNCTION(BlueprintPure, Category = "GT|BodyState|Mud")
	float GetCoatAt(EGTDamageRegion Region, float HeightCm) const;

	UFUNCTION(BlueprintPure, Category = "GT|BodyState|Mud")
	float GetTyreCoat(int32 Wheel) const { return TyreCoat.IsValidIndex(Wheel) ? TyreCoat[Wheel] : 0.f; }

	/** MR2b: a wheel's spray fan, 0..1, and the side it opens to (+1 behind the arch: its tread last moved forward in mud; -1 in front). */
	UFUNCTION(BlueprintPure, Category = "GT|BodyState|Mud")
	float GetFanCoat(int32 Wheel) const { return FanCoat.IsValidIndex(Wheel) ? FanCoat[Wheel] : 0.f; }

	UFUNCTION(BlueprintPure, Category = "GT|BodyState|Mud")
	float GetFanDir(int32 Wheel) const { return FanDir.IsValidIndex(Wheel) ? FanDir[Wheel] : 1.f; }

	UFUNCTION(BlueprintPure, Category = "GT|BodyState|Mud")
	int32 GetThrowHits() const { return ThrowHits; }

	UFUNCTION(BlueprintPure, Category = "GT|BodyState|Mud")
	int32 GetGlassHits() const { return GlassHits; }

	/** The span of a region, cm above the wheel bottoms (a region wholly under the water loses its coat). */
	static FVector2D RegionSpanCm(EGTDamageRegion Region);

	/** The tests' setter. */
	void SetDirtForTest(EGTDamageRegion Region, float Value);

	// ---- rates per second at full spray (a wheel rolling above SprayFullSpeed) ----------------
	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float MudDirtRate = 0.15f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float DustDirtRate = 0.05f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float MudWetRate = 0.3f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float SnowRate = 0.25f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float SnowWetRate = 0.1f;

	/** Wheel speed (cm/s) at which spray is full. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float SprayFullSpeed = 500.f;

	/** Extra spray at full wheelspin, as a fraction of full spray. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float WheelspinSprayScale = 1.f;

	/** The roof only catches spray above this speed (cm/s). */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float RoofSpraySpeed = 1500.f;

	/** Wetness lost per second while nothing wets the car. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float DryRate = 0.01f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState")
	float MeltRate = 0.02f;

	// ---- MR2 rates (proposed; the owner names them after looking) --------------------------------------------------------
	/** The car's speed at which mud's speed factor is full, cm/s. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float MudFullSpeed = 300.f;

	/** A tyre in mud cakes with this time constant, s (0.9 in about 1.8 s). */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float TyreCoatSeconds = 0.8f;

	/** Per second at full speed x sinkage factor: a side's sill (shared by its two wheels), an end's bumper (its two), an arch (its one). */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float SillMudRate = 0.3f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float BumperMudRate = 0.15f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float ArchMudRate = 0.35f;

	/** Per second at full spin: the spinning wheel's end and arch (front: the front bumper and front wing; rear: the rear and rear arch). */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float FlingRate = 0.4f;

	/** Per second while the belly drags (sinkage past the axles): the sills. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float BellyMudRate = 0.4f;

	/** A blob hit coats its region by its volume x this, within BlobHitMin..Max. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float BlobHitCoatPerCm3 = 5.e-5f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float BlobHitMin = 0.003f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float BlobHitMax = 0.05f;

	/** The mud line: sinkage + water + this, plus MudLineSpinCm while a wheel spins (over MudLineSpinShare), the most over MudLineWindowS. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float MudLineBaseCm = 20.f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float MudLineSpinCm = 30.f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float MudLineSpinShare = 0.2f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float MudLineWindowS = 10.f;

	/** Dust settles this high on the body (its coat line), cm above the wheel bottoms. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float DustLineCm = 70.f;

	/** Water deeper than this at a wheel washes, cm; below its waterline at WashMovingRate (over WashMovingSpeed cm/s) or WashStillRate; a tyre at TyreWashRate. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float WashDepthCm = 5.f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float WashMovingRate = 0.3f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float WashStillRate = 0.1f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float WashMovingSpeed = 50.f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float TyreWashRate = 0.5f;

	/** Fresh mud thrown at speed or by spin fills a washed band back at this per second (x the strongest wheel's speed x sinkage + spin, 0..1). */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float WashRefillRate = 0.5f;

	/** Rain washes every region and tyre at this x the rain per second. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float RainWashRate = 0.01f;

	/** MudWet falls from 1 to 0 over this, s. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float MudDrySeconds = 90.f;

	/** MR2b: a wheel's FanCoat rises per second by this x its spin (the tread's speed over the ground's / 300 cm/s, 0..1) and by FanRollRate x its speed x sinkage factor, in mud. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float FanSpinRate = 0.8f;

	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float FanRollRate = 0.3f;

	/** MR2b: a fan's side (FanSide, -1..1) moves toward the way the tread throws by this x the fan's feed per second: a full spin turns it from one side to the other in about 1.25 s. */
	UPROPERTY(EditAnywhere, Category = "GT|BodyState|Mud")
	float FanSideRate = 2.f;

	// ---- state ---------------------------------------------------------------------------------
	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState")
	float Wetness = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState")
	float Snow = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState")
	float MaxWetness = 0.f;

	/** MR2: the rain on the car 0..1 (the pawn sets it from the weather before Update). */
	UPROPERTY(BlueprintReadWrite, Category = "GT|BodyState|Mud")
	float Rain = 0.f;

	/** MR2: how high fresh mud reaches, cm above the wheel bottoms (the deeper of sinkage and water + base (+ spin), the most over the last MudLineWindowS). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	float MudLineCm = 0.f;

	/** MR2: how high the coat on the body reaches (MudLineCm's high mark while mud is laid; only a wash lowers it). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	float CoatLineCm = 0.f;

	/** MR2: the waterline of the last wash, cm above the wheel bottoms, and how clean below it (0..1). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	float WashCm = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	float WashAmount = 0.f;

	/** MR2: 1 fresh and wet, 0 dried. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	float MudWet = 0.f;

	/** MR2: per wheel (FL, FR, RL, RR), the tyre's cake 0..1. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	TArray<float> TyreCoat;

	/** MR2b: per wheel (FL, FR, RL, RR), the spray fan's coat 0..1 and its side (+1 behind the arch, -1 in front). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	TArray<float> FanCoat;

	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	TArray<float> FanDir;

	/** MR2b: per wheel, where its mud went, -1 (in front) .. 1 (behind), weighted by how much was thrown; FanDir is its sign. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|BodyState|Mud")
	TArray<float> FanSide;

private:
	void AddDirt(EGTDamageRegion Region, float Amount);
	void UpdateLegacy(float DeltaSeconds, const UGTTractionComponent& Traction, float ForwardSpeed);
	void UpdateMud(float DeltaSeconds, const UGTTractionComponent& Traction, float ForwardSpeed);

	UPROPERTY(VisibleAnywhere, Category = "GT|BodyState")
	TMap<EGTDamageRegion, float> Dirt;

	static constexpr int32 LineBuckets = 40;
	float LineBucketMax[LineBuckets] = {};
	int64 LineBucketId[LineBuckets] = {};
	double Clock = 0.0;
	int32 ThrowHits = 0;
	int32 GlassHits = 0;
};
