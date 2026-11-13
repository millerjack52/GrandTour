#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Inventory/GTInventoryComponent.h"
#include "GTLootTable.generated.h"

/** One weighted entry: the item and how many of it a pick pays. */
USTRUCT(BlueprintType)
struct FGTLootEntry
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot")
	FName ItemId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot", meta = (ClampMin = 0))
	int32 MinCount = 1;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot", meta = (ClampMin = 0))
	int32 MaxCount = 1;

	/** Relative chance of this entry per pick. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot", meta = (ClampMin = 0))
	float Weight = 1.f;
};

/**
 * A loot table (ARCHITECTURE 4: harvest nodes and wrecks reference one). Each harvest makes
 * PicksMin..PicksMax weighted picks with replacement and merges them into stacks; Guaranteed
 * stacks are paid every time on top. A primary data asset rather than a data table so the
 * picks-per-harvest live with the rows and the C++ defaults can write DA_Loot_* headless.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTLootTable : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot")
	FName TableId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot")
	TArray<FGTLootEntry> Entries;

	/** Paid every harvest regardless of the picks. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot")
	TArray<FGTItemStack> Guaranteed;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot", meta = (ClampMin = 0))
	int32 PicksMin = 1;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Loot", meta = (ClampMin = 0))
	int32 PicksMax = 2;

	/** Rolls one harvest's yield into Out (merged stacks). */
	void Roll(FRandomStream& Random, TArray<FGTItemStack>& Out) const;

	UFUNCTION(BlueprintPure, Category = "GT|Loot")
	FString Describe() const;

	struct FDefault
	{
		const TCHAR* AssetName;
		const TCHAR* Id;
		int32 PicksMin;
		int32 PicksMax;
		TArray<FGTLootEntry> Entries;
		TArray<FGTItemStack> Guaranteed;
	};
	/** CableBundle, Wreck, RadiationCache. */
	static TArrayView<const FDefault> DefaultTables();
	static const FDefault* FindDefault(FName Id);
	void ApplyDefault(const FDefault& Row);

	static FGTLootEntry Entry(FName ItemId, int32 Min, int32 Max, float Weight);
	static FGTItemStack Stack(FName ItemId, int32 Count);
};
