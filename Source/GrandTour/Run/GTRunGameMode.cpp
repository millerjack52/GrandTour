#include "Run/GTRunGameMode.h"

#include "Character/GTPlayerCharacter.h"
#include "Core/GTPlayerController.h"
#include "Inventory/GTInventoryComponent.h"
#include "Run/GTLegActors.h"
#include "Run/GTLegDefinition.h"
#include "Run/GTRunGameState.h"
#include "Terrain/GTProvingGround.h"
#include "Vehicle/GTCarPawn.h"
#include "Weather/GTWeatherStateDefinition.h"
#include "Weather/GTWeatherSubsystem.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"

AGTRunGameMode::AGTRunGameMode()
{
	GameStateClass = AGTRunGameState::StaticClass();
}

void AGTRunGameMode::BeginPlay()
{
	Super::BeginPlay();
	static const TPair<const TCHAR*, EGTM3Test> Flags[] = {
		{TEXT("GTLegTest"), EGTM3Test::Leg},
		{TEXT("GTWeatherTest"), EGTM3Test::Weather},
		{TEXT("GTHazardTest"), EGTM3Test::Hazard},
		{TEXT("GTLootTest"), EGTM3Test::Loot},
		{TEXT("GTEnvTest"), EGTM3Test::Environment},
	};
	for (const auto& Flag : Flags)
	{
		if (FParse::Param(FCommandLine::Get(), Flag.Key))
		{
			UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting %s"), Flag.Key);
			M3Test = MakeUnique<FGTM3TestRunner>(GetWorld(), Flag.Value);
			break;
		}
	}
	if (FParse::Param(FCommandLine::Get(), TEXT("GTBaseTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTBaseTest"));
		M4Test = MakeUnique<FGTM4TestRunner>(GetWorld(), EGTM4Test::Base);
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTLoopTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST loop test on a leg"));
		M4Test = MakeUnique<FGTM4TestRunner>(GetWorld(), EGTM4Test::Loop);
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTDoorTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTDoorTest"));
		M4Test = MakeUnique<FGTM4TestRunner>(GetWorld(), EGTM4Test::Doors);
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTTourTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTTourTest"));
		M5Test = MakeUnique<FGTM5TestRunner>(GetWorld());
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTTerrainTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTTerrainTest"));
		M6Test = MakeUnique<FGTM6TestRunner>(GetWorld(), EGTM6Test::Terrain);
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTWaterTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTWaterTest"));
		M6Test = MakeUnique<FGTM6TestRunner>(GetWorld(), EGTM6Test::Water);
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTHideShots")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTHideShots"));
		M6Test = MakeUnique<FGTM6TestRunner>(GetWorld(), EGTM6Test::HideShots);
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTProvingTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTProvingTest"));
		ProvingTest = MakeUnique<FGTProvingTestRunner>(GetWorld());
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTFordDiag")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTFordDiag (diagnostic, off the gates)"));
		FordDiag = MakeUnique<FGTFordDiagRunner>(GetWorld());
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTProvingShots")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTProvingShots"));
		ProvingShots = MakeUnique<FGTProvingShotsRunner>(GetWorld());
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTDressingTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTDressingTest"));
		DressingTest = MakeUnique<FGTDressingTestRunner>(GetWorld());
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTBiomeTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTBiomeTest"));
		BiomeTest = MakeUnique<FGTBiomeTestRunner>(GetWorld());
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTVegTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTVegTest%s"), FParse::Param(FCommandLine::Get(), TEXT("GTVegScratch")) ? TEXT(" (scratch probe)") : TEXT(""));
		VegTest = MakeUnique<FGTVegTestRunner>(GetWorld());
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTRouteClearTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTRouteClearTest"));
		RouteClearTest = MakeUnique<FGTRouteClearanceTestRunner>(GetWorld());
	}
	// The Proving Ground (a map whose terrain spec names stations): no leg, no checkpoints, no rivals - L_Proving has no
	// AGTLegStart, so ResolveLeg finds none and the run is free roam. The stations and the test cvars go on screen.
	GTProving::ShowHelp(GetWorld(), 15.f);
}

AGTRunGameState* AGTRunGameMode::GetRunState() const
{
	return GetGameState<AGTRunGameState>();
}

void AGTRunGameMode::ResolveLeg()
{
	bLegResolved = true;
	UGTLegDefinition* Leg = nullptr;
	if (const UGTRunSubsystem* Run = GetGameInstance() ? GetGameInstance()->GetSubsystem<UGTRunSubsystem>() : nullptr)
	{
		Leg = Run->GetPendingLeg();
	}
	if (!Leg)
	{
		for (TActorIterator<AGTLegStart> It(GetWorld()); It; ++It)
		{
			Leg = It->Leg;
			if (!Leg && !It->LegAssetPath.IsEmpty())
			{
				Leg = LoadObject<UGTLegDefinition>(nullptr, *It->LegAssetPath);
				if (!Leg)
				{
					UE_LOG(LogTemp, Warning, TEXT("AGTRunGameMode: leg asset %s not found"), *It->LegAssetPath);
				}
			}
			break;
		}
	}
	if (Leg)
	{
		SetLeg(Leg);
	}
	// Whatever the base (or the save) carried: both inventories, the loadout, the condition.
	if (UGTRunSubsystem* Run = GetGameInstance() ? GetGameInstance()->GetSubsystem<UGTRunSubsystem>() : nullptr)
	{
		// A leg started on its own map (Play in the editor) continues the saved campaign; otherwise its extraction
		// would save a fresh campaign over the player's. Self-tests never load the player's save on their own.
		if (Leg && !Run->HasSnapshot() && !UGTRunSubsystem::IsSelfTestRun() && !FParse::Param(FCommandLine::Get(), TEXT("GTNoLoad")) && Run->HasSaveInSlot())
		{
			Run->LoadFromSlot();
		}
		if (Run->HasSnapshot())
		{
			AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0));
			Run->ApplyToPawns(PC ? PC->GetCar() : nullptr, PC ? PC->GetPlayerCharacter() : nullptr);
		}
	}
}

void AGTRunGameMode::SetLeg(UGTLegDefinition* Leg)
{
	AGTRunGameState* State = GetRunState();
	if (!State)
	{
		return;
	}
	const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	const FVector Start = Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector;
	State->OnExtractionReady.RemoveAll(this);
	State->SetLeg(Leg, Start);
	if (Leg)
	{
		State->OnExtractionReady.AddUObject(this, &AGTRunGameMode::FinishLeg);
		ApplyStartWeather(Leg);
		UE_LOG(LogTemp, Display, TEXT("AGTRunGameMode: running %s"), *Leg->Describe());
	}
}

void AGTRunGameMode::ApplyStartWeather(const UGTLegDefinition* Leg)
{
	UGTWeatherSubsystem* Weather = GetWorld()->GetSubsystem<UGTWeatherSubsystem>();
	if (!Weather || !Leg)
	{
		return;
	}
	UGTWeatherStateDefinition* State = Leg->StartWeather ? Leg->StartWeather.Get() : Weather->FindState(Leg->StartWeatherName);
	if (State)
	{
		Weather->SetState(State, /*bInstant*/ true);
	}
}

void AGTRunGameMode::Tick(float DeltaSeconds)
{
	if (!bLegResolved)
	{
		ResolveLeg();   // the player's pawn exists by the first tick; BeginPlay order is not guaranteed
	}
	if (M3Test)
	{
		bool bPass = false;
		FString Summary;
		if (M3Test->Tick(DeltaSeconds, bPass, Summary))
		{
			M3Test.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (M4Test)
	{
		bool bPass = false;
		FString Summary;
		if (M4Test->Tick(DeltaSeconds, bPass, Summary))
		{
			M4Test.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (M5Test)
	{
		bool bPass = false;
		FString Summary;
		if (M5Test->Tick(DeltaSeconds, bPass, Summary))
		{
			M5Test.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (FordDiag)
	{
		bool bPass = false;
		FString Summary;
		if (FordDiag->Tick(DeltaSeconds, bPass, Summary))
		{
			FordDiag.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (ProvingShots)
	{
		bool bPass = false;
		FString Summary;
		if (ProvingShots->Tick(DeltaSeconds, bPass, Summary))
		{
			ProvingShots.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (BiomeTest)
	{
		bool bPass = false;
		FString Summary;
		if (BiomeTest->Tick(DeltaSeconds, bPass, Summary))
		{
			BiomeTest.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (VegTest)
	{
		bool bPass = false;
		FString Summary;
		if (VegTest->Tick(DeltaSeconds, bPass, Summary))
		{
			VegTest.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (RouteClearTest)
	{
		bool bPass = false;
		FString Summary;
		if (RouteClearTest->Tick(DeltaSeconds, bPass, Summary))
		{
			RouteClearTest.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (DressingTest)
	{
		bool bPass = false;
		FString Summary;
		if (DressingTest->Tick(DeltaSeconds, bPass, Summary))
		{
			DressingTest.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (ProvingTest)
	{
		bool bPass = false;
		FString Summary;
		if (ProvingTest->Tick(DeltaSeconds, bPass, Summary))
		{
			ProvingTest.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	if (M6Test)
	{
		bool bPass = false;
		FString Summary;
		if (M6Test->Tick(DeltaSeconds, bPass, Summary))
		{
			M6Test.Reset();
			FinishTest(bPass, Summary);
		}
		return;
	}
	Super::Tick(DeltaSeconds);
}

void AGTRunGameMode::FinishLeg()
{
	AGTRunGameState* State = GetRunState();
	if (!State || !State->GetLeg() || State->GetPhase() == EGTLegPhase::Finished)
	{
		return;
	}
	const UGTLegDefinition* Leg = State->GetLeg();
	AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0));
	AGTCarPawn* Car = PC ? PC->GetCar() : nullptr;
	AGTPlayerCharacter* Character = PC ? PC->GetPlayerCharacter() : nullptr;

	FGTLegResult Result;
	Result.LegId = Leg->LegId;
	Result.LegNumber = Leg->LegNumber;
	Result.Mission = Leg->Mission;
	Result.bCompleted = State->IsMissionSatisfied() && !State->IsMissionFailed();
	Result.TimeSeconds = State->GetLegTime();
	Result.ParTimeSeconds = Leg->ParTimeSeconds;
	Result.bOvertime = State->IsOvertime();
	Result.CheckpointsCleared = State->GetCheckpointsCleared();
	Result.CheckpointCount = State->GetCheckpointCount();
	Result.PhotosTaken = State->GetPhotosTaken();
	switch (Leg->Mission)
	{
	case EGTMissionType::Endurance:
		Result.MissionText = Result.bCompleted ? TEXT("Made it inside the limit") : TEXT("Over the limit: did not finish");
		break;
	case EGTMissionType::Photograph:
		Result.MissionText = Result.bCompleted ? FString::Printf(TEXT("Photographed the %s"), *Leg->PhotoSubjectName) : FString::Printf(TEXT("No picture of the %s"), *Leg->PhotoSubjectName);
		break;
	default:
		Result.MissionText = Result.bOvertime ? TEXT("Extracted, over the limit") : (Result.TimeSeconds <= Leg->ParTimeSeconds ? TEXT("Extracted inside par") : TEXT("Extracted"));
		break;
	}
	auto AddHaul = [&Result](const UGTInventoryComponent* Inventory)
	{
		if (!Inventory)
		{
			return;
		}
		for (const FGTItemStack& Stack : Inventory->Items)
		{
			FGTItemStack* Existing = Result.Haul.FindByPredicate([&Stack](const FGTItemStack& S) { return S.ItemId == Stack.ItemId; });
			if (Existing)
			{
				Existing->Count += Stack.Count;
			}
			else
			{
				Result.Haul.Add(Stack);
			}
			Result.HaulWeightKg += GTItems::WeightKg(Stack.ItemId) * Stack.Count;
			Result.HaulValue += GTItems::BasePrice(Stack.ItemId) * Stack.Count;
		}
	};
	AddHaul(Car ? Car->GetBoot() : nullptr);
	AddHaul(Character ? Character->GetInventory() : nullptr);
	Result.Rank = Leg->RankForTime(Result.TimeSeconds);
	Result.RivalCount = Leg->RivalTimesSeconds.Num();

	if (UGTRunSubsystem* Run = GetGameInstance() ? GetGameInstance()->GetSubsystem<UGTRunSubsystem>() : nullptr)
	{
		Run->ScoreResult(Result, Leg);   // the tour's rivals, the placing, the points and the prize
		Run->CaptureFromPawns(Car, Character);   // the haul, the loadout and the condition travel to the base
		Run->RecordResult(Result);
		Run->SaveToSlot();
	}
	State->FinishLeg(Result);
	++LegsFinished;

	// Freeze the car under the results screen.
	if (Car)
	{
		if (PC)
		{
			Car->DisableInput(PC);
		}
		Car->ResetDrivingInputs();
		if (UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement())
		{
			Move->SetHandbrakeInput(true);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AGTRunGameMode: leg finished: %s"), *Result.Describe());
}

void AGTRunGameMode::ContinueAfterLeg()
{
	const AGTRunGameState* State = GetRunState();
	if (!State || State->GetPhase() != EGTLegPhase::Finished)
	{
		return;
	}
	const FString BasePath = TEXT("/Game/GrandTour/Base/L_Base");
	if (FPackageName::DoesPackageExist(BasePath))
	{
		UE_LOG(LogTemp, Display, TEXT("AGTRunGameMode: continue -> the base"));
		UGameplayStatics::OpenLevel(this, FName(*BasePath));
		return;
	}
	const FString MapName = UGameplayStatics::GetCurrentLevelName(this, true);
	UE_LOG(LogTemp, Display, TEXT("AGTRunGameMode: continue -> reloading %s (no base map: run Art/setup_m4_base.bat)"), *MapName);
	UGameplayStatics::OpenLevel(this, FName(*MapName));
}
