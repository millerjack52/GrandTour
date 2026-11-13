#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTRoadReliefTile.generated.h"
class UProceduralMeshComponent;
class AGTLandscapeSurface;
class UMaterialInstanceDynamic;
/** Host adapter: saved local geometry and matching triangle collision. */
UCLASS()
class GRANDTOUR_API AGTRoadReliefTile : public AActor
{
    GENERATED_BODY()
public:
    AGTRoadReliefTile();
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UProceduralMeshComponent> Mesh;
    /** Query surface stays at authored height; rigid bodies stop at the mineral base. */
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UProceduralMeshComponent> MineralBase;
    UPROPERTY() TObjectPtr<AGTLandscapeSurface> Surface;
    UPROPERTY() TArray<float> Heights;
    UPROPERTY() TArray<FVector> Normals;
    /** Absolute mud depth cm, legacy rest value, firmness, softness. A negative
     * red channel means this vertex keeps the existing landscape paint. */
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TArray<FLinearColor> Soil;
    FLinearColor SoilAt(FVector2D XY,FLinearColor Fallback) const;
    UPROPERTY() int32 Intervals=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) float SpanCm=0;
    UPROPERTY() FString Signature;
    UFUNCTION(BlueprintPure) float HeightAt(FVector2D XY) const;
    UFUNCTION(BlueprintPure) float MineralHeightAt(FVector2D XY) const;
    UFUNCTION(BlueprintPure) int32 TriangleCount() const {return Intervals*Intervals*2;}
    void BuildMesh();
    void BindWindow(FLinearColor Window);
protected:
    virtual void BeginPlay() override;
private:
    void BuildMineralBase();
    float VertexBase(int32 I) const;
    FLinearColor LastWindow;
    bool bHaveWindow=false;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Dynamic;
};
