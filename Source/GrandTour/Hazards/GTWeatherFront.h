#pragma once

#include "CoreMinimal.h"
#include "Hazards/GTHazardVolume.h"
#include "GTWeatherFront.generated.h"

class UGTWeatherStateDefinition;
class UStaticMeshComponent;

/**
 * The moving hazard (ARCHITECTURE 6d, PROJECT_PLAN): a storm wall that crosses the leg at
 * SpeedCmPerSec along its yaw. It owns no weather of its own: every tick it tells the weather
 * subsystem how close its storm is (pressure 1 inside, fading to 0 over InfluenceCm ahead of
 * the box), and the subsystem blends toward the storm state, which is what drops visibility.
 * Inside the box the player drains exposure and the car takes slow body, glass and radiator
 * damage. Greybox: a tall dark slab on the leading face so it can be seen coming.
 */
UCLASS()
class GRANDTOUR_API AGTWeatherFront : public AGTHazardVolume
{
	GENERATED_BODY()

public:
	AGTWeatherFront();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** Travel speed along the actor's forward (X) axis, cm/s. 400 crosses a 1.2 km leg in five minutes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Front")
	float SpeedCmPerSec = 400.f;

	/** Distance ahead of the box over which the storm builds (pressure 0 -> 1). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Front")
	float InfluenceCm = 15000.f;

	/** The state the subsystem blends toward; none = the Storm default. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Front")
	TObjectPtr<UGTWeatherStateDefinition> StormState;

	UPROPERTY(EditAnywhere, Category = "GT|Front|Greybox")
	bool bBuildWall = true;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Front")
	float LastPressure = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Front")
	float Travelled = 0.f;

	/** Distance from a point to the box along its travel axis (negative once inside or behind). */
	UFUNCTION(BlueprintPure, Category = "GT|Front")
	float DistanceAhead(const FVector& WorldLocation) const;

	/** Storm pressure a point feels: 1 inside, 0 beyond InfluenceCm ahead. */
	UFUNCTION(BlueprintPure, Category = "GT|Front")
	float PressureAt(const FVector& WorldLocation) const;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Front")
	TObjectPtr<UStaticMeshComponent> Wall;
};
