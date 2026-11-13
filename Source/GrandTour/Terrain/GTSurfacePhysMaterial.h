#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "GTSurfacePhysMaterial.generated.h"

/**
 * The single source of truth for what is under a wheel (ARCHITECTURE 6a). Assigned to landscape
 * layers and drivable meshes. Dry grip is the inherited Friction (Chaos multiplies tyre grip by
 * it directly); the fields here drive UGTTractionComponent (wet grip, rolling drag, sinkage) and
 * the track paint (TrackDepth).
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTSurfacePhysMaterial : public UPhysicalMaterial
{
	GENERATED_BODY()

public:
	/** Surface.Tarmac, Surface.Mud, ... used by audio, VFX, dirt and the dash. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface")
	FGameplayTag SurfaceTag;

	/** Grip when fully wet, relative to dry (1 = unchanged). Wet tarmac ~0.75, mud ~0.95. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0, ClampMax = 1.5))
	float WetFrictionScale = 0.8f;

	/** Rolling drag multiplier when fully wet (rain turns dirt toward mud). Tarmac 1, dirt 1.6. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0.5, ClampMax = 5))
	float WetRollingResistanceScale = 1.f;

	/** Multiplier on SinkageRate and MaxSinkage when fully wet. Dirt 3 (it sinks like shallow mud), mud 1.3. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0.5, ClampMax = 10))
	float WetSinkageScale = 1.f;

	/** Rolling resistance coefficient: drag force = coefficient x wheel load. Tarmac 0.012, mud 0.12. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0))
	float RollingResistance = 0.012f;

	/** Sinkage growth in metres per second for a wheel at standstill; 0 means firm ground. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0))
	float SinkageRate = 0.f;

	/** Sinkage cap in metres. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0))
	float MaxSinkage = 0.f;

	/** Extra rolling resistance at full sinkage, as a multiple of RollingResistance. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0))
	float SinkageDragScale = 2.f;

	/**
	 * Ploughing drag: fraction of wheel load at full sinkage and 10 m/s, growing with the square
	 * of speed. Negligible when crawling out, brutal when hitting deep mud at 80 km/h.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0))
	float PloughDrag = 0.f;

	/** Fraction of grip lost at full sinkage. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0, ClampMax = 1))
	float SinkageGripLoss = 0.3f;

	/** Visual rut depth 0..1 for the track paint subsystem. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface", meta = (ClampMin = 0, ClampMax = 1))
	float TrackDepth = 0.f;

	/** Benmore integration B1: this surface throws gravel grit and dust (the spray's gravel layers, as a gravel patch does). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface")
	bool bGravelSpray = false;

	/** The gravel grit's two tints (linear). Zero = the spray code's own defaults. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface")
	FLinearColor SprayTintA = FLinearColor(0.f, 0.f, 0.f, 0.f);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface")
	FLinearColor SprayTintB = FLinearColor(0.f, 0.f, 0.f, 0.f);

	/** The gravel dust's tint (linear). Zero = the spray code's own default. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Surface")
	FLinearColor DustTint = FLinearColor(0.f, 0.f, 0.f, 0.f);
};
