#include "Vehicle/GTCarPawn.h"

#include "Dressing/GTVegetationProbeComponent.h"
#include "Vehicle/GTBodyComponent.h"
#include "Vehicle/GTBodyStateComponent.h"
#include "Environment/GTEnvironmentComponent.h"
#include "Parts/GTPartSlotsComponent.h"
#include "Run/GTRunGameState.h"
#include "Weather/GTWeatherSubsystem.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTDashboardComponent.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTSprayComponent.h"
#include "Vehicle/GTVehicleAudioComponent.h"
#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTHullComponent.h"
#include "Vehicle/GTWaterDiag.h"
#include "Vehicle/GTVehicleAnimInstance.h"
#include "Vehicle/GTVehicleTuningComponent.h"
#include "Vehicle/GTSoilVehicleMovement.h"
#include "Vehicle/GTVehicleWheel.h"
#include "Vehicle/GTWinchComponent.h"
#include "Terrain/GTTrackPaintSubsystem.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTMudPatch.h"   // MR5: the mud chunks' channel
#include "Character/GTExposureComponent.h"
#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Core/GTPlayerController.h"
#include "Inventory/GTInventoryComponent.h"

#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "PhysicsEngine/BodyInstance.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/PlayerController.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "HAL/IConsoleManager.h"
#include "UObject/ConstructorHelpers.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ProfilingDebugging/CsvProfiler.h"

CSV_DEFINE_CATEGORY(GTVehicle, true);

static TAutoConsoleVariable<int32> CVarGTResponsiveSteering(TEXT("gt.Vehicle.ResponsiveSteering"),1,
	TEXT("High-range steering input response. 0 restores authored input filtering; 1 enables per-car strength."));
static TAutoConsoleVariable<int32> CVarGTCountersteerResponse(TEXT("gt.Vehicle.CountersteerResponse"),1,
	TEXT("Faster explicit keyboard direction reversal on firm high-range ground. 0 retains RH3 reversal rates; no change to wheel lock or tyre forces."));

namespace
{
	const FName HeadSocketName(TEXT("Head"));

	UInputAction* MakeAction(UObject* Outer, const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* Action = NewObject<UInputAction>(Outer, Name);
		Action->ValueType = Type;
		return Action;
	}

	void MapKey(UInputMappingContext* Context, UInputAction* Action, const FKey& Key, bool bNegate = false, bool bDeadZone = false)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(Action, Key);
		if (bDeadZone)
		{
			// Analogue sticks and triggers drift; without this a resting stick steers the car.
			UInputModifierDeadZone* DeadZone = NewObject<UInputModifierDeadZone>(Context);
			DeadZone->LowerThreshold = 0.2f;
			DeadZone->UpperThreshold = 0.98f;
			Mapping.Modifiers.Add(DeadZone);
		}
		if (bNegate)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(Context));
		}
	}
}

AGTCarPawn::AGTCarPawn(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UGTSoilVehicleMovement>(VehicleMovementComponentName))
{
	PrimaryActorTick.bCanEverTick = true;

	// The blockout skeletal mesh. A Blueprint child can swap it; the wheel bone names below must match.
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> CarMesh(
		TEXT("/Game/GrandTour/Vehicles/Bodies/RangeRover/SK_RangeRover.SK_RangeRover"));
	if (CarMesh.Succeeded())
	{
		GetMesh()->SetSkeletalMeshAsset(CarMesh.Object);
	}
	GetMesh()->SetAnimInstanceClass(UGTVehicleAnimInstance::StaticClass());
	GetMesh()->BodyInstance.bSimulatePhysics = true;

	UChaosWheeledVehicleMovementComponent* Move = GetChaosMovement();
	check(Move);

	Move->WheelSetups.SetNum(4);
	Move->WheelSetups[0].WheelClass = UGTVehicleWheelFront::StaticClass();
	Move->WheelSetups[0].BoneName = TEXT("Wheel_FL");
	Move->WheelSetups[1].WheelClass = UGTVehicleWheelFront::StaticClass();
	Move->WheelSetups[1].BoneName = TEXT("Wheel_FR");
	Move->WheelSetups[2].WheelClass = UGTVehicleWheelRear::StaticClass();
	Move->WheelSetups[2].BoneName = TEXT("Wheel_RL");
	Move->WheelSetups[3].WheelClass = UGTVehicleWheelRear::StaticClass();
	Move->WheelSetups[3].BoneName = TEXT("Wheel_RR");

	// Range Rover Classic: ~2.1 t kerb weight, 3.9 V8 (~310 Nm), permanent four-wheel drive.
	Move->Mass = 2100.f;
	Move->ChassisWidth = 186.f;
	Move->ChassisHeight = 179.f;
	Move->DragCoefficient = 0.45f;
	// The mesh origin is 22.6 cm behind the axle midpoint; put the mass centre between the axles, 60 cm up.
	// Applied in the root body's frame, which is why the root bone must import with identity rotation.
	Move->bEnableCenterOfMassOverride = true;
	Move->CenterOfMassOverride = FVector(22.6f, 0.f, 60.f);
	// Stage 4: the drivetrain is ours (UGTDrivetrainComponent); Chaos's engine, gearbox and reverse-as-brake are off.
	Move->bReverseAsBrake = false;
	Move->bMechanicalSimEnabled = false;
	// Chaos lets a vehicle sleep on any slope under 30 degrees and a sleeping body is not integrated, so a car with
	// the brakes off would sit on a hill for free. Sleep only when level; the handbrake is what holds a parked car.
	Move->SleepSlopeLimit = 0.9995f;
	// MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5): the wheels' suspension traces ignore the mud chunks' channel, so a wheel
	// never rides up on a chunk (the traction breaks the ones its stamp footprint reaches); the body still bumps and pushes them.
	Move->SetWheelTraceResponseToChannel(AGTMudPatch::MudChunkChannel, ECR_Ignore);

	// Owner's LiDAR driving trial: stronger pull in both transfer-case ranges.
	Move->EngineSetup.MaxTorque = 480.f;
	Move->EngineSetup.MaxRPM = 5000.f;
	Move->EngineSetup.EngineIdleRPM = 800.f;
	Move->EngineSetup.EngineBrakeEffect = 0.05f;
	if (FRichCurve* Torque = Move->EngineSetup.TorqueCurve.GetRichCurve())
	{
		Torque->Reset();
		Torque->AddKey(0.f, 0.65f);
		Torque->AddKey(800.f, 0.85f);
		Torque->AddKey(1500.f, 0.95f);
		Torque->AddKey(2500.f, 1.0f);
		Torque->AddKey(4000.f, 0.9f);
		Torque->AddKey(5000.f, 0.65f);
	}

	Move->TransmissionSetup.bUseAutomaticGears = true;
	Move->TransmissionSetup.bUseAutoReverse = true;
	Move->TransmissionSetup.FinalRatio = 3.54f;
	Move->TransmissionSetup.ForwardGearRatios = { 3.32f, 2.13f, 1.40f, 1.00f };
	Move->TransmissionSetup.ReverseGearRatios = { 3.40f };
	Move->TransmissionSetup.ChangeUpRPM = 4200.f;
	Move->TransmissionSetup.ChangeDownRPM = 1800.f;
	Move->TransmissionSetup.GearChangeTime = 0.4f;

	Move->DifferentialSetup.DifferentialType = EVehicleDifferential::AllWheelDrive;
	Move->DifferentialSetup.FrontRearSplit = 0.5f;

	// Steering by speed (driving feel stage 1): full lock (35 deg) at rest, about 12 deg at 60 km/h and 6 at 120,
	// so a keyboard tap at speed asks the front tyres for a slide, not a spin. Chaos reads the curve in mph.
	if (FRichCurve* Steer = Move->SteeringSetup.SteeringCurve.GetRichCurve())
	{
		Steer->Reset();
		Steer->AddKey(0.f, 1.f);
		Steer->AddKey(12.f, 0.72f);    // 20 km/h: 25 deg
		Steer->AddKey(25.f, 0.5f);     // 40 km/h: 17.5
		Steer->AddKey(37.f, 0.34f);    // 60 km/h: 12
		Steer->AddKey(50.f, 0.26f);    // 80 km/h: 9
		Steer->AddKey(62.f, 0.2f);     // 100 km/h: 7
		Steer->AddKey(75.f, 0.17f);    // 120 km/h: 6
		Steer->AddKey(100.f, 0.14f);   // 160 km/h: 5
	}

	DriverCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("DriverCamera"));
	DriverCamera->SetupAttachment(GetMesh());
	DriverCamera->SetRelativeLocation(DriverEyeOffset);
	DriverCamera->bUsePawnControlRotation = false;
	DriverCamera->SetFieldOfView(90.f);

	// Chase camera (C / right stick click): mouse/right-stick orbit with a level horizon,
	// a little lag and collision against the ground or a wall. Off until toggled.
	ChaseArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("ChaseArm"));
	ChaseArm->SetupAttachment(GetMesh());
	ChaseArm->SetRelativeLocation(FVector(0.f, 0.f, ChasePivotHeight));
	ChaseArm->SetRelativeRotation(FRotator(ChasePitch, 0.f, 0.f));
	ChaseArm->TargetArmLength = ChaseArmLength;
	ChaseArm->bUsePawnControlRotation = false;
	ChaseArm->bInheritPitch = false;
	ChaseArm->bInheritRoll = false;
	ChaseArm->bInheritYaw = true;
	ChaseArm->bEnableCameraLag = true;
	ChaseArm->CameraLagSpeed = ChaseLagSpeed;
	ChaseArm->CameraLagMaxDistance = 250.f;
	ChaseArm->bEnableCameraRotationLag = true;
	ChaseArm->CameraRotationLagSpeed = ChaseRotationLagSpeed;
	ChaseArm->bDoCollisionTest = true;
	ChaseArm->ProbeSize = 20.f;
	ChaseCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("ChaseCamera"));
	ChaseCamera->SetupAttachment(ChaseArm, USpringArmComponent::SocketName);
	ChaseCamera->bUsePawnControlRotation = false;
	ChaseCamera->SetFieldOfView(ChaseFieldOfView);
	ChaseCamera->bAutoActivate = false;

	Traction = CreateDefaultSubobject<UGTTractionComponent>(TEXT("Traction"));
	Condition = CreateDefaultSubobject<UGTConditionComponent>(TEXT("Condition"));
	Hull = CreateDefaultSubobject<UGTHullComponent>(TEXT("Hull"));
	Tuning = CreateDefaultSubobject<UGTVehicleTuningComponent>(TEXT("Tuning"));
	Body = CreateDefaultSubobject<UGTBodyComponent>(TEXT("Body"));
	BodyState = CreateDefaultSubobject<UGTBodyStateComponent>(TEXT("BodyState"));
	Spray = CreateDefaultSubobject<UGTSprayComponent>(TEXT("Spray"));
	Audio = CreateDefaultSubobject<UGTVehicleAudioComponent>(TEXT("Audio"));
	RangeRoverAudio = CreateDefaultSubobject<UGTRangeRoverAudioComponent>(TEXT("RangeRoverAudio"));
	Winch = CreateDefaultSubobject<UGTWinchComponent>(TEXT("Winch"));
	Drivetrain = CreateDefaultSubobject<UGTDrivetrainComponent>(TEXT("Drivetrain"));
	Boot = CreateDefaultSubobject<UGTInventoryComponent>(TEXT("Boot"));
	Boot->MaxWeightKg = 250.f;
	Environment = CreateDefaultSubobject<UGTEnvironmentComponent>(TEXT("Environment"));
	Parts = CreateDefaultSubobject<UGTPartSlotsComponent>(TEXT("Parts"));
	VegProbe = CreateDefaultSubobject<UGTVegetationProbeComponent>(TEXT("VegProbe"));

	// Cluster 48 cm ahead of and 17 cm below the driver's eye, tilted 15 degrees up towards it, so the
	// dials sit just above the steering wheel rim (the blockout's dash top is at Z 120 from X 80).
	Dashboard = CreateDefaultSubobject<UGTDashboardComponent>(TEXT("Dashboard"));
	Dashboard->SetupAttachment(GetMesh());
	Dashboard->SetRelativeLocationAndRotation(FVector(58.f, -40.f, 121.f), FRotator(75.f, 0.f, 0.f));
}

UChaosWheeledVehicleMovementComponent* AGTCarPawn::GetChaosMovement() const
{
	return Cast<UChaosWheeledVehicleMovementComponent>(GetVehicleMovementComponent());
}

void AGTCarPawn::NotifyHazardContact(FGameplayTag HazardTag)
{
	HazardContactTimes.Add(HazardTag, GetWorld()->GetTimeSeconds());
}

bool AGTCarPawn::IsInHazard(FGameplayTag HazardTag) const
{
	const double* Last = HazardContactTimes.Find(HazardTag);
	return Last && GetWorld()->GetTimeSeconds() - *Last < 0.25;
}

void AGTCarPawn::BeginPlay()
{
	Super::BeginPlay();

	// Chaos's suspension constraint swaps the ground normal for straight-up at low speed on slopes flatter than
	// p.Chaos.Suspension.SlopeThreshold (cos 45 deg by default) "to stop vehicles sliding slowly down steep slopes":
	// a parked car stays put with no brakes and a climbing car gets an uphill push the engine never made (a 35 %
	// slope was climbed in high range from a standing start on 5.8 kN against 6.8 kN of grade). No slope qualifies
	// at 1.0, so the tyres and the brakes are all that hold the car (driving feel stage 4).
	if (IConsoleVariable* SlopeHack = IConsoleManager::Get().FindConsoleVariable(TEXT("p.Chaos.Suspension.SlopeThreshold")))
	{
		SlopeHack->Set(1.0f, ECVF_SetByGameSetting);
	}
	// Chaos's island sleep put the chassis to sleep the moment it stopped on a slope under full throttle, and a game-thread
	// wake never landed against the physics thread's sleep (the drivetrain test's low-range standing start: 0.0 m, the
	// wheels' torque ignored for 8 s). A body whose sleep thresholds are zero never sleeps (IslandManager: "all zeroes
	// means never sleep"), so the chassis gets a zero multiplier; the vehicle's own explicit sleep at rest on the level
	// (SleepSlopeLimit) still applies, and the handbrake is what holds a parked car.
	if (FBodyInstance* Chassis = GetMesh()->GetBodyInstance())
	{
		Chassis->SleepFamily = ESleepFamily::Custom;
		Chassis->CustomSleepThresholdMultiplier = 0.f;
		FPhysicsCommand::ExecuteWrite(Chassis->GetPhysicsActor(), [](const FPhysicsActorHandle& Actor)
		{
			FPhysicsInterface::SetSleepThresholdMultiplier_AssumesLocked(Actor, 0.f);
		});
	}
	bUseHeadSocket = GetMesh()->DoesSocketExist(HeadSocketName);
	if (bUseHeadSocket)
	{
		DriverCamera->AttachToComponent(GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, HeadSocketName);
	}
	else
	{
		DriverCamera->SetRelativeLocation(DriverEyeOffset);
	}
	// Hit events on a skeletal mesh need the flag on the physics bodies, not only on the component.
	GetMesh()->SetNotifyRigidBodyCollision(true);
	GetMesh()->OnComponentHit.AddDynamic(this, &AGTCarPawn::OnBodyHit);
	// Authored fleet cars start parked. The controller releases these inputs when entering.
	if (!GetController())
	{
		GetChaosMovement()->SetHandbrakeInput(true);
	}
}

void AGTCarPawn::Tick(float DeltaSeconds)
{
	TRACE_CPUPROFILER_EVENT_SCOPE(GTCar_Tick);
	CSV_SCOPED_TIMING_STAT(GTVehicle, Tick);
	Super::Tick(DeltaSeconds);

	if (UChaosWheeledVehicleMovementComponent* Move = GetChaosMovement())
	{
		const float ForwardSpeed = Move->GetForwardSpeed();
		// The weather's ground wetness reaches the tyres here (ARCHITECTURE 6d) and the body through the traction.
		if (const UGTWeatherSubsystem* Weather = GetWorld()->GetSubsystem<UGTWeatherSubsystem>())
		{
			Traction->Wetness = Weather->GetWetness();
			// MudRunner MR2: the rain on the car (none under cover) washes its mud slowly.
			BodyState->Rain = Weather->GetRainAt(GetActorLocation());
		}
		{
			TRACE_CPUPROFILER_EVENT_SCOPE(GTCar_Traction);
			CSV_SCOPED_TIMING_STAT(GTVehicle, Traction);
			Traction->Update(DeltaSeconds, *Move, ForwardSpeed);
		}
		// The current on the body, after the traction (it reads the wheels' contacts for the hull's base plane).
		{
			TRACE_CPUPROFILER_EVENT_SCOPE(GTCar_Hull);
			CSV_SCOPED_TIMING_STAT(GTVehicle, Hull);
			Hull->Update(DeltaSeconds, *Move, *Traction);
		}
		Condition->UpdateFlooding(DeltaSeconds, Traction->FrontWaterDepthM);
		{
			TRACE_CPUPROFILER_EVENT_SCOPE(GTCar_PaintTracks);
			CSV_SCOPED_TIMING_STAT(GTVehicle, PaintTracks);
			PaintTracks(DeltaSeconds, *Move);
		}
		{
			TRACE_CPUPROFILER_EVENT_SCOPE(GTCar_BodyState);
			CSV_SCOPED_TIMING_STAT(GTVehicle, BodyState);
			BodyState->Update(DeltaSeconds, *Traction, ForwardSpeed);
		}
		// Water stage W4: the spray takes the hull too, for the bow spray's submerged height.
		{
			TRACE_CPUPROFILER_EVENT_SCOPE(GTCar_Spray);
			CSV_SCOPED_TIMING_STAT(GTVehicle, Spray);
			Spray->Update(DeltaSeconds, *Traction, *Move, ForwardSpeed, *Condition, Hull);
		}
		Condition->Update(DeltaSeconds, Drivetrain->GetDriveInput(), Drivetrain->GetEngineRpm(), Move->EngineSetup.MaxRPM);
		{
			TRACE_CPUPROFILER_EVENT_SCOPE(GTCar_Body);
			CSV_SCOPED_TIMING_STAT(GTVehicle, Body);
			Body->Update(DeltaSeconds, *Condition, *BodyState, GetMesh()->GetComponentVelocity());
		}
		Audio->Update(DeltaSeconds, *Move, *Traction, *Condition, Drivetrain->GetEngineRpm(), Drivetrain->GetDriveInput());
		const AGTRunGameState* RunState = GetWorld()->GetGameState<AGTRunGameState>();
		Environment->Update(DeltaSeconds, RunState ? RunState->GetLeg() : nullptr, RunState ? RunState->GetProgress() : 0.f,
			Drivetrain->GetDriveInput(), ForwardSpeed, Condition);
		Parts->Update(DeltaSeconds);
		Tuning->UpdateAndApply(DeltaSeconds, *Move, Traction, Condition, Environment, Parts);
		Drivetrain->Update(DeltaSeconds, *Move, *Traction, Tuning->GetCurrent());
		{
		CSV_SCOPED_TIMING_STAT(GTVehicle, SteeringResponse);
		float SinkCm=0.f,WaterCm=0.f;
		bool bSoftSurface=false;
		for(const auto& Wheel:Traction->Wheels)
		{
			if(!Wheel.bInContact)continue;
			SinkCm=FMath::Max(SinkCm,Wheel.Sinkage*100.f);
			WaterCm=FMath::Max(WaterCm,Wheel.WaterDepthM*100.f);
			bSoftSurface|=Wheel.SurfaceTag==GTTags::Surface_Mud || Wheel.SurfaceTag==GTTags::Surface_Bog || Wheel.SurfaceTag==GTTags::Surface_Snow;
		}
		for(const auto& Wheel:Tuning->GetCurrent().Wheels)SinkCm=FMath::Max(SinkCm,Wheel.SinkageCm);
		ResponsiveSteering.Update(Move->SteeringInputRate,FGTResponsiveSteering::Weight(
			Drivetrain->IsLowRange(),bSoftSurface,SinkCm,WaterCm,
			CVarGTResponsiveSteering.GetValueOnGameThread()!=0 ? HighSpeedSteeringResponse : 0.f));
        if(auto* SoilMove=Cast<UGTSoilVehicleMovement>(Move))
        {
            ResponsiveSteering.UpdateReversal(Move->SteeringInputRate,RawSteer,SoilMove->GetFilteredSteeringInput(),
                CVarGTCountersteerResponse.GetValueOnGameThread()!=0 ? FMath::SmoothStep(30.f,60.f,FMath::Abs(ForwardSpeed)*.036f) : 0.f,
                Tuning->GetCurrent().SteeringBias);
            SoilMove->UpdateRallySuspension(DeltaSeconds,FGTResponsiveSteering::Weight(
                Drivetrain->IsLowRange(),bSoftSurface,SinkCm,WaterCm,1.f));
        }
		}
		Move->SetSteeringInput(FMath::Clamp(RawSteer + Tuning->GetCurrent().SteeringBias, -1.f, 1.f));
		Dashboard->UpdateFromVehicle(DeltaSeconds, *Move, *Condition, *Traction, Environment, IsInHazard(GTTags::Hazard_Radiation),
			Drivetrain->GetEngineRpm(), Drivetrain->IsDiffLocked(), Drivetrain->IsLowRange());
		Winch->Update(DeltaSeconds, *GetMesh(), *Condition);
		// Leg dressing LD5: soft vegetation in the car's footprint resists it (nothing to do where there is none).
		{
			TRACE_CPUPROFILER_EVENT_SCOPE(GTCar_VegetationProbe);
			CSV_SCOPED_TIMING_STAT(GTVehicle, VegetationProbe);
			VegProbe->Update(DeltaSeconds, *GetMesh());
		}
		GTWaterDiag::TickCar(*this);   // diagnostic only: logs when gt.Water.Diag is on, reads nothing back
	}
	UpdateCamera(DeltaSeconds);
}

// ---- on foot: the car as an interactable ----------------------------------------------------------

AGTCarPawn::ECarInteraction AGTCarPawn::ResolveInteraction(const FGTInteractionQuery& Query, EGTDamageRegion& OutRegion, int32& OutDoor) const
{
	OutDoor = INDEX_NONE;
	const AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (!Character || Character->IsInCar())
	{
		return ECarInteraction::None;
	}
	const FVector Local = GetMesh()->GetComponentTransform().InverseTransformPosition(Query.HitLocation);
	OutRegion = UGTConditionComponent::ResolveRegion(Local);
	if (Character->HasToolTag(GTTags::Tool_Repair) && Condition->IsRegionDamaged(OutRegion))
	{
		return Character->GetInventory()->Has(GTItems::Scrap, RepairCostScrap) ? ECarInteraction::Repair : ECarInteraction::RepairNoScrap;
	}
	if (Character->IsCarryingHook())
	{
		return ECarInteraction::None;
	}
	// Doors: a hit on a door panel toggles it; a hit on the body inside a door's outline means the door
	// is shut in front of you, or you are looking into the doorway (get in at the front).
	if (Body)
	{
		int32 Door = Body->DoorForComponent(Query.HitComponent);
		const bool bOnPanel = Door != INDEX_NONE;
		if (!bOnPanel)
		{
			Door = Body->DoorAtLocalPoint(Local);
		}
		if (Door != INDEX_NONE)
		{
			OutDoor = Door;
			if (bOnPanel || !Body->IsDoorwayClear(Door))
			{
				return Body->IsDoorOpen(Door) ? ECarInteraction::CloseDoor : ECarInteraction::OpenDoor;
			}
			if (Body->IsDoorFront(Door))
			{
				return ECarInteraction::Enter;
			}
			return Body->IsDoorDetached(Door) ? ECarInteraction::None : ECarInteraction::CloseDoor;
		}
	}
	if (Local.X > 150.f && Winch && Winch->CanTakeHook() && !Character->GetCurrentTool())
	{
		return ECarInteraction::TakeHook;
	}
	// Section 51: at the front with the hook out on an anchor, E lets it go (the winch stows it and the cable rewinds).
	if (Local.X > 150.f && Winch && Winch->GetState() == EGTWinchState::Attached && !Character->GetCurrentTool())
	{
		return ECarInteraction::ReleaseWinch;
	}
	if (Local.X < -150.f)
	{
		return ECarInteraction::Boot;
	}
	if (bEnterNeedsOpenDoor && Body && Body->GetDriverDoor() != INDEX_NONE)
	{
		return ECarInteraction::EnterNeedsDoor;
	}
	return ECarInteraction::Enter;
}

FGTInteractionOffer AGTCarPawn::GetInteractionOffer(const FGTInteractionQuery& Query) const
{
	EGTDamageRegion Region = EGTDamageRegion::None;
	int32 Door = INDEX_NONE;
	const AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	switch (ResolveInteraction(Query, Region, Door))
	{
	case ECarInteraction::OpenDoor:
		return FGTInteractionOffer::Available(FString::Printf(TEXT("Open %s"), *Body->DoorName(Door)), DoorHoldTime);
	case ECarInteraction::CloseDoor:
		return FGTInteractionOffer::Available(FString::Printf(TEXT("Close %s"), *Body->DoorName(Door)), DoorHoldTime);
	case ECarInteraction::EnterNeedsDoor:
		return FGTInteractionOffer::Unavailable(TEXT("Open a front door to get in"));
	case ECarInteraction::Repair:
		return FGTInteractionOffer::Available(FString::Printf(TEXT("Repair %s (%d scrap)"), UGTConditionComponent::RegionName(Region), RepairCostScrap), RepairHoldTime);
	case ECarInteraction::RepairNoScrap:
		return FGTInteractionOffer::Unavailable(FString::Printf(TEXT("Repair %s needs %d scrap"), UGTConditionComponent::RegionName(Region), RepairCostScrap));
	case ECarInteraction::TakeHook:
		return FGTInteractionOffer::Available(TEXT("Take winch hook"), 0.3f);
	case ECarInteraction::ReleaseWinch:
		return FGTInteractionOffer::Available(TEXT("Release winch"), 0.3f);
	case ECarInteraction::Boot:
		return FGTInteractionOffer::Available(Character && Character->IsBootOpen() ? TEXT("Close boot") : TEXT("Open boot"), 0.2f);
	case ECarInteraction::Enter:
		return FGTInteractionOffer::Available(TEXT("Get in"), 0.2f);
	default:
		return FGTInteractionOffer::Unavailable(Character && Character->IsCarryingHook() ? TEXT("Hook in hand: attach it to an anchor or drop it (G)") : TEXT(""));
	}
}

void AGTCarPawn::Interact(const FGTInteractionQuery& Query)
{
	EGTDamageRegion Region = EGTDamageRegion::None;
	int32 Door = INDEX_NONE;
	AGTPlayerCharacter* Character = Cast<AGTPlayerCharacter>(Query.Instigator);
	if (!Character)
	{
		return;
	}
	switch (ResolveInteraction(Query, Region, Door))
	{
	case ECarInteraction::OpenDoor:
		Body->SetDoorOpen(Door, true);
		break;
	case ECarInteraction::CloseDoor:
		Body->SetDoorOpen(Door, false);
		break;
	case ECarInteraction::Repair:
		Character->GetInventory()->Remove(GTItems::Scrap, RepairCostScrap);
		Condition->RepairRegion(Region, RepairAmount);
		++FieldRepairs;
		break;
	case ECarInteraction::TakeHook:
		Winch->TakeHook(Character);
		break;
	case ECarInteraction::ReleaseWinch:
		Winch->Release();
		break;
	case ECarInteraction::Boot:
		if (Character->IsBootOpen()) { Character->CloseBoot(); } else { Character->OpenBoot(this); }
		break;
	case ECarInteraction::Enter:
		if (AGTPlayerController* PC = Cast<AGTPlayerController>(Character->GetController()))
		{
			if (Door == INDEX_NONE && Body)
			{
				// No doorway used (doors not required): the driver's door swings open for you.
				Door = Body->GetDriverDoor();
				if (Door != INDEX_NONE && !Body->IsDoorwayClear(Door))
				{
					Body->SetDoorOpen(Door, true);
				}
			}
			PendingEnterDoor = Door;
			PC->EnterVehicle(this);
		}
		break;
	default:
		break;
	}
}

FVector AGTCarPawn::FindExitLocation(float CapsuleRadius, float CapsuleHalfHeight) const
{
	const FTransform& CarTransform = GetMesh()->GetComponentTransform();
	UWorld* World = GetWorld();
	FCollisionQueryParams GroundParams(SCENE_QUERY_STAT(GTExitGround), false, this);
	FCollisionQueryParams ClearParams(SCENE_QUERY_STAT(GTExitClear), false);
	const FCollisionShape Capsule = FCollisionShape::MakeCapsule(CapsuleRadius, CapsuleHalfHeight);
	FVector Fallback = FVector::ZeroVector;
	// Just behind the driver's door first (it swings open as you get out), then the fixed spots.
	TArray<FVector> Candidates;
	if (Body && Body->GetDriverDoor() != INDEX_NONE)
	{
		Candidates.Add(Body->GetExitSpotBehindDoor(Body->GetDriverDoor(), CapsuleRadius));
	}
	Candidates.Append(ExitOffsets);
	for (int32 Index = 0; Index < Candidates.Num(); ++Index)
	{
		const FVector Candidate = CarTransform.TransformPosition(Candidates[Index]);
		float GroundZ = Candidate.Z;
		FHitResult Hit;
		if (World->LineTraceSingleByChannel(Hit, Candidate + FVector(0.f, 0.f, 150.f), Candidate - FVector(0.f, 0.f, 300.f), ECC_Visibility, GroundParams))
		{
			GroundZ = Hit.ImpactPoint.Z;
		}
		const FVector Location(Candidate.X, Candidate.Y, GroundZ + CapsuleHalfHeight + 2.f);
		if (Index == 0)
		{
			Fallback = Location;
		}
		if (!World->OverlapBlockingTestByChannel(Location, FQuat::Identity, ECC_Pawn, Capsule, ClearParams))
		{
			return Location;
		}
		// Blocked at ground level: a low step at the capsule's foot (the lift's edge, a kerb) should not send you
		// round to the other door, so stand on it as walking would (the character's default step height).
		const float ExitStepUpCm = 45.f;
		const FVector Raised = Location + FVector(0.f, 0.f, ExitStepUpCm);
		FHitResult StepHit;
		// The contact must be a step, not the edge of something taller: the capsule's rounded foot clears a much higher
		// obstacle near its rim, so the raised overlap test alone would stand you on a 70 cm crate.
		if (!World->OverlapBlockingTestByChannel(Raised, FQuat::Identity, ECC_Pawn, Capsule, ClearParams)
			&& World->SweepSingleByChannel(StepHit, Raised, Location, FQuat::Identity, ECC_Pawn, Capsule, ClearParams) && !StepHit.bStartPenetrating
			&& StepHit.ImpactPoint.Z - GroundZ <= ExitStepUpCm)
		{
			return StepHit.Location + FVector(0.f, 0.f, 1.f);
		}
	}
	return Fallback;
}


void AGTCarPawn::PaintTracks(float DeltaSeconds, const UChaosWheeledVehicleMovementComponent& Move)
{
	UGTTrackPaintSubsystem* Paint = GetWorld()->GetSubsystem<UGTTrackPaintSubsystem>();
	if (!Paint)
	{
		return;
	}
	if (IsPlayerControlled())
	{
		Paint->SetFocus(GetActorLocation());
	}
	const int32 NumWheels = FMath::Min(Traction->Wheels.Num(), Move.GetNumWheels());
	if (LastStampPoints.Num() != NumWheels)
	{
		LastStampPoints.SetNum(NumWheels);
		LastStampValid.Init(false, NumWheels);
	}
	if (LastCarryPoints.Num() != NumWheels)
	{
		LastCarryPoints.SetNum(NumWheels);
		LastCarryValid.Init(false, NumWheels);
		CarryToNextCm.Init(0.f, NumWheels);
		CarryDistanceCm.Init(0.f, NumWheels);
		CarryNoiseKeys.Init(0u, NumWheels);
		CarrySeeds.SetNum(NumWheels);
		for (int32 Index = 0; Index < NumWheels; ++Index)
		{
			CarrySeeds[Index] = static_cast<int32>(HashCombine(GetUniqueID(), 7919u * (Index + 1)) & 0x7fffffff);
		}
	}
	// Inside a mud patch the mud field is the record (docs/MUD_DEFORMATION_PLAN.md stage C); the paint keeps dirt and snow.
	const UGTMudSubsystem* Mud = GetWorld()->GetSubsystem<UGTMudSubsystem>();
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		const FGTWheelTraction& Wheel = Traction->Wheels[Index];
		const float Strength = Wheel.bInContact ? Wheel.SinkageFraction * Wheel.TrackDepth : 0.f;
		const FVector Point = Move.GetWheelState(Index).ContactPoint;
		// MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md): a tyre carrying mud lays it outside every patch as broken clumps
		// (UGTTrackPaintSubsystem::AddCarriedMud: G coverage, B wetness), from where it was last tick in contact.
		const bool bInPatch = Mud && Mud->PatchAt(FVector2D(Point.X, Point.Y));
		const bool bCarryContinuous = LastCarryValid[Index] && FVector::DistSquared(LastCarryPoints[Index], Point) < FMath::Square(500.f);
		if (Wheel.bInContact && !bInPatch && bCarryContinuous && Wheel.MudLoad > Paint->MinCarryLoad)
		{
			const float CarryWidth = Move.Wheels.IsValidIndex(Index) && Move.Wheels[Index] ? Move.Wheels[Index]->WheelWidth : 25.f;
			FGTMudCarryState Carry;
			Carry.ToNextCm = CarryToNextCm[Index];
			Carry.Seed = CarrySeeds[Index];
			Carry.DistanceCm = CarryDistanceCm[Index];
			Carry.NoiseKey = CarryNoiseKeys[Index];
			Paint->AddCarriedMud(Carry, LastCarryPoints[Index], Point, CarryWidth, Wheel.MudLoad);
			CarryToNextCm[Index] = Carry.ToNextCm;
			CarrySeeds[Index] = Carry.Seed;
			CarryDistanceCm[Index] = Carry.DistanceCm;
			CarryNoiseKeys[Index] = Carry.NoiseKey;
		}
		LastCarryPoints[Index] = Point;
		LastCarryValid[Index] = Wheel.bInContact;
		if (Strength < 0.02f || bInPatch)
		{
			LastStampValid[Index] = false;
			continue;
		}
		const float Width = Move.Wheels.IsValidIndex(Index) && Move.Wheels[Index] ? Move.Wheels[Index]->WheelWidth : 25.f;
		// A streak from where the wheel was last tick, unless it just started sinking or was teleported.
		const bool bContinuous = LastStampValid[Index] && FVector::DistSquared(LastStampPoints[Index], Point) < FMath::Square(500.f);
		Paint->AddWheelStamp(bContinuous ? LastStampPoints[Index] : Point, Point, Width, Strength, DeltaSeconds);
		LastStampPoints[Index] = Point;
		LastStampValid[Index] = true;
	}
}

void AGTCarPawn::UpdateCamera(float DeltaSeconds)
{
	const double Now = GetWorld()->GetTimeSeconds();
	if (Now - LastLookInputTime > LookRecentreDelay && !LookOffset.IsNearlyZero())
	{
		LookOffset = FMath::RInterpTo(LookOffset, FRotator::ZeroRotator, DeltaSeconds, LookRecentreSpeed);
	}

	// Follow the chassis with lag; remove part of its roll and pitch so rough ground doesn't nauseate.
	const FRotator CarRotation = GetMesh()->GetComponentRotation();
	const FRotator Target(
		CarRotation.Pitch * (1.f - StableHorizon) + LookOffset.Pitch,
		CarRotation.Yaw + LookOffset.Yaw,
		CarRotation.Roll * (1.f - StableHorizon));
	// Eye point: rigid with the seat in the horizontal plane, damped vertically so bumps are softened.
	const FVector SeatLocation = bUseHeadSocket
		? GetMesh()->GetSocketLocation(HeadSocketName)
		: GetMesh()->GetComponentTransform().TransformPosition(DriverEyeOffset);
	if (!bCameraInitialised)
	{
		SmoothedCameraRotation = Target;
		SmoothedCameraZ = SeatLocation.Z;
		bCameraInitialised = true;
	}
	else
	{
		SmoothedCameraRotation = FMath::RInterpTo(SmoothedCameraRotation, Target, DeltaSeconds, CameraLagSpeed);
		SmoothedCameraZ = FMath::FInterpTo(SmoothedCameraZ, SeatLocation.Z, DeltaSeconds, CameraVerticalLagSpeed);
		SmoothedCameraZ = FMath::Clamp(SmoothedCameraZ, SeatLocation.Z - CameraMaxVerticalLag, SeatLocation.Z + CameraMaxVerticalLag);
	}
	DriverCamera->SetWorldLocation(FVector(SeatLocation.X, SeatLocation.Y, SmoothedCameraZ));
	DriverCamera->SetWorldRotation(SmoothedCameraRotation);
}

void AGTCarPawn::OnBodyHit(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent,
                           FVector NormalImpulse, const FHitResult& Hit)
{
	const UChaosWheeledVehicleMovementComponent* Move = GetChaosMovement();
	if (!Move || !Condition || Move->Mass <= 0.f)
	{
		return;
	}
	const FTransform& CarTransform = GetMesh()->GetComponentTransform();
	const FVector LocalPosition = CarTransform.InverseTransformPosition(Hit.ImpactPoint);
	const FVector LocalDirection = CarTransform.InverseTransformVectorNoScale(-Hit.ImpactNormal);
	const float DeltaV = NormalImpulse.Size() / Move->Mass;   // kg cm/s over kg = cm/s
	UE_LOG(LogTemp, Verbose, TEXT("AGTCarPawn hit %s deltaV=%.0f cm/s local=%s"),
		OtherActor ? *OtherActor->GetName() : TEXT("?"), DeltaV, *LocalPosition.ToString());
	Condition->ApplyImpact(LocalPosition, LocalDirection, DeltaV);
}

void AGTCarPawn::BuildDrivingMappings(UInputMappingContext* Context, UInputAction* Throttle, UInputAction* Brake, UInputAction* Steer,
                                      UInputAction* Handbrake, UInputAction* Look, UInputAction* Exit, UInputAction* Reel,
                                     UInputAction* CameraToggle, UInputAction* DiffLock, UInputAction* LowRange,
                                     UInputAction* ReleaseWinch)
{
	MapKey(Context, Throttle, EKeys::W);
	MapKey(Context, Throttle, EKeys::Up);
	MapKey(Context, Throttle, EKeys::Gamepad_RightTriggerAxis, false, /*bDeadZone*/ true);
	MapKey(Context, Brake, EKeys::S);
	MapKey(Context, Brake, EKeys::Down);
	MapKey(Context, Brake, EKeys::Gamepad_LeftTriggerAxis, false, /*bDeadZone*/ true);
	MapKey(Context, Steer, EKeys::D);
	MapKey(Context, Steer, EKeys::Right);
	MapKey(Context, Steer, EKeys::A, /*bNegate*/ true);
	MapKey(Context, Steer, EKeys::Left, /*bNegate*/ true);
	MapKey(Context, Steer, EKeys::Gamepad_LeftX, false, /*bDeadZone*/ true);
	MapKey(Context, Handbrake, EKeys::SpaceBar);
	MapKey(Context, Handbrake, EKeys::Gamepad_FaceButton_Right);
	MapKey(Context, Look, EKeys::Mouse2D);
	MapKey(Context, Look, EKeys::Gamepad_Right2D, false, /*bDeadZone*/ true);
	MapKey(Context, Exit, EKeys::F);
	MapKey(Context, Exit, EKeys::Gamepad_FaceButton_Top);
	MapKey(Context, Reel, EKeys::R);
	MapKey(Context, Reel, EKeys::Gamepad_FaceButton_Left);
	if (CameraToggle)
	{
		MapKey(Context, CameraToggle, EKeys::C);
		MapKey(Context, CameraToggle, EKeys::Gamepad_RightThumbstick);
	}
	if (DiffLock)
	{
		MapKey(Context, DiffLock, EKeys::X);
		MapKey(Context, DiffLock, EKeys::Gamepad_DPad_Right);
	}
	if (LowRange)
	{
		MapKey(Context, LowRange, EKeys::V);
		MapKey(Context, LowRange, EKeys::Gamepad_DPad_Down);
	}
	if (ReleaseWinch)
	{
		// Section 51: G is free in the car (on foot it drops a carried hook), and so is DPad Up.
		MapKey(Context, ReleaseWinch, EKeys::G);
		MapKey(Context, ReleaseWinch, EKeys::Gamepad_DPad_Up);
	}
}

void AGTCarPawn::EnsureDefaultInputAssets()
{
	// Prefer the assets written by Art/setup_m1_input.bat (rebindable in the editor); build the same
	// mapping at runtime when they are missing, so the car drives with no content authored.
	auto LoadAction = [](const TCHAR* Name)
	{
		return LoadObject<UInputAction>(nullptr, *FString::Printf(TEXT("/Game/GrandTour/Input/%s.%s"), Name, Name));
	};
	if (!ThrottleAction)  { ThrottleAction  = LoadAction(TEXT("IA_Throttle")); }
	if (!BrakeAction)     { BrakeAction     = LoadAction(TEXT("IA_Brake")); }
	if (!SteerAction)     { SteerAction     = LoadAction(TEXT("IA_Steer")); }
	if (!HandbrakeAction) { HandbrakeAction = LoadAction(TEXT("IA_Handbrake")); }
	if (!LookAction)      { LookAction      = LoadAction(TEXT("IA_Look")); }
	if (!ExitAction)      { ExitAction      = LoadAction(TEXT("IA_Exit")); }
	if (!ReelAction)      { ReelAction      = LoadAction(TEXT("IA_Reel")); }
	if (!CameraToggleAction) { CameraToggleAction = LoadAction(TEXT("IA_CameraToggle")); }
	if (!DiffLockAction)     { DiffLockAction     = LoadAction(TEXT("IA_DiffLock")); }
	if (!LowRangeAction)     { LowRangeAction     = LoadAction(TEXT("IA_LowRange")); }
	if (!ReleaseWinchAction) { ReleaseWinchAction = LoadAction(TEXT("IA_ReleaseWinch")); }
	if (!DefaultMappingContext && ThrottleAction && BrakeAction && SteerAction && HandbrakeAction && LookAction && ExitAction && ReelAction)
	{
		DefaultMappingContext = LoadObject<UInputMappingContext>(nullptr, TEXT("/Game/GrandTour/Input/IMC_Driving.IMC_Driving"));
	}
	bInputFromAssets = DefaultMappingContext != nullptr;

	if (!ThrottleAction)  { ThrottleAction  = MakeAction(this, TEXT("IA_Throttle"),  EInputActionValueType::Axis1D); }
	if (!BrakeAction)     { BrakeAction     = MakeAction(this, TEXT("IA_Brake"),     EInputActionValueType::Axis1D); }
	if (!SteerAction)     { SteerAction     = MakeAction(this, TEXT("IA_Steer"),     EInputActionValueType::Axis1D); }
	if (!HandbrakeAction) { HandbrakeAction = MakeAction(this, TEXT("IA_Handbrake"), EInputActionValueType::Boolean); }
	if (!LookAction)      { LookAction      = MakeAction(this, TEXT("IA_Look"),      EInputActionValueType::Axis2D); }
	if (!ExitAction)      { ExitAction      = MakeAction(this, TEXT("IA_Exit"),      EInputActionValueType::Boolean); }
	if (!ReelAction)      { ReelAction      = MakeAction(this, TEXT("IA_Reel"),      EInputActionValueType::Boolean); }
	if (!CameraToggleAction) { CameraToggleAction = MakeAction(this, TEXT("IA_CameraToggle"), EInputActionValueType::Boolean); }
	if (!DiffLockAction)     { DiffLockAction     = MakeAction(this, TEXT("IA_DiffLock"),     EInputActionValueType::Boolean); }
	if (!LowRangeAction)     { LowRangeAction     = MakeAction(this, TEXT("IA_LowRange"),     EInputActionValueType::Boolean); }
	if (!ReleaseWinchAction) { ReleaseWinchAction = MakeAction(this, TEXT("IA_ReleaseWinch"), EInputActionValueType::Boolean); }
	if (!DefaultMappingContext)
	{
		DefaultMappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_Drive"));
		BuildDrivingMappings(DefaultMappingContext, ThrottleAction, BrakeAction, SteerAction, HandbrakeAction, LookAction, ExitAction, ReelAction,
			CameraToggleAction, DiffLockAction, LowRangeAction, ReleaseWinchAction);
	}
	else
	{
		// An IMC_Driving asset written before an action existed has no keys for it: add them for this run.
		auto EnsureMapped = [this](UInputAction* Action, const FKey& KeyA, const FKey& KeyB)
		{
			bool bHas = false;
			for (const FEnhancedActionKeyMapping& Mapping : DefaultMappingContext->GetMappings())
			{
				bHas |= Mapping.Action == Action;
			}
			if (!bHas)
			{
				MapKey(DefaultMappingContext, Action, KeyA);
				MapKey(DefaultMappingContext, Action, KeyB);
			}
		};
		EnsureMapped(CameraToggleAction, EKeys::C, EKeys::Gamepad_RightThumbstick);
		EnsureMapped(DiffLockAction, EKeys::X, EKeys::Gamepad_DPad_Right);
		EnsureMapped(LowRangeAction, EKeys::V, EKeys::Gamepad_DPad_Down);
		EnsureMapped(ReleaseWinchAction, EKeys::G, EKeys::Gamepad_DPad_Up);
	}
	UE_LOG(LogTemp, Display, TEXT("AGTCarPawn: driving input from %s, %d mappings"),
		bInputFromAssets ? TEXT("assets") : TEXT("runtime defaults"), DefaultMappingContext->GetMappings().Num());
}

void AGTCarPawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	EnsureDefaultInputAssets();

	if (const APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
			ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			if (!Subsystem->HasMappingContext(DefaultMappingContext))
			{
				Subsystem->AddMappingContext(DefaultMappingContext, 0);
			}
		}
	}

	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		UE_LOG(LogTemp, Error, TEXT("AGTCarPawn: input component is not an EnhancedInputComponent; check DefaultInput.ini"));
		return;
	}
	Input->BindAction(ThrottleAction, ETriggerEvent::Triggered, this, &AGTCarPawn::OnThrottle);
	Input->BindAction(ThrottleAction, ETriggerEvent::Completed, this, &AGTCarPawn::OnThrottleReleased);
	Input->BindAction(BrakeAction, ETriggerEvent::Triggered, this, &AGTCarPawn::OnBrake);
	Input->BindAction(BrakeAction, ETriggerEvent::Completed, this, &AGTCarPawn::OnBrakeReleased);
	Input->BindAction(SteerAction, ETriggerEvent::Triggered, this, &AGTCarPawn::OnSteer);
	Input->BindAction(SteerAction, ETriggerEvent::Completed, this, &AGTCarPawn::OnSteerReleased);
	Input->BindAction(HandbrakeAction, ETriggerEvent::Started, this, &AGTCarPawn::OnHandbrakePressed);
	Input->BindAction(HandbrakeAction, ETriggerEvent::Completed, this, &AGTCarPawn::OnHandbrakeReleased);
	Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AGTCarPawn::OnLook);
	Input->BindAction(ExitAction, ETriggerEvent::Started, this, &AGTCarPawn::OnExit);
	Input->BindAction(ReelAction, ETriggerEvent::Started, this, &AGTCarPawn::OnReelPressed);
	Input->BindAction(ReelAction, ETriggerEvent::Completed, this, &AGTCarPawn::OnReelReleased);
	Input->BindAction(CameraToggleAction, ETriggerEvent::Started, this, &AGTCarPawn::OnCameraToggle);
	Input->BindAction(DiffLockAction, ETriggerEvent::Started, this, &AGTCarPawn::OnDiffLock);
	Input->BindAction(LowRangeAction, ETriggerEvent::Started, this, &AGTCarPawn::OnLowRange);
	Input->BindAction(ReleaseWinchAction, ETriggerEvent::Started, this, &AGTCarPawn::OnReleaseWinch);
}

void AGTCarPawn::OnDiffLock(const FInputActionValue& Value)
{
	if (Drivetrain)
	{
		Drivetrain->SetDiffLock(!Drivetrain->IsDiffLocked());
	}
}

void AGTCarPawn::OnLowRange(const FInputActionValue& Value)
{
	if (Drivetrain)
	{
		Drivetrain->SetLowRange(!Drivetrain->IsLowRange());
	}
}

void AGTCarPawn::OnCameraToggle(const FInputActionValue& Value)
{
	SetChaseCamera(!bChaseCamera);
}

void AGTCarPawn::SetChaseCamera(bool bChase)
{
	// The pawn's view comes from its first active camera component, so activating one and not the other is the switch.
	bChaseCamera = bChase;
	if (DriverCamera)
	{
		DriverCamera->SetActive(!bChase);
	}
	if (ChaseCamera)
	{
		ChaseCamera->SetActive(bChase);
	}
}

void AGTCarPawn::OnExit(const FInputActionValue& Value)
{
	if (AGTPlayerController* PC = Cast<AGTPlayerController>(GetController()))
	{
		PC->ExitCar();
	}
}

void AGTCarPawn::OnReelPressed(const FInputActionValue& Value)  { Winch->SetReeling(true); }
void AGTCarPawn::OnReelReleased(const FInputActionValue& Value) { Winch->SetReeling(false); }

void AGTCarPawn::OnReleaseWinch(const FInputActionValue& Value)
{
	// Only a hook that is out on an anchor: the pull stops at once, the drawn cable rewinds to the drum (section 51).
	if (Winch && Winch->GetState() == EGTWinchState::Attached)
	{
		Winch->Release();
	}
}

void AGTCarPawn::OnThrottle(const FInputActionValue& Value)         { GetChaosMovement()->SetThrottleInput(Value.Get<float>()); }
void AGTCarPawn::OnThrottleReleased(const FInputActionValue& Value) { GetChaosMovement()->SetThrottleInput(0.f); }
void AGTCarPawn::OnBrake(const FInputActionValue& Value)            { GetChaosMovement()->SetBrakeInput(Value.Get<float>()); }
void AGTCarPawn::OnBrakeReleased(const FInputActionValue& Value)    { GetChaosMovement()->SetBrakeInput(0.f); }
void AGTCarPawn::OnSteer(const FInputActionValue& Value)            { RawSteer = Value.Get<float>(); UE_LOG(LogTemp, Verbose, TEXT("GTINPUT steer %.2f"), RawSteer); }
void AGTCarPawn::OnSteerReleased(const FInputActionValue& Value)    { RawSteer = 0.f; }
void AGTCarPawn::OnHandbrakePressed(const FInputActionValue& Value) { GetChaosMovement()->SetHandbrakeInput(true); }
void AGTCarPawn::OnHandbrakeReleased(const FInputActionValue& Value){ GetChaosMovement()->SetHandbrakeInput(false); }

void AGTCarPawn::ResetDrivingInputs()
{
	RawSteer = 0.f;
	if (UChaosWheeledVehicleMovementComponent* Move = GetChaosMovement())
	{
		Move->SetThrottleInput(0.f);
		Move->SetBrakeInput(0.f);
		Move->SetSteeringInput(0.f);
		Move->SetHandbrakeInput(false);
	}
	if (Winch)
	{
		Winch->SetReeling(false);
	}
}

void AGTCarPawn::OnLook(const FInputActionValue& Value)
{
	const FVector2D Look = Value.Get<FVector2D>();
	if (bChaseCamera && ChaseArm)
	{
		// Keep the orbit separate from the cockpit look and its automatic recentring.
		FRotator Orbit = ChaseArm->GetRelativeRotation();
		Orbit.Yaw = FRotator::NormalizeAxis(Orbit.Yaw + Look.X);
		Orbit.Pitch = FMath::Clamp(FRotator::NormalizeAxis(Orbit.Pitch)
			+ (bInvertLookY ? -Look.Y : Look.Y), -75.f, 15.f);
		Orbit.Roll = 0.f;
		ChaseArm->SetRelativeRotation(Orbit);
		return;
	}
	LookOffset.Yaw = FMath::Clamp(LookOffset.Yaw + Look.X, -LookYawLimit, LookYawLimit);
	LookOffset.Pitch = FMath::Clamp(LookOffset.Pitch + (bInvertLookY ? -Look.Y : Look.Y), -LookPitchLimit, LookPitchLimit);
	LastLookInputTime = GetWorld()->GetTimeSeconds();
}
