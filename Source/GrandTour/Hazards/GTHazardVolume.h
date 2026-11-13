#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameplayTagContainer.h"
#include "Vehicle/GTConditionComponent.h"
#include "GTHazardVolume.generated.h"

class AGTCarPawn;
class UBoxComponent;
class UStaticMeshComponent;

/** Health per second a hazard takes from one car part while the car is inside (before resistances). */
USTRUCT(BlueprintType)
struct FGTPartDamageRate
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Hazard")
	EGTCarPart Part = EGTCarPart::Body;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Hazard")
	float PerSecond = 0.01f;
};

/**
 * Hazard volume base (ARCHITECTURE 5): a box that drains the exposure of every player character
 * on foot inside it by HazardTag, and (M3) damages the car's parts over time while the car is
 * inside, resisted by the condition component's per-tag resistance (parts fill it in M4). The
 * car is told it is in the hazard each tick so the dash and HUD can show it. The weather front
 * (moving) and radiation zone (static) derive from this; the plain box is the M2 test hazard.
 */
UCLASS()
class GRANDTOUR_API AGTHazardVolume : public AActor
{
	GENERATED_BODY()

public:
	AGTHazardVolume();

	virtual void Tick(float DeltaSeconds) override;

	/** Oriented box test; the car's skeletal mesh needs no overlap events this way. */
	UFUNCTION(BlueprintPure, Category = "GT|Hazard")
	bool ContainsPoint(const FVector& WorldLocation) const;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Hazard")
	FGameplayTag HazardTag;

	/** Exposure points per second taken from a character on foot inside the volume. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Hazard")
	float ExposureDrainPerSecond = 10.f;

	/** Car part damage per second while the car is inside; empty = the car is safe here. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Hazard")
	TArray<FGTPartDamageRate> CarDamage;

	/** Half extents, cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Hazard")
	FVector Extent = FVector(1000.f, 1000.f, 400.f);

	UPROPERTY(BlueprintReadOnly, Category = "GT|Hazard")
	float TotalDrained = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Hazard")
	float TotalCarDamage = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Hazard")
	int32 CharactersInside = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Hazard")
	bool bCarInside = false;

	UFUNCTION(BlueprintPure, Category = "GT|Hazard")
	FString Describe() const;

protected:
	virtual void BeginPlay() override;

	/** The player's car, if any (the controller's car, driven or parked). */
	AGTCarPawn* FindPlayerCar() const;

	/** Called each tick with the car inside; the base applies CarDamage. */
	virtual void AffectCar(AGTCarPawn* Car, float DeltaSeconds);

	/** Called each tick for a character on foot inside; the base drains exposure. */
	virtual void AffectCharacter(class AGTPlayerCharacter* Character, float DeltaSeconds);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Hazard")
	TObjectPtr<UBoxComponent> Box;
};
