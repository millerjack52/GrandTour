#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameStateBase.h"
#include "Core/GTRunSubsystem.h"
#include "GTRunGameState.generated.h"

class AGTCarPawn;
class AGTCheckpoint;
class AGTExtractionZone;
class AGTPhotoSubject;
class UGTLegDefinition;

DECLARE_MULTICAST_DELEGATE(FGTOnExtractionReady);

UENUM(BlueprintType)
enum class EGTLegPhase : uint8
{
	/** No leg on this map (test tracks): nothing runs. */
	None,
	/** Leg set, timer waiting for the car to move. */
	Staging,
	Running,
	Finished
};

/**
 * Run-scoped state (ARCHITECTURE 5): the leg timer, the ordered checkpoints, the mission's
 * other objectives (photographs), the extraction hold and the progress along the leg that the
 * conditions profile is sampled at. Ticks the checkpoint and extraction tests itself with the
 * player's car; the game mode starts the leg, builds the result and shows the results screen.
 * The extraction only accepts the car once the mission is satisfied (checkpoints, and the
 * pictures on a photograph leg); an endurance leg past its limit is failed but still ends at
 * the zone, as a did-not-finish.
 */
UCLASS()
class GRANDTOUR_API AGTRunGameState : public AGameStateBase
{
	GENERATED_BODY()

public:
	AGTRunGameState();

	virtual void Tick(float DeltaSeconds) override;

	/** Sets the leg and gathers the map's checkpoints (sorted by Index), extraction zone and photo subjects. */
	void SetLeg(UGTLegDefinition* InLeg, const FVector& StartLocation);

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	UGTLegDefinition* GetLeg() const { return Leg; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	EGTLegPhase GetPhase() const { return Phase; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	float GetLegTime() const { return LegTime; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	int32 GetCheckpointsCleared() const { return CheckpointsCleared; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	int32 GetCheckpointCount() const { return Checkpoints.Num(); }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	bool AllCheckpointsCleared() const { return CheckpointsCleared >= Checkpoints.Num(); }

	/** Pictures taken on a photograph leg. */
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	int32 GetPhotosTaken() const { return PhotosTaken; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	int32 GetPhotosRequired() const;

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	int32 GetPhotoSubjectCount() const { return PhotoSubjects.Num(); }

	/** Everything the mission asks before the zone accepts the car. */
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	bool IsMissionSatisfied() const;

	/** An endurance leg past its limit: the extraction ends it as a did-not-finish. */
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	bool IsMissionFailed() const;

	/** Why the zone refuses the car right now ("checkpoint 2 first", "photograph the spectacled bear first"); empty when it would accept. */
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	FString GetExtractionRefusal() const;

	/** The HUD's objective line beyond the checkpoints ("Photograph the spectacled bear  0 / 1", "OVER THE LIMIT: no result"); empty when there is none. */
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	FString GetMissionLine() const;

	/** Progress 0..1 along start -> checkpoints -> extraction, from the car's position on the current segment. */
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	float GetProgress() const { return Progress; }

	/** Progress a world point would have on the current segment (the character on foot samples conditions with it). */
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	float ProgressAt(const FVector& WorldLocation) const;

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	bool IsOvertime() const { return bOvertime; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	AGTCheckpoint* GetNextCheckpoint() const;

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	AGTExtractionZone* GetExtraction() const { return Extraction.Get(); }

	/** Hold progress 0..1 while the car sits in the extraction zone. */
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	float GetExtractionProgress() const;

	/** Distance (cm) and signed bearing (degrees, positive = right) from the car to the next objective; false with none. */
	bool GetObjectiveBearing(float& OutDistance, float& OutBearing) const;

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	const FGTLegResult& GetResult() const { return Result; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	FString Describe() const;

	/** The game mode calls these. */
	void StartLeg();
	void FinishLeg(const FGTLegResult& InResult);
	void ClearCheckpoint(int32 Index);

	/** Photo subjects call these (BeginPlay and Interact). */
	void RegisterPhotoSubject(AGTPhotoSubject* Subject);
	void NotifyPhotographed(AGTPhotoSubject* Subject);

	/** Speed (cm/s) at which the leg timer starts. */
	UPROPERTY(EditAnywhere, Category = "GT|Run")
	float StartSpeed = 50.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Run")
	int32 ExtractionAttemptsRefused = 0;

	/** The last refusal's words, for the HUD. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Run")
	FString LastRefusal;

	/** Fired once when the extraction hold completes; the game mode builds the result. */
	FGTOnExtractionReady OnExtractionReady;

private:
	AGTCarPawn* FindPlayerCar() const;

	UPROPERTY(Transient)
	TObjectPtr<UGTLegDefinition> Leg;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AGTCheckpoint>> Checkpoints;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AGTPhotoSubject>> PhotoSubjects;

	TWeakObjectPtr<AGTExtractionZone> Extraction;
	TArray<FVector> RoutePoints;   // start, checkpoints, extraction
	EGTLegPhase Phase = EGTLegPhase::None;
	float LegTime = 0.f;
	int32 CheckpointsCleared = 0;
	int32 PhotosTaken = 0;
	float Progress = 0.f;
	bool bOvertime = false;
	float ExtractionHold = 0.f;
	bool bExtractionFired = false;
	FGTLegResult Result;
};
