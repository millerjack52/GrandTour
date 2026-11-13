#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GTRenderOptimisationLibrary.generated.h"

class USkeletalMesh;

/** Editor-script access to UE 5.8 LOD settings, which no longer expose LODInfo to Python. */
UCLASS()
class GRANDTOUR_API UGTRenderOptimisationLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	UFUNCTION(BlueprintCallable, Category="GT|Rendering|Editor")
	static TArray<float> GetSkeletalLODScreenSizes(USkeletalMesh* Mesh);

	/** Configure an already-generated additional LOD. Never alters imported LOD0-2 or saves an asset. */
	UFUNCTION(BlueprintCallable, Category="GT|Rendering|Editor")
	static bool ConfigureGeneratedFarLOD(USkeletalMesh* Mesh, int32 LODIndex, int32 MaxVertices, float ScreenSize);
};
