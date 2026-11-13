// MudRunner MR2 (docs/MUDRUNNER_LESSONS_PLAN.md MR2 item 6): GrandTour.Mud.CarMud, CPU only, on the body state component with a
// traction component whose wheels the test sets by hand. Each row prints a "CarMud: " line for Art/mud_shape_test.ps1.
// MR2b: the FanCoat rows (2b): spin feeds only the spinning wheel's fan, which opens away from the spin; it washes like the coat.
#include "Vehicle/GTBodyStateComponent.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Core/GTGameplayTags.h"
#include "HAL/IConsoleManager.h"
#include "UObject/Package.h"
#include "Vehicle/GTTractionComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTCarMudTest, "GrandTour.Mud.CarMud",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace
{
	const EGTDamageRegion CarMudRegions[] = {
		EGTDamageRegion::Front, EGTDamageRegion::Rear, EGTDamageRegion::ArchFL, EGTDamageRegion::ArchFR,
		EGTDamageRegion::ArchRL, EGTDamageRegion::ArchRR, EGTDamageRegion::SideL, EGTDamageRegion::SideR,
		EGTDamageRegion::Roof, EGTDamageRegion::Glass,
	};

	/** Four wheels (FL, FR, RL, RR) in contact, in a bog (a mud patch on the Mud row) or not, with a sinkage, a slip and water. */
	void SetWheels(UGTTractionComponent& Traction, bool bInMud, float SinkageM, float SinkageFraction, float FrontSlip, float RearSlip, float WaterM)
	{
		Traction.Wheels.SetNum(4);
		for (int32 Index = 0; Index < 4; ++Index)
		{
			FGTWheelTraction& Wheel = Traction.Wheels[Index];
			Wheel = FGTWheelTraction();
			Wheel.bInContact = true;
			Wheel.bInMudPatch = bInMud;
			Wheel.SurfaceTag = bInMud ? GTTags::Surface_Mud.GetTag() : FGameplayTag();
			Wheel.Sinkage = SinkageM;
			Wheel.SinkageFraction = SinkageFraction;
			const float Slip = Index < 2 ? FrontSlip : RearSlip;
			Wheel.SlipMagnitude = Slip;
			Wheel.bSlipping = Slip > 0.f;
			Wheel.WaterDepthM = WaterM;
			Wheel.TreadCmPerS = Slip;   // MR2b: the tread's own speed; the runs add the car's speed (SetTread)
		}
	}

	/** MR2b: each wheel's tread speed, the car's speed plus its slip (as Chaos's omega x radius is). */
	void SetTread(UGTTractionComponent& Traction, float SpeedCmPerS)
	{
		for (FGTWheelTraction& Wheel : Traction.Wheels)
		{
			Wheel.TreadCmPerS = SpeedCmPerS + Wheel.SlipMagnitude;
		}
	}

	void Run(UGTBodyStateComponent& State, const UGTTractionComponent& Traction, float Seconds, float SpeedCmPerS, float Dt = 1.f / 60.f)
	{
		for (float Clock = 0.f; Clock < Seconds - 1.e-4f; Clock += Dt)
		{
			State.Update(Dt, Traction, SpeedCmPerS);
		}
	}

	FString Coats(const UGTBodyStateComponent& State)
	{
		return FString::Printf(TEXT("F %.2f R %.2f aFL %.2f aFR %.2f aRL %.2f aRR %.2f sL %.2f sR %.2f roof %.2f glass %.2f"),
			State.GetDirt(EGTDamageRegion::Front), State.GetDirt(EGTDamageRegion::Rear), State.GetDirt(EGTDamageRegion::ArchFL),
			State.GetDirt(EGTDamageRegion::ArchFR), State.GetDirt(EGTDamageRegion::ArchRL), State.GetDirt(EGTDamageRegion::ArchRR),
			State.GetDirt(EGTDamageRegion::SideL), State.GetDirt(EGTDamageRegion::SideR), State.GetDirt(EGTDamageRegion::Roof),
			State.GetDirt(EGTDamageRegion::Glass));
	}
}

bool FGTCarMudTest::RunTest(const FString& Parameters)
{
	IConsoleVariable* CarMudVar = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Mud.CarMud"));
	if (!TestNotNull(TEXT("CarMud: the gt.Mud.CarMud switch exists"), CarMudVar))
	{
		return false;
	}
	const int32 CarMudWas = CarMudVar->GetInt();
	CarMudVar->Set(1, ECVF_SetByCode);
	auto Within = [](float Value, float Asked, float Share) { return FMath::Abs(Value - Asked) <= FMath::Abs(Asked) * Share; };
	auto Fresh = []() { return NewObject<UGTBodyStateComponent>(GetTransientPackage()); };
	UGTTractionComponent* Traction = NewObject<UGTTractionComponent>(GetTransientPackage());
	Traction->Wetness = 0.f;

	// ---- 1. 3 s in mud: the tyres caked, the sills coated, the roof clean -------------------------------------------------
	{
		UGTBodyStateComponent* State = Fresh();
		SetWheels(*Traction, true, 0.15f, 0.5f, 0.f, 0.f, 0.f);
		// Rolling exposes tread; a parked wheel must not cake its whole circumference.
		Run(*State, *Traction, 1.f, 0.f);
		TestEqual(TEXT("CarMud: stationary unladen tread does not acquire a full coating"), State->GetTyreCoat(0), 0.f);
		SetTread(*Traction, 300.f);
		Run(*State, *Traction, 3.f, 300.f);
		const float TyreMin = FMath::Min(FMath::Min(State->GetTyreCoat(0), State->GetTyreCoat(1)), FMath::Min(State->GetTyreCoat(2), State->GetTyreCoat(3)));
		const float SillMin = FMath::Min(State->GetDirt(EGTDamageRegion::SideL), State->GetDirt(EGTDamageRegion::SideR));
		TestTrue(TEXT("CarMud: 3 s in mud brings the tyres to at least 0.9 and the sills to at least 0.5, the roof at 0"),
			TyreMin >= 0.9f && SillMin >= 0.5f && State->GetDirt(EGTDamageRegion::Roof) == 0.f);
		TestTrue(TEXT("CarMud: the windscreen takes no mud from the wheels (throw hits only)"), State->GetDirt(EGTDamageRegion::Glass) == 0.f);
		AddInfo(FString::Printf(TEXT("CarMud: mud - 3 s at 3 m/s, sinkage 15 cm (fraction 0.5), no slip: tyres %.3f / %.3f / %.3f / %.3f (asked 0.9), sills %.3f / %.3f (asked 0.5), roof %.3f (asked 0); %s; mud line %.0f cm, coat line %.0f cm, MudWet %.2f"),
			State->GetTyreCoat(0), State->GetTyreCoat(1), State->GetTyreCoat(2), State->GetTyreCoat(3), State->GetDirt(EGTDamageRegion::SideL),
			State->GetDirt(EGTDamageRegion::SideR), State->GetDirt(EGTDamageRegion::Roof), *Coats(*State), State->MudLineCm, State->CoatLineCm, State->MudWet));

		// The mud line falls back to its base 10 s after the mud; the coat's line stays (dried mud stays until washed).
		const float CoatLine = State->CoatLineCm;
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 0.f);
		Run(*State, *Traction, 11.f, 300.f);
		TestTrue(TEXT("CarMud: the mud line falls to its base 10 s after the mud, the coat's line stays"),
			FMath::IsNearlyEqual(State->MudLineCm, State->MudLineBaseCm, 0.01f) && State->CoatLineCm == CoatLine && State->GetDirt(EGTDamageRegion::SideL) == SillMin);
		AddInfo(FString::Printf(TEXT("CarMud: line - 11 s on firm ground after: mud line %.1f cm (base %.0f), coat line %.1f cm (was %.1f), sill %.3f (was %.3f), MudWet %.3f"),
			State->MudLineCm, State->MudLineBaseCm, State->CoatLineCm, CoatLine, State->GetDirt(EGTDamageRegion::SideL), SillMin, State->MudWet));
	}

	// ---- 2. spin feeds the arches by axle --------------------------------------------------------------------------------
	{
		UGTBodyStateComponent* Front = Fresh();
		SetWheels(*Traction, true, 0.15f, 0.5f, 600.f, 0.f, 0.f);
		Run(*Front, *Traction, 2.f, 0.f);
		UGTBodyStateComponent* Rear = Fresh();
		SetWheels(*Traction, true, 0.15f, 0.5f, 0.f, 600.f, 0.f);
		Run(*Rear, *Traction, 2.f, 0.f);
		const bool bFront = Front->GetDirt(EGTDamageRegion::ArchFL) > 0.5f && Front->GetDirt(EGTDamageRegion::ArchFR) > 0.5f && Front->GetDirt(EGTDamageRegion::Front) > 0.5f
			&& Front->GetDirt(EGTDamageRegion::ArchRL) == 0.f && Front->GetDirt(EGTDamageRegion::ArchRR) == 0.f && Front->GetDirt(EGTDamageRegion::Rear) == 0.f;
		const bool bRear = Rear->GetDirt(EGTDamageRegion::ArchRL) > 0.5f && Rear->GetDirt(EGTDamageRegion::ArchRR) > 0.5f && Rear->GetDirt(EGTDamageRegion::Rear) > 0.5f
			&& Rear->GetDirt(EGTDamageRegion::ArchFL) == 0.f && Rear->GetDirt(EGTDamageRegion::ArchFR) == 0.f && Rear->GetDirt(EGTDamageRegion::Front) == 0.f;
		TestTrue(TEXT("CarMud: spin feeds the arches by axle (front spin: the front arches and bumper only; rear spin: the rear ones only)"), bFront && bRear);
		TestTrue(TEXT("CarMud: spinning raises the mud line by 30 cm"), FMath::IsNearlyEqual(Front->MudLineCm, 15.f + Front->MudLineBaseCm + Front->MudLineSpinCm, 0.01f));
		AddInfo(FString::Printf(TEXT("CarMud: spin - 2 s standing in mud at full slip, front axle: %s; rear axle: %s; mud line %.1f cm (15 + 20 + 30)"),
			*Coats(*Front), *Coats(*Rear), Front->MudLineCm));
	}

	// ---- 2b. MR2b: the spray fans - spin feeds only the spinning wheel's fan, opening away from the spin ------------------
	{
		UGTBodyStateComponent* State = Fresh();
		SetWheels(*Traction, true, 0.15f, 0.5f, 0.f, 0.f, 0.f);
		Traction->Wheels[3].SlipMagnitude = 600.f;   // the right rear alone spins forward, the car standing
		Traction->Wheels[3].TreadCmPerS = 600.f;
		Traction->Wheels[3].bSlipping = true;
		Run(*State, *Traction, 2.f, 0.f);
		const float Spun = State->GetFanCoat(3);
		const float Others = FMath::Max(FMath::Max(State->GetFanCoat(0), State->GetFanCoat(1)), State->GetFanCoat(2));
		const float DirForward = State->GetFanDir(3);
		const FString Fans2s = FString::Printf(TEXT("FL %.3f FR %.3f RL %.3f RR %.3f"), State->GetFanCoat(0), State->GetFanCoat(1), State->GetFanCoat(2), Spun);
		Traction->Wheels[3].SlipMagnitude = -600.f;   // now it spins backward: the fan turns to open in front of the arch
		Traction->Wheels[3].TreadCmPerS = -600.f;
		Run(*State, *Traction, 0.5f, 0.f);
		const float DirHalfSecond = State->GetFanDir(3);   // half a second of it is not enough (FanSideRate: about 1.25 s)
		Run(*State, *Traction, 1.f, 0.f);
		const float DirBackward = State->GetFanDir(3);
		const float OthersAfter = FMath::Max(FMath::Max(State->GetFanCoat(0), State->GetFanCoat(1)), State->GetFanCoat(2));
		// Braking while rolling forward (the slip negative, the tread still moving forward) keeps every fan behind its arch.
		UGTBodyStateComponent* Braked = Fresh();
		SetWheels(*Traction, true, 0.15f, 0.5f, 0.f, 0.f, 0.f);
		SetTread(*Traction, 200.f);
		Run(*Braked, *Traction, 1.f, 200.f);
		SetWheels(*Traction, true, 0.15f, 0.5f, -150.f, -150.f, 0.f);
		for (FGTWheelTraction& Wheel : Traction->Wheels)
		{
			Wheel.bSlipping = true;
		}
		SetTread(*Traction, 200.f);   // the tread at 50 cm/s, still forward
		Run(*Braked, *Traction, 1.f, 200.f);
		const bool bBraking = Braked->GetFanDir(0) == 1.f && Braked->GetFanDir(1) == 1.f && Braked->GetFanDir(2) == 1.f && Braked->GetFanDir(3) == 1.f;
		TestTrue(TEXT("CarMud: spin feeds only the spinning wheel's fan (FanCoat), which opens behind the arch spinning forward and turns in front after over a second spinning backward; braking forward keeps it behind"),
			Spun >= 0.9f && Others == 0.f && OthersAfter == 0.f && DirForward == 1.f && DirHalfSecond == 1.f && DirBackward == -1.f && bBraking);
		AddInfo(FString::Printf(TEXT("CarMud: fans - 2 s standing in mud, the right rear alone at full forward slip: FanCoat %s, RR's side %+.0f (behind); spinning backward: RR's side after 0.5 s %+.0f, after 1.5 s %+.0f (in front), the others %.3f; rolling 1 s at 2 m/s then braking 1 s (slip -150 cm/s): sides %+.0f %+.0f %+.0f %+.0f"),
			*Fans2s, DirForward, DirHalfSecond, DirBackward, OthersAfter,
			Braked->GetFanDir(0), Braked->GetFanDir(1), Braked->GetFanDir(2), Braked->GetFanDir(3)));

		// Rolling through mud feeds every wheel's fan by speed x sinkage (no spin).
		UGTBodyStateComponent* Rolled = Fresh();
		SetWheels(*Traction, true, 0.15f, 0.5f, 0.f, 0.f, 0.f);
		Run(*Rolled, *Traction, 2.f, 300.f);
		TestTrue(TEXT("CarMud: rolling through mud feeds every wheel's fan by speed x sinkage"),
			Rolled->GetFanCoat(0) > 0.2f && FMath::IsNearlyEqual(Rolled->GetFanCoat(0), Rolled->GetFanCoat(3), 1.e-4f));
		AddInfo(FString::Printf(TEXT("CarMud: fans - 2 s at 3 m/s, sinkage fraction 0.5, no slip: FanCoat %.3f / %.3f / %.3f / %.3f"),
			Rolled->GetFanCoat(0), Rolled->GetFanCoat(1), Rolled->GetFanCoat(2), Rolled->GetFanCoat(3)));
	}

	// ---- 2c. MR2b: a fan washes like the coat ---------------------------------------------------------------------------
	{
		auto Coated = [&]()
		{
			UGTBodyStateComponent* State = Fresh();
			SetWheels(*Traction, true, 0.15f, 0.5f, 600.f, 600.f, 0.f);
			Run(*State, *Traction, 2.f, 0.f);
			for (const EGTDamageRegion Region : CarMudRegions)
			{
				State->SetDirtForTest(Region, 1.f);
			}
			return State;
		};
		UGTBodyStateComponent* Shallow = Coated();
		const float Fan0 = Shallow->GetFanCoat(0);
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 0.5f);
		Run(*Shallow, *Traction, 4.f, 200.f);
		UGTBodyStateComponent* Deep = Coated();
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 1.2f);
		Run(*Deep, *Traction, 2.f, 200.f);
		UGTBodyStateComponent* Rained = Coated();
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 0.f);
		Rained->Rain = 1.f;
		Run(*Rained, *Traction, 10.f, 0.f);
		UGTBodyStateComponent* Washed = Coated();
		Washed->Wash();
		bool bShallow = true;
		bool bDeep = true;
		bool bRain = true;
		for (int32 Wheel = 0; Wheel < 4; ++Wheel)
		{
			const EGTDamageRegion Arch = Wheel == 0 ? EGTDamageRegion::ArchFL : Wheel == 1 ? EGTDamageRegion::ArchFR : Wheel == 2 ? EGTDamageRegion::ArchRL : EGTDamageRegion::ArchRR;
			bShallow &= Shallow->GetFanCoat(Wheel) == 1.f && Shallow->GetDirt(Arch) == 1.f;
			bDeep &= FMath::IsNearlyEqual(Deep->GetFanCoat(Wheel), Deep->GetDirt(Arch), 1.e-4f) && Within(Deep->GetFanCoat(Wheel), 0.4f, 0.05f);
			bRain &= FMath::IsNearlyEqual(Rained->GetFanCoat(Wheel), Rained->GetDirt(EGTDamageRegion::Roof), 1.e-4f) && Within(1.f - Rained->GetFanCoat(Wheel), 0.1f, 0.1f);
		}
		const bool bWash = Washed->GetFanCoat(0) == 0.f && Washed->GetFanCoat(3) == 0.f;
		TestTrue(TEXT("CarMud: a fan washes like the coat (kept through 50 cm of water, at the arches' rate wholly under 120 cm, rain 0.01/s, gone with Wash)"),
			Fan0 == 1.f && bShallow && bDeep && bRain && bWash);
		AddInfo(FString::Printf(TEXT("CarMud: fans - from %.2f: 4 s through 50 cm at 2 m/s %.3f (the arch %.3f); 2 s through 120 cm %.3f (the arch %.3f, asked 0.4); 10 s of rain 1 %.3f (a region %.3f); Wash %.3f"),
			Fan0, Shallow->GetFanCoat(0), Shallow->GetDirt(EGTDamageRegion::ArchFL), Deep->GetFanCoat(0), Deep->GetDirt(EGTDamageRegion::ArchFL),
			Rained->GetFanCoat(0), Rained->GetDirt(EGTDamageRegion::Roof), Washed->GetFanCoat(0)));
	}

	// ---- 3. water washes below the waterline only ------------------------------------------------------------------------
	{
		UGTBodyStateComponent* State = Fresh();
		SetWheels(*Traction, true, 0.6f, 1.f, 600.f, 600.f, 0.f);   // a deep spin raises the coat line to 110 cm
		Run(*State, *Traction, 1.f, 0.f);
		for (const EGTDamageRegion Region : CarMudRegions)
		{
			State->SetDirtForTest(Region, 1.f);
		}
		const float Line = State->CoatLineCm;
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 0.5f);
		Run(*State, *Traction, 4.f, 200.f);
		const float Below = State->GetCoatAt(EGTDamageRegion::SideL, 30.f);
		const float Above = State->GetCoatAt(EGTDamageRegion::SideL, 80.f);
		bool bRegionsKept = true;
		for (const EGTDamageRegion Region : CarMudRegions)
		{
			bRegionsKept &= State->GetDirt(Region) == 1.f;
		}
		const float TyreMax = FMath::Max(FMath::Max(State->GetTyreCoat(0), State->GetTyreCoat(1)), FMath::Max(State->GetTyreCoat(2), State->GetTyreCoat(3)));
		TestTrue(TEXT("CarMud: 4 s through 50 cm of water: clean below the waterline (30 cm), untouched above it (80 cm), no region wholly under it washed, tyres clean"),
			Below <= 0.01f && Above == 1.f && bRegionsKept && FMath::IsNearlyEqual(State->WashCm, 50.f, 0.01f) && State->WashAmount >= 0.99f && TyreMax == 0.f);
		AddInfo(FString::Printf(TEXT("CarMud: wash - coat line %.0f cm, 4 s through 50 cm of water at 2 m/s: the band %.0f cm at %.2f, the coat at 30 cm %.3f, at 80 cm %.3f; regions %s; tyres max %.2f"),
			Line, State->WashCm, State->WashAmount, Below, Above, bRegionsKept ? TEXT("all kept at 1") : *Coats(*State), TyreMax));

		UGTBodyStateComponent* Still = Fresh();
		Still->SetDirtForTest(EGTDamageRegion::SideL, 1.f);
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 0.5f);
		Run(*Still, *Traction, 5.f, 0.f);
		UGTBodyStateComponent* Deep = Fresh();
		for (const EGTDamageRegion Region : CarMudRegions)
		{
			Deep->SetDirtForTest(Region, 1.f);
		}
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 1.2f);
		Run(*Deep, *Traction, 2.f, 200.f);
		const bool bDeep = Within(Deep->GetDirt(EGTDamageRegion::Front), 0.4f, 0.05f) && Within(Deep->GetDirt(EGTDamageRegion::ArchFL), 0.4f, 0.05f)
			&& Deep->GetDirt(EGTDamageRegion::SideL) == 1.f && Deep->GetDirt(EGTDamageRegion::Roof) == 1.f && Deep->GetDirt(EGTDamageRegion::Glass) == 1.f;
		TestTrue(TEXT("CarMud: still water washes at 0.1/s; a region wholly under the water washes at 0.3/s moving, the ones above it keep their coat"),
			Within(Still->WashAmount, 0.5f, 0.05f) && bDeep);
		AddInfo(FString::Printf(TEXT("CarMud: wash - 5 s standing in 50 cm: the band at %.3f (asked 0.5); 2 s through 120 cm at 2 m/s: %s (front and arches, wholly under, asked 0.4)"),
			Still->WashAmount, *Coats(*Deep)));
	}

	// ---- 3b. a ford's riverbed (a profiled patch the traction flags, on its Dirt bed) is not mud ---------------------------
	{
		UGTBodyStateComponent* State = Fresh();
		SetWheels(*Traction, false, 0.05f, 0.2f, 0.f, 0.f, 0.f);
		for (FGTWheelTraction& Wheel : Traction->Wheels)
		{
			Wheel.bInMudPatch = true;
			Wheel.bInProfiledPatch = true;
			Wheel.SurfaceTag = GTTags::Surface_Dirt.GetTag();
		}
		Run(*State, *Traction, 2.f, 300.f);
		TestTrue(TEXT("CarMud: a ford's riverbed (a profiled patch on Dirt) lays no mud and cakes no tyre"), State->GetTyreCoat(0) == 0.f && State->MudWet == 0.f && State->GetDirt(EGTDamageRegion::SideL) < 0.05f);
		AddInfo(FString::Printf(TEXT("CarMud: riverbed - 2 s at 3 m/s on a ford's Dirt bed inside its patch: tyre %.3f, MudWet %.2f, sill %.3f (dust only)"),
			State->GetTyreCoat(0), State->MudWet, State->GetDirt(EGTDamageRegion::SideL)));
	}

	// ---- 4. drying over 90 s ----------------------------------------------------------------------------------------------
	{
		UGTBodyStateComponent* State = Fresh();
		SetWheels(*Traction, true, 0.1f, 0.3f, 0.f, 0.f, 0.f);
		Run(*State, *Traction, 0.5f, 100.f);
		const float Wet0 = State->MudWet;
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 0.f);
		float Dried = -1.f;
		float Half = -1.f;
		const float Dt = 1.f / 30.f;
		for (float Clock = 0.f; Clock < 200.f && Dried < 0.f; Clock += Dt)
		{
			State->Update(Dt, *Traction, 0.f);
			if (Half < 0.f && State->MudWet <= 0.5f)
			{
				Half = Clock + Dt;
			}
			if (State->MudWet <= 0.f)
			{
				Dried = Clock + Dt;
			}
		}
		TestTrue(TEXT("CarMud: fresh mud dries from wet to dry in MudDrySeconds (90 s within 10 %)"), Wet0 == 1.f && Within(Dried, State->MudDrySeconds, 0.1f));
		AddInfo(FString::Printf(TEXT("CarMud: drying - MudWet %.2f fresh, 0.5 at %.1f s, dry at %.1f s (asked %.0f)"), Wet0, Half, Dried, State->MudDrySeconds));
	}

	// ---- 5. rain washes slowly, and keeps the mud wet --------------------------------------------------------------------
	{
		UGTBodyStateComponent* State = Fresh();
		SetWheels(*Traction, true, 0.1f, 0.3f, 0.f, 0.f, 0.f);
		// Acquire a real rotating-wheel coating before measuring its rain wash-off.
		SetTread(*Traction, 300.f);
		Run(*State, *Traction, 3.f, 300.f);
		for (const EGTDamageRegion Region : CarMudRegions)
		{
			State->SetDirtForTest(Region, 1.f);
		}
		const float Tyre0 = State->GetTyreCoat(0);
		SetWheels(*Traction, false, 0.f, 0.f, 0.f, 0.f, 0.f);
		State->Rain = 1.f;
		Traction->Wetness = 0.6f;
		Run(*State, *Traction, 10.f, 0.f);
		const float Washed = 1.f - State->GetDirt(EGTDamageRegion::Roof);
		const float TyreWashed = Tyre0 - State->GetTyreCoat(0);
		Run(*State, *Traction, 100.f, 0.f, 1.f / 10.f);
		const float WetAfter = State->MudWet;
		TestTrue(TEXT("CarMud: rain 1 washes 0.01/s off every region and tyre (10 s: 0.1 within 10 %), and keeps MudWet at least the weather's wetness"),
			Within(Washed, 0.1f, 0.1f) && Within(TyreWashed, 0.1f, 0.1f) && WetAfter >= 0.6f - 1.e-4f);
		AddInfo(FString::Printf(TEXT("CarMud: rain - 10 s at rain 1: a region %.3f off (asked 0.1), a tyre %.3f off; MudWet after 110 s with the weather's wetness 0.6: %.3f"),
			Washed, TyreWashed, WetAfter));
		Traction->Wetness = 0.f;
	}

	// ---- 6. a thrown blob on the body: its region, wet, the windscreen ---------------------------------------------------
	{
		UGTBodyStateComponent* State = Fresh();
		State->AddThrowHit(FVector(50.f, -80.f, 130.f), FVector(0.f, -1.f, 0.f), 600.0);   // the side glass
		State->AddThrowHit(FVector(150.f, -60.f, 40.f), FVector(0.f, 0.f, -1.f), 600.0);   // under the front left arch
		const bool bHits = State->GetDirt(EGTDamageRegion::Glass) > 0.f && State->GetDirt(EGTDamageRegion::ArchFL) > 0.f && State->MudWet == 1.f
			&& State->GetThrowHits() == 2 && State->GetGlassHits() == 1;
		TestTrue(TEXT("CarMud: a thrown blob hitting the body coats the region it hits (the glass, an arch from below) and sets MudWet 1"), bHits);
		AddInfo(FString::Printf(TEXT("CarMud: hits - two 600 cm^3 blobs: %s; MudWet %.2f, hits %d (glass %d)"), *Coats(*State), State->MudWet, State->GetThrowHits(), State->GetGlassHits()));
	}

	// ---- 7. gt.Mud.CarMud 0 is the rule before MR2 ------------------------------------------------------------------------
	{
		SetWheels(*Traction, false, 0.15f, 0.5f, 0.f, 0.f, 0.f);
		for (FGTWheelTraction& Wheel : Traction->Wheels)
		{
			Wheel.SurfaceTag = GTTags::Surface_Mud.GetTag();
		}
		UGTBodyStateComponent* On = Fresh();
		Run(*On, *Traction, 1.f, 500.f);
		CarMudVar->Set(0, ECVF_SetByCode);
		UGTBodyStateComponent* Off = Fresh();
		Run(*Off, *Traction, 1.f, 500.f);
		Off->AddThrowHit(FVector(150.f, -60.f, 40.f), FVector(0.f, 0.f, -1.f), 600.0);
		CarMudVar->Set(1, ECVF_SetByCode);
		const bool bLegacy = Within(Off->GetDirt(EGTDamageRegion::ArchFL), 0.15f, 0.01f) && Within(Off->GetDirt(EGTDamageRegion::Glass), 0.03f, 0.02f)
			&& Off->GetThrowHits() == 0 && Off->TyreCoat.Num() == 0 && Off->CoatLineCm == 0.f;
		TestTrue(TEXT("CarMud: gt.Mud.CarMud 0 is the rule before MR2 (the arch 0.15 a second at full spray, the windscreen from the front wheels, no hits, no tyres)"), bLegacy);
		AddInfo(FString::Printf(TEXT("CarMud: switch - 1 s at 5 m/s on the Mud surface: CarMud 1 %s, tyres %.2f; CarMud 0 %s, hits %d"),
			*Coats(*On), On->GetTyreCoat(0), *Coats(*Off), Off->GetThrowHits()));
	}

	CarMudVar->Set(CarMudWas, ECVF_SetByCode);
	return true;
}
#endif
