#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameplayTagContainer.h"
#include "InputActionValue.h"
#include "GTPlayerCharacter.generated.h"

class AGTCarPawn;
class AGTCraftingStation;
class UCameraComponent;
class UGTExposureComponent;
class UGTInteractionComponent;
class UGTInventoryComponent;
class UGTToolDefinition;
class UInputAction;
class UInputMappingContext;
class UMaterialInstanceDynamic;
class UStaticMeshComponent;

/**
 * The player on foot (ARCHITECTURE 9a): a first-person camera on the capsule at eye height, the
 * Epic mannequin drawn as a first-person primitive with its head and legs hidden so only the arms
 * and torso show (SKM_Manny_Simple in the pistol aim pose; Art/setup_m2_character.bat copies it
 * in), a greybox tool box in the right hand, look-at interaction, a weight-limited inventory and
 * the exposure meter. Head bob and the sprint FOV kick are procedural on the camera, each with a
 * toggle (H flips head bob while playing). E always goes to the interaction component; the boot
 * screen only adds scroll (select a stack) and T (move it), so looking at the boot and pressing E
 * closes it like any other prompt.
 *
 * The character always exists while the car does: AGTPlayerController hides it inside the car
 * (SetInCar) and puts it at the driver's door on exit, so its inventory and state never reset.
 * Input assets are optional as on the car: IMC_OnFoot and the IA_* actions are loaded from
 * /Game/GrandTour/Input when present, else the same mapping is built at runtime.
 */
UCLASS()
class GRANDTOUR_API AGTPlayerCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AGTPlayerCharacter();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual FVector GetPawnViewLocation() const override;

	// ---- car ---------------------------------------------------------------------------------
	/** Hidden, collision off and attached to the car while driving; restored when on foot. */
	void SetInCar(bool bIn, AGTCarPawn* Car);

	UFUNCTION(BlueprintPure, Category = "GT|Character")
	bool IsInCar() const { return bInCar; }

	// ---- tools -------------------------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "GT|Tools")
	UGTToolDefinition* GetCurrentTool() const;

	/** True if the current tool grants Tag (never while collapsed). */
	UFUNCTION(BlueprintPure, Category = "GT|Tools")
	bool HasToolTag(FGameplayTag Tag) const;

	/** -1 = bare hands. */
	UFUNCTION(BlueprintCallable, Category = "GT|Tools")
	void SelectTool(int32 Index);

	UFUNCTION(BlueprintCallable, Category = "GT|Tools")
	bool SelectToolByTag(FGameplayTag Tag);

	UFUNCTION(BlueprintCallable, Category = "GT|Tools")
	void NextTool();

	UFUNCTION(BlueprintCallable, Category = "GT|Tools")
	void PrevTool();

	UFUNCTION(BlueprintPure, Category = "GT|Tools")
	int32 GetToolCount() const { return Tools.Num(); }

	UFUNCTION(BlueprintPure, Category = "GT|Tools")
	int32 GetCurrentToolIndex() const { return CurrentToolIndex; }

	// ---- winch hook --------------------------------------------------------------------------
	/** Set by the car's winch when the hook is taken (Car) or put back (nullptr). */
	void SetCarriedHook(AGTCarPawn* Car);

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	bool IsCarryingHook() const { return HookCar.IsValid(); }

	AGTCarPawn* GetHookCar() const { return HookCar.Get(); }

	UFUNCTION(BlueprintCallable, Category = "GT|Winch")
	void DropHook();

	// ---- boot transfer (greybox UI drawn by AGTHUD) -------------------------------------------
	void OpenBoot(AGTCarPawn* Car);
	void CloseBoot();
	bool IsBootOpen() const { return bBootOpen; }
	AGTCarPawn* GetBootCar() const { return BootCar.Get(); }
	int32 GetBootSelection() const { return BootSelection; }

	// ---- station screens (M4, ARCHITECTURE 5 crafting stations) --------------------------------------
	void OpenStation(AGTCraftingStation* Station);
	void CloseStation();
	UFUNCTION(BlueprintPure, Category = "GT|Station")
	bool IsStationOpen() const { return CurrentStation.IsValid(); }
	AGTCraftingStation* GetStation() const { return CurrentStation.Get(); }
	int32 GetStationSelection() const { return StationSelection; }
	/** One selectable row up or down (0: the nearest selectable row); never parks on a caption. Moving re-arms T. */
	UFUNCTION(BlueprintCallable, Category = "GT|Station")
	void MoveStationSelection(int32 Delta);
	/** T: acts on the selected row and keeps the cursor on that row, not its index. If the row is gone, T does nothing until the cursor moves. */
	UFUNCTION(BlueprintCallable, Category = "GT|Station")
	bool ActOnStation();
	bool IsStationSelectionArmed() const { return bStationSelectionArmed; }

	/** The plain inventory screen's selection (scroll); T uses a consumable there. */
	int32 GetInventorySelection() const { return InventorySelection; }

	/** Uses one ItemId from the bag if it is a consumable and would do something now: effects on the car (the controller's) and on the meter. */
	UFUNCTION(BlueprintCallable, Category = "GT|Character")
	bool UseConsumable(FName ItemId);

	/** The player's own temporary resistance to a tag (consumables); 0..1. */
	UFUNCTION(BlueprintPure, Category = "GT|Character")
	float GetResistance(FGameplayTag Tag) const;

	UFUNCTION(BlueprintCallable, Category = "GT|Character")
	void AddTemporaryResistance(FGameplayTag Tag, float Strength, float Seconds);

	/** The consumables' resistances still running, with their time left (the run subsystem carries them between levels). */
	TArray<struct FGTTimedResistance> GetTemporaryResistances() const;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Character")
	int32 ConsumablesUsed = 0;

	/** What the last use from the inventory did, or why it was refused (drawn on the inventory screen). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Character")
	FString LastUseMessage;
	/** Moves the selected stack to the other side; returns units moved. */
	int32 TransferSelected();
	void MoveBootSelection(int32 Delta);

	// ---- state read by the HUD and tests -----------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "GT|Character")
	UGTInteractionComponent* GetInteraction() const { return Interaction; }

	UFUNCTION(BlueprintPure, Category = "GT|Character")
	UGTInventoryComponent* GetInventory() const { return Inventory; }

	UFUNCTION(BlueprintPure, Category = "GT|Character")
	UGTExposureComponent* GetExposure() const { return Exposure; }

	UFUNCTION(BlueprintPure, Category = "GT|Camera")
	UCameraComponent* GetCamera() const { return Camera; }

	UFUNCTION(BlueprintPure, Category = "GT|Camera")
	FVector GetBobOffset() const { return BobOffset; }

	UFUNCTION(BlueprintPure, Category = "GT|Character")
	bool IsSprinting() const;

	/** What the sprint key does; tests drive it directly. */
	UFUNCTION(BlueprintCallable, Category = "GT|Character")
	void SetSprintHeld(bool bHeld) { bSprintHeld = bHeld; }

	UFUNCTION(BlueprintPure, Category = "GT|Character")
	bool IsInventoryOpen() const { return bInventoryOpen; }

	UFUNCTION(BlueprintPure, Category = "GT|Character")
	FString Describe() const;

	/** The default on-foot mapping; also used by Art/setup_m2_character.bat to write IMC_OnFoot. */
	static void BuildOnFootMappings(UInputMappingContext* Context, UInputAction* Move, UInputAction* LookMouse, UInputAction* LookStick,
	                                UInputAction* Sprint, UInputAction* Interact, UInputAction* ToolNext, UInputAction* ToolPrev,
	                                UInputAction* Inventory, UInputAction* DropHook, UInputAction* ToggleHeadBob, UInputAction* Transfer, UInputAction* Jump);

	// ---- movement ----------------------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "GT|Movement")
	float WalkSpeed = 300.f;

	UPROPERTY(EditAnywhere, Category = "GT|Movement")
	float SprintSpeed = 550.f;

	/** Take-off speed of a jump, cm/s: 420 rises about 90 cm. 0 turns jumping off. Collapsed characters cannot jump. */
	UPROPERTY(EditAnywhere, Category = "GT|Movement", meta = (ClampMin = 0, ClampMax = 1500))
	float JumpVelocity = 420.f;

	/** Speed multiplier while collapsed (exposure at zero): drag yourself back to the car. */
	UPROPERTY(EditAnywhere, Category = "GT|Movement", meta = (ClampMin = 0.05, ClampMax = 1))
	float CollapsedSpeedScale = 0.3f;

	// ---- camera ------------------------------------------------------------------------------
	/** Eye height above the capsule centre, cm (capsule half height 96: eyes at 160 cm). */
	UPROPERTY(EditAnywhere, Category = "GT|Camera")
	float EyeHeight = 64.f;

	/** How far the eye drops while collapsed, cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera")
	float CollapsedEyeDrop = 45.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Camera|Options")
	bool bHeadBobEnabled = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Camera|Options")
	bool bSprintFovKickEnabled = true;

	/** Vertical dip per footfall at walking speed, cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 0, ClampMax = 10))
	float HeadBobVertical = 2.0f;

	/** Side-to-side sway per stride at walking speed, cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 0, ClampMax = 10))
	float HeadBobLateral = 1.0f;

	/** Strides per second at walking speed (two footfalls per stride); scales with speed. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 0.2, ClampMax = 4))
	float HeadBobFrequency = 0.9f;

	/** Degrees added to the field of view while sprinting. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera", meta = (ClampMin = 0, ClampMax = 30))
	float SprintFovKick = 8.f;

	/** Degrees of turn per mouse unit (the car uses 1). */
	UPROPERTY(EditAnywhere, Category = "GT|Camera")
	float MouseSensitivity = 1.f;

	/** Degrees per second at full stick. */
	UPROPERTY(EditAnywhere, Category = "GT|Camera")
	float StickLookRate = 120.f;

	UPROPERTY(EditAnywhere, Category = "GT|Camera")
	bool bInvertLookY = false;

	// ---- arms and tools (greybox) --------------------------------------------------------------
	/** The Epic mannequin, copied in by Art/setup_m2_character.bat; missing = no arms, everything else works. */
	// ---- exposure sources on foot (M3, ARCHITECTURE 6c/6d) --------------------------------------
	/** Exposure per second lost standing in full rain with no cover. */
	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float RainExposurePerSecond = 1.5f;

	/** Exposure per second per degree below zero. */
	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float ColdExposurePerDegree = 0.08f;

	/** Exposure per second at full intensity of the leg's Env.Cold / Env.Heat / Env.Dust. */
	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float EnvColdExposurePerSecond = 1.0f;

	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float EnvHeatExposurePerSecond = 0.8f;

	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float EnvDustExposurePerSecond = 0.3f;

	/** Seconds between the upward cover traces. */
	UPROPERTY(EditAnywhere, Category = "GT|Exposure")
	float CoverCheckInterval = 0.25f;

	/** The environment's drain last tick, points per second (HUD and tests). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Exposure")
	float EnvironmentDrainRate = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Exposure")
	bool bUnderCover = false;

	/** Rain, cold and the leg's conditions drain the meter while on foot (weather and profile sampled here). */
	void UpdateEnvironmentExposure(float DeltaSeconds);

	UPROPERTY(EditAnywhere, Category = "GT|Arms")
	FString ArmsMeshPath = TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple");

	/** Looping pose for the arms: the pistol aim brings both hands into view. */
	UPROPERTY(EditAnywhere, Category = "GT|Arms")
	FString ArmsPosePath = TEXT("/Game/Characters/Mannequins/Anims/Pistol/MF_Pistol_Idle_ADS.MF_Pistol_Idle_ADS");

	/** Bones hidden with their children so the mannequin reads as arms only (no head in the camera, no legs). */
	UPROPERTY(EditAnywhere, Category = "GT|Arms")
	TArray<FName> HiddenBones = { TEXT("head"), TEXT("thigh_l"), TEXT("thigh_r") };

	/** Where the head bone sits relative to the camera (behind the eye so the neck stays out of view). */
	UPROPERTY(EditAnywhere, Category = "GT|Arms")
	FVector ArmsHeadOffset = FVector(-12.f, 0.f, 4.f);

	UPROPERTY(EditAnywhere, Category = "GT|Arms")
	FName ToolSocketName = TEXT("hand_r");

	/** Tool box placement relative to the hand socket (with arms) or the camera (without). */
	UPROPERTY(EditAnywhere, Category = "GT|Arms")
	FVector ToolOffsetInHand = FVector(0.f, 0.f, 0.f);

	UPROPERTY(EditAnywhere, Category = "GT|Arms")
	FRotator ToolRotationInHand = FRotator(0.f, 0.f, 0.f);

	UPROPERTY(EditAnywhere, Category = "GT|Arms")
	FVector ToolOffsetInCamera = FVector(45.f, 18.f, -18.f);

	float CoverCheckTimer = 0.f;

	UPROPERTY(EditAnywhere, Category = "GT|Tools")
	FString ToolAssetFolder = TEXT("/Game/GrandTour/Tools");

	/** Set in the editor to override the defaults; empty = load DA_Tool_* from the folder or build the three defaults. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tools")
	TArray<TObjectPtr<UGTToolDefinition>> Tools;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Tools")
	bool bToolsFromAssets = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Arms")
	bool bHasArms = false;

	// ---- input ---------------------------------------------------------------------------------
	UPROPERTY(BlueprintReadOnly, Category = "GT|Input")
	bool bInputFromAssets = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input")
	TObjectPtr<UInputMappingContext> OnFootMappingContext;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> MoveAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> LookMouseAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> LookStickAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> SprintAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> InteractAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> ToolNextAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> ToolPrevAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> InventoryAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> DropHookAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> ToggleHeadBobAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> TransferAction;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Input") TObjectPtr<UInputAction> JumpAction;

protected:
	/** Bob and collapse offsets are applied here; the camera itself follows the control rotation. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Camera")
	TObjectPtr<USceneComponent> CameraRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Camera")
	TObjectPtr<UCameraComponent> Camera;

	/** First-person arms, attached to the camera so they follow the view. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Arms")
	TObjectPtr<USkeletalMeshComponent> Arms;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Arms")
	TObjectPtr<UStaticMeshComponent> ToolMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Character")
	TObjectPtr<UGTInteractionComponent> Interaction;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Character")
	TObjectPtr<UGTInventoryComponent> Inventory;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Character")
	TObjectPtr<UGTExposureComponent> Exposure;

	void LoadArms();
	void LoadTools();
	void EnsureDefaultInputAssets();
	void UpdateToolMesh();
	void UpdateCamera(float DeltaSeconds);

	void OnMove(const FInputActionValue& Value);
	void OnLookMouse(const FInputActionValue& Value);
	void OnLookStick(const FInputActionValue& Value);
	void OnSprintPressed(const FInputActionValue& Value);
	void OnJumpPressed(const FInputActionValue& Value);
	void OnJumpReleased(const FInputActionValue& Value);
	void OnSprintReleased(const FInputActionValue& Value);
	void OnInteractPressed(const FInputActionValue& Value);
	void OnInteractReleased(const FInputActionValue& Value);
	void OnToolNext(const FInputActionValue& Value);
	void OnToolPrev(const FInputActionValue& Value);
	void OnInventory(const FInputActionValue& Value);
	void OnDropHook(const FInputActionValue& Value);
	void OnToggleHeadBob(const FInputActionValue& Value);
	void OnTransfer(const FInputActionValue& Value);

private:
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> ToolMaterial;

	TWeakObjectPtr<AGTCarPawn> HookCar;
	TWeakObjectPtr<AGTCarPawn> BootCar;
	int32 CurrentToolIndex = -1;
	bool bInCar = false;
	bool bSprintHeld = false;
	bool bInventoryOpen = false;
	bool bBootOpen = false;
	int32 BootSelection = 0;
	int32 InventorySelection = 0;
	int32 StationSelection = 0;
	/** False after an act removed the selected row: T waits for the cursor to move rather than act on whatever took its place. */
	bool bStationSelectionArmed = true;
	TWeakObjectPtr<AGTCraftingStation> CurrentStation;
	struct FTemporaryResistance
	{
		FGameplayTag Tag;
		float Strength = 0.f;
		float TimeLeft = 0.f;
	};
	TArray<FTemporaryResistance> TemporaryResistances;
	float BobPhase = 0.f;
	FVector BobOffset = FVector::ZeroVector;
	float BaseFov = 90.f;
	float CurrentFov = 90.f;
	float CurrentEyeDrop = 0.f;
};
