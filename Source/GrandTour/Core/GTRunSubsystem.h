#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Inventory/GTInventoryComponent.h"
#include "Parts/GTPartSlotsComponent.h"
#include "Race/GTStandings.h"
#include "Run/GTLegDefinition.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Vehicle/GTConditionComponent.h"
#include "GTRunSubsystem.generated.h"

class AGTCarPawn;
class AGTPlayerCharacter;
class UGTTourDefinition;

/** What one leg produced (ARCHITECTURE 5: results screen; the standings sum these). */
USTRUCT(BlueprintType)
struct FGTLegResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	FName LegId;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 LegNumber = 0;

	/** The mission was met: a did-not-finish (over an endurance limit) is recorded with this false. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	bool bCompleted = false;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	EGTMissionType Mission = EGTMissionType::TimeTrial;

	/** The verdict in words ("Photographed the spectacled bear", "Over the limit: did not finish"). */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	FString MissionText;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 PhotosTaken = 0;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	float TimeSeconds = 0.f;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	float ParTimeSeconds = 0.f;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	bool bOvertime = false;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 CheckpointsCleared = 0;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 CheckpointCount = 0;

	/** Everything in the boot and the bag at extraction. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TArray<FGTItemStack> Haul;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	float HaulWeightKg = 0.f;

	/** At the item table's base prices; the trader pays a fraction of it. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 HaulValue = 0;

	/** 1 = fastest on the leg (the rivals simulated by the tour, or the leg's fallback times outside one). */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 Rank = 1;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 RivalCount = 0;

	/** The rivals' simulated legs, in the tour's order. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TArray<FGTRivalLegOutcome> Rivals;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 Points = 0;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 PrizeCredits = 0;

	FString Describe() const;
};

/** What travels between levels and into the save: both inventories, the car's loadout and condition, and the consumables still running. */
USTRUCT(BlueprintType)
struct FGTCarrySnapshot
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	bool bValid = false;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TArray<FGTItemStack> Bag;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TArray<FGTItemStack> Boot;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TArray<FGTSlotEntry> Loadout;

	/** Missing from older saves: preserves the original balanced AWD conversion. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	float AWDFrontShare = .5f;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TMap<EGTCarPart, float> PartHealth;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	float FuelLitres = -1.f;

	/** Timed resistances from consumables still running on the car (a blanket used at the base lasts into the leg). */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TArray<FGTTimedResistance> CarResistances;

	/** The same on the character. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TArray<FGTTimedResistance> CharacterResistances;

	FString Describe() const;
};

/** Campaign state that survives level loads and the save (ARCHITECTURE 5, 9): one tour, its leg index, the results and the crew. */
USTRUCT(BlueprintType)
struct FGTCampaignState
{
	GENERATED_BODY()

	/** The tour being run, as a long package path; a runtime Tour 01 stands in when the asset is missing. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	FString TourPath = TEXT("/Game/GrandTour/Race/DA_Tour_01");

	/** Index into the tour's legs of the next leg to run; at the leg count the tour is over. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 CurrentLegIndex = 0;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TArray<FGTLegResult> Results;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 Currency = 300;

	/** Sum of leg times so far. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	float TotalTimeSeconds = 0.f;

	/** Bought crew tiers by track (Crew.Mechanic, Crew.Trader, Crew.Scout, Crew.Workbench). */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	TMap<FGameplayTag, int32> CrewTiers;

	/** Seeds the rivals' draws, so a save replays the same standings. */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Run")
	int32 Seed = 1;
};

/**
 * Owns the current campaign across level loads (ARCHITECTURE 5) and the save (ARCHITECTURE 9).
 * The run game mode reads the pending leg here, writes each leg's result back (scored against
 * the tour's rivals) and captures the carry snapshot at extraction; the base game mode applies
 * the snapshot on arrival, saves, and captures again on departure. A fresh start of the base or
 * of a leg loads the save first. No custom game instance is needed: a game instance subsystem
 * is created on the default one. One slot, GrandTour0; headless self-test runs use
 * GrandTourTest0 instead.
 */
UCLASS()
class GRANDTOUR_API UGTRunSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	// ---- legs and the tour --------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void SetPendingLeg(UGTLegDefinition* Leg) { PendingLeg = Leg; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	UGTLegDefinition* GetPendingLeg() const { return PendingLeg; }

	/** The campaign's tour: the asset at TourPath, else a runtime Tour 01. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	UGTTourDefinition* ResolveTour();

	/** The campaign's next leg from the tour (the asset, else the default leg of that index); null once the tour is over. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	UGTLegDefinition* ResolveNextLeg();

	/** Leg Index of the tour, the same way. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	UGTLegDefinition* ResolveLeg(int32 Index);

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	bool IsTourComplete() const;

	/** Draws the tour's rivals for the leg and fills the result's rank, rivals, points and prize (the leg's own fallback times only when the tour has no rivals). */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void ScoreResult(UPARAM(ref) FGTLegResult& Result, const UGTLegDefinition* Leg);

	/** Records the leg, banks its prize and moves the campaign to the next leg. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void RecordResult(const FGTLegResult& Result);

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	bool HasResult() const { return Campaign.Results.Num() > 0; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	const FGTLegResult& GetLastResult() const { return Campaign.Results.Last(); }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	const FGTCampaignState& GetCampaign() const { return Campaign; }

	/** The tour table so far. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	TArray<FGTStandingRow> BuildStandings();

	/** The ending card's line (the tour's, for the player's final place). */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	FString EndingLine();

	/** A fresh campaign on the same tour: leg 0, the tour's starting credits, a new seed, no snapshot. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void ResetCampaign();

	// ---- currency and crew ------------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	int32 GetCurrency() const { return Campaign.Currency; }

	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void AddCurrency(int32 Amount);

	/** False (and nothing spent) when the campaign cannot afford it. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	bool SpendCurrency(int32 Amount);

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	int32 GetCrewTier(FGameplayTag Track) const;

	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void SetCrewTier(FGameplayTag Track, int32 Tier);

	// ---- carry snapshot -----------------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "GT|Run")
	bool HasSnapshot() const { return Snapshot.bValid; }

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	const FGTCarrySnapshot& GetSnapshot() const { return Snapshot; }

	/** Reads both inventories, the loadout, the part health, the fuel and the running consumables off the pawns. */
	void CaptureFromPawns(const AGTCarPawn* Car, const AGTPlayerCharacter* Character);

	/** Writes the snapshot into the pawns (no-op without a valid snapshot). */
	void ApplyToPawns(AGTCarPawn* Car, AGTPlayerCharacter* Character) const;

	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void ClearSnapshot() { Snapshot = FGTCarrySnapshot(); }

	// ---- save ----------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	bool SaveToSlot();

	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	bool LoadFromSlot();

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	bool HasSaveInSlot() const;

	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	void DeleteSave();

	/** True when the command line carries a headless self-test switch (-GT...Test or -GTBaseShots): such runs save to GrandTourTest0 and never load the player's save on their own. */
	static bool IsSelfTestRun();

	UPROPERTY(BlueprintReadOnly, Category = "GT|Run")
	FString SlotName = TEXT("GrandTour0");

	UPROPERTY(BlueprintReadOnly, Category = "GT|Run")
	int32 SaveCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Run")
	int32 LoadCount = 0;

	/** Where a level-crossing headless test is (empty outside tests); FGTM4TestRunner reads and writes it. */
	UPROPERTY(Transient)
	FString TestStage;

	UFUNCTION(BlueprintPure, Category = "GT|Run")
	FString Describe() const;

private:
	UPROPERTY(Transient)
	TObjectPtr<UGTLegDefinition> PendingLeg;

	/** Default legs built at runtime, by index, when the assets are missing. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UGTLegDefinition>> RuntimeLegs;

	UPROPERTY(Transient)
	TObjectPtr<UGTTourDefinition> RuntimeTour;

	UPROPERTY(Transient)
	FGTCampaignState Campaign;

	UPROPERTY(Transient)
	FGTCarrySnapshot Snapshot;
};
