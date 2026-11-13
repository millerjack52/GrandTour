#include "Hazards/GTRadiationZone.h"

#include "Core/GTGameplayTags.h"
#include "Vehicle/GTWinchAnchor.h"
#include "Weather/GTWeatherSubsystem.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

AGTRadiationZone::AGTRadiationZone()
{
	HazardTag = GTTags::Hazard_Radiation;
	ExposureDrainPerSecond = 6.f;
	Extent = FVector(2500.f, 2500.f, 600.f);
	CarDamage = {
		{EGTCarPart::Engine, 0.004f},
		{EGTCarPart::Radiator, 0.003f},
	};

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

void AGTRadiationZone::BeginPlay()
{
	Super::BeginPlay();
	if (bBuildMarker && Marker)
	{
		Marker->SetRelativeLocation(FVector(0.f, 0.f, -Extent.Z + 3.f));
		Marker->SetRelativeScale3D(FVector(Extent.X * 2.f, Extent.Y * 2.f, 6.f) / 100.f);
		GTGreybox::ApplyPropColour(Marker, this, FLinearColor(0.25f, 0.8f, 0.2f));
	}
	else if (Marker)
	{
		Marker->SetVisibility(false);
	}
}

float AGTRadiationZone::IntensityAt(const FVector& WorldLocation) const
{
	const FVector Local = Box->GetComponentTransform().InverseTransformPositionNoScale(WorldLocation);
	if (FMath::Abs(Local.X) > Extent.X || FMath::Abs(Local.Y) > Extent.Y || FMath::Abs(Local.Z) > Extent.Z)
	{
		return 0.f;
	}
	const float Edge = FMath::Max(FMath::Abs(Local.X) / Extent.X, FMath::Abs(Local.Y) / Extent.Y);
	return FMath::Clamp(1.f - Edge * Edge, 0.f, 1.f);
}

void AGTRadiationZone::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	LastClickRate = 0.f;
	const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	const float Intensity = Pawn ? IntensityAt(Pawn->GetActorLocation()) : 0.f;
	if (Intensity > 0.f)
	{
		LastClickRate = 2.f + ClickRateCentre * Intensity;
		if (UGTWeatherSubsystem* Weather = GetWorld()->GetSubsystem<UGTWeatherSubsystem>())
		{
			Weather->SetClickRate(LastClickRate);
		}
	}
}
