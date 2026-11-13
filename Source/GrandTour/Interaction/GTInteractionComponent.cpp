#include "Interaction/GTInteractionComponent.h"

#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

UGTInteractionComponent::UGTInteractionComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

void UGTInteractionComponent::UpdateTarget()
{
	AActor* Owner = GetOwner();
	UWorld* World = GetWorld();
	if (!Owner || !World || bSuppressed)
	{
		CurrentTarget = nullptr;
		CurrentOffer = FGTInteractionOffer();
		return;
	}
	FVector EyeLocation;
	FRotator EyeRotation;
	Owner->GetActorEyesViewPoint(EyeLocation, EyeRotation);
	const FVector End = EyeLocation + EyeRotation.Vector() * FMath::Max(Range, LongRange);

	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTInteraction), /*bTraceComplex*/ false, Owner);
	FHitResult Hit;
	AActor* NewTarget = nullptr;
	if (World->LineTraceSingleByChannel(Hit, EyeLocation, End, ECC_Visibility, Params))
	{
		AActor* HitActor = Hit.GetActor();
		if (HitActor && HitActor->Implements<UGTInteractable>())
		{
			// Arm's length for everything; further only when the thing itself allows it (a photo subject across a field).
			const float Allowed = FMath::Max(Range, Cast<IGTInteractable>(HitActor)->GetInteractionRange());
			if (Hit.Distance <= Allowed)
			{
				NewTarget = HitActor;
				HitLocation = Hit.ImpactPoint;
				HitComponent = Hit.GetComponent();
			}
		}
	}
	if (NewTarget != CurrentTarget.Get())
	{
		HoldProgress = 0.f;
		CurrentTarget = NewTarget;
	}
	if (NewTarget)
	{
		FGTInteractionQuery Query;
		Query.Instigator = Owner;
		Query.HitLocation = HitLocation;
		Query.HitComponent = HitComponent.Get();
		CurrentOffer = Cast<IGTInteractable>(NewTarget)->GetInteractionOffer(Query);
	}
	else
	{
		CurrentOffer = FGTInteractionOffer();
	}
}

void UGTInteractionComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	UpdateTarget();

	if (!bHolding || bNeedsRelease || !CurrentTarget.IsValid() || !CurrentOffer.bAvailable)
	{
		if (!bHolding)
		{
			bNeedsRelease = false;
		}
		HoldProgress = 0.f;
		return;
	}
	if (CurrentOffer.HoldTime <= 0.f)
	{
		Fire();
		return;
	}
	HoldProgress = FMath::Min(1.f, HoldProgress + DeltaTime / CurrentOffer.HoldTime);
	if (HoldProgress >= 1.f)
	{
		Fire();
	}
}

void UGTInteractionComponent::Fire()
{
	AActor* Target = CurrentTarget.Get();
	if (!Target)
	{
		return;
	}
	FGTInteractionQuery Query;
	Query.Instigator = GetOwner();
	Query.HitLocation = HitLocation;
	Query.HitComponent = HitComponent.Get();
	UE_LOG(LogTemp, Display, TEXT("UGTInteractionComponent: %s -> %s"), *GetNameSafe(GetOwner()), *CurrentOffer.Prompt);
	Cast<IGTInteractable>(Target)->Interact(Query);
	++InteractionsCompleted;
	HoldProgress = 0.f;
	bNeedsRelease = true;   // one interaction per press
	UpdateTarget();
}

void UGTInteractionComponent::SetHoldInput(bool bHeld)
{
	bHolding = bHeld;
	if (!bHeld)
	{
		bNeedsRelease = false;
		HoldProgress = 0.f;
	}
}

FString UGTInteractionComponent::Describe() const
{
	return FString::Printf(TEXT("target=%s available=%d prompt='%s' hold=%.2f/%.1f done=%d"),
		CurrentTarget.IsValid() ? *CurrentTarget->GetName() : TEXT("none"), CurrentOffer.bAvailable ? 1 : 0,
		*GetPrompt(), HoldProgress, CurrentOffer.HoldTime, InteractionsCompleted);
}
