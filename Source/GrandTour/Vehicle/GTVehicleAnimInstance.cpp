#include "Vehicle/GTVehicleAnimInstance.h"

#include "BonePose.h"
#include "ChaosWheeledVehicleMovementComponent.h"

void FGTVehicleAnimInstanceProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	// UVehicleAnimationInstance only tells its own member proxy about the vehicle; fetch it here.
	if (GetWheelAnimData().Num() == 0)
	{
		if (const UVehicleAnimationInstance* VehicleInstance = Cast<UVehicleAnimationInstance>(InAnimInstance))
		{
			if (const UChaosWheeledVehicleMovementComponent* Vehicle = VehicleInstance->GetWheeledVehicleComponent())
			{
				SetWheeledVehicleComponent(Vehicle);
			}
		}
	}
	FVehicleAnimationInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
}

bool FGTVehicleAnimInstanceProxy::Evaluate(FPoseContext& Output)
{
	Output.ResetToRefPose();

	const TArray<FWheelAnimationData>& Wheels = GetWheelAnimData();
	if (Wheels.Num() == 0)
	{
		return true;
	}

	const FBoneContainer& BoneContainer = Output.Pose.GetBoneContainer();
	FCSPose<FCompactPose> ComponentPose;
	ComponentPose.InitPose(Output.Pose);

	bool bChanged = false;
	for (const FWheelAnimationData& Wheel : Wheels)
	{
		const int32 MeshBoneIndex = BoneContainer.GetPoseBoneIndexForBoneName(Wheel.BoneName);
		if (MeshBoneIndex == INDEX_NONE)
		{
			continue;
		}
		const FCompactPoseBoneIndex BoneIndex = BoneContainer.MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshBoneIndex));
		if (BoneIndex.GetInt() == INDEX_NONE)
		{
			continue;
		}
		// Same composition as FAnimNode_WheelController: rotation offset then location offset, in component space.
		FTransform BoneTransform = ComponentPose.GetComponentSpaceTransform(BoneIndex);
		BoneTransform.SetRotation(FQuat(Wheel.RotOffset) * BoneTransform.GetRotation());
		BoneTransform.AddToTranslation(Wheel.LocOffset);
		ComponentPose.SetComponentSpaceTransform(BoneIndex, BoneTransform);
		bChanged = true;
	}

	if (bChanged)
	{
		FCSPose<FCompactPose>::ConvertComponentPosesToLocalPoses(ComponentPose, Output.Pose);
	}
	return true;
}

UGTVehicleAnimInstance::UGTVehicleAnimInstance(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
}

FAnimInstanceProxy* UGTVehicleAnimInstance::CreateAnimInstanceProxy()
{
	return new FGTVehicleAnimInstanceProxy(this);
}

void UGTVehicleAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy)
{
	delete InProxy;
}
