#pragma once

#include "CoreMinimal.h"

class AGTBriefingBoard;
class AGTCarPawn;
class AGTPhotoSubject;
class AGTPlayerCharacter;
class AGTPlayerController;
class AGTRunGameMode;
class AGTRunGameState;
class UGTLegDefinition;
class UGTRunSubsystem;
class UGTTourDefinition;
class UWorld;

/**
 * Scripted headless check for M5 (the tour: leg sequence, mission types, rival standings,
 * ending), driven from AGTRunGameMode::Tick on L_DriveTest with a runtime tour, so no assets
 * are needed. Every step logs a GTDRIVETEST m5 line. In order: the tour and its legs resolve
 * with their missions; the rivals' draw is deterministic, bounded and drops out at the expected
 * rate; placings and points follow the table; a photograph leg in the world refuses the zone
 * until the picture, which is taken on foot from range, while a second subject flees when
 * approached; the result carries the verdict, the placing, the points and the prize; an
 * endurance leg over its limit ends as a did-not-finish worth nothing; the remaining legs are
 * scored to the end of the tour, the final table and the ending line come out and survive a
 * save round trip; the briefing board offers a new tour and starts one.
 */
class FGTM5TestRunner
{
public:
	explicit FGTM5TestRunner(UWorld* InWorld);

	/** Returns true when the test is over; the verdict is in bOutPass / OutSummary. */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	bool Setup();
	void TickTour(float DeltaSeconds);
	void Next();
	void Finish(bool bPass, const FString& Summary);
	void Fail(const FString& Why) { Finish(false, Why); }
	void Log(const FString& Line) const;
	FVector StartLocal(const FVector& Local) const;
	void TeleportCar(const FVector& Location);
	void Throttle(bool bOn);
	void TeleportCharacter(const FVector& GroundLocation, const FVector& LookAt);
	bool ExitCar();
	bool EnterCar();
	bool StepTimedOut(float Seconds, const TCHAR* What);
	UGTLegDefinition* MakeLeg(int32 DefaultIndex, float Par, float Limit);

	TWeakObjectPtr<UWorld> World;
	bool bDone = false;
	bool bPass = false;
	FString Summary;
	int32 Step = -1;
	float StepTime = 0.f;
	float Elapsed = 0.f;
	bool bStepStarted = false;

	TWeakObjectPtr<AGTPlayerController> PC;
	TWeakObjectPtr<AGTCarPawn> Car;
	TWeakObjectPtr<AGTPlayerCharacter> Character;
	TWeakObjectPtr<UGTRunSubsystem> Run;
	TWeakObjectPtr<AGTRunGameMode> GameMode;
	TWeakObjectPtr<AGTRunGameState> State;
	TWeakObjectPtr<UGTTourDefinition> Tour;
	TWeakObjectPtr<AGTPhotoSubject> SubjectA;
	TWeakObjectPtr<AGTPhotoSubject> SubjectB;
	FTransform StartTransform;

	// verdicts
	bool bTourResolved = false;
	bool bDeterministic = false;
	bool bBounded = false;
	float EnduranceDropRate = -1.f;
	float TimeTrialDropRate = -1.f;
	bool bPlacingOk = false;
	bool bPhotoLegSet = false;
	bool bZoneRefused = false;
	FString RefusalText;
	bool bPhotoOffered = false;
	FString PhotoPrompt;
	bool bPhotographed = false;
	bool bFled = false;
	float FledDistance = 0.f;
	bool bPhotoResultOk = false;
	int32 PhotoPrize = 0;
	int32 PhotoPoints = 0;
	bool bDnfOk = false;
	bool bTourEndOk = false;
	bool bSaveRoundTrip = false;
	bool bNewTourOk = false;
	FString Ending;
	FVector SubjectBBefore = FVector::ZeroVector;
};
