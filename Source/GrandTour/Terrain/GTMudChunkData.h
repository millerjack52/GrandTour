#pragma once

#include "CoreMinimal.h"
#include "Engine/AssetUserData.h"
#include "GTMudChunkData.generated.h"

/**
 * MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block item 1): a mud chunk mesh's own numbers, from
 * Art/Export/MudChunks/manifest.json (Art/Blender/build_mud_chunks.py), put on SM_GT_MudChunk_<n> by Art/Unreal/import_mud_chunks.py.
 * AGTMudPatch reads them when it loads the meshes: a break deposits VolumeCm3 x scale^3 into the field, and the mass is
 * 1.6 kg/L of the same. Without it the patch falls back on the hull's own volume (and says so).
 */
UCLASS(BlueprintType, meta = (DisplayName = "GT Mud Chunk Data"))
class GRANDTOUR_API UGTMudChunkData : public UAssetUserData
{
	GENERATED_BODY()

public:
	/** rounded, slab, broken or smear. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|Chunks")
	FString Family;

	/** The closed render mesh's volume at AcrossCm, cm^3 (what a break deposits, x scale^3). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|Chunks")
	float VolumeCm3 = 0.f;

	/** The UCX_ hull's volume at AcrossCm, cm^3 (a readout). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|Chunks")
	float HullVolumeCm3 = 0.f;

	/** How far the render mesh goes on below the pivot (the hull's bottom), cm at AcrossCm: 18 % of its height. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|Chunks")
	float EmbedCm = 0.f;

	/** The mesh's across (its longest horizontal side) at scale 1, cm: 30. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Mud|Chunks")
	float AcrossCm = 30.f;
};
