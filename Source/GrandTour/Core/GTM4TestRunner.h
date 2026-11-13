#pragma once

#include "CoreMinimal.h"

class ACameraActor;
class AGTBriefingBoard;
class AGTCarLift;
class AGTCarPawn;
class AGTCraftingStation;
class AGTCrewTent;
class AGTPlayerCharacter;
class AGTPlayerController;
class AGTTrader;
class AGTWorkbench;
class UGTRunSubsystem;
class UWorld;
struct FGTScreenRow;

enum class EGTM4Test : uint8
{
	/** The stations, spawned beside the car on any map: craft, install, repair, wash, trade, crew, consumables, the review fixes, save round trip. */
	Base,
	/** Across level loads: a leg's extraction carries the haul to the base, the base carries the loadout back to a leg. The stage lives in the run subsystem. */
	Loop,
	/** Pictures of the base for the user (L_Base, -RenderOffScreen): two overviews, the yard at eye level, the lift screen, the doors open, the driver's doorway. */
	Screenshots,
	/** The car doors on L_DriveTest: hinges, swing, exit opens the driver's door, open / close / get in by looking, shut behind you, knocked off and put back; with a GPU, two pictures. */
	Doors
};

/**
 * Scripted headless checks for M4 (the base), driven from AGTRunGameMode::Tick or
 * AGTBaseGameMode::Tick. The loop test crosses OpenLevel twice: each game mode creates a new
 * runner and it continues from UGTRunSubsystem::TestStage.
 */
class FGTM4TestRunner
{
public:
	FGTM4TestRunner(UWorld* InWorld, EGTM4Test InKind);

	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	bool Setup();
	void TickBase(float DeltaSeconds);
	void TickLoop(float DeltaSeconds);
	void TickScreenshots(float DeltaSeconds);
	void TickDoors(float DeltaSeconds);
	void TeleportCharacter(const FVector& GroundLocation, const FVector& LookAt);
	void ShowFromCamera(const FVector& Location, const FRotator& Rotation);
	void RequestShot(const TCHAR* Name);
	int32 PendingCompileJobs() const;
	void Next();
	void Finish(bool bPass, const FString& Summary);
	void Fail(const FString& Why) { Finish(false, Why); }
	void Log(const FString& Line) const;
	FVector CarLocal(const FVector& Local) const;
	void TeleportCar(const FVector& Location);
	bool ExitCar();
	bool EnterCar();
	bool StepTimedOut(float Seconds, const TCHAR* What);
	/** Finds a row by action (and payload when set) and acts on it through the station; false when missing or disabled. */
	bool ActRow(AGTCraftingStation* Station, int32 Action, FName Payload, FString& OutText);
	bool HasRow(AGTCraftingStation* Station, int32 Action, FName Payload, bool& bOutEnabled, FString& OutText) const;
	template <typename T> T* FindActor() const;

	TWeakObjectPtr<UWorld> World;
	EGTM4Test Kind;
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
	TWeakObjectPtr<AGTWorkbench> Workbench;
	TWeakObjectPtr<AGTCarLift> Lift;
	TWeakObjectPtr<AGTTrader> Trader;
	TWeakObjectPtr<AGTCrewTent> Crew;
	TWeakObjectPtr<AGTBriefingBoard> Briefing;

	// base
	bool bCrafted = false;
	int32 ScrapAfterCraft = 0;
	bool bInstalledRadiator = false;
	float RadiatorAfterInstall = 0.f;
	int32 BootRadiators = 0;
	int32 RepairCostSeen = 0;
	float EngineAfterRepair = 0.f;
	float WetAfterWash = 1.f;
	int32 CurrencyAfterSell = 0;
	int32 CurrencyAfterBuy = 0;
	bool bHeaterInstalled = false;
	float ColdResistance = 0.f;
	bool bScoutRefused = false;
	int32 ScoutTier = 0;
	bool bBriefingPeak = false;
	float HeatAfterFlush = 1.f;
	float ColdResistanceWithBlanket = 0.f;
	float OwnColdResistance = 0.f;
	int32 CurrencyBeforeSave = 0;
	int32 CurrencyAfterLoad = -1;
	bool bLoadedLoadoutHasHeater = false;
	bool bAssets = false;

	// base: checks for the review fixes of 2026-09-13
	FVector ExitLocal = FVector::ZeroVector;
	bool bExitBesideStep = false;
	bool bRequiredSlotRefused = false;
	bool bFreeRepair = false;
	bool bWorkbenchNoRoom = false;
	bool bLiftNoRoom = false;
	bool bCursorStays = false;
	bool bCursorDisarmed = false;
	bool bCursorOffHeaders = false;
	bool bNoOpConsumableRefused = false;
	bool bGetInAboveSkin = false;
	bool bSnapshotResistances = false;
	int32 SubStep = 0;

	// screenshots
	FString ShotFolder = TEXT("M4");
	TArray<FString> ShotFiles;
	TWeakObjectPtr<ACameraActor> ShotCamera;
	float SettleLogTimer = 0.f;

	// doors
	bool bFourDoors = false;
	bool bHingesOk = false;
	bool bDriverOk = false;
	bool bAllOpen = false;
	bool bSwingOk = false;
	float SwingError = -1.f;
	bool bClosedBack = false;
	bool bExitBehindDoor = false;
	float DoorExitDistance = 0.f;
	bool bDriverDoorOpenedOnExit = false;
	bool bGetInOffered = false;
	bool bCloseOffered = false;
	bool bClosedByHand = false;
	bool bOpenOffered = false;
	bool bNeedsDoorHint = false;
	bool bOpenedByHand = false;
	bool bEnteredThroughDoor = false;
	bool bShutBehind = false;
	bool bDoorDetached = false;
	bool bGetInWithoutDoor = false;
	bool bReattached = false;
	FString DoorPrompts;
};
