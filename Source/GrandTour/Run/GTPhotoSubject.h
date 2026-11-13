#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interaction/GTInteractable.h"
#include "GTPhotoSubject.generated.h"

class UStaticMeshComponent;

/**
 * The subject of a photograph leg (PROJECT_PLAN 6, leg mission types): a rare animal placed
 * off the route. On foot, look at it from up to PhotoRange and hold E to photograph it; the
 * run game state counts the picture toward the leg's PhotosRequired. Come closer than
 * FleeRadius on foot (or FleeRadiusCar in the car) before the picture and it moves off by
 * FleeDistance, up to MaxFlees times, after which it is too tired to care. Greybox: a body box
 * on four leg posts in the subject's colour, no animation.
 */
UCLASS()
class GRANDTOUR_API AGTPhotoSubject : public AActor, public IGTInteractable
{
	GENERATED_BODY()

public:
	AGTPhotoSubject();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual FGTInteractionOffer GetInteractionOffer(const FGTInteractionQuery& Query) const override;
	virtual void Interact(const FGTInteractionQuery& Query) override;
	virtual float GetInteractionRange() const override { return PhotoRange; }

	UFUNCTION(BlueprintPure, Category = "GT|Photo")
	bool IsPhotographed() const { return bPhotographed; }

	UFUNCTION(BlueprintPure, Category = "GT|Photo")
	FString Describe() const;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Photo")
	FString SubjectName = TEXT("spectacled bear");

	/** How far away the picture can be taken from, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Photo")
	float PhotoRange = 2500.f;

	/** Seconds to hold still for the picture. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Photo")
	float HoldTime = 1.5f;

	/** A character closer than this spooks it, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Photo")
	float FleeRadius = 800.f;

	/** A car closer than this spooks it, cm (cars are loud). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Photo")
	float FleeRadiusCar = 1500.f;

	/** How far it moves off when spooked, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Photo")
	float FleeDistance = 4000.f;

	/** After this many flights it stays put. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Photo")
	int32 MaxFlees = 3;

	UPROPERTY(EditAnywhere, Category = "GT|Photo|Greybox")
	FVector BodySize = FVector(160.f, 70.f, 80.f);

	UPROPERTY(EditAnywhere, Category = "GT|Photo|Greybox")
	FLinearColor Colour = FLinearColor(0.35f, 0.22f, 0.12f);

	UPROPERTY(BlueprintReadOnly, Category = "GT|Photo")
	int32 TimesSpooked = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Photo")
	int32 Photographs = 0;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Photo")
	TObjectPtr<UStaticMeshComponent> Body;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Photo")
	TArray<TObjectPtr<UStaticMeshComponent>> Legs;

	/** Moves off away from a threat; false when it has fled enough times. */
	bool Flee(const FVector& ThreatLocation);

	bool bPhotographed = false;
	float SpookCheckTimer = 0.f;
};
