#pragma once

#include "CoreMinimal.h"
#include "Crafting/GTCraftingStation.h"
#include "GTGarage.generated.h"

USTRUCT(BlueprintType)
struct FGTGarageVehicle
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FText Name;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) TSubclassOf<AGTCarPawn> VehicleClass;
};

/** Door-sized interaction proxy, reusable with any building and fleet. No runtime tick. */
UCLASS()
class GRANDTOUR_API AGTGarage : public AGTCraftingStation
{
	GENERATED_BODY()
public:
	AGTGarage();
	virtual void BeginPlay() override;
	virtual void BuildRows(AGTPlayerCharacter* User, TArray<FGTScreenRow>& Rows) const override;
	virtual bool Act(AGTPlayerCharacter* User, const FGTScreenRow& Row) override;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="GT|Garage") TArray<FGTGarageVehicle> Vehicles;
	/** World-space parked chassis origin, 1 m above the apron. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="GT|Garage", meta=(MakeEditWidget)) FTransform VehicleSpawnTransform;
};
