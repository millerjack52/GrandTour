#include "Vehicle/GTConditionComponent.h"

#include "Vehicle/GTVehicleTuning.h"

namespace
{
	struct FRegionPart
	{
		EGTCarPart Part;
		float Scale;
	};

	// Which parts a region protects and how hard a hit there lands on each (ARCHITECTURE 6b table).
	TArray<FRegionPart> PartsForRegion(EGTDamageRegion Region)
	{
		switch (Region)
		{
		case EGTDamageRegion::Front:  return { {EGTCarPart::Engine, 0.6f}, {EGTCarPart::Radiator, 1.0f}, {EGTCarPart::Winch, 0.3f} };
		case EGTDamageRegion::Rear:   return { {EGTCarPart::FuelTank, 1.0f}, {EGTCarPart::Body, 0.5f} };
		case EGTDamageRegion::ArchFL: return { {EGTCarPart::SuspensionFL, 1.0f}, {EGTCarPart::TyreFL, 0.6f}, {EGTCarPart::Steering, 0.3f} };
		case EGTDamageRegion::ArchFR: return { {EGTCarPart::SuspensionFR, 1.0f}, {EGTCarPart::TyreFR, 0.6f}, {EGTCarPart::Steering, 0.3f} };
		case EGTDamageRegion::ArchRL: return { {EGTCarPart::SuspensionRL, 1.0f}, {EGTCarPart::TyreRL, 0.6f} };
		case EGTDamageRegion::ArchRR: return { {EGTCarPart::SuspensionRR, 1.0f}, {EGTCarPart::TyreRR, 0.6f} };
		case EGTDamageRegion::SideL:
		case EGTDamageRegion::SideR:  return { {EGTCarPart::Body, 1.0f} };
		case EGTDamageRegion::Roof:   return { {EGTCarPart::Body, 0.5f} };
		case EGTDamageRegion::Glass:  return { {EGTCarPart::Glass, 1.0f} };
		default:                      return {};
		}
	}
}

UGTConditionComponent::UGTConditionComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick
	Random.Initialize(0x6754);
	RepairAll();
}

EGTDamageRegion UGTConditionComponent::ResolveRegion(const FVector& P, const FVector& D)
{
	// Car space: X forward, Y right, Z up, origin on the ground under the body's centre. Numbers
	// follow the Range Rover blockout (body X -229..232, arches at X 160 and -115, belt at Z 115).
	// The outward hit direction picks the face first: a box-to-box contact point can sit on an
	// edge, and a frontal wall hit reported at the roof line must still count as Front.
	if (D.X > 0.6f)
	{
		return EGTDamageRegion::Front;
	}
	if (D.X < -0.6f)
	{
		return EGTDamageRegion::Rear;
	}
	if (FMath::Abs(D.Y) > 0.6f)
	{
		if (P.Z > 115.f && FMath::Abs(P.X) < 120.f)
		{
			return EGTDamageRegion::Glass;
		}
		if (FMath::Abs(P.X - 160.f) < 60.f)
		{
			return D.Y < 0.f ? EGTDamageRegion::ArchFL : EGTDamageRegion::ArchFR;
		}
		if (FMath::Abs(P.X + 115.f) < 60.f)
		{
			return D.Y < 0.f ? EGTDamageRegion::ArchRL : EGTDamageRegion::ArchRR;
		}
		return D.Y < 0.f ? EGTDamageRegion::SideL : EGTDamageRegion::SideR;
	}
	if (D.Z > 0.6f)
	{
		return EGTDamageRegion::Roof;
	}
	if (D.Z < -0.6f)
	{
		// Landing on the underside: the nearest corner's suspension takes it.
		return P.X > 0.f ? (P.Y < 0.f ? EGTDamageRegion::ArchFL : EGTDamageRegion::ArchFR)
		                 : (P.Y < 0.f ? EGTDamageRegion::ArchRL : EGTDamageRegion::ArchRR);
	}
	if (P.Z > 150.f)
	{
		return EGTDamageRegion::Roof;
	}
	if (P.Z > 115.f && FMath::Abs(P.X) < 120.f)
	{
		return EGTDamageRegion::Glass;
	}
	if (FMath::Abs(P.Y) > 60.f)
	{
		if (FMath::Abs(P.X - 160.f) < 60.f)
		{
			return P.Y < 0.f ? EGTDamageRegion::ArchFL : EGTDamageRegion::ArchFR;
		}
		if (FMath::Abs(P.X + 115.f) < 60.f)
		{
			return P.Y < 0.f ? EGTDamageRegion::ArchRL : EGTDamageRegion::ArchRR;
		}
	}
	if (P.X > 150.f)
	{
		return EGTDamageRegion::Front;
	}
	if (P.X < -150.f)
	{
		return EGTDamageRegion::Rear;
	}
	return P.Y < 0.f ? EGTDamageRegion::SideL : EGTDamageRegion::SideR;
}

void UGTConditionComponent::ApplyImpact(const FVector& LocalPosition, const FVector& LocalDirection, float DeltaV)
{
	if (DeltaV < MinDamageSpeed)
	{
		return;
	}
	const float Severity = FMath::Clamp((DeltaV - MinDamageSpeed) / FMath::Max(1.f, FullDamageSpeed - MinDamageSpeed), 0.f, 1.f);
	const EGTDamageRegion Region = ResolveRegion(LocalPosition, LocalDirection.GetSafeNormal());

	++TotalImpacts;
	LastImpactDeltaV = DeltaV;
	LastImpactRegion = Region;
	LastImpactLocalDirection = LocalDirection.GetSafeNormal();
	RegionHealth.Add(Region, FMath::Clamp(GetRegionHealth(Region) - Severity, 0.f, 1.f));
	++ImpactsVersion;

	for (const FRegionPart& Entry : PartsForRegion(Region))
	{
		DamagePart(Entry.Part, Severity * Entry.Scale);
	}

	// Dent list: merge into an existing dent within its radius, else add, dropping the shallowest when full.
	const float Depth = Severity * MaxDentDepth;
	const float Radius = 20.f + 40.f * Severity;
	for (FGTImpactRecord& Record : Impacts)
	{
		if (FVector::Dist(Record.LocalPosition, LocalPosition) < Record.Radius)
		{
			Record.Depth = FMath::Min(Record.Depth + Depth, MaxDentDepth);
			Record.Radius = FMath::Max(Record.Radius, Radius);
			return;
		}
	}
	if (Impacts.Num() >= MaxImpacts)
	{
		int32 Shallowest = 0;
		for (int32 Index = 1; Index < Impacts.Num(); ++Index)
		{
			if (Impacts[Index].Depth < Impacts[Shallowest].Depth)
			{
				Shallowest = Index;
			}
		}
		Impacts.RemoveAtSwap(Shallowest);
	}
	FGTImpactRecord NewRecord;
	NewRecord.LocalPosition = LocalPosition;
	NewRecord.LocalDirection = LocalDirection.GetSafeNormal();
	NewRecord.Radius = Radius;
	NewRecord.Depth = Depth;
	Impacts.Add(NewRecord);
}

float UGTConditionComponent::GetPartHealth(EGTCarPart Part) const
{
	const float* Health = PartHealth.Find(Part);
	return Health ? *Health : 1.f;
}

float UGTConditionComponent::GetRegionHealth(EGTDamageRegion Region) const
{
	const float* Health = RegionHealth.Find(Region);
	return Health ? *Health : 1.f;
}

void UGTConditionComponent::SetPartHealth(EGTCarPart Part, float Health)
{
	PartHealth.Add(Part, FMath::Clamp(Health, 0.f, 1.f));
}

void UGTConditionComponent::DamagePart(EGTCarPart Part, float Amount)
{
	SetPartHealth(Part, GetPartHealth(Part) - Amount);
}

float UGTConditionComponent::ApplyHazardDamage(FGameplayTag HazardTag, EGTCarPart Part, float Amount)
{
	const float* Resistance = HazardResistance.Find(HazardTag);
	const float Applied = FMath::Max(0.f, Amount) * (1.f - (Resistance ? FMath::Clamp(*Resistance, 0.f, 1.f) : 0.f));
	if (Applied > 0.f)
	{
		DamagePart(Part, Applied);
		HazardDamageTaken += Applied;
	}
	return Applied;
}

const TCHAR* UGTConditionComponent::RegionName(EGTDamageRegion Region)
{
	switch (Region)
	{
	case EGTDamageRegion::Front:  return TEXT("front");
	case EGTDamageRegion::Rear:   return TEXT("rear");
	case EGTDamageRegion::ArchFL: return TEXT("front-left arch");
	case EGTDamageRegion::ArchFR: return TEXT("front-right arch");
	case EGTDamageRegion::ArchRL: return TEXT("rear-left arch");
	case EGTDamageRegion::ArchRR: return TEXT("rear-right arch");
	case EGTDamageRegion::SideL:  return TEXT("left side");
	case EGTDamageRegion::SideR:  return TEXT("right side");
	case EGTDamageRegion::Roof:   return TEXT("roof");
	case EGTDamageRegion::Glass:  return TEXT("glass");
	default:                      return TEXT("body");
	}
}

bool UGTConditionComponent::IsRegionDamaged(EGTDamageRegion Region) const
{
	if (GetRegionHealth(Region) < 0.999f)
	{
		return true;
	}
	for (const FRegionPart& Entry : PartsForRegion(Region))
	{
		if (GetPartHealth(Entry.Part) < 0.999f)
		{
			return true;
		}
	}
	return false;
}

void UGTConditionComponent::RepairRegion(EGTDamageRegion Region, float Amount)
{
	for (const FRegionPart& Entry : PartsForRegion(Region))
	{
		SetPartHealth(Entry.Part, GetPartHealth(Entry.Part) + Amount);
	}
	RegionHealth.Add(Region, 1.f);
	const int32 Before = Impacts.Num();
	Impacts.RemoveAll([Region](const FGTImpactRecord& Record)
	{
		return ResolveRegion(Record.LocalPosition, Record.LocalDirection) == Region;
	});
	if (Impacts.Num() != Before)
	{
		++ImpactsVersion;
	}
	UE_LOG(LogTemp, Display, TEXT("UGTConditionComponent: repaired %s by %.2f, %d dents cleared"), RegionName(Region), Amount, Before - Impacts.Num());
}

void UGTConditionComponent::RepairAll()
{
	for (uint8 Index = 0; Index < static_cast<uint8>(EGTCarPart::Count); ++Index)
	{
		PartHealth.Add(static_cast<EGTCarPart>(Index), 1.f);
	}
	Impacts.Reset();
	RegionHealth.Reset();
	++ImpactsVersion;
	bMisfiring = false;
	MisfireTimer = 0.f;
}

void UGTConditionComponent::Update(float DeltaSeconds, float ThrottleInput, float EngineRPM, float MaxRPM)
{
	// Fuel: idle burn plus load, compressed by FuelUseScale; a holed tank leaks on top.
	const float Load = FMath::Clamp(ThrottleInput, 0.f, 1.f) * FMath::Clamp(MaxRPM > 0.f ? EngineRPM / MaxRPM : 0.f, 0.f, 1.f);
	float Litres = (IdleLitresPerHour + Load * FullLoadLitresPerHour) / 3600.f * FuelUseScale * DeltaSeconds;
	const float TankHealth = GetPartHealth(EGTCarPart::FuelTank);
	if (TankHealth < 0.5f)
	{
		Litres += LeakLitresPerSecond * ((0.5f - TankHealth) / 0.5f) * DeltaSeconds;
	}
	Litres = FMath::Min(Litres, FuelLitres);
	FuelLitres -= Litres;
	LitresUsed += Litres;
	bOutOfFuel = FuelLitres <= KINDA_SMALL_NUMBER;

	// A damaged radiator cooks the engine slowly.
	const float RadiatorHealth = GetPartHealth(EGTCarPart::Radiator);
	if (RadiatorHealth < 0.5f && ThrottleInput > 0.1f)
	{
		DamagePart(EGTCarPart::Engine, (0.5f - RadiatorHealth) * 0.02f * DeltaSeconds);
	}

	// Misfires below half engine health: short random torque cuts, more often as health drops.
	const float EngineHealth = GetPartHealth(EGTCarPart::Engine);
	if (MisfireTimer > 0.f)
	{
		MisfireTimer -= DeltaSeconds;
		bMisfiring = MisfireTimer > 0.f;
	}
	else if (EngineHealth < 0.5f && ThrottleInput > 0.1f)
	{
		const float PerSecond = (0.5f - EngineHealth) * 6.f;
		if (Random.FRand() < PerSecond * DeltaSeconds)
		{
			MisfireTimer = 0.15f;
			bMisfiring = true;
		}
	}
}

void UGTConditionComponent::UpdateFlooding(float DeltaSeconds, float FrontWaterDepthM)
{
	if (FrontWaterDepthM >= IntakeHeightM)
	{
		if (!bFlooded)
		{
			UE_LOG(LogTemp, Display, TEXT("UGTConditionComponent: engine flooded, %.2f m of water at the intake"), FrontWaterDepthM);
		}
		bFlooded = true;
		FloodTimer = FloodDrainSeconds;
	}
	else if (bFlooded)
	{
		FloodTimer -= DeltaSeconds;
		if (FloodTimer <= 0.f)
		{
			bFlooded = false;
		}
	}
}

void UGTConditionComponent::ModifyTuning(FGTVehicleTuning& Tuning) const
{
	const float EngineHealth = GetPartHealth(EGTCarPart::Engine);
	Tuning.TorqueScale *= (0.4f + 0.6f * EngineHealth) * (bMisfiring ? 0.1f : 1.f) * (bOutOfFuel ? 0.f : 1.f) * (bFlooded ? 0.f : 1.f);

	static const EGTCarPart Tyres[4] = { EGTCarPart::TyreFL, EGTCarPart::TyreFR, EGTCarPart::TyreRL, EGTCarPart::TyreRR };
	const int32 Count = FMath::Min(Tuning.Wheels.Num(), 4);
	for (int32 Index = 0; Index < Count; ++Index)
	{
		Tuning.Wheels[Index].FrictionScale *= 0.5f + 0.5f * GetPartHealth(Tyres[Index]);
	}

	// Damaged suspension on one side pulls the car that way (steer input positive = right).
	const float Left = 0.5f * (GetPartHealth(EGTCarPart::SuspensionFL) + GetPartHealth(EGTCarPart::SuspensionRL));
	const float Right = 0.5f * (GetPartHealth(EGTCarPart::SuspensionFR) + GetPartHealth(EGTCarPart::SuspensionRR));
	Tuning.SteeringBias += 0.25f * (Left - Right);
}
