#include "Vehicle/GTBodyStateComponent.h"

#include "Core/GTGameplayTags.h"
#include "HAL/IConsoleManager.h"
#include "Vehicle/GTTractionComponent.h"
#include "Terrain/GTLandscapeSurface.h"

static TAutoConsoleVariable<int32> CVarCarMud(
	TEXT("gt.Mud.CarMud"), 1,
	TEXT("MR2: 1 a muddy vehicle - tyres caked in mud, a splattered mud line rising with the sinkage, spin flinging mud up the arches, thrown blobs coating the body, wet mud drying lighter, water washing below its waterline, rain washing slowly (the body state and M_GT_Vehicle / M_GT_Tyre / M_GT_Glass); 0 the dirt and its flat sill gradient as before MR2."));

namespace
{
	const EGTDamageRegion AllRegions[] = {
		EGTDamageRegion::Front, EGTDamageRegion::Rear, EGTDamageRegion::ArchFL, EGTDamageRegion::ArchFR,
		EGTDamageRegion::ArchRL, EGTDamageRegion::ArchRR, EGTDamageRegion::SideL, EGTDamageRegion::SideR,
		EGTDamageRegion::Roof, EGTDamageRegion::Glass,
	};

	const TCHAR* ShortName(EGTDamageRegion Region)
	{
		switch (Region)
		{
		case EGTDamageRegion::Front:  return TEXT("F");
		case EGTDamageRegion::Rear:   return TEXT("R");
		case EGTDamageRegion::ArchFL: return TEXT("aFL");
		case EGTDamageRegion::ArchFR: return TEXT("aFR");
		case EGTDamageRegion::ArchRL: return TEXT("aRL");
		case EGTDamageRegion::ArchRR: return TEXT("aRR");
		case EGTDamageRegion::SideL:  return TEXT("sL");
		case EGTDamageRegion::SideR:  return TEXT("sR");
		case EGTDamageRegion::Roof:   return TEXT("roof");
		case EGTDamageRegion::Glass:  return TEXT("glass");
		default:                      return TEXT("?");
		}
	}

	bool IsMudSurface(const FGTWheelTraction& Wheel)
	{
		return Wheel.SurfaceTag == GTTags::Surface_Mud.GetTag() || Wheel.SurfaceTag == GTTags::Surface_Bog.GetTag();
	}

	constexpr float LineBucketSeconds = 0.25f;
}

UGTBodyStateComponent::UGTBodyStateComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick after traction
	for (int32 Index = 0; Index < LineBuckets; ++Index)
	{
		LineBucketId[Index] = -1000;
	}
}

bool UGTBodyStateComponent::IsCarMudEnabled()
{
	return CVarCarMud.GetValueOnGameThread() != 0;
}

void UGTBodyStateComponent::AddDirt(EGTDamageRegion Region, float Amount)
{
	if (Amount <= 0.f)
	{
		return;
	}
	float& Value = Dirt.FindOrAdd(Region);
	Value = FMath::Min(1.f, Value + Amount);
}

void UGTBodyStateComponent::SetDirtForTest(EGTDamageRegion Region, float Value)
{
	Dirt.FindOrAdd(Region) = FMath::Clamp(Value, 0.f, 1.f);
}

float UGTBodyStateComponent::GetDirt(EGTDamageRegion Region) const
{
	if (Region == EGTDamageRegion::None)
	{
		return 0.5f * GetAverageDirt();
	}
	const float* Value = Dirt.Find(Region);
	return Value ? *Value : 0.f;
}

float UGTBodyStateComponent::GetAverageDirt() const
{
	float Sum = 0.f;
	for (const EGTDamageRegion Region : AllRegions)
	{
		Sum += GetDirt(Region);
	}
	return Sum / UE_ARRAY_COUNT(AllRegions);
}

FVector2D UGTBodyStateComponent::RegionSpanCm(EGTDamageRegion Region)
{
	// Car space above the wheel bottoms, from the Range Rover blockout (sills about 35 cm, the belt 115, the roof 170-195).
	switch (Region)
	{
	case EGTDamageRegion::Front:  return FVector2D(25.f, 115.f);
	case EGTDamageRegion::Rear:   return FVector2D(25.f, 140.f);
	case EGTDamageRegion::ArchFL:
	case EGTDamageRegion::ArchFR:
	case EGTDamageRegion::ArchRL:
	case EGTDamageRegion::ArchRR: return FVector2D(30.f, 115.f);
	case EGTDamageRegion::SideL:
	case EGTDamageRegion::SideR:  return FVector2D(25.f, 150.f);
	case EGTDamageRegion::Roof:   return FVector2D(165.f, 200.f);
	case EGTDamageRegion::Glass:  return FVector2D(115.f, 175.f);
	default:                      return FVector2D(25.f, 150.f);
	}
}

float UGTBodyStateComponent::GetCoatAt(EGTDamageRegion Region, float HeightCm) const
{
	// The material's coat before its breakup: the region's coat up to the coat line, thinning over 60 cm above it (thrown splats
	// reach higher at lower density, about a third), and the washed band under the last waterline.
	const float Coat = GetDirt(Region);
	float Shown = HeightCm <= CoatLineCm ? Coat : Coat * 0.35f * FMath::Clamp(1.f - (HeightCm - CoatLineCm) / 60.f, 0.f, 1.f);
	if (HeightCm < WashCm)
	{
		Shown *= 1.f - WashAmount;
	}
	return Shown;
}

void UGTBodyStateComponent::Wash()
{
	Dirt.Reset();
	Wetness = 0.f;
	Snow = 0.f;
	MudLineCm = 0.f;
	CoatLineCm = 0.f;
	WashCm = 0.f;
	WashAmount = 0.f;
	MudWet = 0.f;
	for (float& Coat : TyreCoat)
	{
		Coat = 0.f;
	}
	for (float& Coat : FanCoat)
	{
		Coat = 0.f;
	}
	for (int32 Index = 0; Index < LineBuckets; ++Index)
	{
		LineBucketId[Index] = -1000;
		LineBucketMax[Index] = 0.f;
	}
}

void UGTBodyStateComponent::AddThrowHit(const FVector& LocalPoint, const FVector& LocalNormal, double VolumeCm3)
{
	if (!IsCarMudEnabled() || VolumeCm3 <= 0.0)
	{
		return;
	}
	// The outward normal of the face it hit is the direction from the car toward the blob: the face picks the region (an
	// underside hit goes to the nearest corner's arch).
	const EGTDamageRegion Region = UGTConditionComponent::ResolveRegion(LocalPoint, LocalNormal.GetSafeNormal());
	const float Amount = FMath::Clamp(static_cast<float>(VolumeCm3) * BlobHitCoatPerCm3, BlobHitMin, BlobHitMax);
	AddDirt(Region == EGTDamageRegion::None ? EGTDamageRegion::Roof : Region, Amount);
	MudWet = 1.f;
	++ThrowHits;
	GlassHits += Region == EGTDamageRegion::Glass ? 1 : 0;
}

void UGTBodyStateComponent::Update(float DeltaSeconds, const UGTTractionComponent& Traction, float ForwardSpeed)
{
	if (IsCarMudEnabled())
	{
		UpdateMud(DeltaSeconds, Traction, ForwardSpeed);
	}
	else
	{
		UpdateLegacy(DeltaSeconds, Traction, ForwardSpeed);
	}
}

void UGTBodyStateComponent::UpdateLegacy(float DeltaSeconds, const UGTTractionComponent& Traction, float ForwardSpeed)
{
	const float AbsSpeed = FMath::Abs(ForwardSpeed);
	const float SpeedFactor = FMath::Clamp(AbsSpeed / FMath::Max(1.f, SprayFullSpeed), 0.f, 1.f);
	// Wetness and snow are whole-body values: the strongest wheel sets them, not the sum of four.
	float MudSpray = 0.f;
	float SnowSpray = 0.f;

	for (int32 Index = 0; Index < Traction.Wheels.Num(); ++Index)
	{
		const FGTWheelTraction& Wheel = Traction.Wheels[Index];
		if (!Wheel.bInContact)
		{
			continue;
		}
		const float Spin = Wheel.bSlipping ? FMath::Clamp(Wheel.SlipMagnitude / 300.f, 0.f, 1.f) : 0.f;
		const float Spray = FMath::Min(1.f, SpeedFactor + WheelspinSprayScale * Spin);
		if (Spray <= KINDA_SMALL_NUMBER)
		{
			continue;
		}
		// Wheel order follows the setups: FL, FR, RL, RR.
		const bool bFront = Index < 2;
		const bool bLeft = (Index % 2) == 0;
		const EGTDamageRegion Arch = bFront ? (bLeft ? EGTDamageRegion::ArchFL : EGTDamageRegion::ArchFR)
		                                    : (bLeft ? EGTDamageRegion::ArchRL : EGTDamageRegion::ArchRR);
		const EGTDamageRegion Side = bLeft ? EGTDamageRegion::SideL : EGTDamageRegion::SideR;
		const EGTDamageRegion End = bFront ? EGTDamageRegion::Front : EGTDamageRegion::Rear;
		const float EndScale = bFront ? 0.15f : 0.3f;

		float DirtRate = 0.f;
		if (IsMudSurface(Wheel))
		{
			DirtRate = MudDirtRate;
			MudSpray = FMath::Max(MudSpray, Spray);
		}
		else if (Wheel.SurfaceTag == GTTags::Surface_Dirt.GetTag() || Wheel.SurfaceTag == GTTags::Surface_Sand.GetTag())
		{
			DirtRate = DustDirtRate;
		}
		else if (Wheel.SurfaceTag == GTTags::Surface_Snow.GetTag())
		{
			SnowSpray = FMath::Max(SnowSpray, Spray);
		}
		if (DirtRate > 0.f)
		{
			// The arch takes the full amount; a side collects from two wheels, so its share stays below one arch's.
			const float Amount = DirtRate * Spray * DeltaSeconds;
			AddDirt(Arch, Amount);
			AddDirt(Side, 0.35f * Amount);
			AddDirt(End, EndScale * Amount);
			if (AbsSpeed > RoofSpraySpeed)
			{
				AddDirt(EGTDamageRegion::Roof, 0.05f * Amount);
			}
			if (bFront)
			{
				AddDirt(EGTDamageRegion::Glass, 0.1f * Amount);   // mud throw-up on the windscreen
			}
		}
	}

	Wetness += (MudWetRate * MudSpray + SnowWetRate * SnowSpray) * DeltaSeconds;
	Snow += SnowRate * SnowSpray * DeltaSeconds;
	if (MudSpray <= 0.f && SnowSpray <= 0.f)
	{
		Wetness -= DryRate * DeltaSeconds;
	}
	// The global surface wetness (rain, later) is a floor: a car in the rain never dries.
	Wetness = FMath::Clamp(Wetness, FMath::Clamp(Traction.Wetness, 0.f, 1.f), 1.f);
	Snow = FMath::Clamp(Snow - MeltRate * DeltaSeconds, 0.f, 1.f);
	MaxWetness = FMath::Max(MaxWetness, Wetness);
}

void UGTBodyStateComponent::UpdateMud(float DeltaSeconds, const UGTTractionComponent& Traction, float ForwardSpeed)
{
	const float Dt = FMath::Max(0.f, DeltaSeconds);
	Clock += Dt;
	const float AbsSpeed = FMath::Abs(ForwardSpeed);
	const float SpeedFactor = FMath::Clamp(AbsSpeed / FMath::Max(1.f, SprayFullSpeed), 0.f, 1.f);
	const float MudSpeed = FMath::Clamp(AbsSpeed / FMath::Max(1.f, MudFullSpeed), 0.f, 1.f);
	const int32 NumWheels = Traction.Wheels.Num();
	if (TyreCoat.Num() != NumWheels)
	{
		TyreCoat.SetNumZeroed(NumWheels);
	}
	if (FanCoat.Num() != NumWheels)
	{
		FanCoat.SetNumZeroed(NumWheels);
		FanDir.Init(1.f, NumWheels);
		FanSide.Init(0.f, NumWheels);
	}
	float MudSpray = 0.f;
	float SnowSpray = 0.f;
	bool bMudLaid = false;
	bool bDustLaid = false;
	float LineNow = 0.f;
	float WaterCm = 0.f;
	float Laid = 0.f;
	const float CakeStep = 1.f - FMath::Exp(-Dt / FMath::Max(0.01f, TyreCoatSeconds));

	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		const FGTWheelTraction& Wheel = Traction.Wheels[Index];
		float& Tyre = TyreCoat[Index];
		const auto Surface = Wheel.bInContact ? AGTLandscapeSurface::QuerySurface(this,FVector2D(Wheel.ContactPoint)) : FGTLandscapeSurfaceSample();
		const bool bLandscapeMud = Surface.bAuthored && !Surface.bGranularResponse && Surface.SinkageCapCm > .1f;
		const float Pickup = bLandscapeMud ? FMath::SmoothStep(.1f,8.f,Surface.SinkageCapCm)
			* FMath::Lerp(.25f,1.f,Surface.Wetness)
			* FMath::Lerp(1.f,FMath::SmoothStep(.12f,.75f,Surface.Disturbance),Surface.GrassCover) : 1.f;
		const float WheelWaterCm = Wheel.bInContact ? FMath::Max(0.f, Wheel.WaterDepthM) * 100.f : 0.f;
		// A ford's water washes; a bog's rut water is slurry and coats like the mud round it.
		const bool bWashing = !Wheel.bRutWater && WheelWaterCm > WashDepthCm;
		if (!bWashing)
		{
			Tyre = FMath::Max(Tyre, FMath::Clamp(Wheel.MudLoad, 0.f, 1.f));   // MR1's carried load keeps the tyre caked
		}
		if (!Wheel.bInContact)
		{
			continue;
		}
		const float Spin = Wheel.bSlipping ? FMath::Clamp(Wheel.SlipMagnitude / 300.f, 0.f, 1.f) : 0.f;
		const float Spray = FMath::Min(1.f, SpeedFactor + WheelspinSprayScale * Spin);
		if (bWashing)
		{
			WaterCm = FMath::Max(WaterCm, WheelWaterCm);
		}
		// What surrounds the tyre above its bottom: the sinkage, or the water over the contact (UGTWaterSubsystem measures it from
		// the sunk contact, so it already holds the sinkage: a rut's water sits in the rut the tyre made). The deeper of the two.
		const float VisualSink = bLandscapeMud ? FMath::Max(0.f,-Surface.SurfaceDeltaCm) : 0.f;
		const float Medium = FMath::Max3(FMath::Max(0.f, Wheel.Sinkage) * 100.f, WheelWaterCm,VisualSink);
		LineNow = FMath::Max(LineNow, Medium + MudLineBaseCm + (Spin > MudLineSpinShare ? MudLineSpinCm : 0.f));
		// Wheel order follows the setups: FL, FR, RL, RR.
		const bool bFront = Index < 2;
		const bool bLeft = (Index % 2) == 0;
		const EGTDamageRegion Arch = bFront ? (bLeft ? EGTDamageRegion::ArchFL : EGTDamageRegion::ArchFR)
		                                    : (bLeft ? EGTDamageRegion::ArchRL : EGTDamageRegion::ArchRR);
		const EGTDamageRegion Side = bLeft ? EGTDamageRegion::SideL : EGTDamageRegion::SideR;
		const EGTDamageRegion End = bFront ? EGTDamageRegion::Front : EGTDamageRegion::Rear;
		// Mud is the Mud or Bog surface (a bog's patch, or an old mud lane). Not bInMudPatch alone: a ford's riverbed is a profiled
		// patch the traction flags too, on its Dirt bed, and it re-coated the car on the way out of the water (the first ford run:
		// the washed band back to 0, the tyres to 1).
		if ((IsMudSurface(Wheel) || bLandscapeMud) && !bWashing)
		{
			MudSpray = FMath::Max(MudSpray, Spray);
			bMudLaid = true;
			// Rotation exposes fresh tread. A stationary tyre no longer coats its entire circumference.
			const float Turn = FMath::SmoothStep(2.f,100.f,FMath::Abs(Wheel.TreadCmPerS));
			Tyre += FMath::Max(0.f,Pickup-Tyre) * CakeStep * Turn;
			const float Sink = Pickup * (0.3f + 0.7f * FMath::Clamp(bLandscapeMud
				? VisualSink/FMath::Max(1.f,Surface.SinkageCapCm) : Wheel.SinkageFraction, 0.f, 1.f));
			const float Rolled = MudSpeed * Sink;
			Laid = FMath::Max(Laid, FMath::Min(1.f, Rolled + Spin));
			// The sills and bumpers by speed x sinkage (two wheels share each), the arch by that and by spin.
			AddDirt(Side, 0.5f * SillMudRate * Rolled * Dt);
			AddDirt(End, 0.5f * BumperMudRate * Rolled * Dt);
			AddDirt(Arch, ArchMudRate * (Rolled + Spin) * Dt);
			// Spin flings mud by axle: the front wheels onto the front bumper and front wings, the rears onto the rear.
			if (Spin > 0.f)
			{
				AddDirt(End, FlingRate * Spin * Dt);
				AddDirt(Arch, FlingRate * Spin * Dt);
			}
			// The belly dragging in deep mud: the underside and the sills.
			if (Wheel.Sinkage > Traction.AxleClearanceM)
			{
				AddDirt(Side, 0.5f * BellyMudRate * Dt);
			}
			// MR2b: this wheel's own spray fan, by its spin and by its speed x sinkage. The tread throws the way its surface moves
			// (TreadCmPerS, the wheel's own omega x radius), so a forward spin, rolling forward and braking forward all throw behind
			// the arch, a backward spin or rolling backward in front (the slip's own sign would turn a braking wheel's fan forward:
			// its slip is negative while its tread still moves forward). The spin is the tread's speed over the ground's, either way
			// (braking adds none). The side is a memory of where the mud went, weighted by how much was thrown (FanSideRate), so a
			// moment's wiggle does not turn a fan; FanDir is its sign. (Holding the brake at a stop is reverse: a car parked that way
			// in a bog spins its wheels backward and its fans turn forward, rightly.)
			const float Tread = Wheel.TreadCmPerS;
			const float FanSpin = Wheel.bSlipping ? FMath::Clamp((FMath::Abs(Tread) - AbsSpeed) / 300.f, 0.f, 1.f) : 0.f;
			const float Thrown = FanSpinRate * FanSpin + FanRollRate * Rolled;
			FanCoat[Index] = FMath::Min(1.f, FanCoat[Index] + Thrown * Dt);
			if (FMath::Abs(Tread) > 10.f && Thrown > 0.f)
			{
				FanSide[Index] = FMath::Clamp(FanSide[Index] + (Tread >= 0.f ? 1.f : -1.f) * FanSideRate * Thrown * Dt, -1.f, 1.f);
				FanDir[Index] = FanSide[Index] >= 0.f ? 1.f : -1.f;
			}
		}
		else if ((Wheel.SurfaceTag == GTTags::Surface_Dirt.GetTag() || Wheel.SurfaceTag == GTTags::Surface_Sand.GetTag()) && Spray > KINDA_SMALL_NUMBER && !bWashing)
		{
			// Dust as before MR2, but the windscreen takes nothing (it is coated by throw hits only).
			const float Amount = DustDirtRate * Spray * Dt;
			AddDirt(Arch, Amount);
			AddDirt(Side, 0.35f * Amount);
			AddDirt(End, (bFront ? 0.15f : 0.3f) * Amount);
			if (AbsSpeed > RoofSpraySpeed)
			{
				AddDirt(EGTDamageRegion::Roof, 0.05f * Amount);
			}
			bDustLaid = true;
		}
		else if (Wheel.SurfaceTag == GTTags::Surface_Snow.GetTag())
		{
			SnowSpray = FMath::Max(SnowSpray, Spray);
		}
		if (bWashing)
		{
			Tyre -= TyreWashRate * Dt;
		}
		Tyre = FMath::Clamp(Tyre - RainWashRate * FMath::Clamp(Rain, 0.f, 1.f) * Dt, 0.f, 1.f);
	}

	// The mud line: the most over the last MudLineWindowS, in buckets of a quarter second.
	const int64 Bucket = static_cast<int64>(FMath::FloorToDouble(Clock / LineBucketSeconds));
	const int32 Slot = static_cast<int32>(Bucket % LineBuckets);
	if (LineBucketId[Slot] != Bucket)
	{
		LineBucketId[Slot] = Bucket;
		LineBucketMax[Slot] = 0.f;
	}
	LineBucketMax[Slot] = FMath::Max(LineBucketMax[Slot], LineNow);
	const int64 Window = FMath::Max<int64>(1, FMath::RoundToInt(MudLineWindowS / LineBucketSeconds));
	MudLineCm = 0.f;
	for (int32 Index = 0; Index < LineBuckets; ++Index)
	{
		if (Bucket - LineBucketId[Index] < FMath::Min<int64>(Window, LineBuckets))
		{
			MudLineCm = FMath::Max(MudLineCm, LineBucketMax[Index]);
		}
	}
	if (bMudLaid)
	{
		CoatLineCm = FMath::Max(CoatLineCm, MudLineCm);
		MudWet = 1.f;
		// Fresh mud thrown at speed or by spin fills a washed band back in (standing in mud does not).
		WashAmount = FMath::Max(0.f, WashAmount - WashRefillRate * Laid * Dt);
	}
	if (bDustLaid)
	{
		CoatLineCm = FMath::Max(CoatLineCm, DustLineCm);
	}

	// Water washes below its waterline: the band (WashCm, WashAmount) for the material, and a region wholly under it.
	if (WaterCm > WashDepthCm)
	{
		const float Rate = AbsSpeed > WashMovingSpeed ? WashMovingRate : WashStillRate;
		if (WaterCm > WashCm)
		{
			WashAmount = WashCm > 0.f ? WashAmount * WashCm / WaterCm : 0.f;
			WashCm = WaterCm;
		}
		WashAmount = FMath::Min(1.f, WashAmount + Rate * Dt);
		for (const EGTDamageRegion Region : AllRegions)
		{
			if (RegionSpanCm(Region).Y <= WaterCm)
			{
				if (float* Value = Dirt.Find(Region))
				{
					*Value = FMath::Max(0.f, *Value - Rate * Dt);
				}
			}
		}
		// MR2b: a fan washes with its arch (wholly under the water); below the waterline the material's washed band clears its droplets.
		for (int32 Index = 0; Index < FanCoat.Num(); ++Index)
		{
			const bool bFront = Index < 2;
			const bool bLeft = (Index % 2) == 0;
			const EGTDamageRegion Arch = bFront ? (bLeft ? EGTDamageRegion::ArchFL : EGTDamageRegion::ArchFR)
			                                    : (bLeft ? EGTDamageRegion::ArchRL : EGTDamageRegion::ArchRR);
			if (RegionSpanCm(Arch).Y <= WaterCm)
			{
				FanCoat[Index] = FMath::Max(0.f, FanCoat[Index] - Rate * Dt);
			}
		}
	}
	// Rain washes everything slowly.
	if (Rain > 0.f)
	{
		const float Washed = RainWashRate * FMath::Clamp(Rain, 0.f, 1.f) * Dt;
		for (TPair<EGTDamageRegion, float>& Pair : Dirt)
		{
			Pair.Value = FMath::Max(0.f, Pair.Value - Washed);
		}
		for (float& Coat : FanCoat)
		{
			Coat = FMath::Max(0.f, Coat - Washed);
		}
	}
	// Fresh mud is wet; it dries over MudDrySeconds, never below the weather's wetness.
	if (!bMudLaid)
	{
		MudWet -= Dt / FMath::Max(1.f, MudDrySeconds);
	}
	MudWet = FMath::Clamp(MudWet, FMath::Clamp(Traction.Wetness, 0.f, 1.f), 1.f);

	Wetness += (MudWetRate * MudSpray + SnowWetRate * SnowSpray) * Dt;
	Snow += SnowRate * SnowSpray * Dt;
	if (MudSpray <= 0.f && SnowSpray <= 0.f)
	{
		Wetness -= DryRate * Dt;
	}
	Wetness = FMath::Clamp(Wetness, FMath::Clamp(Traction.Wetness, 0.f, 1.f), 1.f);
	Snow = FMath::Clamp(Snow - MeltRate * Dt, 0.f, 1.f);
	MaxWetness = FMath::Max(MaxWetness, Wetness);
}

FString UGTBodyStateComponent::Describe() const
{
	FString Result = FString::Printf(TEXT("wet=%.2f snow=%.2f dirt:"), Wetness, Snow);
	for (const EGTDamageRegion Region : AllRegions)
	{
		Result += FString::Printf(TEXT(" %s=%.2f"), ShortName(Region), GetDirt(Region));
	}
	if (IsCarMudEnabled())
	{
		Result += FString::Printf(TEXT(" | mud line %.0f coat line %.0f wash %.0f cm @%.2f mudwet %.2f tyres"), MudLineCm, CoatLineCm, WashCm, WashAmount, MudWet);
		for (const float Coat : TyreCoat)
		{
			Result += FString::Printf(TEXT(" %.2f"), Coat);
		}
		Result += TEXT(" fans");
		for (int32 Index = 0; Index < FanCoat.Num(); ++Index)
		{
			Result += FString::Printf(TEXT(" %.2f%s"), FanCoat[Index], FanDir.IsValidIndex(Index) && FanDir[Index] < 0.f ? TEXT("f") : TEXT("b"));
		}
		Result += FString::Printf(TEXT(" hits %d (glass %d)"), ThrowHits, GlassHits);
	}
	return Result;
}
