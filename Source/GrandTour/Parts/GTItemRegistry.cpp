#include "Parts/GTItemRegistry.h"

#include "Crafting/GTRecipeDefinition.h"
#include "Economy/GTUpgradeDefinition.h"
#include "Parts/GTItemDefinition.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"

UGTItemRegistry* UGTItemRegistry::Active = nullptr;

void UGTItemRegistry::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Build();
	Active = this;
	UE_LOG(LogTemp, Display, TEXT("UGTItemRegistry: %s"), *Describe());
}

void UGTItemRegistry::Deinitialize()
{
	if (Active == this)
	{
		Active = nullptr;
	}
	Super::Deinitialize();
}

UGTItemRegistry* UGTItemRegistry::Get(const UObject* WorldContext)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	const UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
	return GameInstance ? GameInstance->GetSubsystem<UGTItemRegistry>() : Active;
}

namespace
{
	template <typename TAsset, typename TRow>
	TAsset* LoadOrBuild(UObject* Outer, const FString& Folder, const FString& AssetName, const TRow& Row, int32& FromAssets)
	{
		TAsset* Asset = LoadObject<TAsset>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), *Folder, *AssetName, *AssetName));
		if (Asset)
		{
			++FromAssets;
			return Asset;
		}
		Asset = NewObject<TAsset>(Outer, *AssetName, RF_Transient);
		GTItemDefaults::Apply(Asset, Row);
		return Asset;
	}
}

void UGTItemRegistry::Build()
{
	Owned.Reset();
	Items.Reset();
	Parts.Reset();
	Recipes.Reset();
	Upgrades.Reset();
	ById.Reset();
	auto Register = [this](UGTItemDefinition* Item)
	{
		if (!Item || Item->ItemId.IsNone())
		{
			return;
		}
		Owned.Add(Item);
		Items.Add(Item);
		ById.Add(Item->ItemId, Item);
		if (UGTPartDefinition* Part = Cast<UGTPartDefinition>(Item))
		{
			Parts.Add(Part);
		}
	};
	for (const GTItemDefaults::FResource& Row : GTItemDefaults::Resources())
	{
		Register(LoadOrBuild<UGTItemDefinition>(this, ItemFolder, GTItemDefaults::AssetName(Row.Id), Row, ItemsFromAssets));
	}
	for (const GTItemDefaults::FPart& Row : GTItemDefaults::Parts())
	{
		Register(LoadOrBuild<UGTPartDefinition>(this, ItemFolder, GTItemDefaults::AssetName(Row.Id), Row, ItemsFromAssets));
	}
	for (const GTItemDefaults::FConsumable& Row : GTItemDefaults::Consumables())
	{
		Register(LoadOrBuild<UGTConsumableDefinition>(this, ItemFolder, GTItemDefaults::AssetName(Row.Id), Row, ItemsFromAssets));
	}
	for (const UGTRecipeDefinition::FDefault& Row : UGTRecipeDefinition::DefaultRecipes())
	{
		UGTRecipeDefinition* Recipe = LoadObject<UGTRecipeDefinition>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), *RecipeFolder, Row.AssetName, Row.AssetName));
		if (Recipe)
		{
			++RecipesFromAssets;
		}
		else
		{
			Recipe = NewObject<UGTRecipeDefinition>(this, Row.AssetName, RF_Transient);
			Recipe->ApplyDefault(Row);
		}
		Recipes.Add(Recipe);
	}
	for (const UGTUpgradeDefinition::FDefault& Row : UGTUpgradeDefinition::DefaultUpgrades())
	{
		UGTUpgradeDefinition* Upgrade = LoadObject<UGTUpgradeDefinition>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), *UpgradeFolder, Row.AssetName, Row.AssetName));
		if (Upgrade)
		{
			++UpgradesFromAssets;
		}
		else
		{
			Upgrade = NewObject<UGTUpgradeDefinition>(this, Row.AssetName, RF_Transient);
			Upgrade->ApplyDefault(Row);
		}
		Upgrades.Add(Upgrade);
	}
}

UGTItemDefinition* UGTItemRegistry::Find(FName ItemId) const
{
	const TObjectPtr<UGTItemDefinition>* Found = ById.Find(ItemId);
	return Found ? Found->Get() : nullptr;
}

UGTPartDefinition* UGTItemRegistry::FindPart(FName ItemId) const
{
	return Cast<UGTPartDefinition>(Find(ItemId));
}

UGTConsumableDefinition* UGTItemRegistry::FindConsumable(FName ItemId) const
{
	return Cast<UGTConsumableDefinition>(Find(ItemId));
}

UGTRecipeDefinition* UGTItemRegistry::FindRecipe(FName RecipeId) const
{
	for (UGTRecipeDefinition* Recipe : Recipes)
	{
		if (Recipe && Recipe->RecipeId == RecipeId)
		{
			return Recipe;
		}
	}
	return nullptr;
}

TArray<UGTItemDefinition*> UGTItemRegistry::GetTraderStock() const
{
	TArray<UGTItemDefinition*> Stock;
	for (UGTItemDefinition* Item : Items)
	{
		if (Item->bTraderStocks && Item->Kind != EGTItemKind::Resource)
		{
			Stock.Add(Item);
		}
	}
	for (UGTItemDefinition* Item : Items)
	{
		if (Item->bTraderStocks && Item->Kind == EGTItemKind::Resource)
		{
			Stock.Add(Item);
		}
	}
	return Stock;
}

FString UGTItemRegistry::Describe() const
{
	return FString::Printf(TEXT("items=%d (assets %d) parts=%d recipes=%d (assets %d) upgrades=%d (assets %d)"),
		Items.Num(), ItemsFromAssets, Parts.Num(), Recipes.Num(), RecipesFromAssets, Upgrades.Num(), UpgradesFromAssets);
}
