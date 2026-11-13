#include "Crafting/GTRecipeDefinition.h"

#include "GameplayTagsManager.h"

namespace
{
	FGTItemStack Stack(const TCHAR* Id, int32 Count)
	{
		FGTItemStack S;
		S.ItemId = Id;
		S.Count = Count;
		return S;
	}

	const TArray<UGTRecipeDefinition::FDefault>& Rows()
	{
		static TArray<UGTRecipeDefinition::FDefault> Table;
		if (Table.Num() == 0)
		{
			const TCHAR* Bench = TEXT("Station.Workbench");
			Table.Add({TEXT("DA_Recipe_Radiator"),      TEXT("Radiator"),      TEXT("Radiator"),       Bench, 0, {Stack(TEXT("Scrap"), 6), Stack(TEXT("Bolts"), 2)},                            Stack(TEXT("Part.Radiator"), 1),      4.f});
			Table.Add({TEXT("DA_Recipe_AirFilter"),     TEXT("AirFilter"),     TEXT("Air filter"),     Bench, 0, {Stack(TEXT("Scrap"), 3), Stack(TEXT("Wire"), 2)},                             Stack(TEXT("Part.AirFilter"), 1),     3.f});
			Table.Add({TEXT("DA_Recipe_Heater"),        TEXT("Heater"),        TEXT("Cabin heater"),   Bench, 0, {Stack(TEXT("Scrap"), 4), Stack(TEXT("Wire"), 3), Stack(TEXT("Bolts"), 2)},   Stack(TEXT("Part.Heater"), 1),        4.f});
			Table.Add({TEXT("DA_Recipe_CoolantFlush"),  TEXT("CoolantFlush"),  TEXT("Coolant flush"),  Bench, 0, {Stack(TEXT("Scrap"), 1), Stack(TEXT("Wire"), 1)},                             Stack(TEXT("Use.CoolantFlush"), 1),   2.f});
			Table.Add({TEXT("DA_Recipe_FilterCleaner"), TEXT("FilterCleaner"), TEXT("Filter cleaner"), Bench, 0, {Stack(TEXT("Wire"), 1)},                                                      Stack(TEXT("Use.FilterCleaner"), 1),  2.f});
			Table.Add({TEXT("DA_Recipe_RadiatorBig"),   TEXT("RadiatorBig"),   TEXT("Big radiator"),   Bench, 1, {Stack(TEXT("Scrap"), 10), Stack(TEXT("Bolts"), 4), Stack(TEXT("RareAlloy"), 1)}, Stack(TEXT("Part.RadiatorBig"), 1), 6.f});
			Table.Add({TEXT("DA_Recipe_LeadLining"),    TEXT("LeadLining"),    TEXT("Lead lining"),    Bench, 1, {Stack(TEXT("Scrap"), 8), Stack(TEXT("RareAlloy"), 2)},                        Stack(TEXT("Part.LeadLining"), 1),    6.f});
		}
		return Table;
	}
}

TArrayView<const UGTRecipeDefinition::FDefault> UGTRecipeDefinition::DefaultRecipes()
{
	return MakeArrayView(Rows());
}

void UGTRecipeDefinition::ApplyDefault(const FDefault& Row)
{
	RecipeId = Row.Id;
	DisplayName = FText::FromString(Row.Name);
	StationTag = UGameplayTagsManager::Get().RequestGameplayTag(FName(Row.Station), false);
	RequiredTier = Row.Tier;
	Inputs = Row.Inputs;
	Output = Row.Output;
	CraftSeconds = Row.Seconds;
}

FString UGTRecipeDefinition::DescribeInputs() const
{
	FString Result;
	for (const FGTItemStack& S : Inputs)
	{
		Result += FString::Printf(TEXT("%s%d %s"), Result.IsEmpty() ? TEXT("") : TEXT(", "), S.Count, *GTItems::DisplayName(S.ItemId).ToLower());
	}
	return Result;
}

FString UGTRecipeDefinition::Describe() const
{
	return FString::Printf(TEXT("%s: %s -> %d %s (tier %d, %.0f s)"), *RecipeId.ToString(), *DescribeInputs(), Output.Count, *Output.ItemId.ToString(), RequiredTier, CraftSeconds);
}
