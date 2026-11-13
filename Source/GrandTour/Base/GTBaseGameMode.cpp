#include "Base/GTBaseGameMode.h"

#include "Character/GTPlayerCharacter.h"
#include "Core/GTPlayerController.h"
#include "Core/GTRunSubsystem.h"
#include "Run/GTLegDefinition.h"
#include "Vehicle/GTCarPawn.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"

AGTBaseGameMode::AGTBaseGameMode()
{
}

UGTRunSubsystem* AGTBaseGameMode::Run() const
{
	return GetGameInstance() ? GetGameInstance()->GetSubsystem<UGTRunSubsystem>() : nullptr;
}

void AGTBaseGameMode::BeginPlay()
{
	Super::BeginPlay();
	if (FParse::Param(FCommandLine::Get(), TEXT("GTLoopTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST loop test continues at the base"));
		M4Test = MakeUnique<FGTM4TestRunner>(GetWorld(), EGTM4Test::Loop);
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTBaseTest")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTBaseTest at the base"));
		M4Test = MakeUnique<FGTM4TestRunner>(GetWorld(), EGTM4Test::Base);
	}
	else if (FParse::Param(FCommandLine::Get(), TEXT("GTBaseShots")))
	{
		UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST starting GTBaseShots"));
		M4Test = MakeUnique<FGTM4TestRunner>(GetWorld(), EGTM4Test::Screenshots);
	}
}

void AGTBaseGameMode::Arrive()
{
	bArrived = true;
	AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0));
	AGTCarPawn* Car = PC ? Cast<AGTCarPawn>(PC->GetPawn()) : nullptr;
	UGTRunSubsystem* RunSub = Run();
	if (!PC || !Car || !RunSub)
	{
		UE_LOG(LogTemp, Warning, TEXT("AGTBaseGameMode: no car or run subsystem at arrival"));
		return;
	}
	// A fresh start restores the save; a level change already carries the snapshot in memory.
	if (!RunSub->HasSnapshot() && !FParse::Param(FCommandLine::Get(), TEXT("GTNoLoad")) && RunSub->HasSaveInSlot())
	{
		bLoadedFromSave = RunSub->LoadFromSlot();
	}
	RunSub->ApplyToPawns(Car, PC->GetPlayerCharacter());
	if (bSaveOnArrival)
	{
		RunSub->CaptureFromPawns(Car, PC->GetPlayerCharacter());
		RunSub->SaveToSlot();
	}
	// On foot beside the car, no blend.
	const float Blend = PC->CameraBlendTime;
	PC->CameraBlendTime = 0.f;
	PC->ExitCar();
	PC->CameraBlendTime = Blend;
	UE_LOG(LogTemp, Display, TEXT("AGTBaseGameMode: arrived (loadedFromSave=%d) %s"), bLoadedFromSave ? 1 : 0, *RunSub->Describe());
}

void AGTBaseGameMode::Tick(float DeltaSeconds)
{
	if (!bArrived)
	{
		Arrive();   // the player's pawn exists by the first tick
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
	Super::Tick(DeltaSeconds);
}

bool AGTBaseGameMode::Depart()
{
	if (bDeparted)
	{
		return false;
	}
	AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0));
	UGTRunSubsystem* RunSub = Run();
	if (!PC || !PC->GetCar() || !RunSub)
	{
		return false;
	}
	UGTLegDefinition* Leg = RunSub->ResolveNextLeg();
	if (!Leg)
	{
		if (!bRefusedLogged)
		{
			bRefusedLogged = true;
			UE_LOG(LogTemp, Display, TEXT("AGTBaseGameMode: the gate refuses: the tour is over (start a new one at the briefing board)"));
		}
		return false;
	}
	bDeparted = true;
	RunSub->CaptureFromPawns(PC->GetCar(), PC->GetPlayerCharacter());
	RunSub->SetPendingLeg(Leg);
	RunSub->SaveToSlot();
	FString Map = Leg->MapPath.IsEmpty() ? TEXT("/Game/GrandTour/Legs/L_Leg01") : Leg->MapPath;
	if (!FPackageName::DoesPackageExist(Map))
	{
		// A leg whose map is not built yet (run Art/setup_m5_legs.bat) runs on Leg 1's map with its own definition.
		UE_LOG(LogTemp, Warning, TEXT("AGTBaseGameMode: map %s is missing; running %s on L_Leg01"), *Map, *Leg->LegId.ToString());
		Map = TEXT("/Game/GrandTour/Legs/L_Leg01");
	}
	UE_LOG(LogTemp, Display, TEXT("AGTBaseGameMode: departing to %s (%s, %s)"), *Map, *Leg->LegId.ToString(), *UGTLegDefinition::MissionName(Leg->Mission));
	UGameplayStatics::OpenLevel(this, FName(*Map));
	return true;
}
