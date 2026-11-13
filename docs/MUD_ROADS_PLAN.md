# Mud roads from the owner's references (MRD1)

Main session, 2026-10-12. The owner sent five reference pictures of mud roads. They are in `Art/Reference/MudRoads/`
(local only, since images are gitignored); look at them before working. **The references lead:** where they disagree
with an earlier plan number, the reference wins.

## What the references show

| File | What it shows |
|---|---|
| `Ref1_SiltRoad_ManyTracks.png` | The whole road surface is covered by dozens of shallow (2-5 cm) curving tyre grooves that overlap, cross and merge, with soft ridges between. Grey-brown silt with a slight wet sheen. Many tracks, but irregular: curving, crossing, varied widths. |
| `Ref2_ChurnZone_Clods.webp` | A churned dark wet zone with clods thrown all over the road around it. Damper and drier patches (dark vs light), faint tracks with partial tread through drier ground, grass tufts poking through. |
| `Ref3_DeepRuts_OrangeWater.webp` | Deep ruts (20-40 cm) with torn, crumbly, blocky walls and overhanging lips. A lumpy churned ridge between them. Ruts full of opaque orange-brown water with ripples and sky reflection. |
| `Ref4_BraidedRuts_Puddles.webp` | Many side-by-side ruts that braid and wander. Puddles in every low run, reflecting the sky clearly. Torn, lumpy mud ridges, partial tread prints, red-brown saturated mud, a crisp edge into grass. |
| `Ref5_Expeditions_Spray.webp` | A pale silty road with tracks and partial treads, sticks and branches strewn on it, darker damp patches, and a dense brown spray cloud behind the wheels. |

**Where we differ** (my look, after MW1b):
- GR1c cut the old ruts to 1-2 pairs to avoid parallel lines. Real mud roads have many braided tracks; what makes them
  read natural is curving, crossing, merging and varied depth and width, not fewness.
- MW1b removed parallax from rut walls (it smeared), so the walls now read soft and plain. The references show torn,
  blocky, crumbly clods and overhanging lips.
- MW1 made puddles rougher (0.2-0.3) to stop the mirror look. The references' puddles reflect the sky clearly. Their
  life is ripples, not roughness.
- No wet/dry variation: the references are dark and saturated near water, lighter on drying crowns and ridges.
- No thrown clods or debris across the road around churned zones.
- The spray is thin next to Ref5.

Older owner rejections still hold: regular or evenly spaced lines and tread ladders, uniformity, swirls, too smooth,
flat planes, too glossy (the mud matte toward the sun, as MW1b fixed), and the river water stays untouched.

## 0. Rules

`docs/MUDRUNNER_LESSONS_PLAN.md` section 0 holds, with the owner's current settings:
- skip test runs: build, setup, and ONE rendered capture run for my look. Commits say "tests not run (owner)";
- run with a game open and name it;
- `Art/wait_unreal_free.ps1` as its own command before every Unreal or UBT run;
- your hunks only; never push; never touch river water.

Another agent (Benmore B1) is working in the tree on the Benmore material, MF_GT_GroundDetail
(`Art/Unreal/ground_detail.py`), grass types and `GTSurfacePhysMaterial`. Don't edit those.

## MRD1: a mud-road profile and look (built on the strips, used on Benmore by B2)

1. **A "MudRoad" pre-churn mode** (a profile number `PreChurnStyle` = Braided; the existing mode stays the default
   for the bog strips unless the owner says otherwise):
   - **Tracks:** 6-14 old tracks across the road width (by width / 0.9 m). Each is a tyre-width trough (×0.8-1.6) on its
     own low-frequency path:
     - wavelengths 15-60 m, lateral swing ±0.4-1.5 m;
     - paths cross and merge (braid), with at least 3 crossings per 20 m of road;
     - tracks start and end at random (present 50-90 % of length).
   - **Depth:** power-law, 2-25 cm (median about 5 cm, top 10 % at 15 cm or more), varying along each track at 2-6 m.
   - **Ridges:** the displaced volume makes the ridges between and beside tracks. Lumps re-seeded heavier on ridges
     (LumpShare 0.5), torn and lumpy.
   - **Walls:** walls of tracks deeper than 10 cm get a stepped, crumbly profile:
     - clump blocks of 6-15 cm across along the lip;
     - 30 % of lip segments overhang a little (lip lumps leaning in by 2-4 cm);
     - the cosine troughs stay for shallow tracks.
   - **Puddles:** wherever a track's floor falls below the water table, water stands. The deepest runs are set 1-5 cm
     below it, so puddles cover 8-15 % of the road area as elongated, irregular pools in the low runs.
   - **Churn zones:** 1-3 per 40 m at crossings or deep spots. Extra lumps and a clod field around them: LM2c clods at
     2-6 per m², falling off over 2-4 m, plus a few MR5 chunks.
   - **Tread:** the freshest 2-3 tracks carry a subtle, partial tyre tread imprint (broken: about 40 % of the length,
     faded at the ends, depth 0.3-0.8 cm, never a full ladder). Switch `gt.Mud.OldTread`, default 1. The owner earlier
     declined crisp tread; this is the references' partial print. Mention it in the report.
   - **Gates (report):**
     - the track count, the depth histogram, crossings per 20 m, and the puddle share of the road area;
     - the heading spread of tracks per 20 m window: sd ≥ 4°, so no parallel bundle.
2. **The look** (`live_mud_style.py`, M_GT_Mud and M_GT_MudWater; rut water only, never river water):
   - **Wet and dry.** A wetness term from the distance to standing water (0 to 60 cm) and from the trough depth:
     - near water, colour ×0.72 and roughness 0.5-0.6 (saturated, a soft sheen at the edges);
     - on ridges and crowns, colour ×1.08 and roughness 0.85-0.95 (drying);
     - between, MW1b's bands.
     - The mud glare gate stays: mud pixels over 0.9 luminance ≤ 3 % in the MW owner frame.
   - **Walls:** DeformDetail strength 0.8 → 1.0, and on walls deeper than 10 cm add the bog slice's height-based AO
     at 1.5× strength, so the blocky clods read without parallax.
   - **Puddles:** settled rut water roughness 0.2-0.3 → 0.06-0.1, so the sky reflection is clear (Ref4). MW1's ruffle,
     gusts and rings carry the motion. The turbid orange-brown colour shows through at shallow edges under 3 cm (Ref3).
     The MW1 water-motion gate stays (≥ 2/255 mean, ≥ 15 % of pixels over 4/255).
3. **Road debris.** Sparse sticks and branches on mud roads: GR2's twig meshes plus 2 new branch meshes (40-120 cm,
   headless Blender, the twig recipe), 0.03-0.08 per m², clustered, lying flat, partly sunk.
4. **Spray:** on mud-road profiles, mud FineScale ×2 (a profile number), for the denser throw of Ref5.
5. **Where it shows first.** Make the L_MudVariants **Standard** section a MudRoad, and put a 60 m MudRoad section on
   L_MudDrive. Benmore's road zones use the profile once B2 lands.
6. **Pictures** (sun behind the camera unless a reference has it otherwise), each set beside its reference in the
   report:
   - `MRD_Ref1.png`: on foot at 1.6 m, looking along the road over many tracks;
   - `MRD_Ref2.png`: a churn zone with its clod field, on foot;
   - `MRD_Ref3.png`: at 1.2 m, close down a deep rut with water and a lip;
   - `MRD_Ref4.png`: at 1.5 m, along braided puddled tracks with the sky behind, so the puddles reflect it;
   - `MRD_Ref5.png`: a chase view of the car driving the road, with spray;
   - `MRD_Top.png`: about 20 m up and 50° down, the braid layout.
7. **Commit** "Mud roads MRD1: braided old tracks with puddles, torn walls, wet/dry mud, debris (tests not run
   (owner))".

## MRD1b: from my look at MRD1 against the references (main session, 2026-10-12)

**Better than before:** braided tracks show on foot (MRD_Ref1, MRD_Ref4), with ridges between them and a stick on the
road.

**Fails, against the references:**
- **Puddles** draw as pale, translucent, glassy oval lenses ("ghost blobs") floating in the ruts. In MRD_Ref1 several
  sit in a dotted row down one track. The references' puddles are long, irregular pools filling the low runs, with an
  opaque turbid orange-brown body (Ref3) and a clear sky reflection on top (Ref4). There's no hard outline: they merge
  into wet mud.
- **The road surface** reads as a cobble or pebble mosaic: the Standard bake's rounded lumps with light tops cover
  everything and compete with the tracks. Lips look like stacked flat stones. The references' road surface is fine
  silt or clay, where the tracks and torn ridges carry the detail. This settles the owner's open "pebbly" question,
  for mud roads.
- **From above** (MRD_Top), the tracks are narrow dark crevices bundled into X shapes, converging toward both patch
  ends.

**Fixes:**
1. **Puddle look** (rut water, M_GT_MudWater, never river water):
   - the body is opaque turbid colour (the variant MudTint, saturated toward orange-brown) at opacity 0.85-0.95 from
     1 cm depth, fading to 0 over the outer 0-1 cm, so the edge melts into wet mud with no rim;
   - a Fresnel sky reflection on top (F0 0.02, roughness 0.06-0.1, plus MW1's ruffle);
   - no pale translucent body anywhere.
   - Gate: in MRD_Ref4, the water pixels' median luminance lies between the wet mud's and the sky's, with R > G > B.
     Report the pixel counts.
2. **Puddle shape and share.** Instead of separate basins, lower each present track's floor along low runs of 2-8 m
   to 1-4 cm under the water table, so pools are long, follow the track and merge where tracks cross.
   - Puddle share of the road: 8-15 % (report).
   - No more than 2 separate pools per 5 m of any one track.
3. **Silt surface on MudRoad profiles.** On the running surface (outside the ridges and lips):
   - the bog bake tiles 2× finer;
   - lump normal, AO and POM depth ×0.4.
   Ridges and lips keep full strength plus DeformDetail. Profile numbers, so bogs are unchanged.
4. **Track layout from above.**
   - Track width ×1.2-2.0 tyre width.
   - Wall AO boost ×1.5 → ×1.0, and only for walls deeper than 15 cm.
   - Track start points spread evenly along the road length, never all at the patch ends.
   - Crossing gate relaxed to ≥ 2 per 20 m.
   - Keep heading sd ≥ 4°.
5. **Fix the L_MudDrive capture camera** (MRD_Ref1_MudDrive and MRD_Top_MudDrive were the same view).
6. **Docs:** commit this plan file (it is untracked), the devlog, the BACKLOG line, a VEHICLE_BUILD_SYSTEM section
   (the next free one at commit time) and a Done note here.
7. **Pictures:** retake MRD_Ref1-4 and MRD_Top (both strips) with the same cameras. Keep MRD1's as `*_MRD1.png`.
   Commit "Mud roads MRD1b: opaque reflective puddles along the runs, silt road surface, wider tracks (tests not run
   (owner))".

## Done notes

**MRD1 (2026-10-12, 4ec7889; tests not run (owner)).** AGTMudPatch::PreChurnBraided (FGTDeformProfile PreChurnStyle Braided), the
churn zones' clod fields (clod Source 6) and chunks, road debris (GR2's twigs, SM_MRD_Branch0-1 from Art/Blender/build_road_branches.py,
RoadDebrisPerM2 0.05), M_GT_Mud's wet/dry term (12 field taps), deformation detail 1.0, partial old tread (gt.Mud.OldTread), rut water
roughness 0.06-0.1; the spray item became the number MudRoadSprayScale only (B1b's code reads it). L_MudVariants' Standard and a 60 m
L_MudDrive section (115-175 m) are MudRoads at a -10 cm water table (the bog's -25 cm lay under every road track: 0.0 % water). Gates:
7 tracks, crossings 5.0 / 3.0 in the fewest window, heading sd 7.5 / 6.7 deg, mud glare 0.01 %; failed: puddles 4.4 / 4.5 %, water motion
1.39 / 1.29 mean. Capture: Art/check_mud_water.ps1 -Tag mrd, Art/sample_mud_roads.py.

**MRD1b (2026-10-12; tests not run (owner)).**
1. The rut water's opaque turbid body (live_mud_style.py MRD1B_WATER_SCALARS: the variant's bog mean x0.8 off Deep, saturation 1.6,
   BodyWarm (1.08, 0.95, 0.78), opacity 0.85-0.95 from 1 cm, faded over the outer 1 cm; AGTMudPatch sets the water's MudVariant).
   Gate in MRD_Ref4 FAILED: water median luminance 0.216 under the wet mud's 0.252 (sky 0.851), colour R 83 > G 49 > B 35 passes;
   37,668 water, 31,735 wet-mud and 441,393 sky pixels.
2. Pools along the tracks in place of basins (runs of 2-8 m, 3 m apart on a track, 1-4 cm under the table, flat across 0.55 of the
   half width, ramped 75 cm; stray water lifted to the table): share 13.5 % (L_MudVariants, 13 runs, mean 3.4 m) and 14.3 % (L_MudDrive,
   26 runs, mean 3.8 m), PASS. Pools in 5 m of a track at most 3 and 4, FAILED against 2: the count runs along each track's line and
   includes the other tracks' pools it crosses.
3. The silt surface (RoadSiltTileMul 2, RoadSiltStrength 0.4: SiltTileMul / SiltStrength on the patch's M_GT_Mud instance; off the
   crowns, lips and walls; the deformation detail keeps its scale).
4. Tracks 1.2-2.0 x the tyre (measured 1.21-2.00, median 1.63 / 1.58; 32-61 cm), stretches placed by shuffled even slots (9 ends in
   view on each strip, the largest gap 0.21 / 0.27 of the road), crossings at least 2 in every 20 m window (2.0 / 2.0), heading sd
   6.0 / 5.7 deg, wall AO x1.0 past 15 cm. Asked depth median 5.2 / 6.9 cm, 11 / 15 % at 15 cm or more.
5. L_MudDrive's pictures are two views now (the camera is made movable if it does not move; the guard did not trigger, so the
   MRD1 cause is unconfirmed). 6. These notes, the devlog, the BACKLOG line, VEHICLE_BUILD_SYSTEM section 109.
7. MRD_Ref1-4, MRD_Top, MRD_Ref1_MudDrive, MRD_Top_MudDrive retaken with MRD1's cameras (GT_MRD_CAMERAS); MRD1's kept as *_MRD1.png.
   Water motion 0.88 / 0.78 mean, 1.8 / 1.1 % over 4/255 (FAILED, lower than MRD1's under the opaque body); mud glare 0.01 %.


## MRD1c: from my look at MRD1b (main session, 2026-10-12)

**On foot** (MRD_Ref1, MRD_Ref4): a big step. Opaque orange-brown pools fill the ruts and follow the tracks between torn
walls, much closer to Ref3 and Ref4. The road surface is finer.

**Fails:**
- **No reflection.** The pools are matte and darker than the wet mud, with no sky reflection, so they read as wet clay
  slabs. Ref4's pools mirror the sky.
- **Square, dashed pools.** They end in straight, square cut-offs. From above (MRD_Top), they read as evenly dashed
  orange bars along each track: regular dashes.

**Fixes:**
1. **Reflection.** The rut water body is near-opaque now, so draw it as an OPAQUE (or masked, with a dithered edge fade
   over the outer 1 cm) material instead of translucent, so it gets the same Lumen and SSR reflections the mud gets.
   - Keep the turbid body colour, F0 0.02 and roughness 0.06-0.1, with MW1's ruffle as the normal.
   - Gate: in MRD_Ref4, the water's median luminance lies between the wet mud's and the sky's. Report it.
   - The MW water-motion gate (≥ 2/255 mean, ≥ 15 % of pixels over 4/255) should pass once the ruffle shows in the
     reflection; report it.
   - If opaque water breaks something (the rings, the froth, the shallow see-through), report it rather than
     redesign.
2. **Pool shape.**
   - Run ends taper over 0.5-1.5 m with an irregular, noise-wobbled outline (no square ends).
   - Run lengths 2-8 m with CV ≥ 0.4; gaps between runs 1-6 m with CV ≥ 0.4.
   - 30 % of runs continue across track crossings, so pools join.
   - Gate: report the CVs, and no evenly dashed look in MRD_Top (my look).
3. **The pools-per-5 m metric** counts each track's own pools only. Report it.
4. The mud-road water table of -10 cm is accepted (main session).
5. Retake MRD_Ref1, MRD_Ref3, MRD_Ref4 and MRD_Top (both strips). Commit "Mud roads MRD1c: reflective opaque puddles
   with tapered irregular runs (tests not run (owner))".

**MRD1c (2026-10-12; tests not run (owner)).**
1. M_GT_MudWater is MASKED: the body's opacity through an interleaved-gradient dither (turned each of 8 frames) into the opacity
   mask, so the rut water takes the mud's Lumen and screen-space reflections; colour, F0 0.02, roughness 0.06-0.1 and the ruffle as
   before. Lost: the see-through rim of settled water and blended froth (the froth now dithers). Gate in MRD_Ref4: water median
   luminance 0.262 against the wet mud's 0.264 and the sky's 0.851 - FAILED by 0.002 (half an 8-bit step), R 94 > G 61 > B 40 passes
   (32,729 water, 45,379 wet-mud, 444,169 sky pixels). Water motion PASSES: 2.75 / 2.77 mean, 25.7 / 24.9 % over 4/255.
2. Pool runs 2-8 m by a power law (u^2), gaps 1-6 m the same way, ends tapering 0.5-1.5 m with the flat narrowing, the outline
   wobbled (+-35 % flat width at 0.6-1.2 m, +-15 % centre, +-18 % cell noise), 30 % of the runs meeting another track's trough carry
   on across it. L_MudVariants / L_MudDrive: run CV 0.379 / 0.399 (FAILED, >= 0.4 asked; 2.0-5.25 and 2.0-6.75 m, median 2.5 / 2.75),
   gap CV 0.502 / 0.532 (pass; 1.0-6.25 and 1.0-8.75 m), runs joined across 6 of 13 / 5 of 22 meeting runs (30 / 13 % of all runs),
   puddles 12.2 / 10.4 % (pass).
3. Pools per 5 m of a track, its own runs only: 2 / 2 (pass); along the line with the crossed pools: 4 / 3.
4. The -10 cm table stands. 5. MRD_Ref1, MRD_Ref3, MRD_Ref4, MRD_Top, MRD_Ref1_MudDrive, MRD_Top_MudDrive retaken with MRD1's
   cameras; MRD1b's kept as *_MRD1b.png. Mud glare 0.05 %.
