#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTTerrainBuilder.generated.h"

class AGTTerrainDressing;
class UGTTerrainSpecAsset;

/**
 * The editor's way to build a leg's ground (M6): place one in the leg map, point it at a
 * UGTTerrainSpecAsset, edit the asset, and press Rebuild Landscape in the Details panel. It
 * throws away the map's landscape, generates and imports a new one from the spec through
 * UGTVehicleSetupLibrary::BuildLegLandscape, and drops the leg's actors (checkpoints, the zone,
 * nodes, wrecks, posts, the bear, the player start, and static meshes whose labels start with
 * the listed prefixes) back onto the new ground at the height they had above the old one.
 * Show Route draws the spec's route, its surface spans and its landforms in the viewport for a
 * while. Editor only: it does nothing in a game. Art/setup_m6_hide.py drives the same functions,
 * so the headless build and the button share one path.
 */
UCLASS(hidecategories = (Rendering, Replication, Collision, Input, Actor, LOD, Cooking, HLOD, Physics, Networking))
class GRANDTOUR_API AGTTerrainBuilder : public AActor
{
	GENERATED_BODY()

public:
	AGTTerrainBuilder();

	/** The ground to build. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	TObjectPtr<UGTTerrainSpecAsset> SpecAsset;

	/** The landscape material, as a path (loaded at build time; the project keeps materials out of constructors). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString LandscapeMaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_Landscape");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString LayerInfoFolder = TEXT("/Game/GrandTour/Terrain/Layers");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString SurfaceFolder = TEXT("/Game/GrandTour/Terrain/Surfaces");

	/** Put the leg's actors back on the new ground after a rebuild, at the height they had above the old ground. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	bool bRegroundActors = true;

	/** Static mesh actors with these label prefixes are re-grounded too (rocks, the hide, roofs, markers). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	TArray<FString> RegroundLabelPrefixes;

	/** Static mesh actors with these label prefixes are never touched (the horizon skirt). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	TArray<FString> KeepLabelPrefixes;

	/** Throws away the map's landscape and builds a new one from the spec, then re-grounds the leg's actors. Returns the landscape, or null. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "GT|Terrain")
	AActor* RebuildLandscape();

	/** Drops the leg's actors onto the spec's ground at the height they now have above whatever is under them. Returns how many moved. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "GT|Terrain")
	int32 RegroundActors();

	/** Draws the route (white), its surface spans (tarmac grey, dirt tan, mud brown, snow white) and the landforms (green up, red down) for a minute. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "GT|Terrain")
	void ShowRoute();

	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	int32 Rebuilds = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	int32 LastRegrounded = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	FString LastMessage;

	/** The map's stones and posts (stage 2), rebuilt from the spec with the landscape; spawned when missing. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	TObjectPtr<AGTTerrainDressing> Dressing;

	/** Places the spec's stones and posts (AGTTerrainDressing) on the spec's ground; spawns the actor when the map has none. Returns the instance count. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "GT|Terrain")
	int32 RebuildDressing();

private:
	/** The actors a rebuild should keep on the ground, with the height each has above what is under it now. */
	struct FRegroundEntry
	{
		TWeakObjectPtr<AActor> Actor;
		float AboveGroundCm = 0.f;
	};
	void CollectRegroundable(TArray<FRegroundEntry>& OutEntries) const;
	bool IsRegroundable(const AActor* Actor) const;
	float GroundUnder(const AActor* Actor, const TArray<AActor*>& NotGround, bool& bOutHit) const;
};
