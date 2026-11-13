#include "Core/GTRunSubsystem.h"

#include "Character/GTPlayerCharacter.h"
#include "Core/GTSaveGame.h"
#include "Race/GTTourDefinition.h"
#include "Run/GTLegDefinition.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTDriveLayout.h"

#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/DateTime.h"

bool UGTRunSubsystem::IsSelfTestRun()
{
	static const bool bTest = []
	{
		TArray<FString> Tokens;
		TArray<FString> Switches;
		FCommandLine::Parse(FCommandLine::Get(), Tokens, Switches);
		for (const FString& Switch : Switches)
		{
			if (Switch.StartsWith(TEXT("GT")) && (Switch.EndsWith(TEXT("Test")) || Switch.Equals(TEXT("GTBaseShots"))))
			{
				return true;
			}
		}
		return false;
	}();
	return bTest;
}

namespace
{
	/** Headless self-tests save here, so no test run can overwrite or delete the player's campaign. */
	const TCHAR* const TestSlotName = TEXT("GrandTourTest0");

	FString ActiveSlot(const FString& PlayerSlot)
	{
		return UGTRunSubsystem::IsSelfTestRun() ? FString(TestSlotName) : PlayerSlot;
	}

	FString DescribeStacks(const TArray<FGTItemStack>& Stacks)
	{
		FString Items;
		for (const FGTItemStack& Stack : Stacks)
		{
			Items += FString::Printf(TEXT(" %s x%d"), *Stack.ItemId.ToString(), Stack.Count);
		}
		return Items.TrimStart();
	}

	/** Loads an asset by its long package path with or without the object suffix. */
	template <typename T>
	T* LoadByPackagePath(const FString& PackagePath)
	{
		if (PackagePath.IsEmpty())
		{
			return nullptr;
		}
		const FString Path = PackagePath.Contains(TEXT(".")) ? PackagePath : FString::Printf(TEXT("%s.%s"), *PackagePath, *FPaths::GetBaseFilename(PackagePath));
		return LoadObject<T>(nullptr, *Path);
	}
}

FString FGTLegResult::Describe() const
{
	FString RivalText;
	for (const FGTRivalLegOutcome& Rival : Rivals)
	{
		RivalText += FString::Printf(TEXT(" %s=%s"), *Rival.Name, Rival.bFinished ? *FString::Printf(TEXT("%.0f"), Rival.TimeSeconds) : TEXT("DNF"));
	}
	return FString::Printf(TEXT("leg=%s #%d %s completed=%d '%s' time=%.1f par=%.0f overtime=%d checkpoints=%d/%d photos=%d haul=[%s] %.1f kg value=%d rank=%d/%d points=%d prize=%d rivals=[%s]"),
		*LegId.ToString(), LegNumber, *UGTLegDefinition::MissionName(Mission), bCompleted ? 1 : 0, *MissionText, TimeSeconds, ParTimeSeconds, bOvertime ? 1 : 0, CheckpointsCleared, CheckpointCount,
		PhotosTaken, *DescribeStacks(Haul), HaulWeightKg, HaulValue, Rank, RivalCount + 1, Points, PrizeCredits, *RivalText.TrimStart());
}

FString FGTCarrySnapshot::Describe() const
{
	FString Parts;
	for (const FGTSlotEntry& E : Loadout)
	{
		Parts += FString::Printf(TEXT(" %s=%s"), *UGTPartSlotsComponent::SlotName(E.Slot), *E.PartId.ToString());
	}
	return FString::Printf(TEXT("valid=%d bag=[%s] boot=[%s] loadout=[%s] health=%d fuel=%.1f"),
		bValid ? 1 : 0, *DescribeStacks(Bag), *DescribeStacks(Boot), *Parts.TrimStart(), PartHealth.Num(), FuelLitres);
}

UGTTourDefinition* UGTRunSubsystem::ResolveTour()
{
	if (UGTTourDefinition* Tour = LoadByPackagePath<UGTTourDefinition>(Campaign.TourPath))
	{
		return Tour;
	}
	if (!RuntimeTour)
	{
		RuntimeTour = NewObject<UGTTourDefinition>(this, TEXT("RuntimeTour01"), RF_Transient);
		RuntimeTour->ApplyDefaultTour01();
	}
	return RuntimeTour;
}

UGTLegDefinition* UGTRunSubsystem::ResolveLeg(int32 Index)
{
	UGTTourDefinition* Tour = ResolveTour();
	if (!Tour || Index < 0 || Index >= Tour->LegCount())
	{
		return nullptr;
	}
	if (UGTLegDefinition* Leg = LoadByPackagePath<UGTLegDefinition>(Tour->LegPaths[Index]))
	{
		return Leg;
	}
	// No asset: the default leg of that index (the tests, or a checkout before setup_m5_legs.bat).
	while (RuntimeLegs.Num() <= Index)
	{
		RuntimeLegs.Add(nullptr);
	}
	if (!RuntimeLegs[Index])
	{
		UGTLegDefinition* Leg = NewObject<UGTLegDefinition>(this, *FString::Printf(TEXT("RuntimeLeg%02d"), Index + 1), RF_Transient);
		Leg->ApplyDefault(Index);
		RuntimeLegs[Index] = Leg;
	}
	return RuntimeLegs[Index];
}

UGTLegDefinition* UGTRunSubsystem::ResolveNextLeg()
{
	return ResolveLeg(Campaign.CurrentLegIndex);
}

bool UGTRunSubsystem::IsTourComplete() const
{
	const UGTTourDefinition* Tour = LoadByPackagePath<UGTTourDefinition>(Campaign.TourPath);
	const int32 LegCount = Tour ? Tour->LegCount() : (RuntimeTour ? RuntimeTour->LegCount() : UGTLegDefinition::DefaultLegCount());
	return Campaign.CurrentLegIndex >= LegCount;
}

void UGTRunSubsystem::ScoreResult(FGTLegResult& Result, const UGTLegDefinition* Leg)
{
	Result.Rivals.Reset();
	Result.Points = 0;
	Result.PrizeCredits = 0;
	const UGTTourDefinition* Tour = ResolveTour();   // the asset, else the runtime tour (built here if nothing asked for it before)
	if (Tour && Leg && Tour->Rivals.Num() > 0)
	{
		Result.Rank = GTStandings::PlaceLeg(*Tour, *Leg, Campaign.CurrentLegIndex, Campaign.Seed, Result.TimeSeconds, Result.bCompleted, Result.Rivals, Result.Points);
		Result.RivalCount = Result.Rivals.Num();
		Result.PrizeCredits = Result.bCompleted ? Tour->PrizeForPlace(Result.Rank) : 0;
	}
	else if (Leg)
	{
		Result.Rank = Result.bCompleted ? Leg->RankForTime(Result.TimeSeconds) : Leg->RivalTimesSeconds.Num() + 1;
		Result.RivalCount = Leg->RivalTimesSeconds.Num();
	}
}

void UGTRunSubsystem::RecordResult(const FGTLegResult& Result)
{
	Campaign.Results.Add(Result);
	Campaign.TotalTimeSeconds += Result.TimeSeconds;
	Campaign.Currency += Result.PrizeCredits;
	++Campaign.CurrentLegIndex;   // a did-not-finish still moves the tour on; the result says so
	UE_LOG(LogTemp, Display, TEXT("UGTRunSubsystem: recorded %s (legs %d, total %.1f s, credits %d, tour %s)"), *Result.Describe(), Campaign.Results.Num(), Campaign.TotalTimeSeconds, Campaign.Currency,
		IsTourComplete() ? TEXT("over") : TEXT("continues"));
}

TArray<FGTStandingRow> UGTRunSubsystem::BuildStandings()
{
	UGTTourDefinition* Tour = ResolveTour();
	return Tour ? GTStandings::Build(*Tour, Campaign.Results) : TArray<FGTStandingRow>();
}

FString UGTRunSubsystem::EndingLine()
{
	UGTTourDefinition* Tour = ResolveTour();
	return Tour ? GTStandings::EndingLine(*Tour, BuildStandings()) : FString();
}

void UGTRunSubsystem::ResetCampaign()
{
	const FString TourPath = Campaign.TourPath;
	Campaign = FGTCampaignState();
	Campaign.TourPath = TourPath;
	Campaign.Seed = static_cast<int32>(FDateTime::UtcNow().GetTicks() & 0x7fffffff);
	if (const UGTTourDefinition* Tour = ResolveTour())
	{
		Campaign.Currency = Tour->StartingCredits;
	}
	Snapshot = FGTCarrySnapshot();
	PendingLeg = nullptr;
}

void UGTRunSubsystem::AddCurrency(int32 Amount)
{
	Campaign.Currency = FMath::Max(0, Campaign.Currency + Amount);
}

bool UGTRunSubsystem::SpendCurrency(int32 Amount)
{
	if (Amount < 0 || Campaign.Currency < Amount)
	{
		return false;
	}
	Campaign.Currency -= Amount;
	return true;
}

int32 UGTRunSubsystem::GetCrewTier(FGameplayTag Track) const
{
	const int32* Tier = Campaign.CrewTiers.Find(Track);
	return Tier ? *Tier : 0;
}

void UGTRunSubsystem::SetCrewTier(FGameplayTag Track, int32 Tier)
{
	Campaign.CrewTiers.Add(Track, FMath::Max(0, Tier));
}

void UGTRunSubsystem::CaptureFromPawns(const AGTCarPawn* Car, const AGTPlayerCharacter* Character)
{
	Snapshot = FGTCarrySnapshot();
	if (Character && Character->GetInventory())
	{
		Snapshot.Bag = Character->GetInventory()->Items;
	}
	if (Character)
	{
		Snapshot.CharacterResistances = Character->GetTemporaryResistances();
	}
	if (Car)
	{
		if (Car->GetBoot())
		{
			Snapshot.Boot = Car->GetBoot()->Items;
		}
		if (Car->GetParts())
		{
			Snapshot.Loadout = Car->GetParts()->GetLoadout();
			Snapshot.AWDFrontShare = Car->GetDrivetrain()->GetAWDFrontShare();
			Snapshot.CarResistances = Car->GetParts()->GetTemporaryResistances();
		}
		if (const UGTConditionComponent* Condition = Car->GetCondition())
		{
			for (uint8 Index = 0; Index < static_cast<uint8>(EGTCarPart::Count); ++Index)
			{
				const EGTCarPart Part = static_cast<EGTCarPart>(Index);
				Snapshot.PartHealth.Add(Part, Condition->GetPartHealth(Part));
			}
			Snapshot.FuelLitres = Condition->FuelLitres;
		}
	}
	Snapshot.bValid = Car != nullptr || Character != nullptr;
	UE_LOG(LogTemp, Display, TEXT("UGTRunSubsystem: captured %s"), *Snapshot.Describe());
}

void UGTRunSubsystem::ApplyToPawns(AGTCarPawn* Car, AGTPlayerCharacter* Character) const
{
	if (!Snapshot.bValid)
	{
		return;
	}
	if (Character && Character->GetInventory())
	{
		Character->GetInventory()->Items = Snapshot.Bag;
		++Character->GetInventory()->Version;
	}
	if (Character)
	{
		for (const FGTTimedResistance& R : Snapshot.CharacterResistances)
		{
			Character->AddTemporaryResistance(R.Tag, R.Strength, R.SecondsLeft);
		}
	}
	if (Car)
	{
		if (Car->GetBoot())
		{
			Car->GetBoot()->Items = Snapshot.Boot;
			++Car->GetBoot()->Version;
		}
		if (Car->GetParts() && Snapshot.Loadout.Num() > 0)
		{
			Car->GetParts()->ApplyLoadout(Snapshot.Loadout, /*bResetHealth*/ false);
		}
		Car->GetDrivetrain()->AWDFrontShare = GTDriveLayout::NormalizeAWDFrontShare(Snapshot.AWDFrontShare);
		if (Car->GetParts())
		{
			for (const FGTTimedResistance& R : Snapshot.CarResistances)
			{
				Car->GetParts()->AddTemporaryResistance(R.Tag, R.Strength, R.SecondsLeft);
			}
		}
		if (UGTConditionComponent* Condition = Car->GetCondition())
		{
			for (const TPair<EGTCarPart, float>& Pair : Snapshot.PartHealth)
			{
				Condition->SetPartHealth(Pair.Key, Pair.Value);
			}
			if (Snapshot.FuelLitres >= 0.f)
			{
				Condition->FuelLitres = FMath::Min(Snapshot.FuelLitres, Condition->TankCapacityLitres);
			}
		}
	}
	UE_LOG(LogTemp, Display, TEXT("UGTRunSubsystem: applied %s"), *Snapshot.Describe());
}

bool UGTRunSubsystem::SaveToSlot()
{
	UGTSaveGame* Save = Cast<UGTSaveGame>(UGameplayStatics::CreateSaveGameObject(UGTSaveGame::StaticClass()));
	if (!Save)
	{
		return false;
	}
	Save->Campaign = Campaign;
	Save->Snapshot = Snapshot;
	const FString Slot = ActiveSlot(SlotName);
	const bool bOk = UGameplayStatics::SaveGameToSlot(Save, Slot, 0);
	if (bOk)
	{
		++SaveCount;
	}
	UE_LOG(LogTemp, Display, TEXT("UGTRunSubsystem: save %s: %s"), *Slot, bOk ? TEXT("ok") : TEXT("FAILED"));
	return bOk;
}

bool UGTRunSubsystem::LoadFromSlot()
{
	const FString Slot = ActiveSlot(SlotName);
	UGTSaveGame* Save = Cast<UGTSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0));
	if (!Save)
	{
		return false;
	}
	Campaign = Save->Campaign;
	Snapshot = Save->Snapshot;
	if (Campaign.TourPath.IsEmpty())
	{
		Campaign.TourPath = FGTCampaignState().TourPath;   // a version 1 save: one leg, no tour
	}
	++LoadCount;
	UE_LOG(LogTemp, Display, TEXT("UGTRunSubsystem: loaded %s (version %d): %s"), *Slot, Save->Version, *Describe());
	return true;
}

bool UGTRunSubsystem::HasSaveInSlot() const
{
	return UGameplayStatics::DoesSaveGameExist(ActiveSlot(SlotName), 0);
}

void UGTRunSubsystem::DeleteSave()
{
	const FString Slot = ActiveSlot(SlotName);
	if (UGameplayStatics::DoesSaveGameExist(Slot, 0))
	{
		UGameplayStatics::DeleteGameInSlot(Slot, 0);
	}
}

FString UGTRunSubsystem::Describe() const
{
	FString Crew;
	for (const TPair<FGameplayTag, int32>& Pair : Campaign.CrewTiers)
	{
		Crew += FString::Printf(TEXT(" %s=%d"), *Pair.Key.ToString(), Pair.Value);
	}
	return FString::Printf(TEXT("tour=%s legIndex=%d results=%d currency=%d total=%.1f seed=%d crew=[%s] snapshot: %s"),
		*Campaign.TourPath, Campaign.CurrentLegIndex, Campaign.Results.Num(), Campaign.Currency, Campaign.TotalTimeSeconds, Campaign.Seed, *Crew.TrimStart(), *Snapshot.Describe());
}
