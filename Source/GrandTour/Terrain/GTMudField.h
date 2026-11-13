#pragma once

#include "CoreMinimal.h"

/**
 * A bog's mud surface (docs/MUD_DEFORMATION_PLAN.md, stage A): a CPU grid over the bog's footprint at CellCm holding
 * the mud's height relative to the ground (negative in a rut, positive on a ridge), a horizontal slide-away offset
 * and a tracks factor. The wheels and the belly draw primitives into it, MudRunner's empirics: a wheel lowers a
 * capsule to its sinkage and pushes a share of the volume up into two ridges beside it while the mud within reach
 * slides outward; the belly flattens a box between the wheels. A texture built from it is what the mud mesh will
 * displace by (stage B) and the traction will read it inside bogs (stage C).
 */
struct GRANDTOUR_API FGTMudField
{
	/** World XY of the grid's corner. */
	FVector2D OriginCm = FVector2D::ZeroVector;
	int32 SizeX = 0;
	int32 SizeY = 0;
	float CellCm = 12.5f;
	TArray<float> HeightCm;
	TArray<FVector2f> OffsetCm;
	TArray<uint8> Tracks;
	/**
	 * The tread (docs/MUD_ONE_SURFACE_PLAN.md stage F). Per cell, the heading of the wheel that stamped it in turns
	 * (0..1 of a full circle) and the lug phase in turns of LugPeriodCm at that cell's centre, written by StampWheel
	 * over the tyre's capsule. The lugs themselves are never in HeightCm: a 9 cm period cannot live on a 12.5 cm cell,
	 * so M_GT_Mud draws them as a normal tilt from these two numbers. PhaseTurns is -1 where no wheel has been (LM3c, snow:
	 * and where the belly's plough scraped, its heading then in HeadingTurns).
	 */
	TArray<float> HeadingTurns;
	TArray<float> PhaseTurns;
	/** Rolled distance per lug: the phase advances one turn every LugPeriodCm the tyre rolls. The mud material uses the same number. */
	float LugPeriodCm = 9.f;

	/** Slumped walls outside the tyre contact area. Kept in the CPU field so rendering and traction agree. */
	float RutShoulderCm = 45.f;
	float RutShoulderDepthScale = 1.2f;
	float RutShoulderVariation = 0.5f;
	/** The fewest cells a rut wall spans (2 before LM3a, mud's; LM3a's snow 1, so a RutShoulderCm of 10 cm gives a near-vertical wall). */
	float RutShoulderMinCells = 2.f;
	/** Coherent firmer pockets leave a shallower floor, never deepen it beyond the requested sinkage. */
	float RutDepthVariation = 0.35f;
	float BellyFeatherCm = 35.f;

	/**
	 * Ridges: the share of a rut's lowered volume that comes back up beside it, over a band this wide, capped.
	 * Stage I (docs/MUD_ONE_SURFACE_PLAN.md section 3, the user's "still very sharp and uniform, needs to be more
	 * mudlike"): the band went 40 -> 90 cm and the cap 25 -> 12, and the sine hump became the plateau below, so the
	 * same volume makes a low wide rounded bank instead of a knife edge over two cells. RidgeReturn is unchanged.
	 */
	float RidgeReturn = 0.6f;
	float RidgeWidthCm = 90.f;
	float MaxRidgeCm = 12.f;
	/**
	 * Stage I1, the plateau profile: the weight rises over this many cm from the tyre's edge, holds flat, and fades to
	 * nothing over the last this many cm (the outer foot). At the default width that is 30 in, a flat third, 30 out.
	 */
	float RidgeFootCm = 30.f;
	/**
	 * Stage I2, variation along the rut. Two hashed noises along the stroke, at RidgeWaveCm and RidgeWaveLongCm, swing
	 * the bank's height by RidgeWave (0.7 of the short one and 0.5 of the long one) and its width by RidgeWidthWave.
	 * The noises are read at the cell's foot on the stroke, so they vary along the rut and not across it: a width that
	 * varied across the band would fold the profile.
	 * The wavelengths and the height swing are measured, not the plan's 120 / 300 / 0.5: stage H's 3-tap smoothing is
	 * applied to a cell by every stroke whose band reaches it, which over a 90 cm band is about 13 times, and that is
	 * a low-pass of sigma 27 cm - it keeps 96 % of a 600 cm wave, 79 % of 250 cm, 35 % of 120 cm and 1.6 % of 60 cm.
	 * With the plan's numbers the crest's coefficient of variation measured 0.20 where 0.35-0.6 was asked (and 0.24
	 * before stage I). At 250 / 600 / 1.0 the surviving swing is about three times that.
	 */
	float RidgeWaveCm = 250.f;
	float RidgeWaveLongCm = 600.f;
	float RidgeWave = 1.f;
	/** The width's own swing, the plan's 0.5 (0.5-1.5 of RidgeWidthCm): it sets the band, and so the stamp's reach and cost. */
	float RidgeWidthWave = 0.5f;
	/** One side of each tyre throws more than the other, by this much either way; which side is chosen by a 1 m noise. */
	float RidgeSideBias = 0.3f;
	/**
	 * Slump: about this share of the rut's length, in stretches of 40-80 cm (a 1 m noise thresholded at 1 - 2 x this),
	 * has half of its bank fall back into the rut. RidgeSlumpFloor of what falls settles on the floor there, which is
	 * the only place in the field where a stamp raises a floor - bounded by the depth the stamp cut plus that rise, so
	 * it cannot compound from tick to tick and can never come out above the ground.
	 */
	float RidgeSlump = 0.25f;
	float RidgeSlumpFloor = 0.333f;
	/** and never more than this much of the rut under it. Uncapped, a slump over a deep fresh stamp filled 3.6 cm of rut and the escape's rut mean went -32.1 -> -28.5; at 3 the bog's middle run sank the body 8 cm where section 23 asks for 8 (9 before stage I), because the rears drive on a floor the fronts' slump has filled, so 1: the slump still shows in the bank, which is where it is looked at, and its floor rise no longer reaches the sinkage model. */
	float RidgeSlumpRiseMaxCm = 1.f;
	/**
	 * How much of a bank's deposit a cell that is already a rut takes. Measured: with the band at 90-135 cm a pass
	 * throws its bank across the next pass's rut (the wheels and the two crawl lines are under a metre apart), and at
	 * 1.0 the escape's rut mean went -32.1 -> -27.3 cm with only 59 of 88 samples still past 0.6 of their sinkage.
	 * Mud thrown into a standing rut is swallowed by the slurry in it rather than rebuilding its floor, so a cell
	 * under -1 cm takes this share. Fresh ground (0) takes all of it, or every bank would lose two thirds.
	 */
	float RidgeFillShare = 0.35f;
	/** Clods: this share of the band's cells carry a lump half the local bank again, ClodMinCm to ClodMaxCm across (the size scales how much of the cell it fills). LM2a: 0 with the lumps on (they were under two cells and smoothed away); stage I's 0.15 stays a code path. */
	float ClodChance = 0.f;
	float ClodMinCm = 8.f;
	float ClodMaxCm = 15.f;
	/** The widest the band can be once RidgeWave has widened it: the stamp's reach, and how far the tests look for a ridge. */
	float RidgeBandCm() const { return RidgeWidthCm * (1.f + FMath::Clamp(RidgeWidthWave, 0.f, 1.f)); }

	/**
	 * Stage H, less spiky ruts (docs/MUD_ONE_SURFACE_PLAN.md section 3; AGTMudPatch owns the defaults as UPROPERTYs and
	 * pushes them in). A new hump is blended into a ridge cell that already carries one by max plus this fraction of the
	 * lesser of the two, not by adding them: every stamp's hump used to be summed, so where two humps met the crest
	 * spiked (the jagged crests of section 30). 1.0 is that sum exactly, which is how the test measures "before"; 0.9
	 * because 0.8 took a fifth off the crest's height (the test's along-crest mean 6.58 -> 5.12 cm) and the plan asks
	 * for the crest to keep it.
	 */
	float RidgeBlend = 0.9f;
	/**
	 * How far the cells a stamp touched are pulled toward a 3-tap mean along the stamp's own direction, in proportion to
	 * how far the stroke rolled over the tyre's width (a stamp is one physics tick, so a flat share per stamp would make
	 * the mud depend on the tick rate): the row of humps becomes one crest and the rut floor loses the step between one
	 * stamp and the next. A cell is only averaged with the cells of the same kind in the same stamp, and a floor cell may
	 * not come out above the depth this stamp cut it to, so compaction still holds. 0 is stage F's behaviour. 0.7 and not
	 * the plan's 0.5: at 0.5 the test's crest read a cell-to-cell difference sd of 0.54 cm where half of 0.94 was asked.
	 */
	float RidgeSmooth = 0.7f;
	/**
	 * Stage H, more randomness. The ridge's return varies by this much either way across the cells (0.65-1.35 at 0.35) at
	 * RidgeNoiseCells, so the crest crumbles into clumps instead of running level; the same noise ragged-edges the tracks
	 * factor across the tyre's edge (at 3 cells, and nothing smooths the tracks). A hash of the cell index, so a second
	 * pass deepens the same clumps: no state, and the same field twice over gives the same mud. 0.7 and not the plan's
	 * 0.35, measured: at 0.35 the crest's coefficient of variation came out 0.12, which is what the field had before
	 * stage H (the smoothing takes away as much as the noise puts in), and the plan asks for 0.2-0.4.
	 */
	float RidgeNoise = 0.7f;
	/**
	 * The clumps' wavelength in cells. The plan asked for 2-3; at that wavelength the 3-tap smoothing that makes the
	 * crest less spiky is the same filter as the noise that makes it random, and it wins (the test read a coefficient of
	 * variation of 0.07 against 0.12 with all of stage H off). 4 cells is half a metre of crest, which the smoothing
	 * passes and the eye reads as clumps rather than as a saw.
	 */
	float RidgeNoiseCells = 4.f;
	/** The rut floor's target varies by this many cm at a 4-6 cell wavelength (only ever lowered to, so a positive draw leaves that cell shallower). */
	float FloorNoiseCm = 1.5f;
	/** LM4 item 1: the cell-unit numbers StampWheel had hard-coded, now the profile's (the defaults are mud's values): the floor noise's wavelength (5 cells, 62.5 cm at 12.5), the firmer pockets' (12, 150 cm) and the tracks' ragged edge (3, 37.5 cm). */
	float FloorNoiseCells = 5.f;
	float PocketNoiseCells = 12.f;
	float TracksEdgeCells = 3.f;
	/** The hash's seed: the noise is a function of the cell alone, never of the stamp, so the same clumps grow pass after pass. */
	int32 NoiseSeed = 1;
	/** Benmore B2: CellNoise's lattice offset, cells (a zone tile's world cell index, so the noise runs on across its neighbours; 0 on every other field). */
	int32 NoiseCellX = 0;
	int32 NoiseCellY = 0;
	/** Slide-away: mud within SlideWidthCm of a wheel moves outward this much per metre the wheel travels, capped. */
	float SlideWidthCm = 60.f;
	float SlideCmPerMetre = 4.f;
	float MaxSlideCm = 20.f;

	/** Volume the stamps have lowered, cm^3 (a second pass down a rut lowers little: compaction). */
	double LoweredCm3 = 0.0;

	// ---- LM1, the living field (docs/LIVING_MUD_PLAN.md): a time step for the cells a wheel has recently touched -----
	/**
	 * Settle's numbers (bog mud; AGTMudPatch owns them as UPROPERTYs and pushes them in, a ford's profile is stiffer).
	 * Slump: a neighbour step steeper than tan(ReposeDeg) x CellCm loses half of min(SlumpRate x dt, 0.2) of its excess
	 * per sub-step. Ooze: while either cell of a pair was written by a stamp in the last SetSeconds, the pair levels by
	 * half of min(OozeRate x dt, 0.2) of its whole step. Smear: the receiving cell's OffsetCm drags SmearCmPerCm per cm
	 * moved. Fresh: 1 where the surface just moved, fading over FreshFadeS. A tile sleeps once it has been still
	 * (nothing over SleepCmPerS), set and dull for 0.5 s.
	 */
	float ReposeDeg = 38.f;
	float SlumpRate = 2.f;
	/** LM1's diffusion, kept for the owner to compare and 0 by default since LM1b: it is a blur (at 1.2 over 4 s it took away everything under 50-75 cm, the owner's "too smooth"). */
	float OozeRate = 0.f;
	float SetSeconds = 4.f;
	/**
	 * LM1b, the shape-keeping relax (docs/LIVING_MUD_PLAN.md LM1b): while a cell's SetS runs, its own height relaxes toward
	 * the ground at a = -ln(1 - RecoverShare) / SetSeconds per second, so a full set gives back RecoverShare of every
	 * cell's height. A rut cell rises and a bank cell sinks in proportion to its own height: the relief scales, it does
	 * not blur, and the rate does not depend on the rut's width. Per sub-step the rises of every set cell below 0 (V_up)
	 * and the falls of every set cell above 0 (V_down) are balanced over the patch: the larger side is scaled down to the
	 * smaller, so the rut rises only by what the banks give up (exact conservation). HeightCm only. Each moved cell's
	 * OffsetCm creeps down the surface's slope by CreepCmPerCm per cm it moved (capped at MaxSlideCm).
	 */
	float RecoverShare = 0.4f;   // the bog's (AGTMudPatch::RecoverShare); the plan's 0.2 gave 7.6 % back, the balance capping the rut at the banks' volume
	float CreepCmPerCm = 3.f;
	/** The relax's volumes so far, cm^3: what the set cells below 0 asked to rise (V_up) and above 0 asked to fall (V_down) before the balance, and what moved each way after it. For the test's report. */
	double RelaxAskedUpCm3 = 0.0;
	double RelaxAskedDownCm3 = 0.0;
	double RelaxMovedCm3 = 0.0;
	float SmearCmPerCm = 0.5f;
	float FreshFadeS = 6.f;
	float SleepCmPerS = 0.05f;
	/** The tile is SettleTileCells cells square (2 m at 12.5 cm) and the sub-step is SettleStepS, from an accumulator, so the result does not depend on the frame rate. */
	int32 SettleTileCells = 16;
	float SettleStepS = 1.f / 30.f;
	/**
	 * At most this many sub-steps in one call, so one frame's cost is at most two sub-steps' (the LM1 cost gate's max):
	 * the result is frame-rate independent down to 15 frames a second, and a frame slower than that (a hitch) drops the
	 * time over it rather than running a burst. 8 measured 1.40 ms on the frame after a 310 ms screenshot hitch.
	 */
	int32 SettleMaxSteps = 2;
	/** Per cell, 0..1: 1 where a stamp, a sub-step or a throw deposit just moved the surface by over FreshMinCm, fading. TreadTexture B. */
	TArray<float> Fresh;
	/** LM2a housekeeping 1: a cell is fresh when its surface moved more than this in one stamp or sub-step (LM1's 0.01 cm missed the relax's 0.006 cm a sub-step, so the sheen faded while the mud still moved). */
	float FreshMinCm = 0.002f;
	/** Per cell, seconds left of the ooze and the relax: SetSeconds where a stamp wrote the cell, counting down in Settle. */
	TArray<float> SetS;

	// ---- LM2a, lumps in the field and the wheel's throw (docs/LIVING_MUD_PLAN.md LM2a) --------------------------------
	/**
	 * Per cell, cm of lump on top of HeightCm. The surface everything reads (HeightAt, GradientAt, CellHeightCm, the
	 * upload, the water depth, Settle's talus, the traction through HeightAt) is SurfaceCm = HeightCm + LumpCm, so the
	 * render and the traction agree. Stage H's blend and smoothing and the stamps' compaction never touch it; the relax
	 * touches HeightCm only (LM1b), so a lump rides the bank as the bank sags.
	 */
	TArray<float> LumpCm;
	/** The surface at a cell: HeightCm + LumpCm. */
	float SurfaceCm(int32 Index) const { return HeightCm[Index] + (LumpCm.IsValidIndex(Index) ? LumpCm[Index] : 0.f); }
	/**
	 * The share of each stamp's bank deposit held back from HeightCm and spread over the stroke's band cells in proportion
	 * to the static lump weight W (smooth domes round hashed jittered sites LumpSpacingCells apart, radius LumpRadiusCells
	 * +- LumpRadiusJitter, seeded by NoiseSeed), normalised so the held volume is exactly what lands. A cell holds at most
	 * LumpMaxCm; the excess goes to HeightCm in the same cell. Bog numbers (AGTMudPatch owns them and pushes them in).
	 */
	float LumpShare = 0.35f;
	float LumpSpacingCells = 4.f;   // LM2a landed: the proposed 3 (37.5 cm) read the crest cv 1.15x LumpShare 0; 4 (50 cm) reads 1.59x (asked at least 1.5)
	float LumpRadiusCells = 1.6f;
	float LumpRadiusJitter = 0.4f;
	float LumpMaxCm = 10.f;
	/**
	 * LM3c follow-up (every medium): a lump's excess over LumpMaxCm goes back into the stroke's bank, spread over the band's
	 * cells that took this stamp's deposit by the weights the bank's plain (non-lump) deposit used, normalised so the volume
	 * is exact, instead of piling into HeightCm in its own cell (LM2a, false), which stacked single cells into spikes. The
	 * plough's berm the same over its own band. A thrown blob's (DepositLump) has no band and keeps LM2a's same-cell rule.
	 */
	bool bLumpOverflowToBand = true;
	// ---- LM2c, break the uniformity (docs/LIVING_MUD_PLAN.md LM2c) -----------------------------------------------
	/**
	 * LM2c on (the default): the sites jittered over their whole grid cell (+-0.5 of the spacing); a cluster noise
	 * (smoothed value noise, LumpClusterCm) leaves LumpAbsentShare of the sites out, in patches; a skewed amplitude per site
	 * (LumpAmpMin + (LumpAmpMax - LumpAmpMin) u^2); elliptical domes (aspect 1..LumpAspectMax, a random orientation, the
	 * radius +- LumpVarietyRadiusJitter); a satellite dome 0.6-0.9 of the radius away on LumpSatelliteChance of the sites.
	 * The bank clods come from random cells of the band's inner ClodBankInner beside the rut (the lip), each stamp's chance
	 * ClodBankPerCm x the cell's deposit (cm) x the cluster weight, power-law sizes (min + (max - min) u^ClodSizePower).
	 * Off: LM2a/LM2b exactly (the Variety test's comparison). Every number is from a hash of the cell or site and NoiseSeed.
	 */
	bool bLumpVariety = true;
	float LumpClusterCm = 150.f;
	float LumpAbsentShare = 0.5f;   // LM2c follow-up landed (0.35-0.55 tried): spacing cv 0.509 (0.45 and under read 0.35); stage I crest cv 0.62-0.64 at every share, so no share keeps it
	float LumpAmpMin = 0.3f;
	float LumpAmpMax = 1.6f;
	float LumpAspectMax = 2.2f;
	float LumpVarietyRadiusJitter = 0.6f;
	float LumpSatelliteChance = 0.2f;
	float ClodBankPerCm = 0.017f;   // LM2c follow-up landed: a third of LM2b's bank clods per metre on the broad test stroke at LumpAbsentShare 0.5 (LM2c's 0.014 at 0.35)
	float ClodBankInner = 0.4f;
	float ClodBankSizeMinCm = 3.f;
	float ClodBankSizeMaxCm = 18.f;
	float ClodSizePower = 2.5f;
	/** LM2c: the cluster noise at a cell (-1..1) and the weight the bank clods take from it: 0 below the absent threshold, rising to 1 half a unit above it. */
	float LumpClusterNoise(int32 X, int32 Y) const;
	float LumpClusterWeight(int32 X, int32 Y) const;
	/** LM2c: the cluster threshold in force (the LumpAbsentShare quantile of the noise over the sites; -2 before the weights are built or with the variety off). */
	float LumpClusterThreshold() const { return LumpClusterT; }
	/** LM2c readouts: lump sites built, left out by the cluster noise, given a satellite; and the bank clods' expected count per unit ClodBankPerCm (sum of deposit x cluster over the candidates, for the rate's calibration). */
	int32 LumpSitesBuilt = 0;
	int32 LumpSitesAbsent = 0;
	int32 LumpSatellites = 0;
	double ClodBankExpectPerRate = 0.0;

	/** The static lump weight at a cell, 0..1 (0 when the cell lies under no dome); LM2c: 0..LumpAmpMax. */
	float LumpWeightAt(int32 Index);
	/** The lump site a cell's dome belongs to (INDEX_NONE under none), and a site's centre in world cm. */
	int32 LumpSiteAt(int32 Index);
	FVector2D LumpSiteCentreCm(int32 Site) const;

	/** LM2a's volumes so far, cm^3 (the tests' bookkeeping; every one is cumulative like LoweredCm3). */
	struct FLumpBook
	{
		double HandedCm3 = 0.0;        // what the bank's cells would have taken with the lumps off: the deposit x the share of the band's weight on cells that take a deposit
		double BankAskedCm3 = 0.0;     // what the bank's cells were asked to take with the lumps on (HandedCm3 less the lumps' hold)
		double BankAddedCm3 = 0.0;     // what the bank's cells actually took (stage H's blend and the MaxRidgeCm cap keep some of it, as before LM2a)
		double LumpHeldCm3 = 0.0;      // the deposit's share held back for the lumps
		double LumpLandedCm3 = 0.0;    // of that, what went into LumpCm
		double LumpOverflowCm3 = 0.0;  // of that, what was over LumpMaxCm and went into HeightCm in the same cell
		double FlattenedCm3 = 0.0;     // lumps a capsule (or the belly) flattened into its displaced volume
		double DepositCm3 = 0.0;       // RidgeReturn x lowered, less the throw: what the stamps handed the bank, the lumps and the slump together
		double ThrownCm3 = 0.0;        // RidgeReturn x lowered x ThrowShare: what the stamps returned for the throw instead
		double ThrowLandedCm3 = 0.0;   // what DepositLump put back (the thrown blobs that came down on this field)
		int32 ThrowDeposits = 0;
	};
	FLumpBook Book;

	/**
	 * LM2a, a thrown blob coming down: a dome into LumpCm of radius DomeRadiusCm (AGTMudPatch::DepositThrown passes 1.5 x
	 * the blob's), at least one cell, with exactly VolumeCm3 (over LumpMaxCm into HeightCm in the same cell). Its cells
	 * are fresh (1) and its tiles wake. Returns the volume put down (0 outside the field).
	 */
	double DepositLump(const FVector2D& XYCm, double VolumeCm3, float DomeRadiusCm);

	// ---- LM2b, clods: the field queues where a clod should appear; AGTMudPatch's tick adds them ---------------------
	struct FClodSpawn
	{
		FVector2D XYCm = FVector2D::ZeroVector;
		float SizeCm = 10.f;
		int32 Seed = 0;
		uint8 Source = 0;   // 0 a bank site, 1 a throw landing, 2 the test fill, 3 (LM4) a lip plate fallen onto the trench floor, 4 (LM4d) spilled into the belly's channel, 5 (MR5) a mud chunk's break, 6 (MRD1) a mud road's churn-zone field (old and dry: no wet sinking)
		/** LM4: the stroke's heading, degrees, where the spawn has one (the snow shards' yaw runs along the lip); bHeading false: a random yaw. */
		float HeadingDeg = 0.f;
		bool bHeading = false;
	};
	/** Queued by StampWheel (bank sites) and AGTMudPatch::DepositThrown (throw landings) while bQueueClods; at most MaxPendingClods (the oldest dropped). */
	TArray<FClodSpawn> PendingClods;
	bool bQueueClods = false;
	int32 MaxPendingClods = 256;
	/** A lump site that has taken at least ClodBankMinCm of lump since its last roll rolls ClodBankChance, at most once per ClodRespawnS. Size ClodBankMinSizeCm..ClodBankMaxSizeCm, larger with the stamp's depth (full at ClodBankFullDepthCm). */
	float ClodBankChance = 0.35f;
	float ClodRespawnS = 3.f;
	float ClodBankMinCm = 2.f;
	float ClodBankMinSizeCm = 6.f;
	float ClodBankMaxSizeCm = 16.f;
	float ClodBankFullDepthCm = 40.f;
	/** The field's own clock, s (AGTMudPatch::Tick advances it every frame, whatever gt.Mud.Settle says): the clod respawn timer reads it. */
	double ClockS = 0.0;
	void AdvanceClock(float DeltaSeconds) { ClockS += FMath::Max(0.f, DeltaSeconds); }
	/** Queue one clod (drops the oldest past MaxPendingClods). */
	void QueueClod(const FClodSpawn& Spawn);

	/**
	 * One fixed-sub-step pass of the living field over the awake tiles and a one-cell border round them (slump, ooze,
	 * smear, fresh, the set timer, sleep). Volume-conserving by construction: every pair's flux leaves one cell and
	 * enters the other, through a delta buffer applied after the sweep, and the grid's outer edge is closed. Called by
	 * AGTMudPatch::Tick on the game thread, the thread the traction's stamps run on. Returns the sub-steps run.
	 */
	int32 Settle(float DeltaSeconds);
	/** Tiles awake now (Settle's work). */
	int32 AwakeTileCount() const;
	/**
	 * LM1b's detail measure over the given cells: D = RMS(S - the 3x3 mean of S) / RMS(S), S the cell's surface (LM2a: HeightCm + LumpCm; the 3x3
	 * mean over the neighbours inside the grid, the cell included). A relief that only scales keeps D; a blur lowers it.
	 */
	float DetailRatio(TArrayView<const int32> Cells) const;
	/** The cell's fresh value, bilinear, 0 outside. */
	float FreshAt(const FVector2D& XYCm) const;

	// ---- MudRunner MR3, muddy rut water (docs/MUDRUNNER_LESSONS_PLAN.md MR3 item 1) ------------------------------------
	/**
	 * Per cell, 0..1 (mud only; empty on snow): how churned the water standing in the cell is. A stamp that moved the cell
	 * (TouchCell, where it sets Fresh) or a throw's landing (DepositLump) sets it to 1 where the water over the cell -
	 * RutWaterTableCm over the surface, the deeper of before and after - is over TurbidMinWaterCm. SettleTurbidity's fixed
	 * sub-step (TurbidStepS) mixes it between wet 4-neighbours (TurbidMixRate per second, a pair exchanging only when both
	 * cells hold water, so never above either and never into a dry cell) and halves it every RutSettleS; a dry cell holds
	 * none. It keeps its own tile flags (TileTurbid, over the settle's tiles): a tile stays awake for it while any cell is
	 * at TurbidSleepBelow or more (or a turbid neighbour's wet edge faces it), then sleeps and its remainder goes to 0. The
	 * heights, offsets, tracks, tread and the settle's own tiles are never touched. Uploaded as TreadTexture A on mud.
	 */
	TArray<float> Turbidity;
	/** gt.Mud.MuddyWater as the patch pushes it (only where its rut water is drawn). False: nothing is set and SetMuddyWater cleared the array. */
	bool bMuddyWater = true;
	/** Where the rut water stands, cm relative to the undisturbed ground (the patch's CurrentWaterTableCm, pushed every tick); the default holds none. */
	float RutWaterTableCm = -1.e9f;
	float RutSettleS = 45.f;
	float TurbidMixRate = 0.15f;
	float TurbidMinWaterCm = 1.f;
	float TurbidSleepBelow = 0.02f;
	float TurbidStepS = 0.1f;
	/** At most this many sub-steps in one call (1 s of them); a longer frame drops the time over it, as Settle does. */
	int32 TurbidMaxSteps = 10;
	/** Per settle tile, awake for the turbidity. */
	TArray<uint8> TileTurbid;
	/** The water over a cell's surface, cm (negative: the surface stands above the table). */
	float WaterOverCm(int32 Index) const { return RutWaterTableCm - SurfaceCm(Index); }
	/** The turbidity's sub-steps for this frame over the turbid tiles; returns how many ran. The patch calls it every tick. */
	int32 SettleTurbidity(float DeltaSeconds);
	/** Tiles awake for the turbidity now. */
	int32 TurbidTileCount() const;
	/** The cell's turbidity, bilinear, 0 outside (or on snow). */
	float TurbidityAt(const FVector2D& XYCm) const;
	/** gt.Mud.MuddyWater: off clears every turbid tile (marked dirty, so the texture goes to 0) and sets nothing after. */
	void SetMuddyWater(bool bOn);
	/** A stamp or a landing churned this cell, whose surface's lower of before and after is SurfaceLowCm: 1 where water over TurbidMinWaterCm stands. */
	void ChurnWater(int32 Index, float SurfaceLowCm)
	{
		if (bMuddyWater && Turbidity.IsValidIndex(Index) && RutWaterTableCm - SurfaceLowCm > TurbidMinWaterCm)
		{
			Turbidity[Index] = 1.f;
			const int32 Tile = ((Index / SizeX) / TileCells) * TilesX + (Index % SizeX) / TileCells;
			if (TileTurbid.IsValidIndex(Tile))
			{
				TileTurbid[Tile] = 1;
			}
		}
	}

	void Init(const FBox2D& BoundsCm, float InCellCm);
	/** GR1b (AGTMudPatch::PreChurn): cells edited outside the stamps (non-zero in Edited, SizeX x SizeY) get a stamp's bookkeeping -
	 * their set timers started and their tiles woken - so Settle works them. Returns the cells. */
	int32 WakeEdited(const TArray<uint8>& Edited);
	bool IsValid() const { return SizeX > 0 && SizeY > 0; }
	FBox2D Bounds() const;
	bool Contains(const FVector2D& XYCm) const;
	// ---- LM3a, snow (docs/LIVING_MUD_PLAN.md LM3a) -------------------------------------------------------------------
	/**
	 * A snow field: the heights are relative to the snow's top, which stands SnowTopCm over the ground (the depth per cell
	 * x a smoothstep taper over SnowEdgeCm in from the box's border, so it meets the landscape at the edge). A tyre sits on
	 * the ground (Chaos has no snow collision), so StampWheel cuts each cell of its capsule to the tyre's own bottom,
	 * -(DepthCm + SnowTopCm), the sinkage below the ground plus the snow above it. Off (mud): every number below is unread.
	 */
	bool bSnow = false;
	float SnowDepthCm = 35.f;
	float SnowEdgeCm = 300.f;
	/** Per cell, the snow's depth (the section's drifts baked in; uniform SnowDepthCm otherwise) and the snow top there (depth x taper at the cell's centre), cm. Empty on mud. */
	TArray<float> SnowDepthCell;
	TArray<float> SnowTopCm;
	/** The belly's plough (PloughBelly): PloughReturn of what it cuts goes into a PloughBandCm band beside its box. */
	float PloughReturn = 0.3f;
	float PloughBandCm = 40.f;
	/** Refill while it snows, cm a minute toward the snow top (Refill). */
	float RefillCmPerMin = 2.f;
	/** The taper at a world point: smoothstep(0, SnowEdgeCm, the distance in from the box's border); 0 outside (geometry only, whatever the medium). */
	float SnowTaperAt(const FVector2D& XYCm) const;
	/** The snow top over the ground at a world point, cm: the cells' depth (bilinear) x the taper there; 0 on mud. */
	float SnowTopAt(const FVector2D& XYCm) const;
	float SnowTopCell(int32 Index) const { return SnowTopCm.IsValidIndex(Index) ? SnowTopCm[Index] : 0.f; }
	/** The snow surface over the ground at a world point, cm: SnowTopAt + HeightAt (HeightAt alone on mud). */
	float GroundRelativeAt(const FVector2D& XYCm) const { return SnowTopAt(XYCm) + HeightAt(XYCm); }
	/** Bakes the snow's depth per cell from DepthAt (world cm -> cm; uniform SnowDepthCm when unset) and the top from it. Init calls it with none on a snow field. */
	void BuildSnow(const TFunction<float(const FVector2D&)>& DepthAt = TFunction<float(const FVector2D&)>());
	/**
	 * LM3a, the belly in snow: a box LengthCm along Forward by WidthCm cut to UndersideCm over the ground wherever the snow
	 * stands above it (each cell to UndersideCm - its snow top, only ever lowered; the sides feathered over one wall,
	 * max(CellCm, RutShoulderCm)), its lumps flattened. PloughReturn of the volume goes into a PloughBandCm band beside each
	 * long side (a sine hump across it; LM3c: the bank path, bPloughBankPath), on cells that are not ruts, normalised so the
	 * volume is exact. LM3c: the cut cells no tyre covered this tick lose their tread and take the belly's heading. Returns
	 * the volume cut.
	 */
	double PloughBelly(const FVector2D& CentreCm, const FVector2D& Forward, float LengthCm, float WidthCm, float UndersideCm);
	/** The plough's readouts, cm^3: cut by the belly, put into its berms, and what found no cell to land on. */
	double PloughedCm3 = 0.0;
	double PloughBermCm3 = 0.0;
	double PloughLostCm3 = 0.0;
	// ---- LM3c, snow polish (docs/LIVING_MUD_PLAN.md LM3c) -------------------------------------------------------------
	/**
	 * LM3c item 3: the plough's berm goes through a tyre's bank path: the bank's plateau across a PloughBandCm band (its width
	 * swung by RidgeWidthWave), stage I's along-stroke waves (RidgeWave at RidgeWaveCm and RidgeWaveLongCm, read at the cell's
	 * foot on the box's long side), RidgeSideBias per side, RidgeNoise's clumps, and LumpShare of the deposit into the lump
	 * domes (LM2c's held share); no MaxRidgeCm cap (LM3b's berm had none) and no smoothing: a berm cell is marked
	 * (SnowMarkBerm) and stage H's ridge smoothing in StampWheel leaves it alone. False: LM3b's sine hump (the test's
	 * comparison). The volume is exact either way (PloughReturn of the cut, PloughBermCm3).
	 */
	bool bPloughBankPath = true;
	/** LM3c follow-up: the share of the plough's side deposit held for the lump domes (the snow profile's PloughLumpShare; the tyres' lips keep LumpShare). */
	float PloughLumpShare = 0.25f;
	/**
	 * LM3c follow-up: the berm's share of the bank path's height swings (RidgeWave, RidgeSideBias, RidgeNoise; 1 = the lips'
	 * own). Not a plan number: the no-spike rows (the crest's 90th percentile at most 1.3x its median, its highest at most
	 * 1.6x) do not hold at the lips' swings even with no lumps, so the berm takes this share of them.
	 */
	float PloughBankVariation = 1.f;
	/** LM3c: of PloughBermCm3, what went into the lumps (LumpCm, the cap's overflow excluded), cm^3. */
	double PloughLumpCm3 = 0.0;
	/**
	 * LM3c item 1 (snow only): per cell, the tyre-stamp tick that last wrote its tread (StampWheel), and the tick in force.
	 * PloughBelly clears the tread (PhaseTurns -1) on the cells it cuts that no tyre capsule covered since the last plough
	 * (the traction stamps the wheels and then ploughs, once a physics tick), writes its own heading there and marks them
	 * scraped; then the tick advances.
	 */
	TArray<uint32> TreadTickOf;
	uint32 TreadTick = 1;
	/** LM3c (snow only): per cell, SnowMarkScraped (the belly scraped it: the material's scrape streaks) and SnowMarkBerm (a plough berm cell). */
	TArray<uint8> SnowMark;
	static constexpr uint8 SnowMarkScraped = 1;
	static constexpr uint8 SnowMarkBerm = 2;
	/**
	 * LM3c item 2, broken lugs (snow only): per cell a static lug strength, 0 or LugStrengthMin..1: value noise at LugWaveCm
	 * ranked over the field into LugStrengthMin..1 (evenly), and LugMissingShare of the cells (a second noise at
	 * LugMissingCm, under its quantile) at 0, in patches. M_GT_Snow scales the lugs' tilt by it (LugTiltDeg the peak).
	 */
	TArray<float> LugStrength;
	float LugStrengthMin = 0.25f;
	float LugWaveCm = 55.f;
	float LugMissingShare = 0.2f;
	float LugMissingCm = 60.f;
	/** Builds LugStrength for the numbers in force (Init calls it on a snow field). */
	void BuildLugStrength();
	/**
	 * LM3c: the tread texture's A for a cell (AGTMudPatch::Upload, snow only): the lug strength where a tyre's tread is set
	 * (PhaseTurns >= 0), -1 where the belly scraped and no tread is set, 0 otherwise. MR3: on mud, the cell's Turbidity.
	 */
	float TreadAlpha(int32 Index) const
	{
		if (!bSnow)
		{
			return Turbidity.IsValidIndex(Index) ? Turbidity[Index] : 0.f;
		}
		if (!PhaseTurns.IsValidIndex(Index))
		{
			return 0.f;
		}
		if (PhaseTurns[Index] >= 0.f)
		{
			return LugStrength.IsValidIndex(Index) ? LugStrength[Index] : 1.f;
		}
		return (SnowMark.IsValidIndex(Index) && (SnowMark[Index] & SnowMarkScraped)) ? -1.f : 0.f;
	}
	/** LM3a: in snow a stamp hands its whole return to the lip's eligible cells (StampWheel); with none, it is booked here, cm^3. */
	double SnowBankLostCm3 = 0.0;
	/**
	 * LM3a, refill while it snows: every cell below the snow top rises RefillCmPerMin x Seconds / 60 toward it (never past),
	 * the tracks fade by the same share of SnowDepthCm, the lumps soften by the same cm. The whole field, dirty once. Returns
	 * the volume added, cm^3 (the snow that fell into the cuts).
	 */
	double Refill(float Seconds);
	double RefilledCm3 = 0.0;
	/** The tracks' fade carried between refill passes (bytes). */
	float RefillTrackCarry = 0.f;

	// ---- LM4, God of War snow deformation (docs/LIVING_MUD_PLAN.md LM4) ----------------------------------------------
	/**
	 * Item 2 (snow), crust plates: with bLumpPlates each lump site owns its Voronoi cell (the nearest site over the whole
	 * jittered set, the absent ones included, so the plates crowd and gap as LM2c's sites do) and a present site's lump is a
	 * flat plane over its cells, tilted PlateTiltMinDeg..PlateTiltMaxDeg toward a hashed azimuth: the deposit is held and
	 * spread over the plates by LM2a's rule (W = the site's LM2c amplitude, flat over its cell), then each plate the stamp
	 * touched is re-levelled to height T + tan(tilt) x (the cell's offset along the azimuth), clamped to 0..LumpMaxCm, with T
	 * solved so the plate keeps its volume (what the clamp cannot hold goes back to the stroke's band as LM3c's overflow).
	 * A plate's edge is a step against the next cell's plate. Off: LM2c's domes.
	 */
	bool bLumpPlates = false;
	float PlateTiltMinDeg = 5.f;
	float PlateTiltMaxDeg = 25.f;
	/** Item 2 readouts, per lump site (plate mode): its centre (cells), its tilt (degrees) and azimuth (radians), present or not. */
	struct FPlateSite
	{
		FVector2f CentreCells = FVector2f::ZeroVector;
		float TiltDeg = 0.f;      // LM4b soft domes: the skew
		float AzimuthRad = 0.f;
		bool bPresent = false;
		float RadiusCm = 0.f;     // LM4b soft domes: the dome's radius (cm) and its height cap (cm)
		float CapCm = 0.f;
	};
	TArray<FPlateSite> PlateSites;
	/** Item 2: the cells of each site's Voronoi cell (plate mode; CSR: SiteCellStart[Site]..SiteCellStart[Site + 1] into SiteCellList). */
	TArray<int32> SiteCellStart;
	TArray<int32> SiteCellList;
	/** Item 2, the plate mask M_GT_Snow reads (the tread texture's B on snow): the lump's share of 1.5 cm on a plate's cell, 0 elsewhere and with the plates off. */
	float PlateAlpha(int32 Index) const
	{
		// LM4b: on the soft domes too (the lumps' mask, which M_GT_Snow's edge mask reads on lips and berms).
		if (!bSnow || !LumpsShaped() || !LumpCm.IsValidIndex(Index) || !LumpSiteOf.IsValidIndex(Index) || LumpSiteOf[Index] == INDEX_NONE)
		{
			return 0.f;
		}
		return FMath::Clamp(LumpCm[Index] / 1.5f, 0.f, 1.f);
	}
	/** Item 2: builds the static lump weights now (a snow patch's plates at Init, so the first stamp does not pay for them). */
	void PrepareLumps() { EnsureLumpWeights(); }
	/**
	 * Item 3 (snow), a broken wall line: the capsule's half-width steps by +-WallStepMinCm..WallStepMaxCm, piecewise constant
	 * over WallSegMinCm..WallSegMaxCm segments along the stroke (segments of the world axis nearer the stroke's direction,
	 * their boundaries jittered; a hash of the segment, the wall's side and its 60 cm lane across). Inward, the cut still
	 * takes the tyre's own width to its full depth (the wall's top moves in, the floor stays). WallDropShare of the segments
	 * drop their lip plate into the trench: the lip cells beside them take no plate (marked SnowMarkDropped; what plate they
	 * held goes too) and that volume lands on the trench floor beside the wall, with FloorChunkChance of a floor chunk (a
	 * clod spawn, Source 3) once per segment. WallStepMaxCm 0: off (LM3c's smooth wall).
	 */
	float WallStepMinCm = 0.f;
	float WallStepMaxCm = 0.f;
	float WallSegMinCm = 15.f;
	float WallSegMaxCm = 30.f;
	float WallDropShare = 0.f;
	float FloorChunkChance = 0.f;
	static constexpr uint8 SnowMarkDropped = 4;
	/** Item 3: the wall's offset at a stroke's foot point (world cm) on the side Side (+1 the +across side of the stroke's dominant world axis, -1 the other), cm, and whether its segment drops its plate; the segment's key out. 0 / false with the steps off. LM4b: the continuous waves in place of the steps (WallWave*), and the drop's feathered share (0..1) in OutDropWeight. */
	float WallOffsetAt(const FVector2D& FootCm, const FVector2D& LineDir, float Side, bool& bOutDrop, uint64& OutKey, float* OutDropWeight = nullptr) const;
	/** Item 3 readouts: lip-plate drops (stamp-side events), the volume moved to the floor (cm^3), floor chunks queued, lip (bank) chunks queued. */
	int32 WallDrops = 0;
	double WallDropCm3 = 0.0;
	int32 FloorChunksQueued = 0;
	int32 LipChunksQueued = 0;
	/** Item 4: the bank clods' chance is per 12.5 cm cell's area (ClodBankPerCm's calibration), so it scales by the cell's area: the count per metre does not depend on the grid. 1 at 12.5. */
	float ClodAreaScale() const { return (CellCm * CellCm) / (12.5f * 12.5f); }
	/**
	 * Item 6 (snow), an uneven snow top: static world noise (three value-noise octaves, each rotated, at SnowTopWaveMaxCm down
	 * to SnowTopWaveMinCm), about SnowTopUndulationCm of sd, added to the depth before the taper. SnowTopAt (and so the mesh's
	 * rest, the stamps' cut through SnowTopCm and the traction's GroundRelativeAt) read it. 0: LM3c's flat top.
	 */
	float SnowTopUndulationCm = 0.f;
	float SnowTopWaveMinCm = 60.f;
	float SnowTopWaveMaxCm = 300.f;
	/** The undulation alone at a world point, cm (0 with it off or on mud). */
	float SnowTopNoiseCm(const FVector2D& XYCm) const;

	// ---- LM4b, soft shape and crumbly detail (docs/LIVING_MUD_PLAN.md LM4b) ------------------------------------------
	/**
	 * Item 1 (snow), a continuous wall line: with WallStepMaxCm 0 (LM4's steps off) the capsule's half-width varies along the
	 * stroke by two octaves of smoothed value noise, WallWaveAmpCm at WallWaveCm and WallWaveLongAmpCm at WallWaveLongCm
	 * (along the world axis nearer the stroke's direction, a lattice row per wall side and 60 cm lane as LM4's segments), so
	 * the outline wanders without a step. The segments stay for the drops (WallDropShare) only. Both 0: no wander.
	 */
	float WallWaveCm = 25.f;
	float WallWaveLongCm = 70.f;
	float WallWaveAmpCm = 0.f;
	float WallWaveLongAmpCm = 0.f;
	/** Item 2: the fallen-plate notch's ends feather over this many cells (the drop's share ramps 0..1 across each segment boundary); 0: LM4's hard notch. */
	float WallDropFeatherCells = 0.f;
	/** Item 2: per cell (snow), the largest feathered drop share a stamp gave it, 0..255 (the soft domes' re-shape keeps 1 - it of the kernel there). */
	TArray<uint8> LipDropShare;
	/** Whether the wall line does anything (steps, waves or drops): snow only. */
	bool WallLineOn() const { return bSnow && (WallStepMaxCm > 0.f || WallWaveAmpCm > 0.f || WallWaveLongAmpCm > 0.f || WallDropShare > 0.f); }
	/**
	 * Item 2 (snow), soft lumps: LM2c's domes (the jittered sites, the cluster skips, the amplitude spread, the ovals and the
	 * satellites) leaning by a skew of LumpSkewMinDeg..LumpSkewMaxDeg toward a hashed azimuth: the dome's weight times
	 * 1 + tan(skew) x (the offset along the azimuth) / the site's height, so a dome at its full height leans by the skew at
	 * its top. The held share lands by W (LM2a's normalisation) and each dome the stamp touched is re-shaped to its own
	 * kernel, T x W, its volume kept, its peak at most the site's height cap: min(LumpMaxCm, LumpHeightPerRadius x its radius),
	 * so a small dome stays low and round instead of a capped column (the excess goes to the band as LM3c's overflow).
	 * Lip chunks come from the domes' edges (LM4's plates' rule). False: LM2c's upright, per-cell capped domes.
	 */
	bool bLumpSoftDomes = false;
	float LumpSkewMinDeg = 0.f;
	float LumpSkewMaxDeg = 0.f;
	float LumpHeightPerRadius = 0.f;
	/** Item 2: the height cap also scales by (the site's amplitude / LM2c's mean amplitude)^LumpCapAmpPower (0: one cap per radius). */
	float LumpCapAmpPower = 0.f;
	/** Item 2: and by (its radius / the mean radius)^LumpCapRadiusPower (0: off). */
	float LumpCapRadiusPower = 0.f;
	/** Item 2: re-shape each listed dome (site) to T x its kernel over its standing cells, keeping its volume up to its cap; returns the excess (cm^3) and widens the written cells' box. */
	double ReshapeDomes(TArrayView<const int32> Sites, int32& InOutX0, int32& InOutY0, int32& InOutX1, int32& InOutY1);
	/** The shaped-lump modes (LM4's plates or LM4b's soft domes): the held share lands by W and each touched site is re-shaped. */
	bool LumpsShaped() const { return bLumpPlates || bLumpSoftDomes; }
	double ReshapeLumps(TArrayView<const int32> Sites, int32& InOutX0, int32& InOutY0, int32& InOutX1, int32& InOutY1)
	{
		return bLumpPlates ? ReshapePlates(Sites, InOutX0, InOutY0, InOutX1, InOutY1) : ReshapeDomes(Sites, InOutX0, InOutY0, InOutX1, InOutY1);
	}

	// ---- LM4c, piles not walls (docs/LIVING_MUD_PLAN.md LM4c) -----------------------------------------------------------
	/**
	 * Item 1 (snow), the talus per cell: with bCellRepose a neighbour pair's talus is the higher cell's - LooseReposeDeg where
	 * that cell stands above the snow top (the berm, the lip, their lumps) or holds a collapse's pile (SnowMarkDebris), and its
	 * static wall repose below the top: WallReposeDeg +- WallReposeRangeDeg by world noise (two octaves of value noise at
	 * WallReposeWaveMinCm and WallReposeWaveMaxCm, ranked over the field so the angles spread evenly over the range). Snow's
	 * SetSeconds stays 0 (no relax). Off: ReposeDeg everywhere (mud, and LM4b's snow).
	 */
	bool bCellRepose = false;
	float LooseReposeDeg = 35.f;
	float WallReposeDeg = 60.f;
	float WallReposeRangeDeg = 20.f;
	float WallReposeWaveMinCm = 40.f;
	float WallReposeWaveMaxCm = 80.f;
	/**
	 * Item 2 (snow), delayed wall collapses: the cut wall in segments of CollapseSegMinCm..CollapseSegMaxCm along the world axis
	 * nearer the stroke (boundaries jittered; a hash of the segment, the wall's side and its 60 cm lane, as LM4's), CollapseChance
	 * of them collapsing CollapseDelayMinS..CollapseDelayMaxS (a hash) after a stamp last cut them (lowered a cell of the cut's
	 * outer CollapseArmOut of the tyre's half width by CollapseArmMinCm or more): per station the top CollapseTopMin..Max of the
	 * wall above the floor beside it (the lip and the berm included) comes off down to a plane rising back from the wall's foot
	 * at the loose repose, its ends feathered over CollapseFeatherCells cells, and the volume lands exactly as a cone on the
	 * trench floor at the wall's foot (its cells marked SnowMarkDebris: loose), with CollapseClumpsMin..Max clumps on it.
	 * Settle drives the timers (SettleClockS), so the same stamps and the same dt give the same collapses. 0: off.
	 */
	float CollapseChance = 0.f;
	float CollapseSegMinCm = 30.f;
	float CollapseSegMaxCm = 80.f;
	float CollapseDelayMinS = 0.5f;
	float CollapseDelayMaxS = 3.f;
	float CollapseTopMin = 0.3f;
	float CollapseTopMax = 0.6f;
	float CollapseFeatherCells = 2.f;
	int32 CollapseClumpsMin = 1;
	int32 CollapseClumpsMax = 2;
	/** Not plan numbers: what arms a segment (a stamp lowering a cell of the cut's outer part, D over CollapseArmOut x the tyre's half width, by at least CollapseArmMinCm). */
	float CollapseArmMinCm = 1.f;
	float CollapseArmOut = 0.6f;
	/** SnowMark: a cell holding a collapse's pile (loose snow below the top); cleared when a stamp cuts the cell. */
	static constexpr uint8 SnowMarkDebris = 8;
	/**
	 * Item 3 (snow), the berm in piles: bPloughFallingProfile - the plough's bank weight across its band falls from the wall
	 * outward ((1 - u)^2 over the band's width, u 0 at the wall) in place of stage I's plateau; and the plough's and the lips'
	 * bank weights are scaled by a cluster factor read at the cell's foot on its line: PileClusterMin..PileClusterMax by a world
	 * value noise of two octaves at PileWaveMinCm and PileWaveMaxCm, ranked over the field (evenly over the range). The volume
	 * is normalised as before, so it is exact. PileClusterMin = Max = 1: off.
	 */
	bool bPloughFallingProfile = false;
	/** Not a plan number: the falling profile's exponent, (1 - u)^PloughFallPower. LM4c landed 0.5 (GrandTour.Snow.Piles' sweep: 2 put most of the berm on the wall's edge, where the loose talus poured it into the trench - the floor debris row read 52 %). */
	float PloughFallPower = 0.5f;
	/** Not a plan number: how the ranked cluster noise maps onto PileClusterMin..Max - 0 evenly (u), 1 by smoothstep(u) (more of the trench in piles and gaps, fewer middling stretches), between them a blend. */
	float PileContrast = 1.f;   // LM4c landed (the sweep: the crest cv 0.29 -> 0.35 at 0.05-1.8 with it)
	float PileClusterMin = 1.f;
	float PileClusterMax = 1.f;
	float PileWaveMinCm = 100.f;
	float PileWaveMaxCm = 250.f;
	/** Whether the per-cell repose and the pile factor are in force (snow with their numbers set). */
	bool CellReposeOn() const { return bSnow && bCellRepose; }
	bool PilesOn() const { return bSnow && (PileClusterMin != 1.f || PileClusterMax != 1.f); }
	/** Builds the static per-cell arrays (the wall repose's talus, the pile factor) for the numbers in force now (the patch calls it at Init; Settle and the stamps build them on first use otherwise). */
	void PrepareSnowPiles() { EnsureSnowPiles(); }
	/** The cluster factor at a world point (the cell under it; 1 with the piles off). */
	float PileFactorAt(const FVector2D& XYCm);
	/** The wall repose at a cell, degrees (ReposeDeg with the per-cell repose off). */
	float WallReposeAt(int32 Index);
	/** The settle clock, s: the sub-steps Settle has run times their length (the collapse timers read it). */
	double SettleClockS = 0.0;
	/** Item 2: one wall segment that collapses, as the last stamp that cut it left it. */
	struct FCollapseSeg
	{
		uint64 Key = 0;
		int8 Side = 0;            // +1 the +across side of the dominant world axis, -1 the other
		bool bAlongX = true;
		double Along0 = 0.0;      // the segment along the axis, world cm
		double Along1 = 0.0;
		FVector2D LinePoint = FVector2D::ZeroVector;   // a point on the stroke's line (world cm) and its direction
		FVector2D LineDir = FVector2D(1.0, 0.0);
		float FaceCm = 0.f;       // the wall's foot, cm out from the line (the tyre's half width plus the wall line's offset)
		float FloorCm = 0.f;      // the cut's floor at the wall's foot (relative to the snow top), cm
		double ArmS = 0.0;        // SettleClockS when a stamp last cut it
		float DelayS = 0.f;       // CollapseDelayMinS..MaxS by the hash
		float TopShare = 0.f;     // CollapseTopMin..Max by the hash
		bool bPending = false;
		int32 Fired = 0;
	};
	TArray<FCollapseSeg> CollapseSegs;
	/** Item 2 readouts: collapses fired, the volume they moved (cm^3), the segments armed (first cut), the clumps queued, and each collapse's record (the first 1024). */
	int32 CollapsesFired = 0;
	double CollapseCm3 = 0.0;
	int32 CollapseSegsArmed = 0;
	int32 CollapseClumpsQueued = 0;
	struct FCollapseEvent
	{
		FVector2D XYCm = FVector2D::ZeroVector;   // the pile's centre (world cm)
		int8 Side = 0;
		float DelayS = 0.f;        // after the last cut
		double VolumeCm3 = 0.0;
		float TopShare = 0.f;
		float PileTopCm = 0.f;     // the pile's highest rise over the floor it landed on, cm
		float SegCm = 0.f;         // the segment's length, cm
		double AtS = 0.0;          // SettleClockS when it fell
	};
	TArray<FCollapseEvent> CollapseLog;
	/** Item 2: the collapse segment at a stroke's foot point (world cm) on side Side: true when it is one of the CollapseChance that collapse; its key and its extent along the axis out. */
	bool CollapseSegmentAt(const FVector2D& FootCm, const FVector2D& LineDir, float Side, uint64& OutKey, double& OutAlong0, double& OutAlong1) const;

	// ---- LM4d, the belly's channel isn't flat (docs/LIVING_MUD_PLAN.md LM4d) ------------------------------------------
	/**
	 * Item 1 (snow): the plough's target over the ground varies by +-BellyUndulationCm - two octaves of value noise, BellyWaveMinCm
	 * and BellyWaveMaxCm across and BellyStretch times longer along the world axis nearer the heading (each octave's lattice
	 * rotated in its own space so it never lines up with the trench). World-anchored, not in the heading's frame: the heading's
	 * small swings would turn a heading-frame noise about the world's origin, and the cut, only ever lowering, would keep the
	 * deepest of every one of them. 0: LM4c's level floor.
	 */
	float BellyUndulationCm = 0.f;
	float BellyWaveMinCm = 20.f;
	float BellyWaveMaxCm = 60.f;
	float BellyStretch = 2.5f;
	/**
	 * Item 2 (snow), smear ridges: snow the belly drags drops out behind it in low ridges along the world axis nearer the heading -
	 * world lanes SmearLaneCm across, each cut into SmearLengthMinCm..MaxCm segments (its own phase, boundaries jittered); a
	 * segment is a ridge on a hash under SmearChance x 2 x a cluster noise at SmearClusterCm (so they bunch), SmearWidthMinCm..MaxCm
	 * wide (its centre jittered in the lane), SmearHeightMinCm..MaxCm high, parabolic across and tapered over its ends. The plough
	 * lays it on the channel's cells (scraped, no tyre) as they leave the box (a ChannelBandCm band behind it, each cell once:
	 * SnowMarkSmeared), out of its return: moved, not lost. 0: none.
	 */
	float SmearChance = 0.f;
	float SmearLaneCm = 20.f;
	float SmearLengthMinCm = 30.f;
	float SmearLengthMaxCm = 80.f;
	float SmearWidthMinCm = 8.f;
	float SmearWidthMaxCm = 15.f;
	float SmearHeightMinCm = 1.f;
	float SmearHeightMaxCm = 3.f;
	float SmearClusterCm = 120.f;
	/**
	 * Item 3 (snow), spill: PloughSpillShare of the plough's side deposit falls back into the channel behind the box as soft domes
	 * on the lump sites (LM4b's, each at most its height cap in LumpCm, what is over it a soft mound in HeightCm under it by the
	 * same kernel), by the site's kernel and the lumps' cluster weight (scattered and clustered); a site's first spill rolls
	 * SpillClumpChance x the cluster weight for a snow clump on it (Source 4). Sites whose centre is SpillBackCm behind the box, so
	 * a dome lies wholly behind it. 0: none.
	 */
	float PloughSpillShare = 0.f;
	float SpillClumpChance = 0.f;
	/** Not plan numbers: the band behind the box the ridges land in (wider than a tick's travel), and how far behind it the spill's domes centre. */
	float ChannelBandCm = 25.f;
	float SpillBackCm = 30.f;
	static constexpr uint8 SnowMarkSmeared = 16;
	/** Item 1: the target's offset at a world point (cm; 0 off). Item 2: the smear ridges' height there (cm; 0 off or between ridges). */
	float BellyOffsetCm(const FVector2D& XYCm, const FVector2D& Forward) const;
	float SmearRidgeCm(const FVector2D& XYCm, const FVector2D& Forward) const;
	/** Readouts: the ridges' volume and cells laid, the spill landed (all of it, and the part in LumpCm), the clumps queued, cm^3. */
	double SmearCm3 = 0.0;
	int32 SmearCells = 0;
	double SpillCm3 = 0.0;
	double SpillLumpCm3 = 0.0;
	int32 SpillClumpsQueued = 0;
	int32 SpillSitesCount() const { return SpillSites.Num(); }
	uint32 StampStepsCount() const { return StampSteps; }

	/** Bilinear samples; the edge value outside. HeightAt is the surface (HeightCm + LumpCm since LM2a). */
	float HeightAt(const FVector2D& XYCm) const;
	/** LM2a: the lumps alone, bilinear. */
	float LumpAt(const FVector2D& XYCm) const;
	FVector2f OffsetAt(const FVector2D& XYCm) const;
	float TracksAt(const FVector2D& XYCm) const;
	/** Height slope, cm per cm, central differences over a cell. */
	FVector2D GradientAt(const FVector2D& XYCm) const;

	/** The cell a point falls in (clamped to the grid), or INDEX_NONE when the field is empty. */
	int32 CellIndexAt(const FVector2D& XYCm) const;
	/** One cell's own height, no interpolation: what the mesh's vertex there carries, and what a profile "every cell" means (the test's along-crest profile). */
	float CellHeightCm(int32 Index) const { return HeightCm.IsValidIndex(Index) ? SurfaceCm(Index) : 0.f; }
	/** A cell's centre in world cm. The values are carried at cell centres, so a bilinear sample here is exactly that cell's own value (the stage G water gate reads the field through the patch's API at a cell it picked by index). */
	FVector2D CellCentreCm(int32 Index) const
	{
		return (SizeX > 0 && HeightCm.IsValidIndex(Index))
			? OriginCm + FVector2D(static_cast<double>(Index % SizeX) + 0.5, static_cast<double>(Index / SizeX) + 0.5) * CellCm
			: OriginCm;
	}
	/** Smoothed value noise over the cell lattice at a wavelength in cells, -1..1: a hash of the cell index and the field's seed, no state. */
	float CellNoise(int32 X, int32 Y, float WavelengthCells, int32 Salt) const;

	/**
	 * The tread phase the mud material draws at a world point: the nearest cell's phase carried across that cell along
	 * the heading it was stamped with (exactly what M_GT_Mud does, so a readback is what the picture will show), 0..1;
	 * -1 where no wheel has stamped. Never interpolated: a wrapping phase and a wrapping angle cannot be blended.
	 */
	float TreadPhaseAt(const FVector2D& XYCm) const;
	/** The heading stamped into the nearest cell, turns 0..1; -1 where no wheel has been. */
	float TreadHeadingAt(const FVector2D& XYCm) const;

	/**
	 * A tyre WidthCm wide rolled from FromCm to ToCm, sunk DepthCm: the capsule is lowered to -DepthCm, ridges and slide
	 * beside it. HeadingDir is where the tyre is heading (world XY, it need not be normalised) and RolledCm how far its
	 * contact patch has travelled over the ground in all (stage H0; the wheel's own rolled distance until then, which
	 * wheelspin ran away with): together they write the tread into every cell of the
	 * capsule, phase = frac((RolledCm + the cell's offset from ToCm along the heading) / LugPeriodCm). A later pass
	 * overwrites it, which is right; reverse flips the heading, which is right too.
	 */
	double StampWheel(const FVector2D& FromCm, const FVector2D& ToCm, float WidthCm, float DepthCm, const FVector2D& HeadingDir, float RolledCm)
	{
		double Unused = 0.0;
		return StampWheel(FromCm, ToCm, WidthCm, DepthCm, HeadingDir, RolledCm, 0.f, Unused);
	}
	/**
	 * LM2a, the throw: ThrowShare of the bank's deposit (RidgeReturn x what this stroke lowered, the flattened lumps
	 * included) is not deposited and is returned in OutThrownCm3 instead (set, not added). ThrowShare 0 is the stroke above.
	 */
	double StampWheel(const FVector2D& FromCm, const FVector2D& ToCm, float WidthCm, float DepthCm, const FVector2D& HeadingDir, float RolledCm,
		float ThrowShare, double& OutThrownCm3);
	/** The belly: a box LengthCm along Forward by WidthCm flattened to -DepthCm, no ridges. */
	double StampBelly(const FVector2D& CentreCm, const FVector2D& Forward, float LengthCm, float WidthCm, float DepthCm);

	/** The cells touched since the last take (Min inclusive, Max exclusive); false when nothing changed. */
	bool TakeDirty(FIntRect& OutRect);
	/**
	 * LM4e cut 2: the same cells as one box per settle tile they fall in (each the tile's touched cells' box), and their union;
	 * false when nothing changed. Either take clears both.
	 */
	bool TakeDirtyRects(TArray<FIntRect>& OutRects, FIntRect& OutUnion);
	/**
	 * LM4e cut 2: Count cells of one row from Index0 into the field texture's texels (R the surface m, GB the slide m, A the
	 * tracks) and the tread texture's (R heading turns, G lug phase, B the lumps' mask on snow or the fresh sheen on mud when
	 * bFreshSheen, A TreadAlpha): AGTMudPatch::Upload's encoding, the same values, with the per-cell checks hoisted.
	 */
	void EncodeTexels(int32 Index0, int32 Count, FFloat16Color* OutField, FFloat16Color* OutTread, bool bFreshSheen) const;

	// ---- LM4e, the snow's cost (docs/LIVING_MUD_PLAN.md LM4e) -----------------------------------------------------------
	/**
	 * LM4e, the record and the replay: one call into the field from outside it - the traction's stamps and plough, the patch's
	 * throw landings, its clock and settle and the end of its frame - so a drive's field can be rebuilt exactly (the before and
	 * after pictures on the same snow, and Settle's and the upload's cost on the same work). Plain data: saved as bytes.
	 */
	struct FEvent
	{
		uint8 Kind = 0;
		uint8 Flag = 0;
		uint8 Pad[6] = {};
		double V[10] = {};
	};
	enum : uint8 { EventStampWheel = 1, EventPloughBelly = 2, EventStampBelly = 3, EventThrow = 4, EventClock = 5, EventSettle = 6, EventFrame = 7, EventRefill = 8, EventChunk = 9 /* MR5: a mud chunk's break, its dome */ };
	/** Set while the patch records: the outside calls append here (the field's own nested calls do not). */
	TArray<FEvent>* EventLog = nullptr;
	/** The outside stamp calls' game-thread time since the patch last took it, ms (StampWheel, PloughBelly, StampBelly and the throw's landings). */
	double StampMs = 0.0;
	/** How deep the outside calls are nested (the outermost one is timed and recorded). */
	int32 CallDepth = 0;
	struct FOuterCall
	{
		FGTMudField& Field;
		double Start = 0.0;
		bool bOuter = false;
		explicit FOuterCall(FGTMudField& InField) : Field(InField)
		{
			bOuter = Field.CallDepth++ == 0;
			if (bOuter)
			{
				Start = FPlatformTime::Seconds();
			}
		}
		~FOuterCall()
		{
			--Field.CallDepth;
			if (bOuter)
			{
				Field.StampMs += (FPlatformTime::Seconds() - Start) * 1000.0;
			}
		}
		void Record(uint8 Kind, std::initializer_list<double> Values) const
		{
			if (bOuter && Field.EventLog)
			{
				FEvent Event;
				Event.Kind = Kind;
				int32 K = 0;
				for (const double Value : Values)
				{
					if (K < 10)
					{
						Event.V[K++] = Value;
					}
				}
				Field.EventLog->Add(Event);
			}
		}
	};
	/** LM4e readouts for the cost: the tiles swept and the tiles in the work list over the sub-steps since the patch last took them. */
	int32 SweptTilesSinceTake = 0;
	int32 ListedTilesSinceTake = 0;
	/**
	 * LM4e cut 1 (snow; the patch pushes gt.Snow.QuietSleep): Settle keeps no fresh sheen on snow (M_GT_Snow draws none: the
	 * tread texture's B is the lumps' mask), so a still tile sleeps after its 0.5 s quiet instead of holding the sheen's 6 s
	 * fade awake and marking the fading cells dirty, and a sleeping tile that flux reaches takes a still tile's test. The
	 * heights and lumps move as before (a tile that is still is swept no more than a sleeping one). Mud keeps its sheen.
	 */
	bool bSnowQuietSleep = true;
	/** LM4e cut 3 (snow; the patch pushes gt.Snow.FastSweep): Settle passes over a pair under the smallest talus before looking its talus up (exact), and keeps no smear on snow (OffsetCm is not drawn on snow nor read back). */
	bool bSnowFastSweep = true;

	// ---- LM4f, the bigger snow cuts behind switches (docs/LIVING_MUD_PLAN.md LM4f) ----------------------------------------
	/**
	 * LM4f item 3 (snow; gt.Snow.FastSettle, which the patch pushes every tick and a new field takes as its default, so the
	 * CPU tests follow the console too):
	 * 1: the snow's talus at FastSettleHz (15 Hz: the sub-step 1/15 s instead of SettleStepS' 1/30, each step moving twice as far);
	 *    only the tiles within FastSettleBandCm of a write (a stamp, the plough, a landing, a collapse) in the last
	 *    FastSettleBandS, or by a pending collapse, stay awake (the others sleep, though flux still reaches them); and the sweep
	 *    and the apply run over the tiles in parallel - each tile's flux logged in the serial order and added in the work list's
	 *    order, so the sums are the serial ones (deterministic, and bit-identical to the serial sweep).
	 * 2: the parallel sweep and apply alone (a check that they are exact: every row as 0).
	 * 3: the parallel part and 15 Hz, no band; 4: the parallel part and the band, at 30 Hz (each half of 1 alone, for the A/B).
	 * 0: LM4e's settle. Mud: always 0.
	 */
	int32 SnowFastSettle = DefaultSnowFastSettle();
	/** gt.Snow.FastSettle's value now (1 if the console variable is not registered). */
	static int32 DefaultSnowFastSettle();
	float FastSettleHz = 15.f;
	float FastSettleBandCm = 200.f;
	float FastSettleBandS = 3.f;
	/**
	 * LM4f item 4: the static per-cell noises the stamps read (StampWheel's stations, floor and band; PloughBelly's berm),
	 * built for the numbers in force (exactly CellNoise's values: the stamps read them instead of hashing per stamp). The
	 * patch calls it once its numbers are in, so no stamp builds them; a stamp rebuilds a stale one (a number or the size
	 * changed).
	 */
	void PrepareStampNoise();

private:
	FIntRect Dirty;
	bool bDirty = false;
	void MarkDirty(int32 X0, int32 Y0, int32 X1, int32 Y1);
	// LM4e cut 2: the dirty cells per settle tile (an empty box where clean) and the tiles that have any, in the order they got them.
	TArray<FIntRect> TileDirtyRect;
	TArray<int32> DirtyTiles;
	bool bDirtyUnsplit = false;

	// LM1: the settle state. Tiles are TilesX x TilesY; a tile is awake while TileAwake is set, and TileQuietS counts how
	// long it has been still. SettleDelta is the sweep's flux, zero outside a sweep.
	int32 TilesX = 0;
	int32 TilesY = 0;
	int32 TileCells = 16;
	TArray<uint8> TileAwake;
	TArray<float> TileQuietS;
	/** An awake tile that was still in the last sub-step (nothing setting, nothing moved over SleepCmPerS): its heights are frozen as a sleeping tile's are and only its sheen fades, so it skips the sweep until flux or a stamp moves it. */
	TArray<uint8> TileStill;
	TArray<uint8> SettleSweeps;    // per tile, swept this sub-step (the pair ownership test)
	TArray<float> SettleDelta;
	/** LM2a: the part of SettleDelta that left a cell by the talus or the ooze (<= 0); it is taken from the cell's LumpCm first, so lumps sag before the bank does. */
	TArray<float> SettleOut;
	TArray<int32> RelaxCells;      // LM1b: the set cells of one sub-step's swept tiles (the relax's two passes)
	// LM2a: the static lump weights, built on first use for the numbers in force (no state: the same domes every pass).
	TArray<float> LumpW;
	TArray<float> LumpWFull;       // LM2c follow-up: the weight a full site set would give (absent sites' domes too); empty with LM2c off
	TArray<int32> LumpSiteOf;
	int32 LumpSitesX = 0;
	int32 LumpSitesY = 0;
	float LumpKeySpacing = -1.f;
	float LumpKeyRadius = -1.f;
	float LumpKeyJitter = -1.f;
	int32 LumpKeySeed = INT32_MIN;
	int32 LumpKeyCells = -1;
	int32 LumpKeyVariety = -1;
	int32 LumpKeyPlates = -1;      // LM4: the plates' switch and tilt range the weights were built for (a hash of them)
	float LumpKeySoft = -1.f;      // LM4b: the soft domes' switch, skew range and height per radius (a sum of them)
	float LumpClusterT = -2.f;     // LM2c: the cluster noise's absent threshold
	uint32 StampSteps = 0;         // LM2c: stamps so far (the bank clods' hash)
	void EnsureLumpWeights();
	/** LM2c: one elliptical dome into LumpW (max-combined; cells in cells), owned by Site. */
	void AddLumpDome(const FVector2D& CentreCells, float RadiusCells, float Aspect, float AngleRad, float Amplitude, int32 Site, bool bPresent = true,
		float SkewTan = 0.f, float SkewAzimuthRad = 0.f, float SkewRefCm = 1.f);
	// LM2b: per lump site, the lump taken since its last clod roll and when it last spawned one.
	TArray<float> SiteLumpCm;
	TArray<double> SiteClodS;
	TArray<int32> SitePeak;        // per site, the cell at the top of its dome
	uint32 ClodRolls = 0;
	/** LM3c follow-up: add Cm of lump to a cell up to LumpMaxCm and return what is over it, cm, without placing it (the caller spreads it over its band). */
	float AddLumpCapped(int32 Index, float Cm)
	{
		float& Lump = LumpCm[Index];
		Lump += Cm;
		const float Over = Lump - LumpMaxCm;
		if (Over > 0.f)
		{
			Lump = LumpMaxCm;
			return Over;
		}
		return 0.f;
	}
	/** LM4 item 2: re-level each listed plate (site) to its tilted plane, keeping its volume; returns what the 0..LumpMaxCm clamp could not hold (cm^3, taken off the plate) and widens the written cells' box. */
	double ReshapePlates(TArrayView<const int32> Sites, int32& InOutX0, int32& InOutY0, int32& InOutX1, int32& InOutY1);
	/** LM4 item 3: the floor chunks already queued, by wall segment key (one per segment). */
	TSet<uint64> FloorChunkKeys;
	// LM4c: the static per-cell arrays (the wall repose's talus in cm per cell, the pile factor), built for the numbers in force.
	TArray<float> WallTalusCm;
	float WallTalusMinCm = 0.f;   // LM4e cut 3: the smallest of WallTalusCm
	TArray<float> PileFactor;
	static constexpr int32 PileKeyCount = 18;
	double PileKeyVals[PileKeyCount] = {};
	bool bPileKeySet = false;
	TMap<uint64, int32> CollapseIndex;   // segment key -> CollapseSegs index
	void EnsureSnowPiles();
	/** LM4d item 3: the lump sites that have taken spill (a site's first spill rolls for a clump). */
	TSet<int32> SpillSites;
	struct FBehindCell
	{
		int32 Index = 0;
		float Along = 0.f;   // along the box's forward from its centre, cm (behind it: under -HalfL)
	};
	/**
	 * LM4d items 2 and 3: the ridges and the spill on the cells behind the box; returns the volume put in the channel (cm^3), at most
	 * Return. The channel: cells the belly scraped that no tyre has covered, between the innermost tyre-covered cells under the box
	 * on either side (InnerNeg..InnerPos across it, cm; the whole box with no tyre under it).
	 */
	double DepositChannel(TArrayView<const FBehindCell> Cells, const FVector2D& CentreCm, const FVector2D& Forward, float HalfL, float InnerNeg, float InnerPos,
		double Return, double& OutRidgeCm3);
	/** LM4c item 2: arm (or re-arm) the collapse segment at this foot for a stamp that just cut its wall. */
	void ArmCollapse(const FVector2D& FootCm, const FVector2D& LineDir, float Side, float FaceCm, float FloorCm);
	/** LM4c item 2: the due collapses (Settle, before a sub-step's sweep); returns how many fell. */
	int32 FireCollapses();
	/** LM4c item 2: one segment's collapse now; false when its wall had nothing to drop (the wall gone or re-cut). */
	bool Collapse(FCollapseSeg& Seg);
	/** LM2a: add Cm of lump to a cell; what is over LumpMaxCm goes to HeightCm there. Returns the overflow, cm. */
	float AddLump(int32 Index, float Cm)
	{
		float& Lump = LumpCm[Index];
		Lump += Cm;
		const float Over = Lump - LumpMaxCm;
		if (Over > 0.f)
		{
			Lump = LumpMaxCm;
			HeightCm[Index] += Over;
			return Over;
		}
		return 0.f;
	}
	// LM4f item 4: the static per-cell noises (CellNoise of the cell at a wavelength and salt), one slot per call site's noise.
	enum ENoiseSlot : int32 { NoiseWave, NoiseWaveLong, NoiseSide, NoiseSlump, NoisePocket, NoiseFloor, NoiseClump, NoiseClod, NoiseClodSize,
		NoiseTracksEdge, NoiseCluster, NoiseSlotCount };
	struct FNoiseCells
	{
		TArray<float> Values;
		float WavelengthCells = -1.f;
		int32 Salt = INT32_MIN;
		int32 Seed = INT32_MIN;
		int32 SX = 0;
		int32 SY = 0;
	};
	FNoiseCells NoiseCache[NoiseSlotCount];
	/** The slot's CellNoise(X, Y, WavelengthCells, Salt) per cell for the field's size and seed, built if missing or stale; null on an empty field. */
	const float* NoiseCells(int32 Slot, float WavelengthCells, int32 Salt);
	/** A cell's noise from its slot (Cells, the cell in the grid), else computed: the same value either way. */
	float NoiseAt(const float* Cells, int32 X, int32 Y, float WavelengthCells, int32 Salt) const
	{
		return (Cells && X >= 0 && Y >= 0 && X < SizeX && Y < SizeY) ? Cells[Y * SizeX + X] : CellNoise(X, Y, WavelengthCells, Salt);
	}
	/** LumpClusterWeight with the cluster noise read from its slot (Cells may be null). */
	float LumpClusterWeightFrom(const float* Cells, int32 X, int32 Y) const
	{
		if (!bLumpVariety || LumpClusterT < -1.5f)
		{
			return 1.f;
		}
		return FMath::Clamp((NoiseAt(Cells, X, Y, FMath::Max(1.f, LumpClusterCm / CellCm), 79) - LumpClusterT) / 0.5f, 0.f, 1.f);
	}
	/** PileFactorAt without its EnsureSnowPiles (the stamp ensures once). */
	float PileFactorReady(const FVector2D& XYCm) const
	{
		if (!PilesOn())
		{
			return 1.f;
		}
		const int32 Index = CellIndexAt(XYCm);
		return PileFactor.IsValidIndex(Index) ? PileFactor[Index] : 1.f;
	}
	// LM4f item 3: per tile, SettleClockS of the last write within FastSettleBandCm (WakeTiles), and this sub-step's pending-collapse mark.
	TArray<double> TileWriteS;
	TArray<uint8> TilePending;
	/** LM4f item 3: one tile's flux (and the tiles it woke) logged by the parallel sweep, added in the serial order after it. */
	struct FFluxLog
	{
		int32 From = 0;   // the cell the snow left (or, for a wake, its X)
		int32 To = 0;     // the cell it went to (or, for a wake, its Y)
		float Q = 0.f;    // the height moved; a wake when negative
		uint8 Flags = 0;  // bit 0 down (else right), bit 1 the pair's higher cell was J (the smear's sign)
	};
	TArray<TArray<FFluxLog>> SweepLogs;
	struct FTileBox
	{
		int32 X0 = INT32_MAX;
		int32 Y0 = INT32_MAX;
		int32 X1 = -1;
		int32 Y1 = -1;
	};
	TArray<FTileBox> ApplyBoxes;
	TArray<int32> SettleList;      // the tiles one sub-step works on (awake, then the ones its flux woke)
	TArray<uint8> TileFlux;        // LM4e cut 3: per tile, flux reached it this sub-step
	TArray<uint8> SettleInList;    // per tile, already in SettleList this sub-step
	double SettleAccumS = 0.0;
	/** A stamp wrote cells X0..X1, Y0..Y1 (inclusive): their tiles wake. */
	void WakeTiles(int32 X0, int32 Y0, int32 X1, int32 Y1);
	/** A stamp wrote this cell: its set timer restarts, and it is fresh when its surface moved over FreshMinCm (LM2a; 0.01 cm until then). */
	void TouchCell(int32 Index, float SurfaceBefore)
	{
		SetS[Index] = SetSeconds;
		if (FMath::Abs(SurfaceCm(Index) - SurfaceBefore) > FreshMinCm)
		{
			Fresh[Index] = 1.f;
			ChurnWater(Index, FMath::Min(SurfaceBefore, SurfaceCm(Index)));   // MR3: and the water standing there is churned
		}
	}
	void SettleStep(float Dt);
	// MR3: the turbidity's clock, its scratch (the mixed values, from the old) and its work list.
	double TurbidAccumS = 0.0;
	TArray<float> TurbidScratch;
	TArray<int32> TurbidList;
	TArray<float> TurbidListMax;
	TArray<FIntRect> TurbidListBox;
	void TurbidStep(float Dt);
	/** A wet cell of From's edge facing To at TurbidSleepBelow or more, across a wet cell of To (From and To are 4-neighbour tiles). */
	bool TurbidEdgeWakes(int32 FromTile, int32 ToTile) const;
};
