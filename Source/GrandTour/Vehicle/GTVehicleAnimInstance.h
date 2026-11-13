#pragma once

#include "CoreMinimal.h"
#include "VehicleAnimationInstance.h"
#include "GTVehicleAnimInstance.generated.h"

/**
 * Poses the wheel bones from the Chaos wheel state in code. Does the same as the Wheel Controller
 * anim node (rotation and suspension offset applied in component space), so the car needs no
 * Animation Blueprint. Replace with an Animation Blueprint when the rig grows (steering wheel,
 * dash needles) and keep the Wheel Controller node there.
 */
struct FGTVehicleAnimInstanceProxy : public FVehicleAnimationInstanceProxy
{
	FGTVehicleAnimInstanceProxy() : FVehicleAnimationInstanceProxy() {}
	FGTVehicleAnimInstanceProxy(UAnimInstance* Instance) : FVehicleAnimationInstanceProxy(Instance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;
};

UCLASS(transient)
class GRANDTOUR_API UGTVehicleAnimInstance : public UVehicleAnimationInstance
{
	GENERATED_BODY()

public:
	UGTVehicleAnimInstance(const FObjectInitializer& ObjectInitializer);

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;
};
