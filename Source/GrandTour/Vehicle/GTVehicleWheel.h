#pragma once

#include "CoreMinimal.h"
#include "ChaosVehicleWheel.h"
#include "GTVehicleWheel.generated.h"

/** Front wheel of the Range Rover blockout: steered, driven (permanent 4WD). Radius/width measured from the mesh. */
UCLASS()
class GRANDTOUR_API UGTVehicleWheelFront : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UGTVehicleWheelFront();
};

/** Rear wheel: driven, handbrake, no steering. */
UCLASS()
class GRANDTOUR_API UGTVehicleWheelRear : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UGTVehicleWheelRear();
};
