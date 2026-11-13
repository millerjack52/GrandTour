#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GTVegetationProbeComponent.generated.h"

class UPrimitiveComponent;

/**
 * Leg dressing LD5 (docs/LEG_DRESSING_PLAN.md): the car's side of the soft vegetation physics. AGTCarPawn::Tick calls
 * Update once per frame before physics (the pawn puts every chassis force on there; the project runs one physics step per
 * frame, no async physics). It hands UGTVegetationSubsystem the car's footprint OBB - the chassis' body bounds in the
 * component frame (the physics asset's bodies, measured once; the subsystem adds the 0.3 m pad) - and puts the resist
 * force it gets back on the chassis at the centre of mass. Nothing to push (no soft vegetation, or gt.Look.Dressing 0):
 * returns at once.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTVegetationProbeComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTVegetationProbeComponent();

	/** One probe against the vegetation index, the resist force applied to Chassis. */
	void Update(float DeltaSeconds, UPrimitiveComponent& Chassis);

	/** The body bounds the footprint is made from (component space, unpadded); invalid before the first Update. */
	const FBox& GetLocalBodyBox() const { return LocalBodyBox; }
	FVector GetLastForceN() const { return LastForceN; }
	int32 GetLastContacts() const { return LastContacts; }
	float GetMassKg() const { return MassKg; }

private:
	void MeasureBody(UPrimitiveComponent& Chassis);

	FBox LocalBodyBox = FBox(ForceInit);
	bool bMeasured = false;
	float MassKg = 0.f;
	FVector LastForceN = FVector::ZeroVector;
	int32 LastContacts = 0;
};
