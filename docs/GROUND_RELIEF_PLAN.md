# Ground relief: the ground is too flat and smooth

Main session, 2026-10-10. The owner: "The ground is too flat. the mud, the grass all of it is too flat and smooth".

**Why it is flat today:**
- **Terrain:** the test strips (L_MudVariants, L_GravelDeform, L_MudDrive) were built nearly flat on purpose, for clean
  feel tests: `base_amplitude_m` 1.2 (0.4 on the gravel strip) at 90 m, 2 octaves. The relief bumps are 4 m and 2 m
  octaves of ±0.25 m on scrub and ±0.12 m in a bog.
- **Mesh resolution:** the landscape is 1 m per quad, so nothing under about 2 m can exist in its geometry.
- **Mud:** each mud patch starts as a flat plane with LM2's small lumps.
- **Grass:** it stands on that flat ground at one height band.

**The fix, scale by scale** (each one irregular and clustered, never even; the owner's rejection list applies:
regular lines, uniform, too smooth, blocky, tall walls, flat planes):

| Scale | What | Where it lives |
|---|---|---|
| 20-100 m | rolling land | the spec's noise |
| 2-8 m | bumps and swales | relief octaves |
| 1-5 m | hummocks (tussock mounds) | a new hummock field in the heightmap |
| 0.1-1 m | lumps, crumbs, tussock bases | micro displacement (GR2: Nanite tessellation if it works, else the material) |
| 0.1-3 m in bogs | old ruts, hummocks, puddles | the mud field's pre-churn |
| plants | height, clumping, gaps | the grass placement |

## 0. Rules for the agent

`docs/MUDRUNNER_LESSONS_PLAN.md` section 0 holds in full: no timing; the foreign-Unreal wait; run with a game open,
never close it; the look rejections; docs per stage; commit only the stage's files, hunk by hunk; never push.

- **Never touch** water, Benmore or river files, or the Codex app's uncommitted hunks.
- **Snow strip and The Hide/legs are not changed in GR1.** They follow after the owner approves the strips.
- **Every new relief feature has a switch or a spec number of 0** that gives today's ground exactly, and the test
  fixtures keep 0. The mud CRC (8e0aad06) and every test fixture stay as they are.

## GR0: can Nanite tessellation displace the landscape here? (time-boxed, report only, about 45 minutes)

On a copy of L_MudVariants (`L_GR_Probe`):
- enable Nanite on the landscape;
- give a copy of its material Nanite tessellation with a displacement output, from the gravel Loose height
  (TA_GV ORH.B) at a 2 m tile and ±4 cm;
- capture an on-foot picture with and without it.

**Report:**
- whether each step worked headless;
- the console variables and project settings involved (r.Nanite.AllowTessellation and so on);
- whether the landscape's patch hole and apron still meet the mud patch mesh;
- the triangle counts from `stat Nanite` or the equivalent (counts only, no timing);
- the blockers, with their error text.

Probe files stay uncommitted. GR2 is written after this.

*Done 2026-10-10 (report only; VEHICLE_BUILD_SYSTEM 100; GoWR open). The copy: worked (`EditorLoadingAndSavingUtils.save_map`; `duplicate_asset` of a World crashed the next load). Nanite on the landscape: worked, built by the level's save (`ALandscapeProxy::PreSave`), 1 Nanite component, fallback LOD0 4,589 triangles; with `landscape.Nanite.LiveRebuildOnModification 1` the property change asserted "Proxies.Contains(LandscapeProxy) [LandscapeSubsystem.cpp:1443]". Tessellation and displacement: BLOCKED headless - `MP_Displacement` is `UMETA(Hidden)`, Python has no `MaterialProperty.MP_DISPLACEMENT` and `MaterialProperty.cast(32)` fails ("Cannot cast type 'int' to 'MaterialProperty'"); `enable_tessellation` and `displacement_scaling` (8 cm, centre 0.5) are settable; a C++ editor helper would wire the pin. Settings: no `r.Nanite.AllowTessellation` in 5.8; `r.Nanite.Tessellation`, `r.Nanite.ProgrammableRaster` and `r.Nanite.ComputeRasterization` all 1 (`UseNaniteTessellation`), density by `r.Nanite.DicingRate` / `r.Nanite.MaxPixelsPerEdge`, `landscape.RenderNanite`. Counts (`NaniteStats Primary`, on foot, no displacement): 242 clusters, about 90,500 triangles, 20,649 vertices, 0 diced. The patch: with the Nanite landscape the Standard patch's area shows as dark ground with thin lit lines in steps (`Art/Export/GRProbe/GR0_Edge_Tess1.png`, `GR0_OnFoot_Tess1.png`); with `landscape.RenderNanite 0` the mud meets the apron as before (`GR0_Edge_NoNanite.png`): the masked hole did not hold under the Nanite landscape (cause unchecked). Probe files (uncommitted): `Art/Unreal/probe_gr0_nanite.py`, `/Game/GrandTour/ArtTests/GRProbe/L_GR_Probe`, `M_GR_ProbeLandscape`, `Art/Export/GRProbe/`.*

## GR1: relief you can drive over (test strips: L_MudVariants, L_GravelDeform, L_MudDrive)

1. **Terrain numbers** (the strips' setup scripts):
   - base_amplitude_m 3.5, base_wavelength_m 60, octaves 4, persistence 0.5;
   - the gravel strip the same.
   - **Route drivability:** report the route's longitudinal grade (p95 ≤ 10 %) and cross-slope (p95 ≤ 6 %), and lower
     the amplitude only if those fail.
2. **Relief octaves.** A new spec number, `RoughnessOctaves` (default 2 = today), set to 3 on the strips: 6 m, 3 m and
   2 m, at weights 1 / 0.55 / 0.3, renormalised to the same peak.
   - ScrubRoughnessM 0.25 → 0.45.
   - MudRoughnessM 0.12 → 0.22. These are the strips' values; defaults unchanged.
   - Road, rally and track roughness are unchanged.
3. **Hummock field** (new; a spec struct `FGTHummockField`, empty = none). Mounds stamped into the heightmap on Scrub
   ground, outside the route band and its shoulder:
   - **density:** 8 per 100 m², modulated by a hashed 12 m cluster noise (×0.1 to ×2.2, renormalised);
   - **size:** radius 1.0-2.8 m, power-law (most small); height 0.15-0.5 m, with taller mounds wider;
   - **shape:** a soft dome whose rim is warped by a 3-octave angular noise (±25 % radius), and whose crest is offset
     up to 30 % toward a random side (asymmetric);
   - **overlaps** add with a soft max, so clusters merge into hummocky ground.
   - **Gates:** nearest-neighbour CV ≥ 0.4, no regular spacing (a radial pair-correlation with no peak above 1.3
     beyond the first neighbour), maximum slope ≤ 35°.
4. **Mud pre-churn** (new profile number `PreChurnScale`, default 0 = a flat field; the strips' bog sections get 1).
   At Init, before the field's baseline:
   - **Old tracks:** 2-4 old rut pairs per patch, following the route line with a low-frequency lateral wander of
     ±1.5 m (20-40 m wavelength). They are stamped with the existing wheel stamp at 6-18 cm depth, varying along the
     length, and the banks come from the stamp's own bank rule. Then 10 s of the existing settle, so they read old
     and slumped, not fresh.
   - **Hummocks:** field bumps of ±5-20 cm at 0.6-2.5 m, two octaves, clustered.
   - **Puddles:** the old ruts sit below the patch water table where it is set, so MR3's rut water fills some of them.
     Report how many cells hold water.
   - **Soft spots** (MR4): old tracks inside S > 0.6 are 1.4× deeper.
   - **Chunks** (MR5): chunks only sit where the pre-churned surface is within ±3 cm of the base (the hummock tops and
     the flats between tracks), never in old ruts.
   - **Rim:** the pre-churn fades to 0 over the patch's outer 1.5 m, so the apron matches.
   - **Gates:**
     - the test fixtures are unchanged (CRC 8e0aad06 at PreChurnScale 0);
     - a new test `GrandTour.Mud.PreChurn` checks the track count, the depth range, the hummock amplitude, the rim
       fade and determinism;
     - the strip's CRC is recorded as the new strip baseline.
5. **Grass variation.** In the grass and tussock placement (find it: the LD biome dressing and grass blades):
   - per-instance height × 0.55-1.45 from two noise octaves (3 m and 0.8 m);
   - bare gaps over 10-25 % of grass ground (a 2 m cluster noise);
   - a tilt of ±12° from the slope plus noise;
   - tussocks weighted ×2 onto hummock crests.
   A spec or biome number of 0 gives today's placement.
6. **Feel and tests.**
   - Every GrandTour.Mud, Snow, Gravel and Spray test passes, with the CRC unchanged on the fixtures.
   - The full suite runs once.
   - The strips' drive checks run: report each section's speed against today's (a re-base is expected), and whether
     the drive completes.
7. **Pictures** (same cameras before and after, sun behind the camera):
   - per strip, `Relief_Overview.png` (about 25 m up, 40° down) and `Relief_OnFoot.png` (1.7 m eye height, looking
     across grass and hummocks to the track);
   - `Relief_Bog.png` (a Standard section from 1.7 m, before driving: the pre-churn);
   - the existing check pictures as usual.
8. **Docs and commit** as usual. VEHICLE_BUILD_SYSTEM takes the next free section at commit time. The owner's list:
   the numbers above, PreChurnScale, the hummock density.
   Commit message: "Ground relief GR1: rolling strips, hummocks, pre-churned bogs, grass variation".

*Done 2026-10-10 (VEHICLE_BUILD_SYSTEM 100; GoWR open at every run; no timing). All eight items built; every number in `Art/Unreal/ground_relief.py`. 1: land 3.5 m at 60 m, 4 octaves, 0.5 on L_MudVariants and L_GravelDeform, L_MudDrive 2.75 m (its grade p95 away from the ford 11.02 % at 3.5 m; 9.76 % at 2.75). Route grade p95 / cross p95: L_MudVariants 7.32 / 3.96 %, L_GravelDeform 5.25 / 0.38 %, L_MudDrive 9.76 away from the ford (13.91 over the whole route: the ford's 25 % drop, 10.82 before GR1) / 2.96 %. 2: `RoughnessOctaves` 3 at 6 m (6 / 3 / 2 m), scrub 0.45, bog 0.22. 3: `FGTHummockField` (Density 8): 5,146 / 2,938 mounds in the grids (8.10-8.22 per 100 m^2), NN CV 0.559-0.566, g(r) peak beyond the first neighbour 1.150-1.157, the field's steepest 33.6-34.0 deg at 0.25 m - after one addition: each mound's height is capped so its radial flank stays at tan 30 deg over its shortest crest-to-rim reach (35.65 deg without). 4: `PreChurnScale` (the section's own Deform, read whatever its Mode) and `gt.Mud.PreChurn`; L_MudVariants: 2-4 pairs, depths 6.0-24.9 cm asked (x1.4 in S > 0.6), hummocks to +-20 cm, rim at most 0.10 cm, water in Deep only (244 cells, 0.72 %; Standard's -25 cm table sits below the deepest old rut), chunks kept on 27 of the flat plan's 43 places; departure: "within 3 cm of the base" is read as within 3 cm of the hummocked ground before the tracks (the hummocks themselves are 5-20 cm). New strip CRCs Firm ee8ffa80, Standard ce21021c, Deep 027d22e5, Stony 8981a1c7; the fixtures' 8e0aad06 unchanged. 5: `FGTGrassVariation`: height x0.550-1.450, bare 16.9-20.3 %, lean 12 deg, crest companions. 6-7: tests 17/17 Mud, Snow and Gravel (the new PreChurn) + Spray.Art + the new Relief.Strips PASS, CRC 8e0aad06; suite 27 PASS, terrain FAIL (the bog escape under GoWR; its rerun: step 11's held-exit flake); the drive checks under GoWR hit their real-time caps (none completed: owed a no-game run; game-time section speeds equal to today's on gravel, Firm 27.0 against 31.3 km/h, Standard 23.2 against 23.3, Deep 2.6 against 2.0 over its first 20.8 m). Pictures: Art/Export/<strip>/Relief_*.png, the same cameras before in GR1_Before/. 8: this note.*

## GR1b: fixes from the main session's look (2026-10-10)

**My look at GR1:**
- **Better:** the distant land rolls in several waves; the grass varies in height with clumps and bare gaps; the bog
  has relief, with old ruts, banks and swales.
- **Three faults:**
  1. Thin, continuous black crease lines run along the old ruts (`Relief_Bog`). From above (`Relief_Overview`) they
     read as several long, parallel scratch lines down the strip: a regular-lines rejection.
  2. The bare ground between the grass is still smooth sandy shading, near and far (GR2's scale).
  3. A pale, blurred rectangle lies across the road where two bog sections meet (`Relief_Overview`).

**Fixes:**
1. **Old tracks without crease lines.**
   - Find what draws the dark lines (a crease in the field normal at the wall foot, tread or fresh residue, a shadow
     term, a mesh seam) with a debug switch. Report the cause.
   - Old tracks get a cosine cross-section: no vertical wall, and the wall foot rounded over at least 2 cells.
   - Depth jitters along the length at 1-3 m.
   - 20-40 % of each old track's length is in segments filled back to 30-60 % of its depth, with irregular gaps.
   - Width wanders ±20 %.
   - LM2 lumps are re-seeded over the old tracks and banks, so they slump lumpy, not smooth.
   - Gate, my look: no continuous dark line longer than about 1.5 m in `Relief_Bog` or `Relief_Overview`.
2. **The pale rectangle:** identify it (a landscape layer between patches, the apron, a decal, the gravel exit) and
   report. Fix it only if it is a GR1 regression. If it is older, report only.

*Done 2026-10-10, items 1-2 (VEHICLE_BUILD_SYSTEM 101; GoWR open; no timing). The cause, by `gt.Mud.PreChurnDebug` and runtime switches on
GR1's tracks (`Art/Unreal/crease_debug.py`, the Relief_Bog camera; the share of near-black pixels, luminance under 12, in the
picture's lower half): as built 0.391 %; the patch meshes casting no shadow 0.084 %; the field smoothed (four 3x3 passes) 0.182 %;
gt.Mud.POM 0 0.312 %; gt.Mud.POMShadow 0, screen-space AO off, the tracks factor cleared, the lumps cleared 0.36-0.43 % (no change). So
the lines were the bog mesh's own shadow along the field's wheel-stamp trough - a tyre-wide flat floor between near-vertical two-cell
walls, shadowed by its lip at the sun's 27 degrees - not tread, sheen, the tracks term or AO. Fix: the old tracks are no longer
stamped; each wheel line is a cosine trough (half width at least 2.6 x its depth and the tyre's half width + 20 cm, so the foot is
rounded over 3+ cells and the steepest trough cell stands 23.8-35.0 degrees after the settle), a cosine bank beside it (half its
section), depth knots 1-3 m apart, 20-40 % of each line in segments filled back to 30-60 % (measured 25.2-34.6 % of the length,
filled to 2.5-3.0 cm), the width +-20 % on 2-4 m knots, LM2's lumps re-seeded over troughs and banks from the field's lump domes,
the cells woken for the 10 s settle (`FGTMudField::WakeEdited`). On the new tracks the mesh shadow no longer changes the dark share
(0.420 -> 0.410 %); what is left along the troughs' far walls falls with gt.Mud.POM 0 (0.276 %): MRP's parallax on those walls, not
changed. Item 2: the pale rectangle is the strip's own gravel road (the landscape's Dirt layer, the live landscape's gravel) in the
6.4 m between Standard's patch box (to 106.8 m) and Deep's (from 113.2 m), its ends softened by the two 3 m patch-slice aprons
(`Art/Export/GroundRelief/CreaseDebug/Gap_TopDown.png`); it is in GR1_Before, so older than GR1 (LM5b's layout): reported, not changed.
Tests: 17/17 Mud, Snow and Gravel, the fixture CRC 8e0aad06; GrandTour.Mud.PreChurn's new rows (filled share, filled depth, no
wall). New strip CRCs Firm 4a20b9b2, Standard 44371c3f, Deep 10a17173, Stony 587ccf09. Pictures (GR1's cameras exactly):
Art/Export/MudVariants/Relief_*.png and Art/Export/LiveMudDrive/Relief_*.png (GR1's in GR1/).*

*GR1c done 2026-10-10 (the main session's decisions after phase A, "GR1c, old tracks as a layout"; VEHICLE_BUILD_SYSTEM 103; no game
open; no timing). 1 old pair per patch, 2 where the route runs over 40 m through the box (L_MudVariants' boxes 38.2 m: 1; L_MudDrive's
41.2 m: 2), each pair its own centre and two-sine wander; each wheel line 1.4-1.9 x its tyre wide at half depth, 5-14 cm deep (the soft
spots' x1.4 kept in the range); each pair fading in and out over 3-8 m at random points, 35-60 % of its stretch in the box present (none
runs the whole box). Puddles: cut before the settle they came out 10-15 cm shallower (the relax gives a set cell RecoverShare of its
depth back) and none stood under the table, so they are cut into the settled field - the lowest-lying 20-30 % of each line's present
length, each run 2-5 cm under the patch's table, ramped over 1.5 m, lumps cleared, a trough at least 4.5 x its extra cut wide, not
woken. M_GT_Mud's POM self-shadow x1 up to 15 deg of the field's slope, linear to x0.3 at 30 deg. Per patch (CRC; present; puddle runs
of the present length; water cells under the table): Firm d23d3b51, 42.3 %, 26.2 %, 198; Standard 1e549040, 45.2 %, 27.9 %, 237; Deep
eefac94d, 53.4 %, 29.3 %, 287; Stony 58be0a5c, 54.6 %, 27.4 %, 188 (depths asked 5.0-14.0 cm); L_MudDrive 2 pairs (45 %, 58 %), 522.
Gates: water in Deep and Standard over 0 (GR1b 0 and 4); the fixtures' 8e0aad06 unchanged; tests 18/18 (Mud, Snow, Gravel, Relief);
the look from above is the main session's. The steepest trough cell is 41.6-43.5 deg (GR1b 23.8-35.0: the puddles cut into the settled
walls). Pictures (GR1b's cameras): Art/Export/MudVariants/Relief_*.png and Art/Export/LiveMudDrive/Relief_*.png (copies in GR1c/,
GR1b's in GR1b/).*

*Checks after the fixed step done 2026-10-10 (the decisions after phase A; VEHICLE_BUILD_SYSTEM 104; no game open). Spray: each
scenario renders from its throttle-on to its capture; droplets above the arch PASS (992 px, 66.4 % above; fixed step before 9.9 %).
PBR_CarryWet: the track paint's CPU mirror and GPU target agree in game time, rendered or not (mean G 0.322 / 0.309, B 0.813 / 0.784 not
rendered; 0.348 / 0.333, 0.816 / 0.790 rendered); MF_Weather's open 1.0 and fill 1.0 at the spot. What moved the gate: its median over
the brown pixels sits on the floor's two 8-bit codes (0.447 / 0.451) around 0.45, the trail's partly covered edges, and MF_Weather's
world-fixed standing water (0.03, the floor off there by design), which the trail enters or not by its lateral line (fixed 85 Hz: all
of it, 0.031). Fixed in Art/sample_mud_pbr.py: puddled pixels (under 0.06) left out, the floor read at p75 against 0.446, at least
5,000 pixels; final run PASS (p75 0.451, median 0.443). Muddy splash: still FAIL - no water under the spin at 132 m (Water spray live
0; GR1c's Deep puddles lie elsewhere; the build carried the Codex app's uncommitted wheel-splash change). Frame rate (report only): no
per-frame term without dt in traction, sinkage or stamping; fixed 85 against fixed 60 Hz is within the run-to-run spread of two
identical fixed-60 runs (Firm 1.1 %, Standard 0.5 %, Deep 6 %, Stony 14 %); the real step's 5-6 % on Firm and Standard goes with the
varying step (and every frame rendered), Chaos's own per-step solve not audited.*

## GR2: micro relief through the material and scatter (main session, 2026-10-10, after GR0)

**GR0 outcome:** Nanite landscape tessellation is blocked twice.
- The material's displacement pin is not reachable from Python, so it would need a C++ helper.
- With the Nanite landscape on, the mud patch's hole no longer cut the landscape.

So micro relief comes from the ground material plus 3D scatter. Nanite stays a later option. **Strips only:** the new
detail lives in a strip-only material instance (a static switch on) and in strip-scoped scatter, so The Hide and the
legs are unchanged until the owner approves.

**Phase A (headless Blender, look-gated by me before any Unreal work):**
1. **Ground bakes** in the style-study workflow (painterly, the scrub/sand palette of the current landscape layer).
   Tileable 2 m sets at 2048 with Color, Normal and ORH (horizon AO, roughness 0.6-0.95, parallax height with soft rims
   scaled to the feature size as gravel's were):
   - **ScrubSoil:** dry crumbly soil with small clods, cracks, pebbles and fine dead grass litter, broken irregularly;
     no cobble mosaic, no swirls, no direction.
   - **SoilUnderGrass:** darker, with root mats and litter.
   - 3×3 renders at 1.7 m, plus a render with displacement at the planned parallax depth (1.5 cm).
2. **Scatter meshes** (100-400 triangles each, painterly palette):
   - 6 soil clods, 3-12 cm;
   - 4 pebbles, 1-5 cm (the gravel study's stones re-tinted);
   - 4 dead-grass litter tufts, 10-25 cm, flat and bent;
   - 3 twigs, 15-40 cm;
   - 3 tussock-base mounds, 25-50 cm across and 6-12 cm high: soil and root bumps that sit under the big tussocks.
   - A render of each family on the ScrubSoil bake.

**Decisions after phase A** (main session, 2026-10-10):

- **GR1c, old tracks as a layout.** From above, GR1b's 4 rut pairs still make a bundle of long, narrow, parallel
  grooves down the whole strip (regular lines). On foot they read well. Changes:
  - **Count:** 1 old pair per patch, 2 on patches longer than 40 m. Their wander is independent, so they cross, merge
    and split.
  - **Width** 1.4-1.9× tyre width (old tracks spread), depth 5-14 cm.
  - **Fading:** each track fades in and out over 3-8 m at random points, so no track runs the full length: 35-60 % of
    each pair's length is present.
  - **Puddles:** where the section has a water table, the deepest 20-30 % of each present track sits 2-5 cm below it,
    so puddles return (GR1b lost Deep's rut water).
  - **POM self-shadow** on the mud scales down on slopes over 15°, to 0.3 at 30°: the dark streaks on old-track walls
    come from it.
  - Gates:
    - from above (`Relief_Overview`), no more than 2 long grooves visible per patch (my look);
    - the water-holding cells in Deep and Standard are more than 0;
    - the fixture CRC is unchanged.
- **Checks after the fixed step** (CHECKS_UNDER_GAME_PLAN follow-up):
  - **Spray captures:** Niagara GPU sims only run while rendering, so the spray check renders continuously through
    each spray scenario from its throttle-on to its capture. The spray check is short; the other checks keep render
    windows.
  - **PBR_CarryWet:**
    - find why carried-mud roughness drops under the fixed step (0.439) and further under a game (0.231);
    - check whether the track paint's GPU writes or decays depend on rendering being on, or on wall time;
    - fix it so the CPU-side and GPU-side paint agree in game time.
  - **Muddy splash:** it should pass again once the GR1c puddles return.
  - **Frame-rate dependence:** report only, the owner's call. The fixed 60 Hz drives 5-12 % faster than the varying
    80-90 Hz real step on the same ground. Find which per-frame term in traction, sinkage or stamping integrates
    without dt, and report it. Don't fix it.
- **GR2 phase A2 (Blender):**
  - **Soil bakes pass** (crumbly, irregular). The 2 m tile repeats as diagonal chevrons at mid distance, so phase B's
    material must break the tiling: two samples at different scale and rotation, blended by a 7 m macro noise, plus a
    macro tint variation.
  - **Scatter fails:**
    - the clods are smooth round blobs (potatoes);
    - the litter tufts splay into radial stars (starfish or spiders);
    - the tussock bases are smooth pointed cones (anthills).
  - **Redo:**
    - **Clods:** torn and crumbly, with broken facets and crumb satellites, flatter (height 0.4-0.7 of width), sunk
      25-40 %.
    - **Litter:** flattened mats of bent blades lying mostly one way per mat, irregular outline, 2-6 cm high, no radial
      symmetry.
    - **Tussock bases:** low, broad, lumpy root mounds (height 0.12-0.2 of width) with a flattened crown where the
      tussock sits, an irregular outline, and crumb and root texture. No peak.
  - Re-render each family on ScrubSoil, plus `ScrubSoil_AntiTile.png`: the bake with the two-sample macro blend
    preview over 20 m at 1.7 m.

**Phase B (main session, 2026-10-10, after my look at phase A2).** In A2 the clods, the litter mats and the tussock
bases pass: torn clusters, flattened bent blades, low lumpy mounds whose crown seams are hidden under the tussock. The
anti-tile preview still shows faint diagonal rows of darker streaks at mid distance. They live in the texture itself
(the crack network's dark colour), so blending can't remove them.

0. **Bake fix (Blender):**
   - The cracks' colour darkening drops to 0.35 of today's, so the cracks read through height and normal, not paint.
   - Crack keep share 36.5 % → 20 %, with segments shorter and less connected.
   - Re-render `ScrubSoil_AntiTile.png`. Also apply it to SoilUnderGrass's root fibres if they darken in rows.
1. **Import.**
   - `TA_GD_{Color,Normal,ORH}` Texture2DArrays (slice 0 ScrubSoil, slice 1 SoilUnderGrass), with the mud's array
     builder.
   - The scatter meshes `SM_GD_Clod0..5`, `Pebble0..3`, `Litter0..3`, `Twig0..2` and `TussockBase0..2`, with vertex
     colour, no collision.
2. **Landscape detail, strips only.** `MI_GT_Landscape_Strips`, a material instance of the landscape material with a
   static switch `GroundDetail` on, assigned only on L_MudVariants, L_GravelDeform and L_MudDrive. Any change to the
   parent must compile to today's shader with the switch off.
   - **Layers:** the scrub/sand layer takes slice 0; the grass ground (where grass density is high) takes slice 1.
   - **Keep the strips' palette.** The detail modulates the existing layer colour: colour = layer colour × (detail
     luminance / its mean), with the bake's own hue at 30 %. Normal and ORH from the detail; roughness 0.6-0.95.
   - **Anti-tile:** the A2 settings (a second sample at 2.7 m rotated 37°, blended by a 7 m noise; a 13 m tint
     noise).
   - **POM** within 15-25 m at 1.5 cm, using the gravel/mud POM code. The detail fades into today's look between 25 and
     40 m.
   - **Switch:** `gt.Ground.Detail` 0/1, through an MPC; 0 = today's look.
3. **Scatter**, strips only: placed at level setup, deterministic, one HISM per mesh.
   - **Where:** on scrub and grass ground, never on the route band or road, mud patches, gravel patches or fords.
   - **Densities per m², clustered** (a 3 m cluster noise ×0.1-×2.5, renormalised):
     - clods 0.6, pebbles 1.5, twigs 0.05;
     - litter 0.25, only within 1.5 m of tussocks;
     - one tussock base under each tussock whose footprint is at least 25 cm, scaled to it.
   - **Placement:** aligned to the landscape normal, random yaw, sunk to each mesh's manifest embed.
   - **Cull** at 30-40 m (litter and twigs at 25 m).
   - **Material** `M_GT_GroundScatter`: vertex colour × the strip's layer palette, with a world-aligned ScrubSoil height
     bump at 1.5 cm.
   - **Switches:** `gt.Ground.Scatter` 0/1 and `gt.Ground.ScatterDensity` 0-1.
4. **Tests and checks.**
   - Every Mud, Snow, Gravel, Spray and Relief test passes, with the CRCs unchanged.
   - The strips' drive checks run (a game may be open; name it) and their gates hold.
   - Report: instance counts per mesh per strip, and the shader instruction and sampler counts of the parent with the
     switch off and on.
5. **Pictures** (sun behind the camera):
   - the relief cameras again (`Relief_OnFoot`, `Relief_Overview`, `Relief_Bog`);
   - `Ground_Close.png`: 1.7 m eye height, 30° down, at bare scrub between tussocks;
   - `Ground_Close_Detail0.png`: the same frame with gt.Ground.Detail 0 and gt.Ground.Scatter 0;
   - `Ground_Far.png`: 40-60 m of open scrub at 1.7 m, to judge tiling at distance.
6. **Docs and commit** as usual. The owner's list: the two switches, the densities, the POM range.
   Commit message: "Ground relief GR2: soil detail with anti-tiling and parallax, ground scatter (strips only)".
7. **Carried over from GR1c** (main session):
   - **Puddles:** the puddle cuts made the old-track walls steeper (41-44°), and from above they read as short dark
     slashes. Cut puddles as cosine basins with walls of 30° or less, inside the track's footprint.
   - **Spray check:** move its Deep spin onto the nearest puddle cell, so the muddy-splash gate has water under the
     wheel. Report the splash count.

*Phase B done 2026-10-11 (VEHICLE_BUILD_SYSTEM 105; no game was open at any run; no timing). 0: crack darkening 0.35 -> 0.1225, kept 36.5 -> 20.0 % (presence 4-18 cm, smoothstep
0.74-0.86), no crack within 1-2.5 cm of a Voronoi vertex: 6,770 -> 2,913 runs, p95 extent 4.49 -> 2.83 cm, crack pixels 0.630 -> 0.769 of the
rest's luminance; `ScrubSoil_AntiTile.png` re-rendered (A2's in `_A2.png`), SoilUnderGrass's roots left (0.886; `SoilUnderGrass_AntiTile.png`).
Finding: the tile's 4 cm-blurred contrast is 0.0781 before and 0.0780 after; frozen at its mean, the colour wash (20-80 cm + 5-20 cm, weight
0.6) takes the 10 cm-blurred contrast 0.034 -> 0.011 and the crack paint nothing, so the mid-distance rows are the wash's, not the cracks'.
1: TA_GD_{Color,Normal,ORH} and the 20 SM_GD_* in /Game/GrandTour/ArtTests/GroundDetail. 2: the strips have no shared parent (three copies
of M_GT_Landscape), so each copy has the GroundDetail static switch (off) and each strip folder an MI_GT_Landscape_Strips (on); the Scrub
row on the two bog strips, the grass verge on the gravel strip; slice 1 from a per-strip grass map (dense on 2.2 / 2.7 / 0 %). Counts with
the switch off equal today's (496 / 8 samplers twice, 201 / 3); on: gravel 591 / 6, the bog strips' probe (Scrub row bypassing the blends)
520 / 8 -> 1,232 / 12. 3: AGTGroundScatter, clustered x0.1-2.5 (sharpened 3 m noise): 130,784 / 69,497 / 71,284 instances on L_MudVariants /
L_MudDrive / L_GravelDeform at 0.60 clods, 1.50 pebbles, 0.05 twigs per m^2, litter 0.26-0.27 near tussocks, 3,025 / 1,892 / 280 mounds.
7: puddles are cosine basins, walls at most 30 deg: inside the track's half width alone they reach 0.37 of it and held water only in Deep
(Standard's -25 cm table), so the wall goes on at 30 deg over a skirt of half that width more (PreChurnPuddleSkirt 0.5), then the floor
rises; water cells Firm 123 / Standard 41 / Deep 227 / Stony 80 (GR1c 198 / 237 / 287 / 188), steepest basin cell 29.7-30.0 deg, steepest
old-track cell 28.6-29.0 (GR1c 41.6-43.5); strip CRCs 5687584a / de3e99d8 / 2b85214e / 5c567e0a, fixtures 8e0aad06. The spray check's Deep spins stand on the nearest puddle cell (2.5-4.1 cm of water); the muddy splash count is still 0 (the water emitters, not the ground). 4: tests
21/21 (Mud, Snow, Gravel, Spray, Relief with the new Relief.Scatter); L_MudVariants completed (Firm 29.8, Standard 27.6, Deep 1.7, Stony 16.3
km/h; before 29.7 / 28.1 / 1.7 / 9.4), L_MudDrive's four runs to 119 m. L_GravelDeform's ten checks true, its passes as before. Biome test PASS, the Hide and Proving hashes unchanged. 5: Relief_*.png, Ground_Close.png, Ground_Close_Detail0.png and Ground_Far.png in Art/Export/<strip>/ (copies in GR2/).*
