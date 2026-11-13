#include "Vehicle/GTHullComponent.h"

#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTTractionComponent.h"

#include "ChaosVehicleWheel.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"

/** Water stage W1: 0 takes the body's push off and leaves only the wheels' drag, for the comparison the gate asks for. */
static TAutoConsoleVariable<int32> CVarWaterHull(
	TEXT("gt.Water.Hull"), 1,
	TEXT("1 the current pushes the car's body (UGTHullComponent), 0 only the wheels feel the water."));

/** Water stage W2: 0 takes the lift off and leaves the drag, so a drive can compare a car that floats with one that does not. */
static TAutoConsoleVariable<int32> CVarWaterBuoyancy(
	TEXT("gt.Water.Buoyancy"), 1,
	TEXT("1 the water lifts the car (UGTHullComponent's displacement), 0 no lift at all."));

UGTHullComponent::UGTHullComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick for a fixed order, after the traction
}

void UGTHullComponent::BeginPlay()
{
	Super::BeginPlay();
	// Stage W2: every buoyancy number is a fraction of the car's mass, and the plan keeps the mass out of itself: it
	// is read here, once, from the body that Chaos actually simulates.
	const USkeletalMeshComponent* Mesh = GetOwner() ? GetOwner()->FindComponentByClass<USkeletalMeshComponent>() : nullptr;
	BodyMassKg = Mesh ? Mesh->GetMass() : 0.f;
	const float BoxM3 = HullLengthM * HullWidthM * FMath::Max(0.1f, HullRoofM - HullKeelM);
	UE_LOG(LogTemp, Display, TEXT("UGTHullComponent: the body's mass is %.0f kg, %.1f m3 displaced sealed %.2f -> the keel floats %.2f m under; WS2 lid fill %.2f of a %.1f m3 box (the fill that displaces the lift's own volume is %.2f)"),
		BodyMassKg, HullVolumeM3, SealedFraction, BodyMassKg > 0.f ? (BodyMassKg / FMath::Max(1.f, WaterDensity * HullVolumeM3 * SealedFraction)) * FMath::Max(0.1f, HullRoofM - HullKeelM) : 0.f,
		LidFill, BoxM3, HullVolumeM3 * SealedFraction / FMath::Max(0.1f, BoxM3));
}

void UGTHullComponent::Update(float DeltaSeconds, const UChaosWheeledVehicleMovementComponent& Movement, const UGTTractionComponent& Traction)
{
	SubmergedHeightM = 0.f;
	LastWaterForce = FVector::ZeroVector;
	LastWaterForceN = 0.f;
	LastAreaM2 = 0.f;
	LastFlowMps = FVector2D::ZeroVector;
	bCapped = false;
	LiftN = 0.f;
	KeelDepthM = 0.f;
	bLiftCapped = false;
	if (BodyMassKg <= 0.f)
	{
		BodyMassKg = Movement.Mass;   // the fallback if the body had no mass yet at BeginPlay
	}
	// The line the keel floats on: mass = rho x V x sealed x (depth / (roof - keel)).
	const float KeelToRoofM = FMath::Max(0.1f, HullRoofM - HullKeelM);
	const float DisplacedKg = FMath::Max(1.f, WaterDensity * HullVolumeM3 * SealedFraction);
	PredictedNeutralKeelDepthM = (BodyMassKg / DisplacedKg) * KeelToRoofM;

	UWorld* World = GetWorld();
	UPrimitiveComponent* Body = Movement.UpdatedPrimitive;
	UGTWaterSubsystem* Water = World ? World->GetSubsystem<UGTWaterSubsystem>() : nullptr;
	LidVolumeM3 = 0.f;
	if (!Body || !Water || CVarWaterHull.GetValueOnGameThread() == 0)
	{
		return;
	}

	// The hull's bottom is the wheels' contact plane, in the car's own frame: a car sunk in mud or squatting on its
	// springs has its box lowered with it. With no wheel in contact the mesh's origin is that plane (the hubs sit at
	// 37.9 cm and the wheels are 38 cm, so the body's origin is at the tyres' bottom).
	const FTransform Frame = Body->GetComponentTransform();
	float BaseLocalZ = 0.f;
	int32 Contacts = 0;
	for (const FGTWheelTraction& Wheel : Traction.Wheels)
	{
		if (Wheel.bInContact)
		{
			BaseLocalZ += static_cast<float>(Frame.InverseTransformPosition(Wheel.ContactPoint).Z);
			++Contacts;
		}
	}
	BaseLocalZ = Contacts > 0 ? BaseLocalZ / Contacts : 0.f;

	const float HalfLengthCm = FMath::Max(10.f, HullLengthM * 100.f) * 0.5f;
	const float HalfWidthCm = FMath::Max(10.f, HullWidthM * 100.f) * 0.5f;
	const float FloorCm = HullFloorM * 100.f;
	const float RoofCm = FMath::Max(FloorCm + 10.f, HullRoofM * 100.f);

	const FVector2D Forward2D = FVector2D(Frame.GetUnitAxis(EAxis::X)).GetSafeNormal();

	struct FHullPush
	{
		FVector ForceN = FVector::ZeroVector;
		FVector At = FVector::ZeroVector;
	};
	FHullPush Pushes[5];
	int32 PushCount = 0;
	FVector SumN = FVector::ZeroVector;
	TArray<AGTWaterSheet*,TInlineAllocator<5>> ContactSheets;

	// Stage W2: the lift, a fifth of the volume at each sample, and its damping (the drag below has no vertical part).
	const bool bBuoyancy = CVarWaterBuoyancy.GetValueOnGameThread() != 0;
	const float KeelCm = HullKeelM * 100.f;
	const float ShareVolumeM3 = FMath::Max(0.f, HullVolumeM3) * SealedFraction * 0.2f;
	const float FloatSpringNPerM = WaterDensity * 9.8f * FMath::Max(0.f, HullVolumeM3) * SealedFraction / KeelToRoofM;
	const float DampingNsPerM = 2.f * LiftDampingRatio * FMath::Sqrt(FMath::Max(0.f, FloatSpringNPerM * BodyMassKg));
	float LiftEachN[5] = { 0.f, 0.f, 0.f, 0.f, 0.f };
	float DampEachN[5] = { 0.f, 0.f, 0.f, 0.f, 0.f };
	FVector LiftAt[5];
	int32 LiftCount = 0;
	float LiftSumN = 0.f;

	// Water stage W3: the one query answers kind Rut inside a mud patch's box - the few centimetres the bog's table
	// leaves standing in a rut. The hull ignores it, here and at the five samples below: rut water is narrower than the
	// hull and lies under the axle line, so a 4.4 x 1.9 m box taking drag, lift and a submerged height from it would be
	// a new force on the bog's already marginal crawl, not a hull in water. The wheels do read it (the traction).
	// A simulated muddy pond can cover the hull; legacy cosmetic rut water still cannot.
	const auto bHullWater = [](const FGTWaterSample& S) { return S.Kind == EGTWaterKind::Ford || S.bSimulatedMudWater; };

	// WS2: the free stream, read one hull length upstream of the car, is what the drag's Cd is defined against (see
	// FreeStreamM). Taken once a tick from the centre: the local reading gives the direction, the offset point the speed.
	FVector2D FreeStream = FVector2D::ZeroVector;
	bool bFreeStreamTaken = false;
	{
		const FVector Centre = Frame.TransformPosition(FVector(0.f, 0.f, BaseLocalZ));
		const FGTWaterSample At = Water->Sample(Centre);
		if (bHullWater(At) && !At.FlowCmPerS.IsNearlyZero() && FreeStreamM > 0.f)
		{
			const FVector2D Dir = At.FlowCmPerS.GetSafeNormal();
			const FVector2D UpstreamXY = FVector2D(Centre.X, Centre.Y) - Dir * (FreeStreamM * 100.f);
			const FGTWaterSample Upstream = Water->Sample(FVector(UpstreamXY.X, UpstreamXY.Y, Centre.Z));
			if (bHullWater(Upstream) && Upstream.DepthCm > 5.f)
			{
				FreeStream = Upstream.FlowCmPerS;
				bFreeStreamTaken = true;
			}
		}
	}

	const FVector2D LocalXY[5] = {
		FVector2D(HalfLengthCm, -HalfWidthCm), FVector2D(HalfLengthCm, HalfWidthCm),
		FVector2D(-HalfLengthCm, -HalfWidthCm), FVector2D(-HalfLengthCm, HalfWidthCm),
		FVector2D(0.f, 0.f)
	};
	for (int32 Index = 0; Index < 5; ++Index)
	{
		// The sample sits at the sill; the hull's bottom under it is the contact plane at that corner.
		const FVector At = Frame.TransformPosition(FVector(LocalXY[Index].X, LocalXY[Index].Y, BaseLocalZ + FloorCm));
		const FVector Bottom = Frame.TransformPosition(FVector(LocalXY[Index].X, LocalXY[Index].Y, BaseLocalZ));
		const FGTWaterSample Sample = Water->Sample(FVector(Bottom.X, Bottom.Y, Bottom.Z));
		if (!bHullWater(Sample))   // W3: no water, and rut water is not the hull's (see bHullWater)
		{
			continue;
		}
		const float HeightCm = FMath::Clamp(Sample.DepthCm, 0.f, RoofCm);
		const float HeightM = HeightCm * 0.01f;
		if(HeightCm>0)
			if(AGTWaterSheet* Sheet=Water->SheetAt(FVector2D(Bottom))) ContactSheets.AddUnique(Sheet);
		SubmergedHeightM = FMath::Max(SubmergedHeightM, HeightM);
		// Stage W2: how far the water stands over this corner's keel, and so how much of its fifth of the volume is
		// displacing. Pitch and roll put the deeper corners under more water and the lift at their own points, which
		// is the righting moment: no torque of our own is added.
		const float FreeKeelOverCm = Sample.SurfaceZCm - (static_cast<float>(Bottom.Z) + KeelCm);
		const float KeelOverCm = Sample.bSimulatedMudWater ? FMath::Min(FreeKeelOverCm,Sample.DepthCm) : FreeKeelOverCm;
		if (Index == 4)
		{
			LastFlowMps = Sample.FlowCmPerS * 0.01f;
			KeelDepthM = KeelOverCm * 0.01f;
		}
		if (bBuoyancy)
		{
			const float Fraction = FMath::Clamp(KeelOverCm / (KeelToRoofM * 100.f), 0.f, 1.f);
			if (Fraction > 0.f)
			{
				const FVector KeelPoint = FVector(At.X, At.Y, static_cast<float>(Bottom.Z) + KeelCm);
				const float UpVelMps = static_cast<float>(Body->GetPhysicsLinearVelocityAtPoint(KeelPoint).Z) * 0.01f;
				LiftEachN[LiftCount] = WaterDensity * 9.8f * ShareVolumeM3 * Fraction;
				DampEachN[LiftCount] = -DampingNsPerM * 0.2f * Fraction * UpVelMps;
				LiftAt[LiftCount] = KeelPoint;
				LiftSumN += LiftEachN[LiftCount];
				++LiftCount;
			}
		}
		if (HeightCm <= 0.f)
		{
			continue;
		}
		// The side that is in the water: the underbody counts for UnderbodyFill of itself, the body for all of itself.
		const float ProfileM = FMath::Min(HeightM, HullFloorM) * UnderbodyFill + FMath::Max(0.f, HeightM - HullFloorM);
		const FVector PointVel = Body->GetPhysicsLinearVelocityAtPoint(At);
		const FVector2D FlowHere = bFreeStreamTaken ? FreeStream : Sample.FlowCmPerS;
		const FVector Rel3 = (FVector(FlowHere.X, FlowHere.Y, 0.f) - FVector(PointVel.X, PointVel.Y, 0.f)) * 0.01f;   // m/s
		const float RelSpeed = static_cast<float>(Rel3.Size());
		if (RelSpeed < 0.01f)
		{
			continue;
		}
		const FVector2D RelDir = FVector2D(Rel3.X, Rel3.Y).GetSafeNormal();
		// The angle of the flow to the hull's own forward axis: broadside takes the long side, head on the front.
		const float Cos = Forward2D.IsNearlyZero() ? 0.f : FMath::Abs(static_cast<float>(FVector2D::DotProduct(RelDir, Forward2D)));
		const float Sin = FMath::Sqrt(FMath::Max(0.f, 1.f - Cos * Cos));
		const float AreaM2 = (HullLengthM * ProfileM * Sin + HullWidthM * ProfileM * Cos) * 0.2f;   // a fifth each: the five sum to the whole projected area
		LastAreaM2 += AreaM2;
		const FVector ForceN = 0.5f * WaterDensity * DragCd * AreaM2 * RelSpeed * Rel3;
		Pushes[PushCount].ForceN = ForceN;
		Pushes[PushCount].At = FVector(At.X, At.Y, static_cast<float>(Bottom.Z) + HeightCm * 0.5f);
		++PushCount;
		SumN += ForceN;
	}

	// Stage WS2: the car as a lid on the water field. The hull's box is stamped from its keel plane - which follows
	// the car's pitch and roll through the slope below - and each wheel in contact from its own contact point, its
	// footprint the tyre's width by its diameter and solid (a tyre is not 24 % anything). The biggest stamp on a cell
	// wins in the field, so a wheel inside the hull's box is not counted twice. The forces above are untouched: they
	// read the effective surface the field hands back, which is the level the car sits in.
	{
		const FVector Up = Frame.GetUnitAxis(EAxis::Z);
		FVector2D Slope = FVector2D::ZeroVector;
		if (FMath::Abs(Up.Z) > 0.1)
		{
			Slope = FVector2D(-Up.X / Up.Z, -Up.Y / Up.Z);
		}
		const FVector KeelCentre = Frame.TransformPosition(FVector(0.f, 0.f, BaseLocalZ + KeelCm));
		const FVector2D KeelXY(KeelCentre.X, KeelCentre.Y);
		// Leading corners can enter before the centre crosses the shoreline.
		// Stamp each contacted sheet once, including the dry-centre entry case.
		if(AGTWaterSheet* Sheet=Water->SheetAt(KeelXY)) ContactSheets.AddUnique(Sheet);
		for(AGTWaterSheet* Sheet:ContactSheets)
		{
			Sheet->StampLid(KeelXY, Forward2D, HalfLengthCm, HalfWidthCm, static_cast<float>(KeelCentre.Z), Slope,
				(HullRoofM - HullKeelM) * 100.f, FMath::Clamp(LidFill, 0.f, 1.f));
			LidVolumeM3 += Sheet->GetField().LidVolumeM3;
		}
		for (int32 Index = 0; Index < Traction.Wheels.Num(); ++Index)
		{
			const FGTWheelTraction& Wheel = Traction.Wheels[Index];
			if (!Wheel.bInContact)
			{
				continue;
			}
			const FVector2D ContactXY(Wheel.ContactPoint.X, Wheel.ContactPoint.Y);
			AGTWaterSheet* Sheet = Water->SheetAt(ContactXY);
			if (!Sheet)
			{
				continue;
			}
			const UChaosVehicleWheel* Setup = Movement.Wheels.IsValidIndex(Index) ? Movement.Wheels[Index].Get() : nullptr;
			const float RadiusCm = Setup ? Setup->GetWheelRadius() : 38.f;
			const float WidthCm = Setup ? Setup->WheelWidth : 25.f;
			Sheet->StampLid(ContactXY, Forward2D, RadiusCm, WidthCm * 0.5f, static_cast<float>(Wheel.ContactPoint.Z),
				FVector2D::ZeroVector, 2.f * RadiusCm, 1.f);
		}
	}

	// Stage W2: the lift goes on whether or not the current is pushing (a car parked in still water floats too), with
	// its own cap, through the same force path the drag uses.
	if (LiftCount > 0)
	{
		const float MaxLiftN = FMath::Max(1.f, FloatCapG * BodyMassKg * 9.8f);
		float LiftScale = 1.f;
		if (LiftSumN > MaxLiftN)
		{
			LiftScale = MaxLiftN / LiftSumN;
			bLiftCapped = true;
		}
		for (int32 Index = 0; Index < LiftCount; ++Index)
		{
			const float UpN = LiftEachN[Index] * LiftScale + DampEachN[Index];
			Body->AddForceAtLocation(FVector(0.0, 0.0, UpN * 100.0), LiftAt[Index]);   // a newton is 100 kg cm/s^2
		}
		LiftN = LiftSumN * LiftScale;
	}

	if (PushCount == 0)
	{
		return;
	}
	// The sim guard, as MaxRollingResistance is for the wheels: the whole push is capped at a multiple of the weight.
	const float MaxN = FMath::Max(1.f, MaxWaterForceG * Movement.Mass * 9.8f);
	const float SumMag = static_cast<float>(SumN.Size());
	float Scale = 1.f;
	if (SumMag > MaxN)
	{
		Scale = MaxN / SumMag;
		bCapped = true;
	}
	for (int32 Index = 0; Index < PushCount; ++Index)
	{
		// Chaos units are kg cm/s^2, so a newton is 100 of them (the traction's own forces go in the same way).
		Body->AddForceAtLocation(Pushes[Index].ForceN * Scale * 100.0, Pushes[Index].At);
	}
	LastWaterForce = SumN * Scale;
	LastWaterForceN = SumMag * Scale;
}
