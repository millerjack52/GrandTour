// Bed-stamp landscape patch: non-destructive, drag-able sculpt stamps:
// channels, steps, hillside benches.
//
// CONTROL CONTRACT (Docs/WorldToolsRoundPlan.md section 0):
//  - C1 user-placed only: nothing here spawns/moves/deletes a stamp.
//  - C3 no auto-fire: no tick, no construction-script randomness. The stamp
//    texture is rebuilt only on PostEditChangeProperty / PostLoad / OnRegister.
//  - C4 every shape parameter is a Details knob; the C++ defaults below are
//    only the shipped-default snapshot of the existing carve machinery.
//  - C7 default blend is Min (cut-only): stamps lower terrain, never raise it,
//    unless the user flips the inherited Blend Mode knob.

#pragma once

#include "CoreMinimal.h"
#include "LandscapeTexturePatch.h"

#include "OWBedStampComponent.generated.h"

class UTexture2D;

/** Profile shape evaluated into the stamp's height/alpha texture. */
UENUM(BlueprintType)
enum class EOWBedStampShape : uint8
{
	/** Flat bed along local X with smoothstep shoulders on both sides. */
	Channel,
	/** Round bowl: flat floor, smoothstep rim. */
	Pool,
	/** Downstream half dropped by DropCm across a sharp lip. */
	Step,
	/** Flat shelf cut into a cross-slope, back wall daylighting into +Y. */
	Bench
};

/**
 * Landscape texture patch that generates its own height + alpha texture from a
 * handful of profile knobs. Editor-only (inherited from ULandscapePatchComponent,
 * IsEditorOnly() == true) and therefore cook-stripped.
 */
UCLASS(ClassGroup = OWGame, meta = (BlueprintSpawnableComponent, DisplayName = "OW Bed Stamp"))
class UOWBedStampComponent : public ULandscapeTexturePatch
{
	GENERATED_BODY()

public:
	UOWBedStampComponent(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());

	/** Profile shape. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp")
	EOWBedStampShape Shape = EOWBedStampShape::Channel;

	/** Channel/Pool floor depth below the stamp actor Z, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "10", ClampMax = "800", UIMin = "10", UIMax = "800"))
	float DepthCm = 200.f;

	/** Channel: half width of the flat bed, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "50", ClampMax = "2000", UIMin = "50", UIMax = "2000"))
	float BedHalfWidthCm = 380.f;

	/** Width of the smoothstep shoulder that daylights the cut, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "10", ClampMax = "1000", UIMin = "10", UIMax = "1000"))
	float ShoulderFalloffCm = 250.f;

	/** Channel/Step/Bench: length along local X, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "500", ClampMax = "20000", UIMin = "500", UIMax = "20000"))
	float LengthCm = 3000.f;

	/** Pool: outer radius, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "200", ClampMax = "4000", UIMin = "200", UIMax = "4000"))
	float RadiusCm = 900.f;

	/** Step: width across flow (local Y), in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "200", ClampMax = "4000", UIMin = "200", UIMax = "4000"))
	float StepWidthCm = 800.f;

	/** Step: height dropped by the downstream half, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "20", ClampMax = "500", UIMin = "20", UIMax = "500"))
	float DropCm = 150.f;

	/** Step: length along local X over which the drop happens, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "10", ClampMax = "400", UIMin = "10", UIMax = "400"))
	float LipSharpnessCm = 60.f;

	/** Bench: shelf width on the -Y side of the stamp, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "100", ClampMax = "3000", UIMin = "100", UIMax = "3000"))
	float BenchHalfWidthCm = 650.f;

	/** How far above the stamp Z the profile daylights before alpha reaches 0, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "50", ClampMax = "900", UIMin = "50", UIMax = "900"))
	float HeadroomCm = 300.f;

	/** Alpha feather at the +/-X ends so chained stamps blend into each other, in cm. */
	UPROPERTY(EditAnywhere, Category = "OW Bed Stamp", meta = (ClampMin = "0", ClampMax = "2000", UIMin = "0", UIMax = "2000"))
	float EndFeatherCm = 400.f;

#if WITH_EDITOR
	// UObject
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
	virtual void PostLoad() override;

	// UActorComponent
	virtual void OnRegister() override;
#endif

private:
	/** Generated height (R) + alpha (A) texture. Owned by this component, not an asset. */
	UPROPERTY()
	TObjectPtr<UTexture2D> StampTexture;

#if WITH_EDITOR
	/** Recomputes coverage + stamp texture from the knobs and pushes them to the patch. */
	void RebuildStamp();
#endif
};
