#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameplayTagContainer.h"
#include "Interaction/GTInteractable.h"
#include "Inventory/GTInventoryComponent.h"
#include "GTHarvestNode.generated.h"

class UGTLootTable;
class UGTWinchAnchorComponent;
class UStaticMeshComponent;

/**
 * A placed resource node (ARCHITECTURE 5): needs a tool that grants RequiredToolTag, takes
 * HarvestTime (scaled by the tool) per use, and pays Yield into the harvester's inventory each
 * use until Uses run out. Greybox: a coloured box that shrinks when depleted. With a LootTable
 * set (the hand-placed nodes of M3) each use rolls the table instead of paying the fixed Yield;
 * the node's random stream is seeded from its name so a node pays the same on every run.
 */
UCLASS()
class GRANDTOUR_API AGTHarvestNode : public AActor, public IGTInteractable
{
	GENERATED_BODY()

public:
	AGTHarvestNode();

	virtual void BeginPlay() override;
	virtual FGTInteractionOffer GetInteractionOffer(const FGTInteractionQuery& Query) const override;
	virtual void Interact(const FGTInteractionQuery& Query) override;

	UFUNCTION(BlueprintPure, Category = "GT|Harvest")
	bool IsDepleted() const { return UsesLeft <= 0; }

	UFUNCTION(BlueprintPure, Category = "GT|Harvest")
	FString Describe() const;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Harvest")
	FString NodeName = TEXT("cable bundle");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Harvest")
	FGameplayTag RequiredToolTag;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Harvest")
	float HarvestTime = 2.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Harvest")
	TArray<FGTItemStack> Yield;

	/** Rolled per use instead of Yield when set. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Harvest")
	TObjectPtr<UGTLootTable> LootTable;

	/** Asset path used when LootTable is unset (/Game/GrandTour/Harvest/DA_Loot_Wreck), so a script-built map needs no object reference. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Harvest")
	FString LootTablePath;

	/** What the last use paid (before the bag limit). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Harvest")
	TArray<FGTItemStack> LastRoll;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Harvest")
	int32 Uses = 3;

	UPROPERTY(EditAnywhere, Category = "GT|Harvest|Greybox")
	FVector GreyboxSize = FVector(80.f, 80.f, 60.f);

	UPROPERTY(EditAnywhere, Category = "GT|Harvest|Greybox")
	FLinearColor Colour = FLinearColor(0.2f, 0.45f, 0.25f);

	UPROPERTY(BlueprintReadOnly, Category = "GT|Harvest")
	int32 UsesLeft = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Harvest")
	int32 HarvestCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Harvest")
	int32 LastAccepted = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Harvest")
	int32 LastDropped = 0;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Harvest")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** The harvest offer alone (a wreck adds the anchor offer in front of it). */
	FGTInteractionOffer HarvestOffer(const FGTInteractionQuery& Query) const;
	void Harvest(const FGTInteractionQuery& Query);

	FRandomStream LootRandom;
};

/** A wreck: pry parts and scrap out of it, or hook the winch to it (it is heavy enough to be an anchor). */
UCLASS()
class GRANDTOUR_API AGTWreck : public AGTHarvestNode
{
	GENERATED_BODY()

public:
	AGTWreck();

	virtual FGTInteractionOffer GetInteractionOffer(const FGTInteractionQuery& Query) const override;
	virtual void Interact(const FGTInteractionQuery& Query) override;

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	UGTWinchAnchorComponent* GetAnchor() const { return Anchor; }

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Winch")
	TObjectPtr<UGTWinchAnchorComponent> Anchor;
};
