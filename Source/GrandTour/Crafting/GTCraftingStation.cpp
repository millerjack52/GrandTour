#include "Crafting/GTCraftingStation.h"

#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Core/GTPlayerController.h"
#include "Core/GTRunSubsystem.h"
#include "Crafting/GTRecipeDefinition.h"
#include "Economy/GTUpgradeDefinition.h"
#include "Inventory/GTInventoryComponent.h"
#include "Parts/GTItemDefinition.h"
#include "Parts/GTItemRegistry.h"
#include "Parts/GTPartSlotsComponent.h"
#include "Race/GTStandings.h"
#include "Race/GTTourDefinition.h"
#include "Run/GTLegDefinition.h"
#include "Vehicle/GTBodyComponent.h"
#include "Vehicle/GTBodyStateComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTWinchAnchor.h"
#include "Weather/GTWeatherStateDefinition.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

FGTScreenRow FGTScreenRow::Header(const FString& Text)
{
	FGTScreenRow Row;
	Row.Text = Text;
	Row.bHeader = true;
	Row.bEnabled = false;
	return Row;
}

FGTScreenRow FGTScreenRow::Line(const FString& Text, int32 Action, bool bEnabled, const FString& Hint)
{
	FGTScreenRow Row;
	Row.Text = Text;
	Row.Action = Action;
	Row.bEnabled = bEnabled;
	Row.Hint = Hint;
	return Row;
}

// ---- base ------------------------------------------------------------------------------------------

AGTCraftingStation::AGTCraftingStation()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		Mesh->SetStaticMesh(CubeMesh.Object);
	}
}

void AGTCraftingStation::BeginPlay()
{
	Super::BeginPlay();
	Mesh->SetRelativeScale3D(GreyboxSize / 100.f);
	GTGreybox::ApplyPropColour(Mesh, this, Colour);
}

UGTRunSubsystem* AGTCraftingStation::Run() const
{
	const UGameInstance* GameInstance = GetWorld() ? GetWorld()->GetGameInstance() : nullptr;
	return GameInstance ? GameInstance->GetSubsystem<UGTRunSubsystem>() : nullptr;
}

UGTItemRegistry* AGTCraftingStation::Registry() const
{
	return UGTItemRegistry::Get(this);
}

AGTCarPawn* AGTCraftingStation::FindPlayerCar() const
{
	if (const AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0)))
	{
		return PC->GetCar() ? PC->GetCar() : Cast<AGTCarPawn>(PC->GetPawn());
	}
	return nullptr;
}

UGTInventoryComponent* AGTCraftingStation::Bag(const AGTPlayerCharacter* User)
{
	return User ? User->GetInventory() : nullptr;
}

UGTInventoryComponent* AGTCraftingStation::Boot(const AGTCarPawn* Car)
{
	return Car ? Car->GetBoot() : nullptr;
}

int32 AGTCraftingStation::CountBoth(const AGTPlayerCharacter* User, const AGTCarPawn* Car, FName ItemId)
{
	return (Bag(User) ? Bag(User)->CountOf(ItemId) : 0) + (Boot(Car) ? Boot(Car)->CountOf(ItemId) : 0);
}

int32 AGTCraftingStation::RemoveBoth(AGTPlayerCharacter* User, AGTCarPawn* Car, FName ItemId, int32 Count)
{
	int32 Removed = Bag(User) ? Bag(User)->Remove(ItemId, Count) : 0;
	if (Removed < Count && Boot(Car))
	{
		Removed += Boot(Car)->Remove(ItemId, Count - Removed);
	}
	return Removed;
}

int32 AGTCraftingStation::GiveBoth(AGTPlayerCharacter* User, AGTCarPawn* Car, FName ItemId, int32 Count)
{
	int32 Given = Bag(User) ? Bag(User)->Add(ItemId, Count) : 0;
	if (Given < Count && Boot(Car))
	{
		Given += Boot(Car)->Add(ItemId, Count - Given);
	}
	return Given;
}

int32 AGTCraftingStation::GiveBootFirst(AGTPlayerCharacter* User, AGTCarPawn* Car, FName ItemId, int32 Count)
{
	int32 Given = Boot(Car) ? Boot(Car)->Add(ItemId, Count) : 0;
	if (Given < Count && Bag(User))
	{
		Given += Bag(User)->Add(ItemId, Count - Given);
	}
	return Given;
}

FGTInteractionOffer AGTCraftingStation::GetInteractionOffer(const FGTInteractionQuery& Query) const
{
	const AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (!Character)
	{
		return FGTInteractionOffer::Unavailable(TEXT(""));
	}
	if (Character->IsCarryingHook())
	{
		return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("%s: hands full with the hook"), *DisplayName));
	}
	const bool bOpen = Character->GetStation() == this;
	return FGTInteractionOffer::Available(FString::Printf(TEXT("%s %s"), bOpen ? TEXT("Close") : TEXT("Use"), *DisplayName), 0.2f);
}

void AGTCraftingStation::Interact(const FGTInteractionQuery& Query)
{
	AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (!Character)
	{
		return;
	}
	if (Character->GetStation() == this)
	{
		Character->CloseStation();
	}
	else
	{
		Character->OpenStation(this);
	}
}

bool AGTCraftingStation::ActOnRow(AGTPlayerCharacter* User, int32 RowIndex)
{
	TArray<FGTScreenRow> Rows;
	BuildRows(User, Rows);
	if (!Rows.IsValidIndex(RowIndex) || !Rows[RowIndex].bEnabled || Rows[RowIndex].bHeader)
	{
		return false;
	}
	const bool bDone = Act(User, Rows[RowIndex]);
	if (bDone)
	{
		++ActsCompleted;
	}
	return bDone;
}

// ---- workbench ---------------------------------------------------------------------------------------

AGTWorkbench::AGTWorkbench()
{
	StationTag = GTTags::Station_Workbench;
	DisplayName = TEXT("workbench");
	GreyboxSize = FVector(160.f, 70.f, 90.f);
	Colour = FLinearColor(0.45f, 0.35f, 0.25f);
}

// ---- room checks -----------------------------------------------------------------------------------------

namespace
{
	/** Adds the weight RemoveBoth would take out of each side for Count units (the bag first). */
	void AddFreedWeight(const UGTInventoryComponent* BagInventory, const UGTInventoryComponent* BootInventory, FName ItemId, int32 Count, float& BagKg, float& BootKg)
	{
		const float Each = GTItems::WeightKg(ItemId);
		const int32 FromBag = BagInventory ? FMath::Min(Count, BagInventory->CountOf(ItemId)) : 0;
		const int32 FromBoot = BootInventory ? FMath::Min(Count - FromBag, BootInventory->CountOf(ItemId)) : 0;
		BagKg += FromBag * Each;
		BootKg += FromBoot * Each;
	}

	/** Whole units of ItemId that fit in FreeKg, rounded like UGTInventoryComponent::Add. */
	int64 UnitsThatFit(float FreeKg, FName ItemId)
	{
		const float Each = GTItems::WeightKg(ItemId);
		return Each > 0.f ? FMath::FloorToInt(FreeKg / Each + KINDA_SMALL_NUMBER) : MAX_int32;
	}

	/** True when Count units of ItemId fit across the bag and the boot once BagFreedKg and BootFreedKg have left them. */
	bool FitsAcross(const UGTInventoryComponent* BagInventory, const UGTInventoryComponent* BootInventory, FName ItemId, int32 Count, float BagFreedKg = 0.f, float BootFreedKg = 0.f)
	{
		int64 Units = 0;
		if (BagInventory)
		{
			Units += UnitsThatFit(BagInventory->GetFreeWeightKg() + BagFreedKg, ItemId);
		}
		if (BootInventory)
		{
			Units += UnitsThatFit(BootInventory->GetFreeWeightKg() + BootFreedKg, ItemId);
		}
		return Units >= Count;
	}

	/** Anything the lift's repair would change: a part below full health or a panel off. The price is a separate question (free at Mechanic II). */
	bool CarNeedsRepair(const AGTCarPawn* Car)
	{
		const UGTConditionComponent* Condition = Car ? Car->GetCondition() : nullptr;
		if (!Condition)
		{
			return false;
		}
		for (uint8 Index = 0; Index < static_cast<uint8>(EGTCarPart::Count); ++Index)
		{
			if (Condition->GetPartHealth(static_cast<EGTCarPart>(Index)) < 0.999f)
			{
				return true;
			}
		}
		return Car->GetBody() && Car->GetBody()->GetDetachedCount() > 0;
	}
}

void AGTWorkbench::BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const
{
	const AGTCarPawn* Car = FindPlayerCar();
	const int32 Tier = Run() ? Run()->GetCrewTier(GTTags::Crew_Workbench) : 0;
	Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("Workbench (tier %d)   T: craft into the bag"), Tier)));
	if (!Registry())
	{
		return;
	}
	for (const UGTRecipeDefinition* Recipe : Registry()->GetRecipes())
	{
		if (!Recipe || Recipe->StationTag != StationTag)
		{
			continue;
		}
		FString Missing;
		float BagFreed = 0.f;
		float BootFreed = 0.f;
		for (const FGTItemStack& Input : Recipe->Inputs)
		{
			const int32 Have = CountBoth(User, Car, Input.ItemId);
			if (Have < Input.Count)
			{
				Missing += FString::Printf(TEXT("%s%d more %s"), Missing.IsEmpty() ? TEXT("") : TEXT(", "), Input.Count - Have, *GTItems::DisplayName(Input.ItemId).ToLower());
			}
			AddFreedWeight(Bag(User), Boot(Car), Input.ItemId, Input.Count, BagFreed, BootFreed);
		}
		const bool bTierOk = Recipe->RequiredTier <= Tier;
		const bool bRoom = FitsAcross(Bag(User), Boot(Car), Recipe->Output.ItemId, Recipe->Output.Count, BagFreed, BootFreed);
		FString Hint;
		if (!bTierOk)
		{
			Hint = FString::Printf(TEXT("needs workbench tier %d"), Recipe->RequiredTier);
		}
		else if (!Missing.IsEmpty())
		{
			Hint = TEXT("needs ") + Missing;
		}
		else if (!bRoom)
		{
			Hint = FString::Printf(TEXT("no room for it (%.0f kg): empty the bag or the boot"), GTItems::WeightKg(Recipe->Output.ItemId) * Recipe->Output.Count);
		}
		else
		{
			Hint = FString::Printf(TEXT("%.0f s"), Recipe->CraftSeconds);
		}
		FGTScreenRow Row = FGTScreenRow::Line(FString::Printf(TEXT("%s   (%s)"), *Recipe->DisplayName.ToString(), *Recipe->DescribeInputs()), 1, bTierOk && Missing.IsEmpty() && bRoom, Hint);
		Row.Payload = Recipe->RecipeId;
		Rows.Add(Row);
	}
}

bool AGTWorkbench::Act(AGTPlayerCharacter* User, const FGTScreenRow& Row)
{
	AGTCarPawn* Car = FindPlayerCar();
	const UGTRecipeDefinition* Recipe = Registry() ? Registry()->FindRecipe(Row.Payload) : nullptr;
	if (!Recipe || !User)
	{
		return false;
	}
	float BagFreed = 0.f;
	float BootFreed = 0.f;
	for (const FGTItemStack& Input : Recipe->Inputs)
	{
		if (CountBoth(User, Car, Input.ItemId) < Input.Count)
		{
			LastMessage = TEXT("missing inputs");
			return false;
		}
		AddFreedWeight(Bag(User), Boot(Car), Input.ItemId, Input.Count, BagFreed, BootFreed);
	}
	// Nothing is used up unless the result has somewhere to go.
	if (!FitsAcross(Bag(User), Boot(Car), Recipe->Output.ItemId, Recipe->Output.Count, BagFreed, BootFreed))
	{
		LastMessage = FString::Printf(TEXT("no room for %s in the bag or the boot"), *Recipe->DisplayName.ToString());
		return false;
	}
	for (const FGTItemStack& Input : Recipe->Inputs)
	{
		RemoveBoth(User, Car, Input.ItemId, Input.Count);
	}
	const int32 Given = GiveBoth(User, Car, Recipe->Output.ItemId, Recipe->Output.Count);
	++Crafted;
	LastMessage = FString::Printf(TEXT("crafted %s%s"), *Recipe->DisplayName.ToString(), Given < Recipe->Output.Count ? TEXT(" (no room: part of it lost)") : TEXT(""));
	UE_LOG(LogTemp, Display, TEXT("AGTWorkbench: %s"), *LastMessage);
	return true;
}

// ---- car lift ------------------------------------------------------------------------------------------

AGTCarLift::AGTCarLift()
{
	StationTag = GTTags::Station_CarLift;
	DisplayName = TEXT("car lift");
	GreyboxSize = FVector(500.f, 260.f, 20.f);
	Colour = FLinearColor(0.25f, 0.28f, 0.32f);
}

int32 AGTCarLift::RepairCost(const AGTCarPawn* Car) const
{
	const UGTConditionComponent* Condition = Car ? Car->GetCondition() : nullptr;
	if (!Condition)
	{
		return 0;
	}
	float Missing = 0.f;
	for (uint8 Index = 0; Index < static_cast<uint8>(EGTCarPart::Count); ++Index)
	{
		Missing += 1.f - Condition->GetPartHealth(static_cast<EGTCarPart>(Index));
	}
	if (Car->GetBody() && Car->GetBody()->GetDetachedCount() > 0)
	{
		Missing += 0.5f * Car->GetBody()->GetDetachedCount();
	}
	const float Factor = UGTUpgradeDefinition::RepairPriceFactor(Run() ? Run()->GetCrewTier(GTTags::Crew_Mechanic) : 0);
	return FMath::CeilToInt(Missing * RepairScrapPerHealth * Factor - KINDA_SMALL_NUMBER);
}

void AGTCarLift::BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const
{
	AGTCarPawn* Car = FindPlayerCar();
	if (!Car || FVector::Dist2D(Car->GetActorLocation(), GetActorLocation()) > LiftRadius)
	{
		Rows.Add(FGTScreenRow::Header(TEXT("Car lift: park the car on the lift")));
		return;
	}
	const UGTPartSlotsComponent* Parts = Car->GetParts();
	const UGTConditionComponent* Condition = Car->GetCondition();
	Rows.Add(FGTScreenRow::Header(TEXT("Installed   T: remove to the boot")));
	for (const FGameplayTag& Slot : Parts->Slots)
	{
		const UGTPartDefinition* Part = Parts->GetInstalledPart(Slot);
		FString Health;
		if (Part && Condition && Part->OwnedParts.Num() > 0)
		{
			float Min = 1.f;
			for (const EGTCarPart Owned : Part->OwnedParts)
			{
				Min = FMath::Min(Min, Condition->GetPartHealth(Owned));
			}
			Health = FString::Printf(TEXT("  %.0f%%"), Min * 100.f);
		}
		// Required slots only swap; anything else comes off only when the boot or the bag can take it.
		const bool bRequired = Parts->IsRequiredSlot(Slot);
		const bool bRoom = Part && FitsAcross(Bag(User), Boot(Car), Part->ItemId, 1);
		FString Hint = TEXT("empty");
		if (Part)
		{
			Hint = bRequired ? FString(TEXT("the car needs one: install a replacement to swap it"))
				: !bRoom ? FString::Printf(TEXT("no room for it (%.0f kg) in the boot or the bag"), Part->WeightKg)
				: FString(TEXT("remove to the boot"));
		}
		FGTScreenRow Row = FGTScreenRow::Line(FString::Printf(TEXT("%-11s %s%s"), *UGTPartSlotsComponent::SlotName(Slot), Part ? *Part->DisplayName.ToString() : TEXT("-"), *Health), Remove,
			Part != nullptr && !bRequired && bRoom, Hint);
		Row.Tag = Slot;
		Row.Payload = Part ? Part->ItemId : NAME_None;
		Rows.Add(Row);
	}
	Rows.Add(FGTScreenRow::Header(TEXT("Parts in the bag and boot   T: install (the old part goes to the boot)")));
	TSet<FName> Seen;
	for (const UGTInventoryComponent* Inventory : { Bag(User), Boot(Car) })
	{
		if (!Inventory)
		{
			continue;
		}
		for (const FGTItemStack& Stack : Inventory->Items)
		{
			const UGTPartDefinition* Part = Registry() ? Registry()->FindPart(Stack.ItemId) : nullptr;
			if (!Part || Seen.Contains(Stack.ItemId))
			{
				continue;
			}
			Seen.Add(Stack.ItemId);
			const FGTFitResult Fit = Parts->CanInstall(Stack.ItemId);
			// The part coming off needs somewhere to go once the new one has left the bag or the boot.
			bool bRoom = true;
			if (Fit.bFits && !Fit.Replaces.IsNone())
			{
				float BagFreed = 0.f;
				float BootFreed = 0.f;
				AddFreedWeight(Bag(User), Boot(Car), Stack.ItemId, 1, BagFreed, BootFreed);
				bRoom = FitsAcross(Bag(User), Boot(Car), Fit.Replaces, 1, BagFreed, BootFreed);
			}
			FString Hint = Fit.Hint;
			if (Fit.bFits)
			{
				Hint = !bRoom ? FString::Printf(TEXT("no room for the old %s (%.0f kg)"), *GTItems::DisplayName(Fit.Replaces), GTItems::WeightKg(Fit.Replaces))
					: Fit.Replaces.IsNone() ? FString(TEXT("fits")) : FString::Printf(TEXT("replaces %s"), *GTItems::DisplayName(Fit.Replaces));
			}
			FGTScreenRow Row = FGTScreenRow::Line(FString::Printf(TEXT("Install %s  ->  %s"), *Part->DisplayName.ToString(), *UGTPartSlotsComponent::SlotName(Part->Slot)), Install, Fit.bFits && bRoom, Hint);
			Row.Payload = Stack.ItemId;
			Rows.Add(Row);
		}
	}
	Rows.Add(FGTScreenRow::Header(TEXT("Service")));
	// Offered whenever something is damaged; the price is separate (free at Mechanic II).
	const int32 Cost = RepairCost(Car);
	const bool bDamaged = CarNeedsRepair(Car);
	const int32 Scrap = CountBoth(User, Car, GTItems::Scrap);
	const FString RepairLabel = Cost > 0 ? FString::Printf(TEXT("Repair everything (%d scrap)"), Cost) : FString(bDamaged ? TEXT("Repair everything (free)") : TEXT("Repair everything"));
	Rows.Add(FGTScreenRow::Line(RepairLabel, Repair, bDamaged && Scrap >= Cost,
		!bDamaged ? FString(TEXT("nothing to repair")) : Scrap >= Cost ? FString(TEXT("parts to full health, panels back on, dents out")) : FString::Printf(TEXT("needs %d more scrap"), Cost - Scrap)));
	Rows.Add(FGTScreenRow::Line(TEXT("Wash"), Wash, true, TEXT("dirt, wetness and snow off the body")));
}

bool AGTCarLift::Act(AGTPlayerCharacter* User, const FGTScreenRow& Row)
{
	AGTCarPawn* Car = FindPlayerCar();
	if (!Car || !User)
	{
		return false;
	}
	UGTPartSlotsComponent* Parts = Car->GetParts();
	switch (Row.Action)
	{
	case Remove:
	{
		const FName Current = Parts->GetInstalled(Row.Tag);
		if (Current.IsNone())
		{
			return false;
		}
		if (Parts->IsRequiredSlot(Row.Tag))
		{
			LastMessage = FString::Printf(TEXT("the car needs its %s: install a replacement to swap it"), *UGTPartSlotsComponent::SlotName(Row.Tag).ToLower());
			return false;
		}
		if (!FitsAcross(Bag(User), Boot(Car), Current, 1))
		{
			LastMessage = FString::Printf(TEXT("no room for %s in the boot or the bag"), *GTItems::DisplayName(Current));
			return false;
		}
		FName Removed;
		if (Parts->Remove(Row.Tag, Removed))
		{
			GiveBootFirst(User, Car, Removed, 1);   // the room was checked above
			LastMessage = FString::Printf(TEXT("removed %s"), *GTItems::DisplayName(Removed));
			return true;
		}
		return false;
	}
	case Install:
	{
		if (CountBoth(User, Car, Row.Payload) < 1)
		{
			return false;
		}
		const FGTFitResult Fit = Parts->CanInstall(Row.Payload);
		if (!Fit.bFits)
		{
			LastMessage = Fit.Hint;
			return false;
		}
		if (!Fit.Replaces.IsNone())
		{
			// Nothing comes off the car unless it has somewhere to go once the new part has left the bag or the boot.
			float BagFreed = 0.f;
			float BootFreed = 0.f;
			AddFreedWeight(Bag(User), Boot(Car), Row.Payload, 1, BagFreed, BootFreed);
			if (!FitsAcross(Bag(User), Boot(Car), Fit.Replaces, 1, BagFreed, BootFreed))
			{
				LastMessage = FString::Printf(TEXT("no room for the old %s in the boot or the bag"), *GTItems::DisplayName(Fit.Replaces));
				return false;
			}
		}
		FName Replaced;
		if (!Parts->Install(Row.Payload, Replaced))
		{
			LastMessage = Parts->CanInstall(Row.Payload).Hint;
			return false;
		}
		RemoveBoth(User, Car, Row.Payload, 1);
		if (!Replaced.IsNone() && GiveBootFirst(User, Car, Replaced, 1) < 1)
		{
			UE_LOG(LogTemp, Warning, TEXT("AGTCarLift: no room for %s, it is lost"), *Replaced.ToString());
		}
		LastMessage = FString::Printf(TEXT("installed %s"), *GTItems::DisplayName(Row.Payload));
		return true;
	}
	case Repair:
	{
		const int32 Cost = RepairCost(Car);
		if (CountBoth(User, Car, GTItems::Scrap) < Cost)
		{
			return false;
		}
		RemoveBoth(User, Car, GTItems::Scrap, Cost);
		Car->GetCondition()->RepairAll();
		if (Car->GetBody())
		{
			Car->GetBody()->ReattachAll();
		}
		++Repairs;
		LastMessage = FString::Printf(TEXT("repaired for %d scrap"), Cost);
		UE_LOG(LogTemp, Display, TEXT("AGTCarLift: %s"), *LastMessage);
		return true;
	}
	case Wash:
		if (Car->GetBodyState())
		{
			Car->GetBodyState()->Wash();
		}
		++Washes;
		LastMessage = TEXT("washed");
		return true;
	default:
		return false;
	}
}

// ---- trader ------------------------------------------------------------------------------------------

AGTTrader::AGTTrader()
{
	StationTag = GTTags::Station_Trader;
	DisplayName = TEXT("trader");
	GreyboxSize = FVector(200.f, 80.f, 100.f);
	Colour = FLinearColor(0.5f, 0.42f, 0.15f);
}

int32 AGTTrader::SellPrice(FName ItemId) const
{
	const float Fraction = UGTUpgradeDefinition::SellFraction(Run() ? Run()->GetCrewTier(GTTags::Crew_Trader) : 0);
	return FMath::Max(1, FMath::FloorToInt(GTItems::BasePrice(ItemId) * Fraction));
}

void AGTTrader::BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const
{
	const AGTCarPawn* Car = FindPlayerCar();
	const int32 Currency = Run() ? Run()->GetCurrency() : 0;
	const float Fraction = UGTUpgradeDefinition::SellFraction(Run() ? Run()->GetCrewTier(GTTags::Crew_Trader) : 0);
	Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("Sell (pays %.0f%% of base)   credits %d"), Fraction * 100.f, Currency)));
	TSet<FName> Seen;
	for (const UGTInventoryComponent* Inventory : { Bag(User), Boot(Car) })
	{
		if (!Inventory)
		{
			continue;
		}
		for (const FGTItemStack& Stack : Inventory->Items)
		{
			if (Stack.Count <= 0 || Seen.Contains(Stack.ItemId))
			{
				continue;
			}
			Seen.Add(Stack.ItemId);
			FGTScreenRow Row = FGTScreenRow::Line(FString::Printf(TEXT("Sell %s x1  (+%d)   have %d"), *GTItems::DisplayName(Stack.ItemId), SellPrice(Stack.ItemId), CountBoth(User, Car, Stack.ItemId)), Sell, true);
			Row.Payload = Stack.ItemId;
			Rows.Add(Row);
		}
	}
	Rows.Add(FGTScreenRow::Header(TEXT("Buy (into the bag, then the boot)")));
	if (!Registry())
	{
		return;
	}
	for (const UGTItemDefinition* Item : Registry()->GetTraderStock())
	{
		const bool bAfford = Currency >= Item->BasePrice;
		FGTScreenRow Row = FGTScreenRow::Line(FString::Printf(TEXT("Buy %s  (-%d)"), *Item->DisplayName.ToString(), Item->BasePrice), Buy, bAfford, bAfford ? TEXT("") : TEXT("not enough credits"));
		Row.Payload = Item->ItemId;
		Rows.Add(Row);
	}
}

bool AGTTrader::Act(AGTPlayerCharacter* User, const FGTScreenRow& Row)
{
	AGTCarPawn* Car = FindPlayerCar();
	if (!Run() || !User)
	{
		return false;
	}
	switch (Row.Action)
	{
	case Sell:
		if (RemoveBoth(User, Car, Row.Payload, 1) == 1)
		{
			Run()->AddCurrency(SellPrice(Row.Payload));
			++Sold;
			LastMessage = FString::Printf(TEXT("sold %s"), *GTItems::DisplayName(Row.Payload));
			return true;
		}
		return false;
	case Buy:
	{
		const int32 Price = GTItems::BasePrice(Row.Payload);
		if (!Run()->SpendCurrency(Price))
		{
			LastMessage = TEXT("not enough credits");
			return false;
		}
		if (GiveBoth(User, Car, Row.Payload, 1) < 1)
		{
			Run()->AddCurrency(Price);   // no room: the sale is off
			LastMessage = TEXT("no room in the bag or the boot");
			return false;
		}
		++Bought;
		LastMessage = FString::Printf(TEXT("bought %s"), *GTItems::DisplayName(Row.Payload));
		return true;
	}
	default:
		return false;
	}
}

// ---- crew ----------------------------------------------------------------------------------------------

AGTCrewTent::AGTCrewTent()
{
	StationTag = GTTags::Station_Crew;
	DisplayName = TEXT("crew tent");
	GreyboxSize = FVector(300.f, 300.f, 220.f);
	Colour = FLinearColor(0.35f, 0.45f, 0.3f);
}

void AGTCrewTent::BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const
{
	const int32 Currency = Run() ? Run()->GetCurrency() : 0;
	Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("Crew   credits %d   T: buy the next tier"), Currency)));
	if (!Registry() || !Run())
	{
		return;
	}
	for (const UGTUpgradeDefinition* Upgrade : Registry()->GetUpgrades())
	{
		const int32 Owned = Run()->GetCrewTier(Upgrade->Track);
		const bool bOwned = Owned >= Upgrade->Tier;
		const bool bNext = Owned == Upgrade->Tier - 1;
		const bool bAfford = Currency >= Upgrade->Cost;
		FGTScreenRow Row = FGTScreenRow::Line(FString::Printf(TEXT("%-14s %-5s %s"), *Upgrade->DisplayName.ToString(), bOwned ? TEXT("owned") : *FString::Printf(TEXT("%d"), Upgrade->Cost), *Upgrade->Effect.ToString()),
			1, !bOwned && bNext && bAfford, bOwned ? TEXT("") : !bNext ? TEXT("buy the earlier tier first") : bAfford ? TEXT("") : TEXT("not enough credits"));
		Row.Payload = Upgrade->UpgradeId;
		Rows.Add(Row);
	}
}

bool AGTCrewTent::Act(AGTPlayerCharacter* User, const FGTScreenRow& Row)
{
	if (!Registry() || !Run())
	{
		return false;
	}
	for (const UGTUpgradeDefinition* Upgrade : Registry()->GetUpgrades())
	{
		if (Upgrade->UpgradeId != Row.Payload)
		{
			continue;
		}
		if (Run()->GetCrewTier(Upgrade->Track) != Upgrade->Tier - 1 || !Run()->SpendCurrency(Upgrade->Cost))
		{
			return false;
		}
		Run()->SetCrewTier(Upgrade->Track, Upgrade->Tier);
		++UpgradesBought;
		LastMessage = FString::Printf(TEXT("bought %s"), *Upgrade->DisplayName.ToString());
		UE_LOG(LogTemp, Display, TEXT("AGTCrewTent: %s"), *LastMessage);
		return true;
	}
	return false;
}

// ---- briefing --------------------------------------------------------------------------------------

AGTBriefingBoard::AGTBriefingBoard()
{
	StationTag = GTTags::Station_Briefing;
	DisplayName = TEXT("briefing board");
	GreyboxSize = FVector(10.f, 160.f, 110.f);
	Colour = FLinearColor(0.85f, 0.8f, 0.6f);
}

namespace
{
	/** Splits a sentence into rows of at most Width characters at spaces. */
	void WrapRows(const FString& Text, int32 Width, const FString& Indent, TArray<FGTScreenRow>& Rows)
	{
		TArray<FString> Words;
		Text.ParseIntoArray(Words, TEXT(" "), true);
		FString Line;
		for (const FString& Word : Words)
		{
			if (!Line.IsEmpty() && Line.Len() + 1 + Word.Len() > Width)
			{
				Rows.Add(FGTScreenRow::Header(Indent + Line));
				Line.Reset();
			}
			Line += (Line.IsEmpty() ? TEXT("") : TEXT(" ")) + Word;
		}
		if (!Line.IsEmpty())
		{
			Rows.Add(FGTScreenRow::Header(Indent + Line));
		}
	}

	FString ClockRow(float Seconds)
	{
		const int32 Whole = FMath::Max(0, FMath::RoundToInt(Seconds));
		return FString::Printf(TEXT("%d:%02d"), Whole / 60, Whole % 60);
	}
}

void AGTBriefingBoard::BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const
{
	UGTRunSubsystem* RunSub = Run();
	UGTTourDefinition* Tour = RunSub ? RunSub->ResolveTour() : nullptr;
	const UGTLegDefinition* Leg = RunSub ? RunSub->ResolveNextLeg() : nullptr;
	if (!RunSub || !Tour)
	{
		Rows.Add(FGTScreenRow::Header(TEXT("Briefing: no tour")));
		return;
	}
	const TArray<FGTStandingRow> Standings = RunSub->BuildStandings();
	if (!Leg)
	{
		// The tour is over: the final table, the ending, and the way to go again.
		const FGTStandingRow Me = GTStandings::PlayerRow(Standings);
		Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("%s is over: you finished %d of %d with %d points"), *Tour->DisplayName.ToString(), Me.Place, Standings.Num(), Me.Points)));
		WrapRows(RunSub->EndingLine(), 78, TEXT("  "), Rows);
		Rows.Add(FGTScreenRow::Header(TEXT("Final standings:")));
		for (const FGTStandingRow& Row : Standings)
		{
			Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("  %d. %-16s %3d pts   %d/%d legs   %s"), Row.Place, *Row.Name, Row.Points, Row.LegsFinished, Row.LegsRun, *ClockRow(Row.TotalTimeSeconds))));
		}
		Rows.Add(FGTScreenRow::Line(TEXT("Start a new tour"), NewTour, true, TEXT("the same legs from leg 1, the tour's starting credits, a fresh table; the car keeps what is on it")));
		return;
	}
	const int32 Scout = RunSub->GetCrewTier(GTTags::Crew_Scout);
	Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("%s, leg %d of %d: %s   [%s]"), *Tour->DisplayName.ToString(), RunSub->GetCampaign().CurrentLegIndex + 1, Tour->LegCount(), *Leg->DisplayName.ToString(), *UGTLegDefinition::MissionName(Leg->Mission))));
	WrapRows(Leg->MissionBrief.ToString(), 78, TEXT("  "), Rows);
	Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("  %s"), *Leg->MissionObjective(0))));
	Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("Par %s%s"), *ClockRow(Leg->ParTimeSeconds),
		Leg->TimeLimitSeconds > 0.f ? *FString::Printf(TEXT("   limit %s%s"), *ClockRow(Leg->TimeLimitSeconds), Leg->Mission == EGTMissionType::Endurance ? TEXT(" (past it: no result)") : TEXT("")) : TEXT(""))));
	Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("Weather at the start: %s"), Leg->StartWeather ? *Leg->StartWeather->DisplayName.ToString() : *Leg->StartWeatherName.ToString())));
	Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("Conditions (scout tier %d):"), Scout)));
	for (const FGTConditionCurve& Condition : Leg->Conditions)
	{
		FString Name = Condition.Tag.ToString();
		Name.RemoveFromStart(TEXT("Env."));
		if (Scout <= 0)
		{
			Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("  %s"), *Name)));
		}
		else if (Scout == 1)
		{
			float Peak = 0.f;
			for (int32 Step = 0; Step <= 20; ++Step)
			{
				Peak = FMath::Max(Peak, Condition.Sample(Step / 20.f));
			}
			Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("  %-6s peak %.0f%%"), *Name, Peak * 100.f)));
		}
		else
		{
			FString Curve;
			for (int32 Step = 0; Step <= 10; ++Step)
			{
				const float V = Condition.Sample(Step / 10.f);
				Curve += V < 0.1f ? TEXT(".") : V < 0.35f ? TEXT("-") : V < 0.65f ? TEXT("=") : TEXT("#");
			}
			Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("  %-6s start>%s>end   %.0f / %.0f / %.0f%%"), *Name, *Curve, Condition.Sample(0.f) * 100.f, Condition.Sample(0.5f) * 100.f, Condition.Sample(1.f) * 100.f)));
		}
	}
	Rows.Add(FGTScreenRow::Header(TEXT("The rivals (their usual pace on this leg, and the table so far):")));
	for (const FGTRivalDefinition& Rival : Tour->Rivals)
	{
		const FGTStandingRow* Row = Standings.FindByPredicate([&Rival](const FGTStandingRow& R) { return !R.bPlayer && R.Name == Rival.Name; });
		Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("  %-16s %-26s about %s   %d pts%s"), *Rival.Name, *Rival.Car, *ClockRow(GTStandings::ExpectedTime(Rival, *Leg)), Row ? Row->Points : 0,
			Row && Row->Place == 1 && Row->Points > 0 ? TEXT("  (leading)") : TEXT(""))));
	}
	const FGTStandingRow Me = GTStandings::PlayerRow(Standings);
	if (Me.LegsRun > 0)
	{
		Rows.Add(FGTScreenRow::Header(FString::Printf(TEXT("  You: %d of %d in the table with %d points after %d legs"), Me.Place, Standings.Num(), Me.Points, Me.LegsRun)));
	}
	Rows.Add(FGTScreenRow::Header(TEXT("Depart: get in the car and drive out through the gate")));
}

bool AGTBriefingBoard::Act(AGTPlayerCharacter* User, const FGTScreenRow& Row)
{
	UGTRunSubsystem* RunSub = Run();
	if (Row.Action != NewTour || !RunSub || !RunSub->IsTourComplete())
	{
		return false;
	}
	RunSub->ResetCampaign();
	RunSub->SaveToSlot();
	++ToursStarted;
	LastMessage = TEXT("a new tour: leg 1 is next");
	UE_LOG(LogTemp, Display, TEXT("AGTBriefingBoard: %s (%s)"), *LastMessage, *RunSub->Describe());
	return true;
}
