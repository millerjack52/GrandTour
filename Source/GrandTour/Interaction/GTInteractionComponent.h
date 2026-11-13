#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Interaction/GTInteractable.h"
#include "GTInteractionComponent.generated.h"

/**
 * Look-at interaction for the first-person character (ARCHITECTURE 5): every tick a line trace
 * from the owner's eyes finds the nearest IGTInteractable within Range, asks it for an offer,
 * and drives hold-to-use: while the use key is held on an available offer, HoldProgress climbs
 * to 1 over the offer's hold time and Interact fires once (instant offers fire on the press).
 * The greybox HUD reads CurrentOffer and HoldProgress for the prompt and ring.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTInteractionComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTInteractionComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Press / release of the use key. */
	UFUNCTION(BlueprintCallable, Category = "GT|Interaction")
	void SetHoldInput(bool bHeld);

	UFUNCTION(BlueprintPure, Category = "GT|Interaction")
	AActor* GetCurrentTarget() const { return CurrentTarget.Get(); }

	UFUNCTION(BlueprintPure, Category = "GT|Interaction")
	bool IsOfferAvailable() const { return CurrentOffer.bAvailable; }

	UFUNCTION(BlueprintPure, Category = "GT|Interaction")
	FString GetPrompt() const { return CurrentOffer.bAvailable ? CurrentOffer.Prompt : CurrentOffer.Reason; }

	UFUNCTION(BlueprintPure, Category = "GT|Interaction")
	float GetHoldProgress() const { return HoldProgress; }

	UFUNCTION(BlueprintPure, Category = "GT|Interaction")
	FString Describe() const;

	const FGTInteractionOffer& GetCurrentOffer() const { return CurrentOffer; }
	const FVector& GetHitLocation() const { return HitLocation; }

	/** Arm's length from the eyes, cm: what most things can be used from. */
	UPROPERTY(EditAnywhere, Category = "GT|Interaction")
	float Range = 300.f;

	/** How far the look trace reaches, cm; a hit beyond Range only counts when the interactable's own GetInteractionRange allows it (photo subjects). */
	UPROPERTY(EditAnywhere, Category = "GT|Interaction")
	float LongRange = 3000.f;

	/** Interactions completed since spawn (tests). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Interaction")
	int32 InteractionsCompleted = 0;

	/** Set while the owner should not interact at all (in the car, collapsed). */
	UPROPERTY(BlueprintReadWrite, Category = "GT|Interaction")
	bool bSuppressed = false;

private:
	void UpdateTarget();
	void Fire();

	TWeakObjectPtr<AActor> CurrentTarget;
	FGTInteractionOffer CurrentOffer;
	FVector HitLocation = FVector::ZeroVector;
	TWeakObjectPtr<UPrimitiveComponent> HitComponent;
	float HoldProgress = 0.f;
	bool bHolding = false;
	bool bNeedsRelease = false;
};
