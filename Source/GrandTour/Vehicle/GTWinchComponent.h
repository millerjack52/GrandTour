#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GTWinchComponent.generated.h"

class AGTPlayerCharacter;
class UCableComponent;
class UGTConditionComponent;
class UGTWinchAnchorComponent;
class USkeletalMeshComponent;

UENUM(BlueprintType)
enum class EGTWinchState : uint8
{
	Stowed,
	HookCarried,
	Attached,
	Snapped
};

/**
 * The car's winch (ARCHITECTURE 6e). The cable is a force, never a constraint: while attached,
 * a clamped spring pulls the car's mount toward the anchor by stiffness x (distance - rest
 * length) plus damping, capped at the pull force scaled by the winch part's health. Reeling from
 * the seat shortens the rest length at the reel speed, slowing to a stall as the tension nears
 * the cap. An anchor whose strength is below the tension for AnchorFailDelay tears out and the
 * cable goes slack; pulling at the cable's limit against something that will not move for
 * SnapDelay snaps the cable, whips the car and damages the winch part. On foot the hook is
 * carried on a tether: the character cannot walk further than the cable length from the mount.
 * A UCableComponent draws it; the winch becomes a gadget-slot part when the part system lands.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTWinchComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTWinchComponent();

	virtual void BeginPlay() override;

	/** Called by the car every tick with its physics body and condition. */
	void Update(float DeltaSeconds, USkeletalMeshComponent& Body, UGTConditionComponent& Condition);

	UFUNCTION(BlueprintCallable, Category = "GT|Winch")
	bool TakeHook(AGTPlayerCharacter* Character);

	UFUNCTION(BlueprintCallable, Category = "GT|Winch")
	void DropHook();

	UFUNCTION(BlueprintCallable, Category = "GT|Winch")
	bool AttachTo(UGTWinchAnchorComponent* Anchor);

	/**
	 * Back to stowed from any state. The pull ends here (the cable is a force, so there is nothing to undo); the drawn
	 * cable then runs back from where the hook was to the drum at RewindSpeed and hides (section 51).
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Winch")
	void Release();

	/** The cable's drawn length in cm: 0 while hidden; during a rewind, what is left to wind in. */
	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	float GetDrawnCableCm() const;

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	bool IsRewinding() const { return RewindRemainingCm > 0.f; }

	UFUNCTION(BlueprintCallable, Category = "GT|Winch")
	void SetReeling(bool bReel) { bReeling = bReel; }

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	bool IsReeling() const { return bReeling; }

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	bool CanTakeHook() const { return bEnabled && (State == EGTWinchState::Stowed || State == EGTWinchState::Snapped); }

	/** False when no winch part is installed in the gadget slot (UGTPartSlotsComponent sets it). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Winch")
	bool bEnabled = true;

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	EGTWinchState GetState() const { return State; }

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	FVector GetMountLocation() const;

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	float GetTensionN() const { return TensionN; }

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	float GetRestLength() const { return RestLength; }

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	float GetCableDistance() const;

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	FString Describe() const;

	UGTWinchAnchorComponent* GetAnchor() const { return Anchor.Get(); }

	/** Mount on the front bumper, car space cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	FVector MountOffset = FVector(240.f, 0.f, 55.f);

	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float CableLength = 2500.f;

	/** Rated line pull, N (42 kN is a 9500 lb winch). */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float PullForceN = 40000.f;

	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float ReelSpeed = 150.f;

	/**
	 * How fast the drawn cable runs back to the drum after a release, cm/s. Visual only (section 51, the owner's
	 * "rewind visibly"): proposed 500 (a full 25 m in 5 s), unmeasured by eye; the owner names it.
	 */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float RewindSpeed = 500.f;

	/** Cable stiffness, N per cm of stretch. */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float SpringNPerCm = 2000.f;

	/** Cable damping, N per cm/s of stretch rate (15 % of critical for the car). */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float DampingNsPerCm = 60.f;

	/** Pulling at or above this (N) against something that does not move snaps the cable. */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float BreakForceN = 36000.f;

	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float SnapDelay = 1.5f;

	/** Below this closing speed (cm/s) the pull counts as stalled. */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float StallSpeed = 20.f;

	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float AnchorFailDelay = 0.3f;

	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float MinRestLength = 150.f;

	/** Winch part health lost when the cable snaps. */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float SnapDamage = 0.5f;

	/** Recoil given to the car when the cable snaps, cm/s. */
	UPROPERTY(EditAnywhere, Category = "GT|Winch")
	float SnapRecoilSpeed = 100.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Winch")
	float MaxTensionN = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Winch")
	int32 CableSnaps = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Winch")
	int32 AnchorFailures = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Winch")
	int32 TetherClamps = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Winch")
	int32 AttachCount = 0;

private:
	void UpdateTether();
	void UpdatePull(float DeltaSeconds, USkeletalMeshComponent& Body, UGTConditionComponent& Condition);
	void Snap(USkeletalMeshComponent& Body, UGTConditionComponent& Condition, const FVector& Direction);
	void UpdateCableVisual();
	void StartRewind(const FVector& HookWorld);
	void UpdateRewind(float DeltaSeconds);
	/** Clears the anchor's HeldBy when it points at this winch. */
	void ForgetAnchor();

	UPROPERTY(Transient)
	TObjectPtr<UCableComponent> Cable;

	TWeakObjectPtr<AGTPlayerCharacter> HookCarrier;
	TWeakObjectPtr<UGTWinchAnchorComponent> Anchor;
	EGTWinchState State = EGTWinchState::Stowed;
	float RestLength = 0.f;
	float TensionN = 0.f;
	float LastStretch = 0.f;
	float SnapTimer = 0.f;
	float AnchorOverloadTimer = 0.f;
	bool bReeling = false;
	/** The rewind after a release: cable left to wind in (cm), the straight run from the drum to the hook, and its direction in the body's space. */
	float RewindRemainingCm = 0.f;
	float RewindChordCm = 0.f;
	FVector RewindDirLocal = FVector::ForwardVector;
};
