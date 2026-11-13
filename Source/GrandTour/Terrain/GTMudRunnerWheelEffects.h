#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Terrain/GTMudRunnerWheelFX.h"
#include "GTMudRunnerWheelEffects.generated.h"
class UProceduralMeshComponent;
class UMaterialInterface;

/** Study-level renderer for the recovered wheel Lua emissions. */
UCLASS()
class GRANDTOUR_API AGTMudRunnerWheelEffects : public AActor
{
    GENERATED_BODY()
public:
    AGTMudRunnerWheelEffects();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TArray<TObjectPtr<UMaterialInterface>> Materials;
    UFUNCTION(BlueprintPure) FString EffectReport() const;
    /** Read-only host placement diagnostics; emission equations stay untouched. */
    UFUNCTION(BlueprintPure) FString PlacementReport() const;
    /** Synthetic wheel input only: does not move or drive the player car. */
    UFUNCTION(BlueprintCallable) void ReviewWheel(FVector CentreCm,float SpeedMps,float Omega,float MudDepthM,float WaterDepthM,float Seconds);
    UFUNCTION(BlueprintCallable) void ClearReview();
    static bool IsActive(const UObject* Context);
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UProceduralMeshComponent> Mesh;
    struct FParticle { GTMudRunnerWheelFX::FSpawn Spawn; double Age=0,Life=1,Scale=1,PlaneY=-1.e10; int32 Frame=0; GTMudRunnerWheelFX::EKind Parent=GTMudRunnerWheelFX::MudSmall; };
    TArray<FParticle> Particles;
    struct FWheelFilter { double Omega=0; FVector Velocity=FVector::ZeroVector; };
    TArray<FWheelFilter> WheelFilters;
    FRandomStream Random{9640861};
    int32 Spawned[GTMudRunnerWheelFX::Count]={};
    GTMudRunnerWheelFX::FWheel Fixture;
    float ReviewRemaining=0;
    void Emit(const GTMudRunnerWheelFX::FWheel& Wheel,float Dt);
    void Draw();
};
