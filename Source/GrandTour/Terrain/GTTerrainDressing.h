#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Terrain/GTTerrainGenerator.h"
#include "GTTerrainDressing.generated.h"

class UHierarchicalInstancedStaticMeshComponent;

/**
 * The small things the generator puts on a leg's ground with collision (driving feel stage 2): stones in the
 * tracks (GTTerrain::TrackStones) and posts along the rally edges (GTTerrain::RallyPosts), as instances of the
 * engine's cube and cylinder, and the ford rocks (water stage R1; their own component since look stage L6). One lives in the leg map; AGTTerrainBuilder rebuilds it from the spec after every
 * landscape rebuild (the button and Art/setup_m6_hide.py share that path), so nothing here is placed by hand.
 * A runtime actor: the instances are saved with the map and the wheels and the body hit them in the game.
 */
UCLASS()
class GRANDTOUR_API AGTTerrainDressing : public AActor
{
	GENERATED_BODY()

public:
	AGTTerrainDressing();

	/** Stones: the engine's cube, partly sunk, turned and tilted. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Terrain")
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Stones;

	/** Posts: the engine's cylinder, RallyPostWidthM wide and RallyPostHeightM tall. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Terrain")
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Posts;

	/** Look stage L6: the ford rocks (GTTerrain::FordRocks), the stones' mesh and collision in a component of their own so they can wear their own material. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Terrain")
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Rocks;

	/**
	 * Look stage L3 (VEHICLE_BUILD_SYSTEM 58): the foliage clumps on the Scrub layer beside the road, a PLACEHOLDER - the
	 * engine's plane stood up, FoliageCardsPerClump crossed per clump, in M_GT_FoliageCard's blade fan - until the owner
	 * models the cards (FoliageMeshPath, the stones' convention). No collision: the car drives through them. Leg dressing
	 * LD3: none on a spec with biomes (GTTerrain::HasBiomes), where the OW PCG graphs dress the ground instead.
	 */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Terrain")
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Foliage;

	/** Meshes and materials by path, loaded at rebuild time (the project keeps assets out of constructors). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString StoneMeshPath = TEXT("/Engine/BasicShapes/Cube.Cube");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString PostMeshPath = TEXT("/Engine/BasicShapes/Cylinder.Cylinder");

	/** Look stage L6 (VEHICLE_BUILD_SYSTEM 57): the runtime painterly instances (Art/setup_look_l6.bat); until they exist the plain ones below. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString StoneMaterialPath = TEXT("/Game/GrandTour/Materials/Painterly/MI_GT_Painterly_Stone");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString PostMaterialPath = TEXT("/Game/GrandTour/Materials/Painterly/MI_GT_Painterly_Post");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString RockMaterialPath = TEXT("/Game/GrandTour/Materials/Painterly/MI_GT_Painterly_Rock");

	/** What the dressing wore before L6, used when a path above does not load (the stones and rocks, the posts). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString PlainStoneMaterialPath = TEXT("/Game/GrandTour/Materials/MI_Env_Greybox");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString PlainPostMaterialPath = TEXT("/Game/GrandTour/Materials/MI_Env_Marker");

	/** Look stage L3: the card mesh, the engine's plane (a PLACEHOLDER) until the owner's card or clump replaces it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	FString FoliageMeshPath = TEXT("/Engine/BasicShapes/Plane.Plane");

	/** Look stage L3: the card material (Art/setup_look_l3.bat). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	FString FoliageMaterialPath = TEXT("/Game/GrandTour/Materials/Foliage/MI_GT_FoliageCard_Scrub");

	/** Clumps a square metre (0.025: one per 40 m2) in the rows beside the road; 0 places none. PROPOSED. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	float FoliageDensity = 0.025f;

	/** No clump nearer than this to the edge of the road or of an alt route, m. PROPOSED. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	float FoliageRouteClearM = 6.f;

	/** At most this many clumps, the ones nearest the road kept. PROPOSED. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	int32 FoliageMaxClumps = 3000;

	/** Cards per clump, crossed (2 for the placeholder plane; an owner's clump mesh takes 1). PROPOSED. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	int32 FoliageCardsPerClump = 2;

	/** A card's size before the clump's scale, m. PROPOSED. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	float FoliageCardWidthM = 1.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	float FoliageCardHeightM = 1.5f;

	/** Each clump's scale, uniform between these. PROPOSED. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	float FoliageScaleMin = 0.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	float FoliageScaleMax = 1.3f;

	/** A card's foot this far below the ground under the clump's middle, cm (a slope under a flat card). PROPOSED. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Foliage")
	float FoliageSinkCm = 10.f;

	/** How much of a stone's height sits below the ground, 0..1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float StoneSinkFraction = 0.3f;

	/** Throws away every instance and places the spec's stones and posts on the spec's ground. Returns the instance count. */
	UFUNCTION(BlueprintCallable, Category = "GT|Terrain")
	int32 Rebuild(const FGTTerrainSpec& Spec);

	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	int32 StoneCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	int32 PostCount = 0;

	/** Water stage R1: how many rocks stand in the fords' channels (GTTerrain::FordRocks); since L6 the Rocks component's instances. */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	int32 FordRockCount = 0;

	/** Look stage L3: the foliage clumps placed, and their cards (the Foliage component's instances). */
	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	int32 FoliageCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	int32 FoliageCardCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Terrain")
	FString LastMessage;

	/** The dressing actor of a world, or none. */
	static AGTTerrainDressing* Find(UWorld* World);

private:
	/** Look stage L3: the foliage clumps' transforms, world space. */
	void PlaceFoliage(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, TArray<FTransform>& OutCards);
};
