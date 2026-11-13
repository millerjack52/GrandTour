#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTDressingExclusion.generated.h"

class UBoxComponent;
class UGTTerrainSpecAsset;

/**
 * Leg dressing LD3 (docs/LEG_DRESSING_PLAN.md section 2.5): where the OW PCG graphs must not dress a leg. An editor-only
 * actor tagged OWDressing.Exclude - every OW / GT biome graph subtracts the primitive bounds of actors with that tag
 * (OWCreateBiomePCGCommandlet's exclusion getter) - holding box components built from the leg's terrain spec and the
 * gameplay actors in its world, never placed by hand:
 *  - the main route and every alt route: oriented boxes every RouteBoxLengthM (10 m), half as wide as the road there
 *    (GTTerrain::HalfWidthAt: the section's width scale) or the alt route's HalfWidthM, plus RouteClearM (4 m), and
 *    RouteBoxHeightM (10 m) tall round the ground under them (taller where that ground spans more than 6 m);
 *  - every Mud and Ford section: its extent (its route points every 2 m, +- the road's half width) plus SectionMarginM
 *    (10 m); every mud patch box (GTTerrain::MudPatchBoxCm) and deform patch box (DeformPatchBoxCm) plus PatchMarginM (5 m);
 *  - gameplay: AGTLegStart, AGTCheckpoint, AGTExtractionZone, every actor that implements IGTInteractable or carries a
 *    UGTInteractionComponent (harvest nodes, loot, stations, anchors), and actors labelled Hide_*, Roof_*, Marker_* or
 *    Water_*: each one's bounds (its colliding components', else all of them, empty ones left out, else its location;
 *    LD7: a leg volume's Extent and a harvest node's GreyboxSize, the sizes they take at BeginPlay) plus GameplayMarginM (5 m).
 * The boxes are QueryOnly (PCG's overlap test needs a body) and ignore every channel, so nothing in a game ever hits them,
 * and they are hidden in game; the actor is editor-only, so a cooked game never has it at all.
 */
UCLASS(hidecategories = (Rendering, Replication, Input, LOD, Cooking, HLOD, Physics, Networking))
class GRANDTOUR_API AGTDressingExclusion : public AActor
{
	GENERATED_BODY()

public:
	AGTDressingExclusion();

	/**
	 * LD7 (paid 2026-09-27): a game world on uncooked content (-game, PIE) still loads this editor-only actor, and its
	 * QueryOnly boxes answer object-type queries (WorldStatic): the ground traces of the water field, the leg volumes'
	 * markers and the tests landed on the route boxes' tops. The boxes that exist when play begins get NoCollision; the
	 * editor world never begins play, so PCG's overlap test keeps its bodies.
	 */
	virtual void BeginPlay() override;

	/** The tag every OW / GT biome graph subtracts. */
	static const FName ExcludeTag;

	/** The leg's terrain spec (DA_Terrain_*): what Rebuild and RebuildFromSpec(null) build from. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Dressing")
	TObjectPtr<UGTTerrainSpecAsset> SpecAsset;

	/** Clear ground beyond the road's edge each side, m (the plan's DressingRouteClearM). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Dressing")
	float RouteClearM = 4.f;

	/** A route box's length along the line, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Dressing")
	float RouteBoxLengthM = 10.f;

	/** A route box's height, m (more where the ground under it spans more than this less 4 m). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Dressing")
	float RouteBoxHeightM = 10.f;

	/** A Mud or Ford section's extent grows by this, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Dressing")
	float SectionMarginM = 10.f;

	/** A mud patch or deform patch box grows by this, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Dressing")
	float PatchMarginM = 5.f;

	/** A gameplay actor's bounds grow by this, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Dressing")
	float GameplayMarginM = 5.f;

	/** Actors whose label starts with one of these count as gameplay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Dressing")
	TArray<FString> GameplayLabelPrefixes;

	/**
	 * Throws away every box and builds them again from InSpecAsset (null: SpecAsset; a given one is kept in SpecAsset) and
	 * the gameplay actors in this actor's world now. Returns the box count (0 with no spec).
	 */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "GT|Dressing")
	int32 RebuildFromSpec(UGTTerrainSpecAsset* InSpecAsset);

	/** The Details panel's button (a CallInEditor function with a parameter gets none): RebuildFromSpec(SpecAsset). */
	UFUNCTION(CallInEditor, Category = "GT|Dressing")
	void Rebuild();

	/** The boxes, in build order: the main route's, the alt routes', the sections', the patches', the gameplay actors'. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	TArray<TObjectPtr<UBoxComponent>> Boxes;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	int32 RouteBoxCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	int32 AltBoxCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	int32 SectionBoxCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	int32 PatchBoxCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	int32 GameplayBoxCount = 0;

	/** The length of the main route and of all the alt routes the route boxes cover, m. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	float CoveredRouteM = 0.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	float CoveredAltM = 0.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Dressing")
	FString LastMessage;

private:
	/** One QueryOnly, all-ignoring, hidden-in-game box, world space (the actor stays where it is). */
	UBoxComponent* AddBox(const FVector& CentreCm, const FRotator& Rotation, const FVector& HalfExtentCm);
	void ClearBoxes();
};
