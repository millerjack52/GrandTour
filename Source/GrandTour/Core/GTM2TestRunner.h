#pragma once

#include "CoreMinimal.h"

class AGTCarPawn;
class AGTHarvestNode;
class AGTHazardVolume;
class AGTPlayerCharacter;
class AGTPlayerController;
class AGTWinchAnchor;
class AGTWreck;
class AStaticMeshActor;
class UWorld;

/**
 * Scripted headless checks for M2, driven from AGTDriveTestGameMode::Tick on L_DriveTest:
 *  -GTOnFootTest  get out of the car (character possessed, car persists, contexts swapped), walk
 *                 with head bob then without, harvest a node (refused bare-handed, accepted with
 *                 the cutter), field-repair the radiator with the kit for scrap, move items to the
 *                 boot and hit the weight limit, drain exposure in a hazard volume, get back in and
 *                 recover.
 *  -GTWinchTest   take the hook at the nose, walk past the cable length (tether stops you), hook a
 *                 post (the post then offers "Detach", the nose "Release winch"), get in, reel (car
 *                 moves), let go with IA_ReleaseWinch (G / DPad Up: stowed, the cable rewinds to the
 *                 drum) and hook the post again, reel against a wall (cable snaps, winch damaged),
 *                 reel on a weak anchor (it tears out).
 * Every step logs a GTDRIVETEST line; the verdict goes back to the game mode's FinishTest.
 */
class FGTM2TestRunner
{
public:
	FGTM2TestRunner(UWorld* InWorld, bool bInWinchTest);

	/** Returns true when the test is over; the verdict is in bOutPass / OutSummary. */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	bool Setup();
	void TickOnFoot(float DeltaSeconds);
	void TickWinch(float DeltaSeconds);
	void Next();
	void Finish(bool bPass, const FString& Summary);
	void Fail(const FString& Why) { Finish(false, Why); }
	void Log(const FString& Line) const;
	FVector CarLocal(const FVector& Local) const;
	void TeleportCharacter(const FVector& GroundLocation, const FVector& LookAt);
	void AimAt(const FVector& Target);
	bool TargetIs(const AActor* Actor) const;
	bool PromptContains(const TCHAR* Text) const;
	bool StepTimedOut(float Seconds, const TCHAR* What);

	TWeakObjectPtr<UWorld> World;
	bool bWinchTest = false;
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
	TWeakObjectPtr<AGTHarvestNode> Node;
	TWeakObjectPtr<AGTWreck> Wreck;
	TWeakObjectPtr<AGTHazardVolume> Hazard;
	TWeakObjectPtr<AGTWinchAnchor> StrongAnchor;
	TWeakObjectPtr<AGTWinchAnchor> WeakAnchor;
	TWeakObjectPtr<AStaticMeshActor> Wall;

	// on-foot measurements
	bool bExitOk = false;
	bool bContextsAfterExit = false;
	float ExitDistance = 0.f;
	FVector WalkStart = FVector::ZeroVector;
	float WalkDistance = 0.f;
	float BobMax = 0.f;
	float BobAfterOff = 0.f;
	bool bBareHandsRefused = false;
	bool bCutterOffered = false;
	int32 WireAfterHarvest = 0;
	bool bRepairOffered = false;
	float RadiatorAfterRepair = 0.f;
	int32 ScrapAfterRepair = -1;
	int32 BootWire = 0;
	int32 OverfillAccepted = 0;
	bool bWeightRespected = false;
	float ExposureAfterHazard = 100.f;
	bool bEnterOk = false;
	bool bContextsAfterEnter = false;
	float ExposureAtEntry = 0.f;
	float ExposureAfterCar = 0.f;
	bool bSameCar = false;
	float JumpStartZ = 0.f;
	float JumpPeak = 0.f;
	bool bJumpLeftGround = false;
	bool bJumpLanded = false;

	// winch measurements
	bool bHookOffered = false;
	bool bHookTaken = false;
	float MaxHookDistance = 0.f;
	bool bTetherOk = false;
	bool bAttachOffered = false;
	bool bAttached = false;
	FVector ReelStart = FVector::ZeroVector;
	float PullDistance = 0.f;
	float ReelMaxTension = 0.f;
	bool bReelOk = false;
	bool bSnapped = false;
	float WinchHealthAfterSnap = 1.f;
	bool bWeakFailed = false;

	// winch release (section 51)
	float AttachedAt = -1.f;
	bool bDetachOffered = false;
	bool bFrontReleaseOffered = false;
	bool bReleaseOnG = false;
	bool bReleaseOnDPadUp = false;
	bool bAttachedBeforeRelease = false;
	float PressedAt = -1.f;
	float TensionBeforeRelease = 0.f;
	float ReleasedAt = -1.f;
	bool bReleasedByAction = false;
	float TensionAtRelease = -1.f;
	float MaxTensionAfterRelease = 0.f;
	float RewindStartCm = 0.f;
	float LastDrawnCm = 0.f;
	bool bRewindMonotone = true;
	int32 RewindTicks = 0;
	float RewindSeconds = 0.f;
	bool bRewindHidden = false;
	bool bReattached = false;
	int32 WinchAttachesAfter = 0;
	int32 AnchorAttachesAfter = 0;
};
