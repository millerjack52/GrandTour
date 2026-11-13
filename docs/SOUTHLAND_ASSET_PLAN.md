# Southland asset plan

Written 2026-10-17. Owner: "We need to create a lot of assets for Southland New Zealand."
Builds on the native plant kit (`docs/NATIVE_PLANT_KIT_PLAN.md`: 20 meshes, deterministic
Blender pipeline, imported, `L_NativePlants` lineup at the owner gate) and the Waimeamea
photos in `Art/References/Waimeamea/`. Target maps: L_LidarStudy first (LP3 placement, LP4
farm and house), Benmore high country second.

## Pipeline (the kit's, unchanged)

Blender 5.1 scripts on `Art/Blender/native_plant_lib.py`: opaque modelled geometry, linear
vertex colours, no textures, no alpha cards, three authored LODs from one design, convex hull
collision only where a car must stop, `validate_native_plants.py` round-trip, manifest, Cycles
review renders with a 1.8 m figure, one-call runner `bash Art/build_native_plants.sh <set>`.
Unreal import on `Art/Unreal/import_native_plants.py`'s pattern into
`/Game/GrandTour/Environment/NativePlants/v01`, a lineup level per batch, captures at owner
angles. Sonnet agents execute from a complete brief; Opus only if a family fails the look
twice. Fable looks at every render against the photos before import; the owner gates in play.
Budgets: at most 14 meshes per agent run; triangle ceilings like the kit (hero tree <= 28k,
mid plant <= 10k, small <= 3.5k; LOD2 <= 2k), descending strictly.

## Catalogue (E = exists in the kit, N = new)

- **S1 Bush floor and river** (photos 01, 03, 04, 05, 06, 07, 08): kiokio / hound's-tongue
  fern A/B N; mossy fallen log A/B N; rotten stump N; moss hummock A/B N; river cobble cluster
  S/M/L N; cobble bar shell N; bleached driftwood log N; log jam N; mossy boulder A/B N;
  crown fern A/B/C E; tree fern A/B/Young E; dead spar E.
- **S2 Farm and road** (photos 02, 09, 10): post-and-wire fence module with battens N;
  strainer post assembly N; steel farm gate N; cattle stop N; culvert pipe with headwall N;
  water trough N; wooden power pole with cross-arm N; rural sign post set (give way, name
  blade, no exit; lettering as plain blocks) N; letterbox N; round hay bale N; gorse bush in
  flower N; broom N; rush clump for wet hollows N; thistle N; verge tussock clump N;
  shelterbelt radiata pine young/mature N; macrocarpa N; harakeke E; ti kouka E; coprosma E.
- **S3 Canopy variety** (photos 01, 05, 08): kamahi N; rimu emergent N; totara N; lancewood
  juvenile/adult N; broadleaf N; fuchsia with peeling bark N; supplejack vine curtain N;
  pepper tree N; mingimingi N; beech mature/pole/edge E; kanuka E.
- **S4 Buildings, massing only** (photos 02, 12; LP4): weatherboard house with deck and iron
  roof; black iron garage; implement shed; water tank; the hunting hut of photo 12 (plywood and
  weatherboard, iron roof with a green gable, iron skirt, deck with steps, flue). All N.
- **S5 High country for Benmore**: matagouri E; dense tussock E; briar rose N; wilding pine N;
  schist tor N; scree patch N.

- **Ground litter for dense ground** (owner 2026-10-17: "ensure the ground is dense and
  interesting"): twig litter patch A/B N; root tangle N; leaf litter mound N; moss hummock E
  (S1); cobble cluster E (S1); puddle discs are a material/decal job, not a mesh.

S2 is split into S2b (verge plants, shelterbelt trees, ground litter; 15 meshes) and S2a (farm
hardware: fence, strainer, gate, cattle stop, culvert, trough, power pole, signs, letterbox,
hay bale; 10 meshes). Order S1, S2b, S2a, S3, S4, S5. Each batch: build and validate (no Unreal), Fable's look against the
photos, one fix round at most, then import and lineup (one Unreal), then the owner gate.
Nothing is placed in L_LidarStudy until the kit's own gate verdict is in (LP3).

## Stage log

- 2026-10-17: plan written; S1 briefed to a Sonnet agent (14 meshes, build and renders only).
- 2026-10-17 S1 built (Sonnet): 15 meshes x 3 LODs, all within budget, NATIVE_VALIDATION_OK 45,
  byte-stable GLB. Fable's look at Lineup_Floor / Assembly_River: PASS on geometry (logs, stump,
  log jam, driftwood, boulders, cobbles, kiokio all read as what they are at true scale), FAIL
  on look: driftwood and log jam near-white plastic, cobbles a pastel pile on pale sand with no
  dark gaps and uniform size, boulders pale, log moss as camouflage blotches, kiokio bright
  plastic green with cartoon-orange new fronds, river scene flat with no bank or overhang.
  S1b briefed (Sonnet): darker desaturated wood/stone/moss, luminance-only tint, lognormal
  cobble sizes with wet lower thirds and dark gaps, kiokio darker with more fronds, river
  assembly with banks, dark water and overhanging beech, exposure back to the kit's 1.8.
- 2026-10-17 S1b built (Sonnet): same 15 meshes within budget, NATIVE_VALIDATION_OK 45. Fable's
  look at Assembly_River: PASS to import. It reads as a forest stream (dark amber water with
  trunk reflections, mossy banks, beech limbs overhanging, kiokio over the lip, tree ferns).
  Logged for the Unreal look: driftwood and log jam still light grey and smooth, the cobble spit
  a sparse patch on pale sand rather than a dense wet bar, log moss a 10 cm speckle (vertex
  spacing), kiokio new fronds read orange-tan in open light. S1 import + lineup briefed (Sonnet):
  third lineup row, logs/stump/hummocks in the bush stand, a 24 x 6 m dry riverbed strip, two
  new owner-angle cameras NZ_FloorLogs and NZ_Riverbed.
- 2026-10-17 S1 imported (Sonnet): 15 meshes in /Game/GrandTour/Environment/NativePlants/v01
  (hulls and sizes as manifest, importer now skips existing meshes, `native_plants.ps1
  -Reimport <set>` forces), L_NativePlants row 3, logs/stumps/hummocks in the bush stand, a
  24 x 6 m dry riverbed strip, cameras NZ_FloorLogs (37 mean, shade, not gating) and
  NZ_Riverbed (98, gating). Fable's look at UE_Riverbed: the strip is props on a flat brown
  plane with no water, bank or sand; boulders read (grey with moss caps); cobbles pale pebbles
  on tan pads; driftwood and log jam bleached grey-tan; kiokio stiff saturated rosettes; nothing
  reads wet. Logs in the fern mass sit in blue-black shade as smooth tubes. Verdict: geometry
  usable, colour and wetness are a material job, not more vertex-colour rounds: S1c (after the
  owner's verdict) = a wet-stone / wet-wood darkening in M_NZ_Bark (lower-third darkening,
  roughness drop, tannin tint under the LiDAR water) and placement under real water in
  L_LidarStudy where the tannin material does the rest. GATE OPEN with the kit's: owner runs
  Play-NativePlants.bat, walks the fern mass and the riverbed strip. S2 held until then.
- 2026-10-17 owner: start S2 now; keep dense, interesting ground in mind; after the LiDAR map
  is good, an easy guide to adjusting the level; bring clay/gravel roads into the map, plus a
  deformable clay soil and clay material (clay is present on the block, photo 10's cut bank).
  S2b briefed (Sonnet) with the litter props and an Assembly_Litter render judged on density.
  Clay and the guide are stages LP1b, CL1-CL3 and LP7 in docs/LIDAR_PLACE_PLAN.md.
- 2026-10-17 S2b built (Sonnet, ~0.65M tokens): 15 verge meshes within budget, NATIVE_VALIDATION_OK
  45 (FBX not byte-stable on rerun, GLB is). Agent darkened bark/pasture/litter below the brief's
  numbers because exposure 1.8 rendered them pale, enlarged radiata sprays to 30/60 cm and added
  dark mass layers under gorse and tree crowns to stop see-through. Fable's look at
  Assembly_Litter: PASS on density, the floor reads like photo 08 (twigs, leaf mounds, roots,
  mossy logs, puddle, ferns overlapping). Logged: moss hummocks (S1) too smooth and lime-bright,
  root tangle a flat grey-green spider, leaf mounds faceted, some flat peat mid-frame; agent's
  own notes on Edge2 (gorse and coprosma identical clipped balls, tussock evenly spaced, pale
  pasture) and Shelterbelt (radiata crowns read as leaf fans, pale trunks, LOD2 skeletal).
  S2b import + lineup and S2a farm hardware briefed (Sonnet).
- 2026-10-17 S2b imported (Sonnet): 15 verge meshes in the kit folder (50 total), L_NativePlants
  row 4, 205 litter instances in the bush stand (no 1 m bare square by the coverage grid),
  edge scrub band (gorse, broom, tussock drifts, rush dip, thistle), shelterbelt row on the
  stand's west side, cameras NZ_DenseFloor (29, shade), NZ_EdgeBand (51), NZ_Shelterbelt (114).
  Agent's look, accepted by Fable: DenseFloor does NOT read dense in Unreal (litter thin and
  the same value as the flat peat, ferns flat and faceted, no moss or root mass); EdgeBand reads
  as a scrub fringe but gorse, broom and coprosma are uniform clipped balls and the tussock is
  evenly spaced; Shelterbelt reads as a row but crowns look broadleaf. Decision: no fix round in
  the lineup level. It has one flat peat plane and none of the painterly surface, grass or mud
  layers, so it cannot show dense ground; the density test moves to LP3 placement on the LiDAR
  map, where the ground, the near-band fern layer and these litter props combine. Known: the
  EdgeWall brightness gate sits 0.6 above its threshold with +-1 run noise (flaky).
- 2026-10-17 S2a built (Sonnet, ~0.5M tokens): 11 farm meshes (fence module, strainer, gate,
  cattle stop, culvert, trough, power pole, sign post, give way, letterbox, hay bale) x 3 LODs
  within budget, hulls as specified, NATIVE_VALIDATION_OK 33; validator gained `min_z_band` for
  part-buried meshes (culvert, cattle stop). Agent's look at Assembly_Gateway (Fable has not
  looked): reads as a gateway off a gravel track in scale, but pale and clean at exposure 1.8,
  2 mm wires vanish at 30 m (fence reads as bare posts: in Unreal the wires need a thicker
  card or a line material), gate and pole near-white, tussock sparse and even, gravel a smear.
  Import HELD until the owner's gate verdict (the lineup level cannot show lighting or ground
  properly, and three batches already wait there). Renders sent to the owner.
  Assets now: kit 20 + floor 15 + verge 15 + farm 11 = 61 meshes, 183 LODs, all validated.

