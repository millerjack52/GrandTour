#include "Race/GTTourDefinition.h"

#include "Run/GTLegDefinition.h"

namespace
{
	int32 ByPlace(const TArray<int32>& Table, int32 Place)
	{
		if (Table.Num() == 0 || Place < 1)
		{
			return 0;
		}
		return Table[FMath::Min(Place - 1, Table.Num() - 1)];
	}
}

int32 UGTTourDefinition::PointsForPlace(int32 Place) const
{
	return ByPlace(PointsByPlace, Place);
}

int32 UGTTourDefinition::PrizeForPlace(int32 Place) const
{
	return ByPlace(PrizeByPlace, Place);
}

FString UGTTourDefinition::Describe() const
{
	FString Names;
	for (const FGTRivalDefinition& Rival : Rivals)
	{
		Names += FString::Printf(TEXT(" %s(x%.2f)"), *Rival.Name, Rival.Skill);
	}
	return FString::Printf(TEXT("%s '%s' region=%s legs=%d rivals=[%s] credits=%d"), *TourId.ToString(), *DisplayName.ToString(), *Region.ToString(), LegPaths.Num(), *Names.TrimStart(), StartingCredits);
}

void UGTTourDefinition::ApplyDefaultTour01(const FString& LegFolder)
{
	TourId = TEXT("Tour01");
	DisplayName = FText::FromString(TEXT("The Altiplano"));
	Region = FText::FromString(TEXT("Bolivia"));
	CampMapPath = TEXT("/Game/GrandTour/Base/L_Base");
	LegPaths.Reset();
	for (int32 Index = 0; Index < UGTLegDefinition::DefaultLegCount(); ++Index)
	{
		LegPaths.Add(LegFolder / UGTLegDefinition::DefaultAssetName(Index));
	}
	Rivals.Reset();
	auto Add = [this](const TCHAR* Name, const TCHAR* Car, float Skill, float Consistency, float Grit)
	{
		FGTRivalDefinition Rival;
		Rival.Name = Name;
		Rival.Car = Car;
		Rival.Skill = Skill;
		Rival.Consistency = Consistency;
		Rival.Grit = Grit;
		Rivals.Add(Rival);
	};
	// One who is quick and fragile, one steady, one who never quits, one who is just slow.
	Add(TEXT("Ines Varga"), TEXT("a lowered Impreza"), 0.88f, 0.10f, 0.70f);
	Add(TEXT("Teodor Balan"), TEXT("a tidy Pajero"), 0.97f, 0.05f, 0.90f);
	Add(TEXT("Marisol Quispe"), TEXT("a tired Hilux"), 1.06f, 0.06f, 0.98f);
	Add(TEXT("Wendell Price"), TEXT("something with a snorkel"), 1.22f, 0.12f, 0.80f);
	StartingCredits = 300;
	PointsByPlace = { 10, 8, 6, 5, 4 };
	PrizeByPlace = { 200, 150, 100, 60, 40 };
	EndingWin = FText::FromString(TEXT("You won the Altiplano. The crew would like it noted that the car did most of it."));
	EndingPodium = FText::FromString(TEXT("A podium on the Altiplano. Not the top step, but the car is still a car, which is more than some can say."));
	EndingLose = FText::FromString(TEXT("You finished the Altiplano, which the producers say is the main thing. They are not paying you for it."));
}
