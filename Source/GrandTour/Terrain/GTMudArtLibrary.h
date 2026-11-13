#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GTMudArtLibrary.generated.h"

class UTexture;
class UTexture2D;
class UTexture2DArray;

/**
 * Living mud LM5b (docs/LIVING_MUD_PLAN.md LM5b, docs/MUD_VARIANTS.md): editor helpers for the mud art scripts
 * (Art/Unreal/import_mud_variants.py). Python can set a Texture2DArray's Source Textures, but whether the array's own
 * source is rebuilt from them depends on its edit notification; these two make the build explicit and measurable.
 */
UCLASS()
class GRANDTOUR_API UGTMudArtLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Editor only: Array's source rebuilt from Slices (slice i = Slices[i]; all one size and one pixel format), then the
	 * array rebuilt (PostEditChange) and its package marked dirty. Returns the array's source slice count, or -1 with
	 * OutMessage saying why (0 outside the editor).
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	static int32 BuildTextureArray(UTexture2DArray* Array, const TArray<UTexture2D*>& Slices, FString& OutMessage);

	/** Editor only: the slices in the array's source (0 when it has none), and its source size (OutSizeX x OutSizeY). */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	static int32 TextureArraySourceSlices(UTexture2DArray* Array, int32& OutSizeX, int32& OutSizeY);

	/**
	 * MudRunner MRP follow-up 3 (the owner's 6 GB card): a texture's whole video-memory size from its built platform data -
	 * every mip of every slice in the built pixel format (CalcTextureMemorySizeEnum(TMC_AllMips)), whether or not it is
	 * resident now (Blueprint_GetMemorySize reports only what is resident: 4 KB for an array nothing has drawn) - and that
	 * format's name. The editor waits for the platform data first.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Mud")
	static int64 TextureAllMipsBytes(UTexture* Texture, FString& OutFormat);
};
