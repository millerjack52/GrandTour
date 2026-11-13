#include "Hazards/GTWeatherFront.h"

#include "Core/GTGameplayTags.h"
#include "Vehicle/GTWinchAnchor.h"
#include "Weather/GTWeatherStateDefinition.h"
#include "Weather/GTWeatherSubsystem.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

AGTWeatherFront::AGTWeatherFront()
{
	HazardTag = GTTags::Hazard_Weather;
	ExposureDrainPerSecond = 8.f;
	Extent = FVector(4000.f, 15000.f, 2000.f);   // 80 m deep, 300 m wide, tall
	CarDamage = {
		{EGTCarPart::Glass, 0.010f},
		{EGTCarPart::Body, 0.008f},
		{EGTCarPart::Radiator, 0.004f},
	};

	Wall = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Wall"));
	Wall->SetupAttachment(Box);
	Wall->SetMobility(EComponentMobility::Movable);
	Wall->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Wall->SetCastShadow(false);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		Wall->SetStaticMesh(CubeMesh.Object);
	}
}

void AGTWeatherFront::BeginPlay()
{
	Super::BeginPlay();
	if (bBuildWall && Wall)
	{
		// A 2 m thick dark slab on the leading face, the full width and height of the box.
		Wall->SetRelativeLocation(FVector(Extent.X - 100.f, 0.f, 0.f));
		Wall->SetRelativeScale3D(FVector(200.f, Extent.Y * 2.f, Extent.Z * 2.f) / 100.f);
		GTGreybox::ApplyPropColour(Wall, this, FLinearColor(0.12f, 0.12f, 0.15f));
	}
	else if (Wall)
	{
		Wall->SetVisibility(false);
	}
}

float AGTWeatherFront::DistanceAhead(const FVector& WorldLocation) const
{
	const FVector Local = Box->GetComponentTransform().InverseTransformPositionNoScale(WorldLocation);
	return Local.X - Extent.X;   // positive: ahead of the leading face
}

float AGTWeatherFront::PressureAt(const FVector& WorldLocation) const
{
	const FVector Local = Box->GetComponentTransform().InverseTransformPositionNoScale(WorldLocation);
	if (FMath::Abs(Local.Y) > Extent.Y + InfluenceCm || FMath::Abs(Local.Z) > Extent.Z + InfluenceCm)
	{
		return 0.f;
	}
	const float Ahead = FMath::Max(Local.X - Extent.X, -Local.X - Extent.X);   // distance outside along X, either side
	if (Ahead <= 0.f)
	{
		return 1.f;
	}
	return FMath::Clamp(1.f - Ahead / FMath::Max(1.f, InfluenceCm), 0.f, 1.f);
}

void AGTWeatherFront::Tick(float DeltaSeconds)
{
	if (SpeedCmPerSec != 0.f)
	{
		const FVector Step = GetActorForwardVector() * SpeedCmPerSec * DeltaSeconds;
		AddActorWorldOffset(Step, false, nullptr, ETeleportType::TeleportPhysics);
		Travelled += Step.Size();
	}
	Super::Tick(DeltaSeconds);   // exposure and car damage inside the box

	UGTWeatherSubsystem* Weather = GetWorld()->GetSubsystem<UGTWeatherSubsystem>();
	if (!Weather)
	{
		return;
	}
	if (!StormState)
	{
		StormState = Weather->FindState(TEXT("Storm"));
	}
	const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	LastPressure = Pawn ? PressureAt(Pawn->GetActorLocation()) : 0.f;
	if (LastPressure > 0.f)
	{
		Weather->ReportStormPressure(LastPressure, StormState);
	}
}
