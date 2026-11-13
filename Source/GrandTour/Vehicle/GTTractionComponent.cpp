#include "Vehicle/GTTractionComponent.h"

#include "Core/GTGameplayTags.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "Terrain/GTTrackPaintSubsystem.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTVehicleTuning.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTHullComponent.h"
#include "Vehicle/GTWaterDrag.h"
#include "Terrain/GTGravelStones.h"   // Deformable gravel DG1
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTLandscapeSurface.h"
#include "ChaosVehicleWheel.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

/** RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): 0 takes the outside-a-patch cap off the visible sinking, as before section 52. */
static TAutoConsoleVariable<int32> CVarMudSinkCap(
	TEXT("gt.Mud.SinkCap"), 1,
	TEXT("1 outside every mud patch box the wheel's visible sinking (the Chaos radius shrink) is capped at OutsidePatchSinkCapM and rises back at VisibleSinkRiseRate per metre; 0 it follows the raw sinkage everywhere (before section 52)."));

/** RIVERBED S2, diagnostic: the ford diagnostic's bog_right_noramp run sets 1000 to measure the ledge the ramp takes away. */
static TAutoConsoleVariable<float> CVarMudSinkRiseRate(
	TEXT("gt.Mud.SinkRiseRate"), -1.f,
	TEXT("At 0 or more it replaces VisibleSinkRiseRate (metres of visible sinkage per metre of ground on the way out of a mud patch box); -1 (default) uses the property."));

/** LM3b (docs/LIVING_MUD_PLAN.md LM3b housekeeping 1), the snow feel's two tuning numbers, for the drive check's trials. */
static TAutoConsoleVariable<float> CVarSnowPlough(
	TEXT("gt.Snow.Plough"), -1.f,
	TEXT("At 0 or more it replaces the snow patch's SnowPlough (the uncut snow ahead's plough drag coefficient); -1 (default) uses the patch's."));
static TAutoConsoleVariable<float> CVarSnowBellyDrag(
	TEXT("gt.Snow.BellyDrag"), -1.f,
	TEXT("At 0 or more it replaces the snow patch's SnowBellyDrag (the scale on the belly's drag in snow, BellyDragPerMetre x the snow over its underside); -1 (default) uses the patch's."));

UGTTractionComponent::UGTTractionComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick for a fixed order
}

void UGTTractionComponent::PatchSinkage(float BaseRate, float BaseCap, float WetSink, float RateScale, float CapScale, float SoftSinkScale, float& OutRate, float& OutCap)
{
	// MR4: the order of the products before MR4 (base x wet x variant), the soft scale last, so a scale of 1 changes no bit.
	OutRate = BaseRate * WetSink * RateScale * SoftSinkScale;
	OutCap = BaseCap * WetSink * CapScale * SoftSinkScale;
}

void UGTTractionComponent::PatchMediumFlags(bool bInContact, bool bInProfiledPatch, uint8 Medium, bool& bOutSnow, bool& bOutGravel)
{
	const bool bIn = bInContact && bInProfiledPatch;
	bOutSnow = bIn && Medium == static_cast<uint8>(EGTDeformMedium::Snow);
	bOutGravel = bIn && Medium == static_cast<uint8>(EGTDeformMedium::Gravel);
}

float UGTTractionComponent::StepMudLoad(float Load, const FGTMudLoadStep& Step, float Rate, float ShedHalfM, float WashHalfM, float WashDepthM)
{
	if (!Step.bInContact)
	{
		return Load;
	}
	if (Step.bInSnowPatch)
	{
		return 0.f;
	}
	// MudRunner MR2: a ford's water over its riverbed patch washes the load (it rose there before MR2); a bog's rut water does not.
	const bool bWashing = Step.WaterDepthM > WashDepthM && !Step.bRutWater;
	if (Step.bInMudPatch && !bWashing)
	{
		const float Rise = FMath::Max(0.f, Rate) * (0.5f + FMath::Clamp(Step.SinkageFraction, 0.f, 1.f)) * (1.f + FMath::Clamp(Step.SlipShare, 0.f, 1.f));
		return FMath::Clamp(Load + Rise * FMath::Max(0.f, Step.DeltaSeconds), 0.f, 1.f);
	}
	const float HalfM = Step.WaterDepthM > WashDepthM ? WashHalfM : ShedHalfM;
	if (HalfM <= 0.f || Step.DistanceCm <= 0.f)
	{
		return Load;
	}
	return Load * FMath::Pow(0.5f, Step.DistanceCm / (HalfM * 100.f));
}

void UGTTractionComponent::Update(float DeltaSeconds, const UChaosWheeledVehicleMovementComponent& Movement, float ForwardSpeed)
{
	const int32 NumWheels = Movement.WheelSetups.Num();
	if (Wheels.Num() != NumWheels)
	{
		Wheels.SetNum(NumWheels);
	}
	const float AbsSpeed = FMath::Abs(ForwardSpeed);
	int32 SunkWheels = 0;
	int32 SpinningWheels = 0;
	// LM3b: the row a tyre's own sinkage rolls at inside a snow patch (the Dirt row), looked up once.
	if (!bSnowBaseLooked)
	{
		bSnowBaseLooked = true;
		SnowBase = SnowBaseRow.IsNull() ? nullptr : SnowBaseRow.LoadSynchronous();
		if (!SnowBase && !SnowBaseRow.IsNull())
		{
			UE_LOG(LogTemp, Warning, TEXT("UGTTractionComponent: SnowBaseRow %s missing; a tyre in a snow patch rolls at its contact's own row"), *SnowBaseRow.ToString());
		}
	}

	// The tyre load (stage 1). Chaos 5.8 holds the car up with a per-wheel suspension constraint (a quarter of the
	// spring rate as PBD stiffness, ChaosWheeledVehicleMovementComponent CreateVehicle) and never applies the force
	// model's spring; that spring, rate x displacement, is what it presses the tyre in with (WheelLoadRatio 1 on our
	// wheels) and what it reports as SpringForce. The constraint settles where the virtual spring reads about 69 % of
	// the weight, so the springs are scaled here so the wheels in contact carry the car: the true load per wheel, the
	// weight transfer kept. The same factor goes to Chaos through the friction multiplier (LoadCorrection).
	float SpringSum = 0.f;
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		FGTWheelTraction& Wheel = Wheels[Index];
		const FWheelStatus& Status = Movement.GetWheelState(Index);
		const float RawSpring = Status.bInContact ? FMath::Max(0.f, Status.SpringForce) : 0.f;
		Wheel.SpringForce = FMath::FInterpTo(Wheel.SpringForce, RawSpring, DeltaSeconds, LoadFilterRate);
		if (Status.bInContact)
		{
			SpringSum += Wheel.SpringForce;
		}
	}
	const float Weight = Movement.Mass * 980.f;
	// 2026-09-22 (docs/VEHICLE_BUILD_SYSTEM.md section 49, W2's flag "no grip cut when wading"): the target is the
	// weight less the hull's lift, so buoyancy takes load (and the grip that follows it) off the tyres. It was the dry
	// weight, which normalised the lift away: the loads summed to 20580 N at forda with 2478 N of lift. The hull ticks
	// after the traction, so this is last tick's lift (newtons; x100 to Chaos units). No hull, no lift: on land nothing changes.
	if (!bHullLooked)
	{
		Hull = GetOwner() ? GetOwner()->FindComponentByClass<UGTHullComponent>() : nullptr;
		bHullLooked = true;
	}
	const float LiftChaos = Hull ? FMath::Max(0.f, Hull->LiftN) * 100.f : 0.f;
	// The springs read a third of the weight or less for a second after a drop, so the clamp is generous.
	LoadCorrection = SpringSum > Weight * 0.05f ? FMath::Clamp((Weight - LiftChaos) / SpringSum, 0.5f, 5.f) : 1.f;

	// Water and your own ruts are read at each wheel's contact point (the rut just ahead, so a wheel does not read the
	// stamp it is laying this tick).
	UWorld* World = GetWorld();
	const UGTTrackPaintSubsystem* Paint = World ? World->GetSubsystem<UGTTrackPaintSubsystem>() : nullptr;
	UGTMudSubsystem* Mud = World ? World->GetSubsystem<UGTMudSubsystem>() : nullptr;
	// Water stage W1: the one water query. Depth is what DepthCmAt gave; the current beside it is new.
	const UGTWaterSubsystem* Water = World ? World->GetSubsystem<UGTWaterSubsystem>() : nullptr;
	// Stopped, the rut that matters is the one the car is about to drive into: fresh mud ahead, its own channel behind
	// when the drivetrain is in reverse (backing into your ruts is the way out of a dead stop).
	FVector Ahead = FVector::ZeroVector;
	FVector2D Forward2D = FVector2D::ZeroVector;
	FVector2D Right2D = FVector2D::ZeroVector;
	float Speed2D = 0.f;
	if (Movement.UpdatedPrimitive)
	{
		const FVector Velocity2D = FVector::VectorPlaneProject(Movement.UpdatedPrimitive->GetComponentVelocity(), FVector::UpVector);
		Speed2D = Velocity2D.Size();
		if (Speed2D > RutReadSpeed)
		{
			Ahead = Velocity2D.GetSafeNormal();
		}
		else
		{
			const UGTDrivetrainComponent* Train = GetOwner() ? GetOwner()->FindComponentByClass<UGTDrivetrainComponent>() : nullptr;
			Ahead = Movement.UpdatedPrimitive->GetForwardVector().GetSafeNormal2D() * ((Train && Train->IsReversing()) ? -1.f : 1.f);
		}
		const FVector Fwd3 = Movement.UpdatedPrimitive->GetForwardVector();
		Forward2D = FVector2D(Fwd3.X, Fwd3.Y).GetSafeNormal();
		Right2D = FVector2D(-Forward2D.Y, Forward2D.X);
	}
	const FVector2D Ahead2D(Ahead.X, Ahead.Y);
	// Stage F, the tread: the rolled distance per wheel. Chaos asserts inside GetRotationAngularVelocity when the async
	// output is missing, so the output is checked first (as UGTDrivetrainComponent does); Movement is const here only
	// because nothing else in this component writes it, and PhysicsVehicleOutput() has no const accessor.
	const bool bWheelOutput = const_cast<UChaosWheeledVehicleMovementComponent&>(Movement).PhysicsVehicleOutput().IsValid();
	// The rut hold's push fades in over the rut read speed: a parked car is not shoved about by the wall ahead of a turned wheel.
	const float HoldFade = FMath::Clamp(Speed2D / FMath::Max(1.f, RutReadSpeed), 0.f, 1.f);
	// LM2a, the throw: the drive's direction, so a wheel spinning backward in reverse throws and a locked wheel does not.
	const UGTDrivetrainComponent* ThrowTrain = GetOwner() ? GetOwner()->FindComponentByClass<UGTDrivetrainComponent>() : nullptr;
	const float DriveSign = (ThrowTrain && ThrowTrain->IsReversing()) ? -1.f : 1.f;
	ReadBellyChannel(Mud, Movement, Ahead2D, Forward2D, Right2D);
	FrontWaterDepthM = 0.f;
	MaxWaterDepthM = 0.f;

	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		FGTWheelTraction& Wheel = Wheels[Index];
		const FWheelStatus& Status = Movement.GetWheelState(Index);
		Wheel.bInContact = Status.bInContact;
		Wheel.bSlipping = Status.bInContact && Status.bIsSlipping;
		Wheel.SlipMagnitude = Status.bInContact ? Status.SlipMagnitude : 0.f;
		if (Status.bInContact)
		{
			Wheel.ContactPoint = Status.ContactPoint;
		}
		// The true load and the ground's coefficient scale the tyre's slip graph: 1.0 on the graph is the grip available.
		Wheel.Load = Status.bInContact ? Wheel.SpringForce * LoadCorrection : 0.f;
		const FGTWaterSample WaterHere = (Water && Status.bInContact) ? Water->Sample(Status.ContactPoint) : FGTWaterSample();
		Wheel.WaterDepthM = Status.bInContact ? FMath::Max(0.f, WaterHere.DepthCm) * 0.01f : 0.f;
		Wheel.bRutWater = Status.bInContact && WaterHere.Kind == EGTWaterKind::Rut && WaterHere.DepthCm > 0.f;
		Wheel.FlowCmPerS = WaterHere.FlowCmPerS;
		// Water stage W3 (docs/WATER_PLAN.md): one water query and nothing else. The rut water the bog's table leaves
		// in a rut used to be a second read through UGTMudSubsystem::bRutWaterPhysics and the deeper of the pair; the
		// subsystem answers it now (kind Rut), so the line above is every kind of water there is and it feeds the same
		// drag, buoyancy and engine flood a ford's sheet feeds. The switch is gone.
		MaxWaterDepthM = FMath::Max(MaxWaterDepthM, Wheel.WaterDepthM);
		if (Index < 2)
		{
			FrontWaterDepthM = FMath::Max(FrontWaterDepthM, Wheel.WaterDepthM);
		}
		Wheel.SurfaceFriction = (Status.bInContact && Status.PhysMaterial.IsValid()) ? Status.PhysMaterial->Friction : 1.f;
		const UGTSurfacePhysMaterial* Surface = Status.bInContact ? Cast<UGTSurfacePhysMaterial>(Status.PhysMaterial.Get()) : nullptr;
		// Benmore B2: inside a mud deform zone the zone's rows (the Mud row, the Bog row on its core) stand in for the ground's own (Benmore's
		// landscape has no Mud or Bog layer); off every zone patch nothing changes.
		if (Mud && Status.bInContact && Mud->HasZonePatches())
		{
			const AGTMudPatch* ZonePatch = Mud->PatchAt(FVector2D(Status.ContactPoint.X, Status.ContactPoint.Y));
			if (const UGTSurfacePhysMaterial* ZoneRow = ZonePatch ? ZonePatch->ZoneSurfaceAt(FVector2D(Status.ContactPoint.X, Status.ContactPoint.Y)) : nullptr)
			{
				Surface = ZoneRow;
				Wheel.SurfaceFriction = ZoneRow->Friction;
			}
		}

		// Untagged ground behaves like dry tarmac. Rain (Wetness, from the weather subsystem) scales
		// drag and sinkage per surface, so wet dirt drives like shallow mud (ARCHITECTURE 6d).
		const float Wet = FMath::Clamp(Wetness, 0.f, 1.f);
		const float WetScale = Surface ? Surface->WetFrictionScale : 0.75f;
		const float BaseDrag = (Surface ? Surface->RollingResistance : 0.012f) * FMath::Lerp(1.f, Surface ? Surface->WetRollingResistanceScale : 1.f, Wet);
		const float WetSink = FMath::Lerp(1.f, Surface ? Surface->WetSinkageScale : 1.f, Wet);
		// RIVERBED S4 (2026-09-23, VEHICLE_BUILD_SYSTEM 54): the patch first. Inside the box of a patch with a deformation
		// profile (a ford's bed), on ground that sinks at all (the row's MaxSinkage over 0: tarmac stays firm), the
		// profile's two numbers stand in for the row's; the row's wet scale and the rest of the row still apply. A bog's
		// patch has no profile, so a bog reads its rows exactly as before.
		const AGTMudPatch* BoxPatch = (Mud && Status.bInContact) ? Mud->PatchAt(FVector2D(Status.ContactPoint.X, Status.ContactPoint.Y)) : nullptr;
		Wheel.bInProfiledPatch = BoxPatch && BoxPatch->bHasProfile && Surface && Surface->MaxSinkage > 0.f;
		// Living mud LM5b (docs/LIVING_MUD_PLAN.md LM5b, docs/MUD_VARIANTS.md): a mud variant's scales on the numbers the
		// wheel takes inside the patch - the rows (Mud and Bog alike) on a bog's patch, the profile's on a profiled one - for
		// the sinkage's cap and rate and for the friction (below, on FrictionScale: the Chaos friction circle, the slip graph
		// and the drive cap all scale as for a row with that much more Friction). Every scale is 1 on a Standard bog and on
		// every patch before LM5b, so those read exactly as before.
		const bool bMudRow = Surface && (Surface->SurfaceTag == GTTags::Surface_Mud.GetTag() || Surface->SurfaceTag == GTTags::Surface_Bog.GetTag());
		const bool bVariantScaled = BoxPatch && (Wheel.bInProfiledPatch || (!BoxPatch->bHasProfile && bMudRow));
		// MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4): the soft spot under the contact, on top of the variant's scales - the
		// sinkage's cap and rate times its SinkScale, the friction times its FrictionScale; exactly 1 off a soft-spot patch (a
		// profiled one, snow) and with gt.Mud.SoftSpots 0, so those read exactly as before.
		const FVector2D SoftScales = bVariantScaled ? BoxPatch->SoftScalesAt(FVector2D(Status.ContactPoint.X, Status.ContactPoint.Y)) : FVector2D(1.0, 1.0);
		const float VariantFriction = bVariantScaled ? BoxPatch->FrictionScale * static_cast<float>(SoftScales.Y) : 1.f;
		float SinkRate = 0.f;
		float MaxSink = 0.f;
		PatchSinkage(Wheel.bInProfiledPatch ? BoxPatch->ProfileSinkageRate : (Surface ? Surface->SinkageRate : 0.f),
			Wheel.bInProfiledPatch ? BoxPatch->ProfileMaxSinkageM : (Surface ? Surface->MaxSinkage : 0.f), WetSink,
			bVariantScaled ? BoxPatch->SinkageRateScale : 1.f, bVariantScaled ? BoxPatch->MaxSinkageScale : 1.f, static_cast<float>(SoftScales.X), SinkRate, MaxSink);
		Wheel.SurfaceTag = (Surface && Surface->SurfaceTag.IsValid()) ? Surface->SurfaceTag : GTTags::Surface_Tarmac.GetTag();
		Wheel.TrackDepth = Surface ? Surface->TrackDepth : 0.f;

		const UChaosVehicleWheel* WheelSetup = Movement.Wheels.IsValidIndex(Index) ? Movement.Wheels[Index].Get() : nullptr;
		// MR2b: the tread's own speed (Chaos's omega x the radius: forward positive), for the body's spray fans.
		Wheel.TreadCmPerS = (bWheelOutput && WheelSetup && Status.bInContact) ? WheelSetup->GetWheelAngularVelocity() * WheelSetup->WheelRadius : 0.f;
		if (!Ahead2D.IsNearlyZero())
		{
			Wheel.TyreHeading = Ahead2D;
		}
		else if (!Forward2D.IsNearlyZero())
		{
			Wheel.TyreHeading = Forward2D;
		}
		// How far this tyre's contact patch has travelled over the ground, whichever way it turns: the heading it is
		// stamped along carries the direction, so no sign is needed here. It was the wheel's own rolled distance
		// (|angular speed| x radius) until stage H, and under the slip of a low-range bog crawl that advances metres
		// for every centimetre of ground, so two neighbouring cells written by two ticks held phases with nothing to do
		// with each other and the tread picture repeated at the 12.5 cm cell instead of the 9 cm lug (section 33). The
		// ground travel is continuous across cells. A wheel that is not turning lays no tread, so it is clamped at 0.
		if (bWheelOutput && WheelSetup && Status.bInContact && Movement.UpdatedPrimitive)
		{
			const bool bTurning = FMath::Abs(WheelSetup->GetRotationAngularVelocity()) > 1.f;   // degrees a second
			if (bTurning)
			{
				const FVector ContactVelocity = Movement.UpdatedPrimitive->GetPhysicsLinearVelocityAtPoint(Status.ContactPoint);
				const float Travel = static_cast<float>(FVector2D::DotProduct(FVector2D(ContactVelocity.X, ContactVelocity.Y), Wheel.TyreHeading));
				Wheel.RolledCm += FMath::Max(0.f, Travel) * DeltaSeconds;
			}
		}

		// The rut ahead of the tyre. Inside a mud patch the field is the record (stage C): read where the tyre is
		// heading, the chassis heading turned by the wheel's steer, the way it travels; elsewhere the track paint
		// along the car's heading as before.
		Wheel.RutDepth = 0.f;
		Wheel.RutClimb = 0.f;
		Wheel.RutCrossSlope = 0.f;
		Wheel.RutHoldLateralN = 0.f;
		Wheel.bInMudPatch = false;
		// LM3a: a snow patch (a profiled one whose medium is snow; the same contact as the box lookup above).
		PatchMediumFlags(Status.bInContact, Wheel.bInProfiledPatch, Wheel.bInProfiledPatch ? static_cast<uint8>(BoxPatch->Medium) : 0, Wheel.bInSnowPatch, Wheel.bInGravelPatch);
		// Wheel spray P2: the variant slice of the patch at the contact (the spray's mud colour, its clumps' slice), Standard
		// outside every patch.
		Wheel.PatchVariant = (Status.bInContact && BoxPatch) ? static_cast<uint8>(BoxPatch->MudVariant) : 0;
		Wheel.SnowAheadCm = 0.f;
		// LM2a, the throw: 0 below the wheel's SlipThreshold (bSlipping's), rising to the patch's ThrowMax at SlipSaturation.
		Wheel.ThrowShare = 0.f;
		if (BoxPatch && Wheel.bSlipping && BoxPatch->ThrowMax > 0.f)
		{
			const float Threshold = WheelSetup ? FMath::Max(0.f, WheelSetup->SlipThreshold) : 20.f;
			const float Spin = Wheel.SlipMagnitude * DriveSign;
			const float Full = FMath::Max(Threshold + 1.f, SlipSaturation);
			Wheel.ThrowShare = FMath::Clamp(BoxPatch->ThrowMax, 0.f, 1.f) * FMath::Clamp((Spin - Threshold) / (Full - Threshold), 0.f, 1.f);
		}
		if (Status.bInContact && !Ahead2D.IsNearlyZero())
		{
			const FVector2D XY(Status.ContactPoint.X, Status.ContactPoint.Y);
			const bool bMudTag = Wheel.SurfaceTag == GTTags::Surface_Mud.GetTag() || Wheel.SurfaceTag == GTTags::Surface_Bog.GetTag();
			// RIVERBED S4: the tag gate widened to "a patch with a profile" (a ford's Dirt bed reads its field); a bog's
			// patch still wants the Mud or Bog tag. The same patch the lookup above found (the same contact).
			const AGTMudPatch* Patch = (bMudTag || Wheel.bInProfiledPatch) ? BoxPatch : nullptr;
			if (Patch)
			{
				Wheel.bInMudPatch = true;
				const FGTMudField& Field = Patch->GetField();
				const float Steer = (Movement.Wheels.IsValidIndex(Index) && Movement.Wheels[Index]) ? Movement.Wheels[Index]->GetSteerAngle() : 0.f;
				FVector2D Dir = Forward2D.IsNearlyZero() ? Ahead2D : Forward2D.GetRotated(Steer);
				if (FVector2D::DotProduct(Dir, Ahead2D) < 0.0)
				{
					Dir = -Dir;
				}
				Wheel.TyreHeading = Dir;   // the tread is stamped along the same heading the rut is read along
				const FVector2D Probe = XY + Dir * RutLookAheadCm;
				// The rut: the deepest of three probes across the tyre's width, so a tyre half over a rut reads it (the hold pushes it in).
				const FVector2D Side(-Dir.Y, Dir.X);
				const float HalfWidth = 0.5f * ((Movement.Wheels.IsValidIndex(Index) && Movement.Wheels[Index]) ? Movement.Wheels[Index]->WheelWidth : 25.f);
				// LM3a: against the ground, so in snow (whose field is relative to the snow's top) a rut is the cut below the
				// ground, the snow top added back; on mud the snow top is 0 and this is the field's height, as before.
				const float G0 = Field.GroundRelativeAt(Probe);
				const float G1 = Field.GroundRelativeAt(Probe + Side * HalfWidth);
				const float G2 = Field.GroundRelativeAt(Probe - Side * HalfWidth);
				const float RutCm = FMath::Max3(-G0, -G1, -G2);
				Wheel.RutDepth = MaxSink > 0.f ? FMath::Clamp(RutCm / (MaxSink * 100.f), 0.f, 1.f) : 0.f;
				if (Wheel.bInSnowPatch)
				{
					// LM3a: the snow ahead standing over the tyre's bottom (the ground less its sinkage), the mean of the three
					// probes: a tyre half in its own cut ploughs half.
					const float BottomCm = -Wheel.Sinkage * 100.f;
					Wheel.SnowAheadCm = (FMath::Max(0.f, G0 - BottomCm) + FMath::Max(0.f, G1 - BottomCm) + FMath::Max(0.f, G2 - BottomCm)) / 3.f;
				}
				// The field's slope there, clamped (a stamp's wall reads steeper over one cell than any bank): up along
				// the heading is a climb out of the rut or over a ridge, across is the wall that holds the tyre. Only
				// ruts and ridges hold (the tracks factor), never untouched mud.
				const float Hold = Field.TracksAt(Probe);
				const FVector2D Slope = Field.GradientAt(Probe);
				const float Along = static_cast<float>(FVector2D::DotProduct(Dir, Slope));
				Wheel.RutClimb = FMath::Clamp(Along, 0.f, RutHoldMaxSlope) * Hold;
				const FVector2D Across = (Slope - Dir * Along).GetClampedToMaxSize(RutHoldMaxSlope) * Hold;
				Wheel.RutCrossSlope = static_cast<float>(FVector2D::DotProduct(Across, Right2D));
				if (RutHoldLateral > 0.f && Wheel.Load > 0.f && HoldFade > 0.f && !Across.IsNearlyZero() && Movement.UpdatedPrimitive)
				{
					// The wall pushes the tyre back down into its rut, at the contact (Chaos units, like the load).
					const FVector2D Push = -Across * (RutHoldLateral * Wheel.Load * HoldFade);
					Movement.UpdatedPrimitive->AddForceAtLocation(FVector(Push.X, Push.Y, 0.0), Status.ContactPoint);
					Wheel.RutHoldLateralN = static_cast<float>(FVector2D::DotProduct(Push, Right2D)) * 0.01f;   // diagnostic (LM2a's crawl log)
				}
			}
			else if (Paint)
			{
				Wheel.RutDepth = FMath::Clamp(Paint->SampleDepth(Status.ContactPoint + Ahead * RutLookAheadCm), 0.f, 1.f);
			}
		}
		const float RutFactor = RutEase * Wheel.RutDepth;

		if (Status.bInContact && SinkRate > 0.f && MaxSink > 0.f)
		{
			// Settling (always), ploughing (rolling through it), wheelspin (slipping).
			const float Moving = FMath::Clamp(AbsSpeed / FMath::Max(1.f, PloughSpeed), 0.f, 1.f);
			const float SlipFraction = Wheel.bSlipping ? FMath::Clamp(Wheel.SlipMagnitude / FMath::Max(1.f, SlipSaturation), 0.f, 1.f) : 0.f;
			const float Growth = SinkRate * (SettleFraction + (1.f - SettleFraction) * Moving + WheelspinSinkageScale * SlipFraction) * (1.f - RutFactor);
			// A rut of yours ahead: the wheel drops into it (no ploughing to get there) and grows from it.
			Wheel.Sinkage = FMath::Max(Wheel.Sinkage, Wheel.RutDepth * MaxSink * 0.8f);
			if (Wheel.Sinkage > MaxSink)
			{
				// 2026-09-22 (section 49, the ledge): onto a shallower row (Mud 0.22 -> Dirt 0.05 at a ford's or a bog's
				// exit) the sinkage comes back at the recovery rate instead of snapping to the new row's MaxSink: the snap
				// grew the wheel 16.2 -> 33.0 cm and its load 4.3 -> 14.0 kN in one tick, the "invisible ledge".
				Wheel.Sinkage = FMath::Max(MaxSink, Wheel.Sinkage - SinkageRecoveryRate * DeltaSeconds);
			}
			else
			{
				Wheel.Sinkage = FMath::Min(Wheel.Sinkage + Growth * DeltaSeconds, MaxSink);
			}
		}
		else
		{
			Wheel.Sinkage = FMath::Max(0.f, Wheel.Sinkage - SinkageRecoveryRate * DeltaSeconds);
		}
		Wheel.SinkageFraction = MaxSink > 0.f ? FMath::Clamp(Wheel.Sinkage / MaxSink, 0.f, 1.f) : 0.f;
		// MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md): the mud the tyre carries. A bog's Mud or Bog row inside a mud patch
		// loads it (not a ford's bed: a profiled patch on another row is not a bog); snow carries none. Read by the pawn's track
		// paint outside every patch and by nothing in the physics.
		{
			FGTMudLoadStep Step;
			Step.bInContact = Status.bInContact;
			Step.bInMudPatch = Status.bInContact && BoxPatch && BoxPatch->Medium == EGTDeformMedium::Mud && bMudRow;
			Step.bInSnowPatch = Status.bInContact && BoxPatch && BoxPatch->IsSnow();
			Step.SinkageFraction = Wheel.SinkageFraction;
			Step.SlipShare = Wheel.bSlipping ? FMath::Clamp(FMath::Abs(Wheel.SlipMagnitude) / FMath::Max(1.f, SlipSaturation), 0.f, 1.f) : 0.f;
			Step.WaterDepthM = Wheel.WaterDepthM;
			Step.bRutWater = Wheel.bRutWater;
			// Ground covered this tick: the chassis's own speed over the ground. Not the contact point's movement (it wanders a
			// little from tick to tick) nor the velocity at the contact (a parked body's small rocking times the lever arm): either
			// shed a parked car's load, 0.7 -> 0.4 in 45 s on L_MudVariants (2026-10-08). Under 20 cm/s counts as standing.
			float GroundSpeed = 0.f;
			if (Status.bInContact && Movement.UpdatedPrimitive)
			{
				const FVector Body = Movement.UpdatedPrimitive->GetPhysicsLinearVelocity();
				GroundSpeed = static_cast<float>(FVector2D(Body.X, Body.Y).Size());
			}
			Step.DistanceCm = GroundSpeed > 20.f ? FMath::Min(500.f, GroundSpeed * DeltaSeconds) : 0.f;
			Step.DeltaSeconds = DeltaSeconds;
			Wheel.MudLoad = StepMudLoad(Wheel.MudLoad, Step, MudLoadRate, MudShedHalfM, MudWashHalfM, MudWashDepthM);
		}
		// RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): what the Chaos radius shrinks by. Only a mud patch deforms, so
		// only inside a patch's box (the box, not bInMudPatch, which also wants the Mud or Bog tag) does the wheel go down
		// by its whole sinkage; outside every box the shrink is capped at OutsidePatchSinkCapM. Drag, grip, the belly and
		// the F2 decay above keep the raw Sinkage. On the way out of a box the shrink falls at most VisibleSinkRiseRate
		// metres per metre of ground travelled (no limit going down), so the box's edge is a ramp, not a one-tick ledge.
		if (Status.bInContact)
		{
			Wheel.bInPatchBox = BoxPatch != nullptr;   // RIVERBED S4: the lookup at the top of the loop (the same contact)
		}
		if (CVarMudSinkCap.GetValueOnGameThread() == 0)
		{
			Wheel.VisibleSinkage = Wheel.Sinkage;
		}
		else
		{
			const float VisibleTarget = Wheel.bInPatchBox ? Wheel.Sinkage : FMath::Min(Wheel.Sinkage, OutsidePatchSinkCapM);
			float TravelM = 0.f;
			if (Status.bInContact && Movement.UpdatedPrimitive)
			{
				const FVector ContactVelocity = Movement.UpdatedPrimitive->GetPhysicsLinearVelocityAtPoint(Status.ContactPoint);
				TravelM = static_cast<float>(FVector2D(ContactVelocity.X, ContactVelocity.Y).Size()) * DeltaSeconds * 0.01f;
			}
			// Never deeper than the raw sinkage (so the F2 decay still lifts a wheel standing still), never shallower than
			// the target, and between the two it comes up with the ground travelled.
			const float RiseOverride = CVarMudSinkRiseRate.GetValueOnGameThread();
			const float RiseRate = RiseOverride >= 0.f ? RiseOverride : VisibleSinkRiseRate;
			Wheel.VisibleSinkage = FMath::Max(VisibleTarget, FMath::Min(Wheel.VisibleSinkage - RiseRate * TravelM, Wheel.Sinkage));
		}
		if (Wheel.SinkageFraction >= BogSinkageFraction)
		{
			++SunkWheels;
		}
		if (Wheel.bSlipping)
		{
			++SpinningWheels;
		}

		const float GripLoss = Surface ? Surface->SinkageGripLoss : 0.f;
		const float DragScale = Surface ? Surface->SinkageDragScale : 0.f;
		const float Plough = Surface ? Surface->PloughDrag : 0.f;
		// LM3a: in a snow patch the plough is the snow ahead's (the bog's term with the snow ahead over the wheel's radius in
		// place of the sinkage fraction, SnowPlough in place of the row's coefficient: a cut rut has none), and the belly
		// drags by the snow standing over its underside ahead of it.
		const float WheelRadiusCm = (WheelSetup && WheelSetup->WheelRadius > 1.f) ? WheelSetup->WheelRadius : 38.f;
		// LM3b: the two snow numbers can be overridden for the drive check's trials (gt.Snow.Plough, gt.Snow.BellyDrag).
		const float PloughOverride = CVarSnowPlough.GetValueOnGameThread();
		const float BellyOverride = CVarSnowBellyDrag.GetValueOnGameThread();
		const float SnowPloughK = (Wheel.bInSnowPatch && BoxPatch) ? FMath::Max(0.f, PloughOverride >= 0.f ? PloughOverride : BoxPatch->SnowPlough) : 0.f;
		const float SnowBellyScale = (Wheel.bInSnowPatch && BoxPatch) ? FMath::Max(0.f, BellyOverride >= 0.f ? BellyOverride : BoxPatch->SnowBellyDrag) : 0.f;
		const float SnowBellyDrag = (Wheel.bInSnowPatch && bBellyInSnow) ? BellyDragPerMetre * BellySnowCm * 0.01f * SnowBellyScale : 0.f;
		// LM3b (housekeeping 1): inside a snow patch the row's sinkage rolling resistance counted the snow a second time
		// (the plough and the belly carry the uncut snow). There the tyre's own sinkage, its few cm in the packed base,
		// rolls at the SnowBaseRow's rate (the Dirt row): its RollingResistance x (1 + its SinkageDragScale x the sinkage
		// fraction), with the contact row's wet scale. Outside snow patches every row reads as before.
		const bool bSnowRoll = Wheel.bInSnowPatch && SnowBase != nullptr;
		const float RollBase = bSnowRoll ? SnowBase->RollingResistance * FMath::Lerp(1.f, Surface ? Surface->WetRollingResistanceScale : 1.f, Wet) : BaseDrag;
		const float RollScale = bSnowRoll ? SnowBase->SinkageDragScale : DragScale;
		const float SpeedRatio = AbsSpeed / 1000.f;   // per 10 m/s
		// Ploughing: linear with speed at a crawl (a bow wave of mud pushed at walking pace), squared past 10 m/s (the momentum
		// eater). Squared all the way made deep mud a wall a car cannot pull out of: the crawl speed a surface allows is
		// (grip - drag at rest) / plough x 10 m/s, and a squared law put that at a tenth of walking pace on the flat.
		const float PloughSpeed2 = SpeedRatio * FMath::Max(1.f, SpeedRatio);
		// Past the axle clearance the axles ride on the mud: they plough and they carry load the tyres lose.
		const float Over = FMath::Clamp((Wheel.Sinkage - AxleClearanceM) / FMath::Max(0.05f, AxleClearanceM), 0.f, 1.f);
		// Water stage W2: WaterBuoyancyGripLoss is 0 now, so this term is 0 - the lift in UGTHullComponent takes the
		// weight off the springs instead, and the load below follows it. The term stays for a comparison run.
		const auto NativeSurface=AGTLandscapeSurface::QuerySurface(GetOwner(),FVector2D(Status.ContactPoint));
		Wheel.AuthoredSurface = Status.bInContact && NativeSurface.bAuthored ? NativeSurface.SurfaceTag : NAME_None;
		Wheel.GroundWetness = Status.bInContact && NativeSurface.bAuthored ? NativeSurface.Wetness : 0.f;
		Wheel.GroundWaterDepthCm = Status.bInContact && NativeSurface.bAuthored ? NativeSurface.WaterDepthCm : 0.f;
		const bool bNativeSubstance=Status.bInContact && NativeSurface.bNativeSubstanceResponse && NativeSurface.SinkageCapCm>.01f;
		const bool bNativeWater=NativeSurface.bNativeWaterResponse;
		const float Buoyancy = bNativeSubstance ? 0.f : WaterBuoyancyGripLoss * FMath::Clamp(Wheel.WaterDepthM / FMath::Max(0.05f, WaterBuoyancyDepthM), 0.f, 1.f);
		// The axle's channel: inside a mud patch the one the field says is already cut ahead of the belly, elsewhere your own rut.
		const float BellyEase = Wheel.bInMudPatch ? BellyChannelEase * BellyChannel : RutFactor;
		Wheel.FrictionScale = FMath::Lerp(1.f, WetScale, Wet) * (1.f - GripLoss * Wheel.SinkageFraction) * (1.f - BellyGripLoss * Over) * (1.f - Buoyancy) * VariantFriction;   // LM5b: 1 off a variant
		if(bNativeSubstance)Wheel.FrictionScale=VariantFriction;
		// Still/rut water retains its established rolling-drag response. Flowing
		// water needs a signed world force: rolling resistance always opposes the
		// car and cannot represent a following current or a parked car's push.
		float WaterRatio = SpeedRatio;
		float WaterAlong = 1.f;
		FVector2D WaterRelative=FVector2D::ZeroVector;
		const bool bFlowingWater=Wheel.WaterDepthM>0.f && !Wheel.FlowCmPerS.IsNearlyZero() && Movement.UpdatedPrimitive;
		if (bFlowingWater)
		{
			const FVector PointVel = Movement.UpdatedPrimitive->GetPhysicsLinearVelocityAtPoint(Status.ContactPoint);
			WaterRelative=FVector2D(PointVel.X,PointVel.Y)-Wheel.FlowCmPerS;
			WaterRatio=WaterRelative.Size()/1000.f;
			WaterAlong=0.f; // Applied below, never counted again as rolling resistance.
		}
		const float WaterDrag = bNativeWater ? 0.f : WaterDragPerMetre * Wheel.WaterDepthM * WaterRatio * WaterRatio;
		const float PloughDrag = Wheel.bInSnowPatch ? SnowPloughK * (Wheel.SnowAheadCm / WheelRadiusCm) * PloughSpeed2
			: Plough * Wheel.SinkageFraction * (1.f - RutFactor) * PloughSpeed2;
		Wheel.RollingResistance = FMath::Min(MaxRollingResistance,
			RollBase * (1.f + RollScale * Wheel.SinkageFraction)
			+ PloughDrag
			+ BellyDragPerMetre * FMath::Max(0.f, Wheel.Sinkage - AxleClearanceM) * (1.f - BellyEase) + SnowBellyDrag
			+ RutHoldDrag * Wheel.RutClimb   // steered up the wall of a rut or over a ridge
			+ WaterDrag * WaterAlong);
		// Diagnostic only (gt.Water.Diag, Vehicle/GTWaterDiag.cpp): the sum's terms above, uncapped; nothing reads them.
		Wheel.DiagSurfaceDrag = RollBase * (1.f + RollScale * Wheel.SinkageFraction);
		Wheel.DiagPloughDrag = PloughDrag;
		Wheel.DiagBellyDrag = BellyDragPerMetre * FMath::Max(0.f, Wheel.Sinkage - AxleClearanceM) * (1.f - BellyEase) + SnowBellyDrag;
		Wheel.DiagRutDrag = RutHoldDrag * Wheel.RutClimb;
		Wheel.RutHoldDragN = Wheel.DiagRutDrag * Wheel.Load * 0.01f;   // diagnostic (LM2a's crawl log); Chaos units are 100 x a newton
		Wheel.DiagWaterDrag = WaterDrag;
		Wheel.DiagSinkRate = SinkRate;
		Wheel.DiagMaxSink = MaxSink;
		Wheel.WaterLateralN = 0.f;
		Wheel.WaterForceN = FVector2D::ZeroVector;
		if (bFlowingWater && Wheel.Load > 0.f && !bNativeWater)
		{
			const FVector2D Fraction=GTWaterDrag::FlowingWheelFraction(WaterRelative,Wheel.WaterDepthM,
				WaterDragPerMetre,FMath::Max(0.f,MaxRollingResistance-Wheel.RollingResistance));
			const FVector2D Push=Fraction*Wheel.Load;
			Movement.UpdatedPrimitive->AddForceAtLocation(FVector(Push.X, Push.Y, 0.0), Status.ContactPoint);
			Wheel.WaterForceN=Push*.01;
			Wheel.WaterLateralN=FVector2D::DotProduct(Wheel.WaterForceN,Right2D);
		}
	}

	bBogged = SunkWheels >= BogWheelCount && SpinningWheels >= BogWheelCount && AbsSpeed < BogSpeedThreshold;

	if (bStampMud && Mud)
	{
		StampMud(*Mud, Movement);
	}
}

void UGTTractionComponent::ReadBellyChannel(const UGTMudSubsystem* Mud, const UChaosWheeledVehicleMovementComponent& Movement, const FVector2D& Ahead, const FVector2D& Forward, const FVector2D& Right)
{
	BellyChannel = 0.f;
	bBellyInMudPatch = false;
	BellySnowCm = 0.f;
	bBellyInSnow = false;
	if (!Mud || Ahead.IsNearlyZero() || Forward.IsNearlyZero())
	{
		return;
	}
	// The box the belly would flatten (StampMud's: between the tyres in contact, inset), and the depth it would cut to
	// from the deepest wheel's sinkage last tick.
	FVector2D Centre = FVector2D::ZeroVector;
	float MaxSink = 0.f;
	TArray<FVector2D, TInlineAllocator<8>> Contacts;
	for (int32 Index = 0; Index < Wheels.Num(); ++Index)
	{
		const FWheelStatus& Status = Movement.GetWheelState(Index);
		if (!Status.bInContact)
		{
			continue;
		}
		const FVector2D XY(Status.ContactPoint.X, Status.ContactPoint.Y);
		Centre += XY;
		Contacts.Add(XY);
		MaxSink = FMath::Max(MaxSink, Wheels[Index].Sinkage);
	}
	const float DepthCm = (MaxSink - AxleClearanceM) * 100.f;
	// LM3a: the snow over the belly's underside just ahead of its box, read before the mud's depth gate (in snow the
	// tyres sink 5 cm at most, well short of the axles, but the snow stands over them). The same box and points as below.
	if (Contacts.Num() >= 3)
	{
		FVector2D SnowCentre = FVector2D::ZeroVector;
		for (const FVector2D& Contact : Contacts)
		{
			SnowCentre += Contact;
		}
		SnowCentre /= Contacts.Num();
		float SnowHalfLength = 0.f;
		float SnowHalfWidth = 0.f;
		for (const FVector2D& Contact : Contacts)
		{
			SnowHalfLength = FMath::Max(SnowHalfLength, FMath::Abs(static_cast<float>(FVector2D::DotProduct(Contact - SnowCentre, Forward))));
			SnowHalfWidth = FMath::Max(SnowHalfWidth, FMath::Abs(static_cast<float>(FVector2D::DotProduct(Contact - SnowCentre, Right))));
		}
		const FVector2D SnowLead = SnowCentre + Ahead * (FMath::Max(0.f, SnowHalfLength - BellyStampInsetCm) + RutLookAheadCm);
		const AGTMudPatch* SnowPatch = Mud->PatchAt(SnowLead);
		if (SnowPatch && SnowPatch->IsSnow())
		{
			bBellyInSnow = true;
			const float UndersideCm = (AxleClearanceM - MaxSink) * 100.f;
			const float SnowInner = FMath::Max(0.f, SnowHalfWidth - BellyStampInsetCm) * 0.5f;
			float SnowSum = 0.f;
			for (float Side = -1.f; Side <= 1.f; Side += 1.f)
			{
				SnowSum += FMath::Max(0.f, SnowPatch->GetField().GroundRelativeAt(SnowLead + Right * (Side * SnowInner)) - UndersideCm);
			}
			BellySnowCm = SnowSum / 3.f;
		}
	}
	if (Contacts.Num() < 3 || DepthCm <= 0.5f)
	{
		return;
	}
	Centre /= Contacts.Num();
	float HalfLength = 0.f;
	float HalfWidth = 0.f;
	for (const FVector2D& Contact : Contacts)
	{
		HalfLength = FMath::Max(HalfLength, FMath::Abs(static_cast<float>(FVector2D::DotProduct(Contact - Centre, Forward))));
		HalfWidth = FMath::Max(HalfWidth, FMath::Abs(static_cast<float>(FVector2D::DotProduct(Contact - Centre, Right))));
	}
	// Just ahead of the box's leading end, the way the car is going: three points across its inner width.
	const FVector2D Lead = Centre + Ahead * (FMath::Max(0.f, HalfLength - BellyStampInsetCm) + RutLookAheadCm);
	const AGTMudPatch* Patch = Mud->PatchAt(Lead);
	if (!Patch)
	{
		return;
	}
	bBellyInMudPatch = true;
	const float Inner = FMath::Max(0.f, HalfWidth - BellyStampInsetCm) * 0.5f;
	float Sum = 0.f;
	for (float Side = -1.f; Side <= 1.f; Side += 1.f)
	{
		Sum += FMath::Max(0.f, -Patch->GetField().HeightAt(Lead + Right * (Side * Inner)));
	}
	BellyChannel = FMath::Clamp(Sum / (3.f * DepthCm), 0.f, 1.f);
}

void UGTTractionComponent::StampMud(UGTMudSubsystem& Mud, const UChaosWheeledVehicleMovementComponent& Movement)
{
	const int32 NumWheels = Wheels.Num();
	if (LastStampXY.Num() != NumWheels || LastChunkContact.Num() != NumWheels)
	{
		LastStampXY.Init(FVector2D::ZeroVector, NumWheels);
		LastStampValid.Init(false, NumWheels);
		LastChunkContact.Init(false, NumWheels);
	}
	// Each wheel on mud: a capsule from where it stamped last to its contact now, its tyre's width, to its sinkage.
	AGTMudPatch* BellyPatch = nullptr;
	float MaxSink = 0.f;
	FVector2D Centre = FVector2D::ZeroVector;
	int32 OnMud = 0;
	TArray<FVector2D, TInlineAllocator<8>> Contacts;
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		FGTWheelTraction& Wheel = Wheels[Index];
		const FVector2D XY(Wheel.ContactPoint.X, Wheel.ContactPoint.Y);
		// MudRunner MR5: a wheel in contact inside a patch breaks every chunk its stamp footprint reaches (the capsule from last
		// frame's contact, its tyre's width), stamping or not: the suspension traces ignore the chunks, so a wheel never rides up
		// on one. Before the stamp, which then cuts through the chunk's dome.
		if (Wheel.bInContact)
		{
			if (AGTMudPatch* ChunkPatch = Mud.PatchAt(XY))
			{
				const float TyreWidth = (Movement.Wheels.IsValidIndex(Index) && Movement.Wheels[Index]) ? Movement.Wheels[Index]->WheelWidth : 25.f;
				const bool bStroke = LastChunkContact[Index] && FVector2D::Distance(LastStampXY[Index], XY) < 300.f;   // a teleport is not a stroke
				ChunkPatch->BreakMudChunksUnderWheel(bStroke ? LastStampXY[Index] : XY, XY, 0.5f * TyreWidth);
				// Deformable gravel DG1 item 3: a gravel patch's loose stones under the same footprint are pushed aside, pressed in or,
				// with wheelspin, flicked back the way the tread runs (visual only: the field's windrow carries the volume).
				if (UGTGravelStones* Stones = ChunkPatch->GetGravelStones())
				{
					const float Slip = Wheel.bSlipping ? FMath::Clamp(Wheel.SlipMagnitude / FMath::Max(1.f, SlipSaturation), 0.f, 1.f) : 0.f;
					Stones->PushUnderWheel(bStroke ? LastStampXY[Index] : XY, XY, 0.5f * TyreWidth, Wheel.TyreHeading * (Wheel.TreadCmPerS < 0.f ? -1.f : 1.f), Slip);
				}
			}
		}
		LastChunkContact[Index] = Wheel.bInContact;
		// RIVERBED S4: or inside a profiled patch (a ford's bed), whatever the tag.
		// LM3a: in a snow patch whatever the sinkage (the tyre cuts the snow above its bottom).
		const bool bOnMud = Wheel.bInContact && (Wheel.Sinkage > 0.005f || Wheel.bInSnowPatch)
			&& (Wheel.SurfaceTag == GTTags::Surface_Mud.GetTag() || Wheel.SurfaceTag == GTTags::Surface_Bog.GetTag() || Wheel.bInProfiledPatch);
		AGTMudPatch* Patch = bOnMud ? Mud.PatchAt(XY) : nullptr;
		if (Patch)
		{
			const float Width = (Movement.Wheels.IsValidIndex(Index) && Movement.Wheels[Index]) ? Movement.Wheels[Index]->WheelWidth : 25.f;
			const bool bContinuous = LastStampValid[Index] && FVector2D::Distance(LastStampXY[Index], XY) < 300.f;   // a teleport is not a stroke
			// LM2a: the wheel's throw share of the bank's deposit comes back instead of being banked; the spray throws it.
			double Thrown = 0.0;
			Wheel.MudLoweredCm3 += static_cast<float>(Patch->GetField().StampWheel(bContinuous ? LastStampXY[Index] : XY, XY, Width, Wheel.Sinkage * 100.f, Wheel.TyreHeading, Wheel.RolledCm,
				Wheel.ThrowShare, Thrown));
			Wheel.ThrownCm3 += Thrown;
			// Benmore B2: a zone tile's stroke also into its live neighbours' overlap, so the rut runs on across the tile border.
			if (Patch->bZonePatch)
			{
				Mud.StampZoneNeighbours(*Patch, bContinuous ? LastStampXY[Index] : XY, XY, Width, Wheel.Sinkage * 100.f, Wheel.TyreHeading, Wheel.RolledCm);
			}
			BellyPatch = Patch;
			MaxSink = FMath::Max(MaxSink, Wheel.Sinkage);
			Centre += XY;
			Contacts.Add(XY);
			++OnMud;
		}
		LastStampXY[Index] = XY;
		LastStampValid[Index] = Patch != nullptr;
	}
	// The belly, once the axles ride on the mud: a box between the tyres flattened to the axle depth.
	const AActor* Owner = GetOwner();
	if (BellyPatch && Owner && OnMud >= 3 && BellyPatch->IsSnow())
	{
		// LM3a, the plough in snow: the belly's underside stands AxleClearanceM over the deepest tyre's bottom; wherever the
		// snow is above it the box cuts it down, with berms beside it. The box spans the car's width out to the tyres'
		// outer edges (no side inset: the tyres cut below the underside, so the box cannot fill their ruts), so the trench
		// is car-wide and the berms land outside the tyres; its ends are inset by BellyStampInsetCm as the mud's are.
		Centre /= OnMud;
		const FVector Fwd3 = Owner->GetActorForwardVector();
		const FVector2D Forward = FVector2D(Fwd3.X, Fwd3.Y).GetSafeNormal();
		const FVector2D Right(-Forward.Y, Forward.X);
		float HalfLength = 0.f;
		float HalfWidth = 0.f;
		for (const FVector2D& Contact : Contacts)
		{
			HalfLength = FMath::Max(HalfLength, FMath::Abs(static_cast<float>(FVector2D::DotProduct(Contact - Centre, Forward))));
			HalfWidth = FMath::Max(HalfWidth, FMath::Abs(static_cast<float>(FVector2D::DotProduct(Contact - Centre, Right))));
		}
		const float TyreWidth = (Movement.Wheels.Num() > 0 && Movement.Wheels[0]) ? Movement.Wheels[0]->WheelWidth : 25.f;
		BellyPloughedCm3 += BellyPatch->GetField().PloughBelly(Centre, Forward, 2.f * FMath::Max(0.f, HalfLength - BellyStampInsetCm), 2.f * HalfWidth + TyreWidth, (AxleClearanceM - MaxSink) * 100.f);
	}
	else if (BellyPatch && Owner && OnMud >= 3 && MaxSink > AxleClearanceM)
	{
		Centre /= OnMud;
		const FVector Fwd3 = Owner->GetActorForwardVector();
		const FVector2D Forward = FVector2D(Fwd3.X, Fwd3.Y).GetSafeNormal();
		const FVector2D Right(-Forward.Y, Forward.X);
		float HalfLength = 0.f;
		float HalfWidth = 0.f;
		for (const FVector2D& Contact : Contacts)
		{
			HalfLength = FMath::Max(HalfLength, FMath::Abs(static_cast<float>(FVector2D::DotProduct(Contact - Centre, Forward))));
			HalfWidth = FMath::Max(HalfWidth, FMath::Abs(static_cast<float>(FVector2D::DotProduct(Contact - Centre, Right))));
		}
		BellyPatch->GetField().StampBelly(Centre, Forward, 2.f * (HalfLength - BellyStampInsetCm), 2.f * (HalfWidth - BellyStampInsetCm), (MaxSink - AxleClearanceM) * 100.f);
	}
}

void UGTTractionComponent::ModifyTuning(FGTVehicleTuning& Tuning) const
{
	const int32 Count = FMath::Min(Tuning.Wheels.Num(), Wheels.Num());
	for (int32 Index = 0; Index < Count; ++Index)
	{
		Tuning.Wheels[Index].FrictionScale *= Wheels[Index].FrictionScale;
		Tuning.Wheels[Index].RollingResistance = Wheels[Index].RollingResistance;
		Tuning.Wheels[Index].bInContact = Wheels[Index].bInContact;
		Tuning.Wheels[Index].SlipGraphScale = Wheels[Index].Load * Wheels[Index].SurfaceFriction / 10000.f;
		Tuning.Wheels[Index].LoadCorrection *= LoadCorrection;
		Tuning.Wheels[Index].SinkageCm = Wheels[Index].VisibleSinkage * 100.f;   // RIVERBED S2: the visible sinking, not the raw
	}
	if (bBogged)
	{
		Tuning.TorqueScale *= BoggedTorqueScale;
	}
}

float UGTTractionComponent::GetMaxSinkageFraction() const
{
	float Result = 0.f;
	for (const FGTWheelTraction& Wheel : Wheels)
	{
		Result = FMath::Max(Result, Wheel.SinkageFraction);
	}
	return Result;
}
