#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "Inventory/GTInventoryComponent.h"
#include "GTRecipeDefinition.generated.h"

/**
 * A crafting recipe (ARCHITECTURE 4): the station it needs, the workbench tier that unlocks it,
 * inputs, output and a craft time. Assets under /Game/GrandTour/Crafting (Art/setup_m4_base.bat
 * writes DA_Recipe_*); the registry builds the C++ defaults when they are missing.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTRecipeDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Recipe")
	FName RecipeId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Recipe")
	FText DisplayName;

	/** Station.Workbench (the lift and trader are not crafting stations). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Recipe")
	FGameplayTag StationTag;

	/** Workbench crew tier needed (0 = always; tier 1 unlocks the tier-2 parts). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Recipe", meta = (ClampMin = 0, ClampMax = 3))
	int32 RequiredTier = 0;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Recipe")
	TArray<FGTItemStack> Inputs;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Recipe")
	FGTItemStack Output;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Recipe", meta = (ClampMin = 0))
	float CraftSeconds = 3.f;

	UFUNCTION(BlueprintPure, Category = "GT|Recipe")
	FString DescribeInputs() const;

	UFUNCTION(BlueprintPure, Category = "GT|Recipe")
	FString Describe() const;

	struct FDefault
	{
		const TCHAR* AssetName;
		const TCHAR* Id;
		const TCHAR* Name;
		const TCHAR* Station;
		int32 Tier;
		TArray<FGTItemStack> Inputs;
		FGTItemStack Output;
		float Seconds;
	};
	static TArrayView<const FDefault> DefaultRecipes();
	void ApplyDefault(const FDefault& Row);
};
