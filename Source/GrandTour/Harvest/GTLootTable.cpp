#include "Harvest/GTLootTable.h"

FGTLootEntry UGTLootTable::Entry(FName ItemId, int32 Min, int32 Max, float Weight)
{
	FGTLootEntry E;
	E.ItemId = ItemId;
	E.MinCount = Min;
	E.MaxCount = Max;
	E.Weight = Weight;
	return E;
}

FGTItemStack UGTLootTable::Stack(FName ItemId, int32 Count)
{
	FGTItemStack S;
	S.ItemId = ItemId;
	S.Count = Count;
	return S;
}

namespace
{
	void Merge(TArray<FGTItemStack>& Out, FName ItemId, int32 Count)
	{
		if (ItemId.IsNone() || Count <= 0)
		{
			return;
		}
		for (FGTItemStack& Existing : Out)
		{
			if (Existing.ItemId == ItemId)
			{
				Existing.Count += Count;
				return;
			}
		}
		Out.Add(UGTLootTable::Stack(ItemId, Count));
	}

	const UGTLootTable::FDefault* BuildDefaults()
	{
		static TArray<UGTLootTable::FDefault> Rows;
		if (Rows.Num() == 0)
		{
			Rows.Add({TEXT("DA_Loot_CableBundle"), TEXT("CableBundle"), 1, 1,
				{UGTLootTable::Entry(GTItems::Wire, 2, 4, 3.f), UGTLootTable::Entry(GTItems::Bolts, 1, 3, 1.f)},
				{}});
			Rows.Add({TEXT("DA_Loot_Wreck"), TEXT("Wreck"), 1, 2,
				{UGTLootTable::Entry(GTItems::Scrap, 2, 4, 6.f), UGTLootTable::Entry(GTItems::PartRadiator, 1, 1, 1.5f),
				 UGTLootTable::Entry(GTItems::PartTyre, 1, 1, 1.f), UGTLootTable::Entry(GTItems::FuelCan, 1, 1, 0.75f)},
				{UGTLootTable::Stack(GTItems::Scrap, 1)}});
			Rows.Add({TEXT("DA_Loot_RadiationCache"), TEXT("RadiationCache"), 1, 1,
				{UGTLootTable::Entry(GTItems::RareAlloy, 1, 2, 4.f), UGTLootTable::Entry(GTItems::Scrap, 1, 2, 1.f)},
				{UGTLootTable::Stack(GTItems::RareAlloy, 1)}});
		}
		return Rows.GetData();
	}
	constexpr int32 DefaultCount = 3;
}

TArrayView<const UGTLootTable::FDefault> UGTLootTable::DefaultTables()
{
	return MakeArrayView(BuildDefaults(), DefaultCount);
}

const UGTLootTable::FDefault* UGTLootTable::FindDefault(FName Id)
{
	for (const FDefault& Row : DefaultTables())
	{
		if (Id == FName(Row.Id))
		{
			return &Row;
		}
	}
	return nullptr;
}

void UGTLootTable::ApplyDefault(const FDefault& Row)
{
	TableId = Row.Id;
	PicksMin = Row.PicksMin;
	PicksMax = Row.PicksMax;
	Entries = Row.Entries;
	Guaranteed = Row.Guaranteed;
}

void UGTLootTable::Roll(FRandomStream& Random, TArray<FGTItemStack>& Out) const
{
	for (const FGTItemStack& Sure : Guaranteed)
	{
		Merge(Out, Sure.ItemId, Sure.Count);
	}
	float TotalWeight = 0.f;
	for (const FGTLootEntry& E : Entries)
	{
		TotalWeight += FMath::Max(0.f, E.Weight);
	}
	if (TotalWeight <= 0.f || Entries.Num() == 0)
	{
		return;
	}
	const int32 Picks = Random.RandRange(FMath::Min(PicksMin, PicksMax), FMath::Max(PicksMin, PicksMax));
	for (int32 Pick = 0; Pick < Picks; ++Pick)
	{
		float Roll = Random.FRand() * TotalWeight;
		const FGTLootEntry* Chosen = &Entries.Last();
		for (const FGTLootEntry& E : Entries)
		{
			Roll -= FMath::Max(0.f, E.Weight);
			if (Roll <= 0.f)
			{
				Chosen = &E;
				break;
			}
		}
		Merge(Out, Chosen->ItemId, Random.RandRange(FMath::Min(Chosen->MinCount, Chosen->MaxCount), FMath::Max(Chosen->MinCount, Chosen->MaxCount)));
	}
}

FString UGTLootTable::Describe() const
{
	FString Rows;
	for (const FGTLootEntry& E : Entries)
	{
		Rows += FString::Printf(TEXT(" %s %d-%d w%.1f"), *E.ItemId.ToString(), E.MinCount, E.MaxCount, E.Weight);
	}
	return FString::Printf(TEXT("%s picks=%d-%d guaranteed=%d entries=[%s]"), *TableId.ToString(), PicksMin, PicksMax, Guaranteed.Num(), *Rows.TrimStart());
}
