#include "Dressing/GTVegetationProbeComponent.h"

#include "Dressing/GTVegetationSubsystem.h"

#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "PhysicsEngine/PhysicsAsset.h"

UGTVegetationProbeComponent::UGTVegetationProbeComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick, before physics, with the other chassis forces
}

void UGTVegetationProbeComponent::MeasureBody(UPrimitiveComponent& Chassis)
{
	bMeasured = true;
	FBox Box(ForceInit);
	FString Source = TEXT("physics asset bodies");
	if (const USkeletalMeshComponent* Skeletal = Cast<USkeletalMeshComponent>(&Chassis))
	{
		if (UPhysicsAsset* Physics = Skeletal->GetPhysicsAsset())
		{
			Box = Physics->CalcAABB(Skeletal, FTransform::Identity);
		}
	}
	if (!Box.IsValid)
	{
		Box = Chassis.CalcBounds(FTransform::Identity).GetBox();
		Source = TEXT("component bounds");
	}
	const FVector Size = Box.IsValid ? Box.GetSize() : FVector::ZeroVector;
	if (Size.X < 150.0 || Size.X > 900.0 || Size.Y < 100.0 || Size.Y > 400.0)
	{
		// Not a car-sized box: the Range Rover's own numbers (447 x 186 x 179 cm, the mesh origin near the axle midpoint).
		Box = FBox(FVector(-230.0, -93.0, 20.0), FVector(230.0, 93.0, 179.0));
		Source = FString::Printf(TEXT("fallback (measured %s was not car-sized)"), *Size.ToCompactString());
	}
	LocalBodyBox = Box;
	MassKg = Chassis.IsSimulatingPhysics() ? Chassis.GetMass() : 0.f;
	if (MassKg <= 0.f)
	{
		MassKg = 2100.f;
	}
	UE_LOG(LogTemp, Display, TEXT("GTVEG probe on %s: body box %s .. %s cm (%s), %.0f kg"),
		*GetNameSafe(GetOwner()), *Box.Min.ToCompactString(), *Box.Max.ToCompactString(), *Source, MassKg);
}

void UGTVegetationProbeComponent::Update(float DeltaSeconds, UPrimitiveComponent& Chassis)
{
	LastForceN = FVector::ZeroVector;
	LastContacts = 0;
	UWorld* World = GetWorld();
	UGTVegetationSubsystem* Veg = World ? World->GetSubsystem<UGTVegetationSubsystem>() : nullptr;
	if (!Veg || !Veg->IsActive() || !Chassis.IsSimulatingPhysics())
	{
		return;
	}
	if (!bMeasured)
	{
		MeasureBody(Chassis);
	}
	FTransform CarTransform = Chassis.GetComponentTransform();
	CarTransform.SetScale3D(FVector::OneVector);
	LastForceN = Veg->ProbeCar(Chassis, CarTransform, LocalBodyBox, MassKg, DeltaSeconds, LastContacts);
	if (!LastForceN.IsNearlyZero())
	{
		Chassis.AddForce(LastForceN * 100.0, NAME_None, /*bAccelChange*/ false);   // at the centre of mass; N -> kg cm/s^2
	}
}
