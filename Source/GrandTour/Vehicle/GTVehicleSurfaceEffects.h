#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTVehicleSurfaceEffects.generated.h"
class AGTCarPawn;
class AGTDustLab;
class AGTMudFlickLab;
class UNiagaraSystem;

/** A level opt-in for all cars, including later spawns and vehicle switching. */
UCLASS()
class GRANDTOUR_API AGTVehicleSurfaceEffects : public AActor
{
    GENERATED_BODY()
public:
    AGTVehicleSurfaceEffects();
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Vehicle Surface Effects")
    TObjectPtr<UNiagaraSystem> DustSystem;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Vehicle Surface Effects")
    TObjectPtr<UNiagaraSystem> MudSystem;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Vehicle Surface Effects")
    bool bEnabled = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Vehicle Surface Effects", meta=(ClampMin="0",ClampMax="3"))
    float DustIntensity = 2.4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Vehicle Surface Effects", meta=(ClampMin="0",ClampMax="3"))
    float MudIntensity = 1.4f;
    UFUNCTION(BlueprintPure, Category="Vehicle Surface Effects")
    int32 GetManagedCarCount() const { return Bindings.Num(); }
private:
    struct FBinding
    {
        TWeakObjectPtr<AGTCarPawn> Car;
        TWeakObjectPtr<AGTDustLab> Dust;
        TWeakObjectPtr<AGTMudFlickLab> Mud;
    };
    TArray<FBinding> Bindings;
    void Release(FBinding& Binding);
};
