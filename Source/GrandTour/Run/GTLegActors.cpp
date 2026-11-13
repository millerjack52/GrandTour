#include "Run/GTLegActors.h"

#include "Vehicle/GTWinchAnchor.h"

#include "Components/BoxComponent.h"
#include "Engine/World.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

AGTLegVolume::AGTLegVolume()
{
	PrimaryActorTick.bCanEverTick = false;   // the game state polls ContainsPoint with the car's location

	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	SetRootComponent(Box);
	Box->SetMobility(EComponentMobility::Movable);
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Box->SetGenerateOverlapEvents(false);

	Marker = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Marker"));
	Marker->SetupAttachment(Box);
	Marker->SetMobility(EComponentMobility::Movable);
	Marker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Marker->SetCastShadow(false);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		Marker->SetStaticMesh(CubeMesh.Object);
	}
}

void AGTLegVolume::BeginPlay()
{
	Super::BeginPlay();
	Box->SetBoxExtent(Extent);
	if (bBuildMarker && Marker)
	{
		// A 6 cm slab on the ground across the box's footprint. The box centre usually sits well above
		// the floor, so the ground is found with a trace against static geometry; the box bottom is the fallback.
		const FVector Centre = GetActorLocation();
		float GroundZ = Centre.Z - Extent.Z;
		FHitResult Hit;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(GTLegVolumeGround), false, this);
		if (GetWorld()->LineTraceSingleByObjectType(Hit, Centre, Centre - FVector(0.f, 0.f, Extent.Z + 5000.f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
		{
			GroundZ = Hit.ImpactPoint.Z;
		}
		Marker->SetWorldLocation(FVector(Centre.X, Centre.Y, GroundZ + 3.f));
		Marker->SetRelativeScale3D(FVector(Extent.X * 2.f, Extent.Y * 2.f, 6.f) / 100.f);
		GTGreybox::ApplyPropColour(Marker, this, MarkerColour);
	}
	else if (Marker)
	{
		Marker->SetVisibility(false);
	}
}

bool AGTLegVolume::ContainsPoint(const FVector& WorldLocation) const
{
	const FVector Local = Box->GetComponentTransform().InverseTransformPositionNoScale(WorldLocation);
	return FMath::Abs(Local.X) <= Extent.X && FMath::Abs(Local.Y) <= Extent.Y && FMath::Abs(Local.Z) <= Extent.Z;
}

AGTCheckpoint::AGTCheckpoint()
{
	Extent = FVector(150.f, 1200.f, 500.f);
	MarkerColour = FLinearColor(0.95f, 0.8f, 0.15f);
}

AGTExtractionZone::AGTExtractionZone()
{
	Extent = FVector(800.f, 800.f, 500.f);
	MarkerColour = FLinearColor(0.2f, 0.85f, 0.35f);
}

AGTLegStart::AGTLegStart()
{
	PrimaryActorTick.bCanEverTick = false;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
}
