#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayTagContainer.h"
#include "GTExposureComponent.generated.h"

/**
 * The player's exposure meter (ARCHITECTURE 9a): one 0..100 value. Hazard volumes drain it by
 * tag, the car (and later the base) restores it. At zero the character is collapsed: it can
 * only crawl back to the car, no sprint, no tools, until the meter recovers past the threshold.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTExposureComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTExposureComponent();

	/** Called by the character every tick; bSheltered = inside the car. */
	void Update(float DeltaSeconds, bool bSheltered);

	/** A hazard takes Amount points; Tag says which hazard (resistances by tag come with the parts). */
	UFUNCTION(BlueprintCallable, Category = "GT|Exposure")
	void Drain(float Amount, FGameplayTag HazardTag);

	UFUNCTION(BlueprintPure, Category = "GT|Exposure")
	float GetFraction() const { return MaxExposure > 0.f ? Exposure / MaxExposure : 0.f; }

	UFUNCTION(BlueprintPure, Category = "GT|Exposure")
	bool IsCollapsed() const { return bCollapsed; }

	UFUNCTION(BlueprintPure, Category = "GT|Exposure")
	FString Describe() const;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Exposure")
	float MaxExposure = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Exposure")
	float Exposure = 100.f;

	/** Points per second regained inside the car. */
	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float ShelteredRecoveryPerSecond = 10.f;

	/** Points per second regained outside once no hazard has touched the meter for RecoveryDelay. */
	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float OpenAirRecoveryPerSecond = 1.f;

	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float RecoveryDelay = 5.f;

	/** Collapsed until the meter climbs back above this. */
	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float RecoverThreshold = 25.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Exposure")
	float TotalDrained = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Exposure")
	FGameplayTag LastHazardTag;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Exposure")
	int32 CollapseCount = 0;

private:
	bool bCollapsed = false;
	float TimeSinceDrain = 1000.f;
};
