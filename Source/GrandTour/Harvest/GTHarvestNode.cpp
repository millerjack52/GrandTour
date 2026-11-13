#include "Harvest/GTHarvestNode.h"

#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Harvest/GTLootTable.h"
#include "Tools/GTToolDefinition.h"
#include "Vehicle/GTWinchAnchor.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	FString ToolNameForTag(const FGameplayTag& Tag)
	{
		for (const UGTToolDefinition::FDefault& Row : UGTToolDefinition::DefaultTools())
		{
			if (Tag.GetTagName() == FName(Row.Tag))
			{
				return FString(Row.Name).ToLower();
			}
		}
		return Tag.ToString();
	}
}

AGTHarvestNode::AGTHarvestNode()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		Mesh->SetStaticMesh(CubeMesh.Object);
	}
	RequiredToolTag = GTTags::Tool_Cut;
	FGTItemStack Wire;
	Wire.ItemId = GTItems::Wire;
	Wire.Count = 2;
	Yield.Add(Wire);
}

void AGTHarvestNode::BeginPlay()
{
	Super::BeginPlay();
	UsesLeft = Uses;
	Mesh->SetRelativeScale3D(GreyboxSize / 100.f);
	GTGreybox::ApplyPropColour(Mesh, this, Colour);
	if (!LootTable && !LootTablePath.IsEmpty())
	{
		LootTable = LoadObject<UGTLootTable>(nullptr, *LootTablePath);
		if (!LootTable)
		{
			UE_LOG(LogTemp, Warning, TEXT("AGTHarvestNode %s: loot table %s not found, paying the fixed yield"), *NodeName, *LootTablePath);
		}
	}
	LootRandom.Initialize(GetTypeHash(GetFName()));
}

FGTInteractionOffer AGTHarvestNode::HarvestOffer(const FGTInteractionQuery& Query) const
{
	const AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (!Character)
	{
		return FGTInteractionOffer::Unavailable(TEXT(""));
	}
	if (IsDepleted())
	{
		return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("%s: nothing left"), *NodeName));
	}
	if (Character->IsCarryingHook())
	{
		return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("%s: hands full with the hook"), *NodeName));
	}
	if (!Character->HasToolTag(RequiredToolTag))
	{
		return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("%s: needs a %s"), *NodeName, *ToolNameForTag(RequiredToolTag)));
	}
	const UGTToolDefinition* Tool = Character->GetCurrentTool();
	return FGTInteractionOffer::Available(FString::Printf(TEXT("Harvest %s (%d left)"), *NodeName, UsesLeft), HarvestTime * (Tool ? Tool->UseTimeScale : 1.f));
}

FGTInteractionOffer AGTHarvestNode::GetInteractionOffer(const FGTInteractionQuery& Query) const
{
	return HarvestOffer(Query);
}

void AGTHarvestNode::Harvest(const FGTInteractionQuery& Query)
{
	AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (!Character || !HarvestOffer(Query).bAvailable)
	{
		return;
	}
	LastAccepted = 0;
	LastDropped = 0;
	LastRoll.Reset();
	if (LootTable)
	{
		LootTable->Roll(LootRandom, LastRoll);
	}
	else
	{
		LastRoll = Yield;
	}
	for (const FGTItemStack& Stack : LastRoll)
	{
		const int32 Accepted = Character->GetInventory()->Add(Stack.ItemId, Stack.Count);
		LastAccepted += Accepted;
		LastDropped += Stack.Count - Accepted;   // no room: lost for now (dropped-item actors are an M3 item)
	}
	--UsesLeft;
	++HarvestCount;
	UE_LOG(LogTemp, Display, TEXT("AGTHarvestNode %s: harvested, accepted %d dropped %d, %d uses left"), *NodeName, LastAccepted, LastDropped, UsesLeft);
	if (IsDepleted())
	{
		Mesh->SetRelativeScale3D(GreyboxSize / 100.f * FVector(1.f, 1.f, 0.35f));
	}
}

void AGTHarvestNode::Interact(const FGTInteractionQuery& Query)
{
	Harvest(Query);
}

FString AGTHarvestNode::Describe() const
{
	return FString::Printf(TEXT("%s uses=%d/%d harvested=%d lastAccepted=%d lastDropped=%d"), *NodeName, UsesLeft, Uses, HarvestCount, LastAccepted, LastDropped);
}

// ---- wreck -------------------------------------------------------------------------------------

AGTWreck::AGTWreck()
{
	NodeName = TEXT("wreck");
	RequiredToolTag = GTTags::Tool_Pry;
	HarvestTime = 3.f;
	Uses = 2;
	GreyboxSize = FVector(320.f, 160.f, 110.f);
	Colour = FLinearColor(0.45f, 0.2f, 0.1f);
	Yield.Reset();
	FGTItemStack Scrap;
	Scrap.ItemId = GTItems::Scrap;
	Scrap.Count = 3;
	Yield.Add(Scrap);
	FGTItemStack Radiator;
	Radiator.ItemId = GTItems::PartRadiator;
	Radiator.Count = 1;
	Yield.Add(Radiator);

	Anchor = CreateDefaultSubobject<UGTWinchAnchorComponent>(TEXT("Anchor"));
	Anchor->SetupAttachment(Mesh);
	Anchor->SetRelativeLocation(FVector(0.f, 0.f, 0.f));
	Anchor->StrengthN = 30000.f;   // a wreck drags before a good winch stalls
	Anchor->DisplayName = TEXT("wreck");
}

FGTInteractionOffer AGTWreck::GetInteractionOffer(const FGTInteractionQuery& Query) const
{
	const AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (Character && Character->IsCarryingHook())
	{
		return GTGreybox::AnchorOffer(Anchor, Query);
	}
	return HarvestOffer(Query);
}

void AGTWreck::Interact(const FGTInteractionQuery& Query)
{
	const AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (Character && Character->IsCarryingHook())
	{
		GTGreybox::AttachHook(Anchor, Query);
		return;
	}
	Harvest(Query);
}
