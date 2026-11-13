#pragma once

#include "CoreMinimal.h"
#include "GTStandings.generated.h"

class UGTLegDefinition;
class UGTTourDefinition;
struct FGTLegResult;
struct FGTRivalDefinition;

/** A rival's simulated leg: the time, whether they finished, and where that put them. */
USTRUCT(BlueprintType)
struct FGTRivalLegOutcome
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Race")
	FString Name;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Race")
	float TimeSeconds = 0.f;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Race")
	bool bFinished = true;

	/** 1-based placing on the leg (the player included). */
	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Race")
	int32 Place = 0;

	UPROPERTY(BlueprintReadOnly, SaveGame, Category = "GT|Race")
	int32 Points = 0;
};

/** One row of the tour standings. */
USTRUCT(BlueprintType)
struct FGTStandingRow
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GT|Race")
	FString Name;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Race")
	bool bPlayer = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Race")
	int32 Points = 0;

	/** Sum of the finished legs' times. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Race")
	float TotalTimeSeconds = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Race")
	int32 LegsFinished = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Race")
	int32 LegsRun = 0;

	/** 1-based placing in the tour. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Race")
	int32 Place = 0;
};

/**
 * The rival standings simulation (PROJECT_PLAN 6: rivals are standings only). A rival's leg is
 * drawn once from the campaign's seed, the leg index and the rival's index, so a save replays
 * the same table and the briefing can quote expectations without spoiling the draw: time = par
 * x skill x (1 + consistency x a clamped normal), a did-not-finish by (1 - grit) x the mission's
 * hardness (time trial 0.25, photograph 0.7, endurance 1.0, plus over the limit), and points
 * and prize money by placing from the tour's tables. The standings sum the recorded results.
 */
namespace GTStandings
{
	/** The rival's draw for a leg; deterministic for the same seed, leg index and rival index. */
	GRANDTOUR_API FGTRivalLegOutcome SimulateRival(const FGTRivalDefinition& Rival, const UGTLegDefinition& Leg, int32 LegIndex, int32 RivalIndex, int32 Seed);

	/** What the briefing quotes before the leg: the rival at par x skill. */
	GRANDTOUR_API float ExpectedTime(const FGTRivalDefinition& Rival, const UGTLegDefinition& Leg);

	/** Draws every rival, places the player among them (finishers by time, then the rest) and fills Place and Points for all. Returns the player's place. */
	GRANDTOUR_API int32 PlaceLeg(const UGTTourDefinition& Tour, const UGTLegDefinition& Leg, int32 LegIndex, int32 Seed, float PlayerTime, bool bPlayerFinished, TArray<FGTRivalLegOutcome>& OutRivals, int32& OutPlayerPoints);

	/** The tour table from the recorded results, sorted: points, then legs finished, then total time. */
	GRANDTOUR_API TArray<FGTStandingRow> Build(const UGTTourDefinition& Tour, const TArray<FGTLegResult>& Results);

	/** The player's row, or a default one. */
	GRANDTOUR_API FGTStandingRow PlayerRow(const TArray<FGTStandingRow>& Rows);

	/** The ending card's line for where the player finished. */
	GRANDTOUR_API FString EndingLine(const UGTTourDefinition& Tour, const TArray<FGTStandingRow>& Rows);
}
