#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTRoadWaterMesh.generated.h"
class UProceduralMeshComponent;
UCLASS()
class GRANDTOUR_API AGTRoadWaterMesh : public AActor
{
    GENERATED_BODY()
public:
    AGTRoadWaterMesh();
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UProceduralMeshComponent> Mesh;
};
