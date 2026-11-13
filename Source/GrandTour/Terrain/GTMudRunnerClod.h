#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTMudRunnerClod.generated.h"
class UStaticMeshComponent;
class UPhysicsConstraintComponent;
UCLASS()
class GRANDTOUR_API AGTMudRunnerClod : public AActor
{
    GENERATED_BODY()
public:
    AGTMudRunnerClod();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPhysicsConstraintComponent> Anchor;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bLarge=false;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) bool bReleased=false;
    UFUNCTION(BlueprintCallable) void ReviewImpulse(FVector ImpulseNewtonSeconds);
};
