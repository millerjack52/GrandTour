#include "Run/GTPhotoSubject.h"

#include "Character/GTPlayerCharacter.h"
#include "Core/GTPlayerController.h"
#include "Run/GTRunGameState.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTWinchAnchor.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

AGTPhotoSubject::AGTPhotoSubject()
{
	PrimaryActorTick.bCanEverTick = true;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));

	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	SetRootComponent(Body);
	Body->SetMobility(EComponentMobility::Movable);
	Body->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	if (CubeMesh.Succeeded())
	{
		Body->SetStaticMesh(CubeMesh.Object);
	}
	for (int32 Index = 0; Index < 4; ++Index)
	{
		UStaticMeshComponent* Leg = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("Leg%d"), Index));
		Leg->SetupAttachment(Body);
		Leg->SetMobility(EComponentMobility::Movable);
		Leg->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		if (CubeMesh.Succeeded())
		{
			Leg->SetStaticMesh(CubeMesh.Object);
		}
		Legs.Add(Leg);
	}
}

void AGTPhotoSubject::BeginPlay()
{
	Super::BeginPlay();
	// The body sits a leg's length above the ground; the actor location is the body's centre.
	const float LegLength = 60.f;
	Body->SetRelativeScale3D(BodySize / 100.f);
	GTGreybox::ApplyPropColour(Body, this, Colour);
	for (int32 Index = 0; Index < Legs.Num(); ++Index)
	{
		const float X = (Index < 2 ? 0.35f : -0.35f);
		const float Y = (Index % 2 == 0 ? 0.3f : -0.3f);
		// Relative to the scaled body: undo the body scale so the legs stay 12 cm square.
		Legs[Index]->SetRelativeLocation(FVector(X, Y, -0.5f - (LegLength * 0.5f) / BodySize.Z));
		Legs[Index]->SetRelativeScale3D(FVector(12.f / BodySize.X, 12.f / BodySize.Y, LegLength / BodySize.Z));
		GTGreybox::ApplyPropColour(Legs[Index], this, Colour * 0.8f);
	}
	if (AGTRunGameState* State = GetWorld()->GetGameState<AGTRunGameState>())
	{
		State->RegisterPhotoSubject(this);
	}
}

FGTInteractionOffer AGTPhotoSubject::GetInteractionOffer(const FGTInteractionQuery& Query) const
{
	const AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (!Character)
	{
		return FGTInteractionOffer::Unavailable(TEXT(""));
	}
	if (bPhotographed)
	{
		return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("%s: already on film"), *SubjectName));
	}
	if (Character->IsCarryingHook())
	{
		return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("%s: hands full with the hook"), *SubjectName));
	}
	return FGTInteractionOffer::Available(FString::Printf(TEXT("Photograph the %s (hold still)"), *SubjectName), HoldTime);
}

void AGTPhotoSubject::Interact(const FGTInteractionQuery& Query)
{
	if (bPhotographed || !Cast<AGTPlayerCharacter>(Query.Instigator))
	{
		return;
	}
	bPhotographed = true;
	++Photographs;
	if (AGTRunGameState* State = GetWorld()->GetGameState<AGTRunGameState>())
	{
		State->NotifyPhotographed(this);
	}
	UE_LOG(LogTemp, Display, TEXT("AGTPhotoSubject: %s photographed from %.1f m after %d flights"), *SubjectName, FVector::Dist(Query.Instigator->GetActorLocation(), GetActorLocation()) / 100.f, TimesSpooked);
}

bool AGTPhotoSubject::Flee(const FVector& ThreatLocation)
{
	if (TimesSpooked >= MaxFlees)
	{
		return false;
	}
	FVector Away = GetActorLocation() - ThreatLocation;
	Away.Z = 0.f;
	if (!Away.Normalize())
	{
		Away = GetActorForwardVector();
	}
	const FVector Target = GetActorLocation() + Away * FleeDistance;
	// Land on whatever is under the new spot; keep the body a leg's length above it.
	FVector Landing = Target;
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTPhotoFlee), false, this);
	if (GetWorld()->LineTraceSingleByObjectType(Hit, Target + FVector(0.f, 0.f, 500.f), Target - FVector(0.f, 0.f, 5000.f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
	{
		Landing.Z = Hit.ImpactPoint.Z + 60.f + BodySize.Z * 0.5f;
	}
	SetActorLocation(Landing, false, nullptr, ETeleportType::TeleportPhysics);
	SetActorRotation(Away.Rotation());
	++TimesSpooked;
	UE_LOG(LogTemp, Display, TEXT("AGTPhotoSubject: %s spooked (%d/%d), moved %.0f m to %s"), *SubjectName, TimesSpooked, MaxFlees, FleeDistance / 100.f, *Landing.ToCompactString());
	return true;
}

void AGTPhotoSubject::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bPhotographed || TimesSpooked >= MaxFlees)
	{
		return;
	}
	SpookCheckTimer += DeltaSeconds;
	if (SpookCheckTimer < 0.1f)
	{
		return;
	}
	SpookCheckTimer = 0.f;
	const AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0));
	if (!PC)
	{
		return;
	}
	const AGTCarPawn* Car = PC->GetCar();
	const AGTPlayerCharacter* Character = PC->GetPlayerCharacter();
	if (Car && FVector::DistSquared2D(Car->GetActorLocation(), GetActorLocation()) < FleeRadiusCar * FleeRadiusCar)
	{
		Flee(Car->GetActorLocation());
	}
	else if (Character && !PC->IsDriving() && FVector::DistSquared2D(Character->GetActorLocation(), GetActorLocation()) < FleeRadius * FleeRadius)
	{
		Flee(Character->GetActorLocation());
	}
}

FString AGTPhotoSubject::Describe() const
{
	return FString::Printf(TEXT("%s at %s photographed=%d spooked=%d/%d"), *SubjectName, *GetActorLocation().ToCompactString(), bPhotographed ? 1 : 0, TimesSpooked, MaxFlees);
}
