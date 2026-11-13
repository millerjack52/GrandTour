#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "GTInteractable.generated.h"

class UPrimitiveComponent;

/** Who is asking and where they are looking, passed to every interactable query. */
struct FGTInteractionQuery
{
	/** The interacting actor (the player character on foot). */
	AActor* Instigator = nullptr;

	/** World point the look trace hit on the interactable. */
	FVector HitLocation = FVector::ZeroVector;

	UPrimitiveComponent* HitComponent = nullptr;
};

/** What an interactable offers for a query: the prompt to show, how long to hold, or why not. */
struct FGTInteractionOffer
{
	bool bAvailable = false;

	/** Shown when available ("Harvest scrap pile"). */
	FString Prompt;

	/** Shown when not available ("Needs a cutter"); empty means show nothing. */
	FString Reason;

	/** Seconds the use key must be held; 0 = instant. */
	float HoldTime = 0.f;

	static FGTInteractionOffer Unavailable(const FString& InReason)
	{
		FGTInteractionOffer Offer;
		Offer.Reason = InReason;
		return Offer;
	}

	static FGTInteractionOffer Available(const FString& InPrompt, float InHoldTime)
	{
		FGTInteractionOffer Offer;
		Offer.bAvailable = true;
		Offer.Prompt = InPrompt;
		Offer.HoldTime = InHoldTime;
		return Offer;
	}
};

UINTERFACE(MinimalAPI)
class UGTInteractable : public UInterface
{
	GENERATED_BODY()
};

/**
 * One interface for everything the player can use on foot (ARCHITECTURE 5, Interaction): nodes,
 * wrecks, anchors, the car. UGTInteractionComponent asks GetInteractionOffer every tick for what
 * the player is looking at and calls Interact when the hold completes. Tool requirements are a
 * gameplay tag check inside the offer (the character's current tool grants tags).
 */
class GRANDTOUR_API IGTInteractable
{
	GENERATED_BODY()

public:
	virtual FGTInteractionOffer GetInteractionOffer(const FGTInteractionQuery& Query) const = 0;
	virtual void Interact(const FGTInteractionQuery& Query) = 0;

	/** How far away (cm) this can be used from; 0 = the component's arm's-length default. A photo subject answers with its camera range. */
	virtual float GetInteractionRange() const { return 0.f; }
};
