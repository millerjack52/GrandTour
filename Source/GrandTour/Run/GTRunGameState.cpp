#include "Run/GTRunGameState.h"

#include "Core/GTPlayerController.h"
#include "Run/GTLegActors.h"
#include "Run/GTLegDefinition.h"
#include "Run/GTPhotoSubject.h"
#include "Vehicle/GTCarPawn.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

AGTRunGameState::AGTRunGameState()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;
}

AGTCarPawn* AGTRunGameState::FindPlayerCar() const
{
	if (const AGTPlayerController* PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(this, 0)))
	{
		if (PC->GetCar())
		{
			return PC->GetCar();
		}
		return Cast<AGTCarPawn>(PC->GetPawn());
	}
	return nullptr;
}

void AGTRunGameState::SetLeg(UGTLegDefinition* InLeg, const FVector& StartLocation)
{
	Leg = InLeg;
	Checkpoints.Reset();
	PhotoSubjects.Reset();
	Extraction = nullptr;
	for (TActorIterator<AGTCheckpoint> It(GetWorld()); It; ++It)
	{
		It->bCleared = false;
		Checkpoints.Add(*It);
	}
	Checkpoints.Sort([](const AGTCheckpoint& A, const AGTCheckpoint& B) { return A.Index < B.Index; });
	for (TActorIterator<AGTExtractionZone> It(GetWorld()); It; ++It)
	{
		Extraction = *It;
		break;
	}
	for (TActorIterator<AGTPhotoSubject> It(GetWorld()); It; ++It)
	{
		PhotoSubjects.Add(*It);
	}
	RoutePoints.Reset();
	RoutePoints.Add(StartLocation);
	for (const AGTCheckpoint* Checkpoint : Checkpoints)
	{
		RoutePoints.Add(Checkpoint->GetActorLocation());
	}
	if (Extraction.IsValid())
	{
		RoutePoints.Add(Extraction->GetActorLocation());
	}
	CheckpointsCleared = 0;
	PhotosTaken = 0;
	LegTime = 0.f;
	Progress = 0.f;
	bOvertime = false;
	ExtractionHold = 0.f;
	bExtractionFired = false;
	ExtractionAttemptsRefused = 0;
	LastRefusal.Reset();
	Result = FGTLegResult();
	Phase = Leg ? EGTLegPhase::Staging : EGTLegPhase::None;
	UE_LOG(LogTemp, Display, TEXT("AGTRunGameState: leg %s (%s) with %d checkpoints, extraction=%d, photo subjects %d, route points %d"),
		Leg ? *Leg->LegId.ToString() : TEXT("none"), Leg ? *UGTLegDefinition::MissionName(Leg->Mission) : TEXT("-"), Checkpoints.Num(), Extraction.IsValid() ? 1 : 0, PhotoSubjects.Num(), RoutePoints.Num());
}

void AGTRunGameState::StartLeg()
{
	if (Phase == EGTLegPhase::Staging)
	{
		Phase = EGTLegPhase::Running;
		LegTime = 0.f;
		UE_LOG(LogTemp, Display, TEXT("AGTRunGameState: leg started"));
	}
}

void AGTRunGameState::FinishLeg(const FGTLegResult& InResult)
{
	Result = InResult;
	Phase = EGTLegPhase::Finished;
}

void AGTRunGameState::ClearCheckpoint(int32 Index)
{
	if (!Checkpoints.IsValidIndex(Index))
	{
		return;
	}
	Checkpoints[Index]->bCleared = true;
	CheckpointsCleared = Index + 1;
	UE_LOG(LogTemp, Display, TEXT("AGTRunGameState: checkpoint %d/%d at %.1f s"), CheckpointsCleared, Checkpoints.Num(), LegTime);
}

void AGTRunGameState::RegisterPhotoSubject(AGTPhotoSubject* Subject)
{
	if (Subject && !PhotoSubjects.Contains(Subject))
	{
		PhotoSubjects.Add(Subject);
	}
}

void AGTRunGameState::NotifyPhotographed(AGTPhotoSubject* Subject)
{
	RegisterPhotoSubject(Subject);
	++PhotosTaken;
	UE_LOG(LogTemp, Display, TEXT("AGTRunGameState: photograph %d/%d at %.1f s (%s)"), PhotosTaken, GetPhotosRequired(), LegTime, Subject ? *Subject->SubjectName : TEXT("?"));
}

int32 AGTRunGameState::GetPhotosRequired() const
{
	return Leg && Leg->Mission == EGTMissionType::Photograph ? FMath::Max(1, Leg->PhotosRequired) : 0;
}

bool AGTRunGameState::IsMissionSatisfied() const
{
	if (!AllCheckpointsCleared())
	{
		return false;
	}
	return PhotosTaken >= GetPhotosRequired();
}

bool AGTRunGameState::IsMissionFailed() const
{
	return Leg && Leg->Mission == EGTMissionType::Endurance && bOvertime;
}

FString AGTRunGameState::GetExtractionRefusal() const
{
	if (!AllCheckpointsCleared())
	{
		return FString::Printf(TEXT("checkpoint %d first"), CheckpointsCleared + 1);
	}
	if (PhotosTaken < GetPhotosRequired())
	{
		return FString::Printf(TEXT("photograph the %s first"), Leg ? *Leg->PhotoSubjectName : TEXT("subject"));
	}
	return FString();
}

FString AGTRunGameState::GetMissionLine() const
{
	if (!Leg)
	{
		return FString();
	}
	if (IsMissionFailed())
	{
		return TEXT("OVER THE LIMIT: no result");
	}
	if (Leg->Mission == EGTMissionType::Photograph)
	{
		return FString::Printf(TEXT("Photograph the %s   %d / %d"), *Leg->PhotoSubjectName, PhotosTaken, GetPhotosRequired());
	}
	if (Leg->Mission == EGTMissionType::Endurance && Leg->TimeLimitSeconds > 0.f)
	{
		const float Left = FMath::Max(0.f, Leg->TimeLimitSeconds - LegTime);
		return FString::Printf(TEXT("Make it inside the limit   %d:%02d left"), FMath::FloorToInt(Left) / 60, FMath::FloorToInt(Left) % 60);
	}
	return FString();
}

AGTCheckpoint* AGTRunGameState::GetNextCheckpoint() const
{
	return Checkpoints.IsValidIndex(CheckpointsCleared) ? Checkpoints[CheckpointsCleared].Get() : nullptr;
}

float AGTRunGameState::GetExtractionProgress() const
{
	return Extraction.IsValid() && Extraction->HoldSeconds > 0.f ? FMath::Clamp(ExtractionHold / Extraction->HoldSeconds, 0.f, 1.f) : 0.f;
}

float AGTRunGameState::ProgressAt(const FVector& WorldLocation) const
{
	const int32 Segments = RoutePoints.Num() - 1;
	if (Segments <= 0)
	{
		return 0.f;
	}
	const int32 Segment = FMath::Clamp(CheckpointsCleared, 0, Segments - 1);
	const FVector A = RoutePoints[Segment];
	const FVector B = RoutePoints[Segment + 1];
	const FVector AB = B - A;
	const float Length2 = AB.SizeSquared2D();
	const float T = Length2 > 1.f ? FMath::Clamp(FVector::DotProduct(FVector(WorldLocation - A), AB) / Length2, 0.f, 1.f) : 0.f;
	return FMath::Clamp((Segment + T) / Segments, 0.f, 1.f);
}

bool AGTRunGameState::GetObjectiveBearing(float& OutDistance, float& OutBearing) const
{
	const AGTCarPawn* Car = FindPlayerCar();
	AActor* Target = GetNextCheckpoint();
	if (!Target && Extraction.IsValid())
	{
		Target = Extraction.Get();
	}
	if (!Car || !Target)
	{
		return false;
	}
	const FVector To = Target->GetActorLocation() - Car->GetActorLocation();
	OutDistance = To.Size2D();
	const FVector Forward = Car->GetActorForwardVector();
	const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(To.Y, To.X) - FMath::Atan2(Forward.Y, Forward.X));
	OutBearing = FMath::UnwindDegrees(Yaw);
	return true;
}

void AGTRunGameState::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (Phase == EGTLegPhase::None || Phase == EGTLegPhase::Finished)
	{
		return;
	}
	AGTCarPawn* Car = FindPlayerCar();
	if (!Car)
	{
		return;
	}
	const FVector CarLocation = Car->GetActorLocation();
	const float Speed = Car->GetVelocity().Size2D();
	if (Phase == EGTLegPhase::Staging)
	{
		if (Speed > StartSpeed)
		{
			StartLeg();
		}
		else
		{
			return;
		}
	}

	LegTime += DeltaSeconds;
	if (Leg && Leg->TimeLimitSeconds > 0.f && LegTime > Leg->TimeLimitSeconds && !bOvertime)
	{
		bOvertime = true;
		UE_LOG(LogTemp, Display, TEXT("AGTRunGameState: over the time limit (%.0f s)%s"), Leg->TimeLimitSeconds, IsMissionFailed() ? TEXT(": did not finish") : TEXT(""));
	}

	// The next checkpoint in order; later ones wait.
	if (AGTCheckpoint* Next = GetNextCheckpoint())
	{
		if (Next->ContainsPoint(CarLocation))
		{
			ClearCheckpoint(CheckpointsCleared);
		}
	}
	Progress = ProgressAt(CarLocation);

	// Extraction: stop inside with the mission met and hold. A failed endurance leg still ends here, as a did-not-finish.
	if (Extraction.IsValid() && !bExtractionFired)
	{
		const bool bInside = Extraction->ContainsPoint(CarLocation);
		const AGTPlayerController* PC = Cast<AGTPlayerController>(Car->GetController());
		const bool bDriving = PC && PC->IsDriving();
		if (bInside && bDriving && Speed < Extraction->StopSpeed)
		{
			if (IsMissionSatisfied())
			{
				ExtractionHold = FMath::Max(0.f, ExtractionHold) + DeltaSeconds;
				Extraction->HoldProgress = GetExtractionProgress();
				if (ExtractionHold >= Extraction->HoldSeconds)
				{
					bExtractionFired = true;
					UE_LOG(LogTemp, Display, TEXT("AGTRunGameState: extraction complete at %.1f s%s"), LegTime, IsMissionFailed() ? TEXT(" (did not finish)") : TEXT(""));
					OnExtractionReady.Broadcast();
				}
			}
			else if (ExtractionHold == 0.f)
			{
				++ExtractionAttemptsRefused;
				ExtractionHold = -1.f;   // one refusal logged per visit
				LastRefusal = GetExtractionRefusal();
				UE_LOG(LogTemp, Display, TEXT("AGTRunGameState: extraction refused, %s (%d/%d checkpoints, %d/%d photos)"), *LastRefusal, CheckpointsCleared, Checkpoints.Num(), PhotosTaken, GetPhotosRequired());
			}
		}
		else
		{
			ExtractionHold = 0.f;
			Extraction->HoldProgress = 0.f;
		}
	}
}

FString AGTRunGameState::Describe() const
{
	return FString::Printf(TEXT("phase=%d time=%.1f checkpoints=%d/%d photos=%d/%d progress=%.2f overtime=%d failed=%d extractionHold=%.2f refused=%d"),
		static_cast<int32>(Phase), LegTime, CheckpointsCleared, Checkpoints.Num(), PhotosTaken, GetPhotosRequired(), Progress, bOvertime ? 1 : 0, IsMissionFailed() ? 1 : 0, ExtractionHold, ExtractionAttemptsRefused);
}
