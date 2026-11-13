#include "Crafting/GTGarage.h"
#include "Character/GTPlayerCharacter.h"
#include "Core/GTPlayerController.h"
#include "Vehicle/GTCarPawn.h"
#include "Components/StaticMeshComponent.h"

AGTGarage::AGTGarage()
{
	DisplayName = TEXT("Riverside garage");
	GreyboxSize = FVector(100,18,210);
}

void AGTGarage::BeginPlay()
{
	Super::BeginPlay();
	Mesh->SetHiddenInGame(true);
}

void AGTGarage::BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const
{
	const AGTPlayerController* PC = User ? Cast<AGTPlayerController>(User->GetController()) : nullptr;
	Rows.Add(FGTScreenRow::Header(TEXT("Choose a vehicle - scroll to select, T to collect")));
	for (int32 Index=0; Index<Vehicles.Num(); ++Index)
	{
		const auto& Entry = Vehicles[Index];
		const bool bCurrent = PC && PC->GetCar() && PC->GetCar()->GetClass()==Entry.VehicleClass;
		Rows.Add(FGTScreenRow::Line(Entry.Name.ToString()+(bCurrent ? TEXT("  [current]") : TEXT("")), Index,
			Entry.VehicleClass && PC && PC->GetPawn()==User && !bCurrent, bCurrent ? TEXT("Already yours") : TEXT("Replace current car")));
	}
}

bool AGTGarage::Act(AGTPlayerCharacter* User, const FGTScreenRow& Row)
{
	AGTPlayerController* PC = User ? Cast<AGTPlayerController>(User->GetController()) : nullptr;
	if (!PC || User->GetStation()!=this || FVector::DistSquared(User->GetActorLocation(),GetActorLocation())>FMath::Square(600.f) || !Vehicles.IsValidIndex(Row.Action)) return false;
	if (PC->GetCar() && PC->GetCar()->GetClass()==Vehicles[Row.Action].VehicleClass) return false;
	return PC->ReplaceGarageVehicle(Vehicles[Row.Action].VehicleClass,VehicleSpawnTransform,LastMessage);
}
