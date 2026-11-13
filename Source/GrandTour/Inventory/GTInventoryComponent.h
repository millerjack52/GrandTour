#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GTInventoryComponent.generated.h"

/** A stack of one item kind. Items are identified by name until the item data assets arrive (ARCHITECTURE 4). */
USTRUCT(BlueprintType)
struct FGTItemStack
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Inventory")
	FName ItemId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Inventory")
	int32 Count = 1;
};

/** The greybox item table: weight per unit, a display name and a base price. Unknown items weigh 1 kg and are worth 1. */
namespace GTItems
{
	GRANDTOUR_API float WeightKg(FName ItemId);
	GRANDTOUR_API FString DisplayName(FName ItemId);
	GRANDTOUR_API int32 BasePrice(FName ItemId);

	inline const FName Scrap(TEXT("Scrap"));
	inline const FName Wire(TEXT("Wire"));
	inline const FName Bolts(TEXT("Bolts"));
	inline const FName FuelCan(TEXT("FuelCan"));
	inline const FName PartRadiator(TEXT("Part.Radiator"));
	inline const FName PartTyre(TEXT("Part.Tyre"));
	/** The rare resource of the radiation pockets (PROJECT_PLAN: the rare stuff lives in hazard zones). */
	inline const FName RareAlloy(TEXT("RareAlloy"));
}

/**
 * Weight-limited item storage (ARCHITECTURE 5): the character carries one, the car's boot is
 * another. Add returns how many units fitted; Transfer moves what fits into the other side.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTInventoryComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTInventoryComponent();

	/** Adds up to Count units; returns the number that fitted under the weight limit. */
	UFUNCTION(BlueprintCallable, Category = "GT|Inventory")
	int32 Add(FName ItemId, int32 Count);

	/** Removes up to Count units; returns the number removed. */
	UFUNCTION(BlueprintCallable, Category = "GT|Inventory")
	int32 Remove(FName ItemId, int32 Count);

	UFUNCTION(BlueprintPure, Category = "GT|Inventory")
	int32 CountOf(FName ItemId) const;

	UFUNCTION(BlueprintPure, Category = "GT|Inventory")
	bool Has(FName ItemId, int32 Count) const { return CountOf(ItemId) >= Count; }

	UFUNCTION(BlueprintPure, Category = "GT|Inventory")
	float GetTotalWeightKg() const;

	UFUNCTION(BlueprintPure, Category = "GT|Inventory")
	float GetFreeWeightKg() const { return FMath::Max(0.f, MaxWeightKg - GetTotalWeightKg()); }

	/** Moves up to Count units of ItemId into To; returns the number moved. */
	UFUNCTION(BlueprintCallable, Category = "GT|Inventory")
	int32 TransferTo(UGTInventoryComponent* To, FName ItemId, int32 Count);

	UFUNCTION(BlueprintPure, Category = "GT|Inventory")
	FString Describe() const;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Inventory")
	float MaxWeightKg = 40.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Inventory")
	TArray<FGTItemStack> Items;

	/** Bumps on every change (HUD refresh, tests). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Inventory")
	int32 Version = 0;
};
