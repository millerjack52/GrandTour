#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Terrain/GTTerrainGenerator.h"
#include "GTVehicleSetupLibrary.generated.h"

class UGTSurfacePhysMaterial;
class UInputMappingContext;
class UMaterialExpression;
class UMaterialInterface;
class UPhysicsAsset;
class USkeletalMesh;
class UStaticMesh;

/** Scripting helpers for vehicle asset setup. Called from Art/Unreal/setup_m0.py (Python cannot reach body setups). */
UCLASS()
class GRANDTOUR_API UGTVehicleSetupLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Removes every body, and every constraint touching it, whose bone name starts with BonePrefix.
	 * Chaos wheels are swept from the suspension and must not have bodies of their own; only the
	 * chassis body should remain. Returns the number of bodies removed.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static int32 RemoveBodiesByBonePrefix(UPhysicsAsset* PhysicsAsset, const FString& BonePrefix);

	/**
	 * Replaces the collision of BoneName's body with one box. CenterCS and SizeCS are in the
	 * skeletal mesh's component space (cm, full lengths); the box is converted into bone space
	 * using the mesh's reference pose. Returns false if the body or bone is missing.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static bool SetBoxBody(UPhysicsAsset* PhysicsAsset, const USkeletalMesh* SkeletalMesh, FName BoneName,
	                       FVector CenterCS, FVector SizeCS);

	/** Replaces one body's collision with component-space boxes (cm, full sizes). */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static bool SetCompoundBoxBody(UPhysicsAsset* PhysicsAsset, const USkeletalMesh* SkeletalMesh, FName BoneName,
	                               const TArray<FVector>& CentersCS, const TArray<FVector>& SizesCS);

	/**
	 * Spawns a StaticMeshActor with Mesh, deferred so the mesh is set before registration. Plain
	 * UWorld spawning: works in commandlets, where the editor actor subsystems crash.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle", meta = (WorldContext = "WorldContextObject"))
	static AActor* SpawnStaticMeshActor(UObject* WorldContextObject, UStaticMesh* Mesh, FTransform Transform,
	                                    const FString& Label);

	/** Spawns an actor of ActorClass at Transform through UWorld::SpawnActor and labels it. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle", meta = (WorldContext = "WorldContextObject"))
	static AActor* SpawnActorOfClass(UObject* WorldContextObject, TSubclassOf<AActor> ActorClass, FTransform Transform,
	                                 const FString& Label);

	/** Turns on "simulation generates hit events" for every body so the car's collisions reach the condition component. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static int32 EnableHitEvents(UPhysicsAsset* PhysicsAsset);

	/** Sets a surface material's tag from its name; FGameplayTag is read-only from Python. False if the tag is unknown. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static bool SetSurfaceTag(UGTSurfacePhysMaterial* Material, FName TagName);

	/** Destroys every actor in the world whose editor label starts with Prefix. Returns the count. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle", meta = (WorldContext = "WorldContextObject"))
	static int32 DestroyActorsWithLabelPrefix(UObject* WorldContextObject, const FString& Prefix);

	/** One line per body: bone name, physics type and primitive counts. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static TArray<FString> DescribeBodies(const UPhysicsAsset* PhysicsAsset);

	/**
	 * Writes IA_Throttle / Brake / Steer / Handbrake / Look and IMC_Driving under Folder with exactly
	 * the mappings AGTCarPawn builds at runtime, so they can be rebound in the editor. Editor only.
	 * Returns the number of assets saved.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static int32 CreateDrivingInputAssets(const FString& Folder);

	/**
	 * Writes IA_Move / LookMouse / LookStick / Sprint / Interact / ToolNext / ToolPrev / Inventory /
	 * DropHook / ToggleHeadBob / Transfer / Jump and IMC_OnFoot under Folder with the mapping AGTPlayerCharacter
	 * builds at runtime. Editor only. Returns the number of assets saved (13).
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Character")
	static int32 CreateOnFootInputAssets(const FString& Folder);

	/** Writes DA_Tool_Cutter / PryBar / RepairKit under Folder from UGTToolDefinition's defaults. Editor only. Returns the number saved. */
	UFUNCTION(BlueprintCallable, Category = "GT|Character")
	static int32 CreateToolAssets(const FString& Folder);

	/** Writes DA_Weather_Clear / Overcast / Rain / Storm / Snow under Folder from UGTWeatherStateDefinition's defaults. Editor only. Returns the number saved (5). */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	static int32 CreateWeatherStateAssets(const FString& Folder);

	/** Writes DA_Loot_CableBundle / Wreck / RadiationCache under Folder from UGTLootTable's defaults. Editor only. Returns the number saved (3). */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	static int32 CreateLootTableAssets(const FString& Folder);

	/** Writes DA_Leg_01..05 under Folder from UGTLegDefinition's default legs, pointing each StartWeather at WeatherFolder's asset of that name. Editor only. Returns the number saved (5). */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	static int32 CreateLegAssets(const FString& Folder, const FString& WeatherFolder);

	/** Writes DA_Tour_01 under Folder from UGTTourDefinition's defaults, its legs at LegFolder/DA_Leg_0N. Editor only. Returns 1 when saved. */
	UFUNCTION(BlueprintCallable, Category = "GT|Run")
	static int32 CreateTourAssets(const FString& Folder, const FString& LegFolder);

	// ---- terrain (M6) ----
	/** The Hide's terrain spec (GTTerrain::HideSpec), so the setup script and the tests share one route and one set of landforms. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static FGTTerrainSpec MakeHideTerrainSpec();

	/** Writes DA_Terrain_Hide under Folder from GTTerrain::HideSpec (only when it does not exist yet, so the user's edits survive a re-run; pass bOverwrite to reset it). Editor only. Returns 1 when saved. */
	UFUNCTION(BlueprintCallable, Category = "GT|Terrain")
	static int32 CreateTerrainSpecAssets(const FString& Folder, bool bOverwrite);

	/** The Proving Ground's terrain spec (GTTerrain::ProvingSpec), beside The Hide's. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static FGTTerrainSpec MakeProvingTerrainSpec();

	/** Writes DA_Terrain_Proving under Folder from GTTerrain::ProvingSpec, kept when it exists unless bOverwrite, as CreateTerrainSpecAssets does for The Hide. Editor only. Returns 1 when saved or kept. */
	UFUNCTION(BlueprintCallable, Category = "GT|Terrain")
	static int32 CreateProvingTerrainSpecAsset(const FString& Folder, bool bOverwrite);

	/** The generated ground under a world XY, cm. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static float SampleTerrainHeightCm(const FGTTerrainSpec& Spec, float XCm, float YCm);

	/** Distance (m) from a world XY to the spec's route, and the arc length along it where the nearest point lies. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static float TerrainRouteDistanceM(const FGTTerrainSpec& Spec, float XCm, float YCm, float& OutArcM);

	/** A point on the spec's route at an arc length (m), in world cm, with the route's yaw there. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static FVector TerrainRoutePointCm(const FGTTerrainSpec& Spec, float ArcM, float& OutYaw);

	/** The dominant surface layer at a world XY: 0 tarmac, 1 dirt, 2 mud, 3 snow, 4 scrub. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static int32 TerrainLayerAt(const FGTTerrainSpec& Spec, float XCm, float YCm);

	/** The ground's slope at a world XY, degrees. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static float TerrainSlopeDegrees(const FGTTerrainSpec& Spec, float XCm, float YCm);

	/** The main route's length, m. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static float TerrainRouteLengthM(const FGTTerrainSpec& Spec);

	/** The section kind of the main route at an arc length. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static EGTRouteSectionKind TerrainSectionKindAt(const FGTTerrainSpec& Spec, float ArcM);

	/** The camber of the road at an arc length, degrees, positive when the right side is higher. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static float TerrainCamberDegreesAt(const FGTTerrainSpec& Spec, float ArcM);

	/** The water surface of ford section Index (into Spec.Sections), world cm; 0 when it is not a ford. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static float TerrainFordWaterLevelCm(const FGTTerrainSpec& Spec, int32 SectionIndex);

	/** A point on alternative route Index at an arc length (m), in world cm, with the line's yaw there. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static FVector TerrainAltRoutePointCm(const FGTTerrainSpec& Spec, int32 AltIndex, float ArcM, float& OutYaw);

	/** Alternative route Index's length, m. */
	UFUNCTION(BlueprintPure, Category = "GT|Terrain")
	static float TerrainAltRouteLengthM(const FGTTerrainSpec& Spec, int32 AltIndex);

	/**
	 * Generates the spec's ground and imports it as a Landscape actor in World with the material and four weight
	 * layers (Tarmac, Dirt, Mud, Snow), whose layer info assets are written under LayerInfoFolder pointing at the
	 * physical materials PM_<name> in SurfaceFolder. Editor only. Returns the landscape, or null.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Terrain")
	static AActor* BuildLegLandscape(UWorld* World, const FGTTerrainSpec& Spec, UMaterialInterface* Material, const FString& LayerInfoFolder, const FString& SurfaceFolder, const FString& Label);

	/** Writes DA_Item_* (resources, parts, consumables) under Folder from GTItemDefaults. Editor only. Returns the number saved. */
	UFUNCTION(BlueprintCallable, Category = "GT|Base")
	static int32 CreateItemAssets(const FString& Folder);

	/** Writes DA_Recipe_* under Folder from UGTRecipeDefinition's defaults. Editor only. */
	UFUNCTION(BlueprintCallable, Category = "GT|Base")
	static int32 CreateRecipeAssets(const FString& Folder);

	/** Writes DA_Upgrade_* under Folder from UGTUpgradeDefinition's defaults. Editor only. */
	UFUNCTION(BlueprintCallable, Category = "GT|Base")
	static int32 CreateUpgradeAssets(const FString& Folder);

	/** Key mappings in a context; Python cannot see 5.8's mapping storage, the setup script checks through this. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static int32 GetMappingCount(const UInputMappingContext* Context);

	/**
	 * Connects an expression output to a material's CustomData0 (Index 0: clear coat) or CustomData1
	 * (1: clear coat roughness); those properties are hidden from Python. Editor only.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static bool ConnectMaterialCustomData(UMaterialExpression* Expression, const FString& OutputName, int32 Index);

	/** Connects an expression output to a material's Pixel Depth Offset (hidden from Python like CustomData). Editor only. */
	UFUNCTION(BlueprintCallable, Category = "GT|Vehicle")
	static bool ConnectMaterialPixelDepthOffset(UMaterialExpression* Expression, const FString& OutputName);
};
