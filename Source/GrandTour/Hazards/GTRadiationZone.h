#pragma once

#include "CoreMinimal.h"
#include "Hazards/GTHazardVolume.h"
#include "GTRadiationZone.generated.h"

class UStaticMeshComponent;

/**
 * The static hazard (PROJECT_PLAN: the radiation pocket where the rare resources are). Drains
 * exposure on foot, cooks the engine and radiator slowly while the car is inside, lights the
 * dash's radiation lamp and feeds the Geiger click rate to the ambience. The rare nodes are
 * hand-placed inside it with a loot table (ARCHITECTURE 5). Greybox: a green slab on the ground.
 */
UCLASS()
class GRANDTOUR_API AGTRadiationZone : public AGTHazardVolume
{
	GENERATED_BODY()

public:
	AGTRadiationZone();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** Geiger clicks per second at the centre; falls off toward the edge. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Radiation")
	float ClickRateCentre = 30.f;

	UPROPERTY(EditAnywhere, Category = "GT|Radiation|Greybox")
	bool bBuildMarker = true;

	/** Intensity 0..1 at a point: 1 at the centre, 0 at the edge and outside. */
	UFUNCTION(BlueprintPure, Category = "GT|Radiation")
	float IntensityAt(const FVector& WorldLocation) const;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Radiation")
	float LastClickRate = 0.f;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Radiation")
	TObjectPtr<UStaticMeshComponent> Marker;
};
