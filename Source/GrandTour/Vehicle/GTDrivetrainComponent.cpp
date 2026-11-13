#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTDriveLayout.h"

#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTVehicleTuning.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "Vehicle/GTRangeRoverDrivetrain.h"
#include "Parts/GTPartSlotsComponent.h"
#include "Core/GTGameplayTags.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

UGTDrivetrainComponent::UGTDrivetrainComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick after the tuning
}

void UGTDrivetrainComponent::BeginPlay()
{
	Super::BeginPlay();
	if(!IsFerrari()) return;
	// The old tune was stored on a placed Benmore instance; new blueprint spawns
	// still inherited the base car's AWD/four-speed/5000 RPM configuration. Set the
	// Ferrari profile on this movement instance before tuning captures its base.
	auto* Move=CastChecked<AGTCarPawn>(GetOwner())->GetChaosMovement();
	CentreSplitFront=0.f; LowRangeRatio=2.f;
	auto& Engine=Move->EngineSetup;
	Engine.MaxTorque=450.f; Engine.MaxRPM=7500.f; Engine.EngineIdleRPM=900.f; Engine.EngineBrakeEffect=.05f;
	Engine.TorqueCurve.ExternalCurve=nullptr;
	auto* Curve=Engine.TorqueCurve.GetRichCurve();Curve->Reset();
	for(const FVector2D Key : {FVector2D(0,.48),FVector2D(900,.58),FVector2D(2000,.74),FVector2D(3500,.94),FVector2D(4500,1),FVector2D(5500,.98),FVector2D(6500,.94),FVector2D(7000,.88),FVector2D(7500,.72)})
		Curve->SetKeyInterpMode(Curve->AddKey(Key.X,Key.Y),RCIM_Linear);
	auto& Transmission=Move->TransmissionSetup;
	// Restore the authored launch ratio now that tyre spin retains its momentum;
	// the taller first gear was masking the old wheel solver's power response.
	Transmission.ForwardGearRatios={3.4f,2.25f,1.58f,1.18f,.92f}; Transmission.FinalRatio=4.1f;
	Transmission.ChangeUpRPM=7000.f; Transmission.ChangeDownRPM=2700.f; Transmission.GearChangeTime=.22f;
}

int32 UGTDrivetrainComponent::GetRangeRoverSetup() const
{
	const auto* Car=Cast<AGTCarPawn>(GetOwner());
	return Car && UGTRangeRoverAudioComponent::IsRangeRover(Car)
		? GTRangeRoverDrivetrain::Index(Car->GetParts()->GetInstalled(GTTags::Slot_Engine)) : -1;
}

bool UGTDrivetrainComponent::IsFerrari() const
{
	const auto* Car=Cast<AGTCarPawn>(GetOwner());
	return Car && Car->GetMesh() && Car->GetMesh()->GetSkeletalMeshAsset()
		&& Car->GetMesh()->GetSkeletalMeshAsset()->GetPathName()==TEXT("/Game/GrandTour/Vehicles/Ferrari288Good/SK_Ferrari288.SK_Ferrari288");
}

int32 UGTDrivetrainComponent::GetDriveLayout() const
{
	const auto* Car=Cast<AGTCarPawn>(GetOwner());
	return Car ? GTDriveLayout::Index(Car->GetParts()->GetInstalled(GTTags::Slot_DriveLayout)) : 0;
}

float UGTDrivetrainComponent::GetEffectiveFrontShare() const
{
	return GetDriveLayout()==3 ? AWDFrontShare : GTDriveLayout::FrontShare(GetDriveLayout(),CentreSplitFront);
}

bool UGTDrivetrainComponent::SetAWDFrontShare(float FrontShare)
{
	if(GetOwner() && GetOwner()->GetVelocity().Size()>30.f) return false;
	AWDFrontShare=GTDriveLayout::NormalizeAWDFrontShare(FrontShare);
	return true;
}

void UGTDrivetrainComponent::SetLowRange(bool bOn)
{
	// Avoid an instantaneous ratio/RPM jump in the independent-engine cars while travelling.
	// Existing fleet controls retain their authored behavior.
	if((GetRangeRoverSetup()>=0 || IsFerrari()) && bOn!=bLowRange && GetOwner()->GetVelocity().Size()>30.f) return;
	bLowRange=bOn;
}

FString UGTDrivetrainComponent::SetupReport() const
{
	const auto* Car=Cast<AGTCarPawn>(GetOwner());
	if(!Car) return TEXT("{}");
	const auto* Move=Car->GetChaosMovement();
	const int32 Index=GetRangeRoverSetup();
	const auto& S=GTRangeRoverDrivetrain::Setup(Index);
	const bool Upgraded=Index>0;
	auto J=MakeShared<FJsonObject>();
	J->SetNumberField(TEXT("setup"),Index);
	J->SetBoolField(TEXT("independent_engine"),Index>=0 || IsFerrari());
	J->SetBoolField(TEXT("ferrari"),IsFerrari());
	J->SetNumberField(TEXT("front_share"),GetEffectiveFrontShare());
	J->SetNumberField(TEXT("awd_front_share"),AWDFrontShare);
	J->SetNumberField(TEXT("drive_layout"),GetDriveLayout());
	J->SetStringField(TEXT("drive_layout_name"),GTDriveLayout::Name(GetDriveLayout()));
	J->SetStringField(TEXT("name"),IsFerrari() ? TEXT("Ferrari") : Index<0 ? TEXT("Authored") : S.Name);
	J->SetNumberField(TEXT("final_ratio"),Upgraded ? S.FinalRatio : Move->TransmissionSetup.FinalRatio);
	J->SetNumberField(TEXT("low_ratio"),Upgraded ? S.LowRatio : LowRangeRatio);
	J->SetNumberField(TEXT("up_rpm"),Upgraded ? S.UpRPM : Move->TransmissionSetup.ChangeUpRPM);
	J->SetNumberField(TEXT("down_rpm"),Upgraded ? S.DownRPM : Move->TransmissionSetup.ChangeDownRPM);
	J->SetNumberField(TEXT("shift_seconds"),Upgraded ? S.ShiftSeconds : Move->TransmissionSetup.GearChangeTime);
	J->SetNumberField(TEXT("pedal_exponent"),Upgraded ? S.PedalExponent : 1.f);
	J->SetNumberField(TEXT("centre_lsd"),Upgraded ? S.CentreLSD : 0.f);
	J->SetNumberField(TEXT("front_lsd"),Upgraded ? S.FrontLSD : 0.f);
	J->SetNumberField(TEXT("rear_lsd"),IsFerrari() ? .25f : Upgraded ? S.RearLSD : 0.f);
	TArray<TSharedPtr<FJsonValue>> Ratios;
	if(Upgraded) { for(float R:S.Gears) Ratios.Add(MakeShared<FJsonValueNumber>(R)); }
	else { for(float R:Move->TransmissionSetup.ForwardGearRatios) Ratios.Add(MakeShared<FJsonValueNumber>(R)); }
	J->SetArrayField(TEXT("gears"),Ratios);
	J->SetNumberField(TEXT("rpm"),EngineRpm); J->SetNumberField(TEXT("engine_nm"),EngineTorqueNm);
	J->SetNumberField(TEXT("pedal"),DriveInput); J->SetNumberField(TEXT("total_ratio"),TotalRatio);
	J->SetNumberField(TEXT("gear"),GetGear());
	J->SetBoolField(TEXT("low"),bLowRange); J->SetBoolField(TEXT("locked"),bDiffLock);
	J->SetNumberField(TEXT("road_rpm"),RoadRpmForShift);
	J->SetNumberField(TEXT("shaft_rpm"),WheelRpm);
	J->SetNumberField(TEXT("clutch_engagement"),ClutchEngagement);
	J->SetNumberField(TEXT("clutch_nm"),ClutchTorqueNm);
	J->SetNumberField(TEXT("shift_cut_remaining"),FMath::Max(0.f,ShiftTimer));
	J->SetBoolField(TEXT("wheelspin_shift_hold"),bWheelspinShiftHold);
	J->SetNumberField(TEXT("contacts"),ContactCount);
	J->SetNumberField(TEXT("torque_scale"),AppliedTorqueScale);
	J->SetNumberField(TEXT("requested_wheel_nm"),RequestedWheelTorqueNm);
	float Delivered=0.f; for(const auto& W:Wheels) Delivered+=W.DriveTorqueNm;
	J->SetNumberField(TEXT("delivered_wheel_nm"),Delivered);
	FString Result; FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Result)); return Result;
}

void UGTDrivetrainComponent::Split(float T, float CapA, float CapB, float OmegaA, float OmegaB, float Lock, float& OutA, float& OutB, bool bConserveTorque, float ShareA) const
{
	// Open: a side gets at most what the other side can react, so a spinning wheel starves its partner. The lock
	// lifts that limit and adds a stiff coupling that hands torque from the faster side to the slower one.
	const float Sign = T >= 0.f ? 1.f : -1.f;
	const float DemandA = FMath::Abs(T) * FMath::Clamp(ShareA,0.f,1.f);
	const float DemandB = FMath::Abs(T) - DemandA;
	const float LimitA = CapB + Lock * FMath::Abs(T);
	const float LimitB = CapA + Lock * FMath::Abs(T);
	// Independent-engine cars: do not discard shaft torque at low grip. Chaos already limits
	// tyre force to available grip and turns excess torque into wheelspin. Applying
	// a second grip cap here acts like unintended traction control, twice through
	// centre and axle diffs. Keep the legacy model for the rest of the fleet.
	OutA = Sign * (bConserveTorque ? DemandA : FMath::Min(DemandA, LimitA));
	OutB = Sign * (bConserveTorque ? DemandB : FMath::Min(DemandB, LimitB));
	if (Lock > 0.f)
	{
		const float Coupling = FMath::Clamp(Lock * LockCouplingNmPerRadS * (OmegaB - OmegaA), -LockCouplingMaxNm, LockCouplingMaxNm);
		OutA += Coupling;
		OutB -= Coupling;
	}
}

void UGTDrivetrainComponent::Update(float DeltaSeconds, UChaosWheeledVehicleMovementComponent& Movement, const UGTTractionComponent& Traction, const FGTVehicleTuning& Tuning)
{
	const int32 NumWheels = Movement.WheelSetups.Num();
	if (Wheels.Num() != NumWheels)
	{
		Wheels.SetNum(NumWheels);
	}
	if (NumWheels == 0 || Movement.Wheels.Num() < NumWheels || !Movement.PhysicsVehicleOutput().IsValid())
	{
		return;   // Chaos has not created the vehicle yet
	}
	if (!bOverrideSet)
	{
		// The wheel classes carry the override as well; this covers a wheel class that does not.
		for (int32 Index = 0; Index < NumWheels; ++Index)
		{
			Movement.SetTorqueCombineMethod(ETorqueCombineMethod::Override, Index);
		}
		bOverrideSet = true;
	}

	// Pedals. Forward: throttle drives, brake brakes; held at a stop the brake puts the car in reverse, where the
	// brake pedal drives backward and the throttle brakes, and the throttle held at a stop takes it out again.
	const float ThrottleIn = FMath::Clamp(Movement.GetThrottleInput(), 0.f, 1.f);
	const float BrakeIn = FMath::Clamp(Movement.GetBrakeInput(), 0.f, 1.f);
	const float HandbrakeIn = FMath::Clamp(Movement.GetHandbrakeInput(), 0.f, 1.f);
	const float ForwardSpeed = Movement.GetForwardSpeed();
	if (!bReverse && BrakeIn > 0.05f && ThrottleIn <= 0.05f && FMath::Abs(ForwardSpeed) < ReverseSpeedThreshold)
	{
		bReverse = true;
	}
	else if (bReverse && ThrottleIn > 0.05f && BrakeIn <= 0.05f && FMath::Abs(ForwardSpeed) < ReverseSpeedThreshold)
	{
		bReverse = false;
	}
	DriveInput = bReverse ? BrakeIn : ThrottleIn;
	BrakeInput = bReverse ? ThrottleIn : BrakeIn;
	const float PedalInput=DriveInput;
	const int32 SetupIndex=GetRangeRoverSetup();
	const auto& Package=GTRangeRoverDrivetrain::Setup(SetupIndex);
	const bool Upgraded=SetupIndex>0;
	const bool RangeRover=SetupIndex>=0;
	const bool Ferrari=IsFerrari();
	const bool Independent=RangeRover || Ferrari;
	const int32 Layout=GetDriveLayout();
	const float FrontShare=GetEffectiveFrontShare();
	const bool ConserveTorque=Independent || Layout!=0;
	if(SetupIndex!=LastSetup || Layout!=LastLayout)
	{
		Gear=1; ShiftTimer=0.f; TimeSinceShift=10.f; MaxGearReached=1; LastSetup=SetupIndex; LastLayout=Layout;
		ClutchEngagement=0.f;
	}
	if(Upgraded) DriveInput=GTRangeRoverDrivetrain::Pedal(SetupIndex,DriveInput);

	// Wheels: speed, radius and what the tyre can react (true load x friction x radius, UGTTractionComponent).
	float OmegaSum = 0.f;
	ContactCount=0;
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		FGTDrivetrainWheel& Wheel = Wheels[Index];
		const UChaosVehicleWheel* Setup = Movement.Wheels[Index];
		// Chaos negates the wheel's angular velocity for the accessor (a forward-rolling wheel reads negative); undo that.
		Wheel.OmegaRadS = Setup ? -FMath::DegreesToRadians(Setup->GetRotationAngularVelocity()) : 0.f;
		const float RadiusM = Setup ? Setup->GetWheelRadius() * 0.01f : 0.38f;
		float Cap = OpenSpinAllowanceNm;
		if (Traction.Wheels.IsValidIndex(Index) && Traction.Wheels[Index].bInContact)
		{
			++ContactCount;
			const FGTWheelTraction& Tyre = Traction.Wheels[Index];
			Cap += Tyre.Load * 0.01f * Tyre.SurfaceFriction * Tyre.FrictionScale * RadiusM;   // kg cm/s^2 -> N
		}
		Wheel.CapNm = Cap;
		OmegaSum += Wheel.OmegaRadS;
	}
	float OmegaMean = OmegaSum / NumWheels;
	int32 DrivenContacts=ContactCount;
	if((Independent || Layout!=0) && NumWheels>=4)
	{
		OmegaMean=GTIndependentDrivetrain::DrivenOmega((Wheels[0].OmegaRadS+Wheels[1].OmegaRadS)*.5f,
			(Wheels[2].OmegaRadS+Wheels[3].OmegaRadS)*.5f,FrontShare);
		DrivenContacts=0;
		for(int32 I=0;I<4;++I)
			if((I<2 ? FrontShare>0 : FrontShare<1) && Traction.Wheels.IsValidIndex(I) && Traction.Wheels[I].bInContact) ++DrivenContacts;
	}

	// Gearbox input speed. The opted-in engines are integrated independently below.
	// The custom drivetrain owns wheel torque. Override only its local configuration;
	// never mutate Chaos setup, wheel CDOs or another pawn's authored settings.
	const FVehicleTransmissionConfig& Transmission=Movement.TransmissionSetup;
	const FVehicleEngineConfig& Engine = Movement.EngineSetup;
	const int32 NumGears = Upgraded ? 4 : FMath::Max(1, Transmission.ForwardGearRatios.Num());
	Gear = FMath::Clamp(Gear, 1, NumGears);
	// With the clutch open at a stop, select the launch gear without a shift cut.
	if(Independent && HandbrakeIn>.05f && FMath::Abs(ForwardSpeed)<ReverseSpeedThreshold)
	{
		Gear=1; ShiftTimer=0.f;
	}
	const float GearRatio = bReverse
		? (Transmission.ReverseGearRatios.Num() > 0 ? Transmission.ReverseGearRatios[0] : 3.4f)
		: Upgraded ? Package.Gears[Gear-1] : Transmission.ForwardGearRatios[Gear - 1];
	TotalRatio = (Upgraded ? Package.FinalRatio : Transmission.FinalRatio) * GearRatio * (bLowRange ? (Upgraded ? Package.LowRatio : LowRangeRatio) : 1.f);
	WheelRpm = FMath::Abs(OmegaMean) * TotalRatio * 60.f / (2.f * PI);
	if(!Independent) EngineRpm = FMath::Clamp(FMath::Max(Engine.EngineIdleRPM, WheelRpm), 0.f, Engine.MaxRPM * 1.05f);
	else EngineRpm=FMath::Max(Engine.EngineIdleRPM,EngineRpm);
	// Wheelspin in yielding soil must not trigger repeated upshift / torque-cut cycles.
	// Free engine revs and spinning wheels must not request an upshift.
	bool bSoilContact=false;
	for(const auto& Tyre : Tuning.Wheels) bSoilContact |= Tyre.bLandscapeSupport;
	const int32 ShiftWheel=FrontShare<=0 && NumWheels>=4 ? 2 : 0;
	const float ShiftRadius=Movement.Wheels[ShiftWheel] ? Movement.Wheels[ShiftWheel]->GetWheelRadius() : 38.f;
	const float RoadRpm=FMath::Abs(ForwardSpeed)/FMath::Max(1.f,ShiftRadius)*TotalRatio*60.f/(2.f*PI);
	RoadRpmForShift=RoadRpm;
	bWheelspinShiftHold=Independent && GTRangeRoverDrivetrain::IsWheelspin(WheelRpm,RoadRpm,Engine.EngineIdleRPM,DrivenContacts);
	const float ShiftRpm=(Independent || bSoilContact) ? FMath::Min(EngineRpm,FMath::Max(Engine.EngineIdleRPM,RoadRpm+500.f)) : EngineRpm;
	const float UpRPM=Upgraded ? Package.UpRPM : Transmission.ChangeUpRPM;
	const float DownRPM=Upgraded ? Package.DownRPM : Transmission.ChangeDownRPM;

	// Automatic gearbox on the engine speed, a torque cut while it changes.
	TimeSinceShift += DeltaSeconds;
	if (ShiftTimer > 0.f)
	{
		ShiftTimer -= DeltaSeconds;
	}
	else if (!bReverse && TimeSinceShift >= MinShiftIntervalSeconds && (!Independent || HandbrakeIn<=.05f))
	{
		if (ShiftRpm > UpRPM && Gear < NumGears && GTRangeRoverDrivetrain::CanShiftUp(bWheelspinShiftHold))
		{
			++Gear;
			ShiftTimer = Upgraded ? Package.ShiftSeconds : Transmission.GearChangeTime;
			TimeSinceShift = 0.f;
		}
		else if (ShiftRpm < DownRPM && Gear > 1 && GTRangeRoverDrivetrain::CanShiftDown(bWheelspinShiftHold,EngineRpm,DownRPM))
		{
			--Gear;
			ShiftTimer = Upgraded ? Package.ShiftSeconds : Transmission.GearChangeTime;
			TimeSinceShift = 0.f;
		}
	}
	MaxGearReached = FMath::Max(MaxGearReached, Gear);

	const float MaxTorque = FMath::Max(0.f, Tuning.MaxEngineTorque * Tuning.TorqueScale);
	AppliedTorqueScale=Tuning.TorqueScale;
	const FRichCurve* Curve = Engine.TorqueCurve.GetRichCurveConst();
	const float CurveValue = Curve && Curve->GetNumKeys() > 0 ? FMath::Max(0.f, Curve->Eval(EngineRpm)) : 1.f;
	float Torque = DriveInput * MaxTorque * CurveValue * (Upgraded ? GTRangeRoverDrivetrain::TorqueScale(SetupIndex,EngineRpm) : 1.f);
	if (EngineRpm >= Engine.MaxRPM)
	{
		Torque = 0.f;   // the limiter
	}
	// Use the pedal position for lift-off detection. Expedition's progressive map
	// must not turn a light throttle request into unintended engine braking.
	if (PedalInput <= 0.05f && WheelRpm > Engine.EngineIdleRPM)
	{
		Torque -= Engine.EngineBrakeEffect * MaxTorque * FMath::Clamp(WheelRpm / FMath::Max(1.f, Engine.MaxRPM), 0.f, 1.f);
	}
	if (ShiftTimer > 0.f)
	{
		Torque = 0.f;
	}
	EngineTorqueNm = Torque;
	if(Independent)
	{
		// Integrate engine and clutch together. The reaction that loads the engine is
		// exactly the torque sent into the gearbox, including flywheel energy on release.
		// Small substeps keep this stable across render-frame variations.
		const float Duration=FMath::Clamp(DeltaSeconds,0.f,.1f);
		const int32 Steps=FMath::Max(1,FMath::CeilToInt(Duration*120.f));
		const float Dt=Duration/Steps;
		// Keep shaft direction relative to the selected gear. Absolute wheel RPM
		// during rollback would incorrectly apply drive downhill through the clutch.
		const float SignedShaftRpm=OmegaMean*TotalRatio*60.f/(2.f*PI)*(bReverse ? -1.f : 1.f);
		float Sum=0.f;
		for(int32 Step=0;Step<Steps;++Step)
		{
			const float Value=Curve && Curve->GetNumKeys()>0 ? FMath::Max(0.f,Curve->Eval(EngineRpm)) : 1.f;
			float Combustion=DriveInput*MaxTorque*Value*(Upgraded ? GTRangeRoverDrivetrain::TorqueScale(SetupIndex,EngineRpm) : 1.f);
			if(EngineRpm>=Engine.MaxRPM || ShiftTimer>0.f) Combustion=0.f;
			EngineTorqueNm=Combustion;
			Sum+=GTRangeRoverDrivetrain::StepClutch(Dt,SignedShaftRpm,Combustion,Tuning.MaxEngineTorque,
				Engine.EngineIdleRPM,Engine.MaxRPM,HandbrakeIn>.05f || ShiftTimer>0.f,EngineRpm,ClutchEngagement,TotalRatio,Ferrari ? .38f : .65f,Ferrari ? 3.333333f : 2.5f);
		}
		Torque=Sum/Steps;
	}
	ClutchTorqueNm=Torque;
	const float Direction = bReverse ? -1.f : 1.f;
	const float DrivelineTorque = Torque * TotalRatio * DrivelineEfficiency * Direction;
	RequestedWheelTorqueNm=DrivelineTorque;

	// Centre diff between the axles, then an open or locked diff on each axle.
	// A modest coast coupling releases most LSD preload on lift-off. Full selectable
	// locks retain the existing behavior; Rally differs when those locks are off.
	const float LSDLoad=FMath::Lerp(.15f,1.f,DriveInput);
	const float CentreLock = bDiffLock ? CentreLockWhenOn : Upgraded ? Package.CentreLSD*LSDLoad : 0.f;
	const float AxleLock = bDiffLock ? AxleLockWhenOn : 0.f;
	const float FrontLock=FrontShare<=0 ? 0.f : bDiffLock ? AxleLock : Ferrari ? .25f*LSDLoad : Upgraded ? Package.FrontLSD*LSDLoad : 0.f;
	const float RearLock=FrontShare>=1 ? 0.f : bDiffLock ? AxleLock : Ferrari ? .25f*LSDLoad : Upgraded ? Package.RearLSD*LSDLoad : 0.f;
	float FrontTorque = DrivelineTorque * FrontShare;
	float RearTorque = DrivelineTorque * (1.f - FrontShare);
	if (NumWheels >= 4)
	{
		const float FrontCap = Wheels[0].CapNm + Wheels[1].CapNm;
		const float RearCap = Wheels[2].CapNm + Wheels[3].CapNm;
		const float FrontOmega = 0.5f * (Wheels[0].OmegaRadS + Wheels[1].OmegaRadS);
		const float RearOmega = 0.5f * (Wheels[2].OmegaRadS + Wheels[3].OmegaRadS);
		// A single driven axle has no centre differential. Keep the established AWD
		// split for the default car; do not accidentally turn RWD/FWD variants into AWD.
		if (FrontShare > 0.f && FrontShare < 1.f)
		{
			// Only an explicit AWD conversion uses the tuning control. Factory keeps its legacy split.
			Split(DrivelineTorque, FrontCap, RearCap, FrontOmega, RearOmega, CentreLock, FrontTorque, RearTorque,ConserveTorque,Layout==3 ? FrontShare : .5f);
		}
		Split(FrontTorque, Wheels[0].CapNm, Wheels[1].CapNm, Wheels[0].OmegaRadS, Wheels[1].OmegaRadS, FrontLock, Wheels[0].DriveTorqueNm, Wheels[1].DriveTorqueNm,ConserveTorque);
		Split(RearTorque, Wheels[2].CapNm, Wheels[3].CapNm, Wheels[2].OmegaRadS, Wheels[3].OmegaRadS, RearLock, Wheels[2].DriveTorqueNm, Wheels[3].DriveTorqueNm,ConserveTorque);
	}
	else
	{
		for (FGTDrivetrainWheel& Wheel : Wheels)
		{
			Wheel.DriveTorqueNm = DrivelineTorque / NumWheels;
		}
	}

	// Brakes: the foot brake on every wheel, the handbrake on the wheels that take it.
	bool bAnyDrive = false;
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		FGTDrivetrainWheel& Wheel = Wheels[Index];
		const UChaosVehicleWheel* Setup = Movement.Wheels[Index];
		const float FootBrake = BrakeInput * (Setup ? Setup->MaxBrakeTorque : 1500.f);
		const float Handbrake = (Setup && Setup->bAffectedByHandbrake) ? HandbrakeIn * Setup->MaxHandBrakeTorque : 0.f;
		Wheel.BrakeTorqueNm = FootBrake + Handbrake;
		Movement.SetDriveTorque(Wheel.DriveTorqueNm, Index);
		Movement.SetBrakeTorque(Wheel.BrakeTorqueNm, Index);
		bAnyDrive |= FMath::Abs(Wheel.DriveTorqueNm) > 1.f;
	}
	// A body Chaos put to sleep at a stop must be woken for the torque to count.
	if (bAnyDrive && Movement.UpdatedPrimitive && !Movement.UpdatedPrimitive->IsAnyRigidBodyAwake())
	{
		Movement.UpdatedPrimitive->WakeAllRigidBodies();
	}
}

FString UGTDrivetrainComponent::Describe() const
{
	FString Line = FString::Printf(TEXT("drivetrain gear=%d%s%s rpm=%.0f wheelRpm=%.0f ratio=%.2f engineNm=%.0f drive=%.2f brake=%.2f wheels:"),
		GetGear(), bLowRange ? TEXT(" LOW") : TEXT(""), bDiffLock ? TEXT(" LOCK") : TEXT(""), EngineRpm, WheelRpm, TotalRatio, EngineTorqueNm, DriveInput, BrakeInput);
	for (int32 Index = 0; Index < Wheels.Num(); ++Index)
	{
		Line += FString::Printf(TEXT(" [%d] T=%.0f B=%.0f cap=%.0f w=%.1f"), Index, Wheels[Index].DriveTorqueNm, Wheels[Index].BrakeTorqueNm, Wheels[Index].CapNm, Wheels[Index].OmegaRadS);
	}
	return Line;
}
