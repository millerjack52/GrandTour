#pragma once

#include "CoreMinimal.h"
#include "Core/GTPlayerController.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "Core/GTHUD.h"
#include "GTMudLab.generated.h"

/** Optional map-authored route and recovery points for the mud driving studies. */
UCLASS()
class GRANDTOUR_API AGTMudRoute : public AActor
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, Category="Mud Route") FString Title = TEXT("MUD ROAD / forest track");
    UPROPERTY(EditAnywhere, Category="Mud Route") FString CheckpointLabels = TEXT("1 Start   2 Puddles   3 Flooded dip");
    UPROPERTY(EditAnywhere, Category="Mud Route") TArray<FTransform> RecoveryPoints;
    /** Per-map starting state; legacy mud studies retain low range and locked diffs. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Route") bool bStartLowRange = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Route") bool bStartDiffLocked = true;
};

/** Only used by L_MudLab; existing vehicle and terrain laws remain unchanged. */
UCLASS()
class GRANDTOUR_API AGTMudLabController : public AGTPlayerController
{
    GENERATED_BODY()
public:
    virtual void SetupInputComponent() override;
    virtual void OnPossess(APawn* Pawn) override;
    UFUNCTION(BlueprintCallable, Category="Mud Lab") void SelectLane(int32 Lane);
    UFUNCTION(BlueprintCallable, Category="Mud Lab") void ResetLab();
    UFUNCTION(BlueprintCallable, Category="Mud Lab") void ToggleDriveInfo() { bShowDriveInfo=!bShowDriveInfo; }
    UPROPERTY(BlueprintReadOnly, Category="Mud Lab") bool bShowDriveInfo = true;
    UPROPERTY(BlueprintReadOnly, Category="Mud Lab") int32 SelectedLane = 1;
private:
    void FirmLane() { SelectLane(1); }
    void SoftLane() { SelectLane(2); }
    void WaterLane() { SelectLane(3); }
    void SandLane() { SelectLane(4); }
    void GrassLane() { SelectLane(5); }
    void RiverLane() { SelectLane(6); }
    void RecoverySeven() { SelectLane(7); }
    void RecoveryEight() { SelectLane(8); }
    void RecoveryNine() { SelectLane(9); }
};

UCLASS()
class GRANDTOUR_API AGTMudLabHUD : public AGTHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};

UCLASS()
class GRANDTOUR_API AGTMudLabGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AGTMudLabGameMode();
};
