#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GTSprayComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;
class UGTBodyStateComponent;
class UGTConditionComponent;
class UPrimitiveComponent;
class UGTMudSubsystem;
class UGTMudSplatSubsystem;
class UGTHullComponent;
class UGTTractionComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UNiagaraComponent;
class UNiagaraSystem;
class UGTSurfacePhysMaterial;
struct FWheelStatus;
struct FGTWheelTraction;

UENUM(BlueprintType)
enum class EGTSprayKind : uint8
{
	Mud,
	Dust,
	Snow,
	Steam,
	/** Water stage W4: a wheel's splash in water and the hull's bow spray. Its own emitter, so it can take a water colour. */
	Water,
	Count UMETA(Hidden)
};

/**
 * Greybox wheel spray (ARCHITECTURE 6a: spray and snow-kick emitters by surface tag). A small
 * CPU particle pool per kind, drawn as instanced spheres: mud throws opaque brown blobs that
 * fall fast, dirt and sand raise slow translucent dust that grows and drifts, snow kicks white
 * puffs. A wheel emits once it rolls above SprayFullSpeed or spins, at MudRate / DustRate /
 * SnowRate per second, from its contact point, backwards and up relative to the car. A damaged
 * radiator (below half health) steams from the bonnet: grey puffs that rise and drift with the car.
 * Water stage W4 (docs/WATER_PLAN.md) adds a water state on top, additively: a wheel standing in more than
 * SplashDepthM of the one water query's water throws pale droplets at SplashRate x speed x depth, and a hull whose
 * SubmergedHeightM is over BowSprayHeightM throws a bow spray off its front edge at BowSprayRate x speed x
 * submersion. Nothing on the on-foot character.
 * Replace the drawing with Niagara in the art pass; the emission rules are what carry over.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTSprayComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTSprayComponent();

	virtual void BeginPlay() override;

	void Update(float DeltaSeconds, const UGTTractionComponent& Traction, const UChaosWheeledVehicleMovementComponent& Move, float ForwardSpeed,
	            const UGTConditionComponent& Condition, const UGTHullComponent* Hull = nullptr);

	UFUNCTION(BlueprintPure, Category = "GT|Spray")
	int32 GetLiveCount(EGTSprayKind Kind) const;

	UFUNCTION(BlueprintPure, Category = "GT|Spray")
	int32 GetTotalSpawned() const { return TotalSpawned; }

	UFUNCTION(BlueprintPure, Category = "GT|Spray")
	FString Describe() const;

	/** Particles per kind; dead ones sit at zero scale. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray")
	int32 PoolPerKind = 120;

	/** Wheel speed (cm/s) at which emission is full. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray")
	float SprayFullSpeed = 500.f;

	/** Particles per wheel per second at full spray. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray")
	float MudRate = 40.f;

	UPROPERTY(EditAnywhere, Category = "GT|Spray")
	float DustRate = 25.f;

    /** Runtime opt-in owned by a placed vehicle-surface-effects coordinator.
     * Suppresses only replaced cosmetic layers; volume-carrying clumps are unchanged. */
    UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category="GT|Spray|Integration")
    bool bExternalDustEffects = false;
    UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category="GT|Spray|Integration")
    bool bExternalMudEffects = false;

	UPROPERTY(EditAnywhere, Category = "GT|Spray")
	float SnowRate = 30.f;

	/** Steam puffs per second with a dead radiator; scales with the damage below half health. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray")
	float SteamRate = 25.f;

	/** Where the steam leaves, car space: the front of the bonnet. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray")
	FVector SteamOrigin = FVector(170.f, 0.f, 105.f);

	// ---- water stage W4 (docs/WATER_PLAN.md): the thrown water -------------------------------------------
	// Additive: the mud, dust and snow branches are untouched, so a wheel on a ford's muddy bed still throws what it
	// threw before and the spray test's lane counts do not move. Nothing here touches the on-foot character.

	/** A wheel throws water once its own water is deeper than this, metres (the one water query's depth at its contact). */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float SplashDepthM = 0.025f;

	/** And once the car is moving faster than this, m/s. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float SplashSpeedMps = 0.35f;

	/** Droplets per wheel per second at full speed and full depth. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float SplashRate = 80.f;

	/** Where the speed's share of the rate saturates, m/s. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float SplashFullSpeedMps = 5.f;

	/** Where the depth's share saturates, metres. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float SplashFullDepthM = 0.25f;

	/** The hull throws a bow spray once its deepest submerged height is over this, metres. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float BowSprayHeightM = 0.10f;

	/** And once the car is moving faster than this, m/s. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float BowSprayMps = 0.6f;

	/** Droplets per second at full speed and full submersion. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float BowSprayRate = 100.f;

	/** Where the speed's share of the bow rate saturates, m/s. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float BowSprayFullSpeedMps = 4.f;

	/** Where the submerged height's share saturates, metres. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	float BowSprayFullHeightM = 0.4f;

	/** Where the bow spray leaves, car space: the front edge at about the keel. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Water")
	FVector BowSprayOrigin = FVector(220.f, 0.f, 20.f);

	/** True while any wheel is throwing water this tick. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Water")
	bool IsWheelSplashing() const { return bWheelSplashing; }

	/** True while the hull is throwing a bow spray this tick. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Water")
	bool IsBowSpraying() const { return bBowSpraying; }

	/** The water state in one line, for the tests and the pictures' logs. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Water")
	FString DescribeWater() const;

	/** How many wheels threw water this tick, and the deepest of them, metres. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Water")
	int32 GetWheelsSplashing() const { return SplashWheels; }

	UFUNCTION(BlueprintPure, Category = "GT|Spray|Water")
	float GetSplashDeepestM() const { return SplashDeepestM; }

	/** The wheels' droplets per second this tick, added up over them. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Water")
	float GetSplashRateNow() const { return SplashRateNow; }

	/** The hull's submerged height the bow spray read this tick, metres, and the rate it asked for. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Water")
	float GetBowSubmergedM() const { return BowSubmergedM; }

	UFUNCTION(BlueprintPure, Category = "GT|Spray|Water")
	float GetBowRateNow() const { return BowRateNow; }

	// ---- LM2a, the throw (docs/LIVING_MUD_PLAN.md LM2a): the mud emission spends each wheel's FGTWheelTraction::ThrownCm3
	// on blobs that carry it. Additive: the volumeless spray above is unchanged.

	/** A thrown blob is ThrowBlobMinCm..ThrowBlobMaxCm across and carries 4/3 pi r^3 x ThrowBlobFill of mud. LM2c: 4-16 cm by a power law, min + (max - min) u^ThrowSizePower (LM2a: 6-14 uniform). */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowBlobMinCm = 4.f;

	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowBlobMaxCm = 16.f;

	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowSizePower = 2.5f;

	/** LM2c: each blob's heading off straight back, degrees either way, and its own throw speed (not the car's share) scaled 1 +- ThrowSpeedSpread. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowHeadingSpreadDeg = 25.f;

	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowSpeedSpread = 0.5f;

	/**
	 * LM2c: the blobs leave at random intervals, exponential in the thrown volume (a Poisson stream), at the same mean rate
	 * as LM2a's (the volume conserves it). The stream's rate rides on what is waiting at the wheel: it settles at about
	 * ThrowReserveBlobs mean blobs' worth, so the mud that waits stays small and nothing is made or lost.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowReserveBlobs = 3.f;

	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowBlobFill = 0.6f;

	/** At most this many blobs per wheel per tick (the rest waits as the wheel's pending volume). */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	int32 ThrowBlobsPerTick = 6;

	/** How fast the spin flings a blob: backwards this share of the spin speed (a random 0.4-0.8 of it scaled by this) on top of today's 0.3-0.6 x the car's speed, and up 150-350 cm/s plus ThrowUpPerSpin x the spin. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowBackPerSpin = 1.f;

	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowUpPerSpin = 0.3f;

	/** A thrown blob still airborne after this long is counted lost. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float ThrowBlobMaxLifeS = 3.f;

	/** LM2a readouts: thrown volume emitted, landed on a patch (AGTMudPatch::DepositThrown), lost outside every patch, and still waiting at the wheels, cm^3; blob counts. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	double GetThrowEmittedCm3() const { return ThrowEmittedCm3; }
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	double GetThrowLandedCm3() const { return ThrowLandedCm3; }
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	double GetThrowLostCm3() const { return ThrowLostCm3; }
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	double GetThrowPendingCm3() const { return ThrowPendingCm3; }
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetThrowBlobsEmitted() const { return ThrowBlobsEmitted; }
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetThrowBlobsLanded() const { return ThrowBlobsLanded; }
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetThrowBlobsLost() const { return ThrowBlobsLost; }
	/** LM3b: the thrown blobs that left through the Snow kind (a wheel in a snow patch), of GetThrowBlobsEmitted. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetThrowBlobsSnow() const { return ThrowBlobsSnow; }
	/** The readouts back to zero (the check script, before the spin test). */
	UFUNCTION(BlueprintCallable, Category = "GT|Spray|Throw")
	void ResetThrowStats();

	// ---- MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1 item 3): splats. A volume-carrying blob outside every patch is
	// traced along its path once a frame (UGTMudSplatSubsystem::ReserveTrace, 64 a frame), from where it was last traced; a hit
	// on the landscape or a static mesh splats there (UGTMudSplatSubsystem::Splat), a hit inside a patch's box lands there as
	// before. Its mud still counts as lost to the fields (the books LM2a keeps), and as splatted below. gt.Mud.Splats 0: as
	// before MR1. MR2 housekeeping 4: traced only while descending within UGTMudSplatSubsystem::TraceBandCm of the surface under
	// it (a patch's field, or the landscape's height, a heightfield lookup); one that goes under the landscape's height splats
	// there without a trace.
	/** How far below its throw's contact a blob outside every patch may fall before it is lost (while splats are on), cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Throw")
	float SplatFallCm = 400.f;

	/** MR1: the thrown volume and blobs that splatted outside every patch (a part of the lost). */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	double GetThrowSplattedCm3() const { return ThrowSplattedCm3; }
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetThrowBlobsSplatted() const { return ThrowBlobsSplatted; }

	// ---- MudRunner MR2 (docs/MUDRUNNER_LESSONS_PLAN.md MR2 item 2): a thrown mud blob that meets the car's own body (its
	// collision, the chassis) coats the region it hits (UGTBodyStateComponent::AddThrowHit) and is gone; one that meets the
	// underside coats it and drops back, its mud landing in the field as before. Traced only while the
	// blob is inside the body's local bounds grown by BodyTraceMarginCm, against that one component, at most
	// MaxBodyTracesPerFrame a frame for this car (its own budget; a refused blob traces the longer path next frame). Its mud
	// counts as lost to the fields, as a splat does. gt.Mud.CarMud 0: no body traces (as before MR2).
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Spray|Throw")
	int32 MaxBodyTracesPerFrame = 32;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Spray|Throw")
	float BodyTraceMarginCm = 30.f;

	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetBodyTraces() const { return BodyTraces; }

	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetBodyTracesCapped() const { return BodyTracesCapped; }

	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetThrowBlobsOnCar() const { return ThrowBlobsOnCar; }

	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	double GetThrowOnCarCm3() const { return ThrowOnCarCm3; }

	/** Blobs that met the underside: they coat it and drop back (not counted in GetThrowBlobsOnCar; their mud still lands). */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Throw")
	int32 GetThrowBlobsUnderCar() const { return ThrowBlobsUnderCar; }

	// ---- Wheel spray P2 (docs/WHEEL_SPRAY_PLAN.md): the painterly layers, drawing only ------------------------------------------
	// gt.Spray.Art 0 is today's greybox exactly; gt.Spray.Fine 0 turns the Niagara layers off; gt.Spray.FineScale scales their rates.
	// Nothing here touches the CPU pools' emission, their random stream or the thrown volumes.

	/** Niagara MudDroplets per second per wheel = this x the Mud kind's current emission rate on that wheel. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Art")
	float FineMudPerRate = 6.f;

	/** Niagara GravelGrit per second per wheel in a gravel patch = this x max(speed factor, slip factor) (the Dust kind's factors).
	 *  P2b: 30 (P2's 10 was invisible). */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Art")
	float FineGritPerFactor = 30.f;

	/** Niagara GravelDust per second per wheel in a gravel patch = this x the same factor x the dryness (0 from wetness 0.6).
	 *  P2b: 8 (P2's 2.5 was invisible). */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Art")
	float FineDustPerFactor = 8.f;

	/** The bursts' noise, Hz: every rate rides b(t) = (0.3 + 1.4 n(t))^2 over its mean, n a per-wheel smooth noise. */
	UPROPERTY(EditAnywhere, Category = "GT|Spray|Art")
	float BurstHz = 3.f;

	/** Live particles of one painterly emitter (0 MudDroplets, 1 GravelGrit, 2 GravelDust) over all the wheels. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Art")
	int32 GetFineLiveCount(int32 Emitter) const;

	/** The rate last given to a wheel's emitter (0 MudDroplets, 1 GravelGrit, 2 GravelDust), per second, bursts and FineScale in. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Art")
	float GetFineRate(int32 Wheel, int32 Emitter) const;

	/** Live particles of one emitter of any Niagara component (P2b: the checks' own test components). */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Art")
	static int32 GetNiagaraLiveCount(UNiagaraComponent* Component, int32 Emitter);

	/** The CPU Mud kind's blobs drawn as clumps this frame (0 at gt.Spray.Art 0). */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Art")
	int32 GetClumpsDrawn() const { return ClumpsDrawn; }

	UFUNCTION(BlueprintPure, Category = "GT|Spray|Art")
	static bool IsArtEnabled();

	UFUNCTION(BlueprintPure, Category = "GT|Spray|Art")
	static bool IsFineEnabled();

	/** The three rates for one wheel (GrandTour.Spray.Art). */
	struct FFineRates
	{
		float Mud = 0.f;
		float Grit = 0.f;
		float Dust = 0.f;
	};
	/** bMud: Mud or Bog tag; MudKindRate the Mud kind's current CPU rate; bGravel: in a gravel patch; Speed and Slip the Dust kind's
	 *  factors; Burst b(t). Zero when bFine is false. */
	static FFineRates FineRates(bool bMud, float MudKindRate, bool bGravel, float SpeedFactor, float SlipFactor, float Wetness, float Burst,
		bool bFine, float FineScale, float MudPerRate, float GritPerFactor, float DustPerFactor);
	/** b(t) for a wheel: (0.3 + 1.4 n)^2 over its long-run mean, so its mean is 1. n: a smooth noise at Hz from stratified levels. */
	static float BurstFactor(int32 Wheel, double TimeS, float Hz);
	/** Which of the eight clumps draws a particle (deterministic per id). */
	static int32 ClumpMeshFor(uint32 ParticleId);
	/** The spray's mud colour for a patch's variant slice: its bog bake's mean x 0.8 (wet), linear; Deep (2) exempt (P2d: its bake is
	 *  already the darkest, as MR4's follow-up). */
	static FLinearColor MudTintFor(int32 VariantSlice);
	/** Benmore B1b: the wheel's contact surface when it throws gravel (a UGTSurfacePhysMaterial with bGravelSpray: the grit and dust
	 *  layers as a gravel patch, in its tints where set; no grey Dust spheres at gt.Spray.Art 1), else null (also off the ground). */
	static const UGTSurfacePhysMaterial* GravelSpraySurface(const FWheelStatus& Contact);
	/** Authored classification wins over generic road collision materials. */
	static bool IsGravelContact(const FGTWheelTraction& Wheel, bool bLegacyGravel);

	/** P2d: the BaseVelocity last given to a wheel's painterly emitter (world cm/s; the checks' droplet-height estimate). */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Art")
	FVector GetFineBaseVelocity(int32 Wheel) const { return FineBaseVelocity.IsValidIndex(Wheel) ? FineBaseVelocity[Wheel] : FVector::ZeroVector; }

	/** P2d muddy rut splash: the CPU Water spray's live particles tinted by a Mud patch's rut water this frame. */
	UFUNCTION(BlueprintPure, Category = "GT|Spray|Art")
	int32 GetMuddySplashCount() const { return MuddySplashCount; }

private:
	friend class FGTSprayUploadTest;
	struct FParticle
	{
		FVector Position = FVector::ZeroVector;
		FVector Velocity = FVector::ZeroVector;
		float Life = 0.f;
		float MaxLife = 1.f;
		float Size = 10.f;
		float Growth = 0.f;
		float GroundZ = 0.f;
		/** Water-only sheet / droplet / mist shape and optical density. */
		FVector WaterShape = FVector(1.f);
		float WaterOpacity = 1.f;
		float WaterFamily = 0.f;
		/** LM2a: the mud a thrown blob carries, cm^3 (0: the volumeless spray). */
		double VolumeCm3 = 0.0;
		/** MR1: where the blob's path was last traced from (or where it last was inside a patch's box). */
		FVector TraceFrom = FVector::ZeroVector;
		/** MR2: where its path was last traced against the car's own body. */
		FVector BodyFrom = FVector::ZeroVector;
		/** Wheel spray P2: the particle's id (its clump and spin) and the variant slice of the patch it left (its clump's colour). */
		uint32 Id = 0;
		uint8 Slice = 0;
		/** P2d muddy rut splash (Water kind only): the mud colour's weight (0 outside a Mud patch), its colour, the rut water's turbidity. */
		float MudShare = 0.f;
		float MudTurbidity = 0.f;
		FLinearColor MudTint = FLinearColor::Black;
	};
	/** MR2: the blob's path since BodyFrom against the car's own body; true when it hit (the region coated, the blob gone). */
	bool TraceBody(FParticle& P);
	/** MR1: a blob traced its path this frame: splat, land in a patch, or keep flying. True when it left the pool. bInBox: it is
	 * inside a patch's box, where only a static mesh catches it (the field takes it on the ground, as before). */
	bool TraceThrown(FParticle& P, bool bInBox);

	void Spawn(EGTSprayKind Kind, const FVector& Origin, const FVector& Forward, const FVector& Right, const FVector& CarVelocity, float Speed);
	/** LM2a: one thrown blob of SizeCm carrying VolumeCm3, flung by the wheel's spin (cm/s, signed as Chaos's slip). LM3b: into Kind's pool (Snow from a wheel in a snow patch, white; Mud otherwise). */
	void SpawnThrown(EGTSprayKind Kind, const FVector& Origin, const FVector& Forward, const FVector& Right, const FVector& CarVelocity, float Speed, float SlipCmPerS, float SizeCm, double VolumeCm3);
	/** LM2a: a thrown blob leaves the pool: down on the patch under it, or lost outside every patch. */
	void LandThrown(const FParticle& P, bool bLanded);
	void Integrate(EGTSprayKind Kind, float DeltaSeconds);
	void PushTransforms(EGTSprayKind Kind);
	static bool UseSparseRenderUpdates();
	void SpawnWater(const FVector& Origin, const FVector& Travel, const FVector& Outward, const FVector& CarVelocity, float SpeedMps, float Activity, bool bBow);
	void UpdateWaterWheel(int32 Index, float Dt, const UGTTractionComponent& Traction, const UChaosWheeledVehicleMovementComponent& Move);
	void UpdateWaterBow(float Dt, const UGTTractionComponent& Traction, const UChaosWheeledVehicleMovementComponent& Move, const UGTHullComponent* Hull);

	UPROPERTY(Transient)
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> Meshes;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;

	TArray<FParticle> Particles[static_cast<int32>(EGTSprayKind::Count)];
	TArray<FTransform> Transforms[static_cast<int32>(EGTSprayKind::Count)];
	/** Visible prefix last submitted successfully; expired slots are hidden once. Drawing only. */
	int32 SubmittedLiveCount[static_cast<int32>(EGTSprayKind::Count)] = {};
	TArray<float> SpawnAccumulators;
	float SteamAccumulator = 0.f;
	FRandomStream Random;
	/** Water art never consumes the mud/snow throw's random stream. */
	FRandomStream WaterRandom{0x57415445};
	int32 TotalSpawned = 0;

	// ---- water stage W4: what the splashes read and what they reported this tick ------------------------
	TArray<float> SplashAccumulators;
	float BowAccumulators[2] = {0.f,0.f};
	bool bWheelSplashing = false;
	bool bBowSpraying = false;
	int32 SplashWheels = 0;
	float SplashDeepestM = 0.f;
	float SplashRateNow = 0.f;
	float BowSubmergedM = 0.f;
	float BowRateNow = 0.f;
	float WaterSpeedMps = 0.f;
	// ---- LM2a, the throw -------------------------------------------------------------------------------------------
	TArray<double> ThrowSpentCm3;     // per wheel, what of its ThrownCm3 has gone into blobs
	TArray<float> ThrowNextBlobCm;    // per wheel, the next blob's size
	TArray<double> ThrowSeenCm3;      // LM2c: per wheel, its ThrownCm3 at the last tick (this tick's flow is the difference)
	TArray<double> ThrowHazard;       // LM2c: per wheel, the Poisson stream's clock since the last blob
	TArray<double> ThrowNextGap;      // LM2c: per wheel, the exponential gap to the next blob on that clock
	/** LM2c: the mean blob volume for the size law in force, cm^3 (and the numbers it was worked out for). */
	double ThrowMeanBlobCm3 = 0.0;
	FVector3f ThrowMeanKey = FVector3f(-1.f);
	float ThrowMeanFill = -1.f;
	UPROPERTY(Transient)
	TObjectPtr<UGTMudSubsystem> MudForThrow = nullptr;
	double ThrowEmittedCm3 = 0.0;
	double ThrowLandedCm3 = 0.0;
	double ThrowLostCm3 = 0.0;
	double ThrowPendingCm3 = 0.0;
	int32 ThrowBlobsEmitted = 0;
	int32 ThrowBlobsLanded = 0;
	int32 ThrowBlobsLost = 0;
	int32 ThrowBlobsSnow = 0;
	// MR1
	UPROPERTY(Transient)
	TObjectPtr<UGTMudSplatSubsystem> SplatsForThrow = nullptr;
	double ThrowSplattedCm3 = 0.0;
	int32 ThrowBlobsSplatted = 0;
	// MR2
	UPROPERTY(Transient)
	TObjectPtr<UGTBodyStateComponent> BodyStateForThrow = nullptr;
	TWeakObjectPtr<UPrimitiveComponent> BodyCollision;
	FBox BodyLocalBox = FBox(ForceInit);
	uint64 BodyTraceFrame = 0;
	int32 BodyTracesThisFrame = 0;
	int32 BodyTraces = 0;
	int32 BodyTracesCapped = 0;
	int32 ThrowBlobsOnCar = 0;
	double ThrowOnCarCm3 = 0.0;
	int32 ThrowBlobsUnderCar = 0;
	// ---- Wheel spray P2 ---------------------------------------------------------------------------------------------------------
	/** One painterly Niagara component per wheel (NS_GT_WheelSpray), at its contact. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UNiagaraComponent>> FineSpray;
	/** NS_GT_WheelSpray, loaded at BeginPlay (null: no painterly spray). */
	UPROPERTY(Transient)
	TObjectPtr<UNiagaraSystem> FineSystem = nullptr;
	/** The eight clumps' ISMs: the Mud kind's blobs at gt.Spray.Art 1 (slot i of each is particle i's, hidden when another draws it). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> ClumpMeshes;
	TArray<float> ClumpLengthCm;
	TArray<FTransform> ClumpTransforms[8];
	TArray<float> FineRateNow;     // per wheel x 3
	TArray<FVector> FineBaseVelocity;   // P2d: per wheel
	uint32 NextParticleId = 1;     // P2d: 0 marks a Water particle not yet stamped (SpawnWater sets no id)
	int32 MuddySplashCount = 0;
	bool bWaterMudDrawn = false;   // P2d: last frame had a muddy splash (one more upload when it ends)
	int32 SubmittedWaterMudCount = 0; // Uploaded prefix; retire old custom-data slots once.
	uint8 SpawnSlice = 0;          // the slice of the wheel spawning now (Spawn and SpawnThrown stamp it on the particle)
	int32 ClumpsDrawn = 0;
	bool bArtDrawn = false;        // the Mud kind drew clumps last frame (the greybox spheres are hidden)
	void BeginArt(USceneComponent* Root);
	void UpdateArt(float DeltaSeconds, const UGTTractionComponent& Traction, const UChaosWheeledVehicleMovementComponent& Move, float ForwardSpeed, float SpeedFactor);
	/** The Mud kind as clumps (true when it drew them; false: the greybox spheres draw as before). */
	bool PushClumps();
	/** P2d muddy rut splash: new Water particles take the mud of the wheel they left (if it is in a Mud patch). */
	void StampWaterMud(const UGTTractionComponent& Traction, const UChaosWheeledVehicleMovementComponent& Move);
	/** P2d: the Water ISM's custom data 2-6 (mud weight, tint RGB, turbidity) after its transforms were pushed. */
	void PushWaterMud();
};
