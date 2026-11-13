#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "GTItemRegistry.generated.h"

class UGTConsumableDefinition;
class UGTItemDefinition;
class UGTPartDefinition;
class UGTRecipeDefinition;
class UGTUpgradeDefinition;

/**
 * Every item, part, consumable, recipe and upgrade the game knows, by id (ARCHITECTURE 4).
 * Loads the DA_* assets under the content folders when they exist and builds the C++ defaults
 * for anything missing, so headless runs and a fresh checkout behave the same. The greybox
 * item table of M2 (GTItems) answers through this once it exists.
 */
UCLASS()
class GRANDTOUR_API UGTItemRegistry : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	static UGTItemRegistry* Get(const UObject* WorldContext);
	/** The registry of the running game instance, if any (for the free GTItems functions). */
	static UGTItemRegistry* Current() { return Active; }

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	UGTItemDefinition* Find(FName ItemId) const;

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	UGTPartDefinition* FindPart(FName ItemId) const;

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	UGTConsumableDefinition* FindConsumable(FName ItemId) const;

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	UGTRecipeDefinition* FindRecipe(FName RecipeId) const;

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	const TArray<UGTItemDefinition*>& GetItems() const { return ObjectPtrDecay(Items); }

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	const TArray<UGTPartDefinition*>& GetParts() const { return ObjectPtrDecay(Parts); }

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	const TArray<UGTRecipeDefinition*>& GetRecipes() const { return ObjectPtrDecay(Recipes); }

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	const TArray<UGTUpgradeDefinition*>& GetUpgrades() const { return ObjectPtrDecay(Upgrades); }

	/** Trader stock: every item flagged bTraderStocks, parts and consumables first. */
	UFUNCTION(BlueprintPure, Category = "GT|Items")
	TArray<UGTItemDefinition*> GetTraderStock() const;

	UFUNCTION(BlueprintPure, Category = "GT|Items")
	FString Describe() const;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Items")
	int32 ItemsFromAssets = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Items")
	int32 RecipesFromAssets = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Items")
	int32 UpgradesFromAssets = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Items")
	FString ItemFolder = TEXT("/Game/GrandTour/Items");

	UPROPERTY(BlueprintReadOnly, Category = "GT|Items")
	FString RecipeFolder = TEXT("/Game/GrandTour/Crafting");

	UPROPERTY(BlueprintReadOnly, Category = "GT|Items")
	FString UpgradeFolder = TEXT("/Game/GrandTour/Economy");

private:
	void Build();

	UPROPERTY(Transient)
	TArray<TObjectPtr<UGTItemDefinition>> Owned;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UGTItemDefinition>> Items;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UGTPartDefinition>> Parts;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UGTRecipeDefinition>> Recipes;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UGTUpgradeDefinition>> Upgrades;

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UGTItemDefinition>> ById;

	static UGTItemRegistry* Active;
};
