#include "Inventory/GTInventoryComponent.h"

#include "Parts/GTItemDefinition.h"
#include "Parts/GTItemRegistry.h"

namespace GTItems
{
	struct FItemInfo
	{
		FName Id;
		float WeightKg;
		const TCHAR* Name;
		int32 Price;
	};

	static const FItemInfo Table[] = {
		{Scrap, 2.0f, TEXT("Scrap metal"), 5},
		{Wire, 0.5f, TEXT("Wire"), 4},
		{Bolts, 0.2f, TEXT("Bolts"), 2},
		{FuelCan, 10.f, TEXT("Fuel can"), 30},
		{PartRadiator, 8.f, TEXT("Radiator"), 80},
		{PartTyre, 12.f, TEXT("Tyre"), 60},
		{RareAlloy, 4.f, TEXT("Rare alloy"), 150},
	};

	static const FItemInfo* Find(FName ItemId)
	{
		for (const FItemInfo& Info : Table)
		{
			if (Info.Id == ItemId)
			{
				return &Info;
			}
		}
		return nullptr;
	}

	static const UGTItemDefinition* Definition(FName ItemId)
	{
		const UGTItemRegistry* Registry = UGTItemRegistry::Current();
		return Registry ? Registry->Find(ItemId) : nullptr;
	}

	float WeightKg(FName ItemId)
	{
		if (const UGTItemDefinition* Item = Definition(ItemId))
		{
			return Item->WeightKg;
		}
		const FItemInfo* Info = Find(ItemId);
		return Info ? Info->WeightKg : 1.f;
	}

	FString DisplayName(FName ItemId)
	{
		if (const UGTItemDefinition* Item = Definition(ItemId))
		{
			return Item->DisplayName.ToString();
		}
		const FItemInfo* Info = Find(ItemId);
		return Info ? FString(Info->Name) : ItemId.ToString();
	}

	int32 BasePrice(FName ItemId)
	{
		if (const UGTItemDefinition* Item = Definition(ItemId))
		{
			return Item->BasePrice;
		}
		const FItemInfo* Info = Find(ItemId);
		return Info ? Info->Price : 1;
	}
}

UGTInventoryComponent::UGTInventoryComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

int32 UGTInventoryComponent::Add(FName ItemId, int32 Count)
{
	if (ItemId.IsNone() || Count <= 0)
	{
		return 0;
	}
	const float Each = GTItems::WeightKg(ItemId);
	const int32 Fits = Each > 0.f ? FMath::FloorToInt(GetFreeWeightKg() / Each + KINDA_SMALL_NUMBER) : Count;
	const int32 Accepted = FMath::Clamp(Fits, 0, Count);
	if (Accepted <= 0)
	{
		return 0;
	}
	for (FGTItemStack& Stack : Items)
	{
		if (Stack.ItemId == ItemId)
		{
			Stack.Count += Accepted;
			++Version;
			return Accepted;
		}
	}
	FGTItemStack Stack;
	Stack.ItemId = ItemId;
	Stack.Count = Accepted;
	Items.Add(Stack);
	++Version;
	return Accepted;
}

int32 UGTInventoryComponent::Remove(FName ItemId, int32 Count)
{
	for (int32 Index = 0; Index < Items.Num(); ++Index)
	{
		if (Items[Index].ItemId == ItemId)
		{
			const int32 Removed = FMath::Clamp(Count, 0, Items[Index].Count);
			Items[Index].Count -= Removed;
			if (Items[Index].Count <= 0)
			{
				Items.RemoveAt(Index);
			}
			if (Removed > 0)
			{
				++Version;
			}
			return Removed;
		}
	}
	return 0;
}

int32 UGTInventoryComponent::CountOf(FName ItemId) const
{
	for (const FGTItemStack& Stack : Items)
	{
		if (Stack.ItemId == ItemId)
		{
			return Stack.Count;
		}
	}
	return 0;
}

float UGTInventoryComponent::GetTotalWeightKg() const
{
	float Total = 0.f;
	for (const FGTItemStack& Stack : Items)
	{
		Total += GTItems::WeightKg(Stack.ItemId) * Stack.Count;
	}
	return Total;
}

int32 UGTInventoryComponent::TransferTo(UGTInventoryComponent* To, FName ItemId, int32 Count)
{
	if (!To || To == this)
	{
		return 0;
	}
	const int32 Available = FMath::Min(Count, CountOf(ItemId));
	if (Available <= 0)
	{
		return 0;
	}
	const int32 Moved = To->Add(ItemId, Available);
	Remove(ItemId, Moved);
	return Moved;
}

FString UGTInventoryComponent::Describe() const
{
	FString Result = FString::Printf(TEXT("%.1f/%.0f kg:"), GetTotalWeightKg(), MaxWeightKg);
	for (const FGTItemStack& Stack : Items)
	{
		Result += FString::Printf(TEXT(" %s x%d"), *Stack.ItemId.ToString(), Stack.Count);
	}
	return Result;
}
