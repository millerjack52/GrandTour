#pragma once

#include "CoreMinimal.h"

/**
 * A ford's water surface (docs/WATER_PLAN.md, stage WS1): a shallow-water height field on FGTMudField's grid shape.
 *
 * The grid is rotated so its +X runs along the section's flow: cell (x, y)'s centre is
 * OriginCm + AxisX * (x + 0.5) * CellCm + AxisY * (y + 0.5) * CellCm, and the two flow-wise ends are the X = 0 and
 * X = SizeX - 1 columns. Per cell the bed's world Z (sampled once at Init, the road's bed included), the water depth
 * h in metres (0 on a dry cell: the banks fall out of the solver on their own) and the volumetric flux through the
 * cell's +X and +Y faces in m3/s.
 *
 * The solver is the virtual-pipe height field (O'Brien & Hodgins 1995, Mei et al. 2007) in fixed sub-steps of
 * SubStepSeconds, at most MaxSubSteps a frame:
 *   1. every face's flux accelerates by dt x g x h_face x (the surface difference between the two cells). The
 *      plan's pipe used a constant cross-section (cell area / cell length = the cell size); this one uses the
 *      water's own cross-section (face width x depth), which is what makes the steady speed
 *      v = sqrt(g h S / BedFriction) - independent of the cell size, and dependent on the depth, as a river is.
 *      With a constant area the same channel's speed would be sqrt(g S CellM / BedFriction) and would change
 *      whenever the resolution did.
 *   2. the flux is damped by PipeDamping per step (the numerical term) and by a Chezy bed friction, BedFriction x
 *      |v| / h per second, which is the term the current's speed is actually set by.
 *   3. a cell's outflows are scaled so its depth can never go below zero, then the depths take the net flux.
 * The two flow-wise ends are fixed heads, re-imposed every sub-step and centred on the level: the X = 0 column half
 * of HeadDropCm over it (upstream) and the X = SizeX - 1 column half under (downstream), so water runs across the bed
 * and the level - base + wetness rise + ExtraRiseCm + the cvar - is still what raises the river. Mass is not
 * conserved at those two columns by design (they are the source and the sink); everywhere else it is conserved to
 * the float. The other two sides are walls, and so is any face between two dry cells.
 *
 * FlowFadeM is W1's fade, now in the solver: the bed friction is multiplied up to 1 + EndFriction over the last
 * FlowFadeM at each flow-wise end. Note what that can and cannot do - in a steady channel continuity forces the
 * same volume through every cross-section, so a friction ramp buys a deeper, slower end only where the bed lets the
 * water stand deeper; it cannot bring the velocity to zero the way W1's fade multiplier did.
 *
 * Stage WS2 gives the field its sources, so still water is not still:
 *   - the LIDS. Per cell, LidM is the metres of the water column a solid occupies this step (the car's hull box and
 *     each wheel, stamped by UGTHullComponent through AGTWaterSheet::StampLid). The solver's surface is
 *     bed + depth + lid, so water is pushed out from under a lid until the effective surface equalises with its
 *     neighbours and flows back when the lid leaves: volume is conserved with no bookkeeping, a moving car piles a
 *     bow wave ahead of itself and leaves a wake behind it, and a parked car in the current stands a crest upstream.
 *     SurfaceCm carries the effective surface, so what the car reads through UGTWaterSubsystem::Sample is the level
 *     it sits in and W1's drag and W2's lift are unchanged where nothing is moving.
 *   - the WIND: volume-neutral flux noise (a random velocity over a small disc, which radiates as a ring), its
 *     amplitude wandering with a gust period.
 *   - the RAIN: volume-neutral impulses - a drop lifts one cell by RainDropCm and takes the same volume from its
 *     eight neighbours, so rings spread and the level stays the boundary's.
 *   - the SPONGE at the two flow-wise ends: over the last FlowFadeM the depth relaxes toward the boundary's own head
 *     with SpongeTauS, so an outgoing wave is absorbed instead of reflected (WS1's flag: a 70 cm raise left the
 *     middle swinging 38-58 cm on a 33 s seiche) while the mean head difference still drives the current.
 */
struct GRANDTOUR_API FGTWaterField
{
	// ---- the grid ------------------------------------------------------------------------------------------
	/** World XY of the field's (0, 0) corner. */
	FVector2D OriginCm = FVector2D::ZeroVector;
	/** The field's +X in world XY, unit: the flow's direction. */
	FVector2D AxisX = FVector2D(1.0, 0.0);
	/** Its left perpendicular, unit. */
	FVector2D AxisY = FVector2D(0.0, 1.0);
	int32 SizeX = 0;
	int32 SizeY = 0;
	float CellCm = 25.f;

	/** The bed's world Z at each cell centre, cm. */
	TArray<float> BedCm;
	/** Water over the bed, metres; 0 is a dry cell. */
	TArray<float> DepthM;
	/** Volumetric flux through the cell's +X face (to cell + 1) and +Y face (to cell + SizeX), m3/s. */
	TArray<float> FluxX;
	TArray<float> FluxY;

	// ---- what the renderer and the car read (rebuilt once a frame after the sub-steps) ----------------------
	/** The water surface's world Z at each cell centre, cm. A dry cell carries its bed, so a bilinear sample walks down to the bank instead of falling off a cliff. */
	TArray<float> SurfaceCm;
	/** The cell's depth-averaged velocity in field space, m/s (X along the flow). */
	TArray<float> VelXMps;
	TArray<float> VelYMps;

	// ---- WS2: the lids (a solid's occupancy of the water column) --------------------------------------------
	/** Metres of this cell's column a solid holds, in force for this step. The solver's surface is bed + depth + lid. */
	TArray<float> LidM;

	// ---- WS2's own numbers (docs/WATER_PLAN.md stage WS2) --------------------------------------------------
	/** How fast a lid may grow or shrink, m/s, so a teleport or a drop does not slam the field. */
	float LidRateMps = 1.5f;
	/** The wind's kick: the velocity it puts on a patch of faces, cm/s, before the gust. */
	float WindRippleCm = 45.f;
	/** How long the wind's amplitude takes to wander, seconds. */
	float WindGustS = 4.f;
	/** The radius of one gust's patch, metres (a patch, not a cell: a one-cell kick is grid noise, not a wave). */
	float WindPatchM = 1.5f;
	/** How many patches a second over the whole field (the gust scales this as well as the kick). */
	float WindPatchesPerS = 60.f;
	/** gt.Water.Wind, set by the sheet each tick: 0 takes the wind off. */
	float WindScale = 1.f;
	/** The weather's rain at the sheet, 0..1, set by the sheet each tick. */
	float RainIntensity = 0.f;
	/** Drops per square metre of wet water per second at rain 1. */
	float RainDropsPerM2S = 20.f;
	/** How high one drop lifts its cell, cm; the same volume comes off its eight neighbours. */
	float RainDropCm = 0.8f;
	/** At most this many drops in one step, whatever the rain (the cost guard). */
	int32 MaxDropsPerStep = 2000;
	/**
	 * How fast the sponge at the two ends pulls the depth back to the boundary's head, seconds (0 takes it off).
	 * Measured and then turned off: a relaxation layer five metres wide cannot absorb the basin's own mode, which is
	 * sixty metres long - with the layer pinned to the nominal head a 70 cm raise at the ends rang the middle 114 cm
	 * peak to peak, and with the layer's target lagging that level by SpongeLevelTauS, 126 cm, against WS1's ~100 cm
	 * over the same window with no layer at all. What stops the reflection is the boundary itself: bOpenEnds.
	 */
	float SpongeTauS = 0.f;
	/** How hard the same ramp damps the flux normal to the end, per second (0 takes it off: the depth relaxation is the absorber). */
	float SpongeFluxDamp = 0.f;

	// ---- WS1's own numbers (docs/WATER_PLAN.md stage WS1; all measured, see VEHICLE_BUILD_SYSTEM 41) --------
	/**
	 * The numerical damping on a pipe, per sub-step. 0.02 (the plan's start) is a drag rate of 1.2/s, fifty times the
	 * bed friction at 1.5 m/s, and the channel would need metres of head; WS1 used 1.e-4, which is 0.006/s and lets
	 * the basin's own mode ring for minutes - the middle still stood 1.75 cm off the level ten seconds after a car had
	 * crossed. WS2's follow-up runs 1.e-3, a rate of 0.06/s: a half-life of 11 s for the slosh, 12 % off the ring's
	 * two-second trip, and HeadDropCm re-set to pay for it.
	 */
	float PipeDamping = 1.e-3f;
	/** The Chezy drag coefficient of the bed: the steady speed is sqrt(g h S / BedFriction). Measured down from 0.01, which needed half a metre of head for 1.5 m/s. */
	float BedFriction = 0.005f;
	/** How much the bed friction is multiplied by at the very flow-wise end (1 + this), ramped in over FlowFadeM. */
	float EndFriction = 1.f;
	/** W1's fade distance, metres, now the length of that friction ramp at each end. */
	float FlowFadeM = 5.f;
	/**
	 * The head across the field, cm: the current's speed is set by it. It is held CENTRED on the level - the upstream
	 * end at level + half of it, the downstream end at level - half - and not, as the plan had it, upstream at the
	 * level + the whole drop. Centred, the flow-wise middle of the sheet stays at the level, which is where the route
	 * crosses, so W1's and W2's ford is exactly as deep as it was; uncentred it would have been 18 cm deeper and the
	 * tuned crossing would have moved with it.
	 */
	float HeadDropCm = 30.f;
	/** The fixed sub-step. sqrt(g h) at the raised ford's 1.43 m is 3.75 m/s, 6.2 cm a step against a 25 cm cell. */
	float SubStepSeconds = 1.f / 60.f;
	int32 MaxSubSteps = 4;
	/**
	 * Water stage R1, the clamp fix (measured: every ford picture but one was taken in a run whose cap had just cut
	 * 0.08 to 0.33 s of simulated time, on the 140-400 ms frames a screenshot costs). Unsimulated time is now carried
	 * across frames instead of being thrown away, bounded at MaxAccumulatorSeconds; a frame that asks for more than
	 * MaxSubSteps may burst to MaxSubStepsBurst while the burst's measured cost stays under BurstBudgetMs; and beyond
	 * that the frame takes CoarseSubStepSeconds steps instead, while the Courant number at the deepest cell
	 * (sqrt(g h) dt / cell) stays under CflLimit - at 25 cm cells 1/30 s allows 2.5 m of water at 0.66.
	 */
	int32 MaxSubStepsBurst = 8;
	float BurstBudgetMs = 6.f;
	float CoarseSubStepSeconds = 1.f / 30.f;
	float CflLimit = 0.9f;
	float MaxAccumulatorSeconds = 0.25f;
	/** Under this much water a cell is dry for the material's mask (the plan's 1 cm cut). */
	float DryDepthM = 0.01f;
	/** The depth the friction and the velocity divide by is never smaller than this, or a puddle divides by zero. */
	float MinDepthM = 0.02f;
	/**
	 * WS2's sim guard, as the drag cap is for the wheels and MaxWaterForceG for the hull: no face may carry water
	 * faster than this. A lid puts a step of up to the whole depth across one cell, which asks for an acceleration of
	 * g x step / cell - 23 m/s2 at 58 cm over 25 cm - and without a cap a cell can empty its entire column into its
	 * neighbour in a sub-step, the neighbour into the next, and the surface runs away (measured: 413 cm of "crest"
	 * and a hull reading 33 m of water over its keel). At 3 m/s a face moves at most a quarter of a cell's column in
	 * a sub-step, which is above the ford's own wave speed (2.4 m/s) and twice its current, so nothing real is
	 * clipped; what a real river does with the rest is stand a bore up, which is what the bow wave is.
	 */
	float MaxFlowSpeedMps = 3.f;
	/** How fast the sponge's own idea of the level follows a change, seconds: a level that jumps at the boundaries must not be pumped into the field by the sponge as well. */
	float SpongeLevelTauS = 5.f;
	/**
	 * WS2's answer to WS1's flag. The two flow-wise ends are no longer columns of water pinned at a head - a pinned
	 * surface is a perfect mirror, and every wave that reached one came back - but open, radiating boundaries
	 * (Flather): the end cell evolves like any other and a ghost face outside it carries
	 *     u = the learned mean + sqrt(g / h) x (the head the boundary asks for - the surface the end actually has),
	 * which is the wave impedance of the water itself, so an outgoing wave leaves and nothing is reflected. The mean
	 * is learned (EdgeMeanTauS) rather than imposed, because driving the ford's 1.3 m/s through a matched boundary
	 * costs u x sqrt(h / g) = 32 cm of head, which the ford's 8.5 cm does not have; learned, the end settles at its
	 * head with the discharge running through it. It only learns while the boundary is quiet (EdgeQuietMps), so a
	 * raise or a wave is radiated instead of taught.
	 *
	 * BUILT, MEASURED AND LEFT OFF. It does what it was written for - a 70 cm raise at the two ends rang the middle
	 * 126 cm peak to peak with the fixed heads and 18.5 with these - but it costs the steadiness the ford is tuned on:
	 * the discharge is learned rather than given, so the loop chases the basin's own 33 s seiche and the field breathes
	 * about 1.3 % of its volume every ten seconds (0.8 cm of level) against 0.1 % fixed, the crossing settles in 90 s
	 * instead of 60 and reads 1.23 m/s instead of 1.26, and the water test's volume and "flat again" gates fail on the
	 * wander alone. The game never raises a ford from its ends - a level that jumps is carried into the field whole
	 * (ShiftLevel, +0.8 cm off) - so the reflection this fixes is a test's scenario and the steadiness is the driver's.
	 * One line to turn it back on.
	 */
	bool bOpenEnds = false;
	/** Opt-in pond: sealed outer faces, no fixed-head reservoir or sponge. */
	bool bClosedBasin = false;
	/** How long the ends take to learn the discharge that runs through them, seconds. Measured: at 4 s the loop chases the basin's own 33 s seiche and the field breathes 1.2 % of its volume every ten seconds; at 10 it settles to 0.6. */
	float EdgeMeanTauS = 10.f;
	/** A boundary whose surface is moving faster than this is not quiet, and its mean is not updated, m/s: a raise moves it at about 0.5 m/s and the basin's swing at 0.15, while the wind's ripple moves it at 0.015. */
	float EdgeQuietMps = 0.1f;
	/**
	 * The most an open end may carry, m/s. A 70 cm raise asks a matched boundary for 2.9 m/s, which fills the basin
	 * in five seconds and overshoots it by half a metre; at 1.5 it still overshot by 29 cm. The steady discharge only
	 * needs about 0.2 m/s through an end (the ends are 74 m of 1.3 m deep water against the crossing's 22 m of 0.6),
	 * so 0.6 leaves three times what the river wants and still fills a 70 cm raise in about ten seconds.
	 */
	float EdgeMaxUMps = 0.6f;
	/** The section's nominal current, m/s (FlowSpeedMps), which the ends are seeded with at Init so the ford runs at speed from the first seconds instead of learning for a minute. */
	float NominalFlowMps = 1.5f;
	/**
	 * WS2: how much of a lid is spread into its neighbours each step, 0 to 1. A hull's side is vertical and a 25 cm
	 * cell cannot hold that: unsmoothed, the four wheels' lids pile the water they push out into a ridge beside the
	 * car and the car then reads its own splash - measured, a car parked in the as-built 0.60 m ford had 1.00 m of
	 * water over its keel and drowned its own engine, where W1 and W2 read 0.64 m and kept it running. Smoothing
	 * costs the crests it spreads (at 0.5 the bow crest fell 27.9 -> 16.1 cm, at 0.25 it reads 19.1), so 0.25 is the
	 * least that keeps the car out of its own water. MaxFlowSpeedMps is what guards the solver; this guards the car.
	 */
	float LidBlend = 0.25f;

	/** The still water level the boundaries are driven from, cm (the sheet's GetLevelCm). */
	float LevelCm = 0.f;
	/** HeadDropCm after gt.Water.FlowScale: 0 is still water. */
	float AppliedHeadDropCm = 0.f;

	// ---- stats (the test's step 3) ------------------------------------------------------------------------
	/** Milliseconds the last Step that ran at least one sub-step took. */
	float StepMs = 0.f;
	double StepMsSum = 0.0;
	int32 StepMsCount = 0;
	float StepMsMax = 0.f;
	int32 SubStepsRun = 0;
	/** Frames whose accumulator asked for more than MaxSubSteps sub-steps (the field then runs slow and the rest of the time is dropped). */
	int32 SubStepClamps = 0;
	/**
	 * Water stage R1 (the standing finding of docs/WATER_PLAN.md section 6): how many sub-steps the accumulator asked
	 * for before the cap took them away, and how much simulated time the cap dropped, seconds. A run whose deficit is
	 * not 0 ran the water in slow motion, which is what the user felt as "the physics of the water" changing when only
	 * a material had.
	 */
	int32 SubStepsAsked = 0;
	float DeficitSeconds = 0.f;
	/** R1: frames that fell back to the coarse step, the Courant number the last of them ran at, and frames whose time the 0.25 s bound dropped. */
	int32 CoarseFrames = 0;
	float LastCoarseCfl = 0.f;
	int32 AccumulatorDrops = 0;
	/** R1: what one sub-step cost on the last stepping frame, ms - what says whether a burst fits in the budget. */
	float LastSubStepMs = 0.f;
	/** WS2: how many cells carry a lid this step and what they displace, m3 (the test reads them). */
	int32 LidCellCount = 0;
	float LidVolumeM3 = 0.f;
	/** WS2: how many cells hold water (the rain's drop count is per square metre of it). */
	int32 WetCellCount = 0;
	/** WS2: drops and wind patches put in since the last ResetStats, and how often the flux cap bit. */
	int32 RainDropsRun = 0;
	int32 WindPatchesRun = 0;
	int32 FluxClamps = 0;
	/** WS2: the highest the surface has stood over the level since the last ResetStats, cm, and how often the depth guard had to hold a cell down (it should never fire). */
	float MaxOverLevelCm = 0.f;
	int32 DepthClamps = 0;

	// ---- RIVERBED S3: the basin ----------------------------------------------------------------------------
	/**
	 * The cells that may be given water (1): the 4-connected fill from the basin's lowest cell at the level the heads
	 * hold (the level + half of HeadDropCm), grown whenever a rise or a calm reaches further, never shrunk. Empty is
	 * every cell (the field before S3, and -GTWaterPlacedBox). Init's still water, the fixed heads, Calm and ShiftLevel
	 * give water only to these, so a hollow the level does not reach through the bed stays dry; the solver itself can
	 * still carry water anywhere a wet neighbour pushes it.
	 */
	TArray<uint8> Basin;
	int32 BasinCells = 0;
	bool InBasin(int32 Index) const { return Basin.Num() == 0 || Basin[Index] != 0; }
	/** Makes the basin the fill from SeedIndex over the beds under FillLevelCm and empties every cell outside it. Returns its cell count. */
	int32 SetBasinFrom(int32 SeedIndex, float FillLevelCm);
	/** Grows the basin over every cell under InLevelCm that touches it (4-connected); returns how many cells joined. */
	int32 GrowBasin(float InLevelCm);

	bool IsValid() const { return SizeX > 1 && SizeY > 1 && DepthM.Num() == SizeX * SizeY; }
	int32 NumCells() const { return SizeX * SizeY; }

	/**
	 * Lays the grid over a rotated footprint and fills it with still water at InLevelCm.
	 * CentreCm is the footprint's world centre, FlowDirWorld the flow (need not be normalised; zero means +X),
	 * HalfSpanAlongCm how far the footprint reaches from the centre along the flow and HalfSpanAcrossCm across it.
	 * BedSamplerCm answers the bed's world Z at a world XY (AGTWaterSheet hands it the landscape's height, a trace
	 * where the landscape has nothing).
	 */
	void Init(const FVector2D& CentreCm, const FVector2D& FlowDirWorld, float HalfSpanAlongCm, float HalfSpanAcrossCm,
		float InCellCm, float InLevelCm, const TFunction<float(const FVector2D&)>& BedSamplerCm);

	/** Runs the solver forward. DeltaSeconds accumulates into fixed sub-steps; HeadScale is gt.Water.FlowScale. */
	void Step(float DeltaSeconds, float InLevelCm, float HeadScale);

	/** Puts the field back to flat still water at InLevelCm with no flux (the tests' "still water", and what a bed rebuild would want). */
	void Calm(float InLevelCm);
	/** Moving bed, preserving water volume (depth), flux and existing disturbances.
	 * Lowering dry soil does not manufacture water. Only the closed-basin mode accepts this. */
	bool UpdateClosedBed(TConstArrayView<float> HeightsCm);

	/**
	 * Carries the whole surface to a new level in one step, keeping the flow's own gradient and its fluxes: a cell
	 * that had water gets the difference added to its depth, a dry cell fills to the new level if its bed is under it.
	 * A level that jumps - SetExtraRiseAll, gt.Water.ExtraRiseCm, an event - has to come in this way. Measured: a
	 * 70 cm step at the boundaries alone reaches the middle in 4.8 s but rings the basin's 32 s seiche hard enough to
	 * leave the middle 40 cm low ten seconds later, and a car parked in the ford then finds no water at all.
	 *
	 * FromLevelCm is the level the field was last CARRIED to; -1.e9 (the default) means "the level Step was last
	 * handed". R1: they are not the same thing. A rise too slow to cross the sheet's 0.01 cm threshold in one frame
	 * is carried a frame or two later, and taking the delta off Step's level threw away every frame that had been
	 * skipped - measured, at the river's 5 cm/s and a thousand frames a second the field gained 81 % of a 49 cm rise
	 * and its surface stood 9.1 cm under the level, against 3.4 cm at the frame rate W5 was measured at. The same
	 * water, a different frame time: the standing finding of docs/WATER_PLAN.md section 6.
	 */
	void ShiftLevel(float NewLevelCm, float FromLevelCm = -1.e9f);

	/** Adds RiseCm of water over a disc: the ring test's impulse, and what WS2's sources will use. Returns the volume added, m3. */
	double AddImpulse(const FVector2D& WorldXY, float RadiusCm, float RiseCm);

	/**
	 * WS2: stamps a solid's occupancy over a rotated box footprint (the car's hull, a wheel). Per cell inside the box
	 * the lid is Fill x clamp(the cell's own effective surface - the solid's bottom there, 0, MaxHeightCm), so a solid
	 * only displaces what is under water; the bottom follows the car's pitch and roll through BottomSlope (dZ/dX and
	 * dZ/dY in world XY, cm per cm). The stamps of a tick are gathered and promoted into LidM at the next Step,
	 * rate-limited by LidRateMps, and the biggest stamp on a cell wins (a wheel inside the hull's box is not counted
	 * twice). Fill is the share of the box that is solid: the hull's is HullVolumeM3 / the box's volume, so the water
	 * the field pushes aside is the water W2's lift displaces; a wheel's is 1.
	 */
	void StampLid(const FVector2D& CentreCm, const FVector2D& ForwardXY, float HalfLenCm, float HalfWidCm,
		float BottomZCm, const FVector2D& BottomSlope, float MaxHeightCm, float Fill);

	/** WS2: drops every lid at once (a car teleported out of the water, gt.Water.Lids 0). */
	void ClearLids();

	/** The water surface's world Z at a world XY, cm, bilinear over the cell centres (the edge value outside). */
	float SurfaceCmAt(const FVector2D& XYCm) const;
	/** The water over the bed there, metres, bilinear. */
	float DepthMAt(const FVector2D& XYCm) const;
	/** The current there in world XY, m/s, bilinear. */
	FVector2D VelocityAt(const FVector2D& XYCm) const;
	/** All the water in the field, m3. */
	double VolumeM3() const;

	/** The cell a world XY falls in, clamped to the grid; INDEX_NONE when the field is empty. */
	int32 CellIndexAt(const FVector2D& XYCm) const;
	/** A cell's centre in world XY. */
	FVector2D CellCentreCm(int32 Index) const;
	/** A world XY in field space (cm from the origin corner, X along the flow). */
	FVector2D ToFieldCm(const FVector2D& XYCm) const;
	/** A field-space XY back in the world. */
	FVector2D ToWorldCm(const FVector2D& FieldCm) const;

	float CellDepthM(int32 Index) const { return DepthM.IsValidIndex(Index) ? DepthM[Index] : 0.f; }
	float CellSurfaceCm(int32 Index) const { return SurfaceCm.IsValidIndex(Index) ? SurfaceCm[Index] : LevelCm; }
	float CellBedCm(int32 Index) const { return BedCm.IsValidIndex(Index) ? BedCm[Index] : 0.f; }
	/** That cell's current in world XY, m/s. */
	FVector2D CellVelocity(int32 Index) const;

	void ResetStats();

	/** Opt-in, fixed-bank river pilot. Evolves height/flux disturbances about a divergence-free baked mean.
	 * This reduced model preserves the authored sloping river; it is not a flood/erosion solver.
	 * The existing ford solver is unchanged when no reference is installed. Init must be called first. */
	bool SetRiverReference(const TArray<float>& InDepthM, const TArray<float>& InFluxX, const TArray<float>& InFluxY, bool bPrescribedMean=false);
	/** Copy overlapping cells/faces on the same world lattice, including pending solid stamps. */
	int32 CopyRiverOverlap(const FGTWaterField& Previous);
	/** Signed disturbance volume left outside a relocated window. */
	double RiverWindowDiscardM3=0;
	bool HasRiverReference() const { return RiverDepthM.Num() == NumCells() && IsValid(); }
	void ResetRiverReference();
	/** Signed water added/removed by the absorbing boundary band (including fixed outer cells). */
	double RiverBoundaryM3 = 0.0;
	float RiverAbsorbWidthM = 4.f;
	float RiverWaveDamping = 0.45f;
	const TArray<float>& GetRiverDepthM() const { return RiverDepthM; }
	/** Bounded cosmetic concentrations, independent of water volume and forces. Opt-in for the moving domain. */
	bool bRiverVisuals=false;
	TArray<FVector2f> RiverDetail; // x: foam, y: suspended sediment, both 0..1
	float RiverDetailMs=0;
	void StepRiverDetail(float DeltaSeconds);
	void AddRiverDetail(FVector2D WorldXY,float RadiusCm,float Foam,float Sediment);
	int32 RiverActiveCells() const { return RiverWetCells.Num(); }

private:
	bool bRiverPrescribedMean=false;
	TArray<float> RiverDepthM, RiverFluxX, RiverFluxY;
	TArray<float> RiverWaveX, RiverWaveY, RiverNextX, RiverNextY, RiverOutScale;
	TArray<int32> RiverWetCells, RiverEdgeCells;
	TArray<float> RiverMeanU, RiverMeanV, RiverEdgeBlend;
	float RiverBlendDt=-1, RiverBlendWidth=-1;
	TArray<FVector2f> RiverDetailNext;
	TArray<float> RiverDetailLid;
	float RiverDetailCarry=0;
	void RiverSubStep(float Dt);
	/** The bed friction's multiplier per column: 1 in the middle, 1 + EndFriction at the flow-wise ends. */
	TArray<float> FrictionScaleX;
	float Accumulator = 0.f;

	// ---- WS2's working state ------------------------------------------------------------------------------
	/** What the writers have stamped since the last Step. */
	TArray<float> LidNextM;
	/** 1 where LidNextM has been written this tick, so a cell is listed once. */
	TArray<uint8> LidDirty;
	TArray<int32> LidDirtyCells;
	/** The cells whose LidM is not zero (so the promotion and the velocity fill walk a handful, not 35,520). */
	TArray<int32> LidCells;
	TArray<int32> LidScratch;
	TArray<uint8> LidFilled;
	/** The sponge's strength per column: 0 in the middle, 1 at the flow-wise ends. */
	TArray<float> SpongeRampX;
	/** The open ends, per row: the learned mean velocity through the ghost face, the velocity it last carried, the ghost flux and the surface it last saw. */
	TArray<float> EdgeUpMeanU;
	TArray<float> EdgeDownMeanU;
	TArray<float> EdgeUpLastU;
	TArray<float> EdgeDownLastU;
	TArray<float> EdgeUpFlux;
	TArray<float> EdgeDownFlux;
	TArray<float> EdgeUpEtaM;
	TArray<float> EdgeDownEtaM;
	float WindPhase = 0.f;
	float WindCarry = 0.f;
	float RainCarry = 0.f;
	/** The level the sponge relaxes toward, cm: LevelCm filtered, and snapped whenever the whole field is carried. */
	float SpongeLevelCm = 0.f;
	FRandomStream Rng;

	void SubStep(float Dt);
	/** Re-imposes the two fixed heads. */
	void ApplyBoundary();
	/** Rebuilds SurfaceCm, VelXMps and VelYMps from the depths, the lids and the fluxes. */
	void UpdateDerived();
	/** WS2: takes the tick's stamps into LidM at LidRateMps. */
	void PromoteLids(float Dt);
	/** WS2: a cell squeezed dry under a solid has no flux of its own, so it takes the stream around it (what a body in the water feels). */
	void FillLidVelocities();
	/** WS2: volume-neutral flux noise over the wet cells, in gusts. */
	void ApplyWind(float Dt);
	/** WS2: volume-neutral drop impulses. */
	void ApplyRain(float Dt);
	/** WS2: the absorbing ends (called inside a sub-step, after the depths). */
	void ApplySponge(float Dt);
	/** WS2: the radiating ghost faces outside the two flow-wise ends (bOpenEnds), m3/s into the field at X = 0 and out of it at X = SizeX - 1. */
	void ComputeEdgeFluxes();
	/** WS2: teaches the two ends the discharge that is running through them, while they are quiet. */
	void LearnEdgeMeans(float Dt);
	/** WS2: spreads each lid into its neighbours so a solid's side is a slope a 25 cm grid can carry. */
	void BlurLids();

public:
	/** WS2: what the two open ends have learned they carry, m/s (the mean over the wet rows) - the test logs it. */
	float EdgeMeanUMps(bool bUpstream) const;

private:
};

/**
 * RIVERBED S3 (docs/RIVERBED_PLAN.md, VEHICLE_BUILD_SYSTEM 53): the basin a ford's water fills at a level. A 4-connected
 * flood fill (the solver's own faces) over the bed's heights on a square lattice in the field's axes (X along the flow,
 * cells of CellCm), centred on the placed sheet and capped at SearchCm a side, from the lowest bed cell inside the placed
 * box. The bed is sampled only over the placed box and where the fill reaches (its wet cells and the ring round them), so
 * a pond costs what its own area costs. AGTWaterSheet logs it as GTFORDFILL.
 */
struct GRANDTOUR_API FGTWaterBasin
{
	float CellCm = 25.f;
	float LevelCm = 0.f;
	/** The lattice's (0, 0) corner in world XY, its axes (X the flow) and its cells a side. */
	FVector2D OriginCm = FVector2D::ZeroVector;
	FVector2D AxisX = FVector2D(1.0, 0.0);
	FVector2D AxisY = FVector2D(0.0, 1.0);
	int32 Size = 0;
	/** The beds sampled (valid where Sampled is 1) and the region (Wet 1). Freed by ReleaseLattice. */
	TArray<float> BedCm;
	TArray<uint8> Sampled;
	TArray<uint8> Wet;
	int32 SeedIndex = INDEX_NONE;
	float SeedBedCm = 0.f;
	/** The region's bounds in lattice cells (inclusive), its cell count, and whether it reached the search square's edge. */
	int32 MinX = 0, MaxX = -1, MinY = 0, MaxY = -1;
	int32 Cells = 0;
	bool bHitSearchEdge = false;
	/** The placed box in lattice cells (inclusive), and what stands under the level inside it. */
	int32 BoxMinX = 0, BoxMaxX = -1, BoxMinY = 0, BoxMaxY = -1;
	int32 BoxUnderLevel = 0;
	int32 RegionInBox = 0;
	/** Cells under the level inside the placed box that the fill does not reach, in how many 4-connected hollows, and the deepest. */
	int32 HollowCells = 0;
	int32 Hollows = 0;
	float HollowDeepestCm = 0.f;
	int32 SampledCells = 0;
	double FillMs = 0.0;

	bool IsValid() const { return SeedIndex != INDEX_NONE && Cells > 0; }
	int32 Index(int32 X, int32 Y) const { return Y * Size + X; }
	FVector2D CellCentreCm(int32 X, int32 Y) const { return OriginCm + AxisX * ((X + 0.5) * CellCm) + AxisY * ((Y + 0.5) * CellCm); }
	/** The lattice cell a world XY falls in, INDEX_NONE outside the lattice. */
	int32 CellAt(const FVector2D& XYCm) const;
	/** The half of the lattice, cells: the placed sheet's centre is the corner between cells Half - 1 and Half. */
	int32 Half() const { return Size / 2; }

	/** Lays the lattice about CentreCm and runs the fill. BoxHalfAlongCm / BoxHalfAcrossCm are the placed box about CentreCm. */
	void Fill(const FVector2D& CentreCm, const FVector2D& FlowDir, float InCellCm, float SearchCm, float InLevelCm,
		float BoxHalfAlongCm, float BoxHalfAcrossCm, const TFunction<float(const FVector2D&)>& BedSamplerCm,
		TOptional<FVector2D> AuthoredSeed = {});

	/** Frees the lattice's arrays; the numbers above stay. */
	void ReleaseLattice();
};
