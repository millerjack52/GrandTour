#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "GTConditionComponent.generated.h"

struct FGTVehicleTuning;

UENUM(BlueprintType)
enum class EGTCarPart : uint8
{
	Engine,
	Radiator,
	Steering,
	FuelTank,
	SuspensionFL,
	SuspensionFR,
	SuspensionRL,
	SuspensionRR,
	TyreFL,
	TyreFR,
	TyreRL,
	TyreRR,
	Body,
	Glass,
	Winch,
	Count UMETA(Hidden)
};

UENUM(BlueprintType)
enum class EGTDamageRegion : uint8
{
	None,
	Front,
	Rear,
	ArchFL,
	ArchFR,
	ArchRL,
	ArchRR,
	SideL,
	SideR,
	Roof,
	Glass
};

/**
 * One dent in the car mesh's local space, centimetres. LocalDirection points outward, from the car
 * toward what it struck (minus the hit's impact normal); the body material pushes vertices the
 * other way. Written to the dent texture by UGTBodyComponent (ARCHITECTURE 6b).
 */
USTRUCT(BlueprintType)
struct FGTImpactRecord
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GT|Condition")
	FVector LocalPosition = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Condition")
	FVector LocalDirection = FVector::ForwardVector;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Condition")
	float Radius = 20.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Condition")
	float Depth = 0.f;
};

/**
 * Car condition (ARCHITECTURE 6b): per-part health, fuel, the impact list and the wear effects
 * that reach handling through the tuning pipeline: engine health and misfires scale torque,
 * tyre health scales grip, uneven suspension damage pulls the steering, an empty tank kills
 * the engine, a holed tank leaks. Impacts arrive from the mesh's hit events via ApplyImpact and
 * are resolved to a damage region in car space, then to the parts that region protects. Each
 * region also has its own health (the panel's integrity): at zero the body component detaches
 * that region's panels, and the glass region's health drives the windscreen crack.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTConditionComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTConditionComponent();

	void Update(float DeltaSeconds, float ThrottleInput, float EngineRPM, float MaxRPM);
	void ModifyTuning(FGTVehicleTuning& Tuning) const;

	/** Record a collision. LocalPosition is in the car mesh's space; DeltaV in cm/s (impulse / mass). */
	UFUNCTION(BlueprintCallable, Category = "GT|Condition")
	void ApplyImpact(const FVector& LocalPosition, const FVector& LocalDirection, float DeltaV);

	UFUNCTION(BlueprintPure, Category = "GT|Condition")
	float GetPartHealth(EGTCarPart Part) const;

	/** Panel integrity of a damage region, 1 = intact, 0 = the region's panels come off. */
	UFUNCTION(BlueprintPure, Category = "GT|Condition")
	float GetRegionHealth(EGTDamageRegion Region) const;

	UFUNCTION(BlueprintCallable, Category = "GT|Condition")
	void SetPartHealth(EGTCarPart Part, float Health);

	UFUNCTION(BlueprintCallable, Category = "GT|Condition")
	void DamagePart(EGTCarPart Part, float Amount);

	UFUNCTION(BlueprintCallable, Category = "GT|Condition")
	void RepairAll();

	/** Field repair (M2): every part the region protects gains Amount, the region's panels are made whole and its dents cleared. */
	UFUNCTION(BlueprintCallable, Category = "GT|Condition")
	void RepairRegion(EGTDamageRegion Region, float Amount);

	/** True if any part behind the region, or the region's own health, is below full. */
	UFUNCTION(BlueprintPure, Category = "GT|Condition")
	bool IsRegionDamaged(EGTDamageRegion Region) const;

	/** Hazard damage (M3): Amount x (1 - HazardResistance[HazardTag]) taken from Part; returns what was applied. */
	UFUNCTION(BlueprintCallable, Category = "GT|Condition")
	float ApplyHazardDamage(FGameplayTag HazardTag, EGTCarPart Part, float Amount);

	/** Resistance 0..1 per hazard tag; installed parts fill it in M4. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Damage")
	TMap<FGameplayTag, float> HazardResistance;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Damage")
	float HazardDamageTaken = 0.f;

	static const TCHAR* RegionName(EGTDamageRegion Region);

	UFUNCTION(BlueprintPure, Category = "GT|Condition")
	float GetFuelFraction() const { return TankCapacityLitres > 0.f ? FuelLitres / TankCapacityLitres : 0.f; }

	/**
	 * Damage region of a hit. LocalDirection (outward, from the car toward what it struck) picks the
	 * face, LocalPosition the sub-region; with a zero direction only the position is used.
	 */
	static EGTDamageRegion ResolveRegion(const FVector& LocalPosition, const FVector& LocalDirection = FVector::ZeroVector);

	// ---- fuel ---------------------------------------------------------------------------------
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Fuel")
	float TankCapacityLitres = 81.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Fuel")
	float FuelLitres = 81.f;

	UPROPERTY(EditAnywhere, Category = "GT|Fuel")
	float IdleLitresPerHour = 1.5f;

	UPROPERTY(EditAnywhere, Category = "GT|Fuel")
	float FullLoadLitresPerHour = 30.f;

	/** Game-time compression on consumption; 10 means a tank lasts a tenth of real time. */
	UPROPERTY(EditAnywhere, Category = "GT|Fuel")
	float FuelUseScale = 10.f;

	/** Leak rate in litres per second when the tank's health is zero, scaled linearly from half health. */
	UPROPERTY(EditAnywhere, Category = "GT|Fuel")
	float LeakLitresPerSecond = 0.5f;

	// ---- damage --------------------------------------------------------------------------------
	/** Impacts below this speed change (cm/s) do nothing. */
	UPROPERTY(EditAnywhere, Category = "GT|Damage")
	float MinDamageSpeed = 150.f;

	/** Speed change (cm/s) that destroys a region's parts in one hit. */
	UPROPERTY(EditAnywhere, Category = "GT|Damage")
	float FullDamageSpeed = 1500.f;

	UPROPERTY(EditAnywhere, Category = "GT|Damage")
	int32 MaxImpacts = 32;

	UPROPERTY(EditAnywhere, Category = "GT|Damage")
	float MaxDentDepth = 15.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Damage")
	TArray<FGTImpactRecord> Impacts;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Damage")
	int32 TotalImpacts = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Damage")
	float LastImpactDeltaV = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Damage")
	EGTDamageRegion LastImpactRegion = EGTDamageRegion::None;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Damage")
	FVector LastImpactLocalDirection = FVector::ZeroVector;

	/** Increments whenever the impact list changes, so the body can rebuild its dent texture. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Damage")
	int32 ImpactsVersion = 0;

	// ---- state read by the dash --------------------------------------------------------------
	UPROPERTY(BlueprintReadOnly, Category = "GT|Condition")
	bool bMisfiring = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Condition")
	bool bOutOfFuel = false;

	/** Water reached the intake: no torque until it has drained (FloodDrainSeconds out of deep water). */
	UPROPERTY(BlueprintReadWrite, Category = "GT|Condition")
	bool bFlooded = false;

	/** Water over the front wheels' contact points that reaches the intake, metres (a snorkel part would raise it). */
	UPROPERTY(EditAnywhere, Category = "GT|Condition")
	float IntakeHeightM = 0.85f;

	UPROPERTY(EditAnywhere, Category = "GT|Condition")
	float FloodDrainSeconds = 5.f;

	/** Called every tick with the water over the front wheels: floods the engine past the intake, drains it after. */
	void UpdateFlooding(float DeltaSeconds, float FrontWaterDepthM);

	UPROPERTY(BlueprintReadOnly, Category = "GT|Condition")
	float LitresUsed = 0.f;

private:
	UPROPERTY(VisibleAnywhere, Category = "GT|Condition")
	TMap<EGTCarPart, float> PartHealth;

	UPROPERTY(VisibleAnywhere, Category = "GT|Condition")
	TMap<EGTDamageRegion, float> RegionHealth;

	float MisfireTimer = 0.f;
	float FloodTimer = 0.f;
	FRandomStream Random;
};
