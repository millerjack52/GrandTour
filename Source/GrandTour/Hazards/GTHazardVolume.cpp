#include "Hazards/GTHazardVolume.h"

#include "Character/GTExposureComponent.h"
#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Core/GTPlayerController.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"

#include "Components/BoxComponent.h"
#include "Kismet/GameplayStatics.h"

AGTHazardVolume::AGTHazardVolume()
{
	PrimaryActorTick.bCanEverTick = true;

	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	SetRootComponent(Box);
	Box->SetMobility(EComponentMobility::Movable);
	Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Box->SetCollisionObjectType(ECC_WorldDynamic);
	Box->SetCollisionResponseToAllChannels(ECR_Ignore);
	Box->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Box->SetGenerateOverlapEvents(true);
	HazardTag = GTTags::Hazard_Weather;
}

void AGTHazardVolume::BeginPlay()
{
	Super::BeginPlay();
	Box->SetBoxExtent(Extent);
	Box->UpdateOverlaps();
}

bool AGTHazardVolume::ContainsPoint(const FVector& WorldLocation) const
{
	const FVector Local = Box->GetComponentTransform().InverseTransformPositionNoScale(WorldLocation);
	return FMath::Abs(Local.X) <= Extent.X && FMath::Abs(Local.Y) <= Extent.Y && FMath::Abs(Local.Z) <= Extent.Z;
}

AGTCarPawn* AGTHazardVolume::FindPlayerCar() const
{
	if (const AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0)))
	{
		return PC->GetCar() ? PC->GetCar() : Cast<AGTCarPawn>(PC->GetPawn());
	}
	return nullptr;
}

void AGTHazardVolume::AffectCar(AGTCarPawn* Car, float DeltaSeconds)
{
	Car->NotifyHazardContact(HazardTag);
	UGTConditionComponent* Condition = Car->GetCondition();
	if (!Condition)
	{
		return;
	}
	for (const FGTPartDamageRate& Rate : CarDamage)
	{
		TotalCarDamage += Condition->ApplyHazardDamage(HazardTag, Rate.Part, Rate.PerSecond * DeltaSeconds);
	}
}

void AGTHazardVolume::AffectCharacter(AGTPlayerCharacter* Character, float DeltaSeconds)
{
	const float Amount = ExposureDrainPerSecond * DeltaSeconds * (1.f - Character->GetResistance(HazardTag));
	Character->GetExposure()->Drain(Amount, HazardTag);
	TotalDrained += Amount;
}

void AGTHazardVolume::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	TArray<AActor*> Overlapping;
	Box->GetOverlappingActors(Overlapping, AGTPlayerCharacter::StaticClass());
	CharactersInside = 0;
	for (AActor* Actor : Overlapping)
	{
		AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Actor);
		if (!Character || Character->IsInCar())
		{
			continue;
		}
		++CharactersInside;
		AffectCharacter(Character, DeltaSeconds);
	}
	AGTCarPawn* Car = FindPlayerCar();
	bCarInside = Car && ContainsPoint(Car->GetActorLocation());
	if (bCarInside)
	{
		AffectCar(Car, DeltaSeconds);
	}
}

FString AGTHazardVolume::Describe() const
{
	return FString::Printf(TEXT("%s tag=%s inside: characters=%d car=%d drained=%.0f carDamage=%.3f"),
		*GetName(), *HazardTag.ToString(), CharactersInside, bCarInside ? 1 : 0, TotalDrained, TotalCarDamage);
}
