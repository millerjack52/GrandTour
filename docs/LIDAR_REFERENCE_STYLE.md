# LiDAR reference style — RS1, 2026-11-05

The owner selected L_LidarStudy for the dense, varied, colourful direction in
`Art/References/ReferenceStyle/2026-11-05.jpg`. This updates the earlier muted
grass palette direction. Southland plants, surveyed layout and grass-only paddocks
remain the setting. This is a material/lighting pass across the map and a bounded
planting study along the first 160 m around the access entrance.

## Authored changes

- Near grass, distant grass and pasture terrain share one continuous world-space
  colour field: fresh green, cooler green patches and smaller warm straw patches.
  The final revision uses two scales of smooth irregular patches; the first
  sine-based trial produced visible bands and was superseded.
- Rank grass gets a warmer mix. Existing blade root-to-tip brightness, wind,
  contact displacement, removal and distance fading remain connected.
- Map-owned beech/fern foliage has lighter tints and softer crown normals.
  The distant canopy cards use the matching colour treatment. Bark is unchanged.
- Sky light intensity is 2.0, previously 1.5. No global saturation filter or
  graphics preset reduction was used.
- The final access study adds 219 instanced plants from seven existing meshes:
  coprosma A/B, gorse, broom, verge tussock A/B and thistle. Woody centres have
  lower planting around them, with gaps between groups. Positions are deterministic.
  Reapplication replaces only actors labelled `LidarStudy_RS1_*`.
- Added roots are outside the three paddock polygons and at least 240 cm from
  road centre lines. Steep candidate positions are rejected; living roots are
  seated against the final relief tiles. Added plants have no collision or shadows,
  with a 100–160 m cull range. Existing tree collision is untouched.

## Source and application

`Art/Unreal/lidar_reference_style.py` holds the palette, material changes and
bounded placement. Run `powershell -NoProfile -ExecutionPolicy Bypass -File
Art/lidar_reference_style.ps1` from C:/GrandTour. It waits for the existing Unreal
reservation, backs up affected assets, applies, saves, reloads, checks invariants
and exits. Never run a second editor or kill an occupied one.

`Art/Export/LidarStudy/Place/reference-style.json` activates preservation hooks in
`lidar_grass_gs3.py`, `lidar_level_polish.py`, `polish_lidar_place.py` and the full
`install_lidar_place.py` rebuild. The standard Prepare → Install → Polish → Water
→ Check workflow therefore retains this treatment. No terrain regeneration was
run for RS1 itself.

The original pre-RS1 binary backup is
`Saved/LidarAuthoringBackups/RS1-1793911144198362000`. Later revision backups are
recorded in their install reports; use the first backup for the original look.
Backups contain the map, affected base materials, map-owned foliage instances,
CanopyKit and GrassGS3. Unrelated work was not reset or committed.

## Evidence

`Saved/LidarAuthoringQA/RS1/` holds install/process reports and final validation.
The first pass is preserved as `install-first-pass.json` and
`process-first-pass.json`. Install assertions compare the terrain output digest,
original forest/understory counts and grass streaming properties before and after,
then check them again after reloading the saved map.

Matched standalone views use `gs3-poses.json` with the unchanged v6 saved graphics
preset at 1600×900, TSR 75%. Baseline is `PF60-palette-before-*.png`; the banded
first trial is `PF60-palette-after-*.png`; final captures are labelled
`PF60-palette-final-*.png`. Corresponding `playperf-*-summary.json` files describe
the short stationary sampling windows. They are not a full driving benchmark or
a claim of locked 120 fps.

Final stationary samples (290 frames per view; milliseconds):

| View | Baseline mean frame | Final mean frame | Baseline mean GPU | Final mean GPU |
|---|---:|---:|---:|---:|
| Paddock middle | 12.123 | 11.833 | 11.046 | 11.016 |
| Paddock gate | 9.733 | 9.661 | 9.153 | 8.997 |
| River | 12.965 | 12.703 | 12.421 | 12.192 |
| Access | 14.840 | 14.532 | 14.344 | 14.010 |

These short samples show no material cost increase in the measured views. The
small reductions are within run-to-run variation, not an optimization claim.
Final frame-time p95 values are 12.979 / 10.816 / 14.794 / 16.513 ms respectively.
Both installs and all three standalone capture processes exited 0.

The existing GrassCheck verifies near/far coverage, streaming consistency, grass
bending/removal and muted vehicle audio. Final reports and limitations are recorded
in `Saved/LidarAuthoringQA/RS1/review.json`. Owner visual and driving acceptance
remain open. The result is an initial step toward the supplied reference; crown
shape variety and larger meadow-flower groupings have not been redesigned.

## RS2 — muddy and gravel roads, 2026-11-05

Owner follow-up: the vegetation looks better; extend the treatment to muddy and
gravel roads. `Art/Unreal/lidar_road_style.py` changes only `RD1Gravel` and
`LT4Final` colour programs in the map-owned M_Terrain/M_Detail materials.

Gravel uses a slightly warmer, lighter grey binder, compressed pebble contrast,
softened wheel lanes and restrained metre-scale colour variation. Existing road
coverage and grass transition masks are retained. Mud retains the native surface
pigment but lifts dark midtones; live negative displacement darkens worked ruts
while positive displacement slightly lifts churned lips. Wetness sheen, normal
detail and geometry remain controlled by the existing programs.

This pass does not rebuild or save the map, add geometry, change surface physics,
or adjust lighting. The map SHA-256 is asserted unchanged. Every other custom
shader program and all material property output connections are checked before
and after, including displacement, normals, roughness and opacity. Reapplication
is checked for stable node counts and identical material signatures.

Run `powershell -NoProfile -ExecutionPolicy Bypass -File Art/lidar_road_style.ps1`
to apply; add `-Check` for saved-material validation, surface probes and a short
low-range mud drive. The guarded launcher reserves the single Unreal slot. The
normal RS1 apply pass and track-detail installer retain RS2 when
`Art/Export/LidarStudy/Place/road-style.json` exists. These hooks were syntax-checked;
the entire terrain rebuild pipeline was not rerun for this material-only pass.

Original material backups are under
`Saved/LidarAuthoringBackups/RS2-1793912450057048800`. The first attempt triggered
temporary missing-input shader errors while extending a connected custom node;
the strict launcher correctly rejected that attempt despite final in-memory
assertions passing. Its report and log remain under `Saved/LidarAuthoringQA/RS2/`
as `*first-input-edit*`. The source now builds missing inputs on a fully wired
replacement node before connecting it to the output chain. A clean reapply passed
without shader errors, and the standalone after capture loaded the saved materials
without shader errors. Do not treat the initial attempt as a clean install.

Matched captures are `PF60-roads-before-*.png` / `PF60-roads-after-*.png` in
Art/Export/LidarStudy/Place, with the same four poses and v6 graphics preset.
The 290-frame stationary GPU means were 12.226/13.865/13.495/14.452 ms before and
11.720/13.493/13.128/14.060 ms after (river, bog214, bog552, access). These short
ordered samples show no observed cost increase; the small reductions are not a
performance-improvement claim. Deep canopy shadows remain; this is not a global
exposure or artificial glow adjustment.

Final validation, limitations and preserved screenshots are recorded in
`Saved/LidarAuthoringQA/RS2/review.json`. Owner visual and driving acceptance remain
open. The short mud drive is a regression smoke check, not full handling acceptance.

## RS3 — riverbank plant variety, 2026-11-05

The river preview exposed repeated fern rosettes at similar heights. The bounded
river reach now replaces selected non-colliding low foliage with nine plant meshes:
two tussocks, two rushes, a smaller crown fern, kiokio, two coprosma shrubs and flax.
Mixed beds use varying radii, dominant species and companion plants, with sage,
olive, deep green and occasional golden grass tints. Root spacing, mature heights
and width vary; deliberately open gravel separates beds. The initial sparse pass
was rejected visually and replaced with 270 fuller clusters (2,354 plants).

The study is an ellipse centred at (-48000, -34600) cm, with 65/75 m radii.
It changes only selected living ground plants there, retaining original low plants
outside it, trees, solid objects, ground and water. Plants respect a 270 cm road
centre clearance and dry ground above the river. Original instance transforms
outside the region are hashed before and after removal. Original seed positions
are persisted in `Art/Export/LidarStudy/Place/river-plant-seeds.json` for repeatability.

Run `Art/lidar_river_plant_variety.ps1` to install, save and reload; run
`Art/review_lidar_river_plants.ps1` to verify saved transforms and capture the views.
Both reserve the single Unreal slot. RS1 and the river-detail installer retain this
pass when `river-plant-variety.json` exists. Full terrain rebuild hooks have only
been syntax-checked. The native plant kit is unchanged; four owned material
instances live under the LiDAR map's RS3 folder.

Original map backup: `Saved/LidarAuthoringBackups/RS3-1793913658946374900`.
The first transform comparison incorrectly compared construction doubles against
Unreal's stored ISM precision. Validation now compares actual instance readback.
The sparse-pass capture process also returned an access-violation exit code during
shutdown after producing its images; that process is not counted as a clean check.
Evidence and final status are in `Saved/LidarAuthoringQA/RS3/review.json`.

## RS4 — steep-bank material, 2026-11-05

The existing rock colour node sampled only world XY, stretching the texture on
steep slopes. `lidar_slope_style.py` replaces that node's code in M_Terrain and
M_Detail with geometric-normal-weighted world XY/YZ/XZ projection. The existing
rock atlas mask and upstream road/soil inputs remain in place. Steep faces gain
warmer stone, broad irregular earth patches and moss biased toward gentler parts
of the face. Flat rock retains its original colour sample. Revision rs4-2 restores
more source-texture contrast after the first preview looked too smooth.

This is a material pass; it does not reshape terrain, move plants, save the map,
or alter water/road physics. Every other custom shader program and all final
material output connections are checked unchanged, including the RS2 road colour
programs. The map SHA-256 is checked before/after and in the fresh runtime process.
Repeated application must retain node count and signatures. Original material
backup: `Saved/LidarAuthoringBackups/RS4-1793916564645915000`.

Run `Art/lidar_slope_style.ps1`; add `-Check` for saved-material checks and river
captures. The RS1 final pass retains RS4 after a rebuild. The RS2 checker recognises
the intentional rock-code change only after verifying RS4's saved code and protected
graph signatures. These hooks are syntax-checked; a full terrain rebuild and a new
performance benchmark are outside this pass. Projection uses three rock texture
samples instead of one, with an early-out outside the rock mask.

The first installation saved valid materials but returned an access-violation code
at shutdown; its subsequent fresh readback/capture exited 0. Preserve that distinction
in `Saved/LidarAuthoringQA/RS4/soft-first-*-process.json`. Final evidence, process
statuses and reviewed images are in `Saved/LidarAuthoringQA/RS4/review.json`.

## RS5 — how plants sit on banks, 2026-11-05

Owner correctly identified that the preceding planting reused level-ground rosettes
and upright root bases on steep faces. `lidar_bank_planting.py` now treats root
support, growth direction and habit separately. In the same river study ellipse:

- Below 18 degrees, original transforms are preserved exactly.
- Low bank ferns use the existing kiokio meshes, which already contain arched outer
  fronds and hanging tips. Their long axis faces downhill, their cross-bank footprint
  narrows, and their crown leans partly out from the bank. This is not a universal
  rotation of every plant to the surface normal.
- Large shrubs/flax need gentler support; tree-fern trunks stay nearly upright and
  are removed from unsupported faces above the placement limits. The first saved
  pass removed 65 such tree ferns and replaced 253 low fern clumps.
- Tussocks lean slightly outward; moss and root mats flatten and follow the slope.
- Eight points around each root crown are seated inside the actual ground. Frond
  tips may overhang; their entire bounding box is not treated as a root footprint.

Local and broader slope samples govern support, with less planting on exposed
faces. The art rules are a placement approximation, not a botanical growth model.
Kiokio's river-bank/cliff habitat and erect or pendulous fronds are described by
[NZPCN](https://www.nzpcn.org.nz/site/assets/files/0/13/746/8052018_102452_a_m_.pdf).

Run `Art/lidar_bank_planting.ps1` to apply, save and reload; run
`Art/review_lidar_bank_planting.ps1` for saved transform/root-support checks and the
same river cameras. The RS3 generator reapplies this fitting after rebuilding its
plant groups. Per-source tags prevent cumulative tilt/scale and preserve owned
replacement fern batches on repeat application. Rebuild hooks are syntax-checked;
the full terrain installation was not rerun.

Outside-reach and flat-ground transforms are hashed before and after. Terrain,
water and material programs are retained. Removing unsupported tree ferns also
removes their existing collision instances; no new colliding plants are added.
The original map backup is `Saved/LidarAuthoringBackups/RS5-1793917649476001900`.
Final evidence and limitations: `Saved/LidarAuthoringQA/RS5/review.json`.

2026-11-05 RS6 - user-selected rocky river bank
The river bend now uses 21 partly buried angular outcrop pieces in seven overlapping
formations. 84 upright rush, tussock, compact shrub and flax clumps are rooted on
actual collision-traced rock ledges and seams. Flat fern rosettes are cleared from
the outcrop footprints. 55 obstructing tree visuals and their 55 trunk colliders
were removed together; all other instance transforms are preserved exactly.
The map-owned M_BankStone uses the same world-space rock texture, scale and
stone/earth/moss pigment code as RS4's bank. It replaces the imported pack's pale
rock and bright green caps. New ledge plants use MI_NZ_Foliage_Bush.
No DEM, road, water, terrain material or lighting change belongs to this pass.
Four root probes per plant are buried at least 4 cm into rock. Outcrop support
samples are embedded by 55 cm; full rock bounds remain at least 15.26 m from road
centreline segments. Tree/collider root pairs are checked after clearing.
Recipe: Art/Unreal/lidar_rocky_bank.py. Guarded repeat install:
  powershell -File Art/preview_lidar_rocky_bank.ps1 -Install
RS3 reapplies RS6 after RS5 when rocky-bank.json exists; RS3/RS4/RS5 review scripts
recognise the RS6 saved checkpoint. Full terrain regeneration was not rerun.
Backup: Saved/LidarAuthoringBackups/RS6-1793920301782955600/L_LidarStudy.umap
QA: Saved/LidarAuthoringQA/RS6/install.json, validation.json and Final-*.png.
Visual evidence is from the editor viewport, not a new driving/PIE benchmark.
2026-11-05 RS6 REJECTED by owner after visual review.
The oversized, separated boulders and perched shrubs do not meet the requested
riverbank quality. Restore the pre-RS6 saved map; archive the rejected map and
disable rocky-bank.json so normal regeneration does not reapply this attempt.
RS6 code and screenshots remain as rejected experiment evidence, not approved art.
Next design work should prove one small bank section first: embedded, connected
rock structure, crevice-rooted vegetation, and material/light coherence. Do not
repeat the rejected boulder row across the river reach.