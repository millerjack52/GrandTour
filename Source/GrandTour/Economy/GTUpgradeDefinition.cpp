#include "Economy/GTUpgradeDefinition.h"

#include "GameplayTagsManager.h"

namespace
{
	const UGTUpgradeDefinition::FDefault UpgradeRows[] = {
		{TEXT("DA_Upgrade_Mechanic1"),  TEXT("Mechanic1"),  TEXT("Mechanic I"),  TEXT("Crew.Mechanic"),  1, 200, TEXT("Lift repairs cost half")},
		{TEXT("DA_Upgrade_Mechanic2"),  TEXT("Mechanic2"),  TEXT("Mechanic II"), TEXT("Crew.Mechanic"),  2, 500, TEXT("Lift repairs are free")},
		{TEXT("DA_Upgrade_Trader1"),    TEXT("Trader1"),    TEXT("Trader I"),    TEXT("Crew.Trader"),    1, 200, TEXT("The trader pays 70% of base price")},
		{TEXT("DA_Upgrade_Trader2"),    TEXT("Trader2"),    TEXT("Trader II"),   TEXT("Crew.Trader"),    2, 500, TEXT("The trader pays 80% of base price")},
		{TEXT("DA_Upgrade_Scout1"),     TEXT("Scout1"),     TEXT("Scout I"),     TEXT("Crew.Scout"),     1, 200, TEXT("The briefing shows peak intensities")},
		{TEXT("DA_Upgrade_Scout2"),     TEXT("Scout2"),     TEXT("Scout II"),    TEXT("Crew.Scout"),     2, 500, TEXT("The briefing shows the intensity curves")},
		{TEXT("DA_Upgrade_Workbench1"), TEXT("Workbench1"), TEXT("Workbench I"), TEXT("Crew.Workbench"), 1, 300, TEXT("Tier-2 recipes at the workbench")},
	};
}

TArrayView<const UGTUpgradeDefinition::FDefault> UGTUpgradeDefinition::DefaultUpgrades()
{
	return MakeArrayView(UpgradeRows, UE_ARRAY_COUNT(UpgradeRows));
}

void UGTUpgradeDefinition::ApplyDefault(const FDefault& Row)
{
	UpgradeId = Row.Id;
	DisplayName = FText::FromString(Row.Name);
	Track = UGameplayTagsManager::Get().RequestGameplayTag(FName(Row.Track), false);
	Tier = Row.Tier;
	Cost = Row.Cost;
	Effect = FText::FromString(Row.Effect);
}

FString UGTUpgradeDefinition::Describe() const
{
	return FString::Printf(TEXT("%s %s tier %d cost %d: %s"), *UpgradeId.ToString(), *Track.ToString(), Tier, Cost, *Effect.ToString());
}

float UGTUpgradeDefinition::SellFraction(int32 TraderTier)
{
	return TraderTier >= 2 ? 0.8f : TraderTier == 1 ? 0.7f : 0.6f;
}

float UGTUpgradeDefinition::RepairPriceFactor(int32 MechanicTier)
{
	return MechanicTier >= 2 ? 0.f : MechanicTier == 1 ? 0.5f : 1.f;
}
