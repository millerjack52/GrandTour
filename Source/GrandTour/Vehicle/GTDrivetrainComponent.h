#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GTDrivetrainComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;
class UGTTractionComponent;
struct FGTVehicleTuning;

USTRUCT(BlueprintType)
struct FGTDrivetrainWheel
{
	GENERATED_BODY()

	/** Torque handed to the wheel this tick, Nm (negative in reverse or under engine braking). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Drivetrain")
	float DriveTorqueNm = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Drivetrain")
	float BrakeTorqueNm = 0.f;

	/** What the tyre can react before it spins: true load x friction x radius, plus the spin allowance. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Drivetrain")
	float CapNm = 0.f;

	/** Wheel speed, rad/s, rolling forward positive. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Drivetrain")
	float OmegaRadS = 0.f;
};

/**
 * The drivetrain (driving feel stage 4, docs/DRIVING_FEEL_PLAN.md): engine, automatic gearbox, transfer case with
 * high and low range, and three differentials (centre, front, rear) that are open or locked. Chaos's own mechanical
 * simulation is off on the car; this hands each wheel its drive and brake torque through the wheel torque override,
 * so a wheel in the air or in slime starves its partner when the diffs are open, and the lock sends the torque to
 * the wheel that can use it. The pedals come from Chaos's smoothed inputs; reverse is the brake pedal held at a stop
 * (as Chaos's ReverseAsBrake did), the throttle then brakes. Range Rover and Ferrari use an independent engine and
 * automatic clutch; remaining cars retain their authored wheel-coupled RPM and legacy torque split.
 * Driven by AGTCarPawn::Tick after the tuning, whose MaxEngineTorque and TorqueScale it uses.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTDrivetrainComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTDrivetrainComponent();

	void Update(float DeltaSeconds, UChaosWheeledVehicleMovementComponent& Movement, const UGTTractionComponent& Traction, const FGTVehicleTuning& Tuning);

	UFUNCTION(BlueprintCallable, Category = "GT|Drivetrain")
	void SetDiffLock(bool bOn) { bDiffLock = bOn; }

	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	bool IsDiffLocked() const { return bDiffLock; }

	UFUNCTION(BlueprintCallable, Category = "GT|Drivetrain")
	void SetLowRange(bool bOn);

	/** -1 for other cars; 0 authored/Standard, 1 Rally, 2 Expedition. Resolved from this car's loadout. */
	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	int32 GetRangeRoverSetup() const;
	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	bool IsFerrari() const;

	/** 0 Factory, 1 FWD, 2 RWD, 3 AWD; stored in the mechanical loadout. */
	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	int32 GetDriveLayout() const;
	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	float GetEffectiveFrontShare() const;
	/** Nominal AWD split; tuning is retained while using other layouts. */
	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	float GetAWDFrontShare() const { return AWDFrontShare; }
	UFUNCTION(BlueprintCallable, Category = "GT|Drivetrain")
	bool SetAWDFrontShare(float FrontShare);

	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	FString SetupReport() const;

	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	bool IsLowRange() const { return bLowRange; }

	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	float GetEngineRpm() const { return EngineRpm; }

	/** 1.. forward gears, -1 reverse. */
	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	int32 GetGear() const { return bReverse ? -1 : Gear; }

	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	bool IsReversing() const { return bReverse; }

	/** The pedal that drives this tick, 0..1 (the throttle forward, the brake pedal in reverse). */
	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	float GetDriveInput() const { return DriveInput; }

	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	float GetBrakeInput() const { return BrakeInput; }

	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	float GetEngineTorqueNm() const { return EngineTorqueNm; }

	/** Engine/flywheel inertia reflected to one driven wheel while the clutch couples it. */
	float GetReflectedEngineInertia(int32 Wheel) const
	{
		const float Front=GetEffectiveFrontShare();
		const float Share=(Wheel<2 ? Front : 1.f-Front)*.5f;
		return (IsFerrari() ? .38f : .65f)*TotalRatio*TotalRatio*Share*ClutchEngagement*ClutchEngagement;
	}

	UFUNCTION(BlueprintPure, Category = "GT|Drivetrain")
	FString Describe() const;

	/** Transfer case low range: the ratio multiplied in. */
	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain")
	float LowRangeRatio = 2.5f;

	/** Share of the torque the centre diff sends forward before the locks and the caps have their say. */
	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain", meta = (ClampMin = 0, ClampMax = 1))
	float CentreSplitFront = 0.5f;

	/** A locked diff: torque handed from the faster side to the slower per rad/s of speed difference, Nm, and its cap. */
	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain")
	float LockCouplingNmPerRadS = 120.f;

	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain")
	float LockCouplingMaxNm = 400.f;

	/** An open diff hands the gripping side no more than the slipping side can react; this much is always reacted (bearings, spinning the wheel up). */
	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain")
	float OpenSpinAllowanceNm = 40.f;

	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain", meta = (ClampMin = 0.5, ClampMax = 1))
	float DrivelineEfficiency = 0.9f;

	/** Shifts wait this long after the last one (the gearbox's own change time comes from Chaos's TransmissionSetup). */
	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain")
	float MinShiftIntervalSeconds = 0.6f;

	/** Below this forward speed (cm/s) the brake pedal held alone puts the car in reverse, the throttle alone takes it out. */
	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain")
	float ReverseSpeedThreshold = 30.f;

	/** Locks applied when the diff lock is on (parts can later restrict which diffs a car has). */
	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain", meta = (ClampMin = 0, ClampMax = 1))
	float CentreLockWhenOn = 1.f;

	UPROPERTY(EditAnywhere, Category = "GT|Drivetrain", meta = (ClampMin = 0, ClampMax = 1))
	float AxleLockWhenOn = 1.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Drivetrain")
	TArray<FGTDrivetrainWheel> Wheels;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Drivetrain")
	float WheelRpm = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Drivetrain")
	float TotalRatio = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Drivetrain")
	int32 MaxGearReached = 1;

private:
	virtual void BeginPlay() override;
	friend class FGTRangeRoverDrivetrainTest;
	/** Splits T between two sides: open, each gets at most what the other can react; locked, a coupling evens their speeds. */
	void Split(float T, float CapA, float CapB, float OmegaA, float OmegaB, float Lock, float& OutA, float& OutB, bool bConserveTorque=false, float ShareA=.5f) const;
	friend class UGTRunSubsystem;
	friend class FGTDriveLayoutTest;
	// Snapshot restoration uses this directly; the workshop setter requires a stopped car.
	float AWDFrontShare = .5f;

	float EngineRpm = 0.f;
	float EngineTorqueNm = 0.f;
	float DriveInput = 0.f;
	float BrakeInput = 0.f;
	int32 Gear = 1;
	bool bReverse = false;
	bool bDiffLock = false;
	bool bLowRange = false;
	float ShiftTimer = 0.f;
	float TimeSinceShift = 10.f;
	bool bOverrideSet = false;
	int32 LastSetup = -1;
	int32 LastLayout = -1;
	float RoadRpmForShift = 0.f;
	float RequestedWheelTorqueNm = 0.f;
	float AppliedTorqueScale = 1.f;
	int32 ContactCount = 0;
	bool bWheelspinShiftHold = false;
	float ClutchEngagement = 0.f;
	float ClutchTorqueNm = 0.f;
};
