#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTMudFlickLab.generated.h"
class AGTCarPawn;
class UNiagaraComponent;
class UNiagaraSystem;
struct FGTWheelTraction;

/** Opt-in fine mud spray; existing spray owns physical clumps and terrain deposits. */
UCLASS()
class GRANDTOUR_API AGTMudFlickLab : public AActor
{
    GENERATED_BODY()
public:
    AGTMudFlickLab();
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Flick Lab")
    TObjectPtr<AGTCarPawn> TargetCar;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Flick Lab")
    TObjectPtr<UNiagaraSystem> MudSystem;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Flick Lab")
    bool bEnabled = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mud Flick Lab", meta=(ClampMin="0", ClampMax="3"))
    float Intensity = 1.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Mud Flick Lab")
    float TotalRate = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Mud Flick Lab")
    int32 EmittingWheels = 0;
    UFUNCTION(BlueprintPure, Category="Mud Flick Lab")
    int32 GetLiveParticles() const;
    UFUNCTION(BlueprintCallable, Category="Mud Flick Lab")
    void ResetSpray();
    static float Activity(bool Contact, bool Mud, float TreadCmS, float SlipCmS, float ThrownCm3S);
    static bool CoversWheel(const FGTWheelTraction& Wheel);
private:
    UPROPERTY(Transient)
    TArray<TObjectPtr<UNiagaraComponent>> Wheels;
    TArray<double> PreviousThrown;
    TArray<FVector> PreviousContacts;
    TWeakObjectPtr<AGTCarPawn> BoundCar;
    float SearchDelay = 0.f;
};
