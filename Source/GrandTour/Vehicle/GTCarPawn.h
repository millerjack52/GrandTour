#pragma once

#include "CoreMinimal.h"
#include "WheeledVehiclePawn.h"
#include "GameplayTagContainer.h"
#include "InputActionValue.h"
#include "Interaction/GTInteractable.h"
#include "Vehicle/GTResponsiveSteering.h"
#include "GTCarPawn.generated.h"

class UCameraComponent;
class USpringArmComponent;
class UChaosWheeledVehicleMovementComponent;
class UGTBodyComponent;
class UGTBodyStateComponent;
class UGTConditionComponent;
class UGTDashboardComponent;
class UGTEnvironmentComponent;
class UGTInventoryComponent;
class UGTPartSlotsComponent;
class UGTSprayComponent;
class UGTTractionComponent;
class UGTHullComponent;
class UGTVehicleAudioComponent;
class UGTRangeRoverAudioComponent;
class UGTVehicleTuningComponent;
class UGTWinchComponent;
class UGTDrivetrainComponent;
class UGTVegetationProbeComponent;
class UInputAction;
class UInputMappingContext;
enum class EGTDamageRegion : uint8;

/**
 * The player's car: a Chaos wheeled vehicle with a first-person driver camera and Enhanced Input
 * driving controls. Vehicle numbers (mass, gearing, wheel classes, bone names) are set in the
 * constructor for the Range Rover blockout; a Blueprint child can override any of them.
 *
 * Every tick: traction reads the ground under the wheels, sinking wheels stamp tyre tracks into
 * the track-paint subsystem, condition burns fuel and runs wear, the tuning component rebuilds
 * the tuning and writes it to Chaos, then steering is applied with the condition's pull.
 * Collisions on the body feed the condition component.
 *
 * Input assets are optional. If DefaultMappingContext or any action is unset, a keyboard +
 * gamepad mapping is built at runtime (W/S or triggers throttle/brake, A/D or left stick steer,
 * Space or B handbrake, mouse or right stick look) so the car drives with no content authored.
 */
UCLASS()
class GRANDTOUR_API AGTCarPawn : public AWheeledVehiclePawn, public IGTInteractable
{
	GENERATED_BODY()

public:
	AGTCarPawn(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UChaosWheeledVehicleMovementComponent* GetChaosMovement() const;

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTTractionComponent* GetTraction() const { return Traction; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTConditionComponent* GetCondition() const { return Condition; }

	/** The car's body in water (docs/WATER_PLAN.md W1): the current's push on the hull. */
	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTHullComponent* GetHull() const { return Hull; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTVehicleTuningComponent* GetTuning() const { return Tuning; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTDashboardComponent* GetDashboard() const { return Dashboard; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTBodyComponent* GetBody() const { return Body; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTBodyStateComponent* GetBodyState() const { return BodyState; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTSprayComponent* GetSpray() const { return Spray; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTVehicleAudioComponent* GetAudio() const { return Audio; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTWinchComponent* GetWinch() const { return Winch; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTDrivetrainComponent* GetDrivetrain() const { return Drivetrain; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTInventoryComponent* GetBoot() const { return Boot; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTEnvironmentComponent* GetEnvironment() const { return Environment; }

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	UGTPartSlotsComponent* GetParts() const { return Parts; }

	/** Leg dressing LD5: the soft vegetation probe (footprint contacts, the resist force on the chassis). */
	UGTVegetationProbeComponent* GetVegProbe() const { return VegProbe; }

	/** A hazard volume the car sits in calls this every tick; IsInHazard stays true for a short grace after the last call. */
	void NotifyHazardContact(FGameplayTag HazardTag);

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	bool IsInHazard(FGameplayTag HazardTag) const;

	UFUNCTION(BlueprintPure, Category = "GT|Vehicle")
	float GetRawSteer() const { return RawSteer; }
	/** Consistent firm-ground high-range input response. Zero retains authored filtering. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Vehicle", meta = (ClampMin = 0, ClampMax = 1))
	float HighSpeedSteeringResponse = 1.f;
	UFUNCTION(BlueprintPure, Category = "GT|Testing")
	float GetSteeringResponseWeight() const { return FMath::Max(0.f, ResponsiveSteering.LastWeight); }
    UFUNCTION(BlueprintPure, Category = "GT|Testing")
    float GetSteeringReversalDirection() const { return ResponsiveSteering.ReversalDirection; }
	/** Tests steer the car with this after disabling player input; the tick applies it with the condition's pull. */
	UFUNCTION(BlueprintCallable, Category = "GT|Testing", meta = (DevelopmentOnly))
	void SetRawSteer(float Steer) { RawSteer = FMath::Clamp(Steer, -1.f, 1.f); }

	// ---- on foot (ARCHITECTURE 5): the car is an interactable -----------------------------------
	/** Looking at the car on foot: repair a damaged region with the kit, take the winch hook at the nose, open the boot at the tail, else get in. */
	virtual FGTInteractionOffer GetInteractionOffer(const FGTInteractionQuery& Query) const override;
	virtual void Interact(const FGTInteractionQuery& Query) override;

	/** A clear spot for a capsule beside the driver's door (then the other door, then behind), on the ground. */
	FVector FindExitLocation(float CapsuleRadius, float CapsuleHalfHeight) const;

	/** Scrap consumed by one field repair and the health it restores to each part of the region. */
	UPROPERTY(EditAnywhere, Category = "GT|Repair")
	int32 RepairCostScrap = 2;

	UPROPERTY(EditAnywhere, Category = "GT|Repair", meta = (ClampMin = 0.05, ClampMax = 1))
	float RepairAmount = 0.5f;

	UPROPERTY(EditAnywhere, Category = "GT|Repair")
	float RepairHoldTime = 2.5f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Repair")
	int32 FieldRepairs = 0;

	// ---- doors -------------------------------------------------------------------------------------
	/** Getting in on foot needs an open front door: open it, then look into the doorway. Off: "Get in" anywhere on the car and the driver's door swings for you. */
	UPROPERTY(EditAnywhere, Category = "GT|Doors")
	bool bEnterNeedsOpenDoor = true;

	/** Seconds after getting in before the door you used swings shut. */
	UPROPERTY(EditAnywhere, Category = "GT|Doors")
	float EnterCloseDelay = 0.2f;

	UPROPERTY(EditAnywhere, Category = "GT|Doors")
	float DoorHoldTime = 0.15f;

	/** The door the character is getting in through; the controller shuts it behind them. */
	int32 PendingEnterDoor = INDEX_NONE;

	/** Fallback exit spots in car space, tried after the spot just behind the driver's door (left-hand drive, so -Y). */
	UPROPERTY(EditAnywhere, Category = "GT|Vehicle")
	TArray<FVector> ExitOffsets = { FVector(40.f, -175.f, 0.f), FVector(40.f, 175.f, 0.f), FVector(-340.f, 0.f, 0.f), FVector(340.f, 0.f, 0.f) };

	UFUNCTION(BlueprintPure, Category = "GT|Camera")
	UCameraComponent* GetDriverCamera() const { return DriverCamera; }

	/** The chase camera on its spring arm (for testing: C or right stick click toggles it). */
	UFUNCTION(BlueprintPure, Category = "GT|Camera")
	UCameraComponent* GetChaseCamera() const { return ChaseCamera; }

	UFUNCTION(BlueprintCallable, Category = "GT|Camera")
	void SetChaseCamera(bool bChase);

	UFUNCTION(BlueprintPure, Category = "GT|Camera")
	bool IsChaseCamera() const { return bChaseCamera; }

	/** Zeroes throttle, brake, steer and handbrake; tests call this after disabling player input. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	void ResetDrivingInputs();

	/** The default keyboard, mouse and gamepad mappings (with dead zones on the sticks and triggers); also used by Art/setup_m1_input.bat to write IMC_Driving. */
	static void BuildDrivingMappings(UInputMappingContext* Context, UInputAction* Throttle, UInputAction* Brake, UInputAction* Steer,
	                                 UInputAction* Handbrake, UInputAction* Look, UInputAction* Exit, UInputAction* Reel,
	                                 UInputAction* CameraToggle, UInputAction* DiffLock = nullptr, UInputAction* LowRange = nullptr,
	                                 UInputAction* ReleaseWinch = nullptr);

	/** True when the input came from the IA_* / IMC_Driving assets rather than the runtime fallback. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Input")
	bool bInputFromAssets = false;

	/** Driver eye position relative to the vehicle origin, in cm (left-hand drive: -Y is the car's left). Used when the mesh has no "Head" socket. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Camera")
	FVector DriverEyeOffset = FVector(10.f, -40.f, 135.f);

	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 0, ClampMax = 180))
	float LookYawLimit = 150.f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 0, ClampMax = 89))
	float LookPitchLimit = 60.f;

	/** Seconds without look input before the cockpit camera drifts back to straight ahead. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera")
	float LookRecentreDelay = 1.0f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera")
	float LookRecentreSpeed = 3.f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera")
	bool bInvertLookY = false;

	/** How fast the camera follows the chassis rotation. Higher = stiffer. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 1, ClampMax = 60))
	float CameraLagSpeed = 14.f;

	/** 0 = camera rolls and pitches with the chassis, 1 = horizon stays level. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 0, ClampMax = 1))
	float StableHorizon = 0.5f;

	/** Vertical damping of the eye point against bumps. Higher = stiffer. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 1, ClampMax = 60))
	float CameraVerticalLagSpeed = 12.f;

	/** The eye point never lags more than this (cm) behind the seat vertically, so it stays inside the cabin. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 0, ClampMax = 30))
	float CameraMaxVerticalLag = 8.f;

	/** Chase camera (testing): the arm's length behind the pivot, the pivot's height over the car's origin, its pitch, its lags and the field of view. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera|Chase")
	float ChaseArmLength = 700.f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera|Chase")
	float ChasePivotHeight = 120.f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera|Chase")
	float ChasePitch = -10.f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera|Chase")
	float ChaseLagSpeed = 10.f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera|Chase")
	float ChaseRotationLagSpeed = 6.f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera|Chase")
	float ChaseFieldOfView = 80.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputMappingContext> DefaultMappingContext;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> ThrottleAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> BrakeAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> SteerAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> HandbrakeAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> ExitAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> ReelAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> CameraToggleAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> DiffLockAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> LowRangeAction;

	/** Section 51: lets the winch go from the seat (G, DPad Up); the hook is stowed and the cable rewinds. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputAction> ReleaseWinchAction;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Camera")
	TObjectPtr<UCameraComponent> DriverCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Camera")
	TObjectPtr<USpringArmComponent> ChaseArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Camera")
	TObjectPtr<UCameraComponent> ChaseCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTTractionComponent> Traction;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTConditionComponent> Condition;

	/** The hull in water: five samples through UGTWaterSubsystem and the current's push on the chassis (W1). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTHullComponent> Hull;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTVehicleTuningComponent> Tuning;

	/** Instrument cluster; its transform is where the dials sit (local Z faces the driver). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTDashboardComponent> Dashboard;

	/** Body panels, dents, detach and the windscreen. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTBodyComponent> Body;

	/** Dirt per region, wetness and snow on the body. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTBodyStateComponent> BodyState;

	/** Greybox wheel spray by surface. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTSprayComponent> Spray;

	/** Procedural engine, tyre, skid and impact audio. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTVehicleAudioComponent> Audio;

	/** Approved H2 recording prototype, enabled only by the Range Rover mesh. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTRangeRoverAudioComponent> RangeRoverAudio;

	/** Winch: cable as a clamped spring force, hook carried on foot (ARCHITECTURE 6e). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTWinchComponent> Winch;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTDrivetrainComponent> Drivetrain;

	/** Boot storage; the character transfers to and from it. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTInventoryComponent> Boot;

	/** The environment stage: the leg's conditions profile sampled at the car (ARCHITECTURE 6c). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTEnvironmentComponent> Environment;

	/** Installed parts: the parts stage of the tuning, resistances, tank, winch (M4). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTPartSlotsComponent> Parts;

	/** Leg dressing LD5: pushes through soft vegetation (UGTVegetationSubsystem); driven by Tick after the winch. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Vehicle")
	TObjectPtr<UGTVegetationProbeComponent> VegProbe;

	enum class ECarInteraction : uint8 { None, Repair, RepairNoScrap, TakeHook, ReleaseWinch, Boot, Enter, OpenDoor, CloseDoor, EnterNeedsDoor };
	ECarInteraction ResolveInteraction(const FGTInteractionQuery& Query, EGTDamageRegion& OutRegion, int32& OutDoor) const;

	void EnsureDefaultInputAssets();
	void UpdateCamera(float DeltaSeconds);
	void PaintTracks(float DeltaSeconds, const UChaosWheeledVehicleMovementComponent& Move);

	UFUNCTION()
	void OnBodyHit(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent,
	               FVector NormalImpulse, const FHitResult& Hit);

	void OnThrottle(const FInputActionValue& Value);
	void OnThrottleReleased(const FInputActionValue& Value);
	void OnBrake(const FInputActionValue& Value);
	void OnBrakeReleased(const FInputActionValue& Value);
	void OnSteer(const FInputActionValue& Value);
	void OnSteerReleased(const FInputActionValue& Value);
	void OnHandbrakePressed(const FInputActionValue& Value);
	void OnHandbrakeReleased(const FInputActionValue& Value);
	void OnLook(const FInputActionValue& Value);
	void OnExit(const FInputActionValue& Value);
	void OnCameraToggle(const FInputActionValue& Value);
	void OnDiffLock(const FInputActionValue& Value);
	void OnLowRange(const FInputActionValue& Value);
	void OnReelPressed(const FInputActionValue& Value);
	void OnReelReleased(const FInputActionValue& Value);
	void OnReleaseWinch(const FInputActionValue& Value);

private:
	FGTResponsiveSteering ResponsiveSteering;
	float RawSteer = 0.f;
	FRotator LookOffset = FRotator::ZeroRotator;
	FRotator SmoothedCameraRotation = FRotator::ZeroRotator;
	float SmoothedCameraZ = 0.f;
	double LastLookInputTime = -1000.0;
	bool bCameraInitialised = false;
	bool bChaseCamera = false;
	bool bUseHeadSocket = false;
	TArray<FVector> LastStampPoints;
	TArray<bool> LastStampValid;
	// MudRunner MR1: each wheel's carried-mud stroke (UGTTrackPaintSubsystem::AddCarriedMud's FGTMudCarryState, kept flat here).
	TArray<FVector> LastCarryPoints;
	TArray<bool> LastCarryValid;
	TArray<float> CarryToNextCm;
	TArray<int32> CarrySeeds;
	// MR2 housekeeping 1: the stroke's covered ground and its noise key (the strength along the track).
	TArray<float> CarryDistanceCm;
	TArray<uint32> CarryNoiseKeys;
	TMap<FGameplayTag, double> HazardContactTimes;
};
