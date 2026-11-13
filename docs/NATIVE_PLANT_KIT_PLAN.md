# Native plant kit (NZ trees and shrubs)

Written 2026-10-16. The owner asked for models of native NZ trees and shrubbery. Nothing usable
exists to buy or download: no Fab or Unreal pack covers NZ natives, the only NZ-specific bundle
(Globe Plants, paid) is dense archviz geometry with alpha-card textures, and Sketchfab has no
CC0 cabbage tree, tree fern, flax or beech. The project already builds its vegetation as
deterministic Blender scripts with vertex colours, modelled opaque leaves and authored LODs
(`Art/Blender/build_shrub_library.py`, `willow_reference_v5.py`), and the owner accepted the
willow family built that way. This kit is built the same way.

The species come from the owner's own places: the Waimeamea bush photos in
`Art/References/Waimeamea/` (silver beech, crown fern, tree fern, margin scrub, flax by the
house) and the Mackenzie high country of L_Benmore (matagouri, kanuka, cabbage tree). Those
photos LEAD: the bush set is judged against photos 01, 08, 09 and 10 before anything is
imported.

## Conventions (same as the shrub library unless stated)

- Blender 5.1.2: `"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup
  --python-exit-code 1 --python <script>`. No add-ons (Sapling is not installed); all geometry
  is generated from code.
- Output: `Art/Export/NativePlants/v01/`. Files `SM_NZ_<Family>_<Variant>_LOD<n>.fbx` and `.glb`,
  `manifest.json`, `validation-report.json`, `GrandTour_NativePlants.blend`, review PNGs. The
  build deletes its own `*.blend1` backups; renders are at most 2000 px wide (disk rule).
- Unreal destination: `/Game/GrandTour/Environment/NativePlants/v01`.
- Mesh: ground pivot at the origin, roots 5-7 cm below ground, no zero-area faces, all
  coordinates finite. Linear FLOAT_COLOR corner attribute `Color`; a `UVMap` layer of local
  surface coordinates (overlapping is fine). FBX exported in centimetres exactly as
  `build_shrub_library.py::export` does (scale vertices by 100, unit scale .01, `-Z` forward,
  `Y` up); GLB in metres.
- Material slots: shrubs, ferns and flax have one slot `Foliage`. Trees (beech, dead spar, tree
  fern, cabbage tree, kanuka, matagouri B) have two: slot 0 `Bark`, slot 1 `Foliage`. The
  manifest records `slots` per mesh. Blender materials are Principled, vertex colour on base
  colour, roughness .87, specular .19, backface culling off.
- No alpha cards, no textures, no wind. Every leaf, pinna, strap and spray is opaque geometry
  with its colour in the vertex colour. Per-element tint variation 0.8-1.2 on every leaf-like
  element; colour blotches on bark are low-frequency irregular patches, never stripes, rings or
  regular rows (the owner rejects regular lines, uniformity and smoothness; see
  `feedback-terrain-look-rejections`).
- Three authored LODs per mesh, built by the same code with the same seed. The RNG is consumed
  identically at every LOD; LOD1 and LOD2 keep every structural branch and a distributed
  subset of foliage elements enlarged (1.0 / 1.3 / 1.55) so coverage holds. Triangle counts
  must descend strictly.
- Collision: trees only. Convex lower-trunk hulls as hidden objects named
  `UCX_<meshname>_00`, `_01`... exported inside the LOD0 FBX (as the willow family); the
  importer uses one convex hull per UCX. Canopy never blocks. Ferns, flax and shrubs: none.
- Determinism: fixed seeds per (family, variant); the build is rerunnable and byte-stable.
- Review renders: Cycles, 24 samples, denoise, AgX, overcast studio (world grey-blue .32/.38/.44
  at .5, two disk area lights), chalk floor, labels, a 1.8 m figure post (capsule) for scale.
- Validation: `validate_native_plants.py` round-trips every FBX (dimensions within 1 mm,
  triangle count equal to the manifest, LODs descend, Color and UV present, slot count as
  recorded, hull objects present for trees, origin at zero) and writes `validation-report.json`.
  Only `ok: true` counts.
- One-call runner: `bash Art/build_native_plants.sh [bush|open|all]` runs the build and the
  validation, logs to `Saved/Logs/native_plants_<set>.log`, prints the manifest summary line
  and the render paths. Blender does not need Unreal closed.

## Shared primitives (`Art/Blender/native_plant_lib.py`)

Port from `build_shrub_library.py` and `willow_reference_v5.py`: `curve` (Catmull-Rom),
`tube(points, radii, sides)` with 4 % radius noise, `leaf` (folded 4-triangle leaf), the
material, export, manifest row and review helpers. Add:

- `spray(anchor, dir, size, colour)`: a small-leaf cluster for beech and kanuka. Three
  overlapping folded quads fanned 35° apart around `dir`, 6-8 triangles.
- `frond(anchor, dir, length, pairs, pinna_len, pinna_width, droop, colour, lod)`: a pinnate
  fern frond. The rachis is a thin ribbon (2 triangles per segment, 8 segments) along a curve
  that rises along `dir` then arches by `droop`. LOD0: `pairs` alternating pinnae, each a single
  quad, length tapering from 50 % at the base to 100 % at 40 % of the frond and 25 % at the
  tip. LOD1: one serrated strip (8 segments, alternating half-widths give a zigzag edge).
  LOD2: one plain tapered strip. Tree-fern fronds are bipinnate: each pinna is itself a
  serrated strip at LOD0.
- `strap(anchor, dir, length, width, arch, colour, edge_colour)`: a keeled leaf for flax and
  cabbage tree. Two quads across (the keel fold, 12° dihedral), 6-8 segments along, tapering
  to a point, rising then arching by `arch`; edge vertices take `edge_colour`.
- `lattice(base, radius, levels, angle, step, colour)`: divaricating twig lattice for coprosma
  and matagouri. Recursive: each twig of length `step` ends in two children at `angle`
  (60-90°) in alternating planes, 5 levels, radius halving per level, 3-sided tubes below
  3 mm radius.
- `bark_paint(mesh, base, patches)`: per-vertex bark colour: base colour, then irregular
  low-frequency blotches (sum of 3 incommensurate sines of the position plus per-vertex noise,
  thresholded) in each patch colour with the given coverage, biased to one side and to a
  height band. Used for moss, lichen and corky fissures.
- `hulls(trunk_curve, radii, count)`: `count` convex 8-sided prisms along the lower trunk,
  named `UCX_<name>_NN`, hidden.
- `figure()`: the 1.8 m scale capsule for renders.

## Species

Colours are linear RGB. "Tint" is the per-element multiplier range.

### NP1: Waimeamea bush set (7 meshes; `build_native_bush.py`)

1. `SM_NZ_Beech_Mature` (silver beech, 22 m, crown 9 m wide). Trunk base radius .32 m, sinuous
   (offset up to .8 m over the first 10 m), clear bole to 9 m carrying 2-3 bleached dead stubs
   (.4-.8 m, radius .03) between 3 and 8 m. From 9 m, 5 main limbs in a rough spiral rising
   40-60° from vertical, 5-7 m long, forking twice; secondaries alternate. Crown an irregular
   dome 9 x 10 m topped at 22 m with two limbs escaping it; 2 bleached dead twigs poke above.
   About 2,600 sprays at LOD0 on the outer third of the branchlets, layered flat-ish as beech
   is. Bark base (.10,.085,.07); moss patches (.17,.21,.09) 30-40 % of the lower 6 m, more on
   one side; lichen flecks (.30,.30,.26) 10-15 % on the upper trunk and limbs. Sprays
   (.045,.095,.035), the outer and top sprays (.11,.20,.055). 3 hulls over the lower 9 m.
   Budget LOD0 ≤ 28k triangles, LOD1 ≤ 8k, LOD2 ≤ 2k.
2. `SM_NZ_Beech_Pole` (12 m). Trunk radius .09, one gentle bend, nothing below 7 m but 2 dead
   stubs; 3 thin limbs; crown 3 x 5 m, about 500 sprays. Same bark rule, less moss (20 %).
   1 hull. Budget ≤ 6k / 2k / 600. This is the pole-stand tree placed by the thousand.
3. `SM_NZ_Beech_Edge` (16 m, the photo-10 margin tree). Trunk radius .28 with a strong lean
   (1.5 m offset at 6 m); limbs from 3 m up, contorted: each limb changes direction 2-3 times
   by 20-40°; crown lopsided, dense on the lee side and thin to windward; 2-3 bare bleached
   limbs stick out of the canopy. About 2,000 sprays. Bark lichen-grey patches (.26,.26,.23)
   25 %, moss 15 %. 3 hulls. Budget ≤ 24k / 7k / 2k.
4. `SM_NZ_DeadSpar` (14 m). Bleached trunk (.42,.40,.36) with darker weathered blotches
   (.24,.22,.20) 20 %, base radius .25, broken jagged top (3-point), 5 stubs .5-2 m at random
   heights above 5 m, one bare limb 4 m. No foliage. 2 hulls. Budget ≤ 1.5k / 600 / 200.
5. `SM_NZ_CrownFern_A/B/C` (Blechnum discolor; the understory, placed 100k+ times). A: .55 m
   tall x 1.0 m wide, 12 fronds, erect. B: .8 x 1.5 m, 18 fronds, the classic crown: fronds
   rise at 55-70° then arch to end 20° below horizontal. C: 1.0 x 1.9 m, 24 fronds plus 3 old
   brown fronds lying low. Fronds radiate from a crown 8 cm above ground; 26-30 pinna pairs,
   pinnae 7-9 cm mid-frond tapering to 2 cm at the tip, 1.2 cm wide. Centre: 3-5 erect narrow
   fertile fronds at .6 length, pinnae .4 cm, colour (.10,.12,.05), LOD0 only. Frond colour
   (.12,.26,.07) tint .8-1.15; the inner new fronds (.22,.36,.10); old fronds (.26,.17,.06).
   Budget LOD0 ≤ 3k (A ≤ 2k), LOD1 ≤ 900, LOD2 ≤ 250. Keep these cheap; they carry the bush.
6. `SM_NZ_TreeFern_A` (wheki, 3.5 m trunk) / `_B` (5 m trunk, 15° lean) / `_Young` (no trunk,
   crown at .3 m). Trunk radius .08 / .10, radius noise ±15 % in irregular bands, colour
   (.065,.05,.04) with sparse moss (.14,.17,.08) 10 %. Crown: 10 / 13 / 7 fronds at 10-30°
   above horizontal arching to the tip, length 2.2 / 2.6 / 1.5 m, bipinnate: 22 pinna pairs,
   each pinna a serrated strip 35-45 cm. Skirt (A, B): 10-14 dead frond midribs hanging
   1.5-2 m down the trunk from below the crown (3-sided tubes, (.22,.14,.07)) and 4-6 dead
   collapsed brown fronds hanging among them. Frond colour (.085,.20,.055) tint .85-1.15.
   1 trunk hull (A, B). Budget A/B ≤ 9k / 3k / 800; Young ≤ 4k / 1.2k / 400.

NP1 renders: `Lineup_Bush.png` (all seven, true scale, figure post, labels, heights);
`Detail_<asset>.png` three-quarter close views; `Assembly_Bush.png`: a 24 x 24 m patch with
14 Beech_Pole, 3 Beech_Mature, 1 Beech_Edge, 1 DeadSpar, 2 TreeFern and about 60 crown ferns
massed to the edge of a 1.6 m dark peat track, camera at 1.6 m eye height, 35 mm, looking
along the track, overcast light; this one is judged against photos 01 and 08.

### NP2: margin and high-country set (10 meshes; `build_native_open.py`)

7. `SM_NZ_Harakeke_A` (flax, 1.8 m, 36 leaves) / `_B` (2.4 m, 50 leaves, 3 korari). Clump of
   4-6 fans; keeled straps 8 cm wide, 1.5-2.4 m long, steep then arching 20-30° in the top
   third; outer leaves lean 50-60°; 15 % dead tan leaves (.40,.30,.15) hanging outward. Leaf
   (.07,.16,.075), edge and keel (.28,.10,.05). Korari: stalk (.20,.07,.04) radius 2 cm, 3.4 m,
   leaning 10-20°, 10-14 short upward side branches each carrying 6-8 pod quads (.08,.05,.03).
   Budget ≤ 5k / 1.6k / 400. No hull.
8. `SM_NZ_Coprosma_A` (mikimiki, 1.4 m) / `_B` (2.3 m). Divaricating lattice: 6-8 stems from
   the base, step 8-12 cm, angle 60-90°, 5 levels, twig (.22,.19,.14). Tiny leaves 1 x .6 cm
   single quads on the outer two levels, (.11,.17,.07), about 3,000 at LOD0. Silhouette a
   dense tangled mound, slightly flat-topped. Budget ≤ 10k / 3k / 800. No hull.
9. `SM_NZ_Matagouri_A` (1.1 m cushion) / `_B` (2.6 m small tree, .6 m trunk radius .06,
   crown 2.8 m, flat-topped). Rigid grey lattice with 90° zigzags, twigs (.33,.33,.30), a
   2-4 cm spine (4-triangle cone) at every node, very sparse tiny leaves (.18,.22,.12).
   Budget ≤ 10k / 3k / 800. B: 1 hull.
10. `SM_NZ_TiKouka_A` (cabbage tree, 5 m, trunk forks at 3 m into 3 heads) / `_B` (8 m, forks at
   2.5 m and again, 7 heads). Trunk radius .22 / .30, corky bark (.30,.28,.25) with fissure
   blotches (.17,.16,.14) 30 %. Each head: 70-90 keeled straps .7-.9 m x 5 cm radiating from a
   10 cm tuft, upper leaves erect, lower drooping; beneath each head a skirt of 20-30 dead
   tan straps (.38,.30,.17) hanging straight down. Leaf (.14,.24,.09). 2 hulls. Budget A ≤ 9k,
   B ≤ 12k / 3k / 800.
11. `SM_NZ_Kanuka_A` (6 m, young, dense, crown 2 m) / `_B` (10 m, mature, crown 5 m, bole clear
   to 3 m). Trunk radius .10 / .18, stringy bark (.28,.22,.16) with broken irregular pale
   strips (.40,.34,.26) along the grain; many fine ascending branches 30-45° from vertical;
   foliage as needle sprays (fan of 3 thin quads 6 cm long) about 2,500 at LOD0 (B), colour
   (.10,.18,.06) with paler tips (.16,.24,.09); crown open, upright, airy. 1 / 2 hulls.
   Budget ≤ 16k / 5k / 1.2k.

NP2 renders: `Lineup_Open.png`, `Detail_<asset>.png`, and `Assembly_Edge.png`: the bush wall
seen from 25 m out in the paddock (photo 09/10): 2 Beech_Edge, 4 Beech_Pole, 1 DeadSpar, a
TreeFern at the margin, a 6 m band of Coprosma A/B and two Harakeke in front, camera at 1.6 m.

### NP3: Unreal import and lineup (one Unreal, after NP1 and NP2)

- `Art/Unreal/import_native_plants.py` and `Art/import_native_plants.ps1` on the shrub-library
  pattern: `M_NZ_Foliage` through `dense_tussock_material.configure`; `M_NZ_Bark` opaque
  default-lit, vertex colour to base colour, roughness .9, specular .1, ISM and Nanite usage;
  slots assigned from the manifest; hulls through `one_convex_hull_per_ucx`, count asserted
  against the manifest; three authored LODs; screen sizes shrubs/ferns/flax [1, .18, .065],
  trees [1, .22, .08]; Nanite off; dimensions asserted within 2.5 cm;
  `unreal-import-report.json`, only `ok: true` counts. Uses `Art/wait_unreal_free.ps1`.
- `Art/Unreal/setup_native_plants_lineup.py`: `/Game/GrandTour/ArtTests/NativePlants/L_NativePlants`
  on the TussockStyle art-test pattern: a 200 m ground plane in dark peat, the kit in two
  rows 6 m apart at true scale, plus the NP1 bush assembly and the NP2 edge assembly rebuilt
  as instances, the project's sky and look layer on. `Play-NativePlants.bat` for the owner.
- `Art/Unreal/check_native_plants.py`: `-RenderOffScreen` captures at the owner angles
  (`feedback-owner-angle-gates`): on foot in the fern mass at 1.6 m, driver height 1.2 m from
  8 m, the lineup from 40 m, the bush track toward the sun, the edge wall from the paddock.
  Fable judges these against the photos before the owner is asked.

### Gate

The owner opens L_NativePlants, walks the fern mass on foot and drives the track, and names what
is wrong species by species. Nothing is placed in L_LidarStudy or L_Benmore until then; that is
LP3 in `docs/LIDAR_PLACE_PLAN.md` and a Benmore stage of its own.

## Stage log

- 2026-10-16: plan written; NP1 briefed.
- 2026-10-16 NP1 built (10 meshes x 3 LODs, validation ok, byte-stable, one-call
  `bash Art/build_native_plants.sh bush`). Fable's look at Lineup/Assembly/Detail renders against
  photos 01/08/10: FAIL on look, pass on geometry. Beech sprays read as maple-leaf fans on a
  thin pale sapling with a columnar crown; tree fern reads as a palm (13 straight flat fronds,
  gapped comb pinnae, thin pale trunk, string skirt); crown fern a sparse comb (18 flat fronds,
  pinnae gapped) and the assembly massing was rows at 0.1/m^2 with a grey void behind. NP1b
  correction briefed: fine dark foliage clusters in tiers for beech, darker mottled columnar
  trunks, overlapping pinnae and denser arching crowns for both ferns, 40 m closed stand at
  photo density under a bright overcast sky for the assembly.
- 2026-10-17 NP1b looked at: Assembly now carries photo 08's character (dark close-set columnar
  trunks against bright sky, massed crown ferns to the track edge, tree-fern umbrellas on black
  trunks with brown collars). Left for NP1c, folded into the NP2 brief: single beech crowns thin
  and see-through (cluster quads too small for a 22 m tree); moss reads as camouflage blotches;
  tree-fern collar reads as rag strips; horizon open beyond 40 m. NP2 briefed to the same agent.
- 2026-10-17 NP1c + NP2 built (20 meshes x 3 LODs, `bash Art/build_native_plants.sh all`,
  60 FBX validated ok). Fable's look at Lineup_Open / Assembly_Edge: ti kouka, harakeke,
  matagouri B, kanuka pass; the edge wall reads as a dark canopy wall with tree ferns at the
  margin. FAIL: coprosma reads as pale dead wiry twigs (photo 10's margin band is lush green
  broadleaf scrub); kanuka bark and matagouri too pale; thin sky band at the trunk bases.
  NP2b briefed: leafier darker coprosma, darker kanuka bark and matagouri, then NP3.
- 2026-10-17 NP2b/NP2c: coprosma now a shell-scattered leaf mound (A 8.5k / B 9.3k LOD0) that
  reads as a dense hedge in the edge band but speckled close up (4,100 leaves of 2.5 x 1.5 cm
  cover a third of a 2.3 m shell); matagouri and kanuka darkened. Held for after the Unreal
  look: NP2d = coprosma leaves 5 x 3 cm at the same count, then re-import the open set.
  NP3 (import, L_NativePlants lineup, captures) running.
- 2026-10-17 NP3 built: 20 meshes in /Game/GrandTour/Environment/NativePlants/v01 (3 LODs, hulls
  as manifest, DeadSpar Bark-only since Unreal drops the empty slot), L_NativePlants saved (rows,
  bush stand 278 + 2,342 ferns, edge stand 500 + 419 scrub, 7 NZ_ cameras, GTRunGameMode),
  `Art/native_plants.ps1 -Mode Import|Lineup|Check`, `Play-NativePlants.bat`. Fable's look at
  UE_Lineup / UE_TowardSun: materials and stand character hold; faults are the level's: ground
  sandy (MI_Env_Dirt), hard sun + .65 skylight leaves the bush interior black, edge wall faces
  away from the sun (EdgeWall/FernMass captures black); tree ferns read as palms at 40 m (LOD1
  strips thin). NP4 (Sonnet): coprosma leaves 5 x 3 cm, tree-fern LOD1 wider strips, peat
  ground, sun from the paddock side, skylight up, re-import, re-capture. Known pre-existing:
  M_GT_PostLook/M_GT_PostKuwahara fail one debug shader permutation on high-res shots.
- 2026-10-17 NP4 (Sonnet): coprosma leaves 5 x 3 cm (edge band reads as a dense green hedge in
  UE_EdgeWall, sun-lit now: sun pitch -40 yaw 90 int 6, skylight 2.5, fog .01), tree fern +2
  fronds LOD0 and 1.3x LOD1 pinnae, ground MI_Env_Bog (reads caramel, not peat). Check gate
  failed on brightness: FernMass mean 37/255, TowardSun 35 (trunks black in shade). Tree ferns
  at 40 m are at LOD2 (6 fan quads) because the tree screen sizes [1,.22,.08] put a 5 m plant
  on LOD2 at ~0.1 screen size. NP4b: small-tree screen sizes [1,.12,.04], peat MI
  (.06,.04,.025), skylight 5, sun pitch -55 int 5, rerun.
- 2026-10-17 NP4b: small-tree screen sizes [1,.12,.04] set; MI_NZ_Peat (M_GT_Environment child,
  BaseColor .06/.04/.025, roughness .95) on the ground; skylight 5 had no visible effect on the
  shade (FernMass 31, EdgeWall 27 means). Same symptom as the Benmore woodland; NP4c applies that
  level's fix: skylight 8 + a post volume with local_exposure_shadow_contrast_scale .65
  (balance_woodland_shadows.py). Tree ferns at 40 m still read as a flat parasol on a stick from
  eye height; accepted for the gate (that is a tree fern's distant silhouette), owner to judge.
- 2026-10-17 NP4c: skylight 8 + NZ_ShadowBalance post volume (local exposure shadow contrast .65,
  the Benmore woodland fix). Check gate PASS (FernMass 50, EdgeWall 41, TowardSun 38 not gating).
  Fable's look at UE_FernMass: peat track between massed crown ferns, close-set dark mossy
  trunks, canopy high, tree-fern collar; shaded trunks cool blue-black, ferns brighter than
  photo 01. GATE OPEN: owner runs Play-NativePlants.bat, walks the fern mass, drives the track.
  Nothing committed. Next after the verdict: LP3 placement in L_LidarStudy, Benmore stage.
- 2026-10-18 (from the LiDAR map placement, LP3a-c in docs/LIDAR_PLACE_PLAN.md): the kit is
  placed on L_LidarStudy at 147k canopy and 164k understory. Material gain: M_NZ_Foliage and
  M_NZ_Bark now carry a Tint VectorParameter (importer add_tint). Found in play-like captures:
  Beech_Mature/Pole crowns are too sparse and small for a closed canopy at 5-8 m spacing (sky
  through; 67% cover by ellipse but see-through crowns); crown-fern green reads saturated lime
  under daylight, photo 11 is grey-green; tree ferns read as palms beyond 30 m. Candidates for
  NP5 after the owner's lineup verdict.
- 2026-10-18 NP5 (Sonnet, ~0.38M): beech crowns rebuilt, structure unchanged: clusters 1.8x
  (Mature .86-1.28 m span, Pole .60-.90, Edge .81-1.20), 4/3/3 domed tiers with wobble, inner
  third filled at 40% plus core plates, colour (.035,.075,.028) / outer (.08,.15,.045), LOD1
  1.4x and LOD2 1.8x enlargement (LOD1 drops the 2 cm branchlets), LOD0 fill 95.7-95.9%.
  Coverage from below .82-.99, from the side .58-.81. Assembly from below: a near-closed dark
  ceiling, more closed than photo 08. Re-imported (10 bush meshes), map canopy rebaked
  (lidar_canopy_assets.py rebakes on a source signature). On the map: Bush_track sky 20% ->
  16% with a closed ceiling on the bush side; House_yard wall a continuous dark mass with
  spars, sky 15% -> 9%. Open: lit leaves bright and angular (canopy tint instance pending),
  far crowns discrete over brown ground in the overview (placement and far card).

