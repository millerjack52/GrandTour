#pragma once

#include "CoreMinimal.h"
#include "Core/GTDriveTestGameMode.h"
#include "Core/GTM4TestRunner.h"
#include "GTBaseGameMode.generated.h"

class AGTCarPawn;
class AGTPlayerCharacter;
class UGTRunSubsystem;

/**
 * The convoy base (ARCHITECTURE 5, AGTBaseGameMode): the car spawns at the PlayerStart (on the
 * lift), the campaign's carry snapshot is applied to the car and the character (loaded from
 * the save on a fresh start), the game is saved on arrival, and the player is put on foot
 * beside the car. Driving out through the AGTDepartGate captures the snapshot, saves, sets the
 * campaign's next leg as pending and opens its map. Derives from the test game mode so the
 * headless flags work here too (-GTLoopTest continues through the base).
 */
UCLASS()
class GRANDTOUR_API AGTBaseGameMode : public AGTDriveTestGameMode
{
	GENERATED_BODY()

public:
	AGTBaseGameMode();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** Captures, saves and opens the next leg. False when nothing to depart with. */
	UFUNCTION(BlueprintCallable, Category = "GT|Base")
	bool Depart();

	UFUNCTION(BlueprintPure, Category = "GT|Base")
	bool HasArrived() const { return bArrived; }

	/** Skips the arrival save (tests that check the slot themselves). */
	UPROPERTY(EditAnywhere, Category = "GT|Base")
	bool bSaveOnArrival = true;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Base")
	bool bLoadedFromSave = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Base")
	bool bDeparted = false;

private:
	void Arrive();
	UGTRunSubsystem* Run() const;

	TUniquePtr<FGTM4TestRunner> M4Test;
	bool bArrived = false;
	bool bRefusedLogged = false;
};
