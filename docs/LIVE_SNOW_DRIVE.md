# Live snow driving strip (L_SnowDrive)

2026-10-05/06, living mud stages LM3a, LM3b and LM3c (docs/LIVING_MUD_PLAN.md LM3a, LM3b, LM3c; VEHICLE_BUILD_SYSTEM
sections 69, 70, 71). The snow sections of the terrain generator on a 140 m test strip, driven by the real car, with LM3b's look (the
God of War target: deep trenches, a crumbly lip, a packed floor holding the tread, fresh snow that glints in the sun and
reads soft and slightly blue in shade) and LM3b's feel, with LM3c's polish (the tread only in the tyres' paths and
broken, the belly's scrape streaks, a crumbly plough berm, white snow clods).

## Open and drive

Open `/Game/GrandTour/ArtTests/LiveSnowDrive/L_SnowDrive`, then Play. The route runs along +X for 140 m:

- 0-30 m: the firm road (the Dirt row; no patch).
- 30-110 m: a Snow section (`EGTRouteSectionKind::Snow`, 1.4x the road's width, the Snow layer across it). Its patch
  carries 35 cm of snow over the ground, tapering to nothing over 3 m in from the patch's box (so the snow meets the
  landscape at the edge).
- 70-80 m: a drift, 60 cm deep, blending from 35 cm over 2 m beyond each end (`FGTRouteSection::SnowDrifts`).
- 110-140 m: the road again.

The car starts at 5 m. Winch posts stand 8 m to the left of the line at 62 m and 92 m, outside the snow. Clear weather;
the refill runs only while the weather snows (precipitation below freezing), or with `gt.Snow.Refill 1`.

## What to feel (LM3b)

The tyres sit on the ground under the snow (Chaos has no snow collision) and cut it to their own bottom. In a snow
patch a tyre's own few centimetres of sinkage roll at the Dirt row's rate (0.06 of the load at full sinkage; the Snow
row's 0.12 counted the snow twice and still applies outside snow patches), and the uncut snow ahead of each tyre drags
(`SnowPlough` 0.78 x the snow ahead over the wheel's radius x the speed). The belly still ploughs the snow over its
underside into berms, but its drag in snow is off (`SnowBellyDrag` 0): with any of it the car fell into a crawl through
the drift. Down your own trench neither drags much.

At full throttle in low range with the diff lock (the check, 2026-10-06): pass 1 in fresh snow runs 10.4 km/h through
40-66 m and 8.4 km/h through 85-110 m (35 cm; 9.3 km/h over both), 5.6 km/h through the drift, and never stops; pass 2 in
its own trench runs 26-28 km/h, the drift 5.1x pass 1's. The drift is bistable in the trials: either 5.5-6.8 km/h or a
1.7-1.9 km/h crawl, nothing between (LM3a's numbers, and any belly drag tried, gave the crawl).

## What to look at (LM3b)

`M_GT_Snow` (the patch) and the landscape's apron, all procedural (no texture files):

- Fresh snow (where no tyre has been): albedo 0.85, a little blue where the surface turns from the sun, a soft grain from
  world-space noise at 2, 12 and 60 cm, roughness 0.7. The glint: 1 cm cells that catch the sun when a cell's facet lines
  up with the sun's half-vector; best seen looking toward the sun over untouched snow (the sun stands to +Y, low).
- The shade: a Substrate Slab with Wrap subsurface and a blue-heavy subsurface colour (0.55, 0.70, 0.90), fading out
  over the patch's 3 m taper.
- Packed snow (the tyres' floors): albedo 0.72, greyer-blue, roughness 0.45, a smoother grain, and the tyre's tread lugs
  at up to 30 degrees (`LugTiltDeg`; the mud keeps 0). LM3c: the lugs only where a tyre's tread is set (not across the
  belly's channel), broken: each 12.5 cm cell's lugs at a strength of 0.25-1.0 from a 55 cm noise, a fifth of the cells
  with none, in patches.
- LM3c, where the belly scraped (the channel between the tyres): faint streaks along the direction of travel, 30-80 cm
  long and 2-4 cm across (`ScrapeLengthCm` 55, `ScrapeWidthCm` 3, `ScrapeSlope` 0.15, `ScrapeAlbedo` 0.03).
- LM3c, the plough's berm beside the trench: built like a tyre's bank (waves along it, clumps, the lump domes; nothing
  smooths it), its own lump share (`PloughLumpShare` 0.25) and a share of the bank's swings (`PloughBankVariation` 0.4);
  a lump's excess over its cap spreads back over the bank, so no single cell towers: about 17-18 cm over the snow top with
  swells up to 31-32 cm on the strip (the LM3c first cut reached 59).
- Walls (by the field's slope): a shade darker blue-grey, roughness 0.55.
- The border: the strip's landscape takes the same fresh-snow response at the patch box's edge, fading to grass over
  3 m outside it.
- The snow clods (`M_GT_Clod_Snow`) along the lip and from the throw; the throw itself is white (the spray's Snow kind).
  LM3c: albedo 0.82 on the snow's own Substrate Slab (Wrap subsurface), so their shaded side takes the snow's soft blue
  light; in the sun they read within 10 % of the snow round them (the check's measure).

Every number is a material parameter on `M_GT_Snow` (and the fresh ones on `M_SnowLandscape` too): `SnowFreshAlbedo`,
`SnowShadeTint`, `SnowNoiseCm`, `SnowNoiseSlope`, `SnowRoughVary`, `SnowAlbedoVary`, `GlintCellCm`, `GlintSpread`,
`GlintAngleDeg`, `GlintRough`, `GlintDensity`, `SnowPackedAlbedo`, `SnowPackedTint`, `SnowPackedRough`, `SnowPackedNoise`,
`SnowWallAlbedo`, `SnowWallTint`, `SnowWallRough`, `SnowWallNoise`, `SnowWallSlopeMin/Max`, `SnowSubsurfaceColor`,
`SnowSSS` (0 turns the subsurface off), `SnowSSSWrap`, `SnowF0`, `SnowEdgeCm`, `LugTiltDeg`, and LM3c's `ScrapeLengthCm`,
`ScrapeWidthCm`, `ScrapeSlope`, `ScrapeAlbedo`. They are proposed; the owner names them at the gate.

LM4 (docs/LIVING_MUD_PLAN.md LM4, God of War snow deformation), what to look at on the strip:
- **The grid**: the snow patch's field and mesh are at 6.25 cm (the mud's stay at 12.5); `gt.Snow.FineGrid 0` (then
  restart Play) builds it at 12.5 for comparison.
- **The lip**: crust plates, 12-30 cm Voronoi cells of the lump sites (half of them absent, in patches), each a flat slab
  tilted 5-25 degrees toward its own direction, with sharp steps to the next; about 15 % of the wall's segments have
  dropped their plate into the trench (a notch in the lip, a shard on the floor beside it).
- **The wall's outline** steps in and out by 3, 5.5 or 8 cm over 15-30 cm segments (the tyre's own width always cut to the
  floor).
- **Shards** (`SM_GT_SnowChunk_0..7`, `M_GT_Clod_Snow`) in place of the clods: at the plates' edges along the lip, on the
  trench floor where a plate fell, and from the throw.
- **The surface**: granular clumps of 1.5 and 6 cm with darker gaps on fresh and packed snow, faceted walls and plates,
  the shade toward a neutral grey-blue.
- **The snow top** undulates (sd 2.5 cm at 0.6-3 m), so the trench's depth varies along it; its floor varies about +-1.5 cm.

LM4's dials on `M_GT_Snow` (the fresh ones on `M_SnowLandscape` too): **`SnowShadeSaturation`** (0.5: half LM3b's
saturation on `SnowShadeTint`, `SnowPackedTint`, `SnowWallTint` and `SnowSubsurfaceColor`; 1 is LM3b's; the owner names
it), `SnowClumpCm` (1.5, 6), `SnowClumpSlope` (0.18, 0.25), `SnowClumpEdge` 0.22, `SnowClumpGapDark` 0.07,
`SnowPackedClump` 0.6, `SnowFacetCm` 4, `SnowFacetTilt` 0.2, `SnowFacetAlbedo` 0.04, `SnowPlateAlbedo` 0.76, and
`SnowWallNoise` 0.3 (LM3b 0.6). The field's (`FGTDeformProfile::SnowDefaults()`): `CellCm` 6.25, `PlateTiltMinDeg`/`MaxDeg`
5 / 25, `WallStepMinCm`/`MaxCm` 3 / 8, `WallSegMinCm`/`MaxCm` 15 / 30, `WallDropShare` 0.15, `FloorChunkChance` 0.18,
`SnowTopUndulationCm` 2.5, `FloorNoiseCm` 1.5, `ClodBankPerCm` 0.017 (per 12.5 cm cell's area), the shards' sizes 4-25 cm
(u^3), and `RidgeSmooth` 0 (not a plan number: stage H's smoothing broke the compaction on the stepped lip). The patch's
shard placement: `ShardYawSpreadDeg` 30, `ShardTiltMinDeg`/`MaxDeg` 10 / 40, `ShardSinkMin`/`Max` 0.2 / 0.5,
`ShardScaleJitter` 0.15.

LM4b (docs/LIVING_MUD_PLAN.md LM4b, the owner's "the snow is a bit blocky"), what to look at on the strip: the shape is
soft and irregular now and the crumbly detail is in the surface, as God of War's is.
- **The wall's outline** wanders smoothly (two noise octaves at 25 and 70 cm, +-3 cm), no steps or square notches.
- **The lip and the berm** carry soft domes, 5-12 cm in radius, leaning a little (2-10 degrees), at most 0.3 of their radius
  high, half the spots empty in patches; where a segment's lumps fell into the trench the notch's ends fade over 12.5 cm.
- **Clumps** in place of LM4's shards: eight rounded, lumpy snow clumps, 5-18 cm across (`SM_GT_SnowChunk_0..7`, the same
  names), along the domes' edges and on the trench floor where a lip's lumps fell.
- **The surface detail**: the snow-clump height map `T_GT_SnowDetail` (R crumbs 1-4 cm, G clods 6-15 cm), tri-planar in world
  space at two tilings. Fresh snow: faint crumbs and a little darkening in their crevices (LM4's crisp cells with dark gaps
  are gone). Edges, walls, the lip and the berm (the edge mask E): crumbs and clods at full strength with their crevices
  darker. The packed floor: smoother, with the tread as LM3c left it.
- **Parallax** (an experiment, off by default): with `gt.Snow.Parallax 1` the detail on the edges (E over 0.2) is drawn with
  parallax occlusion, 2.5 cm deep. Look at the walls and the lip close up with it on and off: does it read deeper, does it
  swim as you move, is it wrong on the walls.

LM4b's dials on `M_GT_Snow` (the fresh ones on `M_SnowLandscape` too; proposed, the owner names them): `SnowDetailTileCm`
(100, 113 cm: the map's two tilings), `SnowDetailCm` (0.8, 2.0: the crumbs' and the clods' height in cm at full strength),
`SnowDetailFresh` 0.35, `SnowCavityFresh` 0.05, `SnowCellGrain` 0 (1 brings LM4's cellular grain back), and on `M_GT_Snow`
only `SnowDetailPacked` 0.2, `SnowCavityPacked` 0.04, `SnowCavityEdge` 0.3, `SnowEdgeSlope` (0.35, 1.2 cm/cm: the edge mask's
slope ramp), `SnowEdgeLipCm` 2 (the lip band's height over the snow top), `SnowParallax` 0, `SnowParallaxCm` 2.5,
`SnowParallaxSteps` 10, `SnowParallaxNearCm` 1.2 (no parallax where a pixel spans more), `SnowEdgeDebug` 1 (draws E red,
the parallax's reach green). `SnowShadeSaturation` stays 0.5. LM4's `SnowFacet*` and `SnowPlateAlbedo` are gone. The field's
(`FGTDeformProfile::SnowDefaults()`): `WallStepMaxCm` 0, `WallWaveAmpCm` 1.0 at `WallWaveCm` 25, `WallWaveLongAmpCm` 2.0 at
`WallWaveLongCm` 70, `bLumpPlates` false, `bLumpSoftDomes` true, `LumpRadiusCells` 1.36 (8.5 cm), `LumpVarietyRadiusJitter`
0.41, `LumpSkewMinDeg`/`MaxDeg` 2 / 10, `LumpHeightPerRadius` 0.30, `LumpCapAmpPower`/`LumpCapRadiusPower` 0,
`WallDropFeatherCells` 2, `ClodBankPerCm` 0.031.

LM4c (docs/LIVING_MUD_PLAN.md LM4c, the owner's "those tall edges need to fall down into piles"), what to look at on the
strip, standing and after a pass:
- **The berm in piles**: separate piles 1-2.5 m apart with low gaps, not a continuous bank; about 10-11 cm over the snow top
  at the median and 16 cm at the 90th percentile in the test (LM4b 19 / 29), sloping back from the trench's edge.
- **Loose snow slumps**: the berm and the lip settle to 50 degrees, so the edge no longer stands as a cliff with the berm on
  top of it; some of it runs down into the trench.
- **The cut wall stands in places and eases in others**: each 40-80 cm stretch of wall has its own angle, 44-84 degrees.
- **Wall collapses after the car**: a fifth of the wall's 30-80 cm segments drop their top 30-60 % 0.5-3 s after the last tyre
  cut them, as a pile on the trench floor at the wall's foot (up to about 12 litres, 11 cm high in the test) with one or two
  clumps on it, leaving a notch with soft ends. Watch the trench behind the car, and walk the wall after a pass.
- **The trench floor** carries some fallen snow (in the test, 29 % of the floor's middle raised 2 cm or more); it is what the
  tyres plough on the second pass.

LM4c's numbers (`FGTDeformProfile::SnowDefaults()`; the plan's starting points in brackets, landed on the field tests):
`bCellRepose` true, `LooseReposeDeg` 50 (35), `WallReposeDeg` 64 (60) +- `WallReposeRangeDeg` 20 at
`WallReposeWaveMinCm`/`MaxCm` 40 / 80; `CollapseChance` 0.2 (0.25), `CollapseSegMinCm`/`MaxCm` 30 / 80,
`CollapseDelayMinS`/`MaxS` 0.5 / 3, `CollapseTopMin`/`Max` 0.3 / 0.6, `CollapseFeatherCells` 2, `CollapseClumpsMin`/`Max` 1 / 2;
`PloughBandCm` 85 (70), `bPloughFallingProfile` true, `PileClusterMin` 0.08 (0.2), `PileClusterMax` 1.8, `PileWaveMinCm`/`MaxCm`
100 / 250. The field's own (not plan numbers): `PloughFallPower` 0.5 (the berm's weight (1 - u)^0.5 from the wall out),
`PileContrast` 1 (the ranked cluster noise mapped by smoothstep: piles and gaps), `CollapseArmMinCm` 1 and `CollapseArmOut`
0.6 (what re-arms a segment's timer).

LM4d (docs/LIVING_MUD_PLAN.md LM4d, the owner's "the middle is still very perfectly flat"), what to look at in the belly's
channel between the trenches:
- **The scrape undulates**: the channel's floor rises and falls by up to 2.5 cm in long, shallow waves (20 and 60 cm across,
  2.5x longer along the trench), instead of one level plane.
- **Smear ridges**: low ridges along the travel, 30-80 cm long, 8-15 cm wide, 1-3 cm high, bunched, about three a metre.
- **Spill**: soft lumps and the odd snow clump fallen back into the channel from the plough's berms, bunched.
- **The surface**: the crumbs and clods detail at mid strength over the channel, and stronger scrape streaks.

LM4d's numbers (`FGTDeformProfile::SnowDefaults()`): `BellyUndulationCm` 2.5, `BellyWaveMinCm`/`MaxCm` 20 / 60, `BellyStretch`
2.5; `SmearChance` 0.25, `SmearLaneCm` 20, `SmearLengthMinCm`/`MaxCm` 30 / 80, `SmearWidthMinCm`/`MaxCm` 8 / 15,
`SmearHeightMinCm`/`MaxCm` 1 / 3, `SmearClusterCm` 120; `PloughSpillShare` 0.15, `SpillClumpChance` 0.15. On `M_GT_Snow`:
`BellyDetail` 0.35 (the edge mask's floor in the channel), `ScrapeSlope` 0.3, `ScrapeAlbedo` 0.06 (LM3c 0.15 / 0.03). The field's own
(not plan numbers): `ChannelBandCm` 25, `SpillBackCm` 30 (where behind the belly the ridges and the spill land).

## Console switches

- `gt.Mud.Settle 0/1`: the field's settling (snow, LM4c: the talus per cell - loose snow at 50 degrees, the wall at 44-84 -
  and the delayed wall collapses; 0 stops both, and the walls stand as cut).
- `gt.Mud.Clods 0/1`: the snow clods along the lip and from the throw.
- `gt.Snow.Refill -1/0/1`: refill while the weather snows (default), never, always (2 cm a minute toward the snow top).
- `gt.Snow.Plough <k>` and `gt.Snow.BellyDrag <s>`: at 0 or more they replace the patch's `SnowPlough` and
  `SnowBellyDrag` (the check's trials use them); -1, the default, uses the patch's own (0.78 and 0 from
  `FGTDeformProfile::SnowDefaults()`).
- `gt.Snow.FineGrid 1/0` (LM4): 1, the default, builds a snow patch at its profile's `CellCm` (6.25 cm); 0 at 12.5 cm with
  every cell-unit number rescaled to keep its size in cm. Read when the patches are built: restart Play after changing it.
- `gt.Snow.Parallax -1/0/1` (LM4b): 1 draws the snow detail with parallax occlusion where the edge mask is over 0.2, 0
  without, -1 (the default) the material's own `SnowParallax` (0). Takes effect at once.
- LM4e, the cost cuts (docs/LIVING_MUD_PLAN.md LM4e, VEHICLE_BUILD_SYSTEM section 76); each on by default, 0 is the old path:
  - `gt.Snow.QuietSleep 1/0`: snow keeps no fresh sheen (M_GT_Snow draws none), so a settled tile sleeps after 0.5 s instead
    of after the sheen's 6 s fade, and no cell is re-uploaded for a fading sheen. At once.
  - `gt.Snow.FastSweep 1/0`: Settle passes over the pairs under the smallest talus first (four cells at a time), skips a tile
    no snow moved into, and keeps no smear on snow (not drawn). Exact. At once.
  - `gt.Snow.UploadTiles 1/0`: the upload sends one box per 2 m settle tile that changed, not one box round all of them. At once.
  - `gt.Snow.MeshLod 1/0`: the snow mesh in 8 m chunks, 6.25 cm within 20 m of the camera, 12.5 cm within 40 m, 25 cm beyond,
    skirts under the chunk edges. Read when the patches are built: restart Play after changing it.
  - `gt.Snow.FastMaterial -1/0/1/2`: M_GT_Snow computes the belly's scrape streaks only where they show (1), everywhere (0);
    -1, the default, the material's own `SnowFastPath` (2 since LM4f, below). At once.
  - M_GT_Snow is opaque now (its mask was 1 everywhere); `/Game/GrandTour/Materials/MI_GT_Snow_Masked` is the masked one, for
    an A/B by hand (no console switch: a blend mode).
- LM4f, the bigger cuts (docs/LIVING_MUD_PLAN.md LM4f, VEHICLE_BUILD_SYSTEM section 77); each on by default and each able to change
  the look or the settle, so the owner A/B's look and cost together and names which stay:
  - `gt.Snow.ShadowProxy 1/0`: 1 the snow chunks cast no shadow and a hidden 25 cm mesh per chunk (the same material, so the same
    displacement every frame) casts it instead; 0 the chunks cast their own (LM4e). Needs `gt.Snow.MeshLod 1`. At once.
  - `gt.Snow.FastMaterial 2` (the material's default now): level 1 and the detail map read top-down only where the surface is under
    30 deg (tri-planar only on walls), only where the edge mask E is over 0.05 (fading in to 0.10), with one tiling where E is under
    0.2 (the second fading in to 0.3); the glint fading out over 12-20 m and the subsurface over 20-35 m. 1 is LM4e's, 0 the full
    material. At once.
  - `gt.Snow.FastSettle 1/0/2/3/4`: 1 the snow's talus at 15 Hz (sub-steps of 1/15 s moving twice as far), only the tiles within 2 m
    of a write (a stamp, the plough, a landing, a collapse) in the last 3 s or by a pending collapse stay awake, and the sweep and the
    apply run over the tiles in parallel (summed in the serial order: the same numbers run to run); 2 the parallel part alone (exact,
    a check); 3 the parallel part and 15 Hz without the band; 4 the parallel part and the band at 30 Hz (each half of 1 on its own);
    0 LM4e's settle. At once (the CPU tests read it too: a new field takes it as its default).
  - No switch: the stamps read their static per-cell noises from arrays built when the patch starts (exactly the values they
    hashed per cell before; every test row identical).

## How to test the optimisation (LM4e, LM4f)

Play L_SnowDrive, drive pass 1 in fresh snow (or stand on foot at the trench), and compare each switch on and off:

- `stat unit` (Frame, Game, Draw, GPU, RHIT) and `stat gpu` (BasePass, ShadowDepths, Lights, Lumen, Translucency,
  PostProcessing, Velocity);
- `stat game`: GT Mud Settle, GT Mud Upload, GT Mud Clods (ms), GT Mud Stamp ms (the wheels' stamps and the plough), GT Mud
  Swept Tiles, GT Mud Upload Cells, GT Snow Drawn Triangles;
- the switches, each with its default: `gt.Snow.QuietSleep 1`, `gt.Snow.FastSweep 1`, `gt.Snow.UploadTiles 1`,
  `gt.Snow.MeshLod 1` (restart Play after changing it), `gt.Snow.FastMaterial -1` (the material's 1); set one to 0 to see its cost;
- the older ones for the whole feature: `gt.Mud.Settle 0`, `gt.Mud.Clods 0`, `gt.Snow.FineGrid 0` (restart Play);
- the targets: Settle mean at most 0.3 ms and p99 0.7 on pass 1, the upload mean at most 0.2 ms, the snow patch's GPU at most the
  clay patch's + 1 ms at a matching view, pass 1's frame at most the mud strip's dry crossing + 2 ms.
- LM4f's switches (each on by default; no timing ran in LM4f, so every saving below is **estimated** from LM4e's before profile:
  the patch hidden on foot -7.8 ms GPU, of it shadow depths -3.4, base -1.4, lighting -1.2; its shadow casting off -2.2 on foot /
  -1.1 in the cost view; MeshLod -0.75 of the shadow depths; M_GT_Mud on the snow patch -1.5 / -3.4; pass 1 after LM4e's cuts
  Settle 0.381 / 1.735 ms mean / p99, stamps 0.864 / 1.854). Look at each one's picture as well as its cost, and name which stay:

  | Switch (default) | 0 gives | What it trades (look risk) | Saving (estimated) |
  |---|---|---|---|
  | `gt.Snow.ShadowProxy 1` | LM4e: the chunks cast | The snow's shadow on itself comes from a 25 cm surface: the trench walls' and the lip's shadow edges move by up to about 12 cm, a dip narrower than 25 cm can fall in shadow where the coarse caster bridges it, the small lumps lose their own little shadows. Medium | about 1.3-2.4 ms GPU on foot (most of the 3.4 ms shadow depths less MeshLod's 0.75: the shadow passes draw about 37k triangles, 1/16 of the 592k at 6.25 cm, instead of LOD 0 near the camera); less in the cost view, whose far chunks were LOD 2 already |
  | `gt.Snow.FastMaterial 2` (`-1`, the material's default) | 1: LM4e's material (0: the full one) | The crumbs and clods go wherever E is 0.05 or under: the untouched fresh snow and the packed floors lose their faint crumbs (the landscape's apron keeps them, so the patch's edge can show), slopes of 18-30 deg take a top-down stretch instead of the tri-planar blend, the detail's tiling changes over E 0.2-0.3, no glints past 20 m (fading from 12), no soft blue subsurface past 35 m (fading from 20). High on fresh snow | about 0.3-1.0 ms GPU of the material's 1.5 (on foot) / 3.4 (cost view) over the clay's; the before profile's detail, glint and SSS toggles alone were within its noise, so the low end is as likely |
  | `gt.Snow.FastSettle 1` | LM4e's settle (2: its parallel half alone, exact) | The talus moves as fast per second in steps twice as big, and a collapse falls up to 1/15 s later; snow more than 2 m from anything written in the last 3 s stops settling where it stands (a pile still slumping then stays a little taller and steeper). With it on GrandTour.Snow.Piles fails one row: 62.3 % of the outer walls' cells stay steeper than 55 deg (asked 15-60; LM4e 57.2) - the band's doing (4 alone: 62.7 %); 3 (15 Hz alone) keeps that row but tips the berm crest cv (0.361 / 0.350) just under its 0.35 on one side, where LM4e passed by a hair at 0.362 / 0.350. Every moved row is in docs/LIVING_MUD_PLAN.md's LM4f note. Low-medium; the feel only where the car meets such a pile | Settle mean about 0.05-0.15 ms, p99 about 0.3-0.7 ms on pass 1 (from 0.381 / 1.735): half the sub-steps, fewer tiles awake (LM4e saw 93-132 awake; the band round the last 3 s of a 10 km/h car is a few tens), the rest across the cores |
  | (no switch) the stamps' static noises from arrays | - | None: exact (every shape-test row identical with FastSettle 0) | about 0.1-0.3 ms of the stamps' 0.86 ms mean on pass 1 (some 500-800 lattice noises a stamp - the station's 4 at every change of foot cell, one to three a row of the stamp's box, 2 per floor cell, 3-4 per lip cell - each 4 integer hashes and a smoothstep blend, and an 18-number key compare per lip cell for the piles: now array reads) |

  The order to try: on foot at the trench, `gt.Snow.ShadowProxy 0` then `1` (the shadows along the trench walls and the lip), then
  `gt.Snow.FastMaterial 1` then `-1` (the fresh snow beside the trench and the patch's edge against the apron, near and at 20-35 m);
  then drive pass 1 with `gt.Snow.FastSettle 0` and `1` (`stat game`: GT Mud Settle; look at the piles behind the car after 3 s).

## Rebuild and checks

From `C:\GrandTour`, with every game (GoWR, GoW, FarCry6) and Unreal closed:

```powershell
& 'C:/Program Files/Git/bin/bash.exe' Art/build.sh
python Art/tools/bake_snow_detail.py
& Art/import_snow_detail.ps1
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup --python-exit-code 1 --python Art/Blender/build_snow_chunks.py
& Art/import_snow_chunks.ps1
& Art/setup_live_snow_drive.ps1
& Art/check_live_snow_drive.ps1
```

LM4: the snow shards come from `Art/Blender/build_snow_chunks.py` (headless; `Art/Export/SnowChunks`) and
`Art/import_snow_chunks.ps1` (`/Game/GrandTour/Mud/SnowChunks`); without them a snow patch draws the clods, with a warning.

`setup_live_snow_drive.ps1` runs `Art/Unreal/setup_live_snow_drive.py`: the snow materials (`live_snow_style.py`:
`M_GT_Snow`, a fresh copy of the live `M_GT_Mud` graph with the LM3b surface and the Slab, and `M_GT_Clod_Snow`), the spec
`DA_SnowDrive`, the strip's landscape material `M_SnowLandscape` (M_GT_Landscape with a flat white Snow row, no OW grass,
and the LM3b snow apron) and the level. It prints the subsurface routes, the materials' instruction counts, LM3c's
Substrate compile output per material (its type and lighting tile, its BSDF features), and fails on any shader error the
log names after the materials are built. Rerun it after a live mud setup changes `M_GT_Mud`.

`check_live_snow_drive.ps1` runs `Art/Unreal/check_live_snow_drive.py` in Play In Editor (a 1440x900 window, the
editor's background throttle off), at full throttle in low range with the diff lock:

1. LM3c: no trials (`TRIALS = False` in the script; LM3b's trials and fit stay behind the switch: each a pass 1 on a
   reset field to 111 m, LM3a's numbers for reference, the patch's own, then up to five chosen by a fit until A and B
   read 8-15 km/h, the drift 3-6 km/h, and no stop over 1 s).
2. Two passes at the landed numbers: completion, lateral deviation, the segment speeds, the longest stop, the drift's
   mean speed (the gate: pass 2 at least 1.15x pass 1), the plough volume, the drag terms (`snow_samples.csv`), the
   spray's throw by kind, the cost of Settle and the clods, the trench profiles (`snow_profile.csv`), LM3c's berm crest
   along 40-66 m (the highest cell 95-185 cm off the line per column: its mean and coefficient of variation per side).
3. Pictures: `Snow_Long.png`, `Snow_Cockpit.png`, `Snow_Trench_Close.png`; `Snow_Glint.png` and `Snow_Glint_NoGlint.png`
   (the same frame, `GlintDensity` 0) with the count of pixels over 245 in a sunlit fresh-snow box; `Snow_Border.png`
   with `Snow_Border_NoSSS.png` and `Snow_Border_NoSSS_F004.png` (diagnostics) and the border counts on
   `Art/tools/sample_border.ps1`'s pattern (dark and sky-coloured pixels along the edge, the strips 1.5 m either side, and
   20 cm strips 10 cm either side of the edge); `Snow_Cost_Snow/Clay/Nosss.png`, what the cost profiles see. LM3c:
   `Snow_Trench_Close_NoClods.png` (the same frame with the clods hidden) and the clods' screen boxes, for the clods'
   luminance against the snow round them (sunlit and shaded); `Snow_Floor_Close.png`, down into the -Y tyre's floor beside
   the belly's channel at 50 m; `Snow_Classify_Snow/Clay/Nosss.png`, Substrate's lighting tiles (`r.Substrate.ViewMode 4`:
   green Simple, yellow Single) and a ProfileGPU dump per material in the log.
4. The cost: the patch wears M_GT_Snow, a M_GT_Mud instance with the same field parameters, or M_GT_Snow with `SnowSSS`
   0, 5 s CSV profiles each from one camera over the snow at 50 m in the order snow, clay, no-SSS, no-SSS, clay, snow;
   GPU/Basepass, Prepass, ShadowDepths and the whole GPU, and every pass that differs by 0.03 ms or more.

5. LM4: the trench profiles and the berm read the patch's own cell. `Snow_GoW_View.png` (the God of War reference's view:
   2.5 m up, 2 m behind and 0.75 m to the left of the +Y tyre's track at 50 m, about 35 degrees down along it) and
   `Snow_OnFoot.png` (eye level, 1.65 m over the -Y tyre's trench floor at 46 m, looking along it) after
   `Snow_Floor_Close.png`. Each pass reports the shards (lip, floor, throw) and the lip plates that fell in. After the main
   session the FineGrid pair: `gt.Snow.FineGrid 0` and then 1, each time the patches rebuilt
   (`UGTMudSubsystem::RebuildPatchesForTest`), passes 1 and 2 again (Settle and upload p99, the CSV game thread and GPU)
   and two 5 s profiles from the cost camera; the mesh's cells, vertices and triangles per session.
6. LM4c: the berm's crest read 95-250 cm off the line (the 85 cm band); each pass reports the collapses (fired, volume,
   segments armed, clumps). After `Snow_Edge_Mask.png`, the collapse pair: `UGTMudSubsystem::CutSnowTrenchForTest` stamps a
   single tyre's cut (28 cm, 5 cm sinkage, 5 cm strokes) on untouched snow 2.9 m to the +Y side of the line from 90 to 99 m
   at once; the camera stands across that trench from the collapsing segment nearest 94.5 m, 70 cm up; `Snow_Collapse_0s.png`
   0.2 s after the cut and `Snow_Collapse_4s.png` 4 s after it (every delay is 0.5-3 s), with the segments armed and the
   collapses that fell between them in the report.
7. LM4d: `Snow_Channel_Close.png` after `Snow_Floor_Close.png` - low along the belly's channel at 50-53 m, 60 cm over its
   floor; each pass reports the smear ridges' and the spill's volume and the channel's clumps.

Everything goes to `Art/Export/LiveSnowDrive`; the wrapper judges by a fresh `ok: true` report. The PIE viewport is
1440x868, so the wrapper moves the projected boxes 16 px down onto the 1440x900 pictures.

## Results, LM4e (2026-10-06): the snow's cost, measured until the owner stopped timing runs

`Art/profile_live_snow.ps1 -Tag <name>` (`Art/Unreal/profile_live_snow.py`) and `Art/profile_live_mud.ps1` are the profiles
(the plan's LM4e note has every number). Measured, ABBA, with Blender running through parts of both runs:

| | Before | After cuts 1-5 | Target |
|---|---|---|---|
| Settle on pass 1, mean / p99 ms | 1.94 / 8.57 (the cleanest base run 0.88 / 3.24) | 0.381 / 1.735 | 0.3 / 0.7 |
| upload on pass 1, mean ms | 1.70 (64,688 cells a frame) | 0.370 (13,045) | 0.2 |
| the pass-1 record replayed: Settle / upload mean ms (cuts off -> on, same session) | 1.38 / 1.52 | 0.84 / 0.53 | |
| the snow patch hidden, GPU ms (on foot / cost view) | -7.8 / -10.1 | -6.6 / -7.7 | clay's (cost-view offsets) 3.69 + 1 |
| pass 1 frame / game / GPU ms | 39.0 / 36.7 / 24.5 (cleanest base 22.9 / 20.9 / 20.1) | 19.6 / 15.5 / 16.6 | the mud strip's dry crossing 18.76 + 2 |

Per cut (replay or standing, in-session): QuietSleep -0.28 ms Settle and -0.21 upload; FastSweep -0.39 Settle; UploadTiles
-0.61 upload; MeshLod -1.29 ms GPU on foot. Unmeasured: the four-at-a-time sweep and the tile skip, the row encoder, the opaque
material (inconclusive), the material fast path. Pictures: below the sky the after frames differ from the before ones by
0.28-0.44 of 255 (0.08-1.14 % of pixels over 8); the chunk seams add no dark or sky pixels.

## Results, LM4d (2026-10-06, no game, no other Unreal): the first check since LM3c

It carries LM4, LM4b, LM4c and LM4d, so it is their owed check too (docs/LIVING_MUD_PLAN.md's LM4d note has every line).
- **Feel**: pass 1 at 6.25 cm reached the end with no stop: A 11.2 km/h, B 3.7, the 35 cm outside the drift **5.6 (asked
  8-15: FAIL)**, the drift 5.5 (3-6); pass 2 the drift 23.8 km/h, **4.31x pass 1 (PASS)**. With `gt.Snow.FineGrid 0` (12.5 cm)
  pass 1 reads A 10.1, B 7.8, outside the drift 8.8, the drift 5.4. Nothing retuned.
- **Cost**: Settle at 6.25 cm, pass 1 mean 1.51 / p99 5.67 ms (gate 0.3 / 0.7: FAIL), awake peak 93-132 tiles; at 12.5 cm 0.40 /
  1.46; the pass's frame 35.6 ms (game thread 34.9). LM4b's parallax: the strip view base pass +0.11 ms, GPU +0.75 (the edge view
  -1.07: noise).
- **The strip**: the berm's crest after pass 1 at 40-66 m, -Y median 10.4 cm (90th 14.6, highest 20.5), +Y 9.2 (14.7, 22.3);
  the walls at 50 m 56.8 and 77.1 deg; 171 collapses on pass 1; the channel's ridges 111,936 cm^3 and spill 853,455 cm^3, 105
  clumps.
- **Pictures** (descriptions in the plan's note; the owner judges): `Snow_OnFoot.png`, `Snow_Channel_Close.png`,
  `Snow_GoW_View.png` and `Snow_Edge_Close.png` (each GoW/OnFoot/Edge with `_Parallax1`), `Snow_Edge_Mask.png`,
  `Snow_Collapse_0s.png` / `Snow_Collapse_4s.png` (8 collapses fell between them), and the LM3 set.

## Results, LM4c (2026-10-06): the check was OWED (it ran with LM4d, above)

God of War Ragnarok ran through the stage, so the drive check has not run: the feel gates (pass 2 now ploughs the snow that
fell into the trench), `Snow_OnFoot.png`, `Snow_GoW_View.png`, `Snow_Edge_Close.png` (each with `_Parallax1`),
`Snow_Edge_Mask.png`, the collapse pair `Snow_Collapse_0s.png` / `Snow_Collapse_4s.png`, the LM3 set, and the Settle,
FineGrid 1 / 0 and Parallax 1 / 0 cost (LM4 and LM4b's owed items with them). The strip's setup ran (LIVE_SNOW_SETUP_OK,
M_GT_Snow 1,641 pixel instructions, no compile error) and so did the field tests (docs/LIVING_MUD_PLAN.md's LM4c note: 8 of
8 GrandTour.Mud + GrandTour.Snow Success; GrandTour.Snow.Piles new).

## Results, LM4b (2026-10-06): the check is OWED

God of War Ragnarok ran from 14:25, so the drive check has not run: the feel gates, `Snow_GoW_View.png`, `Snow_OnFoot.png`
and `Snow_Edge_Close.png` (each with `_Parallax1`), `Snow_Edge_Mask.png`, the LM3 set, the strip's clump counts, and the
FineGrid 1 / 0 and Parallax 1 / 0 cost. The strip's setup ran (M_GT_Snow 1,641 pixel instructions, 4 samplers, no compile
error; the apron compiled), and so did the field tests (docs/LIVING_MUD_PLAN.md's LM4b note: 6 of 7 PASS, GoW's lip crest cv
row failing). LM4b's check adds, after `Snow_Floor_Close.png`: the GoW and on-foot views at `gt.Snow.Parallax 0` and then 1,
`Snow_Edge_Close.png` (60 cm out from the -Y trench's outer lip at 47 m, 30 cm over the snow, looking along it to 53 m) at 0
and 1, `Snow_Edge_Mask.png` (that frame with `SnowEdgeDebug` 1); after the material's cost, the parallax pair: 5 s profiles
from the cost camera (the strip view) and from the edge camera at 0, 1, 1, 0 each, then LM4's FineGrid pair.

## Results, LM4 (2026-10-06): the check is OWED

God of War Ragnarok ran through the stage, so the drive check (the feel gates, the pictures, the FineGrid cost) has not run; the strip's
setup ran (M_GT_Snow 1,542 pixel instructions, no compile error) and so did the field tests (GrandTour.Snow.GoW and
Compact: every row PASS; docs/LIVING_MUD_PLAN.md's LM4 note has the numbers).

## Results, LM3c (2026-10-06, the final check; no game, no other Unreal)

- Feel, the patch's own numbers (not retuned): pass 1 11.6 km/h through 40-66 m, 8.4 km/h through 85-110 m (9.8 over
  both), 5.5 km/h through the drift, never stopped; pass 2 5.21x through the drift.
- The berm's crest along 40-66 m (the LM3c follow-up): median 17-18 cm over the snow top, 90th percentile 25 cm, highest
  31-32 cm, cv 0.26 / 0.31 (the first LM3c cut: highest 56-59 cm). Feel after the follow-up: 9.6 km/h in the 35 cm, 5.5
  through the drift, 5.19x on pass 2.
- The clods: 16 sunlit at 0.916 of the snow round them (asked within 15 %), 12 in shade at 0.794.
- Cost: the GPU +0.60 ms with the snow material against the clay; RenderDeferredLighting +0.36 ms whether its pixels are
  Substrate's Single tiles (subsurface on) or Simple ones (subsurface off): the classification is not that cost.

## Results, LM3b (2026-10-06, its final check; no game, no other Unreal)

- Feel: as above. Trials of the tuning run: (0.35, 1.0) A 23.8 / B 1.7 / drift 1.8 km/h; (0.48, 0.65) 19.5 / 2.3 / 1.7;
  (1.073, 0) 6.9 / 2.0 / 1.7; (0.669, 0) 13.8 / 9.6 / 6.8; (0.741, 0.295) 10.1 / 1.7 / 1.9; (0.78, 0) 10.8 / 8.4 / 5.5
  landed. No trial stopped.
- Throw: pass 1 threw 2,362 blobs, all through the Snow kind; 254 thrown clods live at the end (M_GT_Clod_Snow).
- Glint: 846 of 191,912 pixels over 245 in the fresh-snow box (0 with the glint off).
- Border: 0 dark and 0 sky-coloured pixels in the border box; 10-30 cm either side of the edge +1.6 / +2.0 / +2.4 levels
  (R/G/B), the same with the patch's subsurface off.
- Cost: base pass 1.280 ms with the snow on the patch against 1.336 ms with the clay; the whole GPU +0.85 ms (deferred
  lighting +0.39 whether the subsurface is on or off, Lumen reflections +0.10, the subsurface's Lights and translucent
  lighting +0.25). Settle and the clods PASS their gates.
- Pictures (not judged; the look is the owner's): see docs/LIVING_MUD_PLAN.md LM3b for what each contains.
