#include "Core/GTDriveTestGameMode.h"

#include "Core/GTHUD.h"
#include "Core/GTPlayerController.h"
#include "Vehicle/GTBodyComponent.h"
#include "Vehicle/GTBodyStateComponent.h"
#include "Vehicle/GTSprayComponent.h"
#include "Vehicle/GTVehicleAudioComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTDashboardComponent.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTVehicleTuningComponent.h"
#include "Terrain/GTTrackPaintSubsystem.h"

#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Materials/MaterialInterface.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "HAL/PlatformMisc.h"
#include "GameFramework/PlayerController.h"
#include "InputMappingContext.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "PhysicsEngine/BoxElem.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "ChaosVehicleWheel.h"
#include "TimerManager.h"

namespace
{
	constexpr float SelfTestInterval = 0.5f;
	constexpr float FlatPassDistance = 500.f;   // cm
	const FVector MudLaneStart(13000.f, 0.f, 120.f);   // 10 m into the mud lane of L_TestTrack
	const FVector RoughStart(14100.f, 4000.f, 120.f);  // just past the jump ramp, 14 m before the first ridge
	const FVector WallRunUp(21000.f, 0.f, 120.f);      // snow lane, 35 m before the wall at x = 245 m
	constexpr float RoughPatchEndX = 18500.f;          // the rear wheels are clear of the last ridge (x = 18200)
}

AGTDriveTestGameMode::AGTDriveTestGameMode()
{
	DefaultPawnClass = AGTCarPawn::StaticClass();
	PlayerControllerClass = AGTPlayerController::StaticClass();
	HUDClass = AGTHUD::StaticClass();
	PrimaryActorTick.bCanEverTick = true;   // per-frame sampling for the rough-patch test; Tick early-outs otherwise
}

void AGTDriveTestGameMode::BeginPlay()
{
	Super::BeginPlay();

	bSurfaceTest = FParse::Param(FCommandLine::Get(), TEXT("GTSurfaceTest"));
	bMudTest = FParse::Param(FCommandLine::Get(), TEXT("GTMudTest"));
	bRoughTest = FParse::Param(FCommandLine::Get(), TEXT("GTRoughTest"));
	bTrackTest = FParse::Param(FCommandLine::Get(), TEXT("GTTrackTest"));
	bBodyTest = FParse::Param(FCommandLine::Get(), TEXT("GTBodyTest"));
	bBodyStateTest = FParse::Param(FCommandLine::Get(), TEXT("GTBodyStateTest"));
	bSprayTest = FParse::Param(FCommandLine::Get(), TEXT("GTSprayTest"));
	bGripTest = FParse::Param(FCommandLine::Get(), TEXT("GTGripTest"));
	bDrivetrainTest = FParse::Param(FCommandLine::Get(), TEXT("GTDrivetrainTest"));
	if (FParse::Param(FCommandLine::Get(), TEXT("GTOnFootTest")) || FParse::Param(FCommandLine::Get(), TEXT("GTWinchTest")))
	{
		const bool bWinch = FParse::Param(FCommandLine::Get(), TEXT("GTWinchTest"));
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting %s"), bWinch ? TEXT("winch test") : TEXT("on-foot test"));
		M2Test = MakeUnique<FGTM2TestRunner>(GetWorld(), bWinch);
	}
	if (bSurfaceTest)
	{
		// Matches Art/Unreal/setup_m1_track.py: 60 m lanes along +X from x = 0, wall at 245 m.
		Segments = {
			{TEXT("RunUp"), -3000.f, 0.f},
			{TEXT("Tarmac"), 0.f, 6000.f},
			{TEXT("Dirt"), 6000.f, 12000.f},
			{TEXT("Mud"), 12000.f, 18000.f},
			{TEXT("Snow"), 18000.f, 24000.f},
			{TEXT("Wall"), 24000.f, 26000.f},
		};
		SelfTestDuration = 30.f;
	}
	else if (bMudTest)
	{
		SelfTestDuration = MudSettleSeconds + 8.f;
	}
	else if (bRoughTest)
	{
		SelfTestDuration = 12.f;
	}
	else if (bTrackTest)
	{
		SelfTestDuration = 18.f;   // ends in the snow lane (the snow sample at 200 m painted) with the mud lane still inside the track window; the mud of stage 3 is slower than the 16 s assumed
	}
	else if (bBodyTest)
	{
		SelfTestDuration = 12.f;   // the wall stops it sooner; then two seconds for the panels to fly
	}
	else if (bBodyStateTest || bSprayTest)
	{
		SelfTestDuration = 16.f;   // tarmac, dirt, mud, then into the snow lane
	}
	else if (bDrivetrainTest)
	{
		// An ice strip under the left wheels (a runtime physical material, friction 0.01) 40 m long east of the spawn,
		// and a 35 % ramp 100 m long starting 60 m north of it, both 1 cm proud of the floor at their feet.
		SelfTestDuration = 60.f;
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		UPhysicalMaterial* Ice = NewObject<UPhysicalMaterial>(this, TEXT("PM_TestIce"));
		Ice->Friction = 0.01f;
		Ice->StaticFriction = 0.01f;
		AStaticMeshActor* Strip = Cube ? GetWorld()->SpawnActor<AStaticMeshActor>(FVector(1900.f, -150.f, -4.f), FRotator::ZeroRotator) : nullptr;
		if (Strip)
		{
			Strip->SetMobility(EComponentMobility::Movable);
			Strip->GetStaticMeshComponent()->SetStaticMesh(Cube);
			Strip->SetActorScale3D(FVector(40.f, 2.f, 0.1f));
			Strip->GetStaticMeshComponent()->SetPhysMaterialOverride(Ice);
		}
		// The ramp: a 100 m slab pitched up 19.3 deg (tan = 0.35), its low end at the floor 10 m ahead of the ramp start.
		const float Pitch = FMath::RadiansToDegrees(FMath::Atan(0.35f));
		const FVector RampFoot(0.f, 6000.f, 0.f);
		const FVector Along(FMath::Cos(FMath::DegreesToRadians(Pitch)), 0.f, FMath::Sin(FMath::DegreesToRadians(Pitch)));
		AStaticMeshActor* Ramp = Cube ? GetWorld()->SpawnActor<AStaticMeshActor>(RampFoot + Along * 5000.f - FVector(0.f, 0.f, 9.f), FRotator(Pitch, 0.f, 0.f)) : nullptr;
		if (Ramp)
		{
			Ramp->SetMobility(EComponentMobility::Movable);
			Ramp->GetStaticMeshComponent()->SetStaticMesh(Cube);
			Ramp->SetActorScale3D(FVector(100.f, 8.f, 0.2f));
		}
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST drivetrain props: ice strip=%d ramp=%d (%.1f deg)"), Strip ? 1 : 0, Ramp ? 1 : 0, Pitch);
	}
	else if (bGripTest)
	{
		// Two 200 m pads on the 400 m floor, their tops 1 cm proud, each with a surface physical material.
		SelfTestDuration = 90.f;
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		const TCHAR* Surfaces[2] = { TEXT("Tarmac"), TEXT("Dirt") };
		for (int32 Index = 0; Index < 2; ++Index)
		{
			FGripRun Run;
			Run.Name = Surfaces[Index];
			Run.PadCentre = FVector(Index == 0 ? -10000.f : 10000.f, 0.f, 0.f);
			UPhysicalMaterial* Surface = LoadObject<UPhysicalMaterial>(nullptr, *FString::Printf(TEXT("/Game/GrandTour/Terrain/Surfaces/PM_%s.PM_%s"), Surfaces[Index], Surfaces[Index]));
			AStaticMeshActor* Pad = (Cube && Surface) ? GetWorld()->SpawnActor<AStaticMeshActor>(Run.PadCentre + FVector(0.f, 0.f, -4.f), FRotator::ZeroRotator) : nullptr;
			if (Pad)
			{
				Pad->SetMobility(EComponentMobility::Movable);
				Pad->GetStaticMeshComponent()->SetStaticMesh(Cube);
				Pad->SetActorScale3D(FVector(200.f, 200.f, 0.1f));
				Pad->GetStaticMeshComponent()->SetPhysMaterialOverride(Surface);
			}
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST grip pad %s at (%.0f, %.0f): surface friction %.2f placed=%d"), Surfaces[Index], Run.PadCentre.X, Run.PadCentre.Y, Surface ? Surface->Friction : -1.f, Pad ? 1 : 0);
			GripRuns.Add(Run);
		}
	}
	// -GTProbeMaterial=/Game/Path/M_A,/Game/Path/M_B puts each material on a cube so a -RenderOffScreen
	// run must compile it: commandlets never report custom-HLSL failures, this run logs "Failed to compile".
	FString ProbeMaterialPaths;
	if (FParse::Value(FCommandLine::Get(), TEXT("GTProbeMaterial="), ProbeMaterialPaths, /*bShouldStopOnSeparator*/ false))
	{
		TArray<FString> Paths;
		ProbeMaterialPaths.ParseIntoArray(Paths, TEXT(","), true);
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		for (int32 Index = 0; Index < Paths.Num(); ++Index)
		{
			UMaterialInterface* ProbeMaterial = LoadObject<UMaterialInterface>(nullptr, *Paths[Index]);
			AStaticMeshActor* Probe = (ProbeMaterial && Cube) ? GetWorld()->SpawnActor<AStaticMeshActor>(FVector(-2500.f, 600.f + 200.f * Index, 200.f), FRotator::ZeroRotator) : nullptr;
			if (Probe)
			{
				Probe->SetMobility(EComponentMobility::Movable);
				Probe->GetStaticMeshComponent()->SetStaticMesh(Cube);
				Probe->GetStaticMeshComponent()->SetMaterial(0, ProbeMaterial);
			}
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST probe material %s loaded=%d placed=%d"), *Paths[Index], ProbeMaterial ? 1 : 0, Probe ? 1 : 0);
		}
	}
	bFlatTest = !(bSurfaceTest || bMudTest || bRoughTest || bTrackTest || bBodyTest || bBodyStateTest || bSprayTest || bGripTest || bDrivetrainTest) && FParse::Param(FCommandLine::Get(), TEXT("GTDriveTest"));
	if (bSurfaceTest || bMudTest || bRoughTest || bTrackTest || bBodyTest || bBodyStateTest || bSprayTest || bGripTest || bDrivetrainTest || bFlatTest)
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting %s for %.0f s"),
			bSurfaceTest ? TEXT("surface test") : bMudTest ? TEXT("mud start test") : bRoughTest ? TEXT("rough patch test") : bTrackTest ? TEXT("track paint test") : bBodyTest ? TEXT("body test") : bBodyStateTest ? TEXT("body state test") : bSprayTest ? TEXT("spray and audio test") : bGripTest ? TEXT("grip test") : bDrivetrainTest ? TEXT("drivetrain test") : TEXT("flat test"),
			SelfTestDuration);
		GetWorldTimerManager().SetTimer(SelfTestTimer, this, &AGTDriveTestGameMode::SelfTestTick, SelfTestInterval, true, 0.2f);
	}
}

void AGTDriveTestGameMode::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (M2Test)
	{
		bool bPass = false;
		FString Summary;
		if (M2Test->Tick(DeltaSeconds, bPass, Summary))
		{
			M2Test.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (bGripTest)
	{
		GripFrameTick(DeltaSeconds);
		return;
	}
	if (!bRoughTest || !bSelfTestStarted || DeltaSeconds <= KINDA_SMALL_NUMBER)
	{
		return;
	}
	const AGTCarPawn* Car = Cast<AGTCarPawn>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!Car)
	{
		return;
	}
	const float VerticalVelocity = Car->GetMesh()->GetComponentVelocity().Z;
	const float Pitch = Car->GetMesh()->GetComponentRotation().Pitch;
	const bool bOverPatch = Car->GetActorLocation().X > RoughStart.X + 1000.f;
	if (!bHaveLastSample)
	{
		WindowStartVz = VerticalVelocity;
		WindowStartPitch = Pitch;
		WindowTime = 0.f;
	}
	else if (bOverPatch)
	{
		// Per-frame jolt (the physics step's velocity jump) and a 50 ms average, since headless
		// frames are far shorter than a physics step and would inflate a per-frame acceleration.
		PeakStepDeltaVz = FMath::Max(PeakStepDeltaVz, FMath::Abs(VerticalVelocity - LastVerticalVelocity));
		WindowTime += DeltaSeconds;
		if (WindowTime >= 0.05f)
		{
			const float WindowG = FMath::Abs(VerticalVelocity - WindowStartVz) / WindowTime / 980.f;
			if (Car->GetActorLocation().X < RoughPatchEndX)
			{
				SumG2Time += WindowG * WindowG * WindowTime;
				PatchTime += WindowTime;
			}
			PeakVerticalG = FMath::Max(PeakVerticalG, WindowG);
			PeakPitchRate = FMath::Max(PeakPitchRate, FMath::Abs(FMath::FindDeltaAngleDegrees(WindowStartPitch, Pitch)) / WindowTime);
			WindowStartVz = VerticalVelocity;
			WindowStartPitch = Pitch;
			WindowTime = 0.f;
		}
	}
	// After the patch: how long the body keeps bouncing (the "floaty" number) and how many times.
	if (Car->GetActorLocation().X > RoughPatchEndX)
	{
		PostPatchTime = PostPatchTime < 0.f ? 0.f : PostPatchTime + DeltaSeconds;
		PeakVzSinceCrossing = FMath::Max(PeakVzSinceCrossing, FMath::Abs(VerticalVelocity));
		const float Sign = FMath::Sign(VerticalVelocity);
		if (Sign != 0.f && LastVzSign != 0.f && Sign != LastVzSign)
		{
			if (PeakVzSinceCrossing > 10.f)
			{
				++BouncesAfterPatch;
			}
			PeakVzSinceCrossing = 0.f;
		}
		if (Sign != 0.f)
		{
			LastVzSign = Sign;
		}
		if (SettleTime < 0.f)
		{
			QuietTime = FMath::Abs(VerticalVelocity) < 8.f ? QuietTime + DeltaSeconds : 0.f;
			if (QuietTime >= 0.3f)
			{
				SettleTime = PostPatchTime - QuietTime;
			}
		}
	}
	LastVerticalVelocity = VerticalVelocity;
	LastPitch = Pitch;
	bHaveLastSample = true;
}

AGTDriveTestGameMode::FSegment* AGTDriveTestGameMode::FindSegment(float X)
{
	for (FSegment& Segment : Segments)
	{
		if (X >= Segment.XStart && X < Segment.XEnd)
		{
			return &Segment;
		}
	}
	return nullptr;
}

void AGTDriveTestGameMode::FinishTest(bool bPass, const FString& Summary)
{
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST_RESULT %s %s"), bPass ? TEXT("PASS") : TEXT("FAIL"), *Summary);
	GetWorldTimerManager().ClearTimer(SelfTestTimer);
	FPlatformMisc::RequestExit(false);
}

void AGTDriveTestGameMode::SelfTestTick()
{
	AGTCarPawn* Car = Cast<AGTCarPawn>(UGameplayStatics::GetPlayerPawn(this, 0));
	UChaosWheeledVehicleMovementComponent* Move = Car ? Car->GetChaosMovement() : nullptr;
	if (!Car || !Move)
	{
		FinishTest(false, TEXT("no GTCarPawn possessed by player 0"));
		return;
	}
	const UGTTractionComponent* Traction = Car->GetTraction();
	const UGTConditionComponent* Condition = Car->GetCondition();

	if (!bSelfTestStarted)
	{
		bSelfTestStarted = true;
		// A controller left plugged in must not steer a headless test.
		if (APlayerController* PC = Cast<APlayerController>(Car->GetController()))
		{
			Car->DisableInput(PC);
		}
		Car->ResetDrivingInputs();
		if (bMudTest)
		{
			Car->SetActorLocation(MudLaneStart, false, nullptr, ETeleportType::TeleportPhysics);
		}
		else if (bRoughTest)
		{
			Car->SetActorLocation(RoughStart, false, nullptr, ETeleportType::TeleportPhysics);
		}
		else if (bBodyTest)
		{
			// The run-up is the snow lane: since stage 1 (real snow grip) the car cannot reach the wall at the speed the
			// panel checks were written for, so it starts at 50 km/h and the 35 m of snow trim that to about 45.
			Car->SetActorLocation(WallRunUp, false, nullptr, ETeleportType::TeleportPhysics);
			Car->GetMesh()->SetPhysicsLinearVelocity(FVector(1400.f, 0.f, 0.f));
		}
		SelfTestStart = Car->GetActorLocation();
		if (Car->GetBody())
		{
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST body start %s"), *Car->GetBody()->Describe());
		}
		const USkeletalMeshComponent* Mesh = Car->GetMesh();
		const FBodyInstance* Body = Mesh->GetBodyInstance();
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST spawn actor=%s rootBoneRot=%s com=%s mass=%.0f"),
			*SelfTestStart.ToString(), *Mesh->GetBoneQuaternion(TEXT("Root")).Rotator().ToString(),
			*(Body ? Body->GetCOMPosition() : FVector::ZeroVector).ToString(), Body ? Body->GetBodyMass() : 0.f);
		if (Car->GetDashboard() && Car->GetDriverCamera())
		{
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST dash visibility from eye %s: %s"),
				*Car->GetDriverCamera()->GetComponentLocation().ToString(), *Car->GetDashboard()->CheckDialVisibility(Car->GetDriverCamera()->GetComponentLocation()));
		}
	}
	if (bGripTest)
	{
		SelfTestElapsed += SelfTestInterval;
		GripSelfTestTick(*Car, *Move);
		return;
	}
	if (bDrivetrainTest)
	{
		SelfTestElapsed += SelfTestInterval;
		DrivetrainSelfTestTick(*Car, *Move);
		return;
	}
	const FVector Location = Car->GetActorLocation();
	SelfTestElapsed += SelfTestInterval;
	const bool bThrottleOn = !bMudTest || SelfTestElapsed > MudSettleSeconds;
	Move->SetThrottleInput(bThrottleOn ? 1.f : 0.f);

	const float Speed = Move->GetForwardSpeed();
	if (bThrottleOn)
	{
		SelfTestMaxSpeed = FMath::Max(SelfTestMaxSpeed, Speed);
	}
	// Flat test only: toggle the chase camera at 4 s, read where the view is half a second later, switch back, read again.
	if (bFlatTest)
	{
		const APlayerController* PC = Cast<APlayerController>(Car->GetController());
		const FVector ViewLocation = (PC && PC->PlayerCameraManager) ? PC->PlayerCameraManager->GetCameraLocation() : FVector::ZeroVector;
		const FVector CarForward = Car->GetActorForwardVector();
		if (FMath::IsNearlyEqual(SelfTestElapsed, 4.f))
		{
			Car->SetChaseCamera(true);
		}
		else if (FMath::IsNearlyEqual(SelfTestElapsed, 4.5f))
		{
			const FVector Offset = ViewLocation - Location;
			ChaseBehind = FVector::DotProduct(Offset, CarForward);
			ChaseAbove = Offset.Z;
			bChaseOk = Car->IsChaseCamera() && ChaseBehind < -300.f && ChaseAbove > 100.f;
			Car->SetChaseCamera(false);
		}
		else if (FMath::IsNearlyEqual(SelfTestElapsed, 5.f))
		{
			DriverBack = Car->GetDriverCamera() ? FVector::Dist(ViewLocation, Car->GetDriverCamera()->GetComponentLocation()) : -1.f;
			bDriverBackOk = !Car->IsChaseCamera() && DriverBack >= 0.f && DriverBack < 30.f;
		}
	}
	const FGTVehicleTuning& Tuning = Car->GetTuning()->GetCurrent();
	FString Extra;
	if ((bSurfaceTest || bMudTest) && Traction && Traction->Wheels.Num() > 0 && Condition)
	{
		const FGTWheelTraction& FL = Traction->Wheels[0];
		Extra = FString::Printf(TEXT(" surfFL=%s sinkFL=%.2f slipFL=%.0f%s crrFL=%.3f gripFL=%.2f bogged=%d torqueScale=%.2f engine=%.2f fuel=%.1f"),
			*FL.SurfaceTag.ToString(), FL.Sinkage, FL.SlipMagnitude, FL.bSlipping ? TEXT("*") : TEXT(""), FL.RollingResistance,
			FL.FrictionScale, Traction->bBogged ? 1 : 0, Tuning.TorqueScale,
			Condition->GetPartHealth(EGTCarPart::Engine), Condition->FuelLitres);
		bBoggedEver |= Traction->bBogged;
		MudMaxSinkage = FMath::Max(MudMaxSinkage, Traction->GetMaxSinkageFraction());

		if (bSurfaceTest)
		{
			FSegment* Segment = FindSegment(Location.X);
			const int32 SegmentIndex = Segment ? static_cast<int32>(Segment - Segments.GetData()) : -1;
			if (SegmentIndex != CurrentSegment)
			{
				if (Segments.IsValidIndex(CurrentSegment) && Segments[CurrentSegment].ExitSpeed < 0.f)
				{
					Segments[CurrentSegment].ExitSpeed = Speed;
				}
				if (Segment && Segment->EntrySpeed < 0.f)   // first entry only; a bounce back does not count
				{
					Segment->EntrySpeed = Speed;
				}
				CurrentSegment = SegmentIndex;
			}
			if (Segment)
			{
				Segment->Time += SelfTestInterval;
				Segment->MaxSinkage = FMath::Max(Segment->MaxSinkage, Traction->GetMaxSinkageFraction());
				Segment->bBogged |= Traction->bBogged;
			}
		}
	}
	if (bBodyStateTest && Car->GetBodyState())
	{
		const UGTBodyStateComponent* State = Car->GetBodyState();
		if (Location.X > 0.f && Location.X < 6000.f && (State->GetAverageDirt() > 0.f || State->Wetness > 0.f || State->Snow > 0.f))
		{
			bStateCleanOnTarmac = false;
		}
		if (Location.X >= 18000.f && MudExitArchFL < 0.f)
		{
			MudExitArchFL = State->GetDirt(EGTDamageRegion::ArchFL);
			MudExitSideL = State->GetDirt(EGTDamageRegion::SideL);
			MudExitRoof = State->GetDirt(EGTDamageRegion::Roof);
			MudExitWetness = State->Wetness;
		}
		if (FMath::IsNearlyEqual(FMath::Fmod(SelfTestElapsed, 2.f), 0.f, 0.01f))
		{
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST state t=%.1f %s"), SelfTestElapsed, *State->Describe());
		}
	}
	if (bSprayTest && Car->GetSpray() && Car->GetAudio())
	{
		const UGTSprayComponent* Spray = Car->GetSpray();
		const UGTVehicleAudioComponent* Audio = Car->GetAudio();
		const int32 Mud = Spray->GetLiveCount(EGTSprayKind::Mud);
		const int32 Dust = Spray->GetLiveCount(EGTSprayKind::Dust);
		const int32 Snow = Spray->GetLiveCount(EGTSprayKind::Snow);
		bPoolExceeded |= Mud > Spray->PoolPerKind || Dust > Spray->PoolPerKind || Snow > Spray->PoolPerKind;
		if (Location.X > 0.f && Location.X < 6000.f)
		{
			bSprayCleanOnTarmac &= (Mud + Dust + Snow) == 0;
			if (Location.X > 3000.f && TarmacCutoff < 0.f)
			{
				TarmacCutoff = Audio->TyreCutoff;
				TarmacRms = Audio->RenderTestBlock(4410);
			}
		}
		else if (Location.X >= 6000.f && Location.X < 12000.f)
		{
			MaxDustInDirt = FMath::Max(MaxDustInDirt, Dust);
		}
		else if (Location.X >= 12000.f && Location.X < 18000.f)
		{
			MaxMudInMud = FMath::Max(MaxMudInMud, Mud);
			if (Location.X > 15000.f && MudCutoff < 0.f)
			{
				MudCutoff = Audio->TyreCutoff;
				MudRms = Audio->RenderTestBlock(4410);
			}
		}
		else if (Location.X >= 18000.f)
		{
			MaxSnowInSnow = FMath::Max(MaxSnowInSnow, Snow);
		}
		if (FMath::IsNearlyEqual(FMath::Fmod(SelfTestElapsed, 2.f), 0.f, 0.01f))
		{
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST fx t=%.1f %s | %s"), SelfTestElapsed, *Spray->Describe(), *Audio->Describe());
		}
	}
	UGTTrackPaintSubsystem* Paint = bTrackTest ? GetWorld()->GetSubsystem<UGTTrackPaintSubsystem>() : nullptr;
	if (Paint)
	{
		const float MaxDepth = Paint->GetMaxDepth();
		if (Location.X > 0.f && Location.X < 6000.f && MaxDepth > 0.f)
		{
			bTarmacClean = false;
		}
		Extra = FString::Printf(TEXT(" stamps=%d recentres=%d maxDepth=%.2f origin=(%.0f, %.0f) sinkFL=%.2f"),
			Paint->StampCount, Paint->RecentreCount, MaxDepth, Paint->GetOrigin().X, Paint->GetOrigin().Y,
			Traction && Traction->Wheels.Num() > 0 ? Traction->Wheels[0].SinkageFraction : 0.f);
	}
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST t=%.1f throttle=%d speed=%.0f cm/s gear=%d rpm=%.0f pos=(%.0f, %.0f, %.0f) yaw=%.1f steerIn=%.2f raw=%.2f bias=%.2f%s"),
		SelfTestElapsed, bThrottleOn ? 1 : 0, Speed, Car->GetDrivetrain() ? Car->GetDrivetrain()->GetGear() : 0, Car->GetDrivetrain() ? Car->GetDrivetrain()->GetEngineRpm() : 0.f,
		Location.X, Location.Y, Location.Z, Car->GetActorRotation().Yaw, Move->GetSteeringInput(), Car->GetRawSteer(), Tuning.SteeringBias, *Extra);
	if (bSurfaceTest && Car->GetDashboard() && FMath::IsNearlyEqual(FMath::Fmod(SelfTestElapsed, 4.f), 0.f, 0.01f))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST dash t=%.1f %s"), SelfTestElapsed, *Car->GetDashboard()->Describe());
	}

	const bool bTimeUp = SelfTestElapsed >= SelfTestDuration;
	const bool bStoppedAtWall = (bSurfaceTest || bBodyTest) && Condition && Condition->TotalImpacts > 0 && FMath::Abs(Speed) < 30.f && SelfTestElapsed > 3.f;
	if (bBodyTest && bStoppedAtWall && WallStopTime < 0.f)
	{
		WallStopTime = SelfTestElapsed;   // give the detached panels two seconds to fly before judging
	}
	if (!bTimeUp && !(bStoppedAtWall && (!bBodyTest || SelfTestElapsed >= WallStopTime + 2.f)))
	{
		return;
	}

	const bool bUpright = Location.Z > -100.f && Location.Z < 500.f;
	if (bRoughTest)
	{
		const float Distance = FVector::Dist2D(Location, SelfTestStart);
		FinishTest(Distance > 3000.f && bUpright,
			FString::Printf(TEXT("rough patch: distance=%.0f cm maxspeed=%.0f cm/s peakVerticalG(50ms)=%.2f rmsVerticalG=%.2f peakPitchRate=%.0f deg/s peakStepDeltaVz=%.0f cm/s settleAfterPatch=%.2f s (of %.1f) bounces=%d"),
				Distance, SelfTestMaxSpeed, PeakVerticalG, PatchTime > 0.f ? FMath::Sqrt(SumG2Time / PatchTime) : 0.f, PeakPitchRate, PeakStepDeltaVz,
				SettleTime, FMath::Max(0.f, PostPatchTime), BouncesAfterPatch));
		return;
	}
	if (bMudTest)
	{
		const float Distance = FVector::Dist2D(Location, SelfTestStart);
		const bool bPulledAway = Speed >= 400.f && Distance >= 800.f;
		FinishTest(bPulledAway && bUpright && !(Traction && Traction->bBogged),
			FString::Printf(TEXT("mud start: speed=%.0f cm/s (%.0f km/h) distance=%.0f cm maxspeed=%.0f maxSink=%.2f boggedEver=%d boggedNow=%d"),
				Speed, Speed * 0.036f, Distance, SelfTestMaxSpeed, MudMaxSinkage, bBoggedEver ? 1 : 0,
				(Traction && Traction->bBogged) ? 1 : 0));
		return;
	}
	if (bSprayTest)
	{
		const UGTSprayComponent* Spray = Car->GetSpray();
		const UGTVehicleAudioComponent* Audio = Car->GetAudio();
		if (!Spray || !Audio)
		{
			FinishTest(false, TEXT("no spray or audio component"));
			return;
		}
		const bool bPass = bSprayCleanOnTarmac && !bPoolExceeded && MaxDustInDirt > 0 && MaxMudInMud > 0 && MaxSnowInSnow > 0
			&& TarmacCutoff >= 3000.f && MudCutoff > 0.f && MudCutoff < TarmacCutoff && TarmacRms > 0.02f && MudRms > 0.02f
			&& Audio->EngineHz > 0.f && bUpright;
		FinishTest(bPass, FString::Printf(TEXT("spray+audio: tarmacClean=%d poolExceeded=%d maxDustInDirt=%d maxMudInMud=%d maxSnowInSnow=%d spawned=%d tarmacCutoff=%.0f mudCutoff=%.0f tarmacRms=%.3f mudRms=%.3f | %s"),
			bSprayCleanOnTarmac ? 1 : 0, bPoolExceeded ? 1 : 0, MaxDustInDirt, MaxMudInMud, MaxSnowInSnow, Spray->GetTotalSpawned(),
			TarmacCutoff, MudCutoff, TarmacRms, MudRms, *Audio->Describe()));
		return;
	}
	if (bBodyStateTest)
	{
		const UGTBodyStateComponent* State = Car->GetBodyState();
		if (!State)
		{
			FinishTest(false, TEXT("no body state component"));
			return;
		}
		const float GlassDirt = State->GetDirt(EGTDamageRegion::Glass);
		// MudRunner MR2: with gt.Mud.CarMud on the windscreen is coated by thrown blobs that hit it only, not by the front
		// wheels' spray, so its dirt is reported, not asked for.
		const bool bGlassOk = GlassDirt > 0.f || UGTBodyStateComponent::IsCarMudEnabled();
		const bool bPass = bStateCleanOnTarmac && MudExitArchFL >= 0.2f && MudExitArchFL >= MudExitSideL && MudExitSideL >= MudExitRoof
			&& MudExitWetness >= 0.3f && State->Snow >= 0.15f && bGlassOk && bUpright;
		FinishTest(bPass, FString::Printf(TEXT("body state: tarmacClean=%d mudExit archFL=%.2f sideL=%.2f roof=%.2f wet=%.2f; final snow=%.2f wet=%.2f maxWet=%.2f glassDirt=%.2f finalX=%.0f | %s"),
			bStateCleanOnTarmac ? 1 : 0, MudExitArchFL, MudExitSideL, MudExitRoof, MudExitWetness, State->Snow, State->Wetness, State->MaxWetness,
			GlassDirt, Location.X, *State->Describe()));
		return;
	}
	if (bBodyTest)
	{
		UGTBodyComponent* Body = Car->GetBody();
		if (!Body || !Condition)
		{
			FinishTest(false, TEXT("no body or condition component"));
			return;
		}
		const float FrontHealth = Condition->GetRegionHealth(EGTDamageRegion::Front);
		const int32 Attached = Body->GetPanelCount() - Body->GetDetachedCount();
		const int32 Steam = Car->GetSpray() ? Car->GetSpray()->GetLiveCount(EGTSprayKind::Steam) : 0;
		const bool bPass = Body->GetPanelCount() >= 10 && Body->HiddenSkeletalSlots > 0 && Condition->TotalImpacts > 0
			&& Body->ImpactTextureCount > 0 && FrontHealth <= 0.f && Body->GetDetachedCount() >= 2 && Attached >= 8
			&& (Body->GetSimulatingCount() > 0 || Body->PanelsWithoutCollision > 0) && Steam > 0 && bUpright;
		FinishTest(bPass, FString::Printf(TEXT("body: impacts=%d deltaV=%.0f region=%d lastDir=%s frontHealth=%.2f radiator=%.2f steam=%d %s"),
			Condition->TotalImpacts, Condition->LastImpactDeltaV, static_cast<int32>(Condition->LastImpactRegion),
			*Condition->LastImpactLocalDirection.ToCompactString(), FrontHealth, Condition->GetPartHealth(EGTCarPart::Radiator), Steam, *Body->Describe()));
		return;
	}
	if (bTrackTest)
	{
		if (!Paint)
		{
			FinishTest(false, TEXT("no UGTTrackPaintSubsystem in this world"));
			return;
		}
		// Deepest grid cell across each wheel path (the track is 157 cm, so +-78 cm of the centreline).
		auto MaxAlong = [Paint](float X, float YMin, float YMax)
		{
			float Result = 0.f;
			for (float Y = YMin; Y <= YMax; Y += 10.f)
			{
				Result = FMath::Max(Result, Paint->SampleDepth(FVector(X, Y, 0.f)));
			}
			return Result;
		};
		auto MaxAlongRT = [Paint](float X, float YMin, float YMax, bool& bRead)
		{
			float Result = 0.f;
			for (float Y = YMin; Y <= YMax; Y += 10.f)
			{
				float Depth = 0.f;
				bRead = Paint->ReadRenderTargetDepth(FVector(X, Y, 0.f), Depth);
				if (!bRead)
				{
					return -1.f;
				}
				Result = FMath::Max(Result, Depth);
			}
			return Result;
		};
		const float MudL = MaxAlong(16500.f, -130.f, -30.f);
		const float MudR = MaxAlong(16500.f, 30.f, 130.f);
		const float SnowL = MaxAlong(20000.f, -130.f, -30.f);
		const float SnowR = MaxAlong(20000.f, 30.f, 130.f);
		const float Off = MaxAlong(16500.f, 350.f, 450.f);
		bool bRt = false;
		const float RtMud = MaxAlongRT(16500.f, -130.f, -30.f, bRt);
		const float RtOff = bRt ? MaxAlongRT(16500.f, 350.f, 450.f, bRt) : -1.f;
		const bool bInWindow = Location.X < 22900.f;   // the mud sample at x = 165 m must still be inside the window
		const bool bRtOk = !bRt || (RtMud > 0.05f && RtOff < 0.01f);
		FinishTest(Paint->StampCount > 0 && Paint->RecentreCount > 0 && bTarmacClean && MudL > 0.2f && MudR > 0.2f
			&& SnowL > 0.1f && SnowR > 0.1f && Off <= 0.f && bInWindow && bRtOk && bUpright,
			FString::Printf(TEXT("tracks: stamps=%d recentres=%d tarmacClean=%d mudL=%.2f mudR=%.2f snowL=%.2f snowR=%.2f offPath=%.2f rtMud=%.3f rtOff=%.3f gpu=%d origin=(%.0f, %.0f) finalX=%.0f"),
				Paint->StampCount, Paint->RecentreCount, bTarmacClean ? 1 : 0, MudL, MudR, SnowL, SnowR, Off, RtMud, RtOff,
				Paint->bGpuEnabled ? 1 : 0, Paint->GetOrigin().X, Paint->GetOrigin().Y, Location.X));
		return;
	}
	if (!bSurfaceTest)
	{
		const float Distance = FVector::Dist2D(Location, SelfTestStart);
		const int32 Mappings = Car->DefaultMappingContext ? Car->DefaultMappingContext->GetMappings().Num() : 0;
		FinishTest(Distance > FlatPassDistance && bUpright && Mappings >= 17 && bChaseOk && bDriverBackOk,
			FString::Printf(TEXT("distance=%.0f cm maxspeed=%.0f cm/s (%.0f km/h) finalZ=%.0f inputAssets=%d mappings=%d chase: behind=%.0f above=%.0f ok=%d driverBack=%.0f cm ok=%d"),
				Distance, SelfTestMaxSpeed, SelfTestMaxSpeed * 0.036f, Location.Z, Car->bInputFromAssets ? 1 : 0, Mappings, ChaseBehind, ChaseAbove, bChaseOk ? 1 : 0, DriverBack, bDriverBackOk ? 1 : 0));
		return;
	}

	for (const FSegment& Segment : Segments)
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST segment %-7s time=%.1f s entry=%.0f exit=%.0f cm/s maxSink=%.2f bogged=%d"),
			*Segment.Name, Segment.Time, Segment.EntrySpeed, Segment.ExitSpeed, Segment.MaxSinkage, Segment.bBogged ? 1 : 0);
	}
	const FSegment& Mud = Segments[3];
	const bool bReachedSnow = Location.X >= 18000.f;
	const bool bMudSlowed = Mud.ExitSpeed >= 0.f && Mud.EntrySpeed > 0.f && Mud.ExitSpeed < Mud.EntrySpeed * 0.95f;
	const bool bWallHit = Condition && Condition->TotalImpacts > 0 && Condition->GetPartHealth(EGTCarPart::Engine) < 1.f;
	const bool bFuelUsed = Condition && Condition->LitresUsed > 0.f;
	if (Car->GetDashboard())
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST dash final %s"), *Car->GetDashboard()->Describe());
	}
	// The engine lamp used to be part of this check: since stage 3's mud and snow the car reaches the wall at a crawl and
	// the engine keeps most of its health, so the lamp is the body test's business (a hard hit there) and the env test's.
	const bool bDashOk = Car->GetDashboard() && Car->GetDashboard()->GreyboxPartCount > 0;
	FinishTest(bReachedSnow && bMudSlowed && bWallHit && bFuelUsed && bUpright && bDashOk,
		FString::Printf(TEXT("reachedSnow=%d mudSlowed=%d (entry %.0f exit %.0f) wallHit=%d impacts=%d lastRegion=%d lastDeltaV=%.0f engine=%.2f radiator=%.2f fuelUsed=%.2f L maxspeed=%.0f cm/s finalX=%.0f finalZ=%.0f"),
			bReachedSnow ? 1 : 0, bMudSlowed ? 1 : 0, Mud.EntrySpeed, Mud.ExitSpeed, bWallHit ? 1 : 0,
			Condition ? Condition->TotalImpacts : 0, Condition ? static_cast<int32>(Condition->LastImpactRegion) : -1,
			Condition ? Condition->LastImpactDeltaV : 0.f,
			Condition ? Condition->GetPartHealth(EGTCarPart::Engine) : 0.f,
			Condition ? Condition->GetPartHealth(EGTCarPart::Radiator) : 0.f,
			Condition ? Condition->LitresUsed : 0.f, SelfTestMaxSpeed, Location.X, Location.Z));
}

// ---- grip test (driving feel stage 1) -----------------------------------------------------------------

void AGTDriveTestGameMode::GripFrameTick(float DeltaSeconds)
{
	const AGTCarPawn* Car = Cast<AGTCarPawn>(UGameplayStatics::GetPlayerPawn(this, 0));
	const UChaosWheeledVehicleMovementComponent* Move = Car ? Car->GetChaosMovement() : nullptr;
	if (!Move || !GripRuns.IsValidIndex(GripRun) || GripPhase != 3 || DeltaSeconds <= KINDA_SMALL_NUMBER)
	{
		return;
	}
	FGripRun& Run = GripRuns[GripRun];
	// Lateral acceleration on the circle: yaw rate x speed, what the seat feels once the turn is steady.
	const float Speed = Car->GetMesh()->GetComponentVelocity().Size2D();
	const float YawRate = FMath::DegreesToRadians(Car->GetMesh()->GetPhysicsAngularVelocityInDegrees().Z);
	const float LatG = FMath::Abs(YawRate) * Speed / 980.f;
	Run.SumLatG += LatG * DeltaSeconds;
	Run.SumSpeed += Speed * DeltaSeconds;
	Run.SumTime += DeltaSeconds;
	Run.PeakLatG = FMath::Max(Run.PeakLatG, LatG);
	Run.MinSpeed = FMath::Min(Run.MinSpeed, Speed);
	for (int32 Index = 0; Index < 2 && Index < Move->WheelSetups.Num(); ++Index)
	{
		Run.MaxSlipDeg = FMath::Max(Run.MaxSlipDeg, FMath::RadiansToDegrees(FMath::Abs(Move->GetWheelState(Index).SlipAngle)));
	}
}

void AGTDriveTestGameMode::GripSelfTestTick(AGTCarPawn& Car, UChaosWheeledVehicleMovementComponent& Move)
{
	const float Speed = Move.GetForwardSpeed();
	if (GripRun < 0 || GripPhase == 4)
	{
		++GripRun;
		if (!GripRuns.IsValidIndex(GripRun))
		{
			const FVector Location = Car.GetActorLocation();
			const bool bUpright = Location.Z > -100.f && Location.Z < 500.f && Car.GetActorUpVector().Z > 0.6f;
			const FGripRun& Tarmac = GripRuns[0];
			const FGripRun& Dirt = GripRuns[1];
			const bool bTarmacOk = Tarmac.MeanLatG >= 0.75f && Tarmac.MeanLatG <= 1.15f;
			const bool bDirtOk = Dirt.MeanLatG >= 0.42f && Dirt.MeanLatG <= 0.75f && Dirt.MeanLatG < Tarmac.MeanLatG * 0.85f;
			const bool bSlid = Dirt.MaxSlipDeg >= 8.f && Tarmac.MaxSlipDeg >= 8.f;
			const bool bKeptSpeed = Tarmac.MinSpeed > 800.f && Dirt.MinSpeed > 800.f;
			FinishTest(bTarmacOk && bDirtOk && bSlid && bKeptSpeed && bUpright,
				FString::Printf(TEXT("grip: tarmac %.2f g mean (peak %.2f, slip %.0f deg, %.0f-%.0f km/h) dirt %.2f g mean (peak %.2f, slip %.0f deg, %.0f-%.0f km/h) tarmacOk=%d dirtOk=%d slid=%d keptSpeed=%d upright=%d"),
					Tarmac.MeanLatG, Tarmac.PeakLatG, Tarmac.MaxSlipDeg, Tarmac.MinSpeed * 0.036f, Tarmac.MeanSpeed * 0.036f,
					Dirt.MeanLatG, Dirt.PeakLatG, Dirt.MaxSlipDeg, Dirt.MinSpeed * 0.036f, Dirt.MeanSpeed * 0.036f,
					bTarmacOk ? 1 : 0, bDirtOk ? 1 : 0, bSlid ? 1 : 0, bKeptSpeed ? 1 : 0, bUpright ? 1 : 0));
			return;
		}
		// Drop the car at the pad's near corner facing +X: the straight runs along the pad, the circle turns left into it.
		Car.SetRawSteer(0.f);
		Move.SetThrottleInput(0.f);
		Move.SetHandbrakeInput(false);
		Car.SetActorLocationAndRotation(GripRuns[GripRun].PadCentre + FVector(-9500.f, 6000.f, 120.f), FRotator::ZeroRotator, false, nullptr, ETeleportType::TeleportPhysics);
		Car.GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
		Car.GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
		GripPhase = 0;
		GripPhaseTime = 0.f;
		return;
	}
	GripPhaseTime += SelfTestInterval;
	FGripRun& Run = GripRuns[GripRun];
	const UGTTractionComponent* Traction = Car.GetTraction();
	const FGTWheelTraction* FL = (Traction && Traction->Wheels.Num() > 0) ? &Traction->Wheels[0] : nullptr;
	switch (GripPhase)
	{
	case 0:   // settle on the pad
		if (GripPhaseTime >= 1.5f)
		{
			// At rest: what the springs carry against the car's weight, and where the body sits over the pad's top (z = 1).
			FString Springs;
			float Sum = 0.f;
			for (int32 Index = 0; Index < Move.WheelSetups.Num(); ++Index)
			{
				const FWheelStatus& Status = Move.GetWheelState(Index);
				Sum += Status.SpringForce;
				Springs += FString::Printf(TEXT(" [%d] spring=%.0f norm=%.2f contact=%d"), Index, Status.SpringForce, Status.NormalizedSuspensionLength, Status.bInContact ? 1 : 0);
			}
			FString Boxes;
			if (const UPhysicsAsset* Asset = Car.GetMesh()->GetPhysicsAsset())
			{
				for (const USkeletalBodySetup* Body : Asset->SkeletalBodySetups)
				{
					for (const FKBoxElem& Box : Body->AggGeom.BoxElems)
					{
						Boxes += FString::Printf(TEXT(" %s(z %.0f..%.0f)"), *Body->BoneName.ToString(), Box.Center.Z - Box.Z * 0.5f, Box.Center.Z + Box.Z * 0.5f);
					}
				}
			}
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST grip %s at rest: springs sum %.0f of weight %.0f (%.0f%%), actor z %.1f, loadFL=%.0f ratioFL=%.2f;%s; boxes%s"), *Run.Name, Sum, Move.Mass * 980.f,
				Sum / (Move.Mass * 9.8f), Car.GetActorLocation().Z, FL ? FL->Load : -1.f, Move.Wheels.IsValidIndex(0) && Move.Wheels[0] ? Move.Wheels[0]->WheelLoadRatio : -1.f, *Springs, *Boxes);
			GripPhase = 1;
			GripPhaseTime = 0.f;
		}
		break;
	case 1:   // straight to the entry speed
		Move.SetThrottleInput(1.f);
		if (Speed >= GripEntrySpeed || GripPhaseTime >= 14.f)
		{
			Run.EntrySpeed = Speed;
			Car.SetRawSteer(-1.f);   // full lock left
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST grip %s: full lock at %.0f km/h after %.1f s, surfFL=%s frictionFL=%.2f loadFL=%.0f"), *Run.Name, Speed * 0.036f, GripPhaseTime,
				FL ? *FL->SurfaceTag.ToString() : TEXT("?"), FL ? FL->SurfaceFriction : -1.f, FL ? FL->Load : -1.f);
			GripPhase = 2;
			GripPhaseTime = 0.f;
		}
		break;
	case 2:   // a second for the turn to settle
	case 3:   // measure, the throttle holding the speed against the scrub
		Move.SetThrottleInput(Speed < GripEntrySpeed - 60.f ? 1.f : 0.4f);
		if (GripPhase == 2 && GripPhaseTime >= 1.f)
		{
			GripPhase = 3;
			GripPhaseTime = 0.f;
		}
		else if (GripPhase == 3 && GripPhaseTime >= 4.f)
		{
			Run.MeanLatG = Run.SumTime > 0.f ? Run.SumLatG / Run.SumTime : 0.f;
			Run.MeanSpeed = Run.SumTime > 0.f ? Run.SumSpeed / Run.SumTime : 0.f;
			FString PerWheel;
			for (int32 Index = 0; Index < Move.WheelSetups.Num(); ++Index)
			{
				const FWheelStatus& Status = Move.GetWheelState(Index);
				PerWheel += FString::Printf(TEXT(" [%d] spring=%.0f load=%.0f norm=%.2f slip=%.0f grip=%.2f"), Index, Status.SpringForce,
					Traction && Traction->Wheels.IsValidIndex(Index) ? Traction->Wheels[Index].Load : -1.f, Status.NormalizedSuspensionLength,
					FMath::RadiansToDegrees(FMath::Abs(Status.SlipAngle)), Traction && Traction->Wheels.IsValidIndex(Index) ? Traction->Wheels[Index].FrictionScale : -1.f);
			}
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST grip %s mid-corner:%s"), *Run.Name, *PerWheel);
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST grip %s: mean %.2f g (peak %.2f) at %.0f km/h mean (min %.0f), front slip up to %.0f deg, yaw %.1f steerIn=%.2f loadFL=%.0f correction=%.2f at (%.0f, %.0f, %.0f) up=%.2f"),
				*Run.Name, Run.MeanLatG, Run.PeakLatG, Run.MeanSpeed * 0.036f, Run.MinSpeed * 0.036f, Run.MaxSlipDeg, Car.GetActorRotation().Yaw, Move.GetSteeringInput(), FL ? FL->Load : -1.f,
				Traction ? Traction->LoadCorrection : -1.f, Car.GetActorLocation().X, Car.GetActorLocation().Y, Car.GetActorLocation().Z, Car.GetActorUpVector().Z);
			GripPhase = 4;
		}
		break;
	default:
		break;
	}
	if (SelfTestElapsed >= SelfTestDuration)
	{
		FinishTest(false, TEXT("grip test ran out of time"));
	}
}

// ---- drivetrain test (driving feel stage 4) -----------------------------------------------------------

namespace
{
	// The ramp of the drivetrain test: its foot at (0, 6000, 0), 35 % up along +X.
	float RampPitchDegrees() { return FMath::RadiansToDegrees(FMath::Atan(0.35f)); }
	FVector RampAlong() { const float P = FMath::DegreesToRadians(RampPitchDegrees()); return FVector(FMath::Cos(P), 0.f, FMath::Sin(P)); }
	FVector RampUp() { const float P = FMath::DegreesToRadians(RampPitchDegrees()); return FVector(-FMath::Sin(P), 0.f, FMath::Cos(P)); }
	FVector RampSlopePoint(float AlongCm) { return FVector(0.f, 6000.f, 0.f) + RampAlong() * AlongCm; }
}

void AGTDriveTestGameMode::DrivetrainSelfTestTick(AGTCarPawn& Car, UChaosWheeledVehicleMovementComponent& Move)
{
	UGTDrivetrainComponent* Train = Car.GetDrivetrain();
	if (!Train)
	{
		FinishTest(false, TEXT("no drivetrain component"));
		return;
	}
	DrivetrainPhaseTime += SelfTestInterval;
	const FVector Location = Car.GetActorLocation();
	const float Speed = Move.GetForwardSpeed();
	auto Place = [&](const FVector& Where, float Yaw, float Pitch = 0.f, bool bHandbrake = false)
	{
		Move.SetThrottleInput(0.f);
		Move.SetBrakeInput(0.f);
		Move.SetHandbrakeInput(bHandbrake);
		Car.SetRawSteer(0.f);
		Car.SetActorLocationAndRotation(Where, FRotator(Pitch, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		Car.GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
		Car.GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
		DrivetrainStart = Where;
		DrivetrainPhaseTime = 0.f;
	};
	const float Distance = FVector::Dist2D(Location, DrivetrainStart);
	GearsSeen = FMath::Max(GearsSeen, Train->MaxGearReached);
	if (FMath::IsNearlyEqual(FMath::Fmod(DrivetrainPhaseTime, 1.f), 0.f, 0.01f))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST drivetrain phase %d t=%.1f speed=%.0f dist=%.0f z=%.0f loadCorr=%.2f %s"), DrivetrainPhase, DrivetrainPhaseTime, Speed, Distance, Location.Z,
			Car.GetTraction() ? Car.GetTraction()->LoadCorrection : -1.f, *Train->Describe());
	}
	switch (DrivetrainPhase)
	{
	case 0:   // spawn settles; the left wheels sit on the ice strip (the spawn is at x 0, the strip runs from -100 to 3900 cm at y -250..-50)
		if (DrivetrainPhaseTime >= 1.5f)
		{
			Place(FVector(0.f, 0.f, 120.f), 0.f);
			DrivetrainPhase = 1;
		}
		break;
	case 1:   // settle after the drop
		if (DrivetrainPhaseTime >= 1.f)
		{
			Train->SetDiffLock(false);
			Train->SetLowRange(false);
			DrivetrainStart = Car.GetActorLocation();
			Move.SetThrottleInput(1.f);
			DrivetrainPhase = 2;
			DrivetrainPhaseTime = 0.f;
		}
		break;
	case 2:   // open diffs, full throttle 4 s: the ice side spins, the car barely moves
		Move.SetThrottleInput(1.f);
		if (DrivetrainPhaseTime >= 4.f)
		{
			SplitOpenCm = Distance;
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST drivetrain split open: %.0f cm in 4 s"), SplitOpenCm);
			Train->SetDiffLock(true);
			DrivetrainStart = Car.GetActorLocation();
			DrivetrainPhase = 3;
			DrivetrainPhaseTime = 0.f;
		}
		break;
	case 3:   // locked, 4 s more: the grip side takes the torque
		Move.SetThrottleInput(1.f);
		if (DrivetrainPhaseTime >= 4.f)
		{
			SplitLockedCm = Distance;
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST drivetrain split locked: %.0f cm in 4 s"), SplitLockedCm);
			Train->SetDiffLock(false);
			// On the 35 % slope 10 m up the ramp, held by the handbrake: a standing start, no run-up to lean on.
			Place(RampSlopePoint(1000.f) + RampUp() * 130.f, 0.f, RampPitchDegrees(), true);
			DrivetrainPhase = 4;
		}
		break;
	case 4:   // settle on the brake, then coast free for 2 s (what gravity alone does on the slope), then high range from a standing start
		if (DrivetrainPhaseTime >= 1.5f && DrivetrainPhaseTime < 1.6f)
		{
			DrivetrainStart = Car.GetActorLocation();
			Move.SetHandbrakeInput(false);
			Car.GetMesh()->WakeAllRigidBodies();   // Chaos sleeps a parked car; releasing a pedal does not wake it
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST drivetrain slope coast: released, pitch %.1f, loadCorr %.2f, gravity %.0f, mass %.0f"), Car.GetActorRotation().Pitch,
				Car.GetTraction() ? Car.GetTraction()->LoadCorrection : -1.f, GetWorld()->GetGravityZ(), Move.Mass);
		}
		if (DrivetrainPhaseTime >= 3.5f)
		{
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST drivetrain slope coast: after 2 s speed %.0f cm/s (gravity alone would give about -650), moved %.1f m, pitch %.1f, loadCorr %.2f"),
				Speed, (Location.Z - DrivetrainStart.Z) * 0.01f, Car.GetActorRotation().Pitch, Car.GetTraction() ? Car.GetTraction()->LoadCorrection : -1.f);
			Place(RampSlopePoint(1000.f) + RampUp() * 130.f, 0.f, RampPitchDegrees(), true);
			DrivetrainPhase = 10;
		}
		break;
	case 10:   // settle on the brake again, then high range from a standing start
		if (DrivetrainPhaseTime >= 1.5f)
		{
			RampPeakM = 0.f;
			DrivetrainStart = Car.GetActorLocation();
			Move.SetHandbrakeInput(false);
			Move.SetThrottleInput(1.f);
			DrivetrainPhase = 5;
			DrivetrainPhaseTime = 0.f;
		}
		break;
	case 5:
		Move.SetThrottleInput(1.f);
		RampPeakM = FMath::Max(RampPeakM, (Location.Z - DrivetrainStart.Z) * 0.01f);
		if (DrivetrainPhaseTime >= 8.f || RampPeakM > 25.f)
		{
			RampHighM = RampPeakM;
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST drivetrain ramp high range: climbed %.1f m from a standing start (now %.1f m)"), RampHighM, (Location.Z - DrivetrainStart.Z) * 0.01f);
			Place(RampSlopePoint(1000.f) + RampUp() * 130.f, 0.f, RampPitchDegrees(), true);
			Train->SetLowRange(true);
			DrivetrainPhase = 6;
		}
		break;
	case 6:   // settle on the brake, then low range from the same standing start
		if (DrivetrainPhaseTime >= 1.5f)
		{
			RampPeakM = 0.f;
			DrivetrainStart = Car.GetActorLocation();
			Move.SetHandbrakeInput(false);
			Move.SetThrottleInput(1.f);
			DrivetrainPhase = 7;
			DrivetrainPhaseTime = 0.f;
		}
		break;
	case 7:
		Move.SetThrottleInput(1.f);
		RampPeakM = FMath::Max(RampPeakM, (Location.Z - DrivetrainStart.Z) * 0.01f);
		if (DrivetrainPhaseTime >= 8.f || RampPeakM > 25.f)
		{
			RampLowM = RampPeakM;
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST drivetrain ramp low range: climbed %.1f m"), RampLowM);
			Train->SetLowRange(false);
			Place(FVector(-5000.f, -5000.f, 120.f), 0.f);   // clear floor
			DrivetrainPhase = 8;
		}
		break;
	case 8:   // settle, then the brake pedal held from rest: reverse
		if (DrivetrainPhaseTime >= 1.f)
		{
			Move.SetBrakeInput(1.f);
			DrivetrainPhase = 9;
			DrivetrainPhaseTime = 0.f;
		}
		break;
	case 9:
		Move.SetBrakeInput(1.f);
		if (DrivetrainPhaseTime >= 3.f)
		{
			ReverseSpeed = Speed;
			Move.SetBrakeInput(0.f);
			const bool bSplitOk = SplitOpenCm >= 0.f && SplitOpenCm < 400.f && SplitLockedCm > 1000.f && SplitLockedCm > 2.f * SplitOpenCm;
			const bool bRampOk = RampHighM < 3.f && RampLowM > 8.f && RampLowM > RampHighM + 5.f;
			const bool bReverseOk = ReverseSpeed < -100.f && Train->IsReversing();
			const bool bGearsOk = GearsSeen >= 2;
			FinishTest(bSplitOk && bRampOk && bReverseOk && bGearsOk,
				FString::Printf(TEXT("drivetrain: split-mu open %.0f cm locked %.0f cm ok=%d; ramp 35%% high %.1f m low %.1f m ok=%d; reverse %.0f cm/s ok=%d; gears up to %d ok=%d"),
					SplitOpenCm, SplitLockedCm, bSplitOk ? 1 : 0, RampHighM, RampLowM, bRampOk ? 1 : 0, ReverseSpeed, bReverseOk ? 1 : 0, GearsSeen, bGearsOk ? 1 : 0));
		}
		break;
	default:
		break;
	}
	if (SelfTestElapsed >= SelfTestDuration)
	{
		FinishTest(false, TEXT("drivetrain test ran out of time"));
	}
}
