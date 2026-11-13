// Living mud LM3c item 5 (docs/LIVING_MUD_PLAN.md LM3c): what Substrate compiled a material to, for the diagnosis of the snow
// material's +0.39 ms in deferred lighting (LM3b). Editor-only, called from Art/Unreal/setup_live_snow_drive.py and
// Art/Unreal/check_live_snow_drive.py:
//   unreal.GTSubstrateInfoLibrary.get_substrate_material_info(material) -> str

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"

#include "GTSubstrateInfoLibrary.generated.h"

class UMaterialInterface;

UCLASS()
class UGTSubstrateInfoLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * The base material's Substrate compilation output on the editor's shader platform, one line: the material type and the
	 * lighting tile type it puts its pixels in (Simple / Single / Complex / ComplexSpecial), the closure count, the uints per
	 * pixel, the BSDF feature bits (SSS, MFPPluggedIn, Fuzz, ...), whether the blendable GBuffer's legacy pass-through is
	 * used (the Front Material pin unplugged), the bytes per pixel asked and allowed, and the shading models the legacy
	 * conversion reports; then Substrate's own verbose description. "Substrate off" or "not compiled" when that is so.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Test")
	static FString GetSubstrateMaterialInfo(UMaterialInterface* Material);
};
