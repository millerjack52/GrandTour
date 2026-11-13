#include "Race/GTStandings.h"

#include "Core/GTRunSubsystem.h"
#include "Race/GTTourDefinition.h"
#include "Run/GTLegDefinition.h"

namespace
{
	float Hardness(EGTMissionType Mission)
	{
		switch (Mission)
		{
		case EGTMissionType::Endurance: return 1.f;
		case EGTMissionType::Photograph: return 0.7f;
		default: return 0.25f;
		}
	}

	/** A standard normal from two uniforms, clamped to a believable spread. */
	float ClampedNormal(FRandomStream& Random)
	{
		const float U1 = FMath::Max(Random.FRand(), 1e-6f);
		const float U2 = Random.FRand();
		const float Normal = FMath::Sqrt(-2.f * FMath::Loge(U1)) * FMath::Cos(2.f * PI * U2);
		return FMath::Clamp(Normal, -2.5f, 2.5f);
	}

	const TCHAR* PlayerRowName = TEXT("You");
}

float GTStandings::ExpectedTime(const FGTRivalDefinition& Rival, const UGTLegDefinition& Leg)
{
	return Leg.ParTimeSeconds * Rival.Skill;
}

FGTRivalLegOutcome GTStandings::SimulateRival(const FGTRivalDefinition& Rival, const UGTLegDefinition& Leg, int32 LegIndex, int32 RivalIndex, int32 Seed)
{
	FRandomStream Random(Seed ^ ((LegIndex + 1) * 7919) ^ ((RivalIndex + 1) * 104729));
	FGTRivalLegOutcome Outcome;
	Outcome.Name = Rival.Name;
	const float Spread = ClampedNormal(Random);
	Outcome.TimeSeconds = FMath::Max(1.f, ExpectedTime(Rival, Leg) * (1.f + Rival.Consistency * Spread));
	const float DropChance = (1.f - FMath::Clamp(Rival.Grit, 0.f, 1.f)) * Hardness(Leg.Mission);
	Outcome.bFinished = Random.FRand() >= DropChance;
	if (Leg.Mission == EGTMissionType::Endurance && Leg.TimeLimitSeconds > 0.f && Outcome.TimeSeconds > Leg.TimeLimitSeconds)
	{
		Outcome.bFinished = false;
	}
	return Outcome;
}

int32 GTStandings::PlaceLeg(const UGTTourDefinition& Tour, const UGTLegDefinition& Leg, int32 LegIndex, int32 Seed, float PlayerTime, bool bPlayerFinished, TArray<FGTRivalLegOutcome>& OutRivals, int32& OutPlayerPoints)
{
	OutRivals.Reset();
	for (int32 Index = 0; Index < Tour.Rivals.Num(); ++Index)
	{
		OutRivals.Add(SimulateRival(Tour.Rivals[Index], Leg, LegIndex, Index, Seed));
	}
	// Finishers by time; the player wins ties. Everyone who dropped out shares the places after them, the player first.
	int32 PlayerPlace = 1;
	int32 Finishers = bPlayerFinished ? 1 : 0;
	for (const FGTRivalLegOutcome& Rival : OutRivals)
	{
		if (Rival.bFinished)
		{
			++Finishers;
			if (bPlayerFinished && Rival.TimeSeconds < PlayerTime)
			{
				++PlayerPlace;
			}
		}
	}
	if (!bPlayerFinished)
	{
		PlayerPlace = Finishers + 1;
	}
	for (FGTRivalLegOutcome& Rival : OutRivals)
	{
		if (Rival.bFinished)
		{
			int32 Place = 1;
			if (bPlayerFinished && PlayerTime <= Rival.TimeSeconds)
			{
				++Place;
			}
			for (const FGTRivalLegOutcome& Other : OutRivals)
			{
				if (&Other != &Rival && Other.bFinished && (Other.TimeSeconds < Rival.TimeSeconds || (Other.TimeSeconds == Rival.TimeSeconds && &Other < &Rival)))
				{
					++Place;
				}
			}
			Rival.Place = Place;
			Rival.Points = Tour.PointsForPlace(Place);
		}
		else
		{
			Rival.Place = Finishers + (bPlayerFinished ? 1 : 2);
			Rival.Points = 0;
		}
	}
	OutPlayerPoints = bPlayerFinished ? Tour.PointsForPlace(PlayerPlace) : 0;
	return PlayerPlace;
}

TArray<FGTStandingRow> GTStandings::Build(const UGTTourDefinition& Tour, const TArray<FGTLegResult>& Results)
{
	TArray<FGTStandingRow> Rows;
	FGTStandingRow Player;
	Player.Name = PlayerRowName;
	Player.bPlayer = true;
	Rows.Add(Player);
	for (const FGTRivalDefinition& Rival : Tour.Rivals)
	{
		FGTStandingRow Row;
		Row.Name = Rival.Name;
		Rows.Add(Row);
	}
	for (const FGTLegResult& Result : Results)
	{
		FGTStandingRow& Me = Rows[0];
		++Me.LegsRun;
		Me.Points += Result.Points;
		if (Result.bCompleted)
		{
			++Me.LegsFinished;
			Me.TotalTimeSeconds += Result.TimeSeconds;
		}
		for (const FGTRivalLegOutcome& Outcome : Result.Rivals)
		{
			FGTStandingRow* Row = Rows.FindByPredicate([&Outcome](const FGTStandingRow& R) { return !R.bPlayer && R.Name == Outcome.Name; });
			if (!Row)
			{
				FGTStandingRow Extra;
				Extra.Name = Outcome.Name;
				Row = &Rows.Add_GetRef(Extra);
			}
			++Row->LegsRun;
			Row->Points += Outcome.Points;
			if (Outcome.bFinished)
			{
				++Row->LegsFinished;
				Row->TotalTimeSeconds += Outcome.TimeSeconds;
			}
		}
	}
	Rows.StableSort([](const FGTStandingRow& A, const FGTStandingRow& B)
	{
		if (A.Points != B.Points)
		{
			return A.Points > B.Points;
		}
		if (A.LegsFinished != B.LegsFinished)
		{
			return A.LegsFinished > B.LegsFinished;
		}
		return A.TotalTimeSeconds < B.TotalTimeSeconds;
	});
	for (int32 Index = 0; Index < Rows.Num(); ++Index)
	{
		Rows[Index].Place = Index + 1;
	}
	return Rows;
}

FGTStandingRow GTStandings::PlayerRow(const TArray<FGTStandingRow>& Rows)
{
	for (const FGTStandingRow& Row : Rows)
	{
		if (Row.bPlayer)
		{
			return Row;
		}
	}
	FGTStandingRow Row;
	Row.Name = PlayerRowName;
	Row.bPlayer = true;
	return Row;
}

FString GTStandings::EndingLine(const UGTTourDefinition& Tour, const TArray<FGTStandingRow>& Rows)
{
	const FGTStandingRow Me = PlayerRow(Rows);
	const FText& Line = Me.Place <= 1 ? Tour.EndingWin : Me.Place <= 3 ? Tour.EndingPodium : Tour.EndingLose;
	return Line.IsEmpty() ? FString::Printf(TEXT("You finished %d of %d."), Me.Place, Rows.Num()) : Line.ToString();
}
