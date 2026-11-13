#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "GTEnvironmentComponent.generated.h"

class UGTConditionComponent;
class UGTLegDefinition;
struct FGTVehicleTuning;

/** How far a condition has ramped (ARCHITECTURE 6c: performance, then a warning, then damage). */
UENUM(BlueprintType)
enum class EGTConditionStage : uint8
{
	None,
	Performance,
	Warning,
	Damage
};

/**
 * The car's environment stage (ARCHITECTURE 6c): samples the leg's conditions profile at the
 * car's progress every tick and turns the Tier 1 conditions into tuning modifiers and, past a
 * readable window, part damage. Two small continuous models, the rest are multipliers:
 *  - Env.Heat: coolant heat rises with intensity x engine load and falls at rest; hot engines
 *    lose torque, the temperature dial climbs, above the damage level the engine cooks slowly.
 *  - Env.Dust: the air filter clogs with intensity x distance driven and never clears on the
 *    leg (the base does); a clogged filter loses torque, lights the FILTER lamp, and past the
 *    damage level scores the engine.
 *  - Env.Cold: a multiplier: torque down, the COLD lamp above the warning level, no damage to
 *    the car (the player's exposure is what cold attacks). No continuous state.
 * Order in the tuning pipeline: base -> traction -> environment -> condition -> Chaos. Part
 * answers (heater, big radiator, filter) subtract from the intensities by tag when M4's parts
 * arrive: Resistance is the hook.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTEnvironmentComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTEnvironmentComponent();

	/** Driven by the car every tick; Leg may be null (no conditions). */
	void Update(float DeltaSeconds, const UGTLegDefinition* Leg, float Progress, float ThrottleInput, float SpeedCmPerSec, UGTConditionComponent* Condition);
	void ModifyTuning(FGTVehicleTuning& Tuning) const;

	/** Profile intensity of a tag at the current progress, after resistances. */
	UFUNCTION(BlueprintPure, Category = "GT|Environment")
	float GetIntensity(FGameplayTag Tag) const;

	UFUNCTION(BlueprintPure, Category = "GT|Environment")
	EGTConditionStage GetStage(FGameplayTag Tag) const;

	/** Highest stage across the profile (for the HUD). */
	UFUNCTION(BlueprintPure, Category = "GT|Environment")
	EGTConditionStage GetWorstStage() const;

	static const TCHAR* StageName(EGTConditionStage Stage);

	UFUNCTION(BlueprintPure, Category = "GT|Environment")
	FString Describe() const;

	/** Per-tag resistance 0..1 from installed parts and consumables (M4); 1 cancels the condition. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Environment")
	TMap<FGameplayTag, float> Resistance;

	// ---- heat ---------------------------------------------------------------------------------
	/** Coolant heat gained per second at full intensity and full load. */
	UPROPERTY(EditAnywhere, Category = "GT|Environment|Heat")
	float HeatRate = 0.05f;

	/** Heat lost per second at rest in a cool environment. */
	UPROPERTY(EditAnywhere, Category = "GT|Environment|Heat")
	float CoolRate = 0.03f;

	UPROPERTY(EditAnywhere, Category = "GT|Environment|Heat")
	float HeatTorqueLoss = 0.25f;

	/** Engine health per second lost while the heat is in the damage stage. */
	UPROPERTY(EditAnywhere, Category = "GT|Environment|Heat")
	float HeatDamagePerSecond = 0.01f;

	// ---- dust ---------------------------------------------------------------------------------
	/** Filter clog gained per kilometre at full intensity. */
	UPROPERTY(EditAnywhere, Category = "GT|Environment|Dust")
	float ClogPerKm = 0.5f;

	UPROPERTY(EditAnywhere, Category = "GT|Environment|Dust")
	float ClogTorqueLoss = 0.3f;

	UPROPERTY(EditAnywhere, Category = "GT|Environment|Dust")
	float ClogDamagePerSecond = 0.005f;

	// ---- cold ---------------------------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "GT|Environment|Cold")
	float ColdTorqueLoss = 0.1f;

	// ---- stages -------------------------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "GT|Environment", meta = (ClampMin = 0, ClampMax = 1))
	float PerformanceLevel = 0.2f;

	UPROPERTY(EditAnywhere, Category = "GT|Environment", meta = (ClampMin = 0, ClampMax = 1))
	float WarningLevel = 0.5f;

	UPROPERTY(EditAnywhere, Category = "GT|Environment", meta = (ClampMin = 0, ClampMax = 1))
	float DamageLevel = 0.8f;

	// ---- state ---------------------------------------------------------------------------------
	/** Coolant heat 0..1 (the temperature dial). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Environment")
	float Heat = 0.f;

	/** Air filter clog 0..1. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Environment")
	float Clog = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Environment")
	float Cold = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Environment")
	float HeatIntensity = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Environment")
	float DustIntensity = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Environment")
	float TotalConditionDamage = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Environment")
	float Progress = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Environment")
	bool bHasProfile = false;

private:
	EGTConditionStage StageFor(float Level) const;
	float Resisted(FGameplayTag Tag, float Intensity) const;
};
