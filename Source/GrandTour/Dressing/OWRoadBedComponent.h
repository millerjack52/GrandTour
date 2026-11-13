#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"

#include "OWRoadBedComponent.generated.h"

/**
 * Per-road "Apply Bed & Verge" button (user 2026-07-30). Select a road
 * actor, press the button in its Details panel, and THIS road's spline
 * carves its bed into the landscape and paints the OW_RoadVerge layer
 * (the grass kill-switch) - no console, no script, no other roads
 * touched.
 *
 * Deliberately EXPLICIT, never automatic: landscape carving is
 * destructive and one-way, so firing it on every spline drag would
 * accumulate ghost trenches along every route the user experiments with.
 *
 * Both silent-failure paths this replaces are engine contracts, not
 * guesses (paid 2026-07-30, canvas road round - the script reported
 * success and did nothing):
 *   1. PaintLayer must be the layer info object THIS landscape is
 *      configured with, and every map owns its own *_LayerInfo assets
 *      (LandscapeProxy.h ~L1036) - so it is resolved from the
 *      landscape's own TargetLayers map, never by asset-name search.
 *   2. An edit-layer name the landscape does not have makes the engine
 *      bail out of the WHOLE apply - heights included
 *      (LandscapeBlueprintSupport.cpp:28-31) - so it is resolved from
 *      ALandscape::GetEditLayers() instead of hardcoding "Layer".
 * Every failure reports loudly (editor toast + log), never silently.
 *
 * Knob defaults mirror Scripts/ClaudePaintRoadVerge.py (snapshot
 * doctrine: component defaults = script constants = the
 * RoadLookRoundPlan table).
 */
UCLASS(ClassGroup = (OWGame), meta = (BlueprintSpawnableComponent),
	DisplayName = "OW Road Bed")
class GRANDTOUR_API UOWRoadBedComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	/** Carve the terrain up/down to meet the spline. Off = paint only. */
	UPROPERTY(EditAnywhere, Category = "OW Road Bed")
	bool bDeformBed = true;

	/** Half-width in spline-local space (200 = the 400-wide road bed). */
	UPROPERTY(EditAnywhere, Category = "OW Road Bed")
	float HalfWidth = 200.0f;

	/** Blend shoulder for the CARVE - wide, so the bed melts into the
	 *  surrounding terrain instead of leaving a vertical seam. */
	UPROPERTY(EditAnywhere, Category = "OW Road Bed")
	float DeformSideFalloff = 250.0f;

	/** Falloff for the verge PAINT - 0 keeps the kill zone exactly the
	 *  road bed, so grass grows right up to the road edge. */
	UPROPERTY(EditAnywhere, Category = "OW Road Bed")
	float PaintSideFalloff = 0.0f;

	/** Samples along the spline; higher = smoother bed, slower apply. */
	UPROPERTY(EditAnywhere, Category = "OW Road Bed")
	int32 NumSubdivisions = 40;

	/** Painted target layer whose weight drives the grass kill-switch. */
	UPROPERTY(EditAnywhere, Category = "OW Road Bed")
	FName VergeLayerName = FName(TEXT("OW_RoadVerge"));

	/** Landscape edit layer to write into. None = this landscape's first
	 *  edit layer (correct on every map; a wrong name aborts the apply). */
	UPROPERTY(EditAnywhere, Category = "OW Road Bed")
	FName EditLayerName = NAME_None;

#if WITH_EDITOR
	/** Carve this road's bed + paint its verge, once, now. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "OW Road Bed",
		DisplayName = "Apply Bed & Verge")
	void ApplyBedAndVerge();
#endif
};
