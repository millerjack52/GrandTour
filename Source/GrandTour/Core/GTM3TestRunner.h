#pragma once

#include "CoreMinimal.h"

class AGTCarPawn;
class AGTHarvestNode;
class AGTPlayerCharacter;
class AGTPlayerController;
class AGTRadiationZone;
class AGTRunGameMode;
class AGTRunGameState;
class AGTWeatherFront;
class AStaticMeshActor;
class UGTLegDefinition;
class UGTLootTable;
class UGTWeatherStateDefinition;
class UGTWeatherSubsystem;
class UWorld;

enum class EGTM3Test : uint8
{
	Leg,
	Weather,
	Hazard,
	Loot,
	Environment
};

/**
 * Scripted headless checks for M3 (the run loop), driven from AGTRunGameMode::Tick on L_DriveTest.
 * Each test spawns what it needs (checkpoints, roofs, fronts, zones, nodes) so no map authoring
 * is required, disables player input on both pawns, logs a GTDRIVETEST m3 line per step and
 * returns its verdict through the game mode's FinishTest.
 */
class FGTM3TestRunner
{
public:
	FGTM3TestRunner(UWorld* InWorld, EGTM3Test InKind);

	/** Returns true when the test is over; the verdict is in bOutPass / OutSummary. */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	bool Setup();
	void TickLeg(float DeltaSeconds);
	void TickWeather(float DeltaSeconds);
	void TickHazard(float DeltaSeconds);
	void TickLoot(float DeltaSeconds);
	void TickEnvironment(float DeltaSeconds);
	void Next();
	void Finish(bool bPass, const FString& Summary);
	void Fail(const FString& Why) { Finish(false, Why); }
	void Log(const FString& Line) const;
	FVector CarLocal(const FVector& Local) const;
	void TeleportCar(const FVector& Location);
	void TeleportCharacter(const FVector& GroundLocation, const FVector& LookAt);
	bool ExitCar();
	bool EnterCar();
	AStaticMeshActor* SpawnBox(const FVector& Location, const FVector& Scale, const TCHAR* Label);
	bool StepTimedOut(float Seconds, const TCHAR* What);
	bool EverySecond(float DeltaSeconds) const;

	TWeakObjectPtr<UWorld> World;
	EGTM3Test Kind;
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
	TWeakObjectPtr<AGTRunGameMode> GameMode;
	TWeakObjectPtr<AGTRunGameState> RunState;
	TWeakObjectPtr<UGTWeatherSubsystem> Weather;
	TWeakObjectPtr<UGTLegDefinition> Leg;
	TWeakObjectPtr<AStaticMeshActor> Roof;
	TWeakObjectPtr<AGTWeatherFront> Front;
	TWeakObjectPtr<AGTRadiationZone> Zone;
	TWeakObjectPtr<AGTHarvestNode> Node;
	TWeakObjectPtr<UGTLootTable> Table;

	// leg
	bool bStagingOk = false;
	bool bStartedOnMove = false;
	bool bCheckpoint1 = false;
	bool bEarlyRefused = false;
	bool bCheckpoint2 = false;
	bool bFinished = false;
	float FinishTime = 0.f;
	FString ResultLine;

	// weather
	float RainAfterBlend = 0.f;
	float WetnessAfterRain = 0.f;
	float CollectionRain = -1.f;
	float CollectionWetness = -1.f;
	float TractionWetness = 0.f;
	float TarmacGrip = 1.f;
	int32 LiveDrops = 0;
	int32 DropsUnderRoof = 0;
	int32 RejectedUnderCover = 0;
	float ExposureInRain = 100.f;
	float ExposureUnderRoof = 100.f;
	float ExposureAfterRoof = 100.f;
	float SnowAfterSnow = 0.f;
	float TempInSnow = 0.f;
	float RainFromFront = 0.f;
	float AudioRms = -1.f;
	float OcclusionRoofDepth = -1.f;
	float OcclusionOpenDepth = -1.f;
	bool bOcclusionRead = false;
	int32 EmitterDrawn = 0;

	// hazard
	float PressureFar = -1.f;
	float PressureNear = -1.f;
	bool bInsideFront = false;
	float ExposureInFront = 100.f;
	float GlassAfterFront = 1.f;
	float BodyAfterFront = 1.f;
	float ExposureInZone = 100.f;
	float EngineAfterZone = 1.f;
	bool bRadiationLight = false;
	bool bRareOffered = false;
	FString DashLine;

	// loot
	int32 Rolls = 0;
	int32 MinScrap = 999;
	int32 MaxScrap = 0;
	int32 RadiatorHits = 0;
	int32 TyreHits = 0;
	int32 EmptyRolls = 0;
	int32 AlloyFromNode = 0;
	bool bAssetsLoaded = false;

	// environment
	float HeatAfterDrive = 0.f;
	float ClogAfterDrive = 0.f;
	int32 HeatStage = 0;
	int32 DustStage = 0;
	float TorqueScaleUnderConditions = 1.f;
	float EngineAfterDrive = 1.f;
	bool bFilterLight = false;
	bool bTempNeedle = false;
	float ColdDrainRate = 0.f;
	float BaseDrainRate = 0.f;
	FVector DriveStart = FVector::ZeroVector;
	float NextTeleportTime = 7.f;
};
