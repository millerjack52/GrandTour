#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTForestGroundDetails.generated.h"
class AGTLandscapeSurface;
class UInstancedStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

/** Bounded camera-local forest decoration. Never changes soil physics or vegetation. */
UCLASS()
class GRANDTOUR_API AGTForestGroundDetails : public AActor
{
    GENERATED_BODY()
public:
    AGTForestGroundDetails();
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<AGTLandscapeSurface> Surface;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TArray<TObjectPtr<UStaticMesh>> Meshes;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> Material;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float RadiusCm=3600.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float BudgetMs=.6f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FVector2D CoverageOrigin=FVector2D(-185000,-185000);
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float CoverageSpan=370000.f;
    UPROPERTY() TArray<uint8> Coverage;
    UPROPERTY() int32 CoverageSize=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TArray<TObjectPtr<UInstancedStaticMeshComponent>> FloorComponents;
    UFUNCTION(BlueprintCallable,CallInEditor) bool ImportCoverage(const FString& File);
    UFUNCTION(BlueprintPure) FString ForestGroundReport() const;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
private:
    struct FSlot{int32 Layer=0,Index=0;};
    struct FPending{FIntPoint Key;double Distance=0;};
    TMap<FIntPoint,FSlot> Active;
    TArray<int32> Free[3];
    TArray<FPending> Pending;
    int32 Cursor=0,RejectedSupport=0;
    FVector2D Centre=FVector2D(DBL_MAX,DBL_MAX);
    float PeakPumpMs=0;
    bool bConfigured=false;
    bool bReported=false;
    float Weight(FVector2D Point) const;
    void Refresh(FVector2D View);
    bool Evaluate(FIntPoint Key,int32& Layer,FTransform& Transform,FVector4& Fit);
};
