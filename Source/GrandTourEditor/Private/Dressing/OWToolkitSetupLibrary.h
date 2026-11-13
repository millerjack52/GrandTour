// Test-map helpers for the OW landscape toolkit (docs/LandscapeMigrationManifest.md 9.A step 6, layout 9.C.1).
// Editor-only, called from Art/dressing/setup_toolkit_test_map.py:
//   unreal.OWToolkitSetupLibrary.sample_toolkit_test_height_cm(x, y) -> float
//   unreal.OWToolkitSetupLibrary.toolkit_test_layer_at(x, y) -> str
//   unreal.OWToolkitSetupLibrary.build_toolkit_test_landscape(material, layer_infos, rvt) -> str (report JSON), or None
//     on failure (Python drops a false bool's out values); the report is also logged as "OWToolkitSetup report: {...}".

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"

#include "OWToolkitSetupLibrary.generated.h"

class ULandscapeLayerInfoObject;
class UMaterialInterface;
class URuntimeVirtualTexture;

UCLASS()
class UOWToolkitSetupLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Ground height in cm at world XY on the toolkit test map (9.C.1): base waves plus the scree and alpine hills. */
	UFUNCTION(BlueprintPure, Category = "OW Toolkit")
	static float SampleToolkitTestHeightCm(float X, float Y);

	/** The dominant paint layer at world XY on the toolkit test map (9.C.1), before blending. For debugging the layout. */
	UFUNCTION(BlueprintPure, Category = "OW Toolkit")
	static FString ToolkitTestLayerAt(float X, float Y);

	/**
	 * Spawns the toolkit test landscape in the current editor world: 505 x 505 vertices (8 x 8 components of 63 quads,
	 * 1 section), scale 100, origin 0, heights and blended weights from the 9.C.1 layout, the 13 non-water layer infos
	 * passed in registered as target layers (no others), the final weightmaps written on the CPU (the GPU merge never
	 * runs under NullRHI), and RuntimeVirtualTextures = [RVT]. Refuses if the world already has a landscape.
	 * OutReport is compact JSON: vertex count, components, painted-vertex count per layer, height range.
	 */
	UFUNCTION(BlueprintCallable, Category = "OW Toolkit")
	static bool BuildToolkitTestLandscape(UMaterialInterface* Material, const TArray<ULandscapeLayerInfoObject*>& LayerInfos,
		URuntimeVirtualTexture* RVT, FString& OutReport);
};
