// Wheel spray P2 (docs/WHEEL_SPRAY_PLAN.md): Niagara systems authored headless, through UE 5.8's experimental
// UNiagaraExternalEditUtilities (C++ only, so Python calls these). Art/Unreal/setup_wheel_spray.py calls BuildWheelSpray.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GTNiagaraSetupLibrary.generated.h"

class UMaterialInterface;

UCLASS()
class UGTNiagaraSetupLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Builds AssetPath/AssetName (replacing nothing: the caller deletes an old one first) from the template emitter
	 *  plus ExtraModules ("ScriptUsage|/Module/Path.Asset|AfterModuleName"), and returns every module input (name, type,
	 *  switch / visible / editable, enum display names), the emitter's JSON and its renderers' JSON. For writing builds. */
	UFUNCTION(BlueprintCallable, Category = "GrandTour|FX")
	static FString DescribeEmitterTemplate(const FString& AssetPath, const FString& AssetName, const FString& TemplateEmitter, const TArray<FString>& ExtraModules);

	/** WHEEL_SPRAY P2 item 2: NS_GT_WheelSpray, emitters MudDroplets, GravelGrit, GravelDust, its User parameters, compiled.
	 *  Every input write is guarded (module, input name and type asserted from GetEmitterTopology first; links never to a
	 *  static switch). Returns the log; a line starting FAIL means the build stopped there and nothing further was linked. */
	UFUNCTION(BlueprintCallable, Category = "GrandTour|FX")
	static FString BuildWheelSpray(const FString& AssetPath, const FString& AssetName, UMaterialInterface* MudMaterial,
		UMaterialInterface* GritMaterial, UMaterialInterface* DustMaterial);

	/** Mud and water MW1 item 3d (docs/MUD_WATER_SURFACE_PLAN.md): NS_GT_WaterRings, one CPU emitter WaterRings - flat ring
	 *  sprites (facing +Z through a SetParameters module, Particles.SpriteFacing) spawned at the component by User.RingRate,
	 *  10 cm growing to 120 cm (User.RingScale) over 1.2-2 s, no motion, RingMaterial (its fade by the particle's age). The same
	 *  guard as BuildWheelSpray. Returns the log (a FAIL line stops the build). */
	UFUNCTION(BlueprintCallable, Category = "GrandTour|FX")
	static FString BuildWaterRings(const FString& AssetPath, const FString& AssetName, UMaterialInterface* RingMaterial);
};
