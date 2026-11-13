#include "Core/GTProvingShotsRunner.h"

#include "Core/GTPlayerController.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTProvingGround.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTTractionComponent.h"

#include "Camera/CameraActor.h"
#include "Components/StaticMeshComponent.h"
#include "ContentStreaming.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Materials/MaterialInterface.h"
#include "Engine/DirectionalLight.h"
#include "EngineUtils.h"
#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#endif

namespace
{
	constexpr int32 LastStep = 4;          // LOOK L1's step 4 (the painted props beside the parked car)
	constexpr float SettleMaxS = 30.f;     // Dirt grows 0.3 cm/s at rest (30 % of 0.01 m/s): 5 cm in about 17 s
	constexpr float CameraBackCm = 450.f;  // from the car's middle, square to its side
	constexpr float EyeCm = 70.f;          // above the ground there
	const TCHAR* ShotFolder = TEXT("Proving");
	constexpr float BasinEyeCm = 500.f;    // step 2: a raised eye over the station's ground (170, a standing eye, saw the pond at 3-10 degrees: a sliver)
	// Step 3 (RIVERBED S4): the rut view and the stretch of the left wheels' path it measures, metres from the entry waterline.
	constexpr float RutEyeBackM = 3.f;     // behind the entry waterline along the route
	constexpr float RutEyeLeftM = 3.f;     // to the left of the road
	constexpr float RutEyeUpCm = 300.f;    // over the ground there
	constexpr float RutAimM = 2.75f;       // the aim: the left wheel line this far into the water
	constexpr float RutFromM = 0.5f;       // the measured stretch of the path
	constexpr float RutToM = 5.f;
	constexpr float RutHalfWidthCm = 12.f; // either side of a wheel's path (a 25 cm tyre)
	constexpr float CtrlLeftCm = 250.f;    // the untouched wet bed: the same path this far further left
	constexpr float AssumedHalfTrackCm = 80.f;
	// Wet means more than this much water: a dry cell under a sheet's placed box answers its bed as the surface, and the
	// bed (the field's cell, bilinear) stands a few millimetres off the landscape at a point (the first run of this step
	// found its "waterline" 5.6 m up the dry approach at depth > 0).
	constexpr float WetCm = 2.f;
	// Step 4 (LOOK L1): where the painted props stand along the parked car's heading and where the camera stands.
	constexpr float PaintBoxAheadCm = 380.f;    // SM_TestBox's middle, ahead of the car's origin
	constexpr float PaintCarBehindCm = 520.f;   // SM_TestCar's origin, behind it (4.3 m long: a metre clear of the car)
	constexpr float PaintEyeBackCm = 900.f;     // square to the car, on the sunlit side (past the 7 m half-width of the top)
	constexpr float PaintEyeUpCm = 160.f;       // over the higher of the ground there and the car's (the top falls away at its edge)
	const TCHAR* PaintGreyPath = TEXT("/Game/GrandTour/Materials/M_GT_PaintedGrey.M_GT_PaintedGrey");
}

FGTProvingShotsRunner::FGTProvingShotsRunner(UWorld* InWorld)
	: World(InWorld)
{
	FParse::Value(FCommandLine::Get(), TEXT("GTShotsFrom="), ShotsFrom);
	// Step 1's three pictures (the bank from both sides, the flat control), step 2's one (forda's pond from its station),
	// step 3's three (the ruts before and after a crossing, the bed patch's box edge), step 4's two (the painted props
	// before and after).
	ExpectedShots = (ShotsFrom <= 1 ? 3 : 0) + (ShotsFrom <= 2 ? 1 : 0) + (ShotsFrom <= 3 ? 3 : 0) + (ShotsFrom <= 4 ? 2 : 0);
}

void FGTProvingShotsRunner::Log(const FString& Line) const
{
	UE_LOG(LogTemp, Display, TEXT("GTPROVINGSHOTS step %d: %s"), Step, *Line);
}

void FGTProvingShotsRunner::Next()
{
	++Step;
	StepTime = 0.f;
	Enter(0);
}

void FGTProvingShotsRunner::Enter(int32 InSubStep)
{
	SubStep = InSubStep;
	SubTime = 0.f;
}

void FGTProvingShotsRunner::ShowFromCamera(const FVector& Location, const FRotator& Rotation)
{
	if (!ShotCamera.IsValid())
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ShotCamera = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), Location, Rotation, Params);
	}
	if (ShotCamera.IsValid())
	{
		ShotCamera->SetActorLocationAndRotation(Location, Rotation);
		PC->SetViewTarget(ShotCamera.Get());
	}
	if (PC->GetHUD())
	{
		PC->GetHUD()->bShowHUD = false;
	}
}

void FGTProvingShotsRunner::RequestShot(const FString& Name)
{
	const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("Screenshots") / ShotFolder / Name + TEXT(".png"));
	IFileManager::Get().Delete(*Path, false, true, true);
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path), true);
	FScreenshotRequest::RequestScreenshot(Path, /*bInShowUI*/ false, /*bAddFilenameSuffix*/ false);
	ShotFiles.Add(Path);
	Log(FString::Printf(TEXT("screenshot requested: %s"), *Path));
}

bool FGTProvingShotsRunner::Project(const FVector& Point, FVector2D& OutScreen) const
{
	return PC.IsValid() && PC->ProjectWorldLocationToScreen(Point, OutScreen, false);
}

float FGTProvingShotsRunner::Ground(float XCm, float YCm) const
{
	float Z = 0.f;
	if (!GTProving::GroundZ(World.Get(), XCm, YCm, Z, Car.Get()))
	{
		Z = GTTerrain::SampleHeightCm(Spec, XCm, YCm);
	}
	return Z;
}

bool FGTProvingShotsRunner::FindBankSpot(FVector2D& OutCentre, float& OutYaw)
{
	// forda: the first Ford section. From the crossing's middle, out along the channel either side (square to the road,
	// the car facing away from it) for the first place where the whole car stands on the channel's floor as it was
	// Mud-dominant before section 52 (the channel's dig past 1.5 m, where the paint's Mud weight passed a half), dry
	// (no water at a wheel or a metre beyond the bumpers) and level enough (25 cm across the wheels).
	const FGTRouteSection* Ford = nullptr;
	for (const FGTRouteSection& Section : Spec.Sections)
	{
		if (Section.Kind == EGTRouteSectionKind::Ford)
		{
			Ford = &Section;
			break;
		}
	}
	if (!Ford)
	{
		Log(TEXT("bank: no Ford section in the spec"));
		return false;
	}
	const UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>();
	const UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	const float MidArc = 0.5f * (Ford->StartM + Ford->EndM);
	float RouteYaw = 0.f;
	const FVector2D Mid = GTTerrain::PointOnPolyline(Spec.RouteM, MidArc, RouteYaw) * 100.f;
	const FVector2D Left(-FMath::Sin(FMath::DegreesToRadians(RouteYaw)), FMath::Cos(FMath::DegreesToRadians(RouteYaw)));
	const float MinDigM = FMath::Max(0.1f, Spec.MudChannelDepthM);
	int32 Wet = 0, Shallow = 0, Steep = 0;
	float BestDig = -1.f;
	FVector2D BestCentre = FVector2D::ZeroVector;
	float BestYaw = 0.f;
	for (float D = 1000.f; D <= 4500.f; D += 100.f)
	{
		for (const float Sign : { -1.f, 1.f })
		{
			const FVector2D Centre = Mid + Left * (Sign * D);
			const FVector2D Fwd = Left * Sign;
			const FVector2D Right(-Fwd.Y, Fwd.X);
			bool bDry = true;
			float MinDig = 1.e9f;
			float MinZ = 1.e9f;
			float MaxZ = -1.e9f;
			for (const FVector2D& Offset : { FVector2D(140.f, 80.f), FVector2D(140.f, -80.f), FVector2D(-140.f, 80.f), FVector2D(-140.f, -80.f), FVector2D(340.f, 0.f), FVector2D(-340.f, 0.f) })
			{
				const FVector2D P = Centre + Fwd * Offset.X + Right * Offset.Y;
				const float Z = Ground(P.X, P.Y);
				if (Water && Water->Sample(FVector(P.X, P.Y, Z)).DepthCm > 0.f)
				{
					bDry = false;
				}
				if (FMath::Abs(Offset.X) < 200.f)
				{
					MinDig = FMath::Min(MinDig, GTTerrain::ChannelDigM(Spec, P.X / 100.f, P.Y / 100.f));
					MinZ = FMath::Min(MinZ, Z);
					MaxZ = FMath::Max(MaxZ, Z);
				}
			}
			if (!bDry)
			{
				++Wet;
				continue;
			}
			if (MinDig > BestDig)
			{
				BestDig = MinDig;
				BestCentre = Centre;
				BestYaw = FMath::RadiansToDegrees(FMath::Atan2(Fwd.Y, Fwd.X));
			}
			if (MinDig < MinDigM)
			{
				++Shallow;
				continue;
			}
			if (MaxZ - MinZ > 25.f)
			{
				++Steep;
				continue;
			}
			OutCentre = Centre;
			OutYaw = FMath::RadiansToDegrees(FMath::Atan2(Fwd.Y, Fwd.X));
			Log(FString::Printf(TEXT("bank: forda's crossing at (%.0f, %.0f) route yaw %.1f; the car %.0f m to the %s along the channel at (%.0f, %.0f) yaw %.1f: the channel's dig under the wheels %.2f m or more (Mud-dominant before section 52 past %.2f), dry, %.0f cm across the wheels; %d places wet, %d shallower, %d steeper before it; inside a mud patch box %d"),
				Mid.X, Mid.Y, RouteYaw, D / 100.f, Sign > 0.f ? TEXT("left") : TEXT("right"), Centre.X, Centre.Y, OutYaw, MinDig, MinDigM, MaxZ - MinZ, Wet, Shallow, Steep,
				(Mud && Mud->PatchAt(Centre)) ? 1 : 0));
			return true;
		}
	}
	if (BestDig > 0.f)
	{
		OutCentre = BestCentre;
		OutYaw = BestYaw;
		Log(FString::Printf(TEXT("bank: no dry place past a %.2f m dig; the deepest dry one instead, dig %.2f m at (%.0f, %.0f) yaw %.1f (%d wet, %d shallower, %d steeper)"),
			MinDigM, BestDig, BestCentre.X, BestCentre.Y, BestYaw, Wet, Shallow, Steep));
		return true;
	}
	Log(FString::Printf(TEXT("bank: no dry place beside forda (%d wet)"), Wet));
	return false;
}

void FGTProvingShotsRunner::LogSinkage(const TCHAR* When) const
{
	const UGTTractionComponent* Traction = Car.IsValid() ? Car->GetTraction() : nullptr;
	const UChaosWheeledVehicleMovementComponent* Move = Car.IsValid() ? Car->GetChaosMovement() : nullptr;
	if (!Traction || !Move)
	{
		return;
	}
	FString Line;
	for (int32 Index = 0; Index < Traction->Wheels.Num(); ++Index)
	{
		const FGTWheelTraction& W = Traction->Wheels[Index];
		const UChaosVehicleWheel* Setup = Move->Wheels.IsValidIndex(Index) ? Move->Wheels[Index].Get() : nullptr;
		Line += FString::Printf(TEXT(" | w%d c=%d raw %.2f vis %.2f cm r %.1f tag %s box %d"), Index, W.bInContact ? 1 : 0, W.Sinkage * 100.f, W.VisibleSinkage * 100.f,
			Setup ? Setup->GetWheelRadius() : 0.f, *W.SurfaceTag.ToString(), W.bInPatchBox ? 1 : 0);
	}
	Log(FString::Printf(TEXT("sinkage %s (t %.1f s)%s"), When, SubTime, *Line));
}

void FGTProvingShotsRunner::LogWheels(const FString& Picture, const FVector& Eye)
{
	const UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement();
	const USkeletalMeshComponent* Mesh = Car->GetMesh();
	const UGTTractionComponent* Traction = Car->GetTraction();
	if (!Move || !Mesh || !Traction)
	{
		Log(TEXT("wheels: no movement, mesh or traction"));
		return;
	}
	FVector2D ViewSize(0.0, 0.0);
	if (GEngine && GEngine->GameViewport)
	{
		GEngine->GameViewport->GetViewportSize(ViewSize);
	}
	const FVector Up = Mesh->GetUpVector();
	const FVector Fwd = Mesh->GetForwardVector();
	const FVector Right = Mesh->GetRightVector();
	const FVector CarAt = Car->GetActorLocation();
	const FVector ToCam = (Eye - CarAt).GetSafeNormal2D();
	const float Toward = FVector::DotProduct(Right, ToCam) >= 0.f ? 1.f : -1.f;   // the side of each tyre that faces the camera
	// Which side the sun is on: the tyres the camera sees are lit or in the car's shade (a grey tyre in shade reads like
	// the shadow it stands in, so the sampler can only measure the lit side).
	int32 Sunlit = -1;
	for (TActorIterator<ADirectionalLight> It(World.Get()); It; ++It)
	{
		Sunlit = FVector::DotProduct(ToCam, -It->GetActorForwardVector().GetSafeNormal2D()) > 0.f ? 1 : 0;
		break;
	}
	Log(FString::Printf(TEXT("wheels %s: viewport %.0f x %.0f, eye (%.0f, %.0f, %.0f), sunlit %d"), *Picture, ViewSize.X, ViewSize.Y, Eye.X, Eye.Y, Eye.Z, Sunlit));
	for (int32 Index = 0; Index < Move->WheelSetups.Num() && Index < Move->Wheels.Num(); ++Index)
	{
		const UChaosVehicleWheel* Setup = Move->Wheels[Index];
		if (!Setup)
		{
			continue;
		}
		const FVector Centre = Mesh->GetBoneLocation(Move->WheelSetups[Index].BoneName);
		const bool bNear = FVector::DotProduct(Centre - CarAt, ToCam) > 0.f;
		// The drawn tyre keeps its size (the Chaos radius is what shrinks): the class default's radius, 38 cm.
		const float DrawnR = GetDefault<UChaosVehicleWheel>(Setup->GetClass())->WheelRadius;
		const FVector Face = Centre + Right * (Toward * Setup->WheelWidth * 0.5f);
		const FVector Low = Face - Up * DrawnR;
		// The box round the tyre's lower half: its arc from 60 degrees either side of the bottom, the hub's height at half
		// a radius fore and aft, and 15 cm under the lowest point.
		FVector2D BoxMin(1.e9f, 1.e9f);
		FVector2D BoxMax(-1.e9f, -1.e9f);
		int32 OnScreen = 0;
		TArray<FVector> Points;
		for (int32 K = -2; K <= 2; ++K)
		{
			const float A = FMath::DegreesToRadians(30.f * K);
			Points.Add(Face - Up * (DrawnR * FMath::Cos(A)) + Fwd * (DrawnR * FMath::Sin(A)));
		}
		Points.Add(Face + Fwd * (DrawnR * 0.5f));
		Points.Add(Face - Fwd * (DrawnR * 0.5f));
		Points.Add(Low - Up * 15.f);
		for (const FVector& P : Points)
		{
			FVector2D S;
			if (Project(P, S))
			{
				++OnScreen;
				BoxMin = FVector2D(FMath::Min(BoxMin.X, S.X), FMath::Min(BoxMin.Y, S.Y));
				BoxMax = FVector2D(FMath::Max(BoxMax.X, S.X), FMath::Max(BoxMax.Y, S.Y));
			}
		}
		FVector2D LowS(-1.0, -1.0);
		Project(Low, LowS);
		// The ground line under the tyre's outer face: the ground there at half a radius behind, under and ahead of the hub.
		FVector2D G[3];
		float GroundUnder = 0.f;
		for (int32 K = 0; K < 3; ++K)
		{
			const FVector P = Face + Fwd * (DrawnR * 0.5f * (K - 1));
			const float Z = Ground(P.X, P.Y);
			if (K == 1)
			{
				GroundUnder = Z;
			}
			G[K] = FVector2D(-1.0, -1.0);
			Project(FVector(P.X, P.Y, Z), G[K]);
		}
		// The ground between the face and the camera hides the tyre where it stands higher on screen than the ground at the
		// face (a bump in front): the highest projected ground point every 10 cm over the 2 m in front of the face.
		float Occluder = G[1].Y;
		const FVector ToEye = (Eye - Face).GetSafeNormal2D();
		for (int32 K = 1; K <= 20; ++K)
		{
			const FVector P = Face + ToEye * (10.f * K);
			FVector2D S;
			if (Project(FVector(P.X, P.Y, Ground(P.X, P.Y)), S))
			{
				Occluder = FMath::Min(Occluder, static_cast<float>(S.Y));
			}
		}
		const FGTWheelTraction* T = Traction->Wheels.IsValidIndex(Index) ? &Traction->Wheels[Index] : nullptr;
		Log(FString::Printf(TEXT("wheel %s w%d near %d sunlit %d occluder %.1f box %.0f %.0f %.0f %.0f corners %d low %.1f %.1f ground %.1f %.1f %.1f %.1f %.1f %.1f | drawn radius %.1f cm, the drawn tyre's lowest point %.1f cm under the ground at its face (hub %.1f, low %.1f, ground %.1f); raw %.2f vis %.2f cm, Chaos radius %.1f, tag %s, in a patch box %d"),
			*Picture, Index, bNear ? 1 : 0, Sunlit, Occluder, BoxMin.X, BoxMin.Y, BoxMax.X, BoxMax.Y, OnScreen, LowS.X, LowS.Y, G[0].X, G[0].Y, G[1].X, G[1].Y, G[2].X, G[2].Y,
			DrawnR, GroundUnder - Low.Z, Centre.Z, Low.Z, GroundUnder, T ? T->Sinkage * 100.f : -1.f, T ? T->VisibleSinkage * 100.f : -1.f, Setup->GetWheelRadius(),
			T ? *T->SurfaceTag.ToString() : TEXT("-"), (T && T->bInPatchBox) ? 1 : 0));
	}
}

void FGTProvingShotsRunner::TickBank(float DeltaSeconds)
{
	AGTCarPawn* TheCar = Car.Get();
	switch (SubStep)
	{
	case 0:
	{
		if (bControl)
		{
			// The control: the first flat Dirt plane (a climb's top, relief 2 cm against the scrub's 12), the car along it.
			bool bFound = false;
			for (const FGTTerrainPlane& Plane : Spec.Planes)
			{
				if (Plane.Layer == 1 && FMath::IsNearlyZero(Plane.GradePercent) && FMath::IsNearlyZero(Plane.CrossSlopeDegrees) && Plane.LengthM >= 15.f && Plane.HalfWidthM >= 5.f)
				{
					const float Yaw = FMath::DegreesToRadians(Plane.YawDegrees);
					BankCentre = (Plane.StartM + FVector2D(FMath::Cos(Yaw), FMath::Sin(Yaw)) * (Plane.LengthM * 0.5f)) * 100.f;
					BankYaw = Plane.YawDegrees;
					Log(FString::Printf(TEXT("control: the flat Dirt top at (%.0f, %.0f) yaw %.1f, %.0f x %.0f m, relief %.2f m"), BankCentre.X, BankCentre.Y, BankYaw, Plane.LengthM, Plane.HalfWidthM * 2.f, Plane.RoughnessM));
					bFound = true;
					break;
				}
			}
			if (!bFound)
			{
				Notes.Add(TEXT("control: no flat Dirt plane"));
				Next();
				return;
			}
		}
		else if (!FindBankSpot(BankCentre, BankYaw))
		{
			Notes.Add(TEXT("bank: no spot"));
			Next();
			return;
		}
		const float Z = Ground(BankCentre.X, BankCentre.Y);
		TheCar->SetActorLocationAndRotation(FVector(BankCentre.X, BankCentre.Y, Z + 60.f), FRotator(0.f, BankYaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		TheCar->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
		TheCar->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
		TheCar->ResetDrivingInputs();
		TheCar->SetRawSteer(0.f);
		if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
		{
			Move->SetThrottleInput(0.f);
			Move->SetBrakeInput(0.f);
			Move->SetHandbrakeInput(true);
		}
		if (UGTDrivetrainComponent* Train = TheCar->GetDrivetrain())
		{
			Train->SetLowRange(false);
			Train->SetDiffLock(false);
		}
		LastSinkSum = -1.f;
		SinkCheckTime = 0.f;
		Enter(1);
		break;
	}
	case 1:   // settle until the sinkage stops growing
	{
		SinkCheckTime += DeltaSeconds;
		if (SinkCheckTime < 2.f)
		{
			break;
		}
		SinkCheckTime = 0.f;
		const UGTTractionComponent* Traction = TheCar->GetTraction();
		float Sum = 0.f;
		for (const FGTWheelTraction& W : Traction->Wheels)
		{
			Sum += W.Sinkage;
		}
		LogSinkage(TEXT("settling"));
		const bool bStill = LastSinkSum >= 0.f && FMath::Abs(Sum - LastSinkSum) < 0.002f && SubTime >= 6.f;
		LastSinkSum = Sum;
		if (bStill || SubTime >= SettleMaxS)
		{
			LogSinkage(bStill ? TEXT("settled") : TEXT("settle timed out"));
			Enter(bControl ? 8 : 2);
		}
		break;
	}
	case 2:   // the camera square to the car's left
	case 4:   // then to its right
	case 8:   // the control: the sunlit side
	{
		const FVector Right = TheCar->GetMesh()->GetRightVector().GetSafeNormal2D();
		float Side = SubStep == 2 ? -1.f : 1.f;
		if (SubStep == 8)
		{
			for (TActorIterator<ADirectionalLight> It(World.Get()); It; ++It)
			{
				Side = FVector::DotProduct(Right, -It->GetActorForwardVector().GetSafeNormal2D()) >= 0.f ? 1.f : -1.f;
				break;
			}
		}
		const FVector At = TheCar->GetActorLocation();
		const FVector2D EyeXY = FVector2D(At.X, At.Y) + FVector2D(Right.X, Right.Y) * (Side * CameraBackCm);
		const FVector Eye(EyeXY.X, EyeXY.Y, Ground(EyeXY.X, EyeXY.Y) + EyeCm);
		const FVector LookAt(At.X, At.Y, Ground(At.X, At.Y) + 30.f);
		ShowFromCamera(Eye, (LookAt - Eye).Rotation());
		Log(FString::Printf(TEXT("camera %s of the car: eye (%.0f, %.0f, %.0f), looking at (%.0f, %.0f, %.0f), pitch %.1f"), Side < 0.f ? TEXT("left") : TEXT("right"),
			Eye.X, Eye.Y, Eye.Z, LookAt.X, LookAt.Y, LookAt.Z, (LookAt - Eye).Rotation().Pitch));
		Enter(SubStep + 1);
		break;
	}
	case 3:
	case 5:
	{
		if (SubTime < 3.f)   // the view target taken, auto exposure settled
		{
			break;
		}
		const FString Picture = SubStep == 3 ? TEXT("proving_01_bank_left") : TEXT("proving_02_bank_right");
		LogSinkage(TEXT("at the picture"));
		LogWheels(Picture, ShotCamera.IsValid() ? ShotCamera->GetActorLocation() : FVector::ZeroVector);
		RequestShot(Picture);
		Enter(SubStep == 3 ? 6 : 7);
		break;
	}
	case 6:
		if (SubTime >= 1.5f)
		{
			Enter(4);
		}
		break;
	case 7:
		if (SubTime >= 1.5f)
		{
			bControl = true;
			Enter(0);
		}
		break;
	case 9:
		if (SubTime >= 3.f)
		{
			LogSinkage(TEXT("at the picture"));
			LogWheels(TEXT("proving_03_flat_sunlit"), ShotCamera.IsValid() ? ShotCamera->GetActorLocation() : FVector::ZeroVector);
			RequestShot(TEXT("proving_03_flat_sunlit"));
			Enter(10);
		}
		break;
	default:
		if (SubTime >= 1.5f)
		{
			Next();
		}
		break;
	}
}

void FGTProvingShotsRunner::LogBasinEdges(const FString& Picture)
{
	// RIVERBED S3: along the placed box's two flow-wise ends (the straight edges of the owner's picture 2), pairs of
	// points on the water plane 1 m inside and 1 m outside the old edge, kept where the bed under both stands under the
	// level (inside the basin) and both project on screen. What the car reads there is logged beside each pair.
	const UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>();
	const FGTRouteSection* Ford = Spec.Sections.FindByPredicate([](const FGTRouteSection& S) { return S.Kind == EGTRouteSectionKind::Ford; });
	if (!Water || !Ford)
	{
		Log(TEXT("basin: no water subsystem or no Ford section"));
		return;
	}
	float MidYaw = 0.f;
	const FVector2D Mid = GTTerrain::PointOnPolyline(Spec.RouteM, 0.5f * (Ford->StartM + Ford->EndM), MidYaw) * 100.f;
	const AGTWaterSheet* Sheet = Water->SheetAt(Mid);
	if (!Sheet)
	{
		Log(TEXT("basin: no sheet at forda's middle"));
		return;
	}
	FVector2D ViewSize(1280.0, 720.0);
	if (GEngine && GEngine->GameViewport)
	{
		GEngine->GameViewport->GetViewportSize(ViewSize);
	}
	const FVector2D Dir = Sheet->FlowDirection.IsNearlyZero()
		? FVector2D(FMath::Cos(FMath::DegreesToRadians(Sheet->GetActorRotation().Yaw)), FMath::Sin(FMath::DegreesToRadians(Sheet->GetActorRotation().Yaw)))
		: Sheet->FlowDirection.GetSafeNormal();
	const FVector2D Across(-Dir.Y, Dir.X);
	const FVector2D Centre(Sheet->GetActorLocation().X, Sheet->GetActorLocation().Y);
	const float HalfFlow = Sheet->FlowHalfSpanCm();
	const float HalfCross = Sheet->CrossHalfSpanCm();
	const float Level = Sheet->GetLevelCm();
	constexpr float EdgeStepCm = 50.f;
	constexpr float EdgeOffsetCm = 100.f;
	constexpr float Border = 4.f;
	int32 Kept = 0, Dry = 0, Off = 0;
	for (int32 End = -1; End <= 1; End += 2)
	{
		for (float Cm = -HalfCross; Cm <= HalfCross + 1.f; Cm += EdgeStepCm)
		{
			const FVector2D Edge = Centre + Dir * (End * HalfFlow) + Across * Cm;
			const FVector2D WetXY = Edge - Dir * (End * EdgeOffsetCm);
			const FVector2D DryXY = Edge + Dir * (End * EdgeOffsetCm);
			const float WetBed = Ground(WetXY.X, WetXY.Y);
			const float DryBed = Ground(DryXY.X, DryXY.Y);
			if (WetBed > Level - 5.f || DryBed > Level - 5.f)
			{
				++Dry;
				continue;
			}
			FVector2D WS, DS;
			auto OnScreen = [&ViewSize, Border](const FVector2D& S)
			{
				return S.X >= Border && S.Y >= Border && S.X <= ViewSize.X - 1.f - Border && S.Y <= ViewSize.Y - 1.f - Border;
			};
			if (!Project(FVector(WetXY.X, WetXY.Y, Level), WS) || !Project(FVector(DryXY.X, DryXY.Y, Level), DS) || !OnScreen(WS) || !OnScreen(DS))
			{
				++Off;
				continue;
			}
			const float WetDepth = Water->Sample(FVector(WetXY.X, WetXY.Y, WetBed)).DepthCm;
			const float DryDepth = Water->Sample(FVector(DryXY.X, DryXY.Y, DryBed)).DepthCm;
			Log(FString::Printf(TEXT("edge %s %s %.1f wet %.1f %.1f dry %.1f %.1f | bed wet %.0f dry %.0f cm under a level of %.0f, the depth the car reads wet %.1f dry %.1f cm"),
				*Picture, End < 0 ? TEXT("upstream") : TEXT("downstream"), Cm * 0.01f, WS.X, WS.Y, DS.X, DS.Y, WetBed, DryBed, Level, WetDepth, DryDepth));
			++Kept;
		}
	}
	Log(FString::Printf(TEXT("basin edges %s: the placed box's flow-wise ends at +-%.1f m along (%.2f, %.2f) from (%.0f, %.0f), %.1f m across, a pair every %.1f m, %.1f m either side of the old edge: %d pairs kept, %d with a bed over the level, %d off screen"),
		*Picture, HalfFlow * 0.01f, Dir.X, Dir.Y, Centre.X, Centre.Y, 2.f * HalfCross * 0.01f, EdgeStepCm * 0.01f, EdgeOffsetCm * 0.01f, Kept, Dry, Off));
}

void FGTProvingShotsRunner::TickBasin(float DeltaSeconds)
{
	AGTCarPawn* TheCar = Car.Get();
	switch (SubStep)
	{
	case 0:
	{
		const FGTTerrainStation* Station = Spec.Stations.FindByPredicate([](const FGTTerrainStation& S) { return S.Name == FName(TEXT("forda")); });
		const FGTRouteSection* Ford = Spec.Sections.FindByPredicate([](const FGTRouteSection& S) { return S.Kind == EGTRouteSectionKind::Ford; });
		if (!Station || !Ford)
		{
			Notes.Add(TEXT("basin: no forda station or no Ford section"));
			Next();
			return;
		}
		// The car out of the picture: on the pad, behind the camera, on the handbrake.
		float PadYaw = 0.f;
		const FVector2D Pad = GTTerrain::PointOnPolyline(Spec.RouteM, 0.f, PadYaw) * 100.f;
		TheCar->SetActorLocationAndRotation(FVector(Pad.X, Pad.Y, Ground(Pad.X, Pad.Y) + 60.f), FRotator(0.f, PadYaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		TheCar->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
		TheCar->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
		TheCar->ResetDrivingInputs();
		if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
		{
			Move->SetThrottleInput(0.f);
			Move->SetHandbrakeInput(true);
		}
		// The camera: the station's point and heading, a standing eye over the ground, pitched at the ford's middle on the water.
		float MidYaw = 0.f;
		const FVector2D Mid = GTTerrain::PointOnPolyline(Spec.RouteM, 0.5f * (Ford->StartM + Ford->EndM), MidYaw) * 100.f;
		const UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>();
		const AGTWaterSheet* Sheet = Water ? Water->SheetAt(Mid) : nullptr;
		const float Level = Sheet ? Sheet->GetLevelCm() : Ground(Mid.X, Mid.Y);
		const FVector2D At = Station->PointM * 100.f;
		BasinEye = FVector(At.X, At.Y, Ground(At.X, At.Y) + BasinEyeCm);
		FRotator Look = (FVector(Mid.X, Mid.Y, Level) - BasinEye).Rotation();
		Look.Yaw = Station->YawDegrees;
		ShowFromCamera(BasinEye, Look);
		// The water's own cost from here to the picture is the picture's window.
		for (TActorIterator<AGTWaterSheet> It(World.Get()); It; ++It)
		{
			It->TakeStepStatsLine(TEXT("before the picture"));
		}
		Log(FString::Printf(TEXT("basin: the forda station at (%.0f, %.0f) m heading %.1f; eye (%.0f, %.0f, %.0f), %.0f cm over the ground, yaw %.1f pitch %.1f, at forda's middle (%.0f, %.0f) on the water at %.0f cm; the car on the pad at (%.0f, %.0f)"),
			Station->PointM.X, Station->PointM.Y, Station->YawDegrees, BasinEye.X, BasinEye.Y, BasinEye.Z, BasinEyeCm, Look.Yaw, Look.Pitch, Mid.X, Mid.Y, Level, Pad.X, Pad.Y));
		Enter(1);
		break;
	}
	case 1:
		if (SubTime < 4.f)   // the view taken, auto exposure settled
		{
			break;
		}
		LogBasinEdges(TEXT("proving_04_forda_basin"));
		for (TActorIterator<AGTWaterSheet> It(World.Get()); It; ++It)
		{
			Log(It->TakeStepStatsLine(TEXT("the picture's window")));
		}
		RequestShot(TEXT("proving_04_forda_basin"));
		Enter(2);
		break;
	default:
		if (SubTime >= 1.5f)
		{
			Next();
		}
		break;
	}
}

FVector2D FGTProvingShotsRunner::RouteXY(float ArcM, FVector2D& OutLeft) const
{
	float Yaw = 0.f;
	const FVector2D P = GTTerrain::PointOnPolyline(Spec.RouteM, ArcM, Yaw);
	const float Rad = FMath::DegreesToRadians(Yaw);
	OutLeft = FVector2D(-FMath::Sin(Rad), FMath::Cos(Rad));
	return P * 100.f;
}

void FGTProvingShotsRunner::LogScreenBox(const FString& Name, const TArray<FVector>& Points) const
{
	// hide_17's borderbox line (Art/tools/sample_border.ps1 reads "step N: borderbox <name> x0 y0 x1 y1 corners on screen k").
	float MinX = 1.e9f, MinY = 1.e9f, MaxX = -1.e9f, MaxY = -1.e9f;
	int32 OnScreen = 0;
	for (const FVector& P : Points)
	{
		FVector2D S;
		if (Project(P, S))
		{
			++OnScreen;
			MinX = FMath::Min(MinX, static_cast<float>(S.X));
			MinY = FMath::Min(MinY, static_cast<float>(S.Y));
			MaxX = FMath::Max(MaxX, static_cast<float>(S.X));
			MaxY = FMath::Max(MaxY, static_cast<float>(S.Y));
		}
	}
	Log(FString::Printf(TEXT("borderbox %s %.0f %.0f %.0f %.0f corners on screen %d"), *Name, MinX, MinY, MaxX, MaxY, OnScreen));
}

void FGTProvingShotsRunner::LogRutField(const TCHAR* When) const
{
	// The field's own numbers under forda's water (the diag's GTFORDRUT, here with the left wheels' recorded path).
	const UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	const UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>();
	FVector2D Left;
	const FVector2D Mid = RouteXY(FordMidArc, Left);
	const AGTMudPatch* Patch = Mud ? Mud->PatchAt(Mid) : nullptr;
	if (!Patch || !Water)
	{
		Log(FString::Printf(TEXT("rutfield %s: no %s at forda's middle"), When, Patch ? TEXT("water subsystem") : TEXT("mud patch")));
		return;
	}
	const FGTMudField& Field = Patch->GetField();
	int32 Touched = 0, Wet = 0, Rutted = 0;
	double RutSum = 0.0;
	float Deepest = 0.f;
	for (int32 Index = 0; Index < Field.Tracks.Num(); ++Index)
	{
		if (Field.Tracks[Index] == 0)
		{
			continue;
		}
		++Touched;
		const FVector2D C = Field.CellCentreCm(Index);
		const FGTWaterSample W = Water->Sample(FVector(C.X, C.Y, Ground(C.X, C.Y)));
		if (W.Kind != EGTWaterKind::Ford || W.DepthCm <= WetCm)
		{
			continue;
		}
		++Wet;
		const float H = Field.CellHeightCm(Index);
		Deepest = FMath::Min(Deepest, H);
		if (H < -1.f)
		{
			++Rutted;
			RutSum += H;
		}
	}
	int32 PathWet = 0;
	double FieldSum = 0.0, DepthSum = 0.0;
	for (const FVector2D& P : LeftPath)
	{
		const FGTWaterSample W = Water->Sample(FVector(P.X, P.Y, Ground(P.X, P.Y)));
		if (W.Kind != EGTWaterKind::Ford || W.DepthCm <= WetCm)
		{
			continue;
		}
		++PathWet;
		FieldSum += Field.HeightAt(P);
		DepthSum += W.DepthCm;
	}
	Log(FString::Printf(TEXT("rutfield %s: patch over section %d (profile %d: MaxSinkage %.1f cm, SinkageRate %.3f m/s), hole slot %d, water grid %d vertices (%d quads under a sheet); touched cells %d, %d under the water, %d cut past 1 cm (mean %.2f cm), deepest %.2f cm; the left wheels' path under the water: %d points, field mean %.2f cm, the depth the car reads there mean %.1f cm"),
		When, Patch->SectionIndex, Patch->bHasProfile ? 1 : 0, Patch->ProfileMaxSinkageM * 100.f, Patch->ProfileSinkageRate, Patch->HoleSlot, Patch->WaterVertexCount, Patch->WaterQuadsUnderSheet,
		Touched, Wet, Rutted, Rutted > 0 ? static_cast<float>(RutSum / Rutted) : 0.f, Deepest, PathWet, PathWet > 0 ? static_cast<float>(FieldSum / PathWet) : 0.f, PathWet > 0 ? static_cast<float>(DepthSum / PathWet) : 0.f));
}

void FGTProvingShotsRunner::TickRuts(float DeltaSeconds)
{
	AGTCarPawn* TheCar = Car.Get();
	const UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>();
	const UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	const FGTRouteSection* Ford = Spec.Sections.FindByPredicate([](const FGTRouteSection& S) { return S.Kind == EGTRouteSectionKind::Ford; });
	auto Park = [this, TheCar]()
	{
		float PadYaw = 0.f;
		const FVector2D Pad = GTTerrain::PointOnPolyline(Spec.RouteM, 0.f, PadYaw) * 100.f;
		TheCar->SetActorLocationAndRotation(FVector(Pad.X, Pad.Y, Ground(Pad.X, Pad.Y) + 60.f), FRotator(0.f, PadYaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		TheCar->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
		TheCar->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
		TheCar->ResetDrivingInputs();
		TheCar->SetRawSteer(0.f);
		if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
		{
			Move->SetThrottleInput(0.f);
			Move->SetHandbrakeInput(true);
		}
	};
	switch (SubStep)
	{
	case 0:
	{
		if (!Ford || !Water)
		{
			Notes.Add(TEXT("ruts: no Ford section or no water subsystem"));
			Next();
			return;
		}
		// forda's waterlines along the centre line (the sheet's surface over the ground).
		FordEntryArc = FordExitArc = -1.f;
		for (float A = Ford->StartM - 10.f; A <= Ford->EndM + 10.f; A += 0.25f)
		{
			FVector2D L;
			const FVector2D P = RouteXY(A, L);
			const FGTWaterSample W = Water->Sample(FVector(P.X, P.Y, Ground(P.X, P.Y)));
			if (W.Kind == EGTWaterKind::Ford && W.DepthCm > WetCm)
			{
				FordEntryArc = FordEntryArc < 0.f ? A : FordEntryArc;
				FordExitArc = A;
			}
		}
		if (FordEntryArc < 0.f)
		{
			Notes.Add(TEXT("ruts: no water along forda's centre line"));
			Next();
			return;
		}
		FordMidArc = 0.5f * (FordEntryArc + FordExitArc);
		Park();
		AGTWaterSheet::CalmAll(World.Get());
		FVector2D Left;
		const FVector2D Back = RouteXY(FordEntryArc - RutEyeBackM, Left);
		const FVector2D EyeXY = Back + Left * (RutEyeLeftM * 100.f);
		RutEye = FVector(EyeXY.X, EyeXY.Y, Ground(EyeXY.X, EyeXY.Y) + RutEyeUpCm);
		FVector2D AimLeft;
		const FVector2D Aim = RouteXY(FordEntryArc + RutAimM, AimLeft) + AimLeft * AssumedHalfTrackCm;
		RutLook = (FVector(Aim.X, Aim.Y, Ground(Aim.X, Aim.Y)) - RutEye).Rotation();
		ShowFromCamera(RutEye, RutLook);
		const FGTWaterSample AimWater = Water->Sample(FVector(Aim.X, Aim.Y, Ground(Aim.X, Aim.Y)));
		const FGTWaterSample EyeWater = Water->Sample(FVector(EyeXY.X, EyeXY.Y, Ground(EyeXY.X, EyeXY.Y)));
		Log(FString::Printf(TEXT("ruts: forda's waterlines along the centre line at arc %.2f and %.2f; eye (%.0f, %.0f, %.0f), %.0f cm over the ground (water there %.1f cm), yaw %.1f pitch %.1f, at the left wheel line %.2f m in (%.0f, %.0f), %.1f cm of water; the bed patch there %d"),
			FordEntryArc, FordExitArc, RutEye.X, RutEye.Y, RutEye.Z, RutEyeUpCm, EyeWater.DepthCm, RutLook.Yaw, RutLook.Pitch, RutAimM, Aim.X, Aim.Y, AimWater.DepthCm,
			(Mud && Mud->PatchAt(Aim)) ? 1 : 0));
		LeftPath.Reset();
		LogRutField(TEXT("before the crossing"));
		Enter(1);
		break;
	}
	case 1:
		if (SubTime >= 4.f)   // the view taken, auto exposure settled
		{
			RequestShot(TEXT("proving_05_forda_ruts_before"));
			Enter(2);
		}
		break;
	case 2:
		if (SubTime >= 1.5f)
		{
			// The car 15 m before the entry waterline, on the route, heading along it, on the handbrake to settle.
			FVector2D L;
			float Yaw = 0.f;
			const FVector2D Start = RouteXY(FordEntryArc - 15.f, L);
			GTTerrain::PointOnPolyline(Spec.RouteM, FordEntryArc - 15.f, Yaw);
			TheCar->SetActorLocationAndRotation(FVector(Start.X, Start.Y, Ground(Start.X, Start.Y) + 60.f), FRotator(0.f, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
			TheCar->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
			TheCar->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
			TheCar->ResetDrivingInputs();
			TheCar->SetRawSteer(0.f);
			if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
			{
				Move->SetThrottleInput(0.f);
				Move->SetHandbrakeInput(true);
			}
			if (UGTDrivetrainComponent* Train = TheCar->GetDrivetrain())
			{
				Train->SetLowRange(false);
				Train->SetDiffLock(false);
			}
			DriveTime = 0.f;
			Enter(3);
		}
		break;
	case 3:
		if (SubTime >= 3.f)
		{
			AGTWaterSheet::CalmAll(World.Get());
			Log(FString::Printf(TEXT("ruts: the crossing starts 15 m before the entry waterline, full throttle along the route, high range, diffs open")));
			Enter(4);
		}
		break;
	case 4:   // across forda at full throttle, the ford diag's steering; the left wheels' contacts recorded over the measured stretch
	{
		DriveTime += DeltaSeconds;
		const FVector Location = TheCar->GetActorLocation();
		const FGTRouteHit Hit = GTTerrain::RouteAtCm(Spec, Location.X, Location.Y);
		const float Speed = static_cast<float>(TheCar->GetVelocity().Size2D()) * 0.01f;
		FVector2D L;
		const FVector2D Target = RouteXY(Hit.ArcM + FMath::Clamp(Speed * 0.8f, 4.f, 25.f), L);
		const FVector ToTarget = (FVector(Target.X, Target.Y, Location.Z) - Location).GetSafeNormal2D();
		const FVector Forward = TheCar->GetActorForwardVector().GetSafeNormal2D();
		const float AngleDeg = FMath::RadiansToDegrees(FMath::Atan2(FVector::CrossProduct(Forward, ToTarget).Z, FVector::DotProduct(Forward, ToTarget)));
		TheCar->SetRawSteer(FMath::Clamp(AngleDeg / 20.f, -1.f, 1.f));
		if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
		{
			Move->SetThrottleInput(1.f);
			Move->SetBrakeInput(0.f);
			Move->SetHandbrakeInput(false);
		}
		if (const UGTTractionComponent* Traction = TheCar->GetTraction())
		{
			for (const FGTWheelTraction& W : Traction->Wheels)
			{
				if (!W.bInContact)
				{
					continue;
				}
				const FGTRouteHit WHit = GTTerrain::RouteAtCm(Spec, W.ContactPoint.X, W.ContactPoint.Y);
				const float In = WHit.ArcM - FordEntryArc;
				if (WHit.SignedM > 0.f && In >= RutFromM && In <= RutToM)
				{
					const FVector2D XY(W.ContactPoint.X, W.ContactPoint.Y);
					if (LeftPath.Num() == 0 || FVector2D::Distance(LeftPath.Last(), XY) >= 5.f)
					{
						LeftPath.Add(XY);
					}
				}
			}
		}
		if (Hit.ArcM >= FordExitArc + 10.f || DriveTime > 30.f)
		{
			Log(FString::Printf(TEXT("ruts: the crossing ended at arc %.2f after %.1f s (%s), %.2f m/s; %d left-wheel contacts recorded %.1f-%.1f m into the water"),
				Hit.ArcM, DriveTime, Hit.ArcM >= FordExitArc + 10.f ? TEXT("through") : TEXT("TIMED OUT"), Speed, LeftPath.Num(), RutFromM, RutToM));
			Park();
			AGTWaterSheet::CalmAll(World.Get());
			ShowFromCamera(RutEye, RutLook);
			Enter(5);
		}
		break;
	}
	case 5:
		if (SubTime >= 4.f)
		{
			// The same camera as the before picture. The left wheels' path at the mud's surface (the landscape plus the
			// field: the mesh rests on the ground), a pixel radius per point from 12 cm across it; the control 2.5 m
			// further left over untouched wet bed. Art/tools/sample_ford_ruts.ps1 reads these points.
			const AGTMudPatch* Patch = nullptr;
			if (Mud)
			{
				FVector2D ML;
				Patch = Mud->PatchAt(RouteXY(FordMidArc, ML));
			}
			int32 RutPts = 0, CtrlPts = 0, CtrlTouched = 0, CtrlDry = 0;
			for (const FVector2D& P : LeftPath)
			{
				const FGTRouteHit PHit = GTTerrain::RouteAtCm(Spec, P.X, P.Y);
				FVector2D L;
				RouteXY(PHit.ArcM, L);
				for (int32 Kind = 0; Kind < 2; ++Kind)
				{
					const FVector2D XY = Kind == 0 ? P : P + L * CtrlLeftCm;
					const float Field = Patch ? Patch->GetField().HeightAt(XY) : 0.f;
					const FVector At(XY.X, XY.Y, Ground(XY.X, XY.Y) + Field);
					const FVector Side = At + FVector(L.X, L.Y, 0.f) * RutHalfWidthCm;
					FVector2D S, S2;
					if (!Project(At, S) || !Project(Side, S2))
					{
						continue;
					}
					if (Kind == 1)
					{
						CtrlTouched += (Patch && Patch->GetField().TracksAt(XY) > 0.f) ? 1 : 0;
						CtrlDry += (Water && Water->Sample(FVector(XY.X, XY.Y, Ground(XY.X, XY.Y))).DepthCm <= 0.f) ? 1 : 0;
					}
					Log(FString::Printf(TEXT("rutpt %s %.1f %.1f %.1f field %.1f"), Kind == 0 ? TEXT("rut") : TEXT("ctrl"), S.X, S.Y, FMath::Max(1.0, FVector2D::Distance(S, S2)), Field));
					(Kind == 0 ? RutPts : CtrlPts) += 1;
				}
			}
			Log(FString::Printf(TEXT("ruts: %d rut points, %d control points (%d of them touched by a wheel, %d dry) for proving_05_forda_ruts_before and proving_06_forda_ruts_after"), RutPts, CtrlPts, CtrlTouched, CtrlDry));
			LogRutField(TEXT("after the crossing"));
			RequestShot(TEXT("proving_06_forda_ruts_after"));
			Enter(6);
		}
		break;
	case 6:
		if (SubTime >= 1.5f)
		{
			// The bed patch's box edge where the route comes in (hide_17's view: eye height 3 m outside the box, 3.92 m
			// back along the border, 19 degrees down at the border's middle on the road).
			const AGTMudPatch* Patch = nullptr;
			if (Mud)
			{
				FVector2D ML;
				Patch = Mud->PatchAt(RouteXY(FordMidArc, ML));
			}
			if (!Patch)
			{
				Notes.Add(TEXT("ruts: no bed patch at forda's middle, no box edge picture"));
				Enter(9);
				break;
			}
			FVector2D L;
			const FVector2D Entry = RouteXY(FordEntryArc, L);
			const FVector2D BorderMid(Patch->BoundsMin.X, FMath::Clamp(static_cast<float>(Entry.Y), Patch->BoundsMin.Y + 400.f, Patch->BoundsMax.Y - 400.f));
			const FVector2D Out(-1.f, 0.f);
			const FVector2D AlongB(-Out.Y, Out.X);
			const FVector2D Bearing = Out * 300.f - AlongB * 392.f;
			const FVector2D EyeXY = BorderMid + Bearing;
			const FVector Eye(EyeXY.X, EyeXY.Y, Ground(EyeXY.X, EyeXY.Y) + 170.f);
			const FVector LookAt(BorderMid.X, BorderMid.Y, Ground(BorderMid.X, BorderMid.Y));
			ShowFromCamera(Eye, (LookAt - Eye).Rotation());
			Log(FString::Printf(TEXT("edge: the bed patch's box x %.0f..%.0f y %.0f..%.0f, its -X side (the approach) at (%.0f %.0f), 6 m of it; eye (%.0f %.0f %.0f) pitch %.1f deg"),
				Patch->BoundsMin.X, Patch->BoundsMax.X, Patch->BoundsMin.Y, Patch->BoundsMax.Y, BorderMid.X, BorderMid.Y, Eye.X, Eye.Y, Eye.Z, -(LookAt - Eye).Rotation().Pitch));
			Enter(7);
		}
		break;
	case 7:
		if (SubTime >= 3.f)
		{
			const AGTMudPatch* Patch = nullptr;
			if (Mud)
			{
				FVector2D ML;
				Patch = Mud->PatchAt(RouteXY(FordMidArc, ML));
			}
			FVector2D L;
			const FVector2D Entry = RouteXY(FordEntryArc, L);
			const FVector2D BorderMid(Patch->BoundsMin.X, FMath::Clamp(static_cast<float>(Entry.Y), Patch->BoundsMin.Y + 400.f, Patch->BoundsMax.Y - 400.f));
			const FVector2D Out(-1.f, 0.f);
			const FVector2D AlongB(-Out.Y, Out.X);
			const FVector2D BorderA = BorderMid - AlongB * 300.f;
			const FVector2D BorderB = BorderMid + AlongB * 300.f;
			auto OnGround = [this](const FVector2D& XY) { return FVector(XY.X, XY.Y, Ground(XY.X, XY.Y)); };
			LogScreenBox(TEXT("proving_07_forda_box_edge"), { OnGround(BorderA - Out * 60.f), OnGround(BorderA + Out * 60.f), OnGround(BorderB - Out * 60.f), OnGround(BorderB + Out * 60.f) });
			for (int32 Side = 0; Side < 2; ++Side)
			{
				const FVector2D Centre = BorderMid + Out * (Side == 0 ? -150.f : 150.f);
				LogScreenBox(Side == 0 ? TEXT("mudstrip") : TEXT("landstrip"),
					{ OnGround(Centre - AlongB * 150.f - Out * 50.f), OnGround(Centre - AlongB * 150.f + Out * 50.f),
					  OnGround(Centre + AlongB * 150.f - Out * 50.f), OnGround(Centre + AlongB * 150.f + Out * 50.f) });
			}
			RequestShot(TEXT("proving_07_forda_box_edge"));
			Enter(8);
		}
		break;
	default:
		if (SubTime >= 1.5f)
		{
			Next();
		}
		break;
	}
}

int32 FGTProvingShotsRunner::CompileJobs() const
{
	int32 Jobs = 0;
#if WITH_EDITOR
	Jobs = (GShaderCompilingManager ? GShaderCompilingManager->GetNumRemainingJobs() : 0) + FAssetCompilingManager::Get().GetNumRemainingAssets();
#endif
	return Jobs;
}

bool FGTProvingShotsRunner::FindFlatDirtTop(FVector2D& OutCentre, float& OutYaw) const
{
	// Step 1's control spot: the first flat Dirt plane (a climb's top), the car along it.
	for (const FGTTerrainPlane& Plane : Spec.Planes)
	{
		if (Plane.Layer == 1 && FMath::IsNearlyZero(Plane.GradePercent) && FMath::IsNearlyZero(Plane.CrossSlopeDegrees) && Plane.LengthM >= 15.f && Plane.HalfWidthM >= 5.f)
		{
			const float Yaw = FMath::DegreesToRadians(Plane.YawDegrees);
			OutCentre = (Plane.StartM + FVector2D(FMath::Cos(Yaw), FMath::Sin(Yaw)) * (Plane.LengthM * 0.5f)) * 100.f;
			OutYaw = Plane.YawDegrees;
			Log(FString::Printf(TEXT("painted: the flat Dirt top at (%.0f, %.0f) yaw %.1f, %.0f x %.0f m"), OutCentre.X, OutCentre.Y, OutYaw, Plane.LengthM, Plane.HalfWidthM * 2.f));
			return true;
		}
	}
	return false;
}

void FGTProvingShotsRunner::SetPaintMaterials(bool bPainted)
{
	UMaterialInterface* Grey = LoadObject<UMaterialInterface>(nullptr, PaintGreyPath);
	FString Worn;
	for (int32 i = 0; i < PaintProps.Num(); ++i)
	{
		AStaticMeshActor* Prop = PaintProps[i].Get();
		if (!Prop)
		{
			continue;
		}
		UMaterialInterface* Mat = Grey;
		if (bPainted)
		{
			const FString Path = FString::Printf(TEXT("/Game/GrandTour/Materials/Painted/MI_GT_Painted_%s.MI_GT_Painted_%s"), *PaintNames[i], *PaintNames[i]);
			Mat = LoadObject<UMaterialInterface>(nullptr, *Path);
		}
		if (!Mat)
		{
			Notes.Add(FString::Printf(TEXT("painted: no %s material for %s"), bPainted ? TEXT("painted") : TEXT("grey"), *PaintNames[i]));
			continue;
		}
		UStaticMeshComponent* Comp = Prop->GetStaticMeshComponent();
		for (int32 Slot = 0; Slot < Comp->GetNumMaterials(); ++Slot)
		{
			Comp->SetMaterial(Slot, Mat);
		}
		Worn += FString::Printf(TEXT(" %s=%s"), *PaintNames[i], *Mat->GetName());
	}
	IStreamingManager::Get().StreamAllResources(5.f);
	Log(FString::Printf(TEXT("props wear:%s"), *Worn));
}

void FGTProvingShotsRunner::LogPaintBoxes(const FString& Picture) const
{
	// The middle of each prop's camera-facing side, 25-75 % along it and 30-60 % up it (the car copy's doors, the box's
	// face), from the mesh's own bounds so the box follows the asset.
	for (int32 i = 0; i < PaintProps.Num(); ++i)
	{
		const AStaticMeshActor* Prop = PaintProps[i].Get();
		const UStaticMesh* Mesh = Prop ? Prop->GetStaticMeshComponent()->GetStaticMesh() : nullptr;
		if (!Mesh)
		{
			continue;
		}
		const FBox B = Mesh->GetBoundingBox();
		const float FaceY = PaintSide > 0.f ? B.Max.Y : B.Min.Y;
		const FTransform T = Prop->GetActorTransform();
		TArray<FVector> Corners;
		for (const float U : { 0.25f, 0.75f })
		{
			for (const float V : { 0.30f, 0.60f })
			{
				Corners.Add(T.TransformPosition(FVector(FMath::Lerp(B.Min.X, B.Max.X, U), FaceY, FMath::Lerp(B.Min.Z, B.Max.Z, V))));
			}
		}
		LogScreenBox(Picture + TEXT("/") + PaintNames[i], Corners);
	}
	// The control: the parked car's side under the window line, the same 50 cm either side of its middle.
	if (const AGTCarPawn* TheCar = Car.Get())
	{
		const FVector Fwd = TheCar->GetMesh()->GetForwardVector().GetSafeNormal2D();
		const FVector Right = TheCar->GetMesh()->GetRightVector().GetSafeNormal2D();
		const FVector At = TheCar->GetActorLocation();
		const float Z = Ground(At.X, At.Y);
		TArray<FVector> Corners;
		for (const float U : { -50.f, 50.f })
		{
			for (const float V : { 60.f, 100.f })
			{
				FVector P = At + Fwd * U + Right * (PaintSide * 95.f);
				P.Z = Z + V;
				Corners.Add(P);
			}
		}
		LogScreenBox(Picture + TEXT("/control_car"), Corners);
	}
	// Look L1 follow-up 3 (VEHICLE_BUILD_SYSTEM 55): the car's own panels that carry the owner's bakes, the half nearer
	// the camera, 25-75 % along and 30-60 % up the panel's bounds on its camera-facing face (as the props above).
	// Follow-up 5: Bonnet and Roof too (one mesh each across the car; the same face rule).
	if (const AGTCarPawn* TheCar = Car.Get())
	{
		const FVector Eye = ShotCamera.IsValid() ? ShotCamera->GetActorLocation() : TheCar->GetActorLocation();
		TArray<UStaticMeshComponent*> Comps;
		TheCar->GetComponents<UStaticMeshComponent>(Comps);
		for (const TCHAR* Asset : { TEXT("FrontDoors"), TEXT("RearPanel"), TEXT("Bonnet"), TEXT("Roof") })
		{
			const FString Base = FString::Printf(TEXT("Panel_%s"), Asset);
			const UStaticMeshComponent* Best = nullptr;
			for (const UStaticMeshComponent* Comp : Comps)
			{
				const FString Name = Comp ? Comp->GetName() : FString();
				if (!Comp || !Comp->GetStaticMesh() || (Name != Base && Name != Base + TEXT("_L") && Name != Base + TEXT("_R")))
				{
					continue;
				}
				if (!Best || FVector::DistSquared(Comp->Bounds.Origin, Eye) < FVector::DistSquared(Best->Bounds.Origin, Eye))
				{
					Best = Comp;
				}
			}
			if (!Best)
			{
				Log(FString::Printf(TEXT("car panel %s: no %s component on the car"), Asset, *Base));
				continue;
			}
			const FBox B = Best->GetStaticMesh()->GetBoundingBox();
			const FTransform T = Best->GetComponentTransform();
			const FVector C = B.GetCenter();
			const bool bMaxFace = FVector::DistSquared(T.TransformPosition(FVector(C.X, B.Max.Y, C.Z)), Eye)
				< FVector::DistSquared(T.TransformPosition(FVector(C.X, B.Min.Y, C.Z)), Eye);
			const float FaceY = bMaxFace ? B.Max.Y : B.Min.Y;
			TArray<FVector> Corners;
			for (const float U : { 0.25f, 0.75f })
			{
				for (const float V : { 0.30f, 0.60f })
				{
					Corners.Add(T.TransformPosition(FVector(FMath::Lerp(B.Min.X, B.Max.X, U), FaceY, FMath::Lerp(B.Min.Z, B.Max.Z, V))));
				}
			}
			float UsePaint = -1.f;
			if (const UMaterialInterface* Mat = Best->GetMaterial(0))
			{
				Mat->GetScalarParameterValue(FMaterialParameterInfo(TEXT("UsePaint")), UsePaint);
			}
			Log(FString::Printf(TEXT("car panel %s: %s, mesh %.0f x %.0f x %.0f cm, %s face, material %s, UsePaint %.0f"), Asset,
				*Best->GetName(), B.GetSize().X, B.GetSize().Y, B.GetSize().Z, bMaxFace ? TEXT("+Y") : TEXT("-Y"),
				*GetNameSafe(Best->GetMaterial(0)), UsePaint));
			LogScreenBox(Picture + TEXT("/car_") + Asset, Corners);
		}
	}
}

void FGTProvingShotsRunner::TickPainted(float DeltaSeconds)
{
	AGTCarPawn* TheCar = Car.Get();
	switch (SubStep)
	{
	case 0:
	{
		FVector2D Centre;
		float Yaw = 0.f;
		if (!FindFlatDirtTop(Centre, Yaw))
		{
			Notes.Add(TEXT("painted: no flat Dirt plane"));
			Next();
			return;
		}
		const float Z = Ground(Centre.X, Centre.Y);
		TheCar->SetActorLocationAndRotation(FVector(Centre.X, Centre.Y, Z + 60.f), FRotator(0.f, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
		TheCar->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
		TheCar->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
		TheCar->ResetDrivingInputs();
		TheCar->SetRawSteer(0.f);
		if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
		{
			Move->SetThrottleInput(0.f);
			Move->SetBrakeInput(0.f);
			Move->SetHandbrakeInput(true);
		}
		const FVector Fwd = FRotator(0.f, Yaw, 0.f).Vector();
		struct FPlace { const TCHAR* Name; float AlongCm; };
		for (const FPlace& Place : { FPlace{ TEXT("TestBox"), PaintBoxAheadCm }, FPlace{ TEXT("TestCar"), -PaintCarBehindCm } })
		{
			const FString Path = FString::Printf(TEXT("/Game/GrandTour/Props/Painted/SM_%s.SM_%s"), Place.Name, Place.Name);
			UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
			if (!Mesh)
			{
				Notes.Add(FString::Printf(TEXT("painted: no %s (run bash Art/blender_test.sh, then Art/setup_look_l1.bat)"), *Path));
				continue;
			}
			const FVector2D XY = Centre + FVector2D(Fwd.X, Fwd.Y) * Place.AlongCm;
			const FVector Where(XY.X, XY.Y, Ground(XY.X, XY.Y));
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			AStaticMeshActor* Prop = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Where, FRotator(0.f, Yaw, 0.f), Params);
			if (!Prop)
			{
				Notes.Add(FString::Printf(TEXT("painted: could not spawn %s"), Place.Name));
				continue;
			}
			Prop->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
			Prop->GetStaticMeshComponent()->SetStaticMesh(Mesh);
			Prop->SetActorEnableCollision(false);
			PaintProps.Add(Prop);
			PaintNames.Add(Place.Name);
			const FBox B = Mesh->GetBoundingBox();
			Log(FString::Printf(TEXT("%s at (%.0f, %.0f, %.0f), %.0f cm along the car, mesh %.0f x %.0f x %.0f cm, %d material slot(s)"), Place.Name,
				Where.X, Where.Y, Where.Z, Place.AlongCm, B.GetSize().X, B.GetSize().Y, B.GetSize().Z, Prop->GetStaticMeshComponent()->GetNumMaterials()));
		}
		if (PaintProps.Num() == 0)
		{
			Next();
			return;
		}
		SetPaintMaterials(false);
		Enter(1);
		break;
	}
	case 1:   // the car settled on the handbrake, the grey material's shaders compiled
	{
		if (SubTime < 5.f || (CompileJobs() > 0 && SubTime < 120.f))
		{
			break;
		}
		const FVector Right = TheCar->GetMesh()->GetRightVector().GetSafeNormal2D();
		const FVector Fwd = TheCar->GetMesh()->GetForwardVector().GetSafeNormal2D();
		PaintSide = 1.f;
		for (TActorIterator<ADirectionalLight> It(World.Get()); It; ++It)
		{
			PaintSide = FVector::DotProduct(Right, -It->GetActorForwardVector().GetSafeNormal2D()) >= 0.f ? 1.f : -1.f;
			break;
		}
		const FVector At = TheCar->GetActorLocation() + Fwd * ((PaintBoxAheadCm - PaintCarBehindCm) * 0.5f);
		const FVector2D EyeXY = FVector2D(At.X, At.Y) + FVector2D(Right.X, Right.Y) * (PaintSide * PaintEyeBackCm);
		const FVector Eye(EyeXY.X, EyeXY.Y, FMath::Max(Ground(EyeXY.X, EyeXY.Y), Ground(At.X, At.Y)) + PaintEyeUpCm);
		const FVector LookAt(At.X, At.Y, Ground(At.X, At.Y) + 70.f);
		ShowFromCamera(Eye, (LookAt - Eye).Rotation());
		Log(FString::Printf(TEXT("camera on the %s (sunlit) side: eye (%.0f, %.0f, %.0f), looking at (%.0f, %.0f, %.0f); %d compile jobs left after %.0f s"),
			PaintSide > 0.f ? TEXT("right") : TEXT("left"), Eye.X, Eye.Y, Eye.Z, LookAt.X, LookAt.Y, LookAt.Z, CompileJobs(), SubTime));
		Enter(2);
		break;
	}
	case 2:
		if (SubTime >= 3.f)   // the view target taken, auto exposure settled
		{
			LogPaintBoxes(TEXT("proving_08_painted_before"));
			RequestShot(TEXT("proving_08_painted_before"));
			Enter(3);
		}
		break;
	case 3:
		if (SubTime >= 1.5f)
		{
			SetPaintMaterials(true);
			Enter(4);
		}
		break;
	case 4:   // the painted instances' shaders compiled and their textures streamed
		if (SubTime >= 4.f && (CompileJobs() == 0 || SubTime >= 120.f))
		{
			Log(FString::Printf(TEXT("painted: %d compile jobs left after %.0f s"), CompileJobs(), SubTime));
			LogPaintBoxes(TEXT("proving_09_painted_after"));
			RequestShot(TEXT("proving_09_painted_after"));
			Enter(5);
		}
		break;
	default:
		if (SubTime >= 1.5f)
		{
			Next();
		}
		break;
	}
}

bool FGTProvingShotsRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	if (bDone)
	{
		bOutPass = bPass;
		OutSummary = Summary;
		return true;
	}
	Elapsed += DeltaSeconds;
	StepTime += DeltaSeconds;
	SubTime += DeltaSeconds;
	auto Finish = [&](bool bInPass, const FString& Text)
	{
		bDone = true;
		bPass = bInPass;
		Summary = FString::Printf(TEXT("proving shots: %s%s"), *Text, Notes.Num() > 0 ? *(TEXT("; ") + FString::Join(Notes, TEXT("; "))) : TEXT(""));
		bOutPass = bPass;
		OutSummary = Summary;
		return true;
	};
	if (!World.IsValid())
	{
		return Finish(false, TEXT("no world"));
	}
	if (Elapsed > 600.f)
	{
		return Finish(false, FString::Printf(TEXT("timed out at step %d"), Step));
	}
	if (Step < 0)
	{
		if (Elapsed < 1.5f)
		{
			return false;
		}
		PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(World.Get(), 0));
		Car = PC.IsValid() ? (PC->GetCar() ? PC->GetCar() : Cast<AGTCarPawn>(PC->GetPawn())) : nullptr;
		const UGTTerrainSpecAsset* Asset = GTProving::FindSpecAsset(World.Get());
		if (!Car.IsValid() || !Asset)
		{
			return Elapsed > 15.f ? Finish(false, TEXT("no car or no spec asset")) : false;
		}
		Spec = Asset->Spec;
		if (!PC->IsDriving())
		{
			PC->EnterCar();
		}
		Log(FString::Printf(TEXT("the car found; from step %d, %d picture(s) expected"), FMath::Max(1, ShotsFrom), ExpectedShots));
		Step = 0;
		StepTime = 0.f;
		Enter(0);
		return false;
	}
	if (!Car.IsValid() || !PC.IsValid())
	{
		return Finish(false, TEXT("car or controller vanished"));
	}
	switch (Step)
	{
	case 0:   // shaders and the landscape compiled, the scene settled
	{
		int32 Jobs = 0;
#if WITH_EDITOR
		Jobs = (GShaderCompilingManager ? GShaderCompilingManager->GetNumRemainingJobs() : 0) + FAssetCompilingManager::Get().GetNumRemainingAssets();
#endif
		LogTimer -= DeltaSeconds;
		if (LogTimer <= 0.f)
		{
			LogTimer = 5.f;
			Log(FString::Printf(TEXT("waiting for %d compile jobs (%.0f s)"), Jobs, StepTime));
		}
		if ((Jobs == 0 && StepTime >= 5.f) || StepTime >= 240.f)
		{
			Log(FString::Printf(TEXT("settled after %.0f s with %d jobs left"), StepTime, Jobs));
			Step = FMath::Max(1, ShotsFrom) - 1;
			Next();
		}
		return false;
	}
	case 1:   // S2: the car on forda's channel bank
		TickBank(DeltaSeconds);
		return false;
	case 2:   // S3: forda's pond from its station (the owner's picture 2)
		TickBasin(DeltaSeconds);
		return false;
	case 3:   // S4: forda's ruts under the water, its bed patch's box edge
		TickRuts(DeltaSeconds);
		return false;
	case 4:   // LOOK L1: the painted props beside the parked car, grey then painted
		TickPainted(DeltaSeconds);
		return false;
	default:
		break;
	}
	if (StepTime < 3.f)
	{
		return false;
	}
	int32 Found = 0;
	FString Sizes;
	for (const FString& Path : ShotFiles)
	{
		const int64 Size = IFileManager::Get().FileSize(*Path);
		Found += Size > 0 ? 1 : 0;
		Sizes += FString::Printf(TEXT(" %s=%lld"), *FPaths::GetBaseFilename(Path), Size);
	}
	return Finish(Found == ExpectedShots && ShotFiles.Num() == ExpectedShots,
		FString::Printf(TEXT("screenshots: %d/%d written (%d expected, steps %d..%d):%s"), Found, ShotFiles.Num(), ExpectedShots, FMath::Max(1, ShotsFrom), LastStep, *Sizes));
}
