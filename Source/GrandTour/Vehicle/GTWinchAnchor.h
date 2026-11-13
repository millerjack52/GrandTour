#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "GameFramework/Actor.h"
#include "Interaction/GTInteractable.h"
#include "Vehicle/GTWinchComponent.h"
#include "GTWinchAnchor.generated.h"

class UStaticMeshComponent;
class UGTWinchComponent;

/**
 * Something the winch hook can be attached to (ARCHITECTURE 6e): a strength rating in newtons
 * and a failed flag. Lives on AGTWinchAnchor and on AGTWreck; the winch reads the strength and
 * calls Fail when the cable tension exceeds it.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTWinchAnchorComponent : public USceneComponent
{
	GENERATED_BODY()

public:
	/** Cable tension (N) this anchor holds before it tears out. A 9500 lb winch pulls 42 kN. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Winch")
	float StrengthN = 60000.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Winch")
	FString DisplayName = TEXT("anchor");

	UPROPERTY(BlueprintReadOnly, Category = "GT|Winch")
	bool bFailed = false;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Winch")
	int32 AttachCount = 0;

	/** The winch whose hook is on this anchor: set by AttachTo, cleared by Release and Snap (section 51's "Detach winch hook"). */
	TWeakObjectPtr<UGTWinchComponent> HeldBy;

	/** Tears the anchor out: the owner decides what that looks like (the post topples toward the car). */
	void Fail(const FVector& PullDirection);

	bool CanAttach() const { return !bFailed; }
};

/** A post, tree or rock the level designer marks as an anchor; interact with the hook in hand to attach. */
UCLASS()
class GRANDTOUR_API AGTWinchAnchor : public AActor, public IGTInteractable
{
	GENERATED_BODY()

public:
	AGTWinchAnchor();

	virtual void BeginPlay() override;
	virtual FGTInteractionOffer GetInteractionOffer(const FGTInteractionQuery& Query) const override;
	virtual void Interact(const FGTInteractionQuery& Query) override;

	UFUNCTION(BlueprintPure, Category = "GT|Winch")
	UGTWinchAnchorComponent* GetAnchor() const { return Anchor; }

	/** Called by the anchor component when it fails: the post simulates and topples toward the car. */
	void OnAnchorFailed(const FVector& PullDirection);

	UPROPERTY(EditAnywhere, Category = "GT|Winch|Greybox")
	FLinearColor Colour = FLinearColor(0.35f, 0.25f, 0.15f);

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Winch")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Winch")
	TObjectPtr<UGTWinchAnchorComponent> Anchor;
};

/** Shared by the anchor, nodes and wrecks: a dynamic M_GT_Prop instance in one colour (nullptr if the master is missing). */
namespace GTGreybox
{
	GRANDTOUR_API void ApplyPropColour(UStaticMeshComponent* Mesh, UObject* Outer, const FLinearColor& Colour);
	/** Offer for attaching the hook (or detaching it when a winch holds this anchor and the hands are empty), or the reason it cannot be. */
	GRANDTOUR_API FGTInteractionOffer AnchorOffer(const UGTWinchAnchorComponent* Anchor, const FGTInteractionQuery& Query);
	/** Attaches the instigator's hook to Anchor, or, empty-handed at an anchor a winch holds, releases that winch (section 51); false if nothing happened. */
	GRANDTOUR_API bool AttachHook(UGTWinchAnchorComponent* Anchor, const FGTInteractionQuery& Query);
}
