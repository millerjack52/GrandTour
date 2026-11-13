#include "Base/GTDepartGate.h"

#include "Base/GTBaseGameMode.h"
#include "Core/GTPlayerController.h"
#include "Vehicle/GTCarPawn.h"

#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

AGTDepartGate::AGTDepartGate()
{
	PrimaryActorTick.bCanEverTick = true;
	Extent = FVector(200.f, 600.f, 400.f);
	MarkerColour = FLinearColor(0.9f, 0.3f, 0.2f);
}

void AGTDepartGate::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bTriggered)
	{
		return;
	}
	const AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0));
	const AGTCarPawn* Car = PC ? PC->GetCar() : nullptr;
	if (!Car || !PC->IsDriving() || !ContainsPoint(Car->GetActorLocation()))
	{
		return;
	}
	if (AGTBaseGameMode* Base = GetWorld()->GetAuthGameMode<AGTBaseGameMode>())
	{
		bTriggered = Base->Depart();
	}
}
