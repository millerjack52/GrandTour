#pragma once

#include "CoreMinimal.h"
#include "GTVehicleTuning.generated.h"

/** Per-wheel multipliers produced by the tuning pipeline. */
USTRUCT(BlueprintType)
struct FGTWheelTuning
{
	GENERATED_BODY()

	/** Multiplies the wheel's base friction multiplier (surface wetness, sinkage, tyre health). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float FrictionScale = 1.f;

	/** Rolling resistance coefficient applied as a drag force while the wheel is in contact. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float RollingResistance = 0.012f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	bool bInContact = false;

	/** Scales the wheel's lateral slip graph so its 1.0 is the grip available: true load x surface friction / 10000 (Chaos units); the friction multiplier goes on top. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float SlipGraphScale = 0.f;

	/** True load / the spring force Chaos presses the tyre in with (the constraint suspension holds the car where the force model's spring reads short); multiplied into the friction multiplier only. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float LoadCorrection = 1.f;

	/** How far the tyre has sunk into soft ground, cm: the Chaos wheel radius shrinks by it so the contact drops and the drawn wheel buries itself. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float SinkageCm = 0.f;

	/** Signed support from the opted-in landscape mud field; positive crowns lift the wheel. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float GroundSupportCm = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	bool bLandscapeSupport = false;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning") float SoilDragN = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning") float SoilGrip = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning") float SoilSlip = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning") float SoilContactOffsetCm = 0.f;
};

/**
 * The one struct that reaches Chaos (ARCHITECTURE 6). Rebuilt every tick from the base setup,
 * then modified in order by traction and condition, then applied by UGTVehicleTuningComponent.
 * Installed parts will feed the base values when the part system arrives.
 */
USTRUCT(BlueprintType)
struct FGTVehicleTuning
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float MaxEngineTorque = 320.f;

	/** Multiplier on engine torque: engine health, misfires, fuel, bogging. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float TorqueScale = 1.f;

	/** Added to the steering input: damaged suspension pulls the car to one side. -1..1, negative = left. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float SteeringBias = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float DragCoefficient = 0.45f;

	/** Multiplies the rolling-resistance force (tyre parts). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	float RollingScale = 1.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Tuning")
	TArray<FGTWheelTuning> Wheels;
};
