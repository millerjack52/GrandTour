#include "Vehicle/GTWinchAnchor.h"

#include "Character/GTPlayerCharacter.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTWinchComponent.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

void UGTWinchAnchorComponent::Fail(const FVector& PullDirection)
{
	if (bFailed)
	{
		return;
	}
	bFailed = true;
	UE_LOG(LogTemp, Display, TEXT("UGTWinchAnchorComponent: %s on %s tore out"), *DisplayName, *GetNameSafe(GetOwner()));
	if (AGTWinchAnchor* Post = Cast<AGTWinchAnchor>(GetOwner()))
	{
		Post->OnAnchorFailed(PullDirection);
	}
}

namespace GTGreybox
{
	void ApplyPropColour(UStaticMeshComponent* Mesh, UObject* Outer, const FLinearColor& Colour)
	{
		UMaterialInterface* Prop = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/GrandTour/Materials/M_GT_Prop.M_GT_Prop"));
		if (!Mesh || !Prop)
		{
			return;
		}
		UMaterialInstanceDynamic* Instance = UMaterialInstanceDynamic::Create(Prop, Outer);
		Instance->SetVectorParameterValue(TEXT("BaseColor"), Colour);
		Instance->SetScalarParameterValue(TEXT("Roughness"), 0.8f);
		Mesh->SetMaterial(0, Instance);
	}

	FGTInteractionOffer AnchorOffer(const UGTWinchAnchorComponent* Anchor, const FGTInteractionQuery& Query)
	{
		const AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
		if (!Anchor || !Character)
		{
			return FGTInteractionOffer::Unavailable(TEXT(""));
		}
		if (Anchor->bFailed)
		{
			return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("%s torn out"), *Anchor->DisplayName));
		}
		if (!Character->IsCarryingHook())
		{
			// Section 51: empty-handed at the anchor a winch holds, E takes the hook off; the winch stows it and rewinds.
			const UGTWinchComponent* Holder = Anchor->HeldBy.Get();
			if (Holder && Holder->GetState() == EGTWinchState::Attached && Holder->GetAnchor() == Anchor)
			{
				return FGTInteractionOffer::Available(FString::Printf(TEXT("Detach winch hook from %s"), *Anchor->DisplayName), 0.5f);
			}
			return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("%s: bring the winch hook"), *Anchor->DisplayName));
		}
		return FGTInteractionOffer::Available(FString::Printf(TEXT("Attach winch hook to %s"), *Anchor->DisplayName), 0.5f);
	}

	bool AttachHook(UGTWinchAnchorComponent* Anchor, const FGTInteractionQuery& Query)
	{
		AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
		if (Anchor && Character && !Character->IsCarryingHook())
		{
			UGTWinchComponent* Holder = Anchor->HeldBy.Get();
			if (Holder && Holder->GetState() == EGTWinchState::Attached && Holder->GetAnchor() == Anchor)
			{
				Holder->Release();
				return true;
			}
			return false;
		}
		AGTCarPawn* Car = Character ? Character->GetHookCar() : nullptr;
		UGTWinchComponent* Winch = Car ? Car->GetWinch() : nullptr;
		if (!Anchor || Anchor->bFailed || !Winch)
		{
			return false;
		}
		return Winch->AttachTo(Anchor);
	}
}

AGTWinchAnchor::AGTWinchAnchor()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (CylinderMesh.Succeeded())
	{
		Mesh->SetStaticMesh(CylinderMesh.Object);
	}
	// A 40 cm post, 1.6 m tall, pivot at its base.
	Mesh->SetRelativeScale3D(FVector(0.4f, 0.4f, 1.6f));

	Anchor = CreateDefaultSubobject<UGTWinchAnchorComponent>(TEXT("Anchor"));
	Anchor->SetupAttachment(Mesh);
	Anchor->SetRelativeLocation(FVector(0.f, 0.f, 0.3f));   // scaled by the post: about 50 cm up
	Anchor->DisplayName = TEXT("post");
}

void AGTWinchAnchor::BeginPlay()
{
	Super::BeginPlay();
	GTGreybox::ApplyPropColour(Mesh, this, Colour);
}

FGTInteractionOffer AGTWinchAnchor::GetInteractionOffer(const FGTInteractionQuery& Query) const
{
	return GTGreybox::AnchorOffer(Anchor, Query);
}

void AGTWinchAnchor::Interact(const FGTInteractionQuery& Query)
{
	GTGreybox::AttachHook(Anchor, Query);
}

void AGTWinchAnchor::OnAnchorFailed(const FVector& PullDirection)
{
	// The post comes out of the ground and falls toward the car.
	Mesh->SetSimulatePhysics(true);
	Mesh->SetPhysicsLinearVelocity(PullDirection * 300.f + FVector(0.f, 0.f, 150.f));
	Mesh->SetPhysicsAngularVelocityInDegrees(FVector::CrossProduct(FVector::UpVector, PullDirection) * -120.f);
}
