#pragma once

#include "CoreMinimal.h"
#include "Dressing/GTVegetationSettings.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "GTVegetationSubsystem.generated.h"

class UCapsuleComponent;
class UInstancedStaticMeshComponent;
class UPrimitiveComponent;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * LD5: a snapped sapling or young tree. The root is a capsule that simulates physics (the trunk: the instance's probe
 * radius, the instance's height long, tilted as the tree was); the instance's proxy is attached to it with no collision.
 * Pooled by UGTVegetationSubsystem (at most UGTVegetationSettings::MaxDebris exist).
 */
UCLASS(NotPlaceable, Transient)
class GRANDTOUR_API AGTVegDebrisActor : public AActor
{
	GENERATED_BODY()

public:
	AGTVegDebrisActor();

	UPROPERTY(VisibleAnywhere, Category = "GT|Vegetation")
	TObjectPtr<UCapsuleComponent> Capsule;

	/** The pool index of the proxy it carries (the proxy stays owned by the subsystem's pool actor). */
	int32 Proxy = INDEX_NONE;
	/** The soft instance it came from. */
	int32 Instance = INDEX_NONE;
	double LaunchTime = 0.0;
	bool bInUse = false;
	bool bFrozen = false;
};

/** LD5: counters since UGTVegetationSubsystem::ResetStats, for the tests and the logs. */
struct FGTVegStats
{
	float BendDeg = 20.f;          // the tilt BentOver counts (while in contact)
	float SettledDeg = 5.f;        // the tilt MaxRecoverS times down to
	int32 Contacted = 0;           // distinct instances touched
	int32 BentOver = 0;            // distinct instances whose tilt passed BendDeg while in contact
	int32 Snaps = 0;
	int32 SnapsByClass[3] = { 0, 0, 0 };
	int32 SnapsImpact = 0;         // tilt at the break with the car at v break or faster
	int32 SnapsSustained = 0;      // v2: tilt at the break with p >= 0.9 held for the class's t hold
	float MaxTiltDeg = 0.f;
	float MaxRecoverS = 0.f;       // the longest wait from an instance's last contact to its tilt under SettledDeg
	int32 Recovered = 0;           // instances timed down to SettledDeg
	int32 ContactFrames = 0;       // probe calls with at least one contact
	int32 MaxContacts = 0;         // most instances in contact in one probe call
	float MaxForceN = 0.f;         // largest resist force applied (after the cap)
	int32 Evicted = 0;             // bending instances recovered early to free a proxy (the pool cap)
	int32 NoSlot = 0;              // contacts that found every proxy on an instance still in contact
	int32 DebrisConverted = 0;     // debris turned into no-collision ISM instances (the debris cap)
	double FirstContactTime = -1.0;
	double LastContactTime = -1.0;
	double TickMsSum = 0.0;        // the subsystem's per-frame work (probe calls + tick), for frames with soft vegetation
	float TickMsMax = 0.f;
	int32 TickFrames = 0;
	int32 InstanceUpdates = 0;     // ISM instance transform updates flushed (hide / restore)
};

/**
 * Leg dressing LD5 (docs/LEG_DRESSING_PLAN.md): the soft vegetation physics. At BeginPlay (and on Reindex /
 * IndexComponent / gt.Veg.Reindex, for a map that registers late) it indexes every UInstancedStaticMeshComponent whose
 * component tag is GTVeg.Soft.Brush / .Sapling / .Young: per instance the bend pivot (the instance's origin; for trees
 * the base of the mesh's trunk capsule), a probe radius (brush: the mesh's XY bounds radius x XY scale x 0.5; trees:
 * 0.05 x height; LD5 v2: brush 0.5 x max(bounds extent X, Y) x XY scale, trees the trunk capsule radius x XY scale, at
 * least 5 cm), the height (the mesh's top x Z scale) and the class, in a 2D spatial hash of 4 m cells.
 *
 * A car's UGTVegetationProbeComponent calls ProbeCar once per physics tick with its footprint OBB (the body bounds +
 * 0.3 m): an instance is in contact when its pivot is inside that box expanded by its radius, at intrusion depth d, and
 * pushed by p = saturate(d / 0.5 m).
 *  - Bend (proxy swap): a touched instance is hidden in its component (scale 0; every component's updates of a frame are
 *    flushed together at the tick's end, incremental on a plain ISM) and drawn by a pooled movable UStaticMeshComponent
 *    proxy, rotated about the pivot toward the car's horizontal velocity (below 0.5 m/s: away from the car's
 *    centreline) by a tilt that rises toward theta max x p with tau 0.05 s and springs back with tau 1.5 s (v2: the proxy
 *    casts no shadow while bending; fallen, the debris casts the instance's own); under 1 deg
 *    after contact the instance is restored and the proxy returns to the pool. The pool is the active set (128); when
 *    it is full the oldest instance not in contact this frame recovers first.
 *  - Resist: sum over contacts of -v_hat x K x p x s(v) on the car's body (v2: s(v) = 0.3 + 0.7 saturate(|v| / 10 m/s)),
 *    each class's sum capped (v2: Brush 0.15, Sapling 0.20, Young 0.35 m g) and the total at 0.35 m g, applied at the
 *    centre of mass (and never more than stops the car's horizontal motion within the step).
 *  - Snap (Sapling, Young): tilt >= theta break with the car at v break or faster (impact), or (v2) with p >= 0.9 held
 *    for t hold (Sapling 0.5 s, Young 2 s: a sustained push): the instance stays hidden, the proxy
 *    goes to a pooled AGTVegDebrisActor with the impulse m_debris x v_car x 0.8 and the car gets the opposite. Debris
 *    freezes (physics and collision off) when it sleeps or after 20 s; at most 24 exist and past that the oldest frozen
 *    one becomes a no-collision ISM instance. Snaps last for the run and are never saved.
 * gt.Look.Dressing 0 makes it fully inert: every bent and snapped instance restored, every proxy back in the pool,
 * every debris actor parked and its ISM instances cleared; 1 resumes (the snapped trees stand again). No soft
 * vegetation in the world: ProbeCar and Tick return at once.
 * Every number is a dial in UGTVegetationSettings. The per-frame work (probe calls + tick) is logged as a rolling mean
 * and max (GTVEG lines every 5 s while anything is touched).
 */
UCLASS()
class GRANDTOUR_API UGTVegetationSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UGTVegetationSubsystem, STATGROUP_Tickables); }

	/** Rebuilds the index from every GTVeg.Soft.* ISM in the world (everything restored first). Returns the instance count. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vegetation")
	int32 Reindex();

	/** Adds one component's instances (for a map that registers late). False if it is not a GTVeg.Soft.* ISM or is indexed already. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vegetation")
	bool IndexComponent(UInstancedStaticMeshComponent* Component);

	/** True when there is anything to push: soft instances indexed and gt.Look.Dressing not 0. */
	bool IsActive() const { return Instances.Num() > 0 && !bInert; }

	/**
	 * One probe: the car's footprint (CarTransform x LocalBodyBox, padded) against the hash. Marks the contacts for the
	 * tick and returns the resist force in newtons (world, horizontal) for the caller to put on the chassis at its centre
	 * of mass. Snap impulses on the car are applied by the tick, to Chassis.
	 */
	FVector ProbeCar(UPrimitiveComponent& Chassis, const FTransform& CarTransform, const FBox& LocalBodyBox, float CarMassKg, float DeltaSeconds, int32& OutContacts);

	// ---- test hooks and logs ---------------------------------------------------------------------------------------
	void ResetStats(float BendDeg = 20.f, float SettledDeg = 5.f);
	const FGTVegStats& GetStats() const { return Stats; }
	int32 GetActiveCount() const { return Slots.Num(); }
	/** Debris actors carrying a snapped tree (live or frozen); GetDebrisActorCount counts every debris actor spawned. */
	int32 GetDebrisInUse() const;
	int32 GetDebrisActorCount() const { return Debris.Num(); }
	/** Bending instances whose tilt is above Deg now. */
	int32 CountTiltedOver(float Deg) const;
	int32 GetIndexedCount(EGTVegClass Class) const;
	int32 GetIndexedTotal() const { return Instances.Num(); }
	int32 GetCellCount() const { return Cells.Num(); }
	/** Indexed components by class name: plain ISM or HISM. */
	void CountComponents(int32 OutIsm[3], int32 OutHism[3]) const;
	/** The per-frame work over the last RollingFrames frames with soft vegetation, ms. */
	void GetRollingTickMs(float& OutMean, float& OutMax, int32& OutFrames) const;
	void ForEachInstance(TFunctionRef<void(const FVector& Pivot, EGTVegClass Class, float RadiusCm, float HeightCm, bool bSnapped)> Visit) const;
	bool IsInert() const { return bInert; }
	FString DescribeIndex() const;
	static const TCHAR* ClassName(EGTVegClass Class);

	/**
	 * Setup helper (Art/dressing/setup_veg_test.py): adds a plain UInstancedStaticMeshComponent of Mesh to Actor (a root
	 * scene component is made if the actor has none) with the instances at WorldTransforms, one component tag, the
	 * collision profile and the shadow flag, as an instance component that saves with the level.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Vegetation")
	static UInstancedStaticMeshComponent* AddTaggedInstances(AActor* Actor, UStaticMesh* Mesh, const TArray<FTransform>& WorldTransforms,
		FName ComponentTag, FName CollisionProfile, bool bCastShadow);

private:
	struct FInstance
	{
		FVector Pivot = FVector::ZeroVector;   // world: the bend pivot
		float RadiusCm = 0.f;
		float HeightCm = 0.f;
		int32 Component = INDEX_NONE;
		int32 Index = INDEX_NONE;              // the instance's index in its component
		EGTVegClass Class = EGTVegClass::Brush;
		int32 Slot = INDEX_NONE;               // its bending slot, if any
		bool bSnapped = false;
		bool bStatContact = false;
		bool bStatBent = false;
	};

	struct FComponent
	{
		TWeakObjectPtr<UInstancedStaticMeshComponent> Ism;
		EGTVegClass Class = EGTVegClass::Brush;
		bool bHism = false;
		TArray<TPair<int32, FTransform>> Pending;   // component-space transforms, flushed at the tick's end
	};

	struct FSlot
	{
		int32 Instance = INDEX_NONE;
		int32 Proxy = INDEX_NONE;
		FTransform Local;                      // the instance's own transform, component space
		FTransform World;                      // and in the world: the proxy at rest
		FVector Dir = FVector::ForwardVector;  // horizontal: where the top goes
		float TiltRad = 0.f;
		float Push = 0.f;
		float CarSpeedMs = 0.f;
		float SustainS = 0.f;                  // v2: how long the tilt has been at the break with p >= SustainPush
		FVector CarVelocityDir = FVector::ForwardVector;
		double StartTime = 0.0;
		double ContactEndTime = -1.0;
		uint64 LastContactFrame = 0;
		bool bContact = false;
		bool bSettleTimed = true;
		TWeakObjectPtr<UPrimitiveComponent> Car;
	};

	void Index();
	void ClearIndex();
	int32 IndexComponentInternal(UInstancedStaticMeshComponent* Ism);
	FIntPoint CellOf(const FVector& Location) const;

	int32 AcquireSlot(int32 InstanceIndex);
	void RecoverSlot(int32 SlotIndex);
	void RemoveSlot(int32 SlotIndex);
	void SnapSlot(int32 SlotIndex, bool bSustained);
	FTransform BentTransform(const FSlot& Slot, const FInstance& Inst) const;
	void QueueInstance(int32 InstanceIndex, const FTransform& Local);
	int32 FlushInstances();

	void EnsurePoolActor();
	int32 AcquireProxy();
	void ReleaseProxy(int32 ProxyIndex);
	void ConfigureProxy(int32 ProxyIndex, const UInstancedStaticMeshComponent& Ism);

	AGTVegDebrisActor* AcquireDebris();
	void FreezeDebris(AGTVegDebrisActor& Actor);
	void ConvertDebris(AGTVegDebrisActor& Actor);
	void ParkDebris(AGTVegDebrisActor& Actor);
	void TickDebris(double Now);

	void RestoreAll();
	void MakeInert();
	void AddFrameWork(double Seconds) { FrameWorkSeconds += Seconds; }

	TArray<FInstance> Instances;
	TArray<FComponent> Components;
	TMap<TWeakObjectPtr<UInstancedStaticMeshComponent>, int32> ComponentLookup;
	TMap<FIntPoint, TArray<int32>> Cells;
	float CellCm = 400.f;
	float MaxRadiusCm = 0.f;
	int32 SkippedHidden = 0;

	TArray<FSlot> Slots;
	/** Every instance ever hidden: its own component-space transform (restores read it, never the component's current one). */
	TMap<int32, FTransform> OriginalLocal;

	UPROPERTY(Transient)
	TObjectPtr<AActor> PoolActor;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Proxies;
	TArray<int32> ProxyConfiguredFor;   // per proxy: the component whose mesh and materials it carries
	TArray<int32> FreeProxies;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AGTVegDebrisActor>> Debris;
	/** Converted debris: one no-collision ISM per mesh on the pool actor. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> DebrisIsms;

	bool bInert = false;
	bool bBegun = false;
	FGTVegStats Stats;

	// Timing: this frame's work, the rolling window, the periodic log.
	double FrameWorkSeconds = 0.0;
	static constexpr int32 RollingFrames = 120;
	TArray<float> RollingMs;
	int32 RollingNext = 0;
	double LastLogTime = 0.0;
	bool bActivitySinceLog = false;
	int32 LastProbeContacts = 0;
	float LastForceN = 0.f;
};
