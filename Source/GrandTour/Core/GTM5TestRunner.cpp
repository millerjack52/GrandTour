#include "Core/GTM5TestRunner.h"

#include "Character/GTPlayerCharacter.h"
#include "Core/GTPlayerController.h"
#include "Core/GTRunSubsystem.h"
#include "Crafting/GTCraftingStation.h"
#include "Interaction/GTInteractionComponent.h"
#include "Race/GTStandings.h"
#include "Race/GTTourDefinition.h"
#include "Run/GTLegActors.h"
#include "Run/GTLegDefinition.h"
#include "Run/GTPhotoSubject.h"
#include "Run/GTRunGameMode.h"
#include "Run/GTRunGameState.h"
#include "Vehicle/GTCarPawn.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

FGTM5TestRunner::FGTM5TestRunner(UWorld* InWorld)
	: World(InWorld)
{
}

void FGTM5TestRunner::Log(const FString& Line) const
{
	UE_LOG(LogTemp, Display, TEXT("GTDRIVETEST m5 t=%.1f step %d: %s"), Elapsed, Step, *Line);
}

void FGTM5TestRunner::Finish(bool bInPass, const FString& InSummary)
{
	bDone = true;
	bPass = bInPass;
	Summary = InSummary;
}

void FGTM5TestRunner::Next()
{
	++Step;
	StepTime = 0.f;
	bStepStarted = false;
}

bool FGTM5TestRunner::StepTimedOut(float Seconds, const TCHAR* What)
{
	if (StepTime > Seconds)
	{
		Fail(FString::Printf(TEXT("timed out waiting for %s (%s)"), What, State.IsValid() ? *State->Describe() : TEXT("no state")));
		return true;
	}
	return false;
}

FVector FGTM5TestRunner::StartLocal(const FVector& Local) const
{
	return StartTransform.TransformPosition(Local);
}

void FGTM5TestRunner::TeleportCar(const FVector& Location)
{
	if (!Car.IsValid())
	{
		return;
	}
	Car->SetActorLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
	Car->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	Car->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
	Throttle(false);
}

void FGTM5TestRunner::Throttle(bool bOn)
{
	if (UChaosWheeledVehicleMovementComponent* Move = Car.IsValid() ? Car->GetChaosMovement() : nullptr)
	{
		Move->SetThrottleInput(bOn ? 1.f : 0.f);
		Move->SetHandbrakeInput(!bOn);
	}
}

void FGTM5TestRunner::TeleportCharacter(const FVector& GroundLocation, const FVector& LookAt)
{
	if (!Character.IsValid() || !PC.IsValid())
	{
		return;
	}
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	Character->SetActorLocation(GroundLocation + FVector(0.f, 0.f, HalfHeight + 2.f), false, nullptr, ETeleportType::TeleportPhysics);
	PC->SetControlRotation((LookAt - Character->GetPawnViewLocation()).Rotation());
}

bool FGTM5TestRunner::ExitCar()
{
	if (!PC.IsValid())
	{
		return false;
	}
	if (!PC->IsDriving())
	{
		Character = PC->GetPlayerCharacter();
		return Character.IsValid();
	}
	if (!PC->ExitCar())
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

bool FGTM5TestRunner::EnterCar()
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

UGTLegDefinition* FGTM5TestRunner::MakeLeg(int32 DefaultIndex, float Par, float Limit)
{
	UGTLegDefinition* Leg = NewObject<UGTLegDefinition>(GameMode.Get(), NAME_None, RF_Transient);
	Leg->ApplyDefault(DefaultIndex);
	Leg->Conditions.Reset();
	Leg->ParTimeSeconds = Par;
	Leg->TimeLimitSeconds = Limit;
	return Leg;
}

bool FGTM5TestRunner::Setup()
{
	PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(World.Get(), 0));
	Car = PC.IsValid() ? (PC->GetCar() ? PC->GetCar() : Cast<AGTCarPawn>(PC->GetPawn())) : nullptr;
	GameMode = Cast<AGTRunGameMode>(World->GetAuthGameMode());
	State = World->GetGameState<AGTRunGameState>();
	if (!PC.IsValid() || !Car.IsValid() || !GameMode.IsValid() || !State.IsValid())
	{
		Fail(TEXT("player 0 is not an AGTPlayerController with an AGTCarPawn under the run game mode"));
		return false;
	}
	Car->DisableInput(PC.Get());
	Car->ResetDrivingInputs();
	Character = PC->GetPlayerCharacter();
	if (Character.IsValid())
	{
		Character->DisableInput(PC.Get());
	}
	Run = World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UGTRunSubsystem>() : nullptr;
	if (!Run.IsValid())
	{
		Fail(TEXT("no UGTRunSubsystem"));
		return false;
	}
	StartTransform = FTransform(FRotator(0.f, Car->GetActorRotation().Yaw, 0.f), Car->GetActorLocation());
	Log(FString::Printf(TEXT("car at %s yaw %.0f driving=%d | %s"), *Car->GetActorLocation().ToCompactString(), Car->GetActorRotation().Yaw, PC->IsDriving() ? 1 : 0, *Run->Describe()));
	return true;
}

bool FGTM5TestRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
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
		// Let the car land and stop before anything reads its pose.
		const APawn* Pawn = UGameplayStatics::GetPlayerPawn(World.Get(), 0);
		if (Elapsed < 1.5f || (Pawn && FMath::Abs(Pawn->GetVelocity().Z) > 5.f))
		{
			return false;
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
	if (!Car.IsValid() || !PC.IsValid() || !State.IsValid())
	{
		Fail(TEXT("car, controller or run state vanished"));
	}
	else
	{
		TickTour(DeltaSeconds);
	}
	if (Elapsed > 90.f && !bDone)
	{
		Fail(FString::Printf(TEXT("overall timeout at step %d"), Step));
	}
	bOutPass = bPass;
	OutSummary = Summary;
	return bDone;
}

void FGTM5TestRunner::TickTour(float DeltaSeconds)
{
	switch (Step)
	{
	case 0:   // the tour, its legs and missions; the rivals' draw; placings and points
	{
		Run->ResetCampaign();
		Run->DeleteSave();
		Tour = Run->ResolveTour();
		const UGTLegDefinition* Leg0 = Run->ResolveNextLeg();
		const UGTLegDefinition* Leg2 = Run->ResolveLeg(2);
		const UGTLegDefinition* Leg4 = Run->ResolveLeg(4);
		bTourResolved = Tour.IsValid() && Tour->LegCount() == 5 && Tour->Rivals.Num() == 4 && !Run->IsTourComplete()
			&& Leg0 && Leg0->LegNumber == 1 && Leg0->Mission == EGTMissionType::TimeTrial
			&& Leg2 && Leg2->Mission == EGTMissionType::Photograph && !Leg2->PhotoSubjectName.IsEmpty() && !Leg2->MissionBrief.IsEmpty()
			&& Leg4 && Leg4->Mission == EGTMissionType::Endurance && Leg4->TimeLimitSeconds > 0.f
			&& Run->ResolveLeg(5) == nullptr && Run->GetCurrency() == Tour->StartingCredits;
		Log(FString::Printf(TEXT("tour: %s | leg0 %s | leg2 %s | leg4 %s | credits %d"), Tour.IsValid() ? *Tour->Describe() : TEXT("none"),
			Leg0 ? *Leg0->Describe() : TEXT("-"), Leg2 ? *Leg2->Describe() : TEXT("-"), Leg4 ? *Leg4->Describe() : TEXT("-"), Run->GetCurrency()));
		if (!bTourResolved)
		{
			Fail(TEXT("the tour, its legs or their missions did not resolve"));
			return;
		}

		// The draw: the same inputs give the same outcome, other seeds give other times, every time stays believable.
		const FGTRivalLegOutcome A1 = GTStandings::SimulateRival(Tour->Rivals[0], *Leg0, 0, 0, 12345);
		const FGTRivalLegOutcome A2 = GTStandings::SimulateRival(Tour->Rivals[0], *Leg0, 0, 0, 12345);
		int32 Different = 0;
		for (int32 Seed = 1; Seed <= 20; ++Seed)
		{
			if (!FMath::IsNearlyEqual(GTStandings::SimulateRival(Tour->Rivals[0], *Leg0, 0, 0, Seed).TimeSeconds, A1.TimeSeconds, 0.01f))
			{
				++Different;
			}
		}
		bDeterministic = FMath::IsNearlyEqual(A1.TimeSeconds, A2.TimeSeconds, 0.001f) && A1.bFinished == A2.bFinished && Different >= 15;
		bBounded = true;
		int32 EnduranceDrops = 0;
		int32 TimeTrialDrops = 0;
		const int32 Seeds = 200;
		const UGTLegDefinition* Leg1 = Run->ResolveLeg(1);
		for (int32 Seed = 1; Seed <= Seeds; ++Seed)
		{
			for (int32 LegIndex = 0; LegIndex < 5; ++LegIndex)
			{
				const UGTLegDefinition* Leg = Run->ResolveLeg(LegIndex);
				for (int32 RivalIndex = 0; RivalIndex < Tour->Rivals.Num(); ++RivalIndex)
				{
					const FGTRivalLegOutcome O = GTStandings::SimulateRival(Tour->Rivals[RivalIndex], *Leg, LegIndex, RivalIndex, Seed);
					const float Expected = GTStandings::ExpectedTime(Tour->Rivals[RivalIndex], *Leg);
					if (O.TimeSeconds < Expected * 0.6f || O.TimeSeconds > Expected * 1.9f)
					{
						bBounded = false;
					}
				}
			}
			EnduranceDrops += GTStandings::SimulateRival(Tour->Rivals[3], *Leg1, 1, 3, Seed).bFinished ? 0 : 1;   // grit 0.8 on an endurance leg: about one in five
			TimeTrialDrops += GTStandings::SimulateRival(Tour->Rivals[2], *Leg0, 0, 2, Seed).bFinished ? 0 : 1;   // grit 0.98 on a time trial: almost never
		}
		EnduranceDropRate = static_cast<float>(EnduranceDrops) / Seeds;
		TimeTrialDropRate = static_cast<float>(TimeTrialDrops) / Seeds;
		const bool bDropsOk = EnduranceDropRate >= 0.08f && EnduranceDropRate <= 0.35f && TimeTrialDropRate <= 0.05f;

		// Placings: quicker than everyone is first with full points; slower than everyone is last among the finishers; a DNF scores nothing.
		TArray<FGTRivalLegOutcome> Rivals;
		int32 Points = 0;
		const int32 First = GTStandings::PlaceLeg(*Tour, *Leg0, 0, 777, Leg0->ParTimeSeconds * 0.5f, true, Rivals, Points);
		const bool bFirstOk = First == 1 && Points == Tour->PointsForPlace(1) && Rivals.Num() == 4;
		int32 Finished = 0;
		for (const FGTRivalLegOutcome& R : Rivals)
		{
			Finished += R.bFinished ? 1 : 0;
		}
		const int32 Last = GTStandings::PlaceLeg(*Tour, *Leg0, 0, 777, Leg0->ParTimeSeconds * 10.f, true, Rivals, Points);
		const bool bLastOk = Last == Finished + 1 && Points == Tour->PointsForPlace(Finished + 1);
		const int32 Dnf = GTStandings::PlaceLeg(*Tour, *Leg0, 0, 777, Leg0->ParTimeSeconds, false, Rivals, Points);
		const bool bDnfOkHere = Dnf == Finished + 1 && Points == 0;
		// Everyone who finished holds a distinct place from 1; the rival places are consistent with the player's.
		TArray<int32> Places;
		for (const FGTRivalLegOutcome& R : Rivals)
		{
			if (R.bFinished)
			{
				Places.Add(R.Place);
			}
		}
		Places.Sort();
		bool bDistinct = true;
		for (int32 Index = 0; Index < Places.Num(); ++Index)
		{
			bDistinct &= Places[Index] == Index + 1;   // the player did not finish here, so the rivals fill 1..N
		}
		bPlacingOk = bFirstOk && bLastOk && bDnfOkHere && bDistinct;
		Log(FString::Printf(TEXT("draw: A1=%.1f A2=%.1f finished=%d differentSeeds=%d/20 bounded=%d enduranceDrop=%.2f timeTrialDrop=%.2f | placing: first=%d last=%d (finishers %d) dnf=%d distinct=%d"),
			A1.TimeSeconds, A2.TimeSeconds, A1.bFinished ? 1 : 0, Different, bBounded ? 1 : 0, EnduranceDropRate, TimeTrialDropRate, First, Last, Finished, Dnf, bDistinct ? 1 : 0));
		if (!bDeterministic || !bBounded || !bDropsOk || !bPlacingOk)
		{
			Fail(TEXT("the rivals' draw or the placings are off"));
			return;
		}
		Next();
		break;
	}
	case 1:   // a photograph leg in the world: a checkpoint, the zone, two subjects off to the sides
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		const FRotator Facing = StartTransform.Rotator();
		AGTCheckpoint* CP1 = World->SpawnActor<AGTCheckpoint>(AGTCheckpoint::StaticClass(), StartLocal(FVector(3000.f, 0.f, 250.f)), Facing, Params);
		AGTExtractionZone* Extraction = World->SpawnActor<AGTExtractionZone>(AGTExtractionZone::StaticClass(), StartLocal(FVector(9000.f, 0.f, 250.f)), Facing, Params);
		SubjectA = World->SpawnActor<AGTPhotoSubject>(AGTPhotoSubject::StaticClass(), StartLocal(FVector(5000.f, 4000.f, 100.f)), FRotator(0.f, Facing.Yaw + 90.f, 0.f), Params);
		SubjectB = World->SpawnActor<AGTPhotoSubject>(AGTPhotoSubject::StaticClass(), StartLocal(FVector(5000.f, -4000.f, 100.f)), FRotator(0.f, Facing.Yaw - 90.f, 0.f), Params);
		if (!CP1 || !Extraction || !SubjectA.IsValid() || !SubjectB.IsValid())
		{
			Fail(TEXT("could not spawn the leg actors"));
			return;
		}
		CP1->Index = 1;
		UGTLegDefinition* Leg = MakeLeg(2, 60.f, 0.f);   // Leg 3, The Hide: photograph the bear
		GameMode->SetLeg(Leg);
		const FString MissionLine = State->GetMissionLine();
		bPhotoLegSet = State->GetPhase() == EGTLegPhase::Staging && State->GetCheckpointCount() == 1 && State->GetExtraction() != nullptr && State->GetPhotoSubjectCount() == 2
			&& State->GetPhotosRequired() == 1 && !State->IsMissionSatisfied() && MissionLine.Contains(TEXT("Photograph"));
		Log(FString::Printf(TEXT("photo leg: %s | line '%s' | A %s | B %s"), *State->Describe(), *MissionLine, *SubjectA->Describe(), *SubjectB->Describe()));
		if (!bPhotoLegSet)
		{
			Fail(TEXT("the photograph leg did not stage with its subjects"));
			return;
		}
		Throttle(true);
		Next();
		break;
	}
	case 2:   // the timer starts on the move; through the checkpoint and into the zone by teleport
		if (State->GetPhase() == EGTLegPhase::Running)
		{
			if (const AGTCheckpoint* CP = State->GetNextCheckpoint())
			{
				TeleportCar(FVector(CP->GetActorLocation().X, CP->GetActorLocation().Y, Car->GetActorLocation().Z));
				State->Tick(0.f);
			}
			const FVector Zone = State->GetExtraction()->GetActorLocation();
			TeleportCar(FVector(Zone.X, Zone.Y, Car->GetActorLocation().Z));
			Log(FString::Printf(TEXT("in the zone without the picture: %s"), *State->Describe()));
			Next();
		}
		else if (StepTimedOut(6.f, TEXT("the timer to start")))
		{
			return;
		}
		break;
	case 3:   // the zone refuses the car; get out and stand 20 m from subject A, looking at it
		if (State->ExtractionAttemptsRefused >= 1)
		{
			RefusalText = State->LastRefusal;
			bZoneRefused = State->GetPhase() == EGTLegPhase::Running && State->AllCheckpointsCleared() && RefusalText.Contains(TEXT("photograph"));
			Log(FString::Printf(TEXT("refused: '%s' ok=%d"), *RefusalText, bZoneRefused ? 1 : 0));
			if (!bZoneRefused)
			{
				Fail(TEXT("the zone did not refuse for the missing picture"));
				return;
			}
			if (!ExitCar())
			{
				Fail(TEXT("could not get out"));
				return;
			}
			TeleportCharacter(StartLocal(FVector(3000.f, 4000.f, 0.f)), SubjectA->GetActorLocation());
			Character->GetInteraction()->SetHoldInput(true);
			Next();
		}
		else if (StepTimedOut(5.f, TEXT("the zone's refusal")))
		{
			return;
		}
		break;
	case 4:   // the offer from range, the hold, the picture
	{
		const UGTInteractionComponent* Interaction = Character.IsValid() ? Character->GetInteraction() : nullptr;
		if (Interaction && Interaction->IsOfferAvailable() && Interaction->GetPrompt().Contains(TEXT("Photograph")))
		{
			bPhotoOffered = true;
			PhotoPrompt = Interaction->GetPrompt();
		}
		if (State->GetPhotosTaken() >= 1)
		{
			Character->GetInteraction()->SetHoldInput(false);
			bPhotographed = SubjectA.IsValid() && SubjectA->IsPhotographed() && State->IsMissionSatisfied() && bPhotoOffered;
			Log(FString::Printf(TEXT("photographed: offered=%d prompt='%s' %s | %s"), bPhotoOffered ? 1 : 0, *PhotoPrompt, *SubjectA->Describe(), *State->Describe()));
			if (!bPhotographed)
			{
				Fail(TEXT("the picture was not taken through the offer"));
				return;
			}
			// Now spook subject B: stand 5 m from it.
			SubjectBBefore = SubjectB->GetActorLocation();
			TeleportCharacter(StartLocal(FVector(5000.f, -3500.f, 0.f)), SubjectBBefore);
			Next();
		}
		else if (StepTimedOut(6.f, TEXT("the photograph")))
		{
			Log(FString::Printf(TEXT("interaction: %s"), Interaction ? *Interaction->Describe() : TEXT("none")));
			return;
		}
		break;
	}
	case 5:   // subject B moves off
		if (SubjectB.IsValid() && SubjectB->TimesSpooked >= 1)
		{
			FledDistance = FVector::Dist2D(SubjectB->GetActorLocation(), SubjectBBefore);
			bFled = FledDistance >= 3000.f && !SubjectB->IsPhotographed();
			Log(FString::Printf(TEXT("fled %.1f m: %s"), FledDistance / 100.f, *SubjectB->Describe()));
			if (!bFled)
			{
				Fail(TEXT("the subject did not move off when approached"));
				return;
			}
			if (!EnterCar())
			{
				Fail(TEXT("could not get back in"));
				return;
			}
			Next();
		}
		else if (StepTimedOut(3.f, TEXT("the subject to flee")))
		{
			return;
		}
		break;
	case 6:   // back in the zone: the leg finishes with the verdict, the placing, the points and the prize
		if (State->GetPhase() == EGTLegPhase::Finished)
		{
			const FGTLegResult& R = State->GetResult();
			const TArray<FGTStandingRow> Rows = Run->BuildStandings();
			const FGTStandingRow Me = GTStandings::PlayerRow(Rows);
			PhotoPrize = R.PrizeCredits;
			PhotoPoints = R.Points;
			bPhotoResultOk = R.bCompleted && R.Mission == EGTMissionType::Photograph && R.PhotosTaken == 1 && R.MissionText.Contains(TEXT("Photographed"))
				&& R.Rivals.Num() == 4 && R.Rank >= 1 && R.Rank <= 5 && R.Points == Tour->PointsForPlace(R.Rank) && R.Points > 0
				&& R.PrizeCredits == Tour->PrizeForPlace(R.Rank) && Run->GetCurrency() == Tour->StartingCredits + R.PrizeCredits
				&& Run->GetCampaign().CurrentLegIndex == 1 && Rows.Num() == 5 && Me.Points == R.Points && Me.LegsFinished == 1 && !Run->IsTourComplete();
			Log(FString::Printf(TEXT("result: %s | credits %d | table: %d rows, me %d/%d with %d pts"), *R.Describe(), Run->GetCurrency(), Rows.Num(), Me.Place, Rows.Num(), Me.Points));
			if (!bPhotoResultOk)
			{
				Fail(TEXT("the photograph leg's result is wrong"));
				return;
			}
			Next();
		}
		else if (StepTimedOut(8.f, TEXT("the extraction")))
		{
			return;
		}
		break;
	case 7:   // an endurance leg with a 2 s limit: over it, the zone ends the leg as a did-not-finish
		if (!bStepStarted)
		{
			bStepStarted = true;
			UGTLegDefinition* Leg = MakeLeg(1, 60.f, 2.f);   // Leg 2, The Washout
			GameMode->SetLeg(Leg);
			TeleportCar(StartLocal(FVector(0.f, 0.f, Car->GetActorLocation().Z - StartTransform.GetLocation().Z)));
			Throttle(true);
			Log(FString::Printf(TEXT("endurance leg: %s"), *State->Describe()));
		}
		if (State->GetPhase() == EGTLegPhase::Running && State->GetLegTime() > 2.5f)
		{
			if (!State->IsMissionFailed() || !State->GetMissionLine().Contains(TEXT("OVER THE LIMIT")))
			{
				Fail(FString::Printf(TEXT("not failed past the limit: %s line '%s'"), *State->Describe(), *State->GetMissionLine()));
				return;
			}
			if (const AGTCheckpoint* CP = State->GetNextCheckpoint())
			{
				TeleportCar(FVector(CP->GetActorLocation().X, CP->GetActorLocation().Y, Car->GetActorLocation().Z));
				State->Tick(0.f);
			}
			const FVector Zone = State->GetExtraction()->GetActorLocation();
			TeleportCar(FVector(Zone.X, Zone.Y, Car->GetActorLocation().Z));
			Log(FString::Printf(TEXT("over the limit, in the zone: %s line '%s'"), *State->Describe(), *State->GetMissionLine()));
			Next();
		}
		else if (StepTimedOut(8.f, TEXT("the endurance limit")))
		{
			return;
		}
		break;
	case 8:
		if (State->GetPhase() == EGTLegPhase::Finished)
		{
			const FGTLegResult& R = State->GetResult();
			int32 Finished = 0;
			for (const FGTRivalLegOutcome& Rival : R.Rivals)
			{
				Finished += Rival.bFinished ? 1 : 0;
			}
			bDnfOk = !R.bCompleted && R.Mission == EGTMissionType::Endurance && R.bOvertime && R.MissionText.Contains(TEXT("limit")) && R.Points == 0 && R.PrizeCredits == 0
				&& R.Rank == Finished + 1 && Run->GetCurrency() == Tour->StartingCredits + PhotoPrize && Run->GetCampaign().CurrentLegIndex == 2 && Run->GetCampaign().Results.Num() == 2;
			Log(FString::Printf(TEXT("dnf result: %s | credits %d"), *R.Describe(), Run->GetCurrency()));
			if (!bDnfOk)
			{
				Fail(TEXT("the did-not-finish result is wrong"));
				return;
			}
			Next();
		}
		else if (StepTimedOut(8.f, TEXT("the DNF extraction")))
		{
			return;
		}
		break;
	case 9:   // the rest of the tour scored straight into the campaign; the final table, the ending, the save, a new tour from the board
	{
		int32 Prizes = PhotoPrize;
		int32 PointsSum = PhotoPoints;
		for (int32 Index = 2; Index < 5; ++Index)
		{
			const UGTLegDefinition* Leg = Run->ResolveLeg(Index);
			FGTLegResult R;
			R.LegId = Leg->LegId;
			R.LegNumber = Leg->LegNumber;
			R.Mission = Leg->Mission;
			R.bCompleted = true;
			R.MissionText = TEXT("scored by the test");
			R.TimeSeconds = Leg->ParTimeSeconds * 0.8f;
			R.ParTimeSeconds = Leg->ParTimeSeconds;
			Run->ScoreResult(R, Leg);
			Run->RecordResult(R);
			Prizes += R.PrizeCredits;
			PointsSum += R.Points;
		}
		const TArray<FGTStandingRow> Rows = Run->BuildStandings();
		const FGTStandingRow Me = GTStandings::PlayerRow(Rows);
		bool bSorted = true;
		for (int32 Index = 1; Index < Rows.Num(); ++Index)
		{
			bSorted &= Rows[Index - 1].Points >= Rows[Index].Points && Rows[Index].Place == Index + 1;
		}
		Ending = Run->EndingLine();
		bTourEndOk = Run->IsTourComplete() && Run->ResolveNextLeg() == nullptr && Run->GetCampaign().Results.Num() == 5 && Rows.Num() == 5 && bSorted
			&& Me.Points == PointsSum && Me.LegsFinished == 4 && Me.LegsRun == 5 && Run->GetCurrency() == Tour->StartingCredits + Prizes && !Ending.IsEmpty();
		FString Table;
		for (const FGTStandingRow& Row : Rows)
		{
			Table += FString::Printf(TEXT(" %d.%s=%dpts(%d/%d)"), Row.Place, *Row.Name, Row.Points, Row.LegsFinished, Row.LegsRun);
		}
		Log(FString::Printf(TEXT("tour over: complete=%d table[%s] me %d pts credits %d ending '%s'"), Run->IsTourComplete() ? 1 : 0, *Table, Me.Points, Run->GetCurrency(), *Ending));
		if (!bTourEndOk)
		{
			Fail(TEXT("the tour did not end with the right table"));
			return;
		}

		// The save carries the table and the seed; the runtime tour reloads the same.
		const int32 SeedBefore = Run->GetCampaign().Seed;
		const bool bSaved = Run->SaveToSlot();
		Run->ResetCampaign();
		const bool bLoaded = Run->LoadFromSlot();
		const TArray<FGTStandingRow> After = Run->BuildStandings();
		bSaveRoundTrip = bSaved && bLoaded && Run->IsTourComplete() && Run->GetCampaign().Seed == SeedBefore && After.Num() == Rows.Num() && Run->EndingLine() == Ending;
		for (int32 Index = 0; Index < Rows.Num() && Index < After.Num(); ++Index)
		{
			bSaveRoundTrip &= Rows[Index].Name == After[Index].Name && Rows[Index].Points == After[Index].Points;
		}
		Log(FString::Printf(TEXT("save round trip: saved=%d loaded=%d ok=%d | %s"), bSaved ? 1 : 0, bLoaded ? 1 : 0, bSaveRoundTrip ? 1 : 0, *Run->Describe()));
		if (!bSaveRoundTrip)
		{
			Fail(TEXT("the finished tour did not survive the save"));
			return;
		}

		// The briefing board on a finished tour: the final table, the ending and a new tour.
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		AGTBriefingBoard* Board = World->SpawnActor<AGTBriefingBoard>(AGTBriefingBoard::StaticClass(), StartLocal(FVector(-600.f, 600.f, 60.f)), StartTransform.Rotator(), Params);
		TArray<FGTScreenRow> BoardRows;
		if (Board && Character.IsValid())
		{
			Board->BuildRows(Character.Get(), BoardRows);
		}
		int32 NewTourRow = -1;
		bool bOverShown = false;
		for (int32 Index = 0; Index < BoardRows.Num(); ++Index)
		{
			bOverShown |= BoardRows[Index].bHeader && BoardRows[Index].Text.Contains(TEXT("is over"));
			if (!BoardRows[Index].bHeader && BoardRows[Index].Action == AGTBriefingBoard::NewTour && BoardRows[Index].bEnabled)
			{
				NewTourRow = Index;
			}
		}
		const bool bStarted = Board && NewTourRow >= 0 && Board->ActOnRow(Character.Get(), NewTourRow);
		TArray<FGTScreenRow> FreshRows;
		if (Board && Character.IsValid())
		{
			Board->BuildRows(Character.Get(), FreshRows);
		}
		const bool bFreshBriefing = FreshRows.Num() > 3 && FreshRows[0].Text.Contains(TEXT("leg 1 of 5"));
		bNewTourOk = bOverShown && bStarted && !Run->IsTourComplete() && Run->GetCampaign().CurrentLegIndex == 0 && Run->GetCampaign().Results.Num() == 0
			&& Run->GetCurrency() == Tour->StartingCredits && Run->GetCampaign().Seed != SeedBefore && bFreshBriefing && Run->HasSaveInSlot();
		Log(FString::Printf(TEXT("board: rows=%d overShown=%d newTourRow=%d started=%d fresh='%s' | %s"), BoardRows.Num(), bOverShown ? 1 : 0, NewTourRow, bStarted ? 1 : 0,
			FreshRows.Num() > 0 ? *FreshRows[0].Text : TEXT(""), *Run->Describe()));
		Run->DeleteSave();   // the test slot starts empty next run
		if (!bNewTourOk)
		{
			Fail(TEXT("the briefing board did not end the tour and start a new one"));
			return;
		}
		Finish(true, FString::Printf(TEXT("tour: 5 legs resolved with missions; draw deterministic and bounded (endurance drop %.2f, time trial %.2f); placings ok; photo leg refused '%s', offered '%s', photographed, subject fled %.0f m; result +%d pts +%d credits; endurance DNF 0 pts; tour over: '%s'; save round trip; new tour from the board"),
			EnduranceDropRate, TimeTrialDropRate, *RefusalText, *PhotoPrompt, FledDistance / 100.f, PhotoPoints, PhotoPrize, *Ending));
		break;
	}
	default:
		break;
	}
}
