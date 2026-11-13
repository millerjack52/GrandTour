#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTDustLab.generated.h"

class AGTCarPawn;
class UNiagaraComponent;
class UNiagaraSystem;

/** Opt-in dust experiment. Only worlds with a placed GTDustLab actor run it.
 * Reads traction/weather; never changes vehicle physics, terrain or shared spray assets. */
UCLASS()
class GRANDTOUR_API AGTDustLab : public AActor
{
    GENERATED_BODY()
public:
    AGTDustLab();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dust Lab")
    TObjectPtr<AGTCarPawn> TargetCar;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dust Lab")
    TObjectPtr<UNiagaraSystem> DustSystem;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dust Lab")
    bool bEnabled = true;
    /** Override used by the isolated wet/dry review, -1 uses weather wetness. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dust Lab", meta=(ClampMin="-1", ClampMax="1"))
    float WetnessOverride = -1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dust Lab")
    float Intensity = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dust Lab")
    float WindScale = 0.35f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dust Lab")
    float TotalRate = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dust Lab")
    int32 EmittingWheels = 0;
    UFUNCTION(BlueprintPure, Category="Dust Lab")
    int32 GetLiveParticles() const;
    UFUNCTION(BlueprintCallable, Category="Dust Lab")
    void ResetDust();
    /** Contact and moisture gates are immediate; detached particles retain their natural tail. */
    static float EmissionStrength(bool bContact, bool bDusty, float SpeedCmS, float SlipCmS, float Wetness);

private:
    UPROPERTY(Transient)
    TArray<TObjectPtr<UNiagaraComponent>> Wheels;
    TArray<FVector> PreviousContacts;
    float SearchDelay = 0.f;
    void ZeroRates();
};
