#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/SaveGame.h"
#include "GTWorkshopComponent.generated.h"

class AGTCarPawn;
class AGTPlayerController;
class ACameraActor;
class SGTWorkshop;

/** Cosmetic choices only. Mechanical parts remain in the existing run/loadout save. */
UCLASS()
class GRANDTOUR_API UGTWorkshopSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) int32 Paint = 0;
    UPROPERTY(SaveGame) int32 Rims = 0;
    // -1 identifies the original finish-only save format.
    UPROPERTY(SaveGame) int32 RimModel = -1;
    UPROPERTY(SaveGame) int32 Equipment = 0;
};

/** One local player's reversible walk-around session. No physics or inventory changes during preview. */
UCLASS(ClassGroup=(GT))
class GRANDTOUR_API UGTWorkshopComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UGTWorkshopComponent();
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") bool Open();
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void Close();
    UFUNCTION(BlueprintPure, Category="GT|Workshop") bool IsOpen() const { return bOpen; }
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void SelectPart(int32 Part);
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void Preview(int32 Option);
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void AdjustAWDSplit(int32 Steps);
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void Compare(bool bFitted);
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") bool Fit();
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void Cancel();
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void Orbit(float X, float Y);
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void Zoom(float Amount);
    UFUNCTION(BlueprintPure, Category="GT|Workshop") FString Describe() const;

    static FString SaveSlot();
    static FLinearColor PaintColour(int32 Choice);
    static FLinearColor RimColour(int32 Choice);
    int32 OptionCount() const;
    bool PartAvailable(int32 Part) const;
    int32 NextPart() const;
    FString VehicleName() const;
    FString OptionName(int32 Choice) const;
    FString Detail() const;
    FString FitReason() const;
    bool CanFit() const;
    bool HasPendingChange() const { return SelectedPart==4 ? bEquipmentPreview : SelectedPart>=0 && (SelectedOption!=FittedOption(SelectedPart) || (ShowAWDSplit() && SelectedFrontPercent!=FittedFrontPercent)); }
    bool ShowAWDSplit() const { return SelectedPart==6 && SelectedOption==3; }
    int32 DisplayFrontPercent() const { return bComparing ? FittedFrontPercent : SelectedFrontPercent; }
    void UpdateCamera(float Delta);
    FVector Hotspot(int32 Part) const;
    int32 SelectedPart = INDEX_NONE; // 0 paint, 1 wheels, 2 tyres, 3 suspension, 4 equipment, 5 engine package, 6 drive layout
    int32 SelectedOption = 0;
    bool bComparing = false;
    FString Message;
    AGTCarPawn* Vehicle() const { return Car.Get(); }
    AGTPlayerController* Controller() const;

private:
    void ApplyPreview(bool bFitted);
    int32 FittedOption(int32 Part) const;
    bool bOpen = false;
    bool bWasPaused = false;
    bool bWasCursor = false;
    bool bWasHUD = true;
    bool bWasFullTick = false;
    bool bTestFitting = false;
    int32 FittedPaint = 0, FittedRims = 0;
    int32 FittedEquipment = 0;
    bool bEquipmentPreview = false;
    FName FittedTyres;
    FName FittedSuspension;
    FName FittedDrivetrain;
    FName FittedDriveLayout;
    int32 FittedFrontPercent = 50, SelectedFrontPercent = 50;
    float Yaw = -42.f, Pitch = 15.f, Distance = 780.f;
    float CameraYaw = -42.f, CameraPitch = 15.f, CameraDistance = 780.f;
    float CameraFraming = 0.f;
    TWeakObjectPtr<AGTCarPawn> Car;
    TWeakObjectPtr<AActor> PreviousView;
    UPROPERTY(Transient) TObjectPtr<ACameraActor> Camera;
    TSharedPtr<SGTWorkshop> Widget;
};
