#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Vehicle/GTVehicleTuning.h"
#include "GTVehicleTuningComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;
class UGTConditionComponent;
class UGTEnvironmentComponent;
class UGTPartSlotsComponent;
class UGTTractionComponent;

/**
 * The one place that writes to Chaos (ARCHITECTURE 6): captures the base setup from the movement
 * component, rebuilds FGTVehicleTuning every tick as base -> parts -> traction -> environment -> condition, applies the
 * changed values through the Chaos runtime setters and adds the rolling-resistance force.
 * Installed parts will replace the captured base when the part system exists.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTVehicleTuningComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTVehicleTuningComponent();

	void UpdateAndApply(float DeltaSeconds, UChaosWheeledVehicleMovementComponent& Movement,
	                    const UGTTractionComponent* Traction, const UGTConditionComponent* Condition,
	                    const UGTEnvironmentComponent* Environment = nullptr, const UGTPartSlotsComponent* Parts = nullptr);

	UFUNCTION(BlueprintPure, Category = "GT|Tuning")
	const FGTVehicleTuning& GetCurrent() const { return Current; }

	UFUNCTION(BlueprintPure, Category = "GT|Tuning")
	const FGTVehicleTuning& GetBase() const { return Base; }

	/** Speed (cm/s) below which the rolling-resistance force fades out to avoid jitter at rest. */
	UPROPERTY(EditAnywhere, Category = "GT|Tuning")
	float DragFadeSpeed = 50.f;

	/** The Chaos wheel radius never shrinks by more than this fraction of itself (sunk to the rims), whatever the sinkage. */
	UPROPERTY(EditAnywhere, Category = "GT|Tuning", meta = (ClampMin = 0, ClampMax = 0.9))
	float MaxVisibleSinkFraction = 0.6f;

private:
	void CaptureBase(const UChaosWheeledVehicleMovementComponent& Movement);
	void Apply(UChaosWheeledVehicleMovementComponent& Movement);
	void ApplyLandscapeSupport(float DeltaSeconds, UChaosWheeledVehicleMovementComponent& Movement, const UGTTractionComponent& Traction);
	void ApplyRollingResistance(UChaosWheeledVehicleMovementComponent& Movement) const;

	UPROPERTY(VisibleAnywhere, Category = "GT|Tuning")
	FGTVehicleTuning Base;

	UPROPERTY(VisibleAnywhere, Category = "GT|Tuning")
	FGTVehicleTuning Current;

	TArray<float> BaseWheelFriction;
	TArray<float> AppliedWheelFriction;
	TArray<float> AppliedSlipGraph;
	TArray<float> BaseWheelRadius;
	TArray<float> AppliedWheelRadius;
	TArray<float> GroundSupportCm;
	TArray<float> MudYieldCm;
	float AppliedTorque = -1.f;
	float AppliedDrag = -1.f;
	bool bBaseCaptured = false;
};
