#include "Vehicle/GTVehicleWheel.h"

namespace
{
	// Shared numbers from Art/Export/manifest.json (SK_RangeRover): 38 cm radius, 24.8 cm wide.
	void ApplyRangeRoverWheel(UChaosVehicleWheel& Wheel)
	{
		Wheel.WheelRadius = 38.f;
		Wheel.WheelWidth = 25.f;
		Wheel.WheelMass = 30.f;
		Wheel.bAffectedByEngine = true;
		Wheel.bAffectedByBrake = true;
		// Long-travel off-road suspension. A sphere sweep rolls over edges a ray would snag on.
		// SuspensionSmoothing only filters the drawn wheel offset (Chaos 5.8 does not use it in the
		// force model), so it is a visual choice, not a ride one.
		Wheel.SweepShape = ESweepShape::Spherecast;
		Wheel.SuspensionSmoothing = 2;
		Wheel.SuspensionMaxRaise = 12.f;
		Wheel.SuspensionMaxDrop = 16.f;
		// Chaos: spring force = compression from full drop x rate (x100 internally); damping = ratio x
		// critical for the ~525 kg sprung per corner. 250 / 0.5 (1.10 Hz) felt "soft and floaty",
		// 400 / 0.75 (1.39 Hz) "slightly too jolty": on a sharp crest the damping spike is the jolt.
		// 340 / 0.62 gives 1.28 Hz and 15 cm static sag of the 28 cm travel. SpringPreload is stored
		// but unused by the 5.8 force model.
		Wheel.SpringRate = 340.f;
		Wheel.SpringPreload = 60.f;
		Wheel.SuspensionDampingRatio = 0.62f;
		Wheel.MaxBrakeTorque = 1500.f;
		// Tyre (driving feel stage 1, docs/DRIVING_FEEL_PLAN.md). Chaos grip = load x the surface's Friction x this
		// multiplier; at the Chaos default of 2.0 dirt gave 1.24 g and the car could not slide, so it is 1.0 and the
		// surface table (Art/Unreal/setup_m1_track.py) holds real coefficients. The lateral slip graph is written in
		// fractions of the grip available: UGTVehicleTuningComponent scales it every tick by wheel load x surface
		// friction x the friction multiplier (SetWheelSlipGraphMultiplier), so 1.0 here is the friction circle. It
		// peaks near 8 degrees of slip and eases to 0.68 by 40: past the peak the tyre gives less, which is what
		// makes a slide something to catch rather than a wall. Chaos samples the curve 20 times over its range, so
		// the range stops at 40 degrees (2 degree steps; beyond it the last value holds). SideSlipModifier trims
		// both forces by 10 % while the friction circle clips (throttle or brake in a bend). No ABS, no traction
		// control: a locked wheel is part of the risk.
		Wheel.FrictionForceMultiplier = 1.f;
		Wheel.SideSlipModifier = 0.9f;
		// Stage 4: UGTDrivetrainComponent hands every wheel its drive and brake torque; Chaos's own engine and
		// gearbox are off on the car (bMechanicalSimEnabled false in AGTCarPawn).
		Wheel.ExternalTorqueCombineMethod = ETorqueCombineMethod::Override;
		// The tyre load Chaos uses is WheelLoadRatio x the force model's spring + (1 - ratio) x the resting quarter of
		// the car (default 0.5, "cures lift-off oversteer"). 1.0: the load is the spring alone, which the traction
		// component scales to the true load (the constraint suspension leaves the virtual spring short by a third), so
		// crests, braking and camber move the grip about and a wheel in the air has none.
		Wheel.WheelLoadRatio = 1.f;
		Wheel.bABSEnabled = false;
		Wheel.bTractionControlEnabled = false;
		if (FRichCurve* Slip = Wheel.LateralSlipGraph.GetRichCurve())
		{
			Slip->Reset();
			Slip->AddKey(0.f, 0.f);
			Slip->AddKey(2.f, 0.42f);
			Slip->AddKey(4.f, 0.76f);
			Slip->AddKey(6.f, 0.95f);
			Slip->AddKey(8.f, 1.f);
			Slip->AddKey(10.f, 0.97f);
			Slip->AddKey(14.f, 0.9f);
			Slip->AddKey(20.f, 0.82f);
			Slip->AddKey(30.f, 0.74f);
			Slip->AddKey(40.f, 0.68f);
		}
	}
}

UGTVehicleWheelFront::UGTVehicleWheelFront()
{
	ApplyRangeRoverWheel(*this);
	AxleType = EAxleType::Front;
	bAffectedBySteering = true;
	bAffectedByHandbrake = false;
	MaxSteerAngle = 35.f;
}

UGTVehicleWheelRear::UGTVehicleWheelRear()
{
	ApplyRangeRoverWheel(*this);
	AxleType = EAxleType::Rear;
	bAffectedBySteering = false;
	bAffectedByHandbrake = true;
	MaxHandBrakeTorque = 3000.f;
}
