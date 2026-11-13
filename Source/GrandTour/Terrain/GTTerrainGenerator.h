#pragma once

#include "CoreMinimal.h"
#include "GTTerrainGenerator.generated.h"

/** A landform laid over the noise: a hill or a bowl at a point, a ridge or a channel along a line. */
UENUM(BlueprintType)
enum class EGTTerrainFeatureKind : uint8
{
	Hill,
	Bowl,
	Ridge,
	Channel
};

USTRUCT(BlueprintType)
struct FGTTerrainFeature
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	EGTTerrainFeatureKind Kind = EGTTerrainFeatureKind::Hill;

	/** Metres. Hill / Bowl: the centre. Ridge / Channel: the line's start. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FVector2D StartM = FVector2D::ZeroVector;

	/** Metres. Ridge / Channel: the line's end. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FVector2D EndM = FVector2D::ZeroVector;

	/** Metres from the centre or the line at which the feature has faded to nothing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float RadiusM = 50.f;

	/** Metres at the centre; a bowl and a channel dig by this much. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float HeightM = 10.f;
};

/** A stretch of the route (by arc length) and the surface layer it is paved with: 0 tarmac, 1 dirt, 2 mud, 3 snow. */
USTRUCT(BlueprintType)
struct FGTSurfaceSpan
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float StartM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float EndM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	int32 Layer = 1;
};

/**
 * What a stretch of the route is for (the MudRunner / SnowRunner reference with rally stretches, PROJECT_PLAN 6):
 * it sets the road's width, how closely it follows the land, its steepest grade, whether it banks into bends,
 * and what it is made of. Anything not covered is Road.
 */
UENUM(BlueprintType)
enum class EGTRouteSectionKind : uint8
{
	/** The plain road: full width, the land smoothed over RouteSmoothM, grades to MaxGradePercent, the spans' surface. */
	Road,
	/** A narrow track: TrackWidthScale of the width, otherwise a road. */
	Track,
	/** A rally stretch: a little wider, follows the land over RallySmoothM (crests and dips), grades to RallyGradePercent, banks into bends. */
	Rally,
	/** A bog: wider by MudWidthScale, the road sunk MudSinkM into a trough, mud all across. */
	Mud,
	/** A water crossing: the road drops into the ground's channel at FordGradePercent, a firm Dirt bed (Mud with FGTTerrainSpec::bFordBedMud, M6 stage 3's bed), water to DepthM above the lowest point. */
	Ford,
	/**
	 * Living mud LM3a (docs/LIVING_MUD_PLAN.md): a road-like stretch under deep snow. Wider by SnowWidthScale, no sink, the
	 * Snow layer (3) across the paving. Its patch takes FGTTerrainSpec::SnowProfile (ByKind; a section's own Deform with
	 * Mode On overrides it), whose medium is snow: a snow top SnowDepthCm over the ground (SnowDrifts deepen stretches of
	 * it), compacted by the tyres to their own bottom. Appended after Ford so saved specs keep their values.
	 */
	Snow
};

/** Living mud LM3a: what a deformation profile's patch is made of. Mud is every patch before LM3a; Snow has a snow top over the ground that the tyres and the belly cut down into. */
UENUM(BlueprintType)
enum class EGTDeformMedium : uint8
{
	Mud,
	Snow,
	/** Shallow granular ground on the same field; its section profile supplies the gravel response and material. */
	Gravel
};

/**
 * Living mud LM3a: a deeper stretch of a Snow section (a depth curve along the route, like a Rally section's Bumps): from
 * StartM to EndM along the main route the snow stands DepthCm, blending from the profile's SnowDepthCm over RampM beyond
 * each end (a smoothstep). The patch bakes the depth per cell from the nearest point of the route.
 */
USTRUCT(BlueprintType)
struct FGTSnowDrift
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float StartM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float EndM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float DepthCm = 60.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float RampM = 2.f;
};

/** A crest or a compression on the road (stage 2): a smooth bump on the route's profile, HeightM up (a crest: the car goes light or flies at speed) or down (a compression), foot to foot over LengthM. */
USTRUCT(BlueprintType)
struct FGTProfileBump
{
	GENERATED_BODY()

	/** Along the main route, m (the same arc marks as the sections). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float ArcM = 0.f;

	/** Positive a crest, negative a compression, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float HeightM = 0.8f;

	/** Foot to foot, m. A crest of 0.9 m over 24 m puts the car in the air at 90 km/h and not at 45. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float LengthM = 24.f;
};

/** RIVERBED S4 (2026-09-23, VEHICLE_BUILD_SYSTEM 54): whether a route section's ground deforms by its own profile. */
UENUM(BlueprintType)
enum class EGTDeformProfileMode : uint8
{
	/** By the section's kind: a Ford's bed deforms by the profile's numbers (a mud patch over it, the wheels inside it sink by the profile); a Mud section keeps its surface rows' numbers and the patch's own ridge numbers (the bog as tuned); any other kind does not deform. */
	ByKind,
	/** The profile, whatever the kind: a patch over the section, its numbers for the wheels inside it. */
	On,
	/** No profile: a Mud section keeps the rows' numbers, any other kind gets no patch. */
	Off
};

/**
 * Living mud LM5b (docs/LIVING_MUD_PLAN.md LM5b, docs/MUD_VARIANTS.md): which of the four churned bogs a Mud section is.
 * The look is the variant's slice of the bog texture arrays (M_GT_Mud, the landscape's apron round the patch, the clods);
 * the feel is FGTDeformProfile::MudVariantDefaults (Standard: no profile, the bog exactly as before LM5b). The order is the
 * texture arrays' slice order: never reorder, append.
 */
UENUM(BlueprintType)
enum class EGTMudVariant : uint8
{
	/** The approved A2 churn; the feel is today's bog (no profile). */
	Standard,
	/** Lighter mid-brown, matte lumps; sinks less, grips more. */
	Firm,
	/** Darker and wetter, broad glossy slurry; sinks more, the water stands higher. */
	Deep,
	/** The churn with gravel pressed in; sinks a little less, grips most. */
	Stony
};

/**
 * Mud roads MRD1 (docs/MUD_ROADS_PLAN.md MRD1 item 1): how a bog patch's pre-churn lays its old tracks (AGTMudPatch::PreChurn).
 */
UENUM(BlueprintType)
enum class EGTPreChurnStyle : uint8
{
	/** GR1c: 1-2 old rut pairs along the route line (the bog strips' default). */
	Pairs,
	/** MRD1: a mud road - 6-14 braided old tracks across the road width (crossing, merging, starting and ending at random),
	 *  power-law depths, torn walls on the deep ones, puddles in the low runs, churn zones with clod fields, partial old tread. */
	Braided
};

/**
 * RIVERBED S4 (2026-09-23, VEHICLE_BUILD_SYSTEM 54; the backlog's MUD DEFORMATION TUNABLES profile): how a section's ground
 * gives under a wheel inside its mud patch's box. SinkageRate and MaxSinkageM take the place of the surface row's two
 * numbers for any wheel inside the box on ground that sinks at all (a row with a MaxSinkage over 0: tarmac stays firm);
 * the row's wet scale and everything else of the row still apply. The ridge numbers are copied into the patch (and from it
 * into its field) by UGTMudSubsystem::BuildPatches, as the section's WaterTableCm is. The defaults are the ford bed's
 * starting profile, PROPOSED and UNMEASURED: MaxSinkage 10 cm and SinkageRate 0.02 m/s (the Dirt row's 5 cm and 0.01 x 2),
 * the bog's ridge numbers as AGTMudPatch has them since stage I/J. The owner names them after driving a ford.
 */
USTRUCT(BlueprintType)
struct FGTDeformProfile
{
	GENERATED_BODY()

	/** ByKind (the default) gives every Ford section this profile and leaves a Mud section on its rows, so a spec asset never edited follows it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	EGTDeformProfileMode Mode = EGTDeformProfileMode::ByKind;

	/** Optional field-surface material (must accept MudField, MudTread and PatchMin/Size/Texels).
	 * Empty preserves the existing mud/snow material. Allows shallow gravel to use the same physical field. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Appearance")
	FString SurfaceMaterialPath;

	/** Deformable gravel DG1 item 3 (docs/DEFORMABLE_GRAVEL_PLAN.md): on a Gravel section, its loose stones per m^2 of road (the
	 *  study's rule: about 30 Loose, 12 Firm), times gt.Gravel.StoneDensity; 0 (every other profile) draws none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Gravel")
	float GravelStonesPerM2 = 0.f;
	/** Deformable gravel DG1b: how far the field material's texture slides with the field's offset (M_GT_Gravel's GravelSlideUV), x mud's
	 *  (whose SlideUV is 1). The gravel profiles' is 0.25; the mud materials do not read it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Gravel")
	float TextureSlideScale = 1.f;

	/** m/s while rolling through it (the row's SinkageRate: settling 30 % of it at rest, wheelspin adds up to 150 %). Proposed 0.02, Dirt's x 2. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float SinkageRate = 0.02f;

	/** m, the deepest a wheel goes (the row's MaxSinkage); inside the box the Chaos radius shrinks by all of it. Proposed 0.10, Dirt's x 2. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float MaxSinkageM = 0.10f;

	// ---- the ridge numbers, AGTMudPatch's (stage H and I) as the bog has them; see AGTMudPatch for what each one does ----
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeBlend = 0.9f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeSmooth = 0.7f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeNoise = 0.7f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float FloorNoiseCm = 1.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeWidthCm = 90.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float MaxRidgeCm = 12.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeFootCm = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeWaveCm = 250.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeWaveLongCm = 600.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeWave = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeWidthWave = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeSideBias = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeSlump = 0.25f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeSlumpFloor = 0.333f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeSlumpRiseMaxCm = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeFillShare = 0.35f;
	/** LM2a: 0 with the lumps on (stage I's 0.15 stays a code path). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float ClodChance = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float ClodMinCm = 8.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float ClodMaxCm = 15.f;

	// ---- LM1, the living field (docs/LIVING_MUD_PLAN.md): AGTMudPatch's settle numbers. A ford's bed is stiffer than the
	// bog: a steeper repose (45), a small recovery (LM1b's RecoverShare 0.02; LM1's ooze 0.1 is off, as the bog's is) and
	// a short set (1.5 s); the rest as the bog has them.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float ReposeDeg = 45.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float SlumpRate = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float OozeRate = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float RecoverShare = 0.02f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float CreepCmPerCm = 3.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float SetSeconds = 1.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float SmearCmPerCm = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float FreshFadeS = 6.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float SleepCmPerS = 0.05f;
	/** LM2a housekeeping 1: the fresh mark's threshold, cm a stamp or sub-step moves the surface. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Settle")
	float FreshMinCm = 0.002f;

	// ---- LM2a, lumps and the throw (docs/LIVING_MUD_PLAN.md LM2a): AGTMudPatch's numbers, the bog's as proposed ----
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpShare = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpSpacingCells = 4.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpRadiusCells = 1.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpMaxCm = 10.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float ThrowMax = 0.5f;

	// ---- LM3a housekeeping 3, profile-owned variety (docs/LIVING_MUD_PLAN.md LM3a): LM2c's numbers, copied in BuildPatches
	// like the rest, so snow sets its own. The defaults are the field's / the patch's as LM2c shipped them, so a ford's
	// bed (the only profiled patch before LM3a) is unchanged; AGTMudPatch::bLumpVariety stays the master switch.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpAbsentShare = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpClusterCm = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpAmpMin = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpAmpMax = 1.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpAspectMax = 2.2f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpVarietyRadiusJitter = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpSatelliteChance = 0.2f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float ClodBankPerCm = 0.017f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float ClodThrowChance = 0.065f;

	// ---- LM3a, snow (docs/LIVING_MUD_PLAN.md LM3a). The defaults are mud's (the field's own numbers before LM3a); a Snow
	// section's are FGTDeformProfile::SnowDefaults() (FGTTerrainSpec::SnowProfile).
	/** Mud (every profile before LM3a) or Snow: a snow top over the ground that the tyres cut to their own bottom. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	EGTDeformMedium Medium = EGTDeformMedium::Mud;
	/** The fresh snow's depth over the ground, cm (a section's SnowDrifts deepen stretches of it). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SnowDepthCm = 35.f;
	/** The snow tapers to nothing over this many cm in from the patch box's border (a smoothstep), so it meets the landscape at the edge. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SnowEdgeCm = 300.f;
	/** The share of what a tyre cuts that comes back up beside it (the field's RidgeReturn; snow compacts: 0.2). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RidgeReturn = 0.6f;
	/** The rut wall's width (the field's RutShoulderCm), and the fewest cells it may span (the field's 2 before LM3a; snow 1, so RutShoulderCm 10 stands). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RutShoulderCm = 45.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RutShoulderMinCells = 2.f;
	/** The firmer pockets' share of the depth (the field's RutDepthVariation). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ridge")
	float RutDepthVariation = 0.35f;
	/** Snow: the share of what the belly ploughs that goes into a PloughBandCm band beside its box (berms). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PloughReturn = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PloughBandCm = 40.f;
	/** Snow (LM3c follow-up): the share of the plough's berm deposit held for the lump domes (the tyres' lips keep LumpShare). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PloughLumpShare = 0.25f;
	/** Snow (LM3c follow-up): the berm's share of the bank's height swings (RidgeWave, RidgeSideBias, RidgeNoise; 1 = the lips'). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PloughBankVariation = 1.f;
	/** Snow: while it snows every cell below the snow top rises this many cm a minute toward it (tracks fade and lumps soften at the same rate). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float RefillCmPerMin = 2.f;
	/** Snow: the plough drag of the uncut snow ahead of a tyre, the bog's plough term with (snow surface ahead - tyre bottom) / wheel radius in place of the sinkage fraction. Proposed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SnowPlough = 0.35f;
	/** LM3b: a scale on the belly's drag in snow (UGTTractionComponent's BellyDragPerMetre x the snow standing over its underside); 1 is LM3a's. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SnowBellyDrag = 1.f;

	// ---- LM4, God of War snow deformation (docs/LIVING_MUD_PLAN.md LM4). Every default is the value in force before LM4
	// (mud's, and LM3c's snow at 12.5 cm), so a bog and a ford's bed are unchanged; SnowDefaults() states snow's.
	/** LM4 item 1: the field's cell, cm (the patch mesh follows it). Mud 12.5; snow 6.25 (gt.Snow.FineGrid 0 builds a snow patch at 12.5 with every cell-unit number below rescaled to keep its size in cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float CellCm = 12.5f;
	/** LM4 item 1, the cell-unit numbers that were the field's own (now the profile's, stated at CellCm): stage H's ridge clumps, the settle tile, the rut floor's noise wavelength, the firmer pockets' wavelength and the tracks' ragged edge, in cells. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float RidgeNoiseCells = 4.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	int32 SettleTileCells = 16;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float FloorNoiseCells = 5.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float PocketNoiseCells = 12.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float TracksEdgeCells = 3.f;
	/** LM4 item 2 (snow): the lump kernel is a crust plate - each lump site owns its Voronoi cell and its lump is a flat plane tilted PlateTiltMinDeg..PlateTiltMaxDeg toward a random azimuth, clipped to the cell. False: LM2c's domes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	bool bLumpPlates = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float PlateTiltMinDeg = 5.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float PlateTiltMaxDeg = 25.f;
	/** LM4 item 3 (snow): the cut's half-width steps by WallStepMinCm..WallStepMaxCm either way, piecewise constant over WallSegMinCm..WallSegMaxCm segments (0: a smooth wall line); WallDropShare of the segments drop their lip plate into the trench (FloorChunkChance of them leave a chunk on the floor). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallStepMinCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallStepMaxCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallSegMinCm = 15.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallSegMaxCm = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallDropShare = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float FloorChunkChance = 0.f;
	/** LM4 item 6 (snow): the fresh snow's top undulates by about this sd, cm (static world noise at SnowTopWaveMinCm..SnowTopWaveMaxCm wavelengths; 0: flat). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SnowTopUndulationCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SnowTopWaveMinCm = 60.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SnowTopWaveMaxCm = 300.f;
	/** LM4 item 4: the bank clods' (snow: the shards') sizes, min + (max - min) u^power, cm (the patch's own numbers until LM4). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float ClodBankSizeMinCm = 3.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float ClodBankSizeMaxCm = 18.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float ClodSizePower = 2.5f;

	// ---- LM4b, soft shape and crumbly detail (docs/LIVING_MUD_PLAN.md LM4b). Every default is the value in force before LM4b
	// (mud's, and LM4's snow when the snow profile turns its own off), so a bog and a ford's bed are unchanged.
	/** LM4b item 1 (snow): with WallStepMaxCm 0 the wall line wanders by two octaves of continuous noise along the stroke, WallWaveAmpCm at WallWaveCm and WallWaveLongAmpCm at WallWaveLongCm (both 0: no wander). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallWaveCm = 25.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallWaveLongCm = 70.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallWaveAmpCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallWaveLongAmpCm = 0.f;
	/** LM4b item 2 (snow): the fallen-plate notch's ends feather over this many cells (0: LM4's hard notch). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallDropFeatherCells = 0.f;
	/** LM4b item 2 (snow): soft lumps - LM2c's domes leaning by a skew of LumpSkewMinDeg..LumpSkewMaxDeg, each re-shaped to its kernel with its peak at most min(LumpMaxCm, LumpHeightPerRadius x its radius); lip chunks from the domes' edges. False: LM2c's domes (or LM4's plates with bLumpPlates). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	bool bLumpSoftDomes = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpSkewMinDeg = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpSkewMaxDeg = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpHeightPerRadius = 0.f;
	/** LM4b item 2: the soft domes' height cap also scales by (the site's amplitude / the mean amplitude)^this, so LM2c's amplitude spread survives the cap (0: one cap per radius). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpCapAmpPower = 0.f;
	/** LM4b item 2: and by (its radius / the mean radius)^this (0: off). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Lumps")
	float LumpCapRadiusPower = 0.f;

	// ---- LM4c, piles not walls (docs/LIVING_MUD_PLAN.md LM4c). Every default is off (mud's, and LM4b's snow), so a bog and a
	// ford's bed are unchanged; SnowDefaults() states snow's.
	/** LM4c item 1 (snow): the talus per cell (a pair takes the higher cell's) - LooseReposeDeg above the snow top (the berm, the lip) and on a collapse's pile, WallReposeDeg +- WallReposeRangeDeg by world noise at WallReposeWaveMinCm..MaxCm below it. False: ReposeDeg everywhere. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	bool bCellRepose = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float LooseReposeDeg = 35.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallReposeDeg = 60.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallReposeRangeDeg = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallReposeWaveMinCm = 40.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float WallReposeWaveMaxCm = 80.f;
	/** LM4c item 2 (snow): CollapseChance of the cut wall's CollapseSegMinCm..MaxCm segments collapse CollapseDelayMinS..MaxS after a stamp last cut them: their top CollapseTopMin..Max (above the floor, the lip included) as a cone pile on the trench floor at the wall's foot, the notch's ends feathered over CollapseFeatherCells, CollapseClumpsMin..Max clumps on the pile (0: off). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float CollapseChance = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float CollapseSegMinCm = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float CollapseSegMaxCm = 80.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float CollapseDelayMinS = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float CollapseDelayMaxS = 3.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float CollapseTopMin = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float CollapseTopMax = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float CollapseFeatherCells = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	int32 CollapseClumpsMin = 1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	int32 CollapseClumpsMax = 2;
	/** LM4c item 3 (snow): the plough's band falls from the wall outward ((1 - u)^2) in place of stage I's plateau; the plough's and the lips' deposits scaled along the trench by PileClusterMin..Max at a world noise of PileWaveMinCm..MaxCm (1 / 1: off). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	bool bPloughFallingProfile = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PileClusterMin = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PileClusterMax = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PileWaveMinCm = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PileWaveMaxCm = 250.f;

	// ---- LM4d, the belly's channel isn't flat (docs/LIVING_MUD_PLAN.md LM4d). Every default is off (LM4c's level channel).
	/** LM4d (snow): the plough's target undulates +-BellyUndulationCm (two octaves at BellyWaveMinCm / BellyWaveMaxCm across, BellyStretch longer along the heading's axis); smear ridges along it (SmearChance of SmearLaneCm lanes' SmearLength segments, SmearWidth wide, SmearHeight high, bunched at SmearClusterCm), out of the plough's return; PloughSpillShare of its side deposit back into the channel as soft lumps, SpillClumpChance of the sites a clump. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float BellyUndulationCm = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float BellyWaveMinCm = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float BellyWaveMaxCm = 60.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float BellyStretch = 2.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearChance = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearLaneCm = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearLengthMinCm = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearLengthMaxCm = 80.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearWidthMinCm = 8.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearWidthMaxCm = 15.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearHeightMinCm = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearHeightMaxCm = 3.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SmearClusterCm = 120.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float PloughSpillShare = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Snow")
	float SpillClumpChance = 0.f;

	// ---- LM5b, the four churned-bog variants (docs/LIVING_MUD_PLAN.md LM5b, docs/MUD_VARIANTS.md). Every default is the
	// identity (scales 1, offset 0, bScalesRows false), so a ford's bed and a snow patch are unchanged.
	/**
	 * LM5b: a mud variant's profile (MudVariantDefaults). It does not replace the rows: the patch stays a bog's (the surface
	 * rows and their Mud/Bog tag gate, bHasProfile false, every number the bog's), the rows' sinkage and friction scaled by
	 * the three scales below, RecoverShare, LumpShare and ThrowMax from here and the section's water table moved by
	 * WaterTableOffsetCm. Everything else in the struct is ignored. False: the profile replaces the rows (RIVERBED S4).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Variant")
	bool bScalesRows = false;
	/** LM5b: a scale on the MaxSinkage a wheel inside the patch takes (the row's on a bog, the profile's on a profiled patch). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Variant")
	float MaxSinkageScale = 1.f;
	/** LM5b: a scale on the SinkageRate a wheel inside the patch takes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Variant")
	float SinkageRateScale = 1.f;
	/** LM5b: a scale on the friction of the row a wheel inside the patch stands on (UGTTractionComponent's FrictionScale: the Chaos friction circle, the slip graph and the drive cap alike, as a row with that much more Friction). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Variant")
	float FrictionScale = 1.f;
	/** LM5b: cm added to the section's WaterTableCm (Deep's +10: the water stands 10 cm higher in its ruts). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Variant")
	float WaterTableOffsetCm = 0.f;
	/**
	 * MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4): the soft spots' amplitude on a mud variant's patch, S = 0.5 + (S0 - 0.5)
	 * x this (AGTMudPatch::BuildSoftness). 1 the full spread (Standard, which has no profile, uses 1), 0 S 0.5 everywhere. Read
	 * only with bScalesRows (a profiled patch has no soft spots). Proposed: Firm 0.5, Deep 0.6, Stony 0.6 (the owner names them).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Variant")
	float SoftSpotAmplitude = 1.f;
	/**
	 * MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5): the multiplier on a mud variant's patch's chunk density (AGTMudPatch::
	 * MudChunkDensityPerM2, 1 per 25 m^2 of candidate ground). Read only with bScalesRows (Standard, which has no profile, uses 1).
	 * Proposed: Firm 0.5, Deep 1.5, Stony 1 (the owner names them).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Variant")
	float ChunkDensityScale = 1.f;
	/**
	 * Ground relief GR1 (docs/GROUND_RELIEF_PLAN.md GR1 item 4): a bog patch's pre-churn at Init - old rut pairs along the route
	 * line (GR1b: cosine troughs and banks, partly filled, then 10 s of the field's settle), hummocks, the rim faded (AGTMudPatch::PreChurn).
	 * 0 (the default) a flat field as before; the strips' bog sections 1 (it scales the old tracks' depth and the hummocks).
	 * AGTMudPatch::ApplySection reads the section's own Deform.PreChurnScale whatever its Mode, so a ByKind bog (Standard, or a
	 * variant whose profile is MudVariantDefaults) takes it without a profile of its own. Read only on a Mud-medium bog patch.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float PreChurnScale = 0.f;
	/** Mud roads MRD1 item 1: the pre-churn's layout (Pairs, GR1c's, the default; Braided, a mud road). Read whatever the Mode, as PreChurnScale. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	EGTPreChurnStyle PreChurnStyle = EGTPreChurnStyle::Pairs;
	/** Mud roads MRD1 item 4: the mud road's spray multiplier (1; 2 on MudRoad profiles, Ref5's denser throw). Only the number:
	 *  the spray code that reads it (AGTMudPatch::MudRoadSprayScale) is Benmore B1b's. Read whatever the Mode. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float MudRoadSprayScale = 1.f;
	/** Mud roads MRD1 item 3: sticks and branches per m^2 of the road band on a braided patch (mud roads 0.03-0.08, clustered); 0 none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float RoadDebrisPerM2 = 0.f;
	/** Mud roads MRD1b item 3, the silt surface: the bog bake's tiling divided by this on the patch (M_GT_Mud SiltTileMul; mud roads 2)
	 *  and, on the running surface (off the ridges, lips and walls), the bake's lump normal, AO and parallax depth x RoadSiltStrength
	 *  (SiltStrength; mud roads 0.4). 1 and 1: the bog as before. Read whatever the Mode. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float RoadSiltTileMul = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float RoadSiltStrength = 1.f;

	/** LM4 item 1: every cell-unit number scaled by Factor (gt.Snow.FineGrid 0 builds the profile's patch at 12.5 cm with Factor = CellCm / 12.5, so each keeps its size in cm). */
	void ScaleCellUnits(float Factor)
	{
		WallDropFeatherCells *= Factor;   // LM4b
		CollapseFeatherCells *= Factor;   // LM4c
		RidgeNoiseCells *= Factor;
		LumpSpacingCells *= Factor;
		LumpRadiusCells *= Factor;
		RutShoulderMinCells *= Factor;
		SettleTileCells = FMath::Max(1, FMath::RoundToInt(SettleTileCells * Factor));
		FloorNoiseCells *= Factor;
		PocketNoiseCells *= Factor;
		TracksEdgeCells *= Factor;
	}

	/** LM3a: the snow numbers of the plan (docs/LIVING_MUD_PLAN.md LM3a and its housekeeping item 4), on top of this struct's defaults. */
	static GRANDTOUR_API FGTDeformProfile SnowDefaults();

	/**
	 * LM5b: a mud variant's feel (docs/LIVING_MUD_PLAN.md LM5b's table, proposals the owner names after driving), on the
	 * SnowDefaults pattern: bScalesRows, the sinkage (cap and rate) and friction scales, and RecoverShare, LumpShare and
	 * ThrowMax starting from the bog's own (AGTMudPatch's defaults) with the table's numbers over them. Standard is the
	 * identity (GTTerrain::DeformProfileFor gives a Standard section no profile at all).
	 */
	static GRANDTOUR_API FGTDeformProfile MudVariantDefaults(EGTMudVariant Variant);
};

USTRUCT(BlueprintType)
struct FGTRouteSection
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float StartM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float EndM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	EGTRouteSectionKind Kind = EGTRouteSectionKind::Road;

	/** Ford: water depth over the lowest point of the crossing, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float DepthM = 0.6f;

	/**
	 * Ford only (docs/WATER_PLAN.md, stage W1): how fast the crossing runs, m/s. Art/setup_m6_hide.py hands it to the
	 * AGTWaterSheet it lays over the section; the sheet fades it out at its two ends (FlowFadeM) and the cvar
	 * gt.Water.FlowScale scales it in play. A spec asset never edited follows this default, so The Hide's ford runs at
	 * this speed without touching DA_Terrain_Hide.
	 * 1.5, not the plan's 2.0: measured, 2.0 m/s put 3.0 kN on the hull in the as-built 0.6 m, which is most of the
	 * lateral grip a muddy bed gives, and the crossing at 20 km/h could no longer be driven through (terrain step 13
	 * timed out 12 m short and the raised run was swept 14 m off the route).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float FlowSpeedMps = 1.5f;

	/**
	 * Ford only: which way it runs. The flow's yaw is the section's mid-route heading plus this offset, and Unreal's
	 * yaw is clockwise seen from above, so 90 runs the water across the route from the car's left to its right (the
	 * generator's "+ side").
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float FlowYawOffsetDeg = 90.f;

	/**
	 * Mud (docs/MUD_ONE_SURFACE_PLAN.md stage G): where this bog's water table stands, cm relative to the *undisturbed
	 * ground* at each point - negative is below it, so untouched mud is dry and only a rut cut deeper than this holds
	 * water. -25 puts about 5 cm in a 30 cm rut (stage J3, 2026-09-16: the user asked for the waterline lowered "maybe
	 * by half" after -20 held 10.8 cm in the test's 30.8 cm rut). There is no plane per bog: the water surface follows
	 * the ground cell by cell (AGTMudPatch's WaterMesh), and the weather lifts it by AGTMudPatch::WetTableLiftCm x
	 * wetness, as AGTWaterSheet lifts a ford. A ford's water is its own sheet actor and has nothing to do with this.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float WaterTableCm = -25.f;

	/**
	 * Ford only (The Proving Ground, 2026-09-19): how many rocks this ford gets. -1 (the default) takes the spec's
	 * FordRockCount, as every ford did before; 0 leaves this one clear (the Proving Ground's deep ford).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	int32 FordRockCountOverride = -1;

	/** Rally: the crests and compressions on this stretch (arc along the route, height, length); added on top of the grade-limited profile. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	TArray<FGTProfileBump> Bumps;

	/** RIVERBED S4: the deformation profile (ByKind: a Ford's bed deforms by it, a bog keeps its rows, LM3a: a Snow section takes FGTTerrainSpec::SnowProfile). GTTerrain::DeformProfileFor says whether it applies. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FGTDeformProfile Deform;

	/**
	 * Living mud LM5b, Mud only (docs/MUD_VARIANTS.md): which churned bog this is. The look is the variant's texture slice
	 * everywhere in the patch (and the landscape's apron round it and the clods); with Deform on ByKind (the default) the feel
	 * is FGTDeformProfile::MudVariantDefaults (Standard: none, the bog as before). Deform Mode On replaces the feel with the
	 * section's own profile, Off keeps the rows unscaled; the look stays the variant's either way.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	EGTMudVariant MudVariant = EGTMudVariant::Standard;

	/** LM3a, Snow only: the deeper stretches of this section's snow (arc along the route, depth, ramp); the profile's SnowDepthCm elsewhere. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	TArray<FGTSnowDrift> SnowDrifts;
};

/** Another line between two points of the map, carved like a narrow road: a way round, a shortcut, a detour. */
USTRUCT(BlueprintType)
struct FGTAltRoute
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	TArray<FVector2D> PointsM;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float HalfWidthM = 3.5f;

	/** 0 tarmac, 1 dirt, 2 mud, 3 snow. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	int32 Layer = 1;
};

/**
 * A flat or tilted rectangle laid over the land after the roads are carved (The Proving Ground, 2026-09-19): a skid pan,
 * a ramp at a set grade, a flat top, a cross slope. Its height at a point is BaseZM at StartM plus GradePercent along
 * YawDegrees plus the cross slope across (both read at the nearest point of the rectangle, so it never dips outside
 * it), blended into whatever is under it over BlendM. A spec with no planes is the ground it always was.
 */
USTRUCT(BlueprintType)
struct FGTTerrainPlane
{
	GENERATED_BODY()

	/** The middle of the rectangle's start edge, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FVector2D StartM = FVector2D::ZeroVector;

	/** Which way the rectangle runs from StartM, degrees (Unreal yaw: 0 is +X, 90 is +Y). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float YawDegrees = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float LengthM = 30.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float HalfWidthM = 4.f;

	/** The world height at StartM, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float BaseZM = 0.f;

	/** Rise along the rectangle, per cent. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float GradePercent = 0.f;

	/** Tilt across it, degrees, positive when the left side (seen along YawDegrees) is higher. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float CrossSlopeDegrees = 0.f;

	/** Beyond the rectangle the plane fades into the ground under it over this far, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float BlendM = 6.f;

	/** The bumps on it (+-), m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float RoughnessM = 0.02f;

	/** The layer it is paved with (0 tarmac, 1 dirt, ...); -1 keeps what is under it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	int32 Layer = -1;
};

/** A named place GTGoto puts the car (The Proving Ground): the landing point, 10 m before the station, and its heading. */
USTRUCT(BlueprintType)
struct FGTTerrainStation
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FName Name;

	/** Where the car lands, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FVector2D PointM = FVector2D::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float YawDegrees = 0.f;

	/** The landing point's arc along the main route, m; -1 when the station is off the route. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float ArcM = -1.f;

	/** The station's own start (arc on the route, or metres along YawDegrees from PointM off it), m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float StartAheadM = 10.f;

	/** Climbs: the grade asked, per cent. Slope: 0. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float GradePercent = 0.f;

	/** Slope: the cross slope asked, degrees. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	float CrossSlopeDegrees = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain")
	FString Note;
};

/**
 * Leg dressing LD1 (docs/LEG_DRESSING_PLAN.md): one biome rule. The spec's rules split only the off-road (Scrub) weight
 * into biome layers (the OW names and GrandTour's Thicket), which the OW PCG graphs dress. A rule's mask at a vertex is
 * its height band x its slope band x its noise band (x its route-section band, LD1b: MaxSectionDistM), each 0..1 with a soft edge Fade wide centred on the limit; a zero
 * limit means no limit (a NoiseMax of 1 or more is none either). Rules composite by priority, first wins; see
 * FGTTerrainSpec::Biomes. Several rules may name one layer (Thicket's forest edge and its brush by the fords and bogs).
 */
USTRUCT(BlueprintType)
struct FGTBiomeRule
{
	GENERATED_BODY()

	/** The biome layer this rule paints: its landscape layer name and LI_<Layer> (e.g. OW_Meadow, Thicket). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	FName Layer;

	/** The finished ground's height band, m (0: no limit), with an edge FadeM wide. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float MinHeightM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float MaxHeightM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float FadeM = 0.f;

	/** The ground's slope band, degrees over 4 m (GTTerrain::SlopeDegrees; 0: no limit), with an edge FadeDeg wide. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float MinSlopeDeg = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float MaxSlopeDeg = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float FadeDeg = 0.f;

	/**
	 * A noise band (0: no noise): a Perlin noise of this wavelength, m, remapped to about uniform 0..1 (so a band 0.45-0.55
	 * covers about a tenth of the land), kept between NoiseMin and NoiseMax with an edge NoiseFade wide. Rules with the same
	 * wavelength and Seed read the same noise, so a band next to another draws a ring round it (a forest's edge).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float NoiseWavelengthM = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float NoiseMin = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float NoiseMax = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float NoiseFade = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	int32 Seed = 0;

	/**
	 * LD1b (2026-09-27): a band round route sections (0: none). When above 0, the rule's mask is also 1 within this many
	 * metres of the main route's polyline where it runs through a section of one of SectionKinds (each section's own arc
	 * range, StartM..EndM), fading out over FadeM beyond it (1 - smoothstep from MaxSectionDistM to MaxSectionDistM + FadeM),
	 * and 0 further off. It multiplies the rule's other bands. SectionKinds 0 names no section, so the rule paints nothing.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	float MaxSectionDistM = 0.f;

	/** LD1b: which route section kinds MaxSectionDistM measures from: bit (1 << EGTRouteSectionKind), e.g. Mud | Ford = 24. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome", meta = (Bitmask, BitmaskEnum = "/Script/GrandTour.EGTRouteSectionKind"))
	int32 SectionKinds = 0;
};

/**
 * Ground relief GR1 (docs/GROUND_RELIEF_PLAN.md GR1 item 3): hummocks (tussock mounds) stamped into the heightmap on Scrub
 * ground, outside every route's band and shoulder (they fade in over the shoulder's outer part, as (1 - presence)^3), off the
 * planes and out of channels. A Poisson count per 4 m cell from a hashed 12 m cluster noise (Density (mounds per 100 m^2) x lerp(ClusterMin,
 * ClusterMax, n), renormalised by its mean so the density is Density), each mound a soft dome (1 - u^2)^2 whose rim is
 * warped by a 3-harmonic angular noise and whose crest sits off centre, the overlaps combined as sqrt(sum h^2) (a soft max that
 * adds). Density 0 (the default): none, the ground exactly as before. Every number is a dial (GTTerrain::HummockHeightM).
 */
USTRUCT(BlueprintType)
struct FGTHummockField
{
	GENERATED_BODY()

	/** Mounds per 100 m^2 of the field (before the mask); 0 none. GR1's strips: 8. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float Density = 0.f;

	/** The cluster noise's wavelength, m, and the density multiplier's range over it (renormalised to a mean of 1). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float ClusterWavelengthM = 12.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float ClusterMin = 0.1f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float ClusterMax = 2.2f;

	/** A mound's base radius, m, drawn by a truncated power law of RadiusPower (most small). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float RadiusMinM = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float RadiusMaxM = 2.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float RadiusPower = 2.f;

	/** A mound's height, m: lerp(HeightMinM, HeightMaxM) by its radius's place in the range (taller mounds wider), x0.8-1.2, clamped. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float HeightMinM = 0.15f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float HeightMaxM = 0.5f;

	/** The rim's warp, a share of the radius (+-), and the crest's offset toward a random side, at most this share of the radius. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float RimWarp = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	float CrestOffset = 0.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Hummocks")
	int32 Seed = 0;
};

/**
 * Ground relief GR1 item 5: the grass and tussock placement's variation (GTTerrain::VaryGrass; the strips' setup scripts pass
 * their placements through it). Every number 0 (CrestTussockWeight 1): the placement exactly as given.
 */
USTRUCT(BlueprintType)
struct FGTGrassVariation
{
	GENERATED_BODY()

	/** Per-instance height x (1 +- this) from two noise octaves (HeightWavelengthM and HeightFineWavelengthM); 0.45 gives x0.55-1.45. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float HeightJitter = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float HeightWavelengthM = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float HeightFineWavelengthM = 0.8f;

	/** Bare gaps: an instance is dropped where a BareWavelengthM cluster noise (about uniform) is under the local share, which a
	 * BareShareWavelengthM noise moves between BareShareMin and BareShareMax. Both 0: no gaps. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float BareShareMin = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float BareShareMax = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float BareWavelengthM = 2.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float BareShareWavelengthM = 12.f;

	/** The most an instance leans, degrees: SlopeFollow of the ground's slope plus a noise lean, clamped to this. 0: upright as given. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float TiltDegrees = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float SlopeFollow = 0.5f;

	/** Tussocks on a hummock's crest (the hummock field at least 60 % of its mound's peak) are this many times as dense: each
	 * gets (weight - 1) companions 0.3-0.7 m off. 1: none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	float CrestTussockWeight = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grass")
	int32 Seed = 0;

	bool IsActive() const { return HeightJitter > 0.f || BareShareMax > 0.f || TiltDegrees > 0.f || CrestTussockWeight > 1.f; }
};

/** GR1: what GTTerrain::VaryGrass did to one placement. */
struct FGTGrassStats
{
	int32 In = 0;
	int32 Bare = 0;
	int32 Out = 0;
	int32 CrestExtra = 0;
	float ScaleMin = 1.f;
	float ScaleMax = 1.f;
	float TiltMaxDeg = 0.f;
};

/**
 * Everything that makes one leg's ground (M6, terrain first): the landscape's grid and placement,
 * the noise, the landforms, the route the road is carved along, what it is paved with and what
 * each stretch is for, the other lines, and where the snow line is. The generator is pure: the
 * same spec gives the same heights, so the setup script that imports the landscape, the builder
 * in the editor and the code that places actors on it all agree.
 */
USTRUCT(BlueprintType)
struct FGTTerrainSpec
{
	GENERATED_BODY()

	// ---- grid ----
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	int32 ComponentsPerSide = 16;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	int32 SubsectionsPerComponent = 2;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	int32 QuadsPerSubsection = 63;

	/** World size of one quad, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float QuadSizeCm = 100.f;

	/** World position of the grid's corner vertex, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float OriginXCm = -30000.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float OriginYCm = -100800.f;

	/** The landscape actor's Z scale; heights span +-256 m at 100. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Grid")
	float ZScale = 100.f;

	// ---- the land ----
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Land")
	int32 Seed = 3;

	/** Height of the largest noise octave, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Land")
	float BaseAmplitudeM = 15.f;

	/** Wavelength of the largest noise octave, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Land")
	float BaseWavelengthM = 300.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Land")
	int32 Octaves = 4;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Land")
	float Persistence = 0.5f;

	/** The whole map tilts: metres of rise per kilometre along +X. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Land")
	float SlopeMPerKm = 20.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Land")
	TArray<FGTTerrainFeature> Features;

	// ---- relief (stage 2): bumps of RoughnessWavelengthM and half of it, this high, per surface ----
	/** The bumps' longer wavelength, m (a second octave at half of it); a 1 m landscape carries 2 m bumps. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float RoughnessWavelengthM = 4.f;

	/**
	 * Ground relief GR1 item 2: how many relief octaves. 2 (the default) is the stage-2 relief exactly (RoughnessWavelengthM and
	 * half of it at 0.67 / 0.33); 3 adds a third at a third of it, at weights 1 / 0.55 / 0.3 renormalised to the same peak (the
	 * strips: RoughnessWavelengthM 6, so 6, 3 and 2 m).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	int32 RoughnessOctaves = 2;

	/** Bump height (+-) on a plain road, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float RoadRoughnessM = 0.02f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float RallyRoughnessM = 0.06f;

	/** A track: rough. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float TrackRoughnessM = 0.15f;

	/** A bog: hummocks. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float MudRoughnessM = 0.12f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float FordRoughnessM = 0.08f;

	/** The ground away from any road. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	float ScrubRoughnessM = 0.25f;

	// ---- track features (stage 2): water bars across a track, a rut pair down tracks and bogs, stones in the track ----
	/** A water bar (a ridge across the track that sheds rain) about every this far along a track, m; 0 for none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float WaterBarSpacingM = 100.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float WaterBarHeightM = 0.25f;

	/** The bar's length along the track, foot to foot, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float WaterBarLengthM = 3.f;

	/** The bar runs across the track at this angle from square, degrees, so it drains to one side. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float WaterBarSkewDegrees = 25.f;

	/** The rut pair: two grooves this far either side of the pair's centre, m (the car's wheels are 1.57 m apart). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float RutOffsetM = 0.8f;

	/** Each groove's half width, m (a 1 m landscape needs at least 0.7). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float RutHalfWidthM = 0.75f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float TrackRutDepthM = 0.10f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float MudRutDepthM = 0.18f;

	/** The pair wanders this far either side of the axis, m, over RutWanderWavelengthM, so following it takes steering. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float RutWanderM = 0.4f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float RutWanderWavelengthM = 25.f;

	/** A stone in the track about every this far along it, m (AGTTerrainDressing places them with collision); 0 for none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float TrackStoneSpacingM = 4.f;

	/** A stone's length, m, drawn between these. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float TrackStoneMinM = 0.15f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Track")
	float TrackStoneMaxM = 0.4f;

	// ---- rally edge (stage 2): a verge beyond the paved edge and posts along it ----
	/** The verge beyond a rally road's edge, m, deepest halfway: a ditch where the road is on fill or level ground, a bank where it is in cut (a 1 m landscape needs 3 m to carry it). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Rally")
	float VergeWidthM = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Rally")
	float VergeDitchM = 0.4f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Rally")
	float VergeBankM = 0.5f;

	/** A post either side of a rally stretch about every this far, m, just beyond the verge, with collision; 0 for none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Rally")
	float RallyPostSpacingM = 30.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Rally")
	float RallyPostHeightM = 1.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Rally")
	float RallyPostWidthM = 0.2f;

	// ---- the road ----
	/** The route in metres: start, bends, checkpoints, the zone. The road is carved along it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Road")
	TArray<FVector2D> RouteM;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Road")
	float RoadHalfWidthM = 6.f;

	/** Beyond the road, how far the cut or fill takes to meet the land, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Road")
	float ShoulderM = 14.f;

	/** The road's steepest grade, per cent. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Road")
	float MaxGradePercent = 14.f;

	/** The road's profile is the land's, smoothed over this length, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Road")
	float RouteSmoothM = 80.f;

	/** What the road is paved with along the route; anything not covered is dirt. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Road")
	TArray<FGTSurfaceSpan> Spans;

	/** What each stretch of the route is for; anything not covered is Road. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Road")
	TArray<FGTRouteSection> Sections;

	/** Other lines carved like narrow roads. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Road")
	TArray<FGTAltRoute> AltRoutes;

	// ---- the sections' numbers ----
	/** A track's width as a fraction of the road's. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float TrackWidthScale = 0.55f;

	/** A rally stretch's width as a fraction of the road's (0.75: a 9 m road with verges, since stage 2; it was 1.3). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float RallyWidthScale = 0.75f;

	/** A rally stretch follows the land smoothed over this much less, m, so crests and dips stay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float RallySmoothM = 30.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float RallyGradePercent = 20.f;

	/** How hard a rally bend banks: degrees of camber per radian-per-metre of curvature. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float CamberGainDegrees = 500.f;

	/** The most a rally bend banks, degrees. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float CamberMaxDegrees = 7.f;

	/** A bog's width as a multiple of the road's. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float MudWidthScale = 1.6f;

	/** How far a bog's road sinks below the profile, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float MudSinkM = 0.4f;

	/** A bog's deep mud (layer 5) fills this fraction of its half width down the middle, plus up to BogPocketFraction more where a noise of BogPocketWavelengthM peaks; the rest is mud, the shallow line. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections", meta = (ClampMin = 0, ClampMax = 1))
	float BogCoreFraction = 0.45f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections", meta = (ClampMin = 0, ClampMax = 1))
	float BogPocketFraction = 0.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float BogPocketWavelengthM = 25.f;

	/** A ford drops into the channel at up to this grade, per cent, following the land closely. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float FordGradePercent = 25.f;

	/** LM3a: a Snow section's width as a multiple of the road's. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	float SnowWidthScale = 1.4f;

	/** LM3a: the deformation profile every Snow section takes on ByKind (snow defaults: FGTDeformProfile::SnowDefaults). A section's own Deform with Mode On overrides it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	FGTDeformProfile SnowProfile = FGTDeformProfile::SnowDefaults();

	/**
	 * 2026-09-22, the owner's ford feel (docs/VEHICLE_BUILD_SYSTEM.md section 49): false paints a Ford section's bed
	 * with the Dirt row, the same span that was Mud; true restores the muddy bed of M6 stage 3.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Sections")
	bool bFordBedMud = false;

	// ---- rocks in a ford (docs/WATER_PLAN.md stage R1) ----
	/**
	 * How many rocks the generator tries to stand in each Ford section's wet channel, as the track's stones are
	 * placed (AGTTerrainDressing instances them with collision, and AGTWaterSheet's bed takes the higher of the
	 * landscape and a trace, so a rock is bed: a submerged one a bump the flow runs over, a proud one dry cells it
	 * runs round). 0 for none.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ford")
	int32 FordRockCount = 14;

	/** A ford rock's length, m, drawn between these; about a third are sized to stand over the ford's surface. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ford")
	float FordRockMinM = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ford")
	float FordRockMaxM = 1.6f;

	/** A lane this wide along the route through a ford stays clear of rocks, m; two rocks stand on its edges. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ford")
	float FordLaneM = 4.f;

	/**
	 * And no rock stands within this far of the crossing's middle along the route, m. The current runs ACROSS the
	 * route, so a rock beside the middle is upstream or downstream of the spot the terrain test parks its car in: with
	 * rocks 2 m from it the raised crossing's own current fell from 1.25 to 1.01 m/s and the floating car was carried
	 * 2.11 m in ten seconds instead of 4.20, which is terrain step 16's gate. Six metres leaves the flow tube through
	 * the crossing clear and puts the rocks where the car enters and leaves the water.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ford")
	float FordRockClearM = 6.f;

	// ---- the ground ----
	/** The ground away from the road: 4 scrub (dirt to the wheels, a different face so the road reads). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ground")
	int32 OffRoadLayer = 4;

	/** Above this height everything is snow, m; leave high for none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ground")
	float SnowLineM = 100000.f;

	/** A channel dug deeper than this is mud at the bottom, m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Ground")
	float MudChannelDepthM = 1.5f;

	// ---- biomes (leg dressing LD1, docs/LEG_DRESSING_PLAN.md); empty on every spec until LD6 dresses The Hide ----
	/**
	 * The biome rules, in priority order. At each vertex the off-road layer's weight (OffRoadLayer, Scrub) is shared out
	 * by priority compositing - rule i takes mask_i x prod_{j<i}(1 - mask_j) - and what no rule takes goes to
	 * FallbackBiome (or stays on the off-road layer when that is None). The biome layers are weight layers 6 and up
	 * (GTTerrain::BiomeLayers); layers 0-5 and the heights are exactly what they were, and GTTerrain::LayerAt still
	 * answers 0-5 (a biome counts as its off-road parent). Empty with no fallback: exactly the ground without biomes.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	TArray<FGTBiomeRule> Biomes;

	/** The biome that takes the off-road weight no rule takes (e.g. OW_Meadow); None leaves it on the off-road layer. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Biome")
	FName FallbackBiome;

	// ---- ground relief GR1 (docs/GROUND_RELIEF_PLAN.md); off on every spec but the test strips ----
	/** The hummock field (Density 0: none). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	FGTHummockField Hummocks;

	/** The grass placement's variation (all 0: the placement as given). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Relief")
	FGTGrassVariation Grass;

	// ---- the Proving Ground (2026-09-19); empty on every leg ----
	/** Flat or tilted rectangles over the land after the roads: a skid pan, ramps, a cross slope. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Planes")
	TArray<FGTTerrainPlane> Planes;

	/** Named places for GTGoto; a map whose spec has any prints them at BeginPlay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Terrain|Planes")
	TArray<FGTTerrainStation> Stations;
};

/** Where a point stands relative to a route. */
struct FGTRouteHit
{
	float DistanceM = 0.f;
	/** Signed distance, m: positive to the left of the route's direction. */
	float SignedM = 0.f;
	float ArcM = 0.f;
	int32 Segment = 0;
};

/** A road's height along its route, sampled every StepM and grade-limited, plus the crests and compressions laid on top (analytic, so a crest is smooth at any step). */
struct FGTRouteProfile
{
	float StepM = 5.f;
	TArray<float> HeightsM;
	float LengthM = 0.f;
	TArray<FGTProfileBump> Bumps;

	float HeightAt(float ArcM) const;
};

/** A stone the generator puts in a track (AGTTerrainDressing places it with collision). */
struct FGTTerrainStone
{
	FVector2D PositionM = FVector2D::ZeroVector;
	float SizeM = 0.3f;
	float YawDegrees = 0.f;
	float PitchDegrees = 0.f;
	float RollDegrees = 0.f;
};

/** A post along a rally stretch's edge. */
struct FGTTerrainPost
{
	FVector2D PositionM = FVector2D::ZeroVector;
	float YawDegrees = 0.f;
};

/** The main route's profile and every alternative line's. */
struct FGTTerrainProfiles
{
	FGTRouteProfile Main;
	TArray<FGTRouteProfile> Alts;
	/** RIVERBED S2 (2026-09-23): every Mud section's patch box, world cm (GTTerrain::MudPatchBoxesCm); no Mud or Bog is painted outside them. */
	TArray<FBox2D> MudBoxesCm;
};

namespace GTTerrain
{
	/** The surface layers: 0 tarmac, 1 dirt (the road), 2 mud, 3 snow, 4 scrub (the ground away from the road; dirt to the wheels), 5 bog (deep mud down a bog's middle). */
	constexpr int32 LayerCount = 6;

	/** Vertices along one side of the grid (quads + 1). */
	GRANDTOUR_API int32 VertsPerSide(const FGTTerrainSpec& Spec);

	/** The land before the road: slope, noise and landforms, m. */
	GRANDTOUR_API float BaseHeightM(const FGTTerrainSpec& Spec, float XM, float YM);

	/** The dig of channel features alone at a point (positive, m): what turns to mud. */
	GRANDTOUR_API float ChannelDigM(const FGTTerrainSpec& Spec, float XM, float YM);

	/** The nearest point of a polyline. */
	GRANDTOUR_API FGTRouteHit NearestOnPolyline(const TArray<FVector2D>& PointsM, float XM, float YM);

	/** The nearest point of the main route. */
	GRANDTOUR_API FGTRouteHit NearestRoute(const FGTTerrainSpec& Spec, float XM, float YM);

	/** The section of the main route at an arc length; Road when none covers it. */
	GRANDTOUR_API EGTRouteSectionKind SectionKindAt(const FGTTerrainSpec& Spec, float ArcM);
	GRANDTOUR_API const FGTRouteSection* SectionAt(const FGTTerrainSpec& Spec, float ArcM);

	/** The road's half width at an arc length, by its section, m. */
	GRANDTOUR_API float HalfWidthAt(const FGTTerrainSpec& Spec, float ArcM);

	/**
	 * RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): a Mud section's patch box, world cm: the section's route points
	 * every 2 m, each +- the road's half width there + MarginCm, as one axis-aligned box. UGTMudSubsystem::BuildPatches
	 * sizes its patches with it and the layer weights paint no Mud or Bog outside every one of them, so the ground that
	 * sinks a wheel is ground that deforms. False for a section that is not Mud or has no length.
	 */
	constexpr float MudPatchMarginCm = 200.f;
	GRANDTOUR_API bool MudPatchBoxCm(const FGTTerrainSpec& Spec, int32 SectionIndex, FBox2D& OutBox, float MarginCm = MudPatchMarginCm);
	GRANDTOUR_API void MudPatchBoxesCm(const FGTTerrainSpec& Spec, TArray<FBox2D>& OutBoxes, float MarginCm = MudPatchMarginCm);

	/**
	 * RIVERBED S4 (2026-09-23, VEHICLE_BUILD_SYSTEM 54): the section's deformation profile when it has one - Mode On, or
	 * ByKind on a Ford - else null (a Mud section on ByKind keeps its rows: the bog as tuned).
	 */
	GRANDTOUR_API const FGTDeformProfile* DeformProfileFor(const FGTRouteSection& Section);
	/** LM3a: the same, and a Snow section on ByKind takes the spec's SnowProfile (the one-argument form has no spec, so it gives a Snow section none). LM5b: both forms give a Mud section on ByKind its MudVariant's profile (MudVariantProfile), Standard none. */
	GRANDTOUR_API const FGTDeformProfile* DeformProfileFor(const FGTTerrainSpec& Spec, const FGTRouteSection& Section);
	/** LM5b: the profile of a mud variant, built once from FGTDeformProfile::MudVariantDefaults (null for Standard: no profile). */
	GRANDTOUR_API const FGTDeformProfile* MudVariantProfile(EGTMudVariant Variant);
	/** LM3a: a Snow section's snow depth at a world point, cm: the profile's SnowDepthCm, blended into each SnowDrift's DepthCm by the arc of the nearest point of the main route. */
	GRANDTOUR_API float SnowDepthCmAt(const FGTTerrainSpec& Spec, const FGTRouteSection& Section, const FGTDeformProfile& Profile, float XCm, float YCm);
	/**
	 * RIVERBED S4: the box of a section that gets a mud patch - a Mud section (MudPatchBoxCm's) or a section with a
	 * profile (a ford's bed), by the same rule: the route points every 2 m +- the half width there + MarginCm. The
	 * generator's paint boxes stay MudPatchBoxCm's (Mud only), so a ford's bed stays the Dirt it is.
	 */
	GRANDTOUR_API bool DeformPatchBoxCm(const FGTTerrainSpec& Spec, int32 SectionIndex, FBox2D& OutBox, float MarginCm = MudPatchMarginCm);
	/** RIVERBED S4: how many sections get a patch (the Mud sections plus the profiled ones): what UGTMudSubsystem builds. */
	GRANDTOUR_API int32 DeformPatchCount(const FGTTerrainSpec& Spec);

	/** The steepest grade the road may take at an arc length, per cent, by its section. */
	GRANDTOUR_API float GradeLimitAt(const FGTTerrainSpec& Spec, float ArcM);

	/** The route's heading, radians, smoothed over +-20 m. */
	GRANDTOUR_API float HeadingAt(const FGTTerrainSpec& Spec, float ArcM);

	/** How fast the heading turns at an arc length, radians per metre, positive to the left. */
	GRANDTOUR_API float CurvatureAt(const FGTTerrainSpec& Spec, float ArcM);

	/** The camber of the road at an arc length, degrees, positive when the right side is higher (a left bend banks left). Zero outside rally stretches. */
	GRANDTOUR_API float CamberDegreesAt(const FGTTerrainSpec& Spec, float ArcM);

	/** The main route's profile alone. */
	GRANDTOUR_API FGTRouteProfile BuildRouteProfile(const FGTTerrainSpec& Spec);

	/** Every route's profile. */
	GRANDTOUR_API FGTTerrainProfiles BuildProfiles(const FGTTerrainSpec& Spec);

	/** The finished ground at a point, m, with the roads carved in. */
	GRANDTOUR_API float HeightM(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM);

	/**
	 * GR1: the hummock field alone at a point, m, before its mask (the routes, planes and channels): sqrt of the sum of the
	 * mounds' squares. OutPeakM (optional) takes the tallest mound's own height among those over the point (0 off every mound).
	 * 0 with Spec.Hummocks.Density 0.
	 */
	GRANDTOUR_API float HummockHeightM(const FGTTerrainSpec& Spec, float XM, float YM, float* OutPeakM = nullptr);

	/** GR1: where the hummocks stand, 0..1: (1 - the strongest road's presence)^3 x (1 - every plane's) x out of channels. */
	GRANDTOUR_API float HummockMask(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM);

	/** GR1: the hummocks HeightM adds at a point, m (HummockHeightM x HummockMask); OutPeakM as HummockHeightM's. */
	GRANDTOUR_API float HummockAtM(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM, float* OutPeakM = nullptr);

	/** GR1: every mound whose centre lies in a box, m: (x, y, base radius, height), before the mask. */
	GRANDTOUR_API void HummockCentres(const FGTTerrainSpec& Spec, const FBox2D& AreaM, TArray<FVector4f>& OutMounds);

	/**
	 * GR1 item 5: a grass or tussock placement through Spec.Grass (world cm transforms in and out): the bare gaps dropped, the
	 * height scaled, the lean, and on a tussock placement (bTussock) the crest companions. Spec.Grass inactive: Out = In.
	 */
	GRANDTOUR_API void VaryGrass(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, const TArray<FTransform>& In, bool bTussock,
		TArray<FTransform>& Out, FGTGrassStats* OutStats = nullptr);

	/** The surface layer that dominates a point: 0 tarmac, 1 dirt, 2 mud, 3 snow, 4 scrub, 5 bog; always 0-5 (a biome counts as the off-road layer it splits; BiomeAt names it). */
	GRANDTOUR_API int32 LayerAt(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM);

	/** Ground relief GR2 (the ground scatter): the off-road layer's weight at a point, 0-1 (OffRoadLayer, Scrub; with biomes, before
	 *  the biome split): 1 away from every road and plane, 0 on a road's paving. */
	GRANDTOUR_API float OffRoadWeight(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM);

	/** The ground's slope at a point, degrees. */
	GRANDTOUR_API float SlopeDegrees(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM);

	/** A ford section's water surface, m: DepthM above the lowest point of the road through it. */
	GRANDTOUR_API float FordWaterLevelM(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, const FGTRouteSection& Section);

	/** Stage 2: the arc lengths of a track section's water bars (their centres on the axis). */
	GRANDTOUR_API void WaterBarArcs(const FGTTerrainSpec& Spec, const FGTRouteSection& Section, TArray<float>& OutArcsM);

	/** Stage 2: the rut pair's centre, m to the left of the axis, at an arc length (the pair wanders). */
	GRANDTOUR_API float RutWanderAt(const FGTTerrainSpec& Spec, float ArcM);

	/** Stage 2: the stones in every track section, deterministic from the spec. */
	GRANDTOUR_API void TrackStones(const FGTTerrainSpec& Spec, TArray<FGTTerrainStone>& OutStones);

	/** Stage 2: the posts along every rally section's edges, deterministic from the spec. */
	GRANDTOUR_API void RallyPosts(const FGTTerrainSpec& Spec, TArray<FGTTerrainPost>& OutPosts);

	/**
	 * Water stage R1: the rocks in every Ford section's wet channel, deterministic from the spec. The lane of
	 * FordLaneM along the route stays clear except for two rocks on its edges, and about a third of them are sized to
	 * stand over the ford's own water level.
	 */
	GRANDTOUR_API void FordRocks(const FGTTerrainSpec& Spec, TArray<FGTTerrainStone>& OutRocks);

	/** R1: a ford rock's cube scale from its size, m (longer than it is wide, wider than it is tall). */
	inline FVector FordRockScaleM(float SizeM) { return FVector(SizeM, SizeM * 0.8f, SizeM * 0.7f); }

	/**
	 * R1: how far a ford rock's top stands over the bed at the rock's own centre, cm - a quarter of the cube sunk, so
	 * 52.5 cm per metre of size. The dressing places every rock to mean exactly this whatever its tilt, and the water
	 * test reads it back off the field's bed against the ring of cells a metre out.
	 */
	inline float FordRockExposedCm(float SizeM) { return SizeM * 0.7f * 100.f * 0.75f; }

	/**
	 * The whole grid: landscape height values (row-major, Y then X) and the weight layers - the LayerCount surface layers,
	 * then one per biome layer (BiomeLayers) - every vertex's weights summing to 255. With biomes the surface layers are
	 * made exactly as without, then the off-road layer's byte is shared out among the biome layers to the byte.
	 */
	GRANDTOUR_API void Generate(const FGTTerrainSpec& Spec, TArray<uint16>& OutHeights, TArray<TArray<uint8>>& OutWeights);

	/** LD1: true when the spec has biome rules or a fallback biome (its off-road ground is biome layers). */
	GRANDTOUR_API bool HasBiomes(const FGTTerrainSpec& Spec);

	/**
	 * LD1: the spec's biome layers in weight-layer order (weight layer LayerCount + i): each rule's layer once, in rule
	 * order, then FallbackBiome when no rule names it. Empty when the spec has no biomes.
	 */
	GRANDTOUR_API void BiomeLayers(const FGTTerrainSpec& Spec, TArray<FName>& OutLayers);

	/** LD1: every weight layer's name, in Generate's order: the six surface layers (LayerName), then BiomeLayers. */
	GRANDTOUR_API void WeightLayerNames(const FGTTerrainSpec& Spec, TArray<FName>& OutNames);

	/**
	 * LD1: the biome at a point - the biome layer that takes the most of the off-road weight there (the road is not looked
	 * at: LayerAt says whether the point is off-road) - or NAME_None when the spec has no biomes, or when no rule claims
	 * the point and there is no fallback.
	 */
	GRANDTOUR_API FName BiomeAt(const FGTTerrainSpec& Spec, const FGTTerrainProfiles& Profiles, float XM, float YM);

	/**
	 * Leg dressing LD1 (docs/LEG_DRESSING_PLAN.md): a 64-bit hash of a generated grid - the heights, then every weight
	 * layer in order, each with its length - so the biome test (-GTBiomeTest) pins Generate's output byte for byte.
	 */
	GRANDTOUR_API uint64 HashGrid(const TArray<uint16>& Heights, const TArray<TArray<uint8>>& Weights);

	/** LD1: Generate's output for a spec, hashed by HashGrid. Pure: the same spec gives the same number. */
	GRANDTOUR_API uint64 GenerateHash(const FGTTerrainSpec& Spec);

	/** World cm helpers for placing things: the ground under a world XY, and the main route hit there. */
	GRANDTOUR_API float SampleHeightCm(const FGTTerrainSpec& Spec, float XCm, float YCm);
	GRANDTOUR_API FGTRouteHit RouteAtCm(const FGTTerrainSpec& Spec, float XCm, float YCm);

	/** A point on a polyline at an arc length, m, with the line's yaw there, degrees. */
	GRANDTOUR_API FVector2D PointOnPolyline(const TArray<FVector2D>& PointsM, float ArcM, float& OutYawDegrees);
	GRANDTOUR_API float PolylineLengthM(const TArray<FVector2D>& PointsM);

	/** The Hide (leg 3): a valley start, a rally stretch over the plateau past the bear's dell, a bog, a ford through the stream, a narrow track to the zone, and a detour round the south of the plateau. Since leg dressing LD6 it carries the D2 biome palette (LEG_DRESSING_PLAN section 5): clear Biomes and FallbackBiome for the pre-biome grid. */
	GRANDTOUR_API FGTTerrainSpec HideSpec();

	/** The Proving Ground (L_Proving): a 697 m loop from a tarmac pad at the map's middle through two fords, a bog, a rally stretch and a track, three ramps and a cross slope off it. */
	GRANDTOUR_API FGTTerrainSpec ProvingSpec();

	/** How much a plane claims a point (1 inside, fading to 0 over its BlendM) and its height there, m. */
	GRANDTOUR_API float PlanePresence(const FGTTerrainPlane& Plane, float XM, float YM, float& OutHeightM);

	/** The station of that name (case-insensitive), or null. */
	GRANDTOUR_API const FGTTerrainStation* FindStation(const FGTTerrainSpec& Spec, const FString& Name);

	GRANDTOUR_API const TCHAR* LayerName(int32 Layer);

	/** The surface physical material a layer reads as (PM_<name>): scrub is dirt to the wheels. */
	GRANDTOUR_API const TCHAR* PhysName(int32 Layer);
}
