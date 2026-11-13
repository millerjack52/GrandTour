#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Terrain/GTTerrainGenerator.h"
#include "GTTerrainSpecAsset.generated.h"

/**
 * A leg's ground as an asset the user edits in the editor (M6, 2026-09-14: the user builds levels
 * themselves). The spec is what GTTerrain generates from: the grid, the noise, the landforms, the
 * route the road is carved along, what it is paved with, the snow line. A AGTTerrainBuilder in the
 * leg map points at one of these and rebuilds the landscape from it with a button.
 * Art/setup_m6_hide.bat writes DA_Terrain_Hide from GTTerrain::HideSpec.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTTerrainSpecAsset : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	/** What the ground is called in logs and the landscape actor's label. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Terrain")
	FString DisplayName = TEXT("The Hide");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Terrain", meta = (ShowOnlyInnerProperties))
	FGTTerrainSpec Spec;

	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	FString Describe() const;
};
