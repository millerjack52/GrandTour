#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "GTPlayerController.generated.h"

class AGTCarPawn;
class AGTPlayerCharacter;
class UGTWorkshopComponent;

/**
 * Owns the possession swap (ARCHITECTURE 5, Enter / exit). Both pawns always exist: the game mode
 * spawns the car; the controller spawns the character the first time it possesses a car and
 * keeps it hidden inside. ExitCar puts the character at a clear door position, blends the camera
 * from the seat to the character's eyes and possesses it; the car keeps simulating with the
 * handbrake on. EnterCar reverses it. Mapping contexts follow the possessed pawn: each pawn adds
 * its own on setup and the controller removes the other's here.
 */
UCLASS()
class GRANDTOUR_API AGTPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AGTPlayerController();

	virtual void OnPossess(APawn* InPawn) override;
	virtual void SetupInputComponent() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	/** U: reversible walk-around customization while parked. */
	UFUNCTION(Exec)
	void GTWorkshop();
	UFUNCTION(BlueprintPure, Category = "GT|Workshop")
	UGTWorkshopComponent* GetWorkshop() const { return Workshop; }
	void SetWorkshopFullTick(bool bEnabled) { bShouldPerformFullTickWhenPaused = bEnabled; }

	/** Enter / gamepad Start: continue past the results screen (AGTRunGameMode::ContinueAfterLeg). */
	void OnContinuePressed();

	UFUNCTION(BlueprintCallable, Category = "GT|Possession")
	bool ExitCar();

	UFUNCTION(BlueprintCallable, Category = "GT|Possession")
	bool EnterCar();

	/** Enter the car being interacted with, rather than always returning to the last car. */
	UFUNCTION(BlueprintCallable, Category = "GT|Possession")
	bool EnterVehicle(AGTCarPawn* TargetCar);

	/** Garage transaction: keep the character on foot and replace only this controller's car. */
	UFUNCTION(BlueprintCallable, Category = "GT|Garage")
	bool ReplaceGarageVehicle(TSubclassOf<AGTCarPawn> VehicleClass, const FTransform& SpawnTransform, FString& Result);

	UFUNCTION(BlueprintPure, Category = "GT|Possession")
	bool IsDriving() const;

	/** The Proving Ground: GTGoto <station> puts the car (and you) 10 m before it, at rest; GTGoto list names them (GTProving::Goto). */
	UFUNCTION(Exec)
	void GTGoto(const FString& Station);

	UFUNCTION(BlueprintPure, Category = "GT|Possession")
	AGTCarPawn* GetCar() const { return Car.Get(); }

	UFUNCTION(BlueprintPure, Category = "GT|Possession")
	AGTPlayerCharacter* GetPlayerCharacter() const { return Character.Get(); }

	/** True if the driving context is active in the enhanced input subsystem (tests). */
	bool HasDrivingContext() const;
	bool HasOnFootContext() const;

	/** Seconds of camera blend on a swap; 0 = hard cut. */
	UPROPERTY(EditAnywhere, Category = "GT|Possession")
	float CameraBlendTime = 0.35f;

	/** Fastest the car may be moving (cm/s) to get out. */
	UPROPERTY(EditAnywhere, Category = "GT|Possession")
	float MaxExitSpeed = 300.f;

	UPROPERTY(EditAnywhere, Category = "GT|Possession")
	TSubclassOf<AGTPlayerCharacter> CharacterClass;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Possession")
	int32 SwapCount = 0;

private:
	UPROPERTY(VisibleAnywhere, Category = "GT|Workshop")
	TObjectPtr<UGTWorkshopComponent> Workshop;
	void EnsureCharacter(AGTCarPawn* ForCar);

	TWeakObjectPtr<AGTCarPawn> Car;
	TWeakObjectPtr<AGTPlayerCharacter> Character;
};
