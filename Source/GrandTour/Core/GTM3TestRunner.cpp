#include "Core/GTM3TestRunner.h"

#include "Character/GTExposureComponent.h"
#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Core/GTPlayerController.h"
#include "Core/GTRunSubsystem.h"
#include "Environment/GTEnvironmentComponent.h"
#include "Harvest/GTHarvestNode.h"
#include "Harvest/GTLootTable.h"
#include "Hazards/GTRadiationZone.h"
#include "Hazards/GTWeatherFront.h"
#include "Interaction/GTInteractionComponent.h"
#include "Inventory/GTInventoryComponent.h"
#include "Run/GTLegActors.h"
#include "Run/GTLegDefinition.h"
#include "Run/GTRunGameMode.h"
#include "Run/GTRunGameState.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTDashboardComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTVehicleTuningComponent.h"
#include "Weather/GTRainEmitter.h"
#include "Weather/GTWeatherStateDefinition.h"
#include "Weather/GTWeatherSubsystem.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

FGTM3TestRunner::FGTM3TestRunner(UWorld* InWorld, EGTM3Test InKind)
	: World(InWorld), Kind(InKind)
{
}

void FGTM3TestRunner::Log(const FString& Line) const
{
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST m3 t=%.1f step %d: %s"), Elapsed, Step, *Line);
}

void FGTM3TestRunner::Finish(bool bInPass, const FString& InSummary)
{
	bDone = true;
	bPass = bInPass;
	Summary = InSummary;
}

void FGTM3TestRunner::Next()
{
	++Step;
	StepTime = 0.f;
	bStepStarted = false;
}

bool FGTM3TestRunner::StepTimedOut(float Seconds, const TCHAR* What)
{
	if (StepTime > Seconds)
	{
		Fail(FString::Printf(TEXT("timed out waiting for %s"), What));
		return true;
	}
	return false;
}

bool FGTM3TestRunner::EverySecond(float DeltaSeconds) const
{
	return FMath::IsNearlyEqual(FMath::Fmod(StepTime, 1.f), 0.f, DeltaSeconds * 0.6f) && StepTime > 0.5f;
}

FVector FGTM3TestRunner::CarLocal(const FVector& Local) const
{
	return Car.IsValid() ? Car->GetMesh()->GetComponentTransform().TransformPosition(Local) : Local;
}

void FGTM3TestRunner::TeleportCar(const FVector& Location)
{
	if (!Car.IsValid())
	{
		return;
	}
	Car->SetActorLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
	Car->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	Car->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
	if (UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement())
	{
		Move->SetThrottleInput(0.f);
		Move->SetHandbrakeInput(true);
	}
}

void FGTM3TestRunner::TeleportCharacter(const FVector& GroundLocation, const FVector& LookAt)
{
	if (!Character.IsValid() || !PC.IsValid())
	{
		return;
	}
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	Character->SetActorLocation(GroundLocation + FVector(0.f, 0.f, HalfHeight + 2.f), false, nullptr, ETeleportType::TeleportPhysics);
	PC->SetControlRotation((LookAt - Character->GetPawnViewLocation()).Rotation());
}

bool FGTM3TestRunner::ExitCar()
{
	if (!PC.IsValid() || !PC->ExitCar())
	{
		return false;
	}
	Character = PC->GetPlayerCharacter();
	if (Character.IsValid())
	{
		Character->DisableInput(PC.Get());
	}
	return Character.IsValid();
}

bool FGTM3TestRunner::EnterCar()
{
	if (!PC.IsValid() || !Car.IsValid() || !Character.IsValid())
	{
		return false;
	}
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	Character->SetActorLocation(Car->FindExitLocation(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
	const bool bEntered = PC->EnterCar();
	Car->DisableInput(PC.Get());
	Car->ResetDrivingInputs();
	return bEntered;
}

AStaticMeshActor* FGTM3TestRunner::SpawnBox(const FVector& Location, const FVector& Scale, const TCHAR* Label)
{
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AStaticMeshActor* Box = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Location, Car.IsValid() ? Car->GetActorRotation() : FRotator::ZeroRotator, Params);
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Box && Cube)
	{
		Box->SetMobility(EComponentMobility::Movable);
		Box->GetStaticMeshComponent()->SetStaticMesh(Cube);
		Box->SetActorScale3D(Scale);
		Box->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
	}
	Log(FString::Printf(TEXT("%s at %s"), Label, *Location.ToCompactString()));
	return Box;
}

bool FGTM3TestRunner::Setup()
{
	PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(World.Get(), 0));
	Car = PC.IsValid() ? Cast<AGTCarPawn>(PC->GetPawn()) : nullptr;
	if (!PC.IsValid() || !Car.IsValid())
	{
		Fail(TEXT("player 0 is not an AGTPlayerController driving an AGTCarPawn"));
		return false;
	}
	Car->DisableInput(PC.Get());
	Car->ResetDrivingInputs();
	Character = PC->GetPlayerCharacter();
	if (Character.IsValid())
	{
		Character->DisableInput(PC.Get());
	}
	GameMode = Cast<AGTRunGameMode>(World->GetAuthGameMode());
	RunState = World->GetGameState<AGTRunGameState>();
	Weather = World->GetSubsystem<UGTWeatherSubsystem>();
	if (!GameMode.IsValid() || !RunState.IsValid())
	{
		Fail(TEXT("the game mode is not AGTRunGameMode with AGTRunGameState"));
		return false;
	}
	Log(FString::Printf(TEXT("car at %s, weather=%s"), *Car->GetActorLocation().ToCompactString(), Weather.IsValid() ? *Weather->Describe() : TEXT("none")));
	return true;
}

bool FGTM3TestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	if (bDone)
	{
		bOutPass = bPass;
		OutSummary = Summary;
		return true;
	}
	Elapsed += DeltaSeconds;
	if (Step < 0)
	{
		if (Elapsed < 0.5f)
		{
			return false;   // let the car settle and the subsystems tick once
		}
		if (!Setup())
		{
			bOutPass = bPass;
			OutSummary = Summary;
			return true;
		}
		Next();
	}
	StepTime += DeltaSeconds;
	if (!Car.IsValid() || !PC.IsValid())
	{
		Fail(TEXT("car or controller vanished"));
	}
	else
	{
		switch (Kind)
		{
		case EGTM3Test::Leg:         TickLeg(DeltaSeconds); break;
		case EGTM3Test::Weather:     TickWeather(DeltaSeconds); break;
		case EGTM3Test::Hazard:      TickHazard(DeltaSeconds); break;
		case EGTM3Test::Loot:        TickLoot(DeltaSeconds); break;
		case EGTM3Test::Environment: TickEnvironment(DeltaSeconds); break;
		}
	}
	if (Elapsed > 90.f && !bDone)
	{
		Fail(FString::Printf(TEXT("overall timeout at step %d"), Step));
	}
	bOutPass = bPass;
	OutSummary = Summary;
	return bDone;
}

// ---- leg ---------------------------------------------------------------------------------------

void FGTM3TestRunner::TickLeg(float DeltaSeconds)
{
	UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement();
	AGTRunGameState* State = RunState.Get();
	switch (Step)
	{
	case 0:   // checkpoints, extraction and a runtime leg
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		const FRotator Facing = Car->GetActorRotation();
		AGTCheckpoint* CP1 = World->SpawnActor<AGTCheckpoint>(AGTCheckpoint::StaticClass(), CarLocal(FVector(3000.f, 0.f, 250.f)), Facing, Params);
		AGTCheckpoint* CP2 = World->SpawnActor<AGTCheckpoint>(AGTCheckpoint::StaticClass(), CarLocal(FVector(9000.f, 0.f, 250.f)), Facing, Params);
		AGTExtractionZone* Extraction = World->SpawnActor<AGTExtractionZone>(AGTExtractionZone::StaticClass(), CarLocal(FVector(15000.f, 0.f, 250.f)), Facing, Params);
		if (!CP1 || !CP2 || !Extraction)
		{
			Fail(TEXT("could not spawn the leg actors"));
			return;
		}
		CP1->Index = 1;
		CP2->Index = 2;
		UGTLegDefinition* NewLeg = NewObject<UGTLegDefinition>(GameMode.Get(), NAME_None, RF_Transient);
		NewLeg->ApplyDefaultLeg01();
		NewLeg->Conditions.Reset();
		NewLeg->ParTimeSeconds = 60.f;
		NewLeg->TimeLimitSeconds = 0.f;
		NewLeg->RivalTimesSeconds = { 5.f, 100.f, 200.f };
		Leg = NewLeg;
		GameMode->SetLeg(NewLeg);
		Car->GetBoot()->Add(GTItems::Scrap, 3);
		if (Character.IsValid())
		{
			Character->GetInventory()->Add(GTItems::Wire, 2);
		}
		bStagingOk = State->GetPhase() == EGTLegPhase::Staging && State->GetCheckpointCount() == 2 && State->GetExtraction() != nullptr && State->GetLegTime() == 0.f;
		Log(FString::Printf(TEXT("leg set: %s -> stagingOk=%d"), *State->Describe(), bStagingOk ? 1 : 0));
		Next();
		break;
	}
	case 1:   // drive: the timer starts on the move, checkpoint 1 clears
		if (Move)
		{
			Move->SetThrottleInput(1.f);
			Move->SetHandbrakeInput(false);
		}
		if (!bStartedOnMove && State->GetPhase() == EGTLegPhase::Running)
		{
			bStartedOnMove = true;
			Log(FString::Printf(TEXT("started on move at speed %.0f: %s"), Car->GetVelocity().Size2D(), *State->Describe()));
		}
		if (EverySecond(DeltaSeconds))
		{
			Log(FString::Printf(TEXT("driving x=%.0f speed=%.0f %s"), Car->GetActorLocation().X, Car->GetVelocity().Size2D(), *State->Describe()));
		}
		if (State->GetCheckpointsCleared() >= 1)
		{
			bCheckpoint1 = true;
			Log(FString::Printf(TEXT("checkpoint 1 cleared: %s"), *State->Describe()));
			Next();
		}
		else if (StepTimedOut(14.f, TEXT("checkpoint 1")))
		{
			return;
		}
		break;
	case 2:   // into the extraction zone early: refused
		if (!bStepStarted)
		{
			bStepStarted = true;
			const FVector ZoneLocation = State->GetExtraction()->GetActorLocation();
			TeleportCar(FVector(ZoneLocation.X, ZoneLocation.Y, Car->GetActorLocation().Z));
		}
		if (StepTime >= 3.5f)
		{
			bEarlyRefused = State->ExtractionAttemptsRefused >= 1 && State->GetPhase() == EGTLegPhase::Running;
			Log(FString::Printf(TEXT("early extraction: refused=%d %s"), bEarlyRefused ? 1 : 0, *State->Describe()));
			Next();
		}
		break;
	case 3:   // checkpoint 2 by teleport
		if (!bStepStarted)
		{
			bStepStarted = true;
			const FVector CP = State->GetNextCheckpoint() ? State->GetNextCheckpoint()->GetActorLocation() : FVector::ZeroVector;
			TeleportCar(FVector(CP.X, CP.Y, Car->GetActorLocation().Z));
		}
		if (State->GetCheckpointsCleared() >= 2)
		{
			bCheckpoint2 = true;
			Log(FString::Printf(TEXT("checkpoint 2 cleared: %s"), *State->Describe()));
			Next();
		}
		else if (StepTimedOut(3.f, TEXT("checkpoint 2")))
		{
			return;
		}
		break;
	case 4:   // extraction: stop inside, hold, finished
		if (!bStepStarted)
		{
			bStepStarted = true;
			const FVector ZoneLocation = State->GetExtraction()->GetActorLocation();
			TeleportCar(FVector(ZoneLocation.X, ZoneLocation.Y, Car->GetActorLocation().Z));
		}
		if (EverySecond(DeltaSeconds))
		{
			Log(FString::Printf(TEXT("extracting speed=%.0f %s"), Car->GetVelocity().Size2D(), *State->Describe()));
		}
		if (State->GetPhase() == EGTLegPhase::Finished)
		{
			bFinished = true;
			const FGTLegResult& R = State->GetResult();
			FinishTime = R.TimeSeconds;
			ResultLine = R.Describe();
			const UGTRunSubsystem* Run = World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UGTRunSubsystem>() : nullptr;
			const bool bRecorded = Run && Run->HasResult() && Run->GetLastResult().LegId == R.LegId;
			const int32 Scrap = [&R]() { const FGTItemStack* S = R.Haul.FindByPredicate([](const FGTItemStack& X) { return X.ItemId == GTItems::Scrap; }); return S ? S->Count : 0; }();
			const int32 Wire = [&R]() { const FGTItemStack* S = R.Haul.FindByPredicate([](const FGTItemStack& X) { return X.ItemId == GTItems::Wire; }); return S ? S->Count : 0; }();
			const bool bHaulOk = Scrap == 3 && Wire == 2 && R.HaulValue == 3 * 5 + 2 * 4;
			// Since M5 the run subsystem scores the leg against the tour's four simulated rivals (the runtime tour here); at
			// 9.7 s against a par of 60 the player beats every draw, so the placing is 1 of 5 with full points.
			const bool bRankOk = R.Rank == 1 && R.RivalCount == 4 && R.Rivals.Num() == 4 && R.Points > 0 && R.PrizeCredits > 0 && R.bCompleted;
			const bool bAll = bStagingOk && bStartedOnMove && bCheckpoint1 && bEarlyRefused && bCheckpoint2 && bFinished && FinishTime > 3.f
				&& R.CheckpointsCleared == 2 && R.CheckpointCount == 2 && bHaulOk && bRankOk && bRecorded && GameMode->LegsFinished == 1;
			Finish(bAll, FString::Printf(TEXT("leg: staging=%d startedOnMove=%d cp1=%d earlyRefused=%d cp2=%d finished=%d time=%.1f haulOk=%d rankOk=%d recorded=%d | %s"),
				bStagingOk ? 1 : 0, bStartedOnMove ? 1 : 0, bCheckpoint1 ? 1 : 0, bEarlyRefused ? 1 : 0, bCheckpoint2 ? 1 : 0, bFinished ? 1 : 0, FinishTime,
				bHaulOk ? 1 : 0, bRankOk ? 1 : 0, bRecorded ? 1 : 0, *ResultLine));
		}
		else if (StepTimedOut(8.f, TEXT("the extraction")))
		{
			return;
		}
		break;
	default:
		Fail(TEXT("unknown step"));
		break;
	}
}

// ---- weather -----------------------------------------------------------------------------------

void FGTM3TestRunner::TickWeather(float DeltaSeconds)
{
	if (!Weather.IsValid())
	{
		Fail(TEXT("no UGTWeatherSubsystem in this world"));
		return;
	}
	AGTRainEmitter* Emitter = Weather->GetRainEmitter();
	switch (Step)
	{
	case 0:   // a roof beside the car, then rain in 2 s
	{
		const float Rain0 = Weather->GetRainIntensity();
		Roof = SpawnBox(CarLocal(FVector(0.f, -800.f, 350.f)), FVector(10.f, 10.f, 0.2f), TEXT("roof"));
		UGTWeatherStateDefinition* Rain = NewObject<UGTWeatherStateDefinition>(Weather.Get(), NAME_None, RF_Transient);
		Rain->ApplyDefault(*UGTWeatherStateDefinition::FindDefault(TEXT("Rain")));
		Rain->TransitionSeconds = 2.f;
		Weather->SetState(Rain);
		Log(FString::Printf(TEXT("start rain=%.2f state=%s emitter=%d -> Rain over 2 s"), Rain0, *Weather->GetStateName(), Emitter ? 1 : 0));
		if (Rain0 > 0.01f)
		{
			Fail(TEXT("the weather did not start clear"));
			return;
		}
		Next();
		break;
	}
	case 1:   // after the blend: rain, wetness, collection, traction, drops, none under the roof, ambience
		if (EverySecond(DeltaSeconds))
		{
			Log(Weather->Describe());
		}
		if (StepTime >= 4.f)
		{
			RainAfterBlend = Weather->GetRainIntensity();
			WetnessAfterRain = Weather->GetWetness();
			if (!Weather->ReadCollectionScalar(TEXT("RainIntensity"), CollectionRain)) { CollectionRain = -1.f; }
			if (!Weather->ReadCollectionScalar(TEXT("Wetness"), CollectionWetness)) { CollectionWetness = -1.f; }
			TractionWetness = Car->GetTraction()->Wetness;
			TarmacGrip = Car->GetTraction()->Wheels.Num() > 0 ? Car->GetTraction()->Wheels[0].FrictionScale : 1.f;
			if (Emitter)
			{
				LiveDrops = Emitter->LiveDrops;
				RejectedUnderCover = Emitter->RejectedUnderCover;
				// The space under the roof: from the ground to 10 cm below its underside (the slab is 20 cm thick), 2 m in
				// from the edges: wind-blown drops that fall past the edge drift about a metre in under it, as rain does.
				DropsUnderRoof = Roof.IsValid() ? Emitter->CountDropsInBox(Roof->GetActorLocation() - FVector(0.f, 0.f, 200.f), FVector(300.f, 300.f, 140.f)) : -1;
				AudioRms = Emitter->RenderTestBlock(4410);
				EmitterDrawn = Emitter->TotalSpawned;
			}
			Log(FString::Printf(TEXT("rain=%.2f wet=%.2f collection rain=%.2f wet=%.2f traction wet=%.2f grip=%.2f drops live=%d underRoof=%d rejected=%d rms=%.3f"),
				RainAfterBlend, WetnessAfterRain, CollectionRain, CollectionWetness, TractionWetness, TarmacGrip, LiveDrops, DropsUnderRoof, RejectedUnderCover, AudioRms));
			Next();
		}
		break;
	case 2:   // on foot in the open: the meter drains
		if (!bStepStarted)
		{
			bStepStarted = true;
			if (!ExitCar())
			{
				Fail(TEXT("could not get out of the car"));
				return;
			}
			TeleportCharacter(CarLocal(FVector(700.f, 0.f, 0.f)), CarLocal(FVector(2000.f, 0.f, 160.f)));
		}
		if (StepTime >= 3.f)
		{
			ExposureInRain = Character->GetExposure()->Exposure;
			Log(FString::Printf(TEXT("3 s in the rain: exposure=%.1f drainRate=%.2f underCover=%d"), ExposureInRain, Character->EnvironmentDrainRate, Character->bUnderCover ? 1 : 0));
			Next();
		}
		break;
	case 3:   // under the roof: no rain drain
		if (!bStepStarted)
		{
			bStepStarted = true;
			const FVector Under = Roof.IsValid() ? Roof->GetActorLocation() : CarLocal(FVector(0.f, -800.f, 350.f));
			TeleportCharacter(FVector(Under.X, Under.Y, CarLocal(FVector::ZeroVector).Z), Under + FVector(500.f, 0.f, -200.f));
			ExposureUnderRoof = Character->GetExposure()->Exposure;
		}
		if (StepTime >= 3.f)
		{
			ExposureAfterRoof = Character->GetExposure()->Exposure;
			Log(FString::Printf(TEXT("3 s under the roof: exposure %.1f -> %.1f drainRate=%.2f underCover=%d"), ExposureUnderRoof, ExposureAfterRoof, Character->EnvironmentDrainRate, Character->bUnderCover ? 1 : 0));
			Next();
		}
		break;
	case 4:   // snow: below zero, cover accumulates
		if (!bStepStarted)
		{
			bStepStarted = true;
			EnterCar();
			UGTWeatherStateDefinition* Snow = NewObject<UGTWeatherStateDefinition>(Weather.Get(), NAME_None, RF_Transient);
			Snow->ApplyDefault(*UGTWeatherStateDefinition::FindDefault(TEXT("Snow")));
			Snow->TransitionSeconds = 1.f;
			Weather->SetState(Snow);
		}
		if (StepTime >= 3.f)
		{
			TempInSnow = Weather->GetTemperature();
			SnowAfterSnow = Weather->GetSnowAmount();
			Log(FString::Printf(TEXT("snow: temp=%.1f snow=%.3f %s"), TempInSnow, SnowAfterSnow, *Weather->Describe()));
			Next();
		}
		break;
	case 5:   // a parked front half-way into its influence: storm pressure lifts the rain without a state change
		if (!bStepStarted)
		{
			bStepStarted = true;
			Weather->SetState(Weather->FindState(TEXT("Clear")), /*bInstant*/ true);
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Front = World->SpawnActor<AGTWeatherFront>(AGTWeatherFront::StaticClass(), CarLocal(FVector(9000.f, 0.f, 1500.f)), FRotator(0.f, Car->GetActorRotation().Yaw + 180.f, 0.f), Params);
			if (Front.IsValid())
			{
				Front->SpeedCmPerSec = 0.f;
				Front->InfluenceCm = 10000.f;   // the leading face sits 50 m ahead: pressure 0.5
			}
		}
		if (StepTime >= 1.f)
		{
			RainFromFront = Weather->GetRainIntensity();
			Log(FString::Printf(TEXT("front parked: pressure=%.2f rain=%.2f state=%s"), Weather->GetStormPressure(), RainFromFront, *Weather->GetStateName()));
			if (Front.IsValid())
			{
				Front->Destroy();
			}
			Next();
		}
		break;
	case 6:   // occlusion capture (gpu runs): the roof is nearer the capture than the ground
	{
		if (Emitter && Emitter->bGpuEnabled && Roof.IsValid())
		{
			float RoofDepth = 0.f;
			float OpenDepth = 0.f;
			const bool bRoof = Emitter->ReadOcclusionDepth(Roof->GetActorLocation(), RoofDepth);
			const bool bOpen = Emitter->ReadOcclusionDepth(CarLocal(FVector(700.f, 0.f, 0.f)), OpenDepth);
			bOcclusionRead = bRoof && bOpen;
			OcclusionRoofDepth = RoofDepth;
			OcclusionOpenDepth = OpenDepth;
			Log(FString::Printf(TEXT("occlusion: roofDepth=%.0f openDepth=%.0f read=%d top=%.0f %s"), RoofDepth, OpenDepth, bOcclusionRead ? 1 : 0, Emitter->GetCaptureTopZ(), *Emitter->Describe()));
		}
		const bool bCollectionOk = !Weather->bCollectionFound || (FMath::Abs(CollectionRain - RainAfterBlend) < 0.05f && FMath::Abs(CollectionWetness - WetnessAfterRain) < 0.1f);
		const bool bOcclusionOk = !bOcclusionRead || (OcclusionRoofDepth < OcclusionOpenDepth - 200.f);
		const bool bAll = RainAfterBlend > 0.6f && WetnessAfterRain > 0.3f && bCollectionOk && FMath::Abs(TractionWetness - WetnessAfterRain) < 0.05f && TarmacGrip < 0.95f
			&& LiveDrops > 50 && DropsUnderRoof == 0 && AudioRms > 0.02f
			&& ExposureInRain < 99.f && ExposureAfterRoof >= ExposureUnderRoof - 0.2f
			&& TempInSnow < 0.f && SnowAfterSnow > 0.02f && RainFromFront > 0.3f && bOcclusionOk;
		Finish(bAll, FString::Printf(TEXT("weather: rain=%.2f wet=%.2f collection=%d traction=%.2f grip=%.2f drops=%d underRoof=%d rejected=%d rms=%.3f exposureRain=%.1f roof=%.1f->%.1f snowTemp=%.1f snow=%.3f frontRain=%.2f occlusion(read=%d roof=%.0f open=%.0f) assets=%d"),
			RainAfterBlend, WetnessAfterRain, bCollectionOk ? 1 : 0, TractionWetness, TarmacGrip, LiveDrops, DropsUnderRoof, RejectedUnderCover, AudioRms, ExposureInRain,
			ExposureUnderRoof, ExposureAfterRoof, TempInSnow, SnowAfterSnow, RainFromFront, bOcclusionRead ? 1 : 0, OcclusionRoofDepth, OcclusionOpenDepth, Weather->StatesFromAssets));
		break;
	}
	default:
		Fail(TEXT("unknown step"));
		break;
	}
}

// ---- hazards -----------------------------------------------------------------------------------

void FGTM3TestRunner::TickHazard(float DeltaSeconds)
{
	UGTConditionComponent* Condition = Car->GetCondition();
	switch (Step)
	{
	case 0:   // a front rolls over the parked car
		if (!bStepStarted)
		{
			bStepStarted = true;
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Front = World->SpawnActor<AGTWeatherFront>(AGTWeatherFront::StaticClass(), CarLocal(FVector(9000.f, 0.f, 1500.f)), FRotator(0.f, Car->GetActorRotation().Yaw + 180.f, 0.f), Params);
			if (!Front.IsValid())
			{
				Fail(TEXT("could not spawn the front"));
				return;
			}
			Front->SpeedCmPerSec = 1000.f;
			Front->InfluenceCm = 5000.f;
			Log(FString::Printf(TEXT("front spawned 90 m ahead, leading face %.0f cm ahead, coming at 10 m/s"), Front->DistanceAhead(Car->GetActorLocation())));
		}
		if (PressureFar < 0.f && StepTime >= 0.3f)
		{
			PressureFar = Front->LastPressure;
		}
		if (PressureNear < 0.f && StepTime >= 2.5f)
		{
			PressureNear = Front->LastPressure;
		}
		if (EverySecond(DeltaSeconds))
		{
			Log(FString::Printf(TEXT("front ahead=%.0f pressure=%.2f carInside=%d %s"), Front->DistanceAhead(Car->GetActorLocation()), Front->LastPressure, Front->bCarInside ? 1 : 0, *Weather->Describe()));
		}
		if (StepTime >= 6.f)
		{
			bInsideFront = Front->bCarInside && Car->IsInHazard(GTTags::Hazard_Weather);
			Front->SpeedCmPerSec = 0.f;
			Log(FString::Printf(TEXT("inside=%d pressureFar=%.2f pressureNear=%.2f %s"), bInsideFront ? 1 : 0, PressureFar, PressureNear, *Front->Describe()));
			if (!ExitCar())
			{
				Fail(TEXT("could not get out inside the front"));
				return;
			}
			Next();
		}
		break;
	case 1:   // on foot in the front: exposure; the car: glass and body
		if (StepTime >= 2.5f)
		{
			ExposureInFront = Character->GetExposure()->Exposure;
			GlassAfterFront = Condition->GetPartHealth(EGTCarPart::Glass);
			BodyAfterFront = Condition->GetPartHealth(EGTCarPart::Body);
			Log(FString::Printf(TEXT("in the front: exposure=%.1f glass=%.3f body=%.3f hazardDamage=%.3f %s"), ExposureInFront, GlassAfterFront, BodyAfterFront, Condition->HazardDamageTaken, *Front->Describe()));
			EnterCar();
			Front->Destroy();
			Next();
		}
		break;
	case 2:   // a radiation zone around the car
		if (!bStepStarted)
		{
			bStepStarted = true;
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			// 3 m above the car's origin: the zone's half height is 6 m, so the car is inside with 3 m to spare. At 6 m the
			// car's origin sat exactly on the bottom face and only counted as inside while Chaos held the body asleep; a
			// chassis that never sleeps (stage 2) settles a centimetre and was out.
			Zone = World->SpawnActor<AGTRadiationZone>(AGTRadiationZone::StaticClass(), CarLocal(FVector(0.f, 0.f, 300.f)), FRotator::ZeroRotator, Params);
			if (!Zone.IsValid())
			{
				Fail(TEXT("could not spawn the radiation zone"));
				return;
			}
		}
		if (StepTime >= 3.f)
		{
			EngineAfterZone = Condition->GetPartHealth(EGTCarPart::Engine);
			bRadiationLight = Car->GetDashboard() && Car->GetDashboard()->bRadiationLight;
			DashLine = Car->GetDashboard() ? Car->GetDashboard()->Describe() : TEXT("no dash");
			Log(FString::Printf(TEXT("3 s in the zone: engine=%.3f light=%d clicks=%.0f %s | %s"), EngineAfterZone, bRadiationLight ? 1 : 0, Zone->LastClickRate, *Zone->Describe(), *DashLine));
			if (!ExitCar())
			{
				Fail(TEXT("could not get out in the zone"));
				return;
			}
			Next();
		}
		break;
	case 3:   // on foot in the zone, then the rare cache inside it
		if (StepTime >= 2.f && !bStepStarted)
		{
			bStepStarted = true;
			ExposureInZone = Character->GetExposure()->Exposure;
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Node = World->SpawnActor<AGTHarvestNode>(AGTHarvestNode::StaticClass(), CarLocal(FVector(700.f, 300.f, 30.f)), FRotator::ZeroRotator, Params);
			UGTLootTable* Cache = LoadObject<UGTLootTable>(nullptr, TEXT("/Game/GrandTour/Harvest/DA_Loot_RadiationCache.DA_Loot_RadiationCache"));
			if (!Cache)
			{
				Cache = NewObject<UGTLootTable>(Node.Get(), NAME_None, RF_Transient);
				Cache->ApplyDefault(*UGTLootTable::FindDefault(TEXT("RadiationCache")));
			}
			Node->LootTable = Cache;
			Node->NodeName = TEXT("alloy cache");
			Character->SelectToolByTag(GTTags::Tool_Cut);
			TeleportCharacter(Node->GetActorLocation() + FVector(-200.f, 0.f, -30.f), Node->GetActorLocation());
			Log(FString::Printf(TEXT("2 s in the zone on foot: exposure=%.1f; cache node spawned"), ExposureInZone));
		}
		if (bStepStarted && StepTime >= 2.5f && !bRareOffered)
		{
			UGTInteractionComponent* Interaction = Character->GetInteraction();
			bRareOffered = Interaction->GetCurrentTarget() == Node.Get() && Interaction->IsOfferAvailable();
			Log(FString::Printf(TEXT("cache: %s -> offered=%d"), *Interaction->Describe(), bRareOffered ? 1 : 0));
			if (!bRareOffered)
			{
				Fail(TEXT("the cache was not offered with the cutter"));
				return;
			}
			Interaction->SetHoldInput(true);
		}
		if (Node.IsValid() && Node->HarvestCount >= 1)
		{
			Character->GetInteraction()->SetHoldInput(false);
			AlloyFromNode = Character->GetInventory()->CountOf(GTItems::RareAlloy);
			const bool bAll = PressureFar < 0.2f && PressureNear > PressureFar + 0.2f && bInsideFront && ExposureInFront < 92.f && GlassAfterFront < 0.99f && BodyAfterFront < 0.995f
				&& EngineAfterZone < 0.995f && bRadiationLight && ExposureInZone < 95.f && bRareOffered && AlloyFromNode >= 1;
			Finish(bAll, FString::Printf(TEXT("hazards: front pressure %.2f->%.2f inside=%d exposureFront=%.1f glass=%.3f body=%.3f | zone engine=%.3f light=%d exposureZone=%.1f rareOffered=%d alloy=%d | %s"),
				PressureFar, PressureNear, bInsideFront ? 1 : 0, ExposureInFront, GlassAfterFront, BodyAfterFront, EngineAfterZone, bRadiationLight ? 1 : 0, ExposureInZone,
				bRareOffered ? 1 : 0, AlloyFromNode, *DashLine));
		}
		else if (bStepStarted && StepTimedOut(8.f, TEXT("the cache harvest")))
		{
			return;
		}
		break;
	default:
		Fail(TEXT("unknown step"));
		break;
	}
}

// ---- loot --------------------------------------------------------------------------------------

void FGTM3TestRunner::TickLoot(float DeltaSeconds)
{
	switch (Step)
	{
	case 0:   // 200 rolls of the wreck table
	{
		UGTLootTable* Wreck = LoadObject<UGTLootTable>(nullptr, TEXT("/Game/GrandTour/Harvest/DA_Loot_Wreck.DA_Loot_Wreck"));
		bAssetsLoaded = Wreck != nullptr;
		if (!Wreck)
		{
			Wreck = NewObject<UGTLootTable>(GameMode.Get(), NAME_None, RF_Transient);
			Wreck->ApplyDefault(*UGTLootTable::FindDefault(TEXT("Wreck")));
		}
		FRandomStream Random(1234);
		for (int32 Index = 0; Index < 200; ++Index)
		{
			TArray<FGTItemStack> Out;
			Wreck->Roll(Random, Out);
			++Rolls;
			int32 Scrap = 0;
			for (const FGTItemStack& S : Out)
			{
				if (S.ItemId == GTItems::Scrap) { Scrap += S.Count; }
				if (S.ItemId == GTItems::PartRadiator) { ++RadiatorHits; }
				if (S.ItemId == GTItems::PartTyre) { ++TyreHits; }
			}
			MinScrap = FMath::Min(MinScrap, Scrap);
			MaxScrap = FMath::Max(MaxScrap, Scrap);
			if (Out.Num() == 0) { ++EmptyRolls; }
		}
		Log(FString::Printf(TEXT("%s: %d rolls scrap %d..%d radiator %d tyre %d empty %d (assets=%d)"), *Wreck->Describe(), Rolls, MinScrap, MaxScrap, RadiatorHits, TyreHits, EmptyRolls, bAssetsLoaded ? 1 : 0));
		Next();
		break;
	}
	case 1:   // a node with the cache table pays from it
		if (!bStepStarted)
		{
			bStepStarted = true;
			if (!ExitCar())
			{
				Fail(TEXT("could not get out of the car"));
				return;
			}
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Node = World->SpawnActor<AGTHarvestNode>(AGTHarvestNode::StaticClass(), CarLocal(FVector(700.f, 300.f, 30.f)), FRotator::ZeroRotator, Params);
			UGTLootTable* Cache = LoadObject<UGTLootTable>(nullptr, TEXT("/Game/GrandTour/Harvest/DA_Loot_RadiationCache.DA_Loot_RadiationCache"));
			if (!Cache)
			{
				Cache = NewObject<UGTLootTable>(Node.Get(), NAME_None, RF_Transient);
				Cache->ApplyDefault(*UGTLootTable::FindDefault(TEXT("RadiationCache")));
			}
			Node->LootTable = Cache;
			Character->SelectToolByTag(GTTags::Tool_Cut);
			TeleportCharacter(Node->GetActorLocation() + FVector(-200.f, 0.f, -30.f), Node->GetActorLocation());
		}
		if (StepTime >= 0.5f && !bRareOffered)
		{
			UGTInteractionComponent* Interaction = Character->GetInteraction();
			bRareOffered = Interaction->GetCurrentTarget() == Node.Get() && Interaction->IsOfferAvailable();
			Log(FString::Printf(TEXT("node: %s -> offered=%d"), *Interaction->Describe(), bRareOffered ? 1 : 0));
			if (!bRareOffered)
			{
				Fail(TEXT("the node was not offered"));
				return;
			}
			Interaction->SetHoldInput(true);
		}
		if (Node.IsValid() && Node->HarvestCount >= 1)
		{
			Character->GetInteraction()->SetHoldInput(false);
			AlloyFromNode = Character->GetInventory()->CountOf(GTItems::RareAlloy);
			Log(FString::Printf(TEXT("harvested: %s | %s"), *Node->Describe(), *Character->GetInventory()->Describe()));
			// Wreck table: 1 guaranteed scrap + 1..2 picks of up to 4; radiator weight 1.5 of 9.25 per pick.
			const bool bAll = Rolls == 200 && EmptyRolls == 0 && MinScrap >= 1 && MaxScrap <= 9 && RadiatorHits >= 15 && RadiatorHits <= 100 && TyreHits >= 5
				&& bRareOffered && AlloyFromNode >= 1 && Node->LastRoll.Num() >= 1;
			Finish(bAll, FString::Printf(TEXT("loot: rolls=%d scrap=%d..%d radiator=%d tyre=%d empty=%d assets=%d nodeOffered=%d alloy=%d lastRoll=%d"),
				Rolls, MinScrap, MaxScrap, RadiatorHits, TyreHits, EmptyRolls, bAssetsLoaded ? 1 : 0, bRareOffered ? 1 : 0, AlloyFromNode, Node->LastRoll.Num()));
		}
		else if (StepTimedOut(8.f, TEXT("the node harvest")))
		{
			return;
		}
		break;
	default:
		Fail(TEXT("unknown step"));
		break;
	}
}

// ---- environment ---------------------------------------------------------------------------------

void FGTM3TestRunner::TickEnvironment(float DeltaSeconds)
{
	UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement();
	UGTEnvironmentComponent* Env = Car->GetEnvironment();
	UGTConditionComponent* Condition = Car->GetCondition();
	if (!Env || !Move || !Condition)
	{
		Fail(TEXT("the car has no environment, movement or condition component"));
		return;
	}
	switch (Step)
	{
	case 0:   // a flat profile of all three conditions, then drive flat out
		if (!bStepStarted)
		{
			bStepStarted = true;
			UGTLegDefinition* NewLeg = NewObject<UGTLegDefinition>(GameMode.Get(), NAME_None, RF_Transient);
			NewLeg->ApplyDefaultLeg01();
			NewLeg->Conditions.Reset();
			NewLeg->AddCondition(GTTags::Env_Heat, { {0.f, 1.f}, {1.f, 1.f} });
			NewLeg->AddCondition(GTTags::Env_Dust, { {0.f, 1.f}, {1.f, 1.f} });
			NewLeg->AddCondition(GTTags::Env_Cold, { {0.f, 1.f}, {1.f, 1.f} });
			NewLeg->TimeLimitSeconds = 0.f;
			Leg = NewLeg;
			GameMode->SetLeg(NewLeg);
			Env->ClogPerKm = 5.f;   // a 1.2 km dusty leg clogs at 0.5 per km; the flat test only covers about 150 m of driving
			DriveStart = Car->GetActorLocation();
			Log(FString::Printf(TEXT("leg %s; driving 20 s"), *NewLeg->Describe()));
		}
		if (StepTime >= NextTeleportTime)
		{
			NextTeleportTime += 7.f;
			TeleportCar(DriveStart);   // the flat map is 400 m: come back to the start rather than drive off it
		}
		Move->SetThrottleInput(1.f);
		Move->SetHandbrakeInput(false);
		if (EverySecond(DeltaSeconds))
		{
			Log(FString::Printf(TEXT("drive x=%.0f speed=%.0f torqueScale=%.2f engine=%.3f %s | %s"), Car->GetActorLocation().X - DriveStart.X, Car->GetVelocity().Size2D(),
				Car->GetTuning()->GetCurrent().TorqueScale, Condition->GetPartHealth(EGTCarPart::Engine), *Env->Describe(), *Car->GetDashboard()->Describe()));
		}
		if (StepTime >= 12.f && !bTempNeedle)
		{
			// Half way: the heat should already be past the warning level and the dial moving (a log line, the verdict is at 20 s).
			bTempNeedle = Car->GetDashboard()->TempNeedleDegrees > 3.f;
			Log(FString::Printf(TEXT("12 s: heat=%.2f(%s) clog=%.2f(%s) torqueScale=%.2f coldLight=%d tempNeedle=%.0f"),
				Env->Heat, UGTEnvironmentComponent::StageName(Env->GetStage(GTTags::Env_Heat)), Env->Clog, UGTEnvironmentComponent::StageName(Env->GetStage(GTTags::Env_Dust)),
				Car->GetTuning()->GetCurrent().TorqueScale, Car->GetDashboard()->bColdLight ? 1 : 0, Car->GetDashboard()->TempNeedleDegrees));
		}
		if (StepTime >= 20.f)
		{
			HeatAfterDrive = Env->Heat;
			ClogAfterDrive = Env->Clog;
			HeatStage = static_cast<int32>(Env->GetStage(GTTags::Env_Heat));
			DustStage = static_cast<int32>(Env->GetStage(GTTags::Env_Dust));
			TorqueScaleUnderConditions = Car->GetTuning()->GetCurrent().TorqueScale;
			bFilterLight = Car->GetDashboard()->bFilterLight;
			bTempNeedle = bTempNeedle || Car->GetDashboard()->TempNeedleDegrees > 3.f;
			EngineAfterDrive = Condition->GetPartHealth(EGTCarPart::Engine);
			TeleportCar(DriveStart);   // stopped, on the floor, so the exit below is allowed
			Log(FString::Printf(TEXT("20 s: engine=%.3f conditionDamage=%.3f %s"), EngineAfterDrive, Env->TotalConditionDamage, *Env->Describe()));
			Next();
		}
		break;
	case 1:   // cold on foot: the meter drains at the profile's rate
		if (!bStepStarted)
		{
			if (Car->GetVelocity().Size2D() > 250.f)
			{
				return;   // wait for the car to slow enough to get out
			}
			bStepStarted = true;
			if (!ExitCar())
			{
				Fail(TEXT("could not get out of the car"));
				return;
			}
			TeleportCharacter(CarLocal(FVector(600.f, 0.f, 0.f)), CarLocal(FVector(2000.f, 0.f, 160.f)));
			BaseDrainRate = Character->GetExposure()->Exposure;
		}
		if (bStepStarted && StepTime >= 3.f)
		{
			ColdDrainRate = (BaseDrainRate - Character->GetExposure()->Exposure) / 3.f;
			Log(FString::Printf(TEXT("3 s on foot in the cold: exposure %.1f -> %.1f (%.2f/s) drainRate=%.2f"), BaseDrainRate, Character->GetExposure()->Exposure, ColdDrainRate, Character->EnvironmentDrainRate));
			const bool bAll = HeatAfterDrive > 0.4f && HeatStage >= 2 && ClogAfterDrive > 0.4f && DustStage >= 2 && TorqueScaleUnderConditions < 0.9f
				&& bFilterLight && bTempNeedle && EngineAfterDrive < 0.995f && EngineAfterDrive > 0.8f && Env->TotalConditionDamage > 0.f && ColdDrainRate > 0.5f;
			Finish(bAll, FString::Printf(TEXT("environment: heat=%.2f(stage %d) clog=%.2f(stage %d) torqueScale=%.2f filterLight=%d tempNeedle=%d engine=%.3f conditionDamage=%.3f coldDrain=%.2f/s"),
				HeatAfterDrive, HeatStage, ClogAfterDrive, DustStage, TorqueScaleUnderConditions, bFilterLight ? 1 : 0, bTempNeedle ? 1 : 0, EngineAfterDrive, Env->TotalConditionDamage, ColdDrainRate));
		}
		else if (StepTimedOut(15.f, TEXT("the cold drain")))
		{
			return;
		}
		break;
	default:
		Fail(TEXT("unknown step"));
		break;
	}
}
