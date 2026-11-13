#include "Dressing/GTVegTestRunner.h"

#include "Dressing/GTVegetationProbeComponent.h"
#include "Dressing/GTVegetationSubsystem.h"
#include "Core/GTPlayerController.h"
#include "Terrain/GTProvingGround.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Vehicle/GTCarPawn.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "PhysicsEngine/BodySetup.h"
#include "RenderTimer.h"
#include "DynamicRHI.h"
#include "ShaderCompiler.h"

namespace GTVegTest
{
	constexpr float Kmh = 1.f / 3.6f;
	const FName SolidTag(TEXT("GTVeg.Solid"));
	const FName TestBiomeTag(TEXT("GTBiome.Test"));
	constexpr float TotalTimeoutS = 420.f;
	constexpr float TotalTimeoutGpuS = 1200.f;
	constexpr double WarmSpotMaxS = 150.0;   // real seconds per warm-up spot
	constexpr float SettleS = 2.5f;
	constexpr float HeldMs = 1.f;          // "held" / "a stop": under 1 m/s

	// The bands (docs/LEG_DRESSING_PLAN.md, the LD5 v2 pass list).
	constexpr float BrushBendDeg = 20.f;   // at least half the touched instances bend beyond 20 deg
	constexpr float BrushBentShare = 0.5f;
	constexpr float SettledDeg = 5.f;      // all back under 5 deg ...
	constexpr float SettleWithinS = 6.f;   // ... within 6 s
	constexpr float LossMin = 0.15f, LossMax = 0.60f;   // speed loss over the first 20 m
	constexpr float NeverHeldMs = 2.f / 3.6f;           // saplings at 8 km/h: the lowest speed stays at 2 km/h or above
	constexpr float YoungHeldWithinS = 3.f;
	constexpr float YoungSnapWithinS = 4.f;             // after full throttle
	constexpr float MatureStopWithinS = 1.f;
	constexpr float CleanupAfterS = 10.f;
	constexpr int32 MaxDebrisBand = 24;
	constexpr float GpuPushBandMs = 3.f, GpuViewBandMs = 2.f;   // tentative (reported only)

	FString Kph(float Ms)
	{
		return FString::Printf(TEXT("%.1f km/h"), Ms * 3.6f);
	}

	void SetDressing(int32 Value)
	{
		if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Look.Dressing")))
		{
			Var->Set(Value, ECVF_SetByCode);
		}
	}
}

FGTVegTestRunner::FGTVegTestRunner(UWorld* InWorld)
	: World(InWorld)
{
	bHide = FParse::Param(FCommandLine::Get(), TEXT("GTVegHide"));
	bScratch = bHide || FParse::Param(FCommandLine::Get(), TEXT("GTVegScratch"));
	bGpu = FApp::CanEverRender();
}

void FGTVegTestRunner::Log(const FString& Text) const
{
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST veg %s"), *Text);
}

void FGTVegTestRunner::Next(EStep InStep)
{
	Step = InStep;
	StepTime = 0.f;
	bStepStarted = false;
	bParked = false;
	ParkedTime = -1.0;
}

float FGTVegTestRunner::GroundZ(const FVector2D& At) const
{
	UWorld* W = World.Get();
	if (!W)
	{
		return 0.f;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTVegTestGround), false);
	if (Car.IsValid())
	{
		Params.AddIgnoredActor(Car.Get());
	}
	FHitResult Hit;
	if (W->LineTraceSingleByChannel(Hit, FVector(At, 50000.0), FVector(At, -50000.0), ECC_Visibility, Params))
	{
		return static_cast<float>(Hit.ImpactPoint.Z);
	}
	return -1.e9f;
}

float FGTVegTestRunner::SpeedMs() const
{
	return Car.IsValid() ? static_cast<float>(Car->GetMesh()->GetPhysicsLinearVelocity().Size2D() / 100.0) : 0.f;
}

float FGTVegTestRunner::AlongLine(const FLine& Line) const
{
	if (!Car.IsValid())
	{
		return 0.f;
	}
	const FVector At = Car->GetActorLocation();
	return static_cast<float>(FVector2D::DotProduct(FVector2D(At.X, At.Y) - Line.Origin, Line.Dir));
}

void FGTVegTestRunner::Teleport(const FVector2D& At, const FVector2D& Dir, float InSpeedMs)
{
	if (!Car.IsValid())
	{
		return;
	}
	const float Ground = GroundZ(At);
	const float Z = (Ground > -1.e8f ? Ground : 0.f) + RestOffsetCm + 5.f;
	const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X));
	Car->SetActorLocationAndRotation(FVector(At, Z), FRotator(0.f, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	Car->GetMesh()->SetPhysicsLinearVelocity(FVector(Dir * (InSpeedMs * 100.f), 0.0));
	Car->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
	Car->SetRawSteer(0.f);
	if (UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement())
	{
		Move->SetThrottleInput(0.f);
		Move->SetBrakeInput(0.f);
		Move->SetHandbrakeInput(InSpeedMs <= 0.f);
	}
}

void FGTVegTestRunner::Park()
{
	Teleport(ParkAt, FVector2D(1.0, 0.0), 0.f);
	bParked = true;
	ParkedTime = World.IsValid() ? World->GetTimeSeconds() : 0.0;
}

void FGTVegTestRunner::HoldSpeed(float TargetMs, const FLine& Line, float DeltaSeconds)
{
	UChaosWheeledVehicleMovementComponent* Move = Car.IsValid() ? Car->GetChaosMovement() : nullptr;
	if (!Move)
	{
		return;
	}
	// The hold: a PI on the throttle (full throttle at 1 m/s under the target), never the brake (the brake held at a stop
	// reverses); its throttle logged for the steady pedal. After the first contact: the locked pedal, or floored.
	const float Speed = SpeedMs();
	const float Error = TargetMs - Speed;
	HoldIntegral = FMath::Clamp(HoldIntegral + Error * 0.5f * DeltaSeconds, 0.f, 1.f);
	switch (Pedal)
	{
	case EPedal::Steady:
		LastThrottle = PedalLock;
		break;
	case EPedal::Full:
		LastThrottle = 1.f;
		break;
	default:
		LastThrottle = FMath::Clamp(Error * 1.f + HoldIntegral, 0.f, 1.f);
		ThrottleLog.Emplace(World->GetTimeSeconds(), LastThrottle);
		break;
	}
	Move->SetThrottleInput(LastThrottle);
	Move->SetBrakeInput(0.f);
	Move->SetHandbrakeInput(false);
	// The steering onto the line, aimed a little ahead (the terrain runners' Follow).
	const FVector Location = Car->GetActorLocation();
	const FVector2D At(Location.X, Location.Y);
	const float Along = static_cast<float>(FVector2D::DotProduct(At - Line.Origin, Line.Dir));
	const FVector2D Aim = Line.Origin + Line.Dir * (Along + FMath::Max(800.f, Speed * 120.f));
	const FVector ToAim = FVector(Aim - At, 0.0).GetSafeNormal();
	const FVector Forward = Car->GetActorForwardVector().GetSafeNormal2D();
	const float AngleDeg = FMath::RadiansToDegrees(FMath::Atan2(FVector::CrossProduct(Forward, ToAim).Z, FVector::DotProduct(Forward, ToAim)));
	Car->SetRawSteer(FMath::Clamp(AngleDeg / 20.f, -1.f, 1.f));
}

bool FGTVegTestRunner::FindLanes()
{
	using namespace GTVegTest;
	struct FRow
	{
		FBox2D Box = FBox2D(ForceInit);
		double SumY = 0.0;
		int32 Count = 0;
		float MaxRadius = 0.f;
	};
	FRow Rows[3];
	Veg->ForEachInstance([&Rows](const FVector& Pivot, EGTVegClass Class, float RadiusCm, float, bool)
	{
		FRow& Row = Rows[static_cast<int32>(Class)];
		Row.Box += FVector2D(Pivot.X, Pivot.Y);
		Row.SumY += Pivot.Y;
		++Row.Count;
		Row.MaxRadius = FMath::Max(Row.MaxRadius, RadiusCm);
	});
	for (int32 Index = 0; Index < 3; ++Index)
	{
		if (Rows[Index].Count == 0)
		{
			Failures.Add(FString::Printf(TEXT("no %s instances indexed on the map"), UGTVegetationSubsystem::ClassName(static_cast<EGTVegClass>(Index))));
		}
	}
	// The mature tree: the GTVeg.Solid ISM on the GTBiome.Test actor, its trunk capsule.
	bool bMature = false;
	for (TActorIterator<AActor> It(World.Get()); It && !bMature; ++It)
	{
		if (!It->Tags.Contains(TestBiomeTag))
		{
			continue;
		}
		TArray<UInstancedStaticMeshComponent*> Isms;
		It->GetComponents<UInstancedStaticMeshComponent>(Isms);
		for (const UInstancedStaticMeshComponent* Ism : Isms)
		{
			FTransform T;
			const UStaticMesh* Mesh = Ism->GetStaticMesh();
			const UBodySetup* Body = Mesh ? Mesh->GetBodySetup() : nullptr;
			if (!Ism->ComponentTags.Contains(SolidTag) || Ism->GetInstanceCount() < 1 || !Ism->GetInstanceTransform(0, T, true) || !Body || Body->AggGeom.SphylElems.Num() == 0)
			{
				continue;
			}
			const FKSphylElem& Capsule = Body->AggGeom.SphylElems[0];
			const FVector Axis = T.TransformPosition(Capsule.Center);
			TrunkAxis = FVector2D(Axis.X, Axis.Y);
			TrunkRadiusCm = Capsule.Radius * static_cast<float>(FMath::Max(FMath::Abs(T.GetScale3D().X), FMath::Abs(T.GetScale3D().Y)));
			Log(FString::Printf(TEXT("mature tree %s: trunk axis (%.0f, %.0f) cm, radius %.1f cm, collision %s"),
				*Mesh->GetName(), TrunkAxis.X, TrunkAxis.Y, TrunkRadiusCm, *Ism->GetCollisionProfileName().ToString()));
			bMature = true;
			break;
		}
	}
	if (!bMature)
	{
		Failures.Add(TEXT("no GTVeg.Solid ISM with a trunk capsule on a GTBiome.Test actor"));
	}
	if (Failures.Num() > 0)
	{
		return false;
	}
	auto MakeLane = [](const FRow& Row, FLine& OutLine, float& OutStart, float& OutEnd)
	{
		OutLine.Origin = FVector2D(0.0, Row.SumY / Row.Count);
		OutLine.Dir = FVector2D(1.0, 0.0);
		OutStart = static_cast<float>(Row.Box.Min.X) - Row.MaxRadius;
		OutEnd = static_cast<float>(Row.Box.Max.X) + Row.MaxRadius;
	};
	MakeLane(Rows[0], BrushLane, BrushStart, BrushEnd);
	MakeLane(Rows[1], SaplingLane, SaplingStart, SaplingEnd);
	MakeLane(Rows[2], YoungLane, YoungStart, YoungEnd);
	MatureLane.Origin = FVector2D(0.0, TrunkAxis.Y);
	MatureLane.Dir = FVector2D(1.0, 0.0);
	ParkAt = FVector2D(BrushStart - 5000.f, BrushLane.Origin.Y - 1500.f);
	Log(FString::Printf(TEXT("lanes (cm, along +X): brush %d at y %.0f from %.0f to %.0f; saplings %d at y %.0f from %.0f to %.0f; young %d at y %.0f from %.0f to %.0f; the mature trunk at x %.0f y %.0f; park at (%.0f, %.0f)"),
		Rows[0].Count, BrushLane.Origin.Y, BrushStart, BrushEnd, Rows[1].Count, SaplingLane.Origin.Y, SaplingStart, SaplingEnd,
		Rows[2].Count, YoungLane.Origin.Y, YoungStart, YoungEnd, TrunkAxis.X, TrunkAxis.Y, ParkAt.X, ParkAt.Y));
	return true;
}

void FGTVegTestRunner::WarmTeleport()
{
	const FLine* Lines[4] = { &BrushLane, &SaplingLane, &YoungLane, &MatureLane };
	const float Starts[4] = { BrushStart, SaplingStart, YoungStart, TrunkAxis.X - TrunkRadiusCm };
	const int32 Index = FMath::Clamp(WarmSpot, 0, 3);
	Teleport(Lines[Index]->Origin + Lines[Index]->Dir * (Starts[Index] - 1500.f), Lines[Index]->Dir, 0.f);
	WarmSpotStartReal = FPlatformTime::Seconds();
	FastFrames = 0;
}

void FGTVegTestRunner::SampleFrame()
{
	const float Ms = static_cast<float>(FApp::GetDeltaTime() * 1000.0);
	FrameMsSum += Ms;
	FrameMsMax = FMath::Max(FrameMsMax, Ms);
	GameMsSum += FPlatformTime::ToMilliseconds(GGameThreadTime);
	RenderMsSum += FPlatformTime::ToMilliseconds(GRenderThreadTime);
	GpuMsSum += FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0));
	++FrameCount;
}

FString FGTVegTestRunner::FrameLine() const
{
	const double N = FMath::Max(1, FrameCount);
	return FString::Printf(TEXT("frame %.2f ms mean, %.2f ms max over %d frames (game thread %.2f, render thread %.2f, GPU %.2f ms mean)"),
		FrameCount > 0 ? FrameMsSum / N : -1.0, FrameMsMax, FrameCount, GameMsSum / N, RenderMsSum / N, GpuMsSum / N);
}

void FGTVegTestRunner::BeginCase(const FLine& Line, float ObstacleAlongCm, float TargetMs, EPedal AtContact, float RunUpS)
{
	const UGTVegetationProbeComponent* Probe = Car->GetVegProbe();
	const float Front = (Probe && Probe->GetLocalBodyBox().IsValid) ? static_cast<float>(Probe->GetLocalBodyBox().Max.X) : 230.f;
	const float RunUp = FMath::Max(1500.f, TargetMs * 100.f * RunUpS);
	const float StartAlong = ObstacleAlongCm - Front - 30.f - RunUp;
	Lane = Line;
	TargetSpeedMs = TargetMs;
	HoldIntegral = 0.f;
	Teleport(Line.Origin + Line.Dir * StartAlong, Line.Dir, TargetMs);
	Veg->ResetStats(GTVegTest::BrushBendDeg, GTVegTest::SettledDeg);
	CaseStart = World->GetTimeSeconds();
	bContact = false;
	ContactTime = -1.0;
	EntrySpeedMs = 0.f;
	EntryAlongCm = 0.f;
	SpeedAt20Ms = -1.f;
	MinSpeedInContactMs = 1.e9f;
	HeldTime = -1.0;
	MinAxisDistanceCm = 1.e9f;
	bRecoveryChecked = false;
	TiltedAt6s = -1;
	FrameMsSum = 0.0;
	FrameMsMax = 0.f;
	FrameCount = 0;
	GameMsSum = RenderMsSum = GpuMsSum = 0.0;
	Pedal = EPedal::Hold;
	PedalAtContact = AtContact;
	PedalLock = -1.f;
	ThrottleLog.Reset();
	MinSpeedToEndMs = 1.e9f;
	bReachedEnd = false;
	ReachedEndTime = -1.0;
	FullThrottleTime = -1.0;
	SnapsBeforeFull = 0;
	FirstSnapAfterFull = -1.0;
	bStepStarted = true;
	bParked = false;
}

void FGTVegTestRunner::SampleSoft()
{
	const double Now = World->GetTimeSeconds();
	const float Speed = SpeedMs();
	const float Along = AlongLine(Lane);
	const FGTVegStats& Stats = Veg->GetStats();
	if (!bContact && Stats.FirstContactTime >= 0.0)
	{
		bContact = true;
		ContactTime = Now;
		EntrySpeedMs = Speed;
		EntryAlongCm = Along;
		// The steady pedal: the hold's mean over the 2 s before the first contact.
		if (PedalAtContact == EPedal::Steady)
		{
			double Sum = 0.0;
			int32 Count = 0;
			for (const TPair<double, float>& Sample : ThrottleLog)
			{
				if (Sample.Key >= Now - 2.0)
				{
					Sum += Sample.Value;
					++Count;
				}
			}
			PedalLock = Count > 0 ? static_cast<float>(Sum / Count) : LastThrottle;
		}
		Pedal = PedalAtContact;
		Log(FString::Printf(TEXT("first contact at %s: pedal %s%s"), *GTVegTest::Kph(Speed),
			PedalAtContact == EPedal::Steady ? TEXT("locked at ") : (PedalAtContact == EPedal::Full ? TEXT("floored") : TEXT("still the hold")),
			PedalAtContact == EPedal::Steady ? *FString::Printf(TEXT("%.3f (the hold's mean over the 2 s before)"), PedalLock) : TEXT("")));
	}
	if (!bContact)
	{
		return;
	}
	if (SpeedAt20Ms < 0.f && Along >= EntryAlongCm + 2000.f)
	{
		SpeedAt20Ms = Speed;
	}
	if (Car->GetVegProbe() && Car->GetVegProbe()->GetLastContacts() > 0)
	{
		MinSpeedInContactMs = FMath::Min(MinSpeedInContactMs, Speed);
	}
	if (HeldTime < 0.0 && Speed < GTVegTest::HeldMs)
	{
		HeldTime = Now;
	}
}

bool FGTVegTestRunner::CaseDone(float EndAlongCm, float SecondsAfterContact, float Timeout) const
{
	const double Now = World->GetTimeSeconds();
	return AlongLine(Lane) >= EndAlongCm || (bContact && Now - ContactTime >= SecondsAfterContact) || Now - CaseStart >= Timeout;
}

void FGTVegTestRunner::EndCase()
{
	LastContactAll = FMath::Max(LastContactAll, Veg->GetStats().LastContactTime);
	Park();
}

void FGTVegTestRunner::TickCase(float DeltaSeconds)
{
	using namespace GTVegTest;
	const double Now = World->GetTimeSeconds();
	const FGTVegStats& Stats = Veg->GetStats();
	const float WorkMean = Stats.TickFrames > 0 ? static_cast<float>(Stats.TickMsSum / Stats.TickFrames) : 0.f;
	const FString Work = FString::Printf(TEXT("work %.3f ms mean, %.3f max over %d frames"), WorkMean, Stats.TickMsMax, Stats.TickFrames);
	const FString Snaps = FString::Printf(TEXT("%d snaps (%d impact, %d sustained push)"), Stats.Snaps, Stats.SnapsImpact, Stats.SnapsSustained);
	const FString PedalText = PedalLock >= 0.f ? FString::Printf(TEXT("steady pedal %.3f"), PedalLock) : FString(TEXT("no steady pedal"));
	auto Judge = [this](bool bOk, const FString& Name, const FString& Numbers)
	{
		Log(FString::Printf(TEXT("%s: %s -> %s"), *Name, *Numbers, bOk ? TEXT("PASS") : TEXT("FAIL")));
		(bOk ? Results : Failures).Add(FString::Printf(TEXT("%s %s"), *Name, *Numbers));
	};
	// After the drive the car is parked well away; the step then waits for the bent instances to come back.
	auto WaitRecovered = [this, Now](float MaxS) { return Veg->GetActiveCount() == 0 || Now - ParkedTime >= MaxS; };

	switch (Step)
	{
	case EStep::Brush40:
	case EStep::Brush40Full:
	{
		const bool bFull = Step == EStep::Brush40Full;
		if (!bStepStarted)
		{
			Veg->Reindex();   // fresh plants: a snap lasts for the run, and an earlier case's snaps must not empty this one's row
			BeginCase(BrushLane, BrushStart, 40.f * Kmh, bFull ? EPedal::Full : EPedal::Steady);
			Log(FString::Printf(TEXT("case %s: the brush patch at 40 km/h, %s (%s)"), bFull ? TEXT("1b (information)") : TEXT("1"),
				bFull ? TEXT("full throttle from the first contact") : TEXT("steady pedal"), bGpu ? TEXT("gpu") : TEXT("null RHI")));
			return;
		}
		if (!bParked)
		{
			HoldSpeed(TargetSpeedMs, Lane, DeltaSeconds);
			SampleSoft();
			if (CaseDone(BrushEnd + 800.f, 12.f, 40.f))
			{
				EndCase();
			}
			return;
		}
		// All back under 5 deg within 6 s: the tilts counted 6 s after the last contact, and each instance timed.
		if (!bRecoveryChecked && Stats.LastContactTime >= 0.0 && Now >= Stats.LastContactTime + SettleWithinS)
		{
			bRecoveryChecked = true;
			TiltedAt6s = Veg->CountTiltedOver(SettledDeg);
		}
		if (!bRecoveryChecked || !(Veg->GetActiveCount() == 0 || Now >= Stats.LastContactTime + 12.0))
		{
			if (Now - ParkedTime < 20.0)
			{
				return;
			}
		}
		// The loss over the first 20 m after the first contact; a car that never got 20 m on lost all of it.
		const float Loss = EntrySpeedMs > 0.f ? 1.f - FMath::Max(SpeedAt20Ms, 0.f) / EntrySpeedMs : -1.f;
		const float Share = Stats.Contacted > 0 ? static_cast<float>(Stats.BentOver) / Stats.Contacted : 0.f;
		const bool bSettled = TiltedAt6s == 0 && Stats.MaxRecoverS <= SettleWithinS;
		const FString BentNumbers = FString::Printf(TEXT("%d of the %d touched (%.0f %%) beyond 20 deg in contact (band >= 50 %%); at most %d at once, tilt max %.1f deg"),
			Stats.BentOver, Stats.Contacted, Share * 100.f, Stats.MaxContacts, Stats.MaxTiltDeg);
		const FString SettleNumbers = FString::Printf(TEXT("the slowest back under 5 deg %.2f s after its last contact, %d still over 5 deg at 6 s (band <= 6 s, 0)"),
			Stats.MaxRecoverS, TiltedAt6s);
		const FString LossNumbers = FString::Printf(TEXT("%.0f %% over the first 20 m: %s at the first contact, %s 20 m on (-3.6: never got there) (band 15-60 %%); %s; resist max %.0f N; %s"),
			Loss * 100.f, *Kph(EntrySpeedMs), *Kph(SpeedAt20Ms), *PedalText, Stats.MaxForceN, *Work);
		if (!bFull)
		{
			Judge(Share >= BrushBentShare, TEXT("1 brush bent"), BentNumbers);
			Judge(bSettled, TEXT("1 brush settled"), SettleNumbers);
			Judge(Loss >= LossMin && Loss <= LossMax, TEXT("1 brush speed loss"), LossNumbers);
		}
		else
		{
			const FString Info = FString::Printf(TEXT("full throttle: %.0f %% lost over the first 20 m (%s -> %s); %s; %s; resist max %.0f N (information, no band)"),
				Loss * 100.f, *Kph(EntrySpeedMs), *Kph(SpeedAt20Ms), *BentNumbers, *SettleNumbers, Stats.MaxForceN);
			Log(TEXT("1b brush ") + Info);
			Results.Add(TEXT("1b brush ") + Info);
		}
		Next(bFull ? EStep::Sapling8 : EStep::Brush40Full);
		return;
	}
	case EStep::Sapling8:
	case EStep::Sapling30:
	{
		const bool bSlow = Step == EStep::Sapling8;
		if (!bStepStarted)
		{
			Veg->Reindex();   // fresh plants: a snap lasts for the run, and an earlier case's snaps must not empty this one's row
			BeginCase(SaplingLane, SaplingStart, (bSlow ? 8.f : 30.f) * Kmh, EPedal::Steady);
			Log(FString::Printf(TEXT("case 2: the sapling row at %s, steady pedal"), bSlow ? TEXT("8 km/h") : TEXT("30 km/h")));
			return;
		}
		if (!bParked)
		{
			HoldSpeed(TargetSpeedMs, Lane, DeltaSeconds);
			SampleSoft();
			const float Speed = SpeedMs();
			if (bContact && !bReachedEnd)
			{
				MinSpeedToEndMs = FMath::Min(MinSpeedToEndMs, Speed);
			}
			if (!bReachedEnd && AlongLine(Lane) >= SaplingEnd)
			{
				bReachedEnd = true;
				ReachedEndTime = Now;
			}
			if (CaseDone(SaplingEnd + (bSlow ? 800.f : 1000.f), bSlow ? 30.f : 10.f, bSlow ? 50.f : 30.f))
			{
				EndCase();
				if (bSlow)
				{
					const bool bOk = bReachedEnd && MinSpeedToEndMs >= NeverHeldMs;
					Judge(bOk, TEXT("2 saplings 8 km/h"), FString::Printf(TEXT("lowest %s from the first contact to the row's end (band >= 2 km/h); reached the end: %s, %.1f s after the first contact (band yes); from %s at the first contact; %s; %s; %d touched, resist max %.0f N; %s"),
						*Kph(MinSpeedToEndMs < 1.e8f ? MinSpeedToEndMs : 0.f), bReachedEnd ? TEXT("yes") : TEXT("no"),
						bReachedEnd ? static_cast<float>(ReachedEndTime - ContactTime) : -1.f, *Kph(EntrySpeedMs), *PedalText, *Snaps,
						Stats.Contacted, Stats.MaxForceN, *Work));
				}
				else
				{
					Judge(Stats.SnapsImpact >= 1, TEXT("2 saplings 30 km/h"), FString::Printf(TEXT("%d impact snap(s) (band >= 1); %s from %s at the first contact; %s; %d touched, resist max %.0f N; debris in use %d; %s"),
						Stats.SnapsImpact, *Snaps, *Kph(EntrySpeedMs), *PedalText, Stats.Contacted, Stats.MaxForceN, Veg->GetDebrisInUse(), *Work));
				}
			}
			return;
		}
		if (!WaitRecovered(10.f))
		{
			return;
		}
		Next(bSlow ? EStep::Sapling30 : EStep::Young10);
		return;
	}
	case EStep::Young10:
	{
		if (!bStepStarted)
		{
			Veg->Reindex();   // fresh plants: a snap lasts for the run, and an earlier case's snaps must not empty this one's row
			BeginCase(YoungLane, YoungStart, 10.f * Kmh, EPedal::Steady);
			Log(TEXT("case 3: the young-tree row at 10 km/h, steady pedal; held, then full throttle"));
			return;
		}
		if (!bParked)
		{
			HoldSpeed(TargetSpeedMs, Lane, DeltaSeconds);
			SampleSoft();
			// Held (or 3 s after the first contact without being held): full throttle.
			if (bContact && FullThrottleTime < 0.0 && (HeldTime >= 0.0 || Now - ContactTime >= YoungHeldWithinS))
			{
				FullThrottleTime = Now;
				SnapsBeforeFull = Stats.Snaps;
				Pedal = EPedal::Full;
				Log(FString::Printf(TEXT("3 young: full throttle %.2f s after the first contact (%s), %d snap(s) before it"),
					Now - ContactTime, HeldTime >= 0.0 ? TEXT("held") : TEXT("not held by 3 s"), SnapsBeforeFull));
			}
			if (FullThrottleTime >= 0.0 && FirstSnapAfterFull < 0.0 && Stats.Snaps > SnapsBeforeFull)
			{
				FirstSnapAfterFull = Now;
			}
			const bool bDone = (FirstSnapAfterFull >= 0.0 && Now - FirstSnapAfterFull >= 0.5)
				|| (FullThrottleTime >= 0.0 && Now - FullThrottleTime >= 8.0) || Now - CaseStart >= 45.0;
			if (bDone)
			{
				EndCase();
				const float HeldAfter = (bContact && HeldTime >= 0.0) ? static_cast<float>(HeldTime - ContactTime) : -1.f;
				const float SnapAfter = FirstSnapAfterFull >= 0.0 ? static_cast<float>(FirstSnapAfterFull - FullThrottleTime) : -1.f;
				Judge(HeldAfter >= 0.f && HeldAfter <= YoungHeldWithinS && SnapsBeforeFull == 0, TEXT("3 young 10 km/h held"),
					FString::Printf(TEXT("under 1 m/s %.2f s after the first contact (band <= 3 s; -1 never) from %s, %d snap(s) before full throttle (band 0); %s; resist max %.0f N"),
						HeldAfter, *Kph(EntrySpeedMs), SnapsBeforeFull, *PedalText, Stats.MaxForceN));
				Judge(SnapAfter >= 0.f && SnapAfter <= YoungSnapWithinS, TEXT("3 young full throttle"),
					FString::Printf(TEXT("the tree snapped %.2f s after full throttle (band <= 4 s; -1 never); %s; tilt max %.1f deg; %s"),
						SnapAfter, *Snaps, Stats.MaxTiltDeg, *Work));
			}
			return;
		}
		if (!WaitRecovered(10.f))
		{
			return;
		}
		Next(EStep::Young45);
		return;
	}
	case EStep::Young45:
	{
		if (!bStepStarted)
		{
			Veg->Reindex();   // fresh plants: a snap lasts for the run, and an earlier case's snaps must not empty this one's row
			BeginCase(YoungLane, YoungStart, 45.f * Kmh, EPedal::Steady);
			Log(TEXT("case 3: the young-tree row at 45 km/h, steady pedal"));
			return;
		}
		if (!bParked)
		{
			HoldSpeed(TargetSpeedMs, Lane, DeltaSeconds);
			SampleSoft();
			if (CaseDone(YoungEnd + 1000.f, 6.f, 30.f))
			{
				EndCase();
				Judge(Stats.SnapsImpact >= 1, TEXT("3 young 45 km/h"), FString::Printf(TEXT("%d impact snap(s) (band >= 1); %s from %s at the first contact; %s; %d touched, resist max %.0f N; debris in use %d; %s"),
					Stats.SnapsImpact, *Snaps, *Kph(EntrySpeedMs), *PedalText, Stats.Contacted, Stats.MaxForceN, Veg->GetDebrisInUse(), *Work));
			}
			return;
		}
		if (!WaitRecovered(10.f))
		{
			return;
		}
		Next(EStep::Mature20);
		return;
	}
	case EStep::Mature20:
	{
		if (!bStepStarted)
		{
			BeginCase(MatureLane, TrunkAxis.X - TrunkRadiusCm, 20.f * Kmh, EPedal::Hold);
			Log(TEXT("case 4: the mature tree at 20 km/h (the hold throughout)"));
			return;
		}
		HoldSpeed(TargetSpeedMs, Lane, DeltaSeconds);
		const float Speed = SpeedMs();
		const UGTVegetationProbeComponent* Probe = Car->GetVegProbe();
		const FBox Box = (Probe && Probe->GetLocalBodyBox().IsValid) ? Probe->GetLocalBodyBox() : FBox(FVector(-230.0, -93.0, 20.0), FVector(230.0, 93.0, 179.0));
		FTransform CarXf = Car->GetMesh()->GetComponentTransform();
		CarXf.SetScale3D(FVector::OneVector);
		const FVector Local = CarXf.InverseTransformPositionNoScale(FVector(TrunkAxis, Car->GetActorLocation().Z));
		const float Gap = static_cast<float>(Local.X - TrunkRadiusCm - Box.Max.X);
		const FVector Com = Car->GetMesh()->GetCenterOfMass();
		MinAxisDistanceCm = FMath::Min(MinAxisDistanceCm, static_cast<float>(FVector2D::Distance(FVector2D(Com.X, Com.Y), TrunkAxis)));
		if (!bContact && Gap <= 10.f && FMath::Abs(Local.Y) <= Box.GetExtent().Y + TrunkRadiusCm)
		{
			bContact = true;
			ContactTime = Now;
			EntrySpeedMs = Speed;
		}
		if (bContact && HeldTime < 0.0 && Speed < HeldMs)
		{
			HeldTime = Now;
		}
		if ((bContact && Now - ContactTime >= 3.0) || Now - CaseStart >= 25.0)
		{
			const float StopAfter = (bContact && HeldTime >= 0.0) ? static_cast<float>(HeldTime - ContactTime) : -1.f;
			const bool bOk = bContact && StopAfter >= 0.f && StopAfter <= MatureStopWithinS && MinAxisDistanceCm > TrunkRadiusCm;
			Judge(bOk, TEXT("4 mature 20 km/h"), FString::Printf(TEXT("under 1 m/s %.2f s after contact (band <= 1 s; -1 never) from %s; the centre of mass never nearer the trunk axis than %.0f cm (band > the trunk radius %.1f cm)"),
				StopAfter, *Kph(EntrySpeedMs), MinAxisDistanceCm, TrunkRadiusCm));
			EndCase();
			Next(EStep::Cleanup);
		}
		return;
	}
	case EStep::Cleanup:
	{
		if (!bStepStarted)
		{
			bStepStarted = true;
			Park();
			Log(FString::Printf(TEXT("case 5: clean-up, %.0f s after the last contact"), CleanupAfterS));
			return;
		}
		if (Now < LastContactAll + CleanupAfterS)
		{
			return;
		}
		const int32 Active = Veg->GetActiveCount();
		const int32 Actors = Veg->GetDebrisActorCount();
		Judge(Active == 0 && Actors <= MaxDebrisBand && Veg->GetDebrisInUse() <= MaxDebrisBand, TEXT("5 clean-up"),
			FString::Printf(TEXT("%.1f s after the last contact: active set %d (band 0), debris actors %d with %d in use (band <= %d)"),
				Now - LastContactAll, Active, Actors, Veg->GetDebrisInUse(), MaxDebrisBand));
		Next(bGpu ? EStep::GpuView : EStep::Done);
		return;
	}
	case EStep::GpuView:
	case EStep::GpuView0:
	{
		// Parked 5 m short of the patch, looking at it, nothing bending: the patch's own draw cost, dressing 1 then 0.
		const int32 Dressing = Step == EStep::GpuView ? 1 : 0;
		if (!bStepStarted)
		{
			SetDressing(Dressing);
			BeginCase(BrushLane, BrushStart, 0.f, EPedal::Hold);
			Teleport(BrushLane.Origin + BrushLane.Dir * (BrushStart - 500.f - 232.f), BrushLane.Dir, 0.f);
			return;
		}
		if (StepTime < 1.5f)
		{
			return;
		}
		SampleFrame();
		if (StepTime >= 4.5f)
		{
			ViewFrameMs[Dressing] = FrameCount > 0 ? static_cast<float>(FrameMsSum / FrameCount) : -1.f;
			ViewGpuMs[Dressing] = FrameCount > 0 ? static_cast<float>(GpuMsSum / FrameCount) : -1.f;
			Log(FString::Printf(TEXT("6 parked 5 m short of the patch, looking at it, gt.Look.Dressing %d, nothing bending: %s"), Dressing, *FrameLine()));
			Next(Dressing == 1 ? EStep::GpuOn : EStep::GpuOff);
		}
		return;
	}
	case EStep::GpuOn:
	case EStep::GpuOff:
	{
		const int32 Dressing = Step == EStep::GpuOn ? 1 : 0;
		if (!bStepStarted)
		{
			BeginCase(BrushLane, BrushStart, 30.f * Kmh, EPedal::Hold);
			Log(FString::Printf(TEXT("case 6 (gpu): the brush patch at 30 km/h (the hold), gt.Look.Dressing %d"), Dressing));
			return;
		}
		if (!bParked)
		{
			HoldSpeed(TargetSpeedMs, Lane, DeltaSeconds);
			const float Along = AlongLine(Lane);
			if (Along >= BrushStart - 230.f && Along <= BrushEnd + 230.f)
			{
				SampleFrame();
			}
			if (CaseDone(BrushEnd + 800.f, 1.e9f, 25.f))
			{
				PushFrameMs[Dressing] = FrameCount > 0 ? static_cast<float>(FrameMsSum / FrameCount) : -1.f;
				PushGpuMs[Dressing] = FrameCount > 0 ? static_cast<float>(GpuMsSum / FrameCount) : -1.f;
				Log(FString::Printf(TEXT("6 pushing through the patch at 30 km/h, gt.Look.Dressing %d: %s; vegetation %s"), Dressing, *FrameLine(), *Work));
				EndCase();
			}
			return;
		}
		if (Dressing == 1)
		{
			if (!WaitRecovered(10.f))
			{
				return;
			}
			Next(EStep::GpuView0);
			return;
		}
		SetDressing(1);
		// The tentative bands: reported, never a failure.
		const float PushDelta = PushGpuMs[1] - PushGpuMs[0];
		const float ViewDelta = ViewGpuMs[1] - ViewGpuMs[0];
		const FString Line = FString::Printf(TEXT("6 gpu (tentative bands, reported only): pushing through %.2f ms GPU with the dressing, %.2f without, +%.2f (band <= +%.1f: %s); parked and viewing %.2f with, %.2f without, +%.2f (band <= +%.1f: %s); frames %.2f / %.2f pushing, %.2f / %.2f parked"),
			PushGpuMs[1], PushGpuMs[0], PushDelta, GpuPushBandMs, PushDelta <= GpuPushBandMs ? TEXT("within") : TEXT("OVER"),
			ViewGpuMs[1], ViewGpuMs[0], ViewDelta, GpuViewBandMs, ViewDelta <= GpuViewBandMs ? TEXT("within") : TEXT("OVER"),
			PushFrameMs[1], PushFrameMs[0], ViewFrameMs[1], ViewFrameMs[0]);
		Log(Line);
		Results.Add(Line);
		Next(EStep::Done);
		return;
	}
	default:
		return;
	}
}

bool FGTVegTestRunner::PickScratchLine()
{
	// Soft pivots and solid instance positions (every GTVeg.Solid ISM), a 4 m count grid of the soft ones, the 40 densest
	// 3 x 3 blocks as centres, 8 headings each: the 100 m line through the centre with the most soft pivots within 2 m,
	// no solid within 3.5 m of it or its run-up, and ground every 10 m under both.
	TArray<FVector2D> Soft;
	Veg->ForEachInstance([&Soft](const FVector& Pivot, EGTVegClass, float, float, bool)
	{
		Soft.Add(FVector2D(Pivot.X, Pivot.Y));
	});
	TArray<FVector2D> Solid;
	for (TActorIterator<AActor> It(World.Get()); It; ++It)
	{
		TArray<UInstancedStaticMeshComponent*> Isms;
		It->GetComponents<UInstancedStaticMeshComponent>(Isms);
		for (const UInstancedStaticMeshComponent* Ism : Isms)
		{
			if (!Ism->ComponentTags.Contains(GTVegTest::SolidTag))
			{
				continue;
			}
			for (int32 Index = 0; Index < Ism->GetInstanceCount(); ++Index)
			{
				FTransform T;
				if (Ism->GetInstanceTransform(Index, T, true))
				{
					Solid.Add(FVector2D(T.GetLocation().X, T.GetLocation().Y));
				}
			}
		}
	}
	if (Soft.Num() == 0)
	{
		Failures.Add(TEXT("scratch: no soft instances indexed"));
		return false;
	}
	constexpr float Cell = 400.f;
	// The drive starts about 32 m before the stretch (the 3.5 s run-up at 30 km/h, the car's front, the pad): the solid
	// and ground checks reach 90 m back from the stretch's middle.
	constexpr float RunUpBackCm = 9000.f;
	TMap<FIntPoint, int32> Grid;
	for (const FVector2D& P : Soft)
	{
		++Grid.FindOrAdd(FIntPoint(FMath::FloorToInt32(P.X / Cell), FMath::FloorToInt32(P.Y / Cell)));
	}
	TArray<TPair<int32, FIntPoint>> Blocks;
	for (const TPair<FIntPoint, int32>& Entry : Grid)
	{
		int32 Sum = 0;
		for (int32 DX = -1; DX <= 1; ++DX)
		{
			for (int32 DY = -1; DY <= 1; ++DY)
			{
				const int32* N = Grid.Find(Entry.Key + FIntPoint(DX, DY));
				Sum += N ? *N : 0;
			}
		}
		Blocks.Emplace(Sum, Entry.Key);
	}
	Blocks.Sort([](const TPair<int32, FIntPoint>& A, const TPair<int32, FIntPoint>& B) { return A.Key > B.Key; });
	// LD7 (-GTVegHide): the dense blocks (at least half the densest one's count) in order of their distance to the route,
	// and the first with a clear line wins (its best heading), so the drive goes through the thicket nearest the road.
	const UGTTerrainSpecAsset* SpecAsset = bHide ? GTProving::FindSpecAsset(World.Get()) : nullptr;
	if (bHide && !SpecAsset)
	{
		SpecAsset = LoadObject<UGTTerrainSpecAsset>(nullptr, TEXT("/Game/GrandTour/Terrain/DA_Terrain_Hide.DA_Terrain_Hide"));
	}
	TArray<float> BlockRouteM;
	if (bHide && SpecAsset && Blocks.Num() > 0)
	{
		const int32 Densest = Blocks[0].Key;
		Blocks.RemoveAll([Densest](const TPair<int32, FIntPoint>& Block) { return Block.Key * 2 < Densest; });
		TArray<TPair<float, int32>> Order;
		for (int32 B = 0; B < Blocks.Num(); ++B)
		{
			const FVector2D Centre((Blocks[B].Value.X + 0.5f) * Cell, (Blocks[B].Value.Y + 0.5f) * Cell);
			Order.Emplace(GTTerrain::RouteAtCm(SpecAsset->Spec, static_cast<float>(Centre.X), static_cast<float>(Centre.Y)).DistanceM, B);
		}
		Order.Sort([](const TPair<float, int32>& A, const TPair<float, int32>& B) { return A.Key < B.Key; });
		TArray<TPair<int32, FIntPoint>> Sorted;
		for (const TPair<float, int32>& O : Order)
		{
			Sorted.Add(Blocks[O.Value]);
			BlockRouteM.Add(O.Key);
		}
		Blocks = MoveTemp(Sorted);
		Log(FString::Printf(TEXT("hide: %d dense blocks (3 x 3 cells of 4 m holding at least %d soft pivots, half the densest's %d), the nearest %.1f m from the route"),
			Blocks.Num(), (Densest + 1) / 2, Densest, BlockRouteM.Num() > 0 ? BlockRouteM[0] : -1.f));
	}
	int32 BestScore = -1;
	FLine Best;
	for (int32 B = 0; B < FMath::Min(40, Blocks.Num()); ++B)
	{
		if (bHide && BestScore > 0)
		{
			break;   // the nearest block with a clear line: done
		}
		if (bHide)
		{
			HideRouteDistM = BlockRouteM.IsValidIndex(B) ? BlockRouteM[B] : -1.f;
		}
		const FVector2D Centre((Blocks[B].Value.X + 0.5f) * Cell, (Blocks[B].Value.Y + 0.5f) * Cell);
		for (int32 H = 0; H < 8; ++H)
		{
			const float Rad = FMath::DegreesToRadians(22.5f * H);
			const FVector2D Dir(FMath::Cos(Rad), FMath::Sin(Rad));
			bool bBlocked = false;
			for (const FVector2D& P : Solid)
			{
				const FVector2D D = P - Centre;
				const double Along = FVector2D::DotProduct(D, Dir);
				const double Across = FMath::Abs(FVector2D::CrossProduct(Dir, D));
				if (Along >= -RunUpBackCm && Along <= 5500.0 && Across <= 350.0)
				{
					bBlocked = true;
					break;
				}
			}
			if (bBlocked)
			{
				continue;
			}
			int32 Score = 0;
			for (const FVector2D& P : Soft)
			{
				const FVector2D D = P - Centre;
				const double Along = FVector2D::DotProduct(D, Dir);
				Score += (Along >= -5000.0 && Along <= 5000.0 && FMath::Abs(FVector2D::CrossProduct(Dir, D)) <= 200.0) ? 1 : 0;
			}
			if (Score <= BestScore)
			{
				continue;
			}
			// Ground under the whole drive, the car's run-up included (every 10 m from its start to 2 m past the stretch).
			bool bGround = true;
			for (float At = -RunUpBackCm; At <= 5200.f && bGround; At += 1000.f)
			{
				bGround = GroundZ(Centre + Dir * At) > -1.e8f;
			}
			if (!bGround || GroundZ(Centre + Dir * 5200.f) < -1.e8f)
			{
				continue;
			}
			BestScore = Score;
			Best.Origin = Centre - Dir * 5000.f;   // the line's 0 is the 100 m stretch's start
			Best.Dir = Dir;
		}
	}
	if (BestScore < 0)
	{
		Failures.Add(FString::Printf(TEXT("scratch: no 100 m line clear of %d solid instances"), Solid.Num()));
		return false;
	}
	ScratchLine = Best;
	ScratchScore = BestScore;
	ScratchStartAlong = 0.f;
	if (bHide)
	{
		Log(FString::Printf(TEXT("hide: the chosen block's centre is %.1f m from the route"), HideRouteDistM));
	}
	Log(FString::Printf(TEXT("scratch line: from (%.0f, %.0f) m heading %.1f deg, %d soft pivots within 2 m of the 100 m, no solid within 3.5 m (%d solid, %d soft instances on the map)"),
		Best.Origin.X / 100.f, Best.Origin.Y / 100.f, FMath::RadiansToDegrees(FMath::Atan2(Best.Dir.Y, Best.Dir.X)), BestScore, Solid.Num(), Soft.Num()));
	return true;
}

void FGTVegTestRunner::Finish(bool& bOutPass, FString& OutSummary)
{
	bOutPass = Failures.Num() == 0;
	OutSummary = bOutPass ? FString::Join(Results, TEXT("; ")) : FString::Join(Failures, TEXT("; "));
	Step = EStep::Done;
}

bool FGTVegTestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	using namespace GTVegTest;
	Elapsed += DeltaSeconds;
	StepTime += DeltaSeconds;
	++Ticks;
	UWorld* W = World.Get();
	if (!W)
	{
		bOutPass = false;
		OutSummary = TEXT("no world");
		return true;
	}
	if (Elapsed > (bGpu ? TotalTimeoutGpuS : TotalTimeoutS))
	{
		Failures.Add(FString::Printf(TEXT("timed out at step %d"), static_cast<int32>(Step)));
		Finish(bOutPass, OutSummary);
		return true;
	}
	if (Step != EStep::Wait && (!Car.IsValid() || !Veg.IsValid()))
	{
		Failures.Add(TEXT("lost the car or the vegetation subsystem"));
		Finish(bOutPass, OutSummary);
		return true;
	}

	switch (Step)
	{
	case EStep::Wait:
	{
		if (Elapsed < 1.5f || Ticks < 10)
		{
			return false;
		}
		Car = Cast<AGTCarPawn>(UGameplayStatics::GetPlayerPawn(W, 0));
		if (!Car.IsValid())
		{
			// A leg map (L_Leg03, -GTVegHide) may possess the character: the controller's car then.
			if (AGTPlayerController* GTPC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(W, 0)))
			{
				Car = GTPC->GetCar();
			}
		}
		Veg = W->GetSubsystem<UGTVegetationSubsystem>();
		if (!Car.IsValid() || !Veg.IsValid())
		{
			Failures.Add(!Car.IsValid() ? TEXT("no GTCarPawn possessed by player 0") : TEXT("no UGTVegetationSubsystem"));
			Finish(bOutPass, OutSummary);
			return true;
		}
		if (APlayerController* PC = Cast<APlayerController>(Car->GetController()))
		{
			Car->DisableInput(PC);   // a pad left plugged in must not drive a headless test
		}
		Log(Veg->DescribeIndex());
		int32 Ism[3];
		int32 Hism[3];
		Veg->CountComponents(Ism, Hism);
		Log(FString::Printf(TEXT("soft components by class (Brush / Sapling / Young): plain ISM %d / %d / %d, HISM %d / %d / %d; hash cells %d; indexed Brush %d, Sapling %d, Young %d"),
			Ism[0], Ism[1], Ism[2], Hism[0], Hism[1], Hism[2], Veg->GetCellCount(), Veg->GetIndexedCount(EGTVegClass::Brush),
			Veg->GetIndexedCount(EGTVegClass::Sapling), Veg->GetIndexedCount(EGTVegClass::Young)));
		if (bScratch)
		{
			if (!PickScratchLine())
			{
				Finish(bOutPass, OutSummary);
				return true;
			}
			ParkAt = ScratchLine.Origin - ScratchLine.Dir * 2000.f;
			Next(EStep::ScratchSettle);
		}
		else
		{
			if (!FindLanes())
			{
				Finish(bOutPass, OutSummary);
				return true;
			}
			Next(bGpu ? EStep::Warmup : EStep::Settle);
		}
		return false;
	}
	case EStep::Settle:
	case EStep::ScratchSettle:
	{
		// The car at rest on the ground, for the height every teleport puts it at.
		if (!bStepStarted)
		{
			bStepStarted = true;
			RestOffsetCm = 150.f;
			Teleport(ParkAt, Step == EStep::ScratchSettle ? ScratchLine.Dir : FVector2D(1.0, 0.0), 0.f);
			return false;
		}
		if (StepTime < GTVegTest::SettleS)
		{
			return false;
		}
		if (bHide && bGpu && !bHideWarm)
		{
			// LD7: shaders first (the first frames on a dressed leg compile at a few fps).
			const float FrameMs = static_cast<float>(FApp::GetDeltaTime() * 1000.0);
			FastFrames = FrameMs < 50.f ? FastFrames + 1 : 0;
			const int32 Jobs = GShaderCompilingManager ? GShaderCompilingManager->GetNumRemainingJobs() : 0;
			if (!((StepTime >= 3.f && Jobs == 0 && FastFrames >= 30) || StepTime >= GTVegTest::WarmSpotMaxS))
			{
				return false;
			}
			bHideWarm = true;
			Log(FString::Printf(TEXT("hide: gpu warm-up at the line's start %.1f s, %d shader job(s) left, last frame %.1f ms"), StepTime, Jobs, FrameMs));
		}
		const FVector At = Car->GetActorLocation();
		const float Ground = GroundZ(FVector2D(At.X, At.Y));
		RestOffsetCm = FMath::Clamp(static_cast<float>(At.Z) - Ground, 0.f, 200.f);
		Log(FString::Printf(TEXT("the car rests %.1f cm above the ground (its origin); body box %s; %s"), RestOffsetCm,
			Car->GetVegProbe() && Car->GetVegProbe()->GetLocalBodyBox().IsValid ? *Car->GetVegProbe()->GetLocalBodyBox().ToString() : TEXT("not measured yet"),
			bGpu ? TEXT("gpu") : TEXT("null RHI")));
		Next(Step == EStep::ScratchSettle ? EStep::ScratchDrive : EStep::Brush40);
		return false;
	}
	case EStep::Warmup:
	{
		// GPU runs only: 15 m before each lane, looking down it, until no shader job is left and 30 frames in a row take
		// under 50 ms (at least 3 s, at most 150 s of real time per lane).
		if (!bStepStarted)
		{
			bStepStarted = true;
			WarmSpot = 0;
			RestOffsetCm = 150.f;   // not measured yet: the settle comes after the warm-up
			WarmTeleport();
			return false;
		}
		const float FrameMs = static_cast<float>(FApp::GetDeltaTime() * 1000.0);
		FastFrames = FrameMs < 50.f ? FastFrames + 1 : 0;
		const int32 Jobs = GShaderCompilingManager ? GShaderCompilingManager->GetNumRemainingJobs() : 0;
		const double SpotAge = FPlatformTime::Seconds() - WarmSpotStartReal;
		if ((SpotAge >= 3.0 && Jobs == 0 && FastFrames >= 30) || SpotAge >= WarmSpotMaxS)
		{
			Log(FString::Printf(TEXT("gpu warm-up at lane %d: %.1f s real, %d shader job(s) left, last frame %.1f ms%s"),
				WarmSpot, SpotAge, Jobs, FrameMs, SpotAge >= WarmSpotMaxS ? TEXT(" (gave up waiting)") : TEXT("")));
			++WarmSpot;
			if (WarmSpot >= 4)
			{
				Next(EStep::Settle);
				return false;
			}
			WarmTeleport();
		}
		return false;
	}
	case EStep::ScratchDrive:
	{
		const double Now = W->GetTimeSeconds();
		if (!bStepStarted)
		{
			BeginCase(ScratchLine, 0.f, 30.f * Kmh, EPedal::Hold, 3.5f);
			ScratchMinSpeed = 1.e9f;
			ScratchLastPos = Car->GetActorLocation();
			ScratchPathCm = 0.f;
			Log(TEXT("scratch: 100 m at 30 km/h along the line"));
			return false;
		}
		HoldSpeed(TargetSpeedMs, Lane, DeltaSeconds);
		const float Along = AlongLine(Lane);
		if (Along >= 0.f)
		{
			ScratchMinSpeed = FMath::Min(ScratchMinSpeed, SpeedMs());
			if (Along <= 10000.f)
			{
				SampleFrame();
			}
		}
		const FVector Here = Car->GetActorLocation();
		ScratchPathCm += static_cast<float>(FVector::Dist2D(Here, ScratchLastPos));
		ScratchLastPos = Here;
		if (Along >= 10000.f || Now - CaseStart >= 40.0)
		{
			const FGTVegStats& Stats = Veg->GetStats();
			float Mean = 0.f;
			float Max = 0.f;
			int32 Frames = 0;
			Veg->GetRollingTickMs(Mean, Max, Frames);
			const FString Line = FString::Printf(TEXT("scratch drive at a 30 km/h hold: %.1f m of the 100 m in %.1f s (%.1f m driven since the teleport, the run-up included), lowest speed %s; %d instances touched, %d bent beyond 20 deg, snaps %d (Sapling %d, Young %d; %d impact, %d sustained push), at most %d in contact at once, resist max %.0f N, tilt max %.1f deg, evicted %d, no slot %d; work %.3f ms mean, %.3f ms max over %d frames (rolling %.3f / %.3f over %d); active %d, debris in use %d"),
				FMath::Clamp(Along, 0.f, 10000.f) / 100.f, Now - CaseStart, ScratchPathCm / 100.f, *Kph(ScratchMinSpeed < 1.e8f ? ScratchMinSpeed : 0.f), Stats.Contacted, Stats.BentOver, Stats.Snaps,
				Stats.SnapsByClass[1], Stats.SnapsByClass[2], Stats.SnapsImpact, Stats.SnapsSustained, Stats.MaxContacts, Stats.MaxForceN, Stats.MaxTiltDeg, Stats.Evicted, Stats.NoSlot,
				Stats.TickFrames > 0 ? static_cast<float>(Stats.TickMsSum / Stats.TickFrames) : 0.f, Stats.TickMsMax, Stats.TickFrames, Mean, Max, Frames,
				Veg->GetActiveCount(), Veg->GetDebrisInUse());
			Log(Line + TEXT(" (information, no band)"));
			if (bHide)
			{
				// LD7: this pass's frame and GPU over the 100 m; dressing 1 first, then the same line with 0.
				const int32 Pass = FMath::Clamp(HidePass, 0, 1);
				HideFrameMs[Pass] = FrameCount > 0 ? static_cast<float>(FrameMsSum / FrameCount) : -1.f;
				HideGpuMs[Pass] = FrameCount > 0 ? static_cast<float>(GpuMsSum / FrameCount) : -1.f;
				HideMadeM[Pass] = FMath::Clamp(Along, 0.f, 10000.f) / 100.f;
				HideWork[Pass] = FString::Printf(TEXT("work %.3f ms mean, %.3f ms max over %d frames"),
					Stats.TickFrames > 0 ? static_cast<float>(Stats.TickMsSum / Stats.TickFrames) : 0.f, Stats.TickMsMax, Stats.TickFrames);
				Log(FString::Printf(TEXT("hide pass gt.Look.Dressing %d: %s over the 100 m"), HidePass, *FrameLine()));
				if (HidePass == 1)
				{
					HidePass = 0;
					GTVegTest::SetDressing(0);
					ParkAt = ScratchLine.Origin - ScratchLine.Dir * 2000.f;
					Next(EStep::ScratchSettle);
					return false;
				}
				GTVegTest::SetDressing(1);
				const FString HideLine = FString::Printf(TEXT("hide thicket drive (%.1f m from the route, %d soft pivots within 2 m of the line): dressing 1 frame %.2f ms, GPU %.2f ms, %.1f m made, vegetation %s; dressing 0 frame %.2f ms, GPU %.2f ms, %.1f m made; GPU %+.2f ms, frame %+.2f ms (the vegetation tick budget 0.3 ms)"),
					HideRouteDistM, ScratchScore, HideFrameMs[1], HideGpuMs[1], HideMadeM[1], *HideWork[1], HideFrameMs[0], HideGpuMs[0], HideMadeM[0],
					HideGpuMs[1] - HideGpuMs[0], HideFrameMs[1] - HideFrameMs[0]);
				Log(HideLine);
				Results.Add(HideLine);
			}
			else
			{
				Results.Add(FString::Printf(TEXT("scratch (information): %s; %s"), *Veg->DescribeIndex(), *Line));
			}
			Finish(bOutPass, OutSummary);
			return true;
		}
		return false;
	}
	case EStep::Done:
		Finish(bOutPass, OutSummary);
		return true;
	default:
		TickCase(DeltaSeconds);
		if (Step == EStep::Done)
		{
			Finish(bOutPass, OutSummary);
			return true;
		}
		return false;
	}
}
