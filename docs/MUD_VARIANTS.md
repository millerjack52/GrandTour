# Mud variants: four churned bogs per route section (living mud LM5b)

2026-10-06. The owner, after the A2 renders: "looks good, but the ruts should be the same color and texture as the rest. I
want a number of variants for deformable mud." So the mud is **one layer**: a patch wears its variant's churned-bog bakes
everywhere, ruts, ridges, banks and clods included, and a rut differs from untouched mud only by its shape, the fresh sheen
(a little wetter, drying off), the weather's wetness and the rut water. There are four variants, picked per Mud route
section. The plan is `docs/LIVING_MUD_PLAN.md` LM5b; the bakes are `docs/MUD_WET_STUDY.md` ("LM5b: the four variants").

## The four variants

| Variant (`EGTMudVariant`, slice) | Look (bake set `T_MS_Bog<V>*`) | Feel (`FGTDeformProfile::MudVariantDefaults`) | Soft spots (MR4 `SoftSpotAmplitude`) |
|---|---|---|---|
| `Standard` (0) | the approved A2 churn: dark glossy bog with brown rounded lumps (37.5 % lumps, mud roughness 0.22-0.38) | no profile: the bog exactly as before LM5b (the rows, RecoverShare 0.4, LumpShare 0.35, ThrowMax 0.5, the section's water table) | 1 (no profile: the full spread) |
| `Firm` (1) | lighter mid-brown, matte, small crowded lumps (50 %, median 5.5 cm), mud roughness 0.58-0.72 | sinkage x0.6 (cap and rate), RecoverShare 0.25, LumpShare 0.25, ThrowMax 0.3, friction x1.1 | 0.5 |
| `Deep` (2) | darker and wetter, broad glossy slurry (79 % open mud, roughness 0.15-0.28), fewer, softer lumps | sinkage x1.5, RecoverShare 0.55, LumpShare 0.35, ThrowMax 0.6, water table +10 cm, friction x0.9 | 0.6 |
| `Stony` (3) | the churn with gravel and small stones pressed in (gravel-04 palette with the earth coating) | sinkage x0.8, RecoverShare 0.3, LumpShare 0.2, (ThrowMax the bog's 0.5), friction x1.15 | 0.6 |

The feel numbers are **proposals** the owner names after driving. "Sinkage" scales the surface row's `MaxSinkage` and
`SinkageRate` for a wheel inside the patch (the Mud and the Bog rows alike); "friction" scales the friction of the row the
wheel stands on (through the traction's `FrictionScale`, which moves the Chaos friction circle, the slip graph and the drive
cap together, as a row with that much more `Friction` would). A variant's patch stays a bog's patch: the rows and their
Mud/Bog tag gate, the bog's grid and every other bog number; only the five numbers in the table change.

## Picking a variant

A Mud section's `MudVariant` (`FGTRouteSection`, default `Standard`):
- **In a DA_Terrain / spec asset:** open the asset, Spec > Sections > the Mud section > Mud Variant.
- **In a setup script:** `setprops(u.GTRouteSection(), start_m=30., end_m=55., kind=u.GTRouteSectionKind.MUD, mud_variant=u.GTMudVariant.FIRM)`.
- **The feel follows `Deform`:** on `ByKind` (the default) the section takes the variant's profile; `On` replaces the feel
  with the section's own full profile (RIVERBED S4's); `Off` keeps the rows unscaled. The look is the variant's slice in
  every case.
- Only Mud sections have variants; a ford's bed and a snow patch are `Standard` (their look is their own material).
- `MPC_TrackPaint` holds four patches: a level with more than four mud/ford/snow patches gets no hole or apron on the
  fifth (as before).

Every existing level (L_MudDrive, The Hide, the legs) is `Standard`, so its feel is unchanged and its mud now wears the
Standard bog everywhere in the patch.

## How it is built

- **Data** (`Source/GrandTour/Terrain/GTTerrainGenerator.h/.cpp`): `EGTMudVariant`; `FGTRouteSection::MudVariant`;
  `FGTDeformProfile`'s `bScalesRows`, `MaxSinkageScale`, `SinkageRateScale`, `FrictionScale`, `WaterTableOffsetCm`;
  `FGTDeformProfile::MudVariantDefaults(v)` (the table, RecoverShare/LumpShare/ThrowMax starting from `AGTMudPatch`'s
  defaults); `GTTerrain::MudVariantProfile(v)` and `DeformProfileFor` (a Mud section on ByKind gets its variant's
  profile, Standard none).
- **The patch** (`GTMudPatch.h/.cpp`): `ApplySection` (the water table, the variant, the profile, in that order; the
  subsystem's `BuildPatches` calls it); `ApplyProfile` with `bScalesRows` sets only the scales, the three shares and the
  water table's offset; `MudVariant` goes to the mesh's `M_GT_Mud` instance (`MudVariant`) and, off Standard, to a
  per-patch `M_GT_Clod` instance (`ClodMaterialInstance`), bank and thrown clods alike.
- **The traction** (`GTTractionComponent.cpp`): inside a patch, on the Mud or Bog row (or on a profiled patch), the
  sinkage cap and rate times the patch's scales, the wheel's `FrictionScale` times its friction scale. All 1 on Standard.
- **The landscape's border**: `UGTMudSubsystem` writes each patch's variant into `MPC_TrackPaint`'s `PatchVariant0..3`
  (scalars beside the `Patch0..3` boxes, whose four components are all used); the landscape's mud block takes the nearest
  live box's slice over a 3 m apron round it (the clay outside every apron, unchanged).
- **The textures**: four `Texture2DArray`s, `/Game/GrandTour/ArtTests/MudStyle/TA_MS_Bog{Color,Normal,Rough,Height}`,
  slice = variant, from the sixteen bake PNGs (`Art/Unreal/import_mud_variants.py`).
- **The material** (`Art/Unreal/live_mud_style.py`): see `docs/LIVE_MUD_DRIVE.md` "The one-layer mud".

## L_MudVariants: open, drive, rebuild

`/Game/GrandTour/ArtTests/MudVariants/L_MudVariants` (spec `DA_MudVariants`): one route along +X, 0-215 m, gravel between
four Mud sections of 25 m - **Firm 30-55 m, Standard 75-100 m, Deep 120-145 m, Stony 165-190 m** - with 20 m of gravel
between them (each patch's box reaches 6.8 m past its section, so the boxes stand 6.4 m apart and their 3 m aprons do not
meet) and no ford. The car starts at 5 m, before Firm. Winch posts stand 3 m past each section's end, 6.5 m to the right.
Open it and press Play; the patches, their holes and aprons exist only in play.

From `C:\GrandTour`, with the editor and games closed:

```powershell
& 'C:/Program Files/Git/bin/bash.exe' Art/build.sh
& Art/import_mud_variants.ps1     # the arrays (once, and after revised bakes)
& Art/setup_mud_variants.ps1      # rebuilds the map and re-applies the live mud materials
& Art/check_mud_variants.ps1      # one dry crossing, the numbers and the pictures
```

The setup rebuilds the map, so manual edits in it are replaced. The check drives once, dry, at full throttle in low range
with the diff lock, and reports completion, each section's mean speed and its largest and mean sinkage, then takes an
on-foot picture (eye level along the -Y rut) and a close-up of each section after driving, into `Art/Export/MudVariants`.
It measures no cost or timing: the owner tests performance.

## Re-importing revised bakes

1. Re-bake in Blender (`Art/Blender/export_mud_wet.py -- variant=<V>`, see `docs/MUD_WET_STUDY.md`): it overwrites
   `Art/Export/MudStyleUE/T_MS_Bog<V>{Color,Normal,Rough,Height}.png` (2048, a 3 m tile).
2. `& Art/import_mud_variants.ps1`: re-imports all sixteen PNGs over the same slice textures
   (`/Game/GrandTour/ArtTests/MudStyle/Variants/`) and rebuilds the four arrays from them; the report is
   `Art/Export/MudVariants/import-report.json`.
3. Nothing else: the materials take the arrays by asset. A new variant is a new slice (append to `EGTMudVariant`, to
   `VARIANTS` in `import_mud_variants.py` and `live_mud_style.py`, and a case in `MudVariantDefaults`; never reorder).

## Results (2026-10-06)

No game and no foreign Unreal ran at any step. No cost or timing was measured (the owner's rule).

- **Tests**: 10 of 10 GrandTour.Mud and GrandTour.Snow tests Success, the Settle row's mud CRC **8e0aad06** (unchanged).
  GrandTour.Mud.Variants, one row per variant, built by `UGTMudSubsystem::BuildPatches` in a Game world:
  Firm sinkage cap x0.60 rate x0.60, friction x1.10, RecoverShare 0.25, LumpShare 0.25, ThrowMax 0.30, water table -25.0 cm;
  Standard x1.00 / x1.00, x1.00, 0.40, 0.35, 0.50, -25.0 cm; Deep x1.50 / x1.50, x0.90, 0.55, 0.35, 0.60, -15.0 cm;
  Stony x0.80 / x0.80, x1.15, 0.30, 0.20, 0.50, -25.0 cm; all four without a profile (a bog's patch) on the 12.5 cm grid,
  the field's RecoverShare and LumpShare equal to the patch's.
- **Arrays**: Python built them (the factory, then `source_textures` through `set_editor_property`: 4 slices of 2048 x 2048
  each); `UGTMudArtLibrary::BuildTextureArray` then rebuilds them from the slices on every import (4 x 2048 x 2048 each).
  Packages: Color 6.7 MB, Normal 19.3 MB, Rough 4.5 MB, Height 20.8 MB (source data).
- **The drive** (`& Art/check_mud_variants.ps1`, dry, full throttle, low range, the diff lock): completed, 200.06 m in
  84.6 s, largest lateral 0.51 m, longest stop 0.3 s (at 132.3 m, in Deep). Box gaps 6.4 m.

  | Section | time | mean speed | slowest | sinkage max / mean | friction scale (mean, in the mud) |
  |---|---|---|---|---|---|
  | Firm 30-55 m | 2.8 s | 8.94 m/s (32.2 km/h) | 6.53 m/s | 24.0 / 18.8 cm | 0.859 |
  | Standard 75-100 m | 3.7 s | 6.78 m/s (24.4 km/h) | 3.18 m/s | 40.0 / 32.8 cm | 0.707 |
  | Deep 120-145 m | 49.2 s | 0.51 m/s (1.8 km/h) | 0.04 m/s | 60.0 / 59.4 cm | 0.576 |
  | Stony 165-190 m | 4.0 s | 6.27 m/s (22.6 km/h) | 3.94 m/s | 32.0 / 26.7 cm | 0.842 |

  The sinkage caps are the Mud row's 40 cm times each scale (24 / 40 / 60 / 32). Deep is a crawl at its 60 cm cap (past the
  axle clearance: the belly drags); Firm is crossed at speed. The friction scale column is the traction's whole wheel factor
  (wetness, sinkage grip loss, belly, the variant's scale), not the variant's alone.
- **Pictures** (`Art/Export/MudVariants`, after the drive, the car hidden, dry):
  - `MudVariants_Firm_OnFoot.png`: a lighter brown, matte patch covered in small flat-topped lumps; the two ruts carry the
    same texture with dark shadowed floors; no line at the patch's sides; a pale band across the road at the patch's far end.
  - `MudVariants_Firm_Close.png`: crowded rounded-angular light lumps on a darker brown base, like a bed of pebbles; the rut wall
    on the left shows the lumps stretched along the slope; small hatched marks on some lump edges.
  - `MudVariants_Standard_OnFoot.png`: darker brown mud with lighter rounded lumps; two ruts with grey pools of rut water; the
    pale band at the far end.
  - `MudVariants_Standard_Close.png`: flat light-brown rounded lumps in glossy dark mud, reading as stones set in mud; a
    translucent grey rut-water sheet over part of the rut.
  - `MudVariants_Deep_OnFoot.png`: a wide trench the belly ploughed, filled with grey-brown rut water; dark glossy banks
    with low soft humps and ring-like spots; the pale band at the far end; a pale cloud-like shape in the sky.
  - `MudVariants_Deep_Close.png`: the camera over the flooded trench: the brown translucent water surface fills the frame
    with a few specks; little mud shows.
  - `MudVariants_Stony_OnFoot.png`: dark brown lumpy mud speckled with pale chips; water in both ruts; pale ground beyond the
    grass at both sides and the band at the far end; a pale cloud-like shape in the sky.
  - `MudVariants_Stony_Close.png`: rounded lumps and clusters of pale angular chips in glossy dark mud; the rut's near wall a
    smooth light-brown strip.
- **Seen before LM5b too**: the pale band across the road at a patch's far end and the pale bluish ground beyond the grass
  are in L_MudDrive's `Mud_OnFoot_Dry.png` of 2026-10-06 01:56 (before this stage); their cause is unchecked.
- **Unchecked**: the far gloss fade's effect (no picture with it off); the patch's apron in a top-down or border picture (the
  on-foot views show no line at the patch's sides); L_MudDrive and The Hide in pictures (their material changed: the Standard
  bog everywhere in the patch); the wet look; every cost.

## Carried mud, splats, muddy grass (MudRunner MR1, 2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MR1, VEHICLE_BUILD_SYSTEM section 79. Every level, not only this strip.

- **Carried tracks**: a wheel loads mud on a bog's Mud or Bog row (`FGTWheelTraction::MudLoad`, full in about 1-2 s) and lays it
  outside every patch as overlapping clumps from the splat atlas (MR2 housekeeping: stamped by distance, never further apart than
  0.6 of a clump's radius, so no beads), its strength following a 1-3 m noise along the track so the trail breaks into smears and
  gaps, more gaps as the load sheds (half every 15 m of ground, every 2 m in a ford's water over 5 cm). They fade over 600 s (the
  time constant) and dry from wet (dark, glossy) to dried (lighter, matte) over 90 s.
- **Splats**: thrown mud that comes down outside a patch splats the landscape (the same paint) or a static mesh (a decal: a
  rock, a post, a road mesh), and inside a patch's box it still splats a mesh it hits (the box reaches 2 m past the mud, so the
  winch posts stand inside one). At most 96 decals, the oldest replaced (a decal waits hidden until its material's shaders are
  compiled: before them the engine draws a black box); at most 64 traces a frame, and only for a blob coming down within a metre
  of the ground under it (the landscape's own height, no trace, catches the rest).
- **Muddy grass**: the tussocks' (and The Hide's L3 cards') lower 18-30 cm darken toward the bog's mud over carried mud, with a
  speckle above (MR2 housekeeping: measured from each tussock's own foot - it was the grass component's origin, under the
  strips' ground - and in the bog's own brown, not the straw's).

### Switches (console, 1 = on, the default)

| Switch | What 0 does |
|---|---|
| `gt.Mud.Carry` | no carried tracks are laid (with `gt.Mud.Splats` 0 too, the ground materials skip their cover block) |
| `gt.Mud.Splats` | no blob is traced: thrown mud outside a patch is lost as before MR1, no decals |
| `gt.Mud.GrassMud` | the grass skips its mud (the material's static switch `GrassMud` removes it from the shader) |

### How to see it on L_MudVariants

Drive into any bog until the wheels are in (a second or two), then out onto the gravel and stop 10-20 m on: look back at the
road behind the car. A wheel spun in the mud at a bog's edge throws mud past the patch onto the gravel; `SplatPost_Deep` (a pale
post at Deep's left edge, 121.6 m, 4.2 m left of the line) catches it from a wheel spun right in front of it. Driving off the road
across the tussock verge out of Stony puts the carried mud under the clumps. The look numbers are on `MF_MudCover`
(`MudCoverEdgeLo`/`Hi` 0.15/0.35, `MudDryLighten`, `MudWetDarken`, `MudWetRough`, `MudDryRough`), `M_GT_MudSplatDecal` and the
grass's `GrassMudLineMinCm`/`MaxCm` and `GrassMudDryColor`; the track numbers on `UGTTrackPaintSubsystem` (`CarrySize*`,
`CarrySpacing*`, `CarryJitter`, `CarryCoverage`, `MudFadeSeconds`, `MudDrySeconds`) and the load's on `UGTTractionComponent`
(`MudLoadRate`, `MudShedHalfM`, `MudWashHalfM`). All proposals.

### Rebuild after a rerun of another setup

`& Art/setup_mud_carry.ps1` imports the atlas (bake `Art/Blender/build_mud_splats.py` first; rebuild the C++ after a re-bake:
`GTMudBlots.inl` is the brushes) and wires everything. The strip setups keep the ground cover. Rerun it after
`setup_m6_hide` (rebuilds M_GT_Landscape), `setup_look_l3` (rebuilds M_GT_FoliageCard) or `setup_tussock_style` (rebuilds
M_TS_Grass).

## The muddy car (MudRunner MR2, 2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MR2, VEHICLE_BUILD_SYSTEM section 80. Every level: the car gets muddy wherever it meets mud.

- **Tyres** cake in a second or two in any bog (the treads first, then the sidewalls inward, the rims last as it thickens) and
  stay caked until water or rain washes them; the mud turns with the wheel.
- **The mud line**: the body's coat reaches as high as the mud did - the deeper of the sinkage and the water at the tyres plus
  20 cm, plus 30 cm while a wheel spins, the most over the last 10 s - and stays there once laid (dried mud stays until washed).
  Its edge rises and falls along the body, higher round the wheels, broken by the bog's lumps and a car-space splatter of
  droplets and drips; above it thrown droplets thin out over about 80 cm; below it the coat is thick at the sills and thins in
  clusters toward the line.
- **MR2b, splatter with structure** (VEHICLE_BUILD_SYSTEM section 82): the solid coat's line runs along each side at about
  two thirds of that height, rising about 15 cm over each arch and dipping between them, its slope never steeper than
  about 1.5 (no vertical walls), its edge jagged at two scales (a fine noise and the splatter's own droplets). The droplets
  above it come from the wheels: each wheel has a spray fan (FanCoat, fed by its spin either way and its speed through mud,
  washed like the coat) that opens up and back from its arch, away from the way it last threw, densest just behind and above
  the arch and thinning over about 1.2 m; elsewhere only a sparse tenth as many. Whole droplets appear or not (each droplet in
  the splatter bake has a rank), so a thin fan is fewer droplets, not smaller ones.
- **Where it comes from**: driving through a bog coats the sills, bumpers and arches by speed x sinkage; spinning flings mud
  onto the front bumper and front wings (front wheels) or the rear and rear arches (rear wheels); the belly dragging in deep mud
  coats the sills; a thrown blob that hits the body coats the part it hits (the only way mud reaches the windscreen; a blob
  under the floor coats it and drops back into the bog).
- **Wet and dry**: fresh mud is dark and glossy; it dries over 90 s to lighter and matte (never drier than the weather's
  wetness).
- **Washing**: a ford's water washes everything below its waterline (0.3 a second driving, 0.1 standing; tyres 0.5 a second);
  a bog's rut water does not (it is slurry). Rain washes everything slowly (0.01 a second at full rain).

### Switches (console, 1 = on, the default)

| Switch | What 0 does |
|---|---|
| `gt.Mud.CarMud` | the body state and its materials as before MR2: the dirt per region as a flat colour fading up from the sills, the windscreen's dirt from the front wheels, no tyre mud, no blob hits on the body |

MR1's housekeeping changed no switch: `gt.Mud.Carry`, `gt.Mud.Splats` and `gt.Mud.GrassMud` stay as above.

### How to see it

On L_MudVariants: drive the strip (any bog will do; Deep with a spin-up coats the car to the windows), stop on the gravel and
walk round it, or switch to the chase camera. On L_MudDrive: through the mud (32-60 m), stop at 74 m and look at it, then
through the ford (88-100 m) and stop past 109 m: below the waterline it is clean, above it still muddy. Toggle `gt.Mud.CarMud`
to compare (the state keeps counting either way; the look switches at once). The look numbers are on `M_GT_Vehicle`
(`MudTileCm`, `MudBlurMips`, `MudNormalStrength`, `AboveCm`, `DryLighten`, `WetDarken`, `WetRough`, `DryRough`; MR2b: the line
`LineDropShare`, `ArchRiseCm`, `ArchRampCm`, `LineLongCm` / `LineLongAmpCm`, `LineShortCm` / `LineShortAmpCm`, its edge
`EdgeNoiseCm` / `EdgeNoiseAmpCm`, `EdgeSplatCm`, the fans `FanReachCm`, `FanLowDeg` / `FanHighDeg`, `FanFalloff`,
`FanNoiseCm` / `FanNoiseAmpCm`, `FanBase`; MR2's `LineWaveCm` and `ArchLiftCm` are gone), `M_GT_Tyre` (`TyreTileCm`, `RimShare`, `RubberColour`, `RimColour`) and `M_GT_Glass`; the rates on
`UGTBodyStateComponent` (`TyreCoatSeconds`, `SillMudRate`, `BumperMudRate`, `ArchMudRate`, `FlingRate`, `BellyMudRate`,
`BlobHit*`, `MudLine*`, `Wash*`, `RainWashRate`, `MudDrySeconds`; MR2b `FanSpinRate`, `FanRollRate`). All proposals.

### Rebuild after a rerun of another setup

`Art/setup_m1_body.bat` rebuilds M_GT_Vehicle, M_GT_Tyre and M_GT_Glass (after `Art/import_mud_variants.ps1` and
`& Art/setup_mud_carry.ps1`, whose bog arrays and splatter it reads); then `Art/setup_m1_masters.bat` (the glass's MF_Weather).
MR2b: the splatter's droplet ranks are its G channel (`Art/Blender/build_mud_splats.py`, then `& Art/setup_mud_carry.ps1` to
import it, then `Art/setup_m1_body.bat`).
The checks: `& Art/check_mud_variants.ps1 [-AllowGame]` (Car_Muddy_Side.png, Car_Muddy_Rear.png; MR2b: the droplet-density
row, `python Art/count_car_droplets.py` on the report and the picture, and Car_Muddy_Side_Boxes.png with its boxes) and
`& Art/check_car_washed.ps1 [-AllowGame]` (Car_PreFord.png, Car_Washed.png in Art/Export/LiveMudDrive).

## Muddy rut water (MudRunner MR3, 2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MR3 (rut pools only: the ford's water is being reworked separately and is untouched),
VEHICLE_BUILD_SYSTEM sections 84 and 86 (MR3b). Every bog with rut water, every level.

- **Settled water** (MR3b): a rut pool nobody has churned reads as water - darker than before, glossy, see-through near its
  rim (the rut floor shows faintly there), with more of the sky in it at a low angle.
- **Churned brown**: a wheel that moves the mud under a rut pool (where its fresh sheen is set), or a thrown blob landing in
  one, turns that cell's water an opaque, lighter mid-brown, rougher (`Turbidity` 1 in the mud field, where over 1 cm of water
  stands). The brown is the Standard bog's colour, lightened, softly mottled (the bake far down its mips: no grain, no
  pebbles). Settled and churned are blended by turbidity.
- **Froth** (MR3b): where the churn is fresh (the 6 s sheen) and the water is turbid, clumps of small soft bubbles (about
  0.7-1.6 cm, two random layers) float on it, creamy beige-tan, lighter in the middle with a small glint, thinning toward each
  clump's edge; the clumps come from a 25 cm noise. Past about 4-9 m the bubbles fade into a soft tone. (MR3's froth, the
  splatter bake's droplets, read as spilt paint and is gone.)
- **Settling**: the churned water mixes lightly into the wet cells beside it (never into dry mud, never above fully churned),
  and clears with a half-life of 45 s (`RutSettleS`): half as brown after 45 s, a quarter after 90 s, gone (and the tile
  asleep) after about 4 minutes. It runs on its own clock, whatever `gt.Mud.Settle` says; the heights never change for it.

### Switches (console, 1 = on, the default)

| Switch | What 0 does |
|---|---|
| `gt.Mud.MuddyWater` | the rut water exactly as before MR3: nothing turns turbid (the field's turbidity cleared, the tread texture's A 0) and M_GT_MudWater's wrapper returns its input untouched |

### How to see it

On L_MudVariants: drive into Deep (120-145 m) and spin the wheels in the ruts for a few seconds, then drive or set the car on
and look back at the pools: brown with froth specks at first, clearing over a minute or two. On L_MudDrive the same in its rut
pools (32-60 m). The look numbers are on `M_GT_MudWater` (MR3b settled: `SettledDarken` 0.8, `SettledOpacity` 0.6,
`SettledRimOpacity` 0.3, `SettledDeepCm` 8, `SettledFresnel` 0.45, `SettledRough` 0.07, `SettledGlossRough` 0.03; churned:
`TurbidLighten` 2.3, `TurbidMottle` 0.45, `TurbidMip` 5, `TurbidTileCm` 300, `TurbidOpacity` 0.95, `TurbidRimOpacity` 0.75,
`TurbidOpaqueCm` 3, `TurbidRough` 0.35, `TurbidMean` the Standard bog's mean; the froth `FrothTurbidLo`/`Hi` 0.5/0.85,
`FrothAmount` 1, `FrothClusterCm` 25, `FrothClumpLo`/`Hi` 0.35/0.75, `FrothBubbleCm` 1.6, `FrothNearCm`/`FarCm` 400/900,
`FrothFarCover` 0.55, `FrothColor` 0.28 0.23 0.15, `FrothGlint` 0.35, `FrothRough` 0.3), the rates on the mud field (`RutSettleS` 45, `TurbidMixRate` 0.15 a second,
`TurbidMinWaterCm` 1, `TurbidSleepBelow` 0.02, `TurbidStepS` 0.1). All proposals.

### Rebuild after a rerun of another setup

`live_mud_style.py` puts the wrapper (`Muddy water (MR3)`) on M_GT_MudWater after its own rut-water shading, so
`& Art/setup_live_mud_drive.ps1` or `& Art/setup_mud_variants.ps1` restores it after `Art/setup_m6_water.bat` rebuilds the
material. It reads the bog arrays (`Art/import_mud_variants.ps1`). The check: `& Art/check_mud_variants.ps1 [-AllowGame]`
(Rut_Muddy.png, Rut_Settled.png, MR3b's eye-level Rut_Muddy_Low.png and Rut_Settled_Low.png, and the turbidity readout).

## Physically based mud, parallax occlusion (MudRunner MRP, 2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MRP, VEHICLE_BUILD_SYSTEM section 91. The owner at the world-reacts gate: "That is far too glossy,
we need pbr and occlusion mapping for detail. ensure it is optimised." Every level, every surface that draws mud.

- **Physically based values** (gt.Mud.PBR 1, the default). Mud is a dielectric (F0 0.04, the default specular):
  - **the mud ground** (M_GT_Mud, and the landscapes' 3 m apron round each patch): the bakes' roughness is remapped into the
    physical bands, `r' = 0.45 + (r - 0.14) x 0.5 / 0.77` (clamped 0.45-0.95): the slurry (0.15-0.38 in the bakes) lands at
    0.46-0.61, wet mud; the lump tops (0.83-0.90) at 0.89-0.95, dry soil. The weather's wetness and the fresh sheen (a rut just
    made) take it toward the same surface saturated, 0.45-0.65 (`MudWetRoughLo`/`Hi`), never lower; they darken it 0.65-0.82x
    and 0.85x as before. Nothing on the mud ground goes under 0.4.
  - **the rut water** (M_GT_MudWater): water's F0 0.02 (Specular 0.25); settled water 0.15 with a faint moving ripple; churned
    water 0.5 and opaque; the froth 0.6 (foam). Its grazing-angle tricks are gone: the extra opacity at a grazing angle, the fall
    to 0.03 roughness there, the froth's glint.
  - **the car's mud** (M_GT_Vehicle's Grime, M_GT_Tyre, the glass's splats): wet 0.5 (within 0.45-0.55) to dry 0.9; the clear
    coat 0 under it; after the weather a floor keeps it at 0.45 or more (rain took porous mud to 0.15).
  - **carried mud and splats** (MF_MudCover on the ground materials, the splat decals): dried 0.85-0.95, wet 0.45-0.65 (MR1's
    wet was 0.30-0.32).
  - the clods were already in the bands (dry 0.85, wet 0.45, fresh 0.5) and are unchanged.
- **Ambient occlusion**: each variant's height is turned into a horizon AO map (6 cm radius, `python Art/bake_mud_orh.py`, the
  PNGs beside the bakes: `T_MS_Bog<V>AO.png`) and packed with the remapped roughness and the height into one array,
  `TA_MS_BogORH` (R AO, G roughness, B height; linear BC7). The ground, the carried mud, the splats and the car's mud read Color +
  Normal + ORH: three samples a tiling where there were four. The AO goes to the Ambient Occlusion output (it dims the sky's
  light in the crevices) and tints the crevices' colour by at most 15 % (`MudCavityTint`).
- **Parallax occlusion** on the mud ground (gt.Mud.POM 2, the default): the lumps are pushed in by up to 3 cm
  (`MudPomDepthCm`) along the field's own normal (right on rut walls too), every lookup on both tilings moved with it. Optimised:
  full within 6 m (`MudPomNearM`), fading to nothing by 14 m (`MudPomFarM`) - past it the march is skipped by a dynamic branch;
  8 steps looking straight down, up to 16 at a grazing angle (`MudPomMinSteps`/`MaxSteps`); no march where rut water stands over
  the mud; mip-correct (no shimmer at mip seams). A 4-step shadow toward the sun within 4 m (`MudPomShadowM`, darkening by
  `MudPomShadowStrength` 0.45), gt.Mud.POMShadow.
- **The far gloss fade** (LM5b's band fix: the glossy slurry banded across far ruts) is not needed at these values: its static
  switch `FarGlossFade` is now off (gt.Mud.PBR 0 still applies it, as before MRP).

### Switches (console)

| Switch | Values | What it does |
|---|---|---|
| `gt.Mud.PBR` | 1 (default) / 0 | 1 the physically based values above; 0 the look before MRP, to within the textures' quantisation (the bakes' own roughness through the inverse remap, the far fade, the glossy wet mud, the rut water's grazing gloss and opacity, the froth's glint, the car's 0.3 wet mud), no AO |
| `gt.Mud.POM` | 2 (default) / 1 / 0 | the mud ground's parallax: 2 adaptive 8-16 steps, 1 a flat 8 steps, 0 off |
| `gt.Mud.POMShadow` | 1 (default) / 0 | the parallax's sun shadow within 4 m (needs gt.Mud.POM 1 or 2) |

They are MPC_TrackPaint scalars (`MudPBR`, `MudPOM`, `MudPOMShadow`) that UGTTrackPaintSubsystem writes when they change, so they
switch at once, in play.

### How to A/B (the owner)

1. On L_MudVariants (or L_MudDrive), Play, drive into a bog, stop and get out or use the chase camera.
2. `gt.Mud.PBR 0` / `gt.Mud.PBR 1`: the gloss before and after, on the ground, the rut pools, the car and the carried mud.
3. Stand about 1 m from untouched mud, look across it low: `gt.Mud.POM 0` / `2`: flat or pushed-in lumps. `gt.Mud.POM 1` is the
   cheaper 8 steps.
4. `gt.Mud.POMShadow 0` / `1` with the sun low across the mud.
5. Cost (the owner's to measure): `stat gpu` / `ProfileGPU` with each switch; the static shader numbers are below.
6. The look numbers are parameters on the materials (M_GT_Mud: `MudPomDepthCm`, `MudPomNearM`, `MudPomFarM`, `MudPomMinSteps`,
   `MudPomMaxSteps`, `MudPomGrazingMinSteps`, `MudPomRefine`, `MudPomSteepCap`, `MudPomShadowM`, `MudPomShadowStrength`,
   `MudAOStrength`, `MudCavityTint`, `MudWetRoughLo`/`Hi`;
   M_GT_MudWater: `WaterSpecular`, `SettledRoughPBR`, `TurbidRoughPBR`, `FrothRoughPBR`, `RippleCm`, `RippleSlope`,
   `RippleSpeedCm`; MF_MudCover and M_GT_MudSplatDecal: `MudWetRoughLo`/`Hi`, `MudCavityTint`; M_GT_Vehicle / M_GT_Tyre:
   `WetRoughPBR`, `CavityTint`). All proposals.

### Shader stats (static, not timing)

`MaterialEditingLibrary.get_statistics` at the editor's platform (PCD3D_SM6), before MRP / after; a loop or a branch counts once
whether it runs or not (Art/Unreal/mud_pbr_stats.py, Art/Export/MudVariants/shader-stats-before.json / -after.json).

| Material (role) | pixel instructions | vertex instructions | samplers |
|---|---|---|---|
| `M_GT_Mud` (mud ground) | 503 -> 742 | 264 -> 264 | 7 -> 6 |
| `M_GT_MudWater` (rut water) | 2515 -> 2602 | 339 -> 339 | 8 -> 8 |
| `M_GT_Vehicle` (car body) | 731 -> 750 | 245 -> 245 | 11 -> 10 |
| `M_GT_Tyre` (tyre) | 321 -> 341 | 314 -> 314 | 5 -> 5 |
| `M_GT_Glass` (glass) | 443 -> 443 | 339 -> 339 | 3 -> 3 |
| `M_GT_Landscape` (MF_MudCover user) | 305 -> 319 | 155 -> 155 | 7 -> 6 |
| `M_GT_Environment` (MF_MudCover user) | 357 -> 371 | 155 -> 155 | 8 -> 7 |
| `M_LiveLandscape` (MF_MudCover user) | 477 -> 493 | 155 -> 155 | 10 -> 8 |
| `M_VariantsLandscape` (MF_MudCover user) | 477 -> 493 | 155 -> 155 | 10 -> 8 |
| `M_GT_MudSplatDecal` (splat decal) | 405 -> 415 | 344 -> 344 | 5 -> 6 |
| `M_GT_Clod` (clods) | 262 -> 262 | 148 -> 148 | 3 -> 3 |

M_GT_Mud's +239 pixel instructions are the parallax (its loop body and the shadow's four steps count once each) and the PBR
branch; with gt.Mud.POM 0, or past 14 m, or under rut water, the march does not run. The ORH array took one sampler off every
ground material (the rough and height arrays became one) and added one to the decal (it had no roughness map). M_GT_Glass's count
did not move: its default translucency lighting takes no specular, so its new splat roughness is compiled out. M_GT_Clod is
unchanged (already in the bands).

### Rebuild

`python Art/bake_mud_orh.py` (after a re-bake of the variants), `& Art/import_mud_variants.ps1` (the ORH array with the others),
then `& Art/setup_mud_carry.ps1` (MF_MudCover, the decal), `& Art/setup_live_mud_drive.ps1` / `& Art/setup_mud_variants.ps1`
(M_GT_Mud, the landscapes, the rut water) and the car (`Art/setup_m1_body.bat` then `Art/setup_m1_masters.bat`, or both in one
run with a real RHI: `UnrealEditor.exe GrandTour.uproject -RenderOffScreen ... -ExecutePythonScript=Art/Unreal/run_body_masters_gpu.py`).
The checks: `& Art/check_mud_variants.ps1 [-AllowGame]` (the MRP pictures and captures, then `python Art/sample_mud_pbr.py` on
them) and `& Art/check_car_washed.ps1 [-AllowGame]` (L_MudDrive's captures).

### Results (2026-10-08, no game and no foreign Unreal at any MRP run; no cost or timing measured)

- **PBR rows** (`python Art/sample_mud_pbr.py`, Art/Export/MudVariants/pbr-rows.json and Art/Export/LiveMudDrive/pbr-rows.json;
  the dumps are linear: the gravel reads 0.898 against its 0.9). Ground, the middle of a picture looking down into each patch:
  roughness p5 / median / p95, AO mean / p5, the base colour's linear luminance:

  | Capture | roughness | under 0.40 | AO | base colour (linear RGB, luminance) |
  |---|---|---|---|---|
  | Firm (L_MudVariants) | 0.741 / 0.886 / 0.945 | 0 % | 0.864 / 0.725 | 0.088 0.059 0.034, 0.063 |
  | Standard | 0.502 / 0.643 / 0.918 | 0 % | 0.874 / 0.659 | 0.070 0.040 0.019, 0.045 |
  | Deep | 0.455 / 0.510 / 0.682 | 0 % | 0.975 / 0.918 | 0.049 0.029 0.014, 0.032 |
  | Stony | 0.502 / 0.608 / 0.918 | 0 % | 0.898 / 0.737 | 0.069 0.044 0.022, 0.048 |
  | Standard (L_MudDrive) | 0.502 / 0.671 / 0.918 | 0 % | 0.857 / 0.612 | 0.072 0.041 0.019, 0.046 |

  Every ground's 5th percentile is 0.40 or more (PASS). The base colours sit in the soil range for wet mud (0.0325-0.2) except
  Deep, 0.0322, at its dark edge (the approved colour, not changed). Car mud, the sill band between the arches: wet (L_MudDrive at
  74 m, MudWet 0.89) 0.451 everywhere (the weather's wet path took it lower; the floor after MF_Weather holds it at 0.45), base
  colour luminance 0.028, AO 0.861 (PASS, 0.45 or more); dry (L_MudVariants after the MR3 phase, MudWet 0) 0.886 / 0.898 / 0.910,
  luminance 0.075. The rut water is translucent (not in the GBuffer): its row is the material's formula over the pool's turbidity
  round the Rut_Settled spot (121 cells 20 cm apart, turbidity mean 0.25): median 0.272, lowest 0.15 (PASS, 0.12 or more).
- **Pictures** (Art/Export/MudVariants; the second run, after the close-up camera moved off the first run's shadowed spot):
  - `Mud_PBR_OnFoot.png` / `_POM0.png`: matte brown mud along Standard's ruts, no sheen on the slurry or the rut floors, the rut
    water a darker see-through film; the parallax shows only in the near metres (the lumps a little rounder and shadowed; mean
    difference 6.6 of 255, a quarter of the pixels over 8); no crosswise bands in the far ruts with the far fade off.
  - `Mud_PBR_Close.png` / `_POM0.png` (60 cm, 25 cm up, untouched mud): with POM 0 the lumps are flat plates shaded by their
    normals; with POM 2 they stand up out of the mud, hide the mud behind them and have dark shadowed fronts and undersides
    (mean difference 14.3 of 255). Seen at full size: fine stair-stepping (striations) on the steep flanks of the largest lumps and
    serrated edges along some silhouettes; the undersides are near black, which pushes the Standard lumps toward stones set in mud.
    Stills cannot show swimming; no hard lines at mip seams.
  - `Rut_Settled_PBR.png`: a murky see-through brown film over the rut floor (its lumps show), a soft faint sheen, no mirror
    reflection; the ripple is not visible at 3.4 m.
  - `Car_Muddy_PBR.png`: the coat dried (MudWet 0), a lighter matte brown with the droplets and the caked tyres; nothing glossy.
    L_MudDrive's `Car_PreFord.png` (wet, 0.89): a darker matte coat, no highlights.
  - Nothing reads as glossy in any of them; the section pictures (MudVariants_*_OnFoot / _Close) and the MR1-MR3 set were retaken
    in the same runs at the new values.

### Follow-up (2026-10-08): the parallax's refine, the carried mud's rain floor

- **The march** (the main session saw step bands on the larger lumps' flanks in Mud_PBR_Close): the step search reads the height one
  mip up (slightly blurred, so a thin crest is not jumped); then 5 binary halvings at full resolution (`MudPomRefine`) and a secant
  between the bracket's ends; at least 12 steps at a grazing angle (`MudPomGrazingMinSteps`; 8 looking down, 16 at most). The fade,
  the branch and the water skip are as before. `MudPomSteepCap` (0, off) shrinks the depth where the relief is steep; it was tried
  at 0.6 and did not change the bands. M_GT_Mud: 742 -> 917 pixel instructions (static count).
- **What is left**: on the steepest lump flanks seen at a grazing angle (`Mud_PBR_Close_Steep.png`, about 20 degrees) a fine band
  pattern stays, with or without the cap and with gt.Mud.POMShadow 0 alike (`Mud_PBR_Close_Steep_NoShadow.png`, 0.27 of 255 apart).
  It looks like the packed height's own steps (BC7 keeps at most 16 levels of a 4 x 4 block's range, and a lump's flank spans the
  whole range inside one block), not the march; a higher-precision height (an uncompressed or 16-bit height) would show it, at two
  to four times that array's memory. Not tested.
- **Rain on carried mud**: MF_MudCover's new output `FloorMask` (its cover, with gt.Mud.PBR on) feeds a node after each ground
  material's MF_Weather call (`MudCover rain floor (MRP)`): roughness max(R, 0.45) by FloorMask x (1 - the weather's Puddle). So
  carried mud and landscape splats stay at 0.45 or more in any rain; standing puddles, the gravel and every other surface keep the
  weather's values (MF_Weather is unchanged). The splat decals on meshes were never weathered (they draw over the base pass with
  their own 0.45-0.95). On M_GT_Environment, M_GT_Landscape, M_LiveLandscape and M_VariantsLandscape (+3 / +4 pixel instructions).
- **Checked** (`& Art/check_mud_variants.ps1 -AllowGame`, no game): `Carry_Wet_PBR.png` - fresh tracks driven out of Stony onto the
  gravel, test wetness 1, looking down at 200 m: the track a matte brown band with its lumps (a soft sheen on the lumps' rims), the
  gravel round it wet and darker, a puddle glossy at the left; its dump (PBR_CarryWet): the carried mud's roughness median 0.451, p5
  0.259 (the track's feathered edges, where the cover is partial), the wet gravel's median 0.129, the puddle 0.03.

### Follow-up 2 (2026-10-09): the parallax's height in its own array

- **Arrays**: `TA_MS_BogHeightPOM` - the parallax's height, BC4 (TC_Alpha, one channel with its own endpoints per 4 x 4 block) from
  the 16-bit `T_MS_Bog<V>Height.png`; `TA_MS_BogOR` - the AO (R) and the remapped roughness (G), BC5 (TC_Normalmap, read raw;
  `T_MS_Bog<V>OR.png` from `python Art/bake_mud_orh.py`). `TA_MS_BogORH` (BC7) is no longer built or read; the old `TA_MS_BogHeight`
  (BC1) stays imported for M_GravelLandscape. The ground, the aprons, MF_MudCover, the decal, the car and the tyres read OR, and the
  height array where they need a height. Memory, 4 slices of 2048 with every mip: ORH 22.4 MB; OR 22.4 MB + HeightPOM 11.2 MB =
  33.6 MB. M_GT_Mud 917 -> 919 pixel instructions, 6 -> 7 samplers (one more on each ground material, the car and the tyre).
- **The test** (the main session's BC7 theory): Mud_PBR_Close_Steep with the height in BC7, BC4 and uncompressed G8 (a test array,
  `TA_MS_BogHeightPOM8`, `GT_POM_HEIGHT_G8=1` / `GT_MUD_POM_HEIGHT=G8`) shows the same bands on the steepest flank. The cause is in
  the bakes: their lumps have near-vertical rims (up to 0.36 cm of height per 0.146 cm texel), and the parallax stretches those few
  texels of colour, normal and AO across the whole visible flank. BC4 is kept as built; it does not remove them. Next to try: a
  softer rim in the bakes, or a pre-blurred height for the parallax.

### Follow-up 3 (2026-10-09): a soft-rimmed parallax height, back to one ORH pack

- **ORH's B** is now the parallax's own height with soft rims (`python Art/bake_mud_orh.py`: the slope capped at 1.5 % of the range
  per texel - the mean of the height's two cone envelopes, so tops and floors keep their levels - then a 1.5 texel Gaussian). The AO
  and the shading normal still come from the sharp bake. Max slope per texel before -> after: Standard 23.6 -> 1.5 %; Firm 23.1 -> 1.5 %; Deep 22.1 -> 1.5 %; Stony 17.7 -> 1.5 %. Follow-up 2's split is undone:
  every reader reads ORH again (M_GT_Mud 917 pixel instructions, 6 samplers). Left on disk, unreferenced, for the owner to delete in
  the editor if wanted: `TA_MS_BogOR`, `TA_MS_BogHeightPOM`, `TA_MS_BogHeightPOM8` (/Game/GrandTour/ArtTests/MudStyle) and their slices
  `Variants/T_MS_Bog<V>OR`, `T_MS_Bog<V>HeightPOM`, `T_MS_Bog<V>HeightPOM8`; the PNGs `T_MS_Bog<V>OR.png` and `T_MS_Bog<V>Height8.png`.
- **Seen**: Mud_PBR_Close_Steep - the band pattern down the steepest flank is gone (a smooth slope); a dotted dark line remains along
  some lumps' feet and the shadowed edges of the left lumps are serrated. Mud_PBR_Close POM 0 / 2 - with POM 2 the lumps still stand
  up and hide the mud behind them, lower and softer-edged than with the sharp height (4.2 of 255 from that picture), not flattened.
- **Texture memory** (the built platform data, every mip of every slice: `UGTMudArtLibrary::TextureAllMipsBytes`; Art/Export/MudVariants/
  shader-stats-followup3.json): the bog arrays 53.4 MiB (Color DXT1 10.7, Normal BC5 21.4, ORH BC7 21.4); everything the mud materials
  read 135.9 MiB (RT_TrackPaint 32.0, the bog arrays, the clay and legacy mud maps M_GT_Mud still binds 26.9, the strips' gravel and
  grass 8.1, the splat atlas 13.5, RT_RainOcclusion 2.0); the snow's 62.2 MiB (RT_TrackPaint and the same clay and legacy maps, the
  snow detail 1.4). The unreferenced arrays above are 53.4 MiB on disk and not loaded.
- **The video-memory crashes** (the 6 GB card): the last two check runs ended out of video memory after their pictures and captures,
  the second with `-PoolSize 1500` (r.Streaming.PoolSize). The textures are not the cause: at the crash D3D12 held 26.7 GB of UAV
  buffers against 253 MB of textures and 769 MB of render targets, and the texture pool needed 42 MB. It came after about 25
  HighResShots and 6 buffer dumps in one play session; whether play without them grows the same way is unchecked (`stat
  d3d12resources` over a drive would show it).

## Readable soft spots (MudRunner MR4, 2026-10-09)

docs/MUDRUNNER_LESSONS_PLAN.md MR4, VEHICLE_BUILD_SYSTEM section 96. Every bog's patch (an unprofiled bog or a variant's): not a
ford's or riverbed's bed, not snow. A static softness S per cell: where it is high the wheels sink deeper (the sinkage's cap and
rate x lerp(0.75, 1.5, S)) and grip a little less (friction x lerp(1.05, 0.9, S)), both normalised so the patch's mean stays the
variant's; and the ground there draws as the Deep bake, wetter, filling the hollows between the lumps first. The outer 0.5 m of a
patch is S 0.4, easing to the full S by 2 m in, so its edge matches the landscape's apron. The amplitude per variant is the table's
last column (proposed; the owner names them). Built: `AGTMudPatch::BuildSoftness` / `SoftScalesAt` / `HasSoftSpots`,
`UGTTractionComponent::PatchSinkage`, `FGTDeformProfile::SoftSpotAmplitude`, MudLayer's G (PF_R8G8), live_mud_style.py's SOFT_HLSL.

### Switches (console, 1 = on, the default)

| Switch | At 0 |
|---|---|
| `gt.Mud.SoftSpots` | S is treated as 0.5: the sinkage and friction exactly as before MR4, the layer's G uploaded as 0 (the look as MRP's); at once, in play |

The terrain test's bog run and escape (steps 8-9) run with it at 0: their gates test the tuned bog. Deep's soft spots keep its colour
(only the roughness pull; the x0.85 darkening is for the other variants).

### How to see it on L_MudVariants (the owner)

1. Play and walk to Standard (75-100 m) before driving; `gt.Mud.SoftSpots 0` / `1` shows where the soft spots are.
2. Drive through and compare the ruts' depth in and out of one; the CPU maps `Art/Export/MudVariants/soft-<V>.png` (S as grey, 1 px a
   cell, the route line in red) show where they lie.
3. Name the amplitudes (Firm 0.5, Standard 1, Deep 0.6, Stony 0.6 proposed; `FGTDeformProfile::MudVariantDefaults`).
4. Feel call: the bog escape on L_Leg03 (the terrain test's step 9). Without a game it made 7.0 m in 12 s at gt.Mud.SoftSpots 1 (twice)
   and 9.6 m with the switch at 0; with the step at 0 after a middle run at 1, 6.1 m (GoWR open). Its stop sits on soft ground (mean
   S 0.559 under the wheels' cells, 49 % soft).

### Results (2026-10-09; GoWR open for every run after the Codex pause; no cost or timing measured)

- **GrandTour.Mud.SoftSpots** on L_MudVariants' patches (309 x 109 cells): the soft share whole / interior (2 m in) Firm 11.8 / 16.8 %,
  Standard 20.5 / 25.0 %, Deep 16.7 / 20.6 %, Stony 13.0 / 19.1 %; at amplitude 1 pooled the interior's 25.0 % (the whole 19.4 %), 17
  blobs, median diameter 4.82 m, median shape factor 2.04; S 0.400 at most in the outer 0.5 m; the mean scales 1.0000; the stroke's rut
  ratio 1.5000 = its SinkScale ratio; switch 0 exact. The whole table is in VEHICLE_BUILD_SYSTEM 96.
- 14 of 14 Mud and Snow tests at gt.Mud.SoftSpots 1 and at 0, CRC 8e0aad06 both times, nothing else moved.
- M_GT_Mud 991 pixel instructions, 7 samplers (917 / 6 before; the seventh is MudLayer, compiled out since LM5b).
- **The check** at 1.13 frames a second (GoWR): the drive timed out at 76.28 m, then the scripted pass; Firm's sinkage max 28.47 cm,
  mean 24.66 cm (24.0 / 19.46 committed); mean speeds not comparable on the real clock. The wheel path's (line +-1 m) soft share: Firm
  29.1 %, Standard 18.6 %, Deep 18.0 %, Stony 14.3 %. New pictures and maps: `soft-Firm.png`, `soft-Standard.png`, `soft-Deep.png`,
  `soft-Stony.png`, `Soft_Standard_Before.png`, `Soft_Firm_Before.png`, `Soft_Top.png`, `Soft_Standard_After.png`.
- **Rebuild**: the C++ (`bash Art/build.sh`) and `& Art/setup_mud_variants.ps1` (or `setup_live_mud_drive.ps1`: M_GT_Mud's SOFT_HLSL).

## Breakable mud chunks (MudRunner MR5, 2026-10-09)

docs/MUDRUNNER_LESSONS_PLAN.md MR5 (its execution block), VEHICLE_BUILD_SYSTEM section 97. Chunks are the firm crust and soft
spots the soup: every bog's patch (MR4's scope: an unprofiled bog or a variant's; not a ford's or riverbed's bed, not snow, not
gravel) gets loose clods of dry crust, 20-50 cm across, lying where the soft spots' S is at most 0.55, within 6 m of the route line and
1.5 m in from the patch's rim. Each one is a rigid body (10-40 kg), asleep until touched. The wheels' suspension traces ignore them, so
a wheel never rides up on one: a wheel whose footprint reaches a chunk breaks it into 3-5 clods and a lump dome of its exact volume.
The car's body bumps and pushes them, and breaks one with a hit over `ChunkBreakImpulse` (500 N s); one that lands at over 4 m/s
breaks too. At most 64 are awake in the world at once.

- **Meshes**: six (`Art/Blender/build_mud_chunks.py`, `& Art/import_mud_chunks.ps1`): 2 rounded, 2 slab (one with a broken side),
  1 broken, 1 smear, 30 cm across at scale 1, 806-996 triangles, each with one convex hull (UCX_, at most 64 vertices) over the mesh
  above an embed line at 18 % of its height; the pivot is the hull's bottom, so a resting chunk has its lowest 18 % under the ground.
  `Art/Export/MudChunks/manifest.json` has each one's volume, hull volume and embed height; the import puts them on the mesh
  (`UGTMudChunkData`). Material `M_GT_MudChunk`: M_GT_Clod's graph (live_mud_style.py), the patch's variant slice, freshness 0, a
  tint per chunk (custom primitive data 0).
- **Placement** (`AGTMudPatch::PlanMudChunks`, deterministic per section): 1 per 25 m^2 of the candidate ground x the variant's
  `ChunkDensityScale` (Firm 0.5, Standard 1, Deep 1.5, Stony 1; at most 48 a patch); a 4 m noise marks 35 % of it as cluster
  ground (x2.5 there, x0.2 elsewhere); sizes 20 + 30 u^2.2 cm (u stratified, so even a few span the range); edge gaps of at least
  5 cm; random yaw, tilted up to 12 degrees, lifted until the hull's lowest point is on the landscape.

### Switches (console, 1 = on, the default)

| Switch | At 0 |
|---|---|
| `gt.Mud.Chunks` | no chunks: the existing ones are removed and nothing is deposited (the mud field exactly as before MR5); at once, in play. Back at 1 they are placed anew on the ground the wheels have not touched |

The terrain test's bog run and escape (steps 8-9) run with it at 0, beside gt.Mud.SoftSpots 0 (the tuned bog).

### The owner's test list

1. On L_MudVariants, `gt.Mud.Chunks 0` / `1` before driving, then drive through Standard and Deep: the chunks a wheel reaches break,
   the body pushes the rest.
2. Name `ChunkBreakImpulse` (AGTMudPatch, 50,000 kg cm/s = 500 N s), the density multipliers (`FGTDeformProfile::ChunkDensityScale`
   in `MudVariantDefaults`), and the size range (`MudChunkSizeMinCm` / `MudChunkSizeMaxCm`, 20-50 cm).
3. The cost: one simulated static mesh component per chunk (L_MudVariants: 6 / 10 / 16 / 11 per patch, 43 in all; at most 48 a patch,
   64 awake in the world); `gt.Mud.Chunks 0` for the A/B.

### Results (2026-10-09; no game and no foreign Unreal at any run; no cost or timing measured)

- **GrandTour.Mud.Chunks** on L_MudVariants' patches: Firm 6 / Standard 10 / Deep 16 / Stony 11 chunks, each exactly its target (282.6,
  240.9, 266.8, 267.3 m^2 of candidate ground); sizes 20.0-48.3 cm, size CV 0.28-0.32; nearest-neighbour CV Firm 0.41, Standard 1.14,
  Deep 0.58, Stony 1.41; no chunk on S over 0.55, within 1.5 m of the rim, beyond 6 m of the line or closer than a 5 cm edge gap; all
  asleep on the ground. A wheel's footprint 2 cm clear leaves a chunk, 2 cm into it breaks it (the field takes its exact volume, 5 clods);
  the chassis at 0.9x / 1.1x ChunkBreakImpulse pushes / breaks; 140 woken, 64 stay awake; six chunks dropped 5 cm sleep at 0.37 s on
  their hulls; gt.Mud.Chunks 0 leaves no chunk and the fields as they were. The whole table is in VEHICLE_BUILD_SYSTEM 97.
- 15 of 15 Mud and Snow tests at gt.Mud.Chunks 1 and at 0, CRC 8e0aad06 both times; the full suite 28 PASS.
- **The check** (39 frames a second, the drive through to 200 m): breaks by wheel Firm 1, Deep 3, Stony 2, one Stony chunk pushed by the
  body and broken landing (5.7 m/s); 3667 / 0 / 21036 / 17619 cm^3 deposited; nothing lost; at most one awake at once. Deep's ground
  luminance 0.0323 (0.0324 with gt.Mud.Chunks 0 in a second run: the churn, not the chunks). New pictures: `Chunks_Before.png`,
  `Chunks_After.png`, `Chunks_Close.png`, `Chunks_Firm.png`.
- **L_Leg03** (the terrain test): 17 chunks on its bog at gt.Mud.Chunks 1; the bog run and the escape run at 0 (escape forward 8.4 m).
- **Rebuild**: the C++ (`bash Art/build.sh`), the headless Blender `Art/Blender/build_mud_chunks.py`, `& Art/import_mud_chunks.ps1`,
  then `& Art/setup_mud_variants.ps1` (or `setup_live_mud_drive.ps1`) for M_GT_MudChunk.

## Crisp deformed mud and moving rut water (MW1, 2026-10-12)

docs/MUD_WATER_SURFACE_PLAN.md MW1 (the owner: "mud and water are reading way too smooth - the water is too static"); the build
notes, numbers and pictures are in VEHICLE_BUILD_SYSTEM 106. M_GT_Mud gains a crisp, non-sliding detail on moved mud and steep
banks, a slighter fresh sheen (FreshWet 0.12) and broken highlights on wet mud (roughness +-0.08 noise, wet floor 0.5); SlideUV
stays 1.0 (the diagnosis put the smeared walls on the parallax, not the slide). M_GT_MudWater gains the wind ruffle with moving
gusts, calmer shallow edges, settled roughness 0.2-0.3 and drifting mottle, froth and flecks. Rings spread on rut water round
moving wheels and at each footstep.

### Switches (console, 1 = on, the default)

| Switch | 0 does |
|---|---|
| `gt.Mud.DeformDetail` | no deformation detail (MPC_TrackPaint `MudDeformDetail`) |
| `gt.Mud.WaterMotion` | the rut water before MW1 exactly (MPC_TrackPaint `MudWaterMotion`; needs gt.Mud.PBR 1 to show) |
| `gt.Mud.WaterRings` | no rings; the live ones vanish at once |

UGTMudWaterSubsystem writes the two MPC scalars when they change, so all three switch at once, in play. The look numbers are
parameters: M_GT_Mud `DeformTileMul`, `DeformTurnDeg`, `DeformStrength`, `DeformSlopeLo`/`Hi`, `RoughNoiseAmp`,
`RoughNoiseCm1`/`2`, `WetRoughFloor`, `FreshWet`; M_GT_MudWater `RuffleCm1`/`2`, `RuffleSlope1`/`2`, `RuffleSpeed1Cm`/`2Cm`,
`GustCm`, `GustSpeedCm`, `GustLo`/`Hi`, `EdgeCalmCm`, `EdgeCalm`, `SettledRoughMW`, `RuffleRoughMW`, `DriftLoCm`/`HiCm`,
`DriftPeriodS`, `DriftGradCm`, `Fleck*`; M_GT_WaterRing `RingOpacity`, `RingRough`, `RingDark`, `RingLight`.

### How to see it (the owner)

1. L_MudVariants, Play, drive into Deep (the old track's puddle is at about 137 m), get out and walk through the water.
2. Stand over the puddle: `gt.Mud.WaterMotion 0` / `1` (still against moving); walk through it with `gt.Mud.WaterRings 0` / `1`.
3. Look at a rut bank 2 m away: `gt.Mud.DeformDetail 0` / `1`; and `gt.Mud.POM 0` / `2` (the term the diagnosis found on the walls).

### MW1b (2026-10-12; VEHICLE_BUILD_SYSTEM 107)

No parallax on walls, lips and moved mud (M_GT_Mud `PomFlatLo`/`Hi` 10-22 deg of the field's slope and the moved-mud mask); the mud
matte toward a low sun (`MudDryRoughLo`/`Hi` 0.8-0.95, `MudWetBandLo`/`Hi` 0.62-0.8, `WetRoughFloor` 0.62, `MudSpecOcclusion` 1: Specular
0.5 x AO^2); Deep's slice softened (`DeepNormalScale`, `DeepAOScale`, `DeepPomScale` 0.5). The rut water's drift is one direction per
patch and its ruffle isotropic (the churned pool's swirl marks); churned water ripples at `ChurnRippleSlope` 0.15. No new switch:
`gt.Mud.POM 0` / `2` now changes only flat, unmoved mud.
