#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GTLandscapeWheelEffects.generated.h"

class UInstancedStaticMeshComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class AGTLandscapeSurface;

/** Cosmetic response for the architecture-A surface. Never writes wheel forces or legacy mud volumes. */
UCLASS(ClassGroup=(GT))
class GRANDTOUR_API UGTLandscapeWheelEffects : public UActorComponent
{
    GENERATED_BODY()
public:
    UGTLandscapeWheelEffects();
    virtual void BeginPlay() override;
    virtual void TickComponent(float Dt,ELevelTick TickType,FActorComponentTickFunction* TickFunction) override;
    UFUNCTION(BlueprintPure) FString GetEffectReport() const;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bEnabled = true;
private:
    struct FClod { FVector P,V,Scale; FRotator R,Spin; float Age=0,Life=0; int32 Mesh=0; bool Landed=false; };
    TArray<FClod> Clods;
    TArray<float> Carry;
    TArray<FVector> Last;
    TWeakObjectPtr<AActor> Car;
    UPROPERTY(Transient) TObjectPtr<AGTLandscapeSurface> Surface;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Meshes;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> Fines;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> FineSystem;
    FRandomStream Random{91831};
    int32 Emitted=0, Landed=0;
    float Rate=0;
    int32 AppliedQuality=-1;
    TArray<TArray<FTransform>> InstanceTransforms;
};
