# OW landscape toolkit (ported from OWGameUE)

The landscape dressing toolkit from `D:\Dev\OWGameUE` (read-only source): 6 biome PCG graphs, three road types with a
bed-and-verge tool, a cliff wall, the painterly landscape material and trees, and a test map. Water is left out.
The port plan and its evidence are in `docs/LandscapeMigrationManifest.md` and `docs/landscape_migration/`.
Built 2026-09-26/27 in stages A (C++), D (script ports), B (assets, graphs) and C (test map, tools, docs).

## What's here

**Content** (not in git; same `/Game` paths as the source):
- `/Game/OWGame/Dev/DressingLab`: the graphs `PCG_OW{Forest,Meadow,Scree,Road,Cliff,Alpine}`, `M_OWDressingLab` +
  `MI_OWDressingLab_Style` (the landscape material), `Roads/` (`BP_OWRoad`, `_Dusty`, `_Gravel` and their MIs),
  `Cliffs/BP_OWCliffWall`, the OW foliage masters, MIs and tree variants.
- `/Game/OWGame/Dev/L_OWWorldCanvas_sharedassets`: the 13 layer infos `OW_<Layer>_LayerInfo`.
- Vendor: `/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment` + `StylizedPack_Common` (grass, rocks, RVT
  `RVT_AM_01_Material`), `/Game/MWLandscapeAutoMaterial`, `/Game/3DAssets` (Kasyanik trees, licence file kept),
  `/Game/Materials`, `/Game/Textures`.
- `/Game/GrandTour/Test/L_OWToolkitTest`: the test map (below).

**Code:**
- Runtime (`Source/GrandTour/Dressing/`): `UOWRoadBedComponent` (the Details button **Apply Bed & Verge**, Python
  `apply_bed_and_verge()`), `FGTDressingTestRunner` (the `-GTDressingTest` smoke test, dispatched by `AGTRunGameMode`).
- Editor module `GrandTourEditor` (`Source/GrandTourEditor/Private/Dressing/`):
  - `-run=OWCreateBiomePCG`: (re)builds the 6 graphs from the C++ baselines (river code stripped).
  - `-run=OWCreateTreeVariants`: derived tree meshes from the vendor trees.
  - `-run=OWPaintRoadVerge -Map=<map>`: stamps OW_RoadVerge under every `BP_OWRoad*` spline.
  - `UOWBedStampComponent` / `AOWBedStampActor`: a sculpt stamp (a `ULandscapeTexturePatch`) for channels, steps,
    hillside benches.
  - `UOWToolkitSetupLibrary`: `sample_toolkit_test_height_cm`, `toolkit_test_layer_at`,
    `build_toolkit_test_landscape` (Python), used by the test-map script.
- Config: the CoreRedirect `/Script/OWGameUE.OWRoadBedComponent` -> `/Script/GrandTour.OWRoadBedComponent`,
  `r.Nanite.AllowVoxels=1`, a 256 MB VT pool; plugins PCG, GeometryScripting, LandscapePatch.

**Scripts** (`Art/dressing/`): one `.bat` per headless Unreal step, each ending `if "%GT_NOPAUSE%"=="" pause`.
`Art/dressing/ported/` holds the source's Python scripts, ported; its `README.md` says which ones are pipeline,
regen-only or reference, and which need a ticking editor.

## Regeneration order

Only when rebuilding from scratch; each step stomps what the next one tunes.

1. **Tree variants:** `-run=OWCreateTreeVariants` (below).
2. **Biome graphs:** `Art\dressing\create_biome_pcg.bat`.
3. **Tune:** `Art\dressing\tune_meadow_look.bat` (restores the source's live knob values; always after step 2).
4. **Test map:** `Art\dressing\setup_toolkit_test_map.bat overwrite`.
5. **Verge:** `Art\dressing\paint_road_verge.bat`.
6. **Ticking pass:** `powershell -NoProfile -ExecutionPolicy Bypass -File Art\dressing\tick_harness.ps1`.
7. **Smoke test:** `Art\dressing_toolkit_test.bat`, or `bash Art/suite.sh dressing_toolkit`.

## Commands

Close the editor first (no process whose command line holds `GrandTour.uproject`). Run from PowerShell or cmd, never
Git Bash. Set `GT_NOPAUSE=1` for unattended runs. Gate on each report JSON, not the exit code.

| command | what | report / log |
|---|---|---|
| `UnrealEditor-Cmd.exe C:\GrandTour\GrandTour.uproject -run=OWCreateTreeVariants -Unattended -NullRHI -NoSplash -NoSound` | tree variants | `LogOWCreateTreeVariants` in the log |
| `Art\dressing\create_biome_pcg.bat` | the 6 graphs | `Saved\Logs\create_biome_pcg.log` |
| `Art\dressing\tune_meadow_look.bat` | knob values onto LGTs + graphs | `Art\dressing\tune_meadow_look_report.json` |
| `Art\dressing\audit_toolkit.bat [tag] [resave]` | registry audit: missing deps, water names, `/Script/OWGameUE` | `docs\landscape_migration\audit_<tag>.json` |
| `Art\dressing\graph_node_counts.bat [tag]` | read-only node counts per graph | `docs\landscape_migration\graph_nodes_<tag>.json` |
| `Art\dressing\setup_toolkit_test_map.bat [overwrite]` | builds `L_OWToolkitTest` headless | `Art\dressing\setup_toolkit_test_map_report.json` |
| `Art\dressing\paint_road_verge.bat [/Game/map]` | verge commandlet, with `-AllowCommandletRendering` | `Saved\Logs\paint_road_verge.log` (`LogOWPaintRoadVerge`) |
| `Art\dressing\tick_harness.ps1 [-Task <py>] [-TimeoutMinutes 25]` | full editor runs `tick_apply_and_generate.py` | `Art\dressing\tick_apply_and_generate_report.json` |
| `Art\dressing_toolkit_test.bat [gpu]` | smoke test, `-game -NullRHI` | `Saved\Logs\dressing_toolkit_test.log` (`GTDRIVETEST`) |
| `Art\dressing\copy_closure.ps1 [-DryRun]` | the stage B byte copy from the source (refuses existing files) | `docs\landscape_migration\copied_files.txt` |

## The test map and the smoke test

`/Game/GrandTour/Test/L_OWToolkitTest`, not partitioned, no game-mode override (GTRunGameMode, the global default).
- **Landscape:** 505 x 505 vertices (8 x 8 components of 63 quads), 100 cm, origin 0, so 0..504 m. A 3 x 3 grid of
  168 m cells, one biome layer each (manifest 9.C.1), a radius-4 box blur between cells. Scree hill at (252, 420) m,
  70 m high; alpine hill at (420, 420) m, 40 m high with a snow cap. Material `MI_OWDressingLab_Style`, RVT
  `RVT_AM_01_Material`, the 13 layer infos registered as target layers.
- **Actors:** sun (atmosphere sun), SkyAtmosphere, SkyLight (real-time capture), height fog; one RVT volume over the
  landscape bounds; 6 `PCGVolume`s `OWTEST_PCG_<Biome>` over the whole landscape (50400 x 50400 x 10000 cm), graph
  `PCG_OW<Biome>`, tag `OWBiome.<Biome>`, generate on demand, not partitioned; `BP_OWRoad`, `BP_OWRoad_Dusty`,
  `BP_OWRoad_Gravel` in columns 0, 1, 2 (4 points each, rows 0-1); `BP_OWCliffWall` on a 52 m arc around the scree
  hill's south side; a PlayerStart at (84, 84) m facing +Y.
- **Setup numbers (2026-09-27):** height -149.6..7017.5 cm, 38 weightmap textures, painted vertices per layer: Meadow
  29584, MeadowLush 30272, MeadowDry 29756, Bare 60531, Alpine 19712, Snow 3817, Forest 30272, ForestBeech 16192,
  ForestBirch 16192, ForestFir 15916, ForestOak 15916, Scree 14089, RoadVerge 0 (until the verge step).
- **Verge:** 3 roads, 5969 vertices stamped; read-back at 31 centre samples: verge 255, other layers 0.
- **Ticking pass (2026-09-27, run 2):** 45 s wall (warm caches), the task 23 s. Height by a line trace down on
  the landscape; before -> after `apply_bed_and_verge`, in cm, at half each road's length: BP_OWRoad 27.5 -> -52.2
  (spline -51.9), Dusty 49.7 -> 3.3 (spline 3.7), Gravel 9.8 -> 11.1 (spline 11.6). At the middle control point
  (index 2) it barely moves (-100.8 -> -100.8, 60.2 -> 59.4, 81.2 -> 81.2): the points sit at the layout height. Verge weight 1.0 at all
  six points before and after (the commandlet painted it). Generation settled in 8 s; ISM instances saved per volume:
  Forest 1108, Meadow 128, Scree 163, Road 1624, Cliff 78, Alpine 58. Run 1 (cold: shaders and mesh builds, 206 s)
  counted 1121 / 213 / 327 / 2958 / 110 / 116 after 104 s, with PCG warning "Identical ISM Component spawn" on one
  volume; that map was rebuilt.
- **Smoke test** (`-GTDressingTest`): PASS needs 3 `BP_OWRoad*` actors each with a `UOWRoadBedComponent`, the
  landscape material `MI_OWDressingLab_Style`, exactly the 13 non-water layer infos in the weightmap allocations
  (none named Bed or RiverWet; OW_RoadVerge must be painted), and ISM instances > 0 saved on each of the 6
  `OWBiome.*` volumes. It is in `Art/suite.sh`'s default list as `dressing_toolkit`. 2026-09-27: PASS (14 s), and
  `bash Art/suite.sh dressing_toolkit terrain` 2 PASS.

## Water exclusions

Nothing water-related was ported: no River/ assets, no `PCG_OWRiver`, no water village materials, no Water plugin.
- The 4 graphs that referenced `OWRiverMesh` were regenerated from the stripped commandlet; no redirect exists for
  that class on purpose.
- `M_OWDressingLab` still samples OW_BedGravel, OW_BedSand, OW_BedRock and OW_RiverWet (4 of its 17 layer samples).
  They have no layer infos and weigh 0: the Paint panel lists them, harmless.
- The bed/wet layer infos stayed in the source; only the 13 WorldCanvas layer infos came over.
- The ported scripts pass `grep -i -E "river|water|OWGameUE"` with nothing found.

## Leg dressing: the GT variants on a GrandTour leg (LD1-LD8a)

The plan and its decisions: `docs/LEG_DRESSING_PLAN.md`; the build log: `docs/VEHICLE_BUILD_SYSTEM.md` section 62.
Only The Hide (`/Game/GrandTour/Legs/L_Leg03`) is dressed. The OW graphs, `tune_meadow_look` and `L_OWToolkitTest`
are untouched by all of it.

**The GT variant mode.** `Art\dressing\create_biome_pcg.bat GT` (`-run=OWCreateBiomePCG -Variant=GT`) builds
`PCG_GT_Forest/Meadow/Scree/Alpine/Brush` into `/Game/GrandTour/Dressing/PCG/` from the same builders (report
`docs\landscape_migration\ld4_gt_graphs.json`). On top of the OW baselines it adds tree size classes (Sapling, Young,
Mature; instance scale about 0.25-1.7, x the variant's baked prescale about 0.25-4.2), a physical class on every
spawner (collision profile plus one component tag: `GTVeg.Solid` BlockAll, `GTVeg.Soft.Brush` / `.Sapling` / `.Young`
NoCollision, none for unclassed), forest understorey and the `Thicket` brush graph. Soft classes are always plain ISM
(the bend swaps instances); the solid pack meshes are HISM. Never run `tune_meadow_look` on the GT graphs.
Tree variants (`create_tree_variants.bat`) give every tree, dead tree and stump one trunk capsule (canopy never blocks).
Since LD7 the GT soft pack meshes (`SM_BirchBush_01..05_Summer`, `SM_CoverPlant_01..04_Summer`) are Nanite passthrough
copies, `/Game/GrandTour/Dressing/Nanite/SM_GTN_<name>` (`Art\dressing\create_nanite_pack.bat`, which runs
`-run=OWCreateTreeVariants -GTNanitePack`; the vendor meshes are untouched): run it before `create_biome_pcg.bat GT`.
`create_biome_pcg.bat GT hism` (`-GTSoftHISM`) is the LD7 A/B only; PCG turns an HISM descriptor into a plain ISM for
any Nanite mesh anyway, so with the copies it changes nothing.

**Perf dials** (LD7 took the cut order to its end; LD8a, 2026-09-28, undid the three that measured no gain):
- kept: `grass.CullDistanceScale=0.6` and `grass.DensityScale=0.5` in `Config/DefaultEngine.ini` `[SystemSettings]`
  (every landscape grass type; the LGT assets untouched; 1 = their own values), and the Nanite pack copies above;
- `GTBrushDensityScale` in `OWCreateBiomePCGCommandlet.cpp` (1 since LD8a; LD7 had 0.5): the GT soft brush streams
  (understorey and Thicket bushes and cover plants) at that share of LD4's densities; rebuild the graphs and regenerate;
- the forest band in `GTTerrain::HideSpec()` (`AddHideBiomes`): the 300 m noise from 0.70 (LD7 had 0.75), the ring
  0.64-0.70 (Forest + ForestFir 27.1 % of the off-road land, the biome test's floor 22 %); push it with
  `setup_dress_hide.bat pushspec`, then regenerate;
- `r.Nanite.AllowVoxels` in `[/Script/Engine.RendererSettings]` (1 since LD8a; LD7 had 0; read-only, so a restart).
Step 2 (tree shadows at distance) was not taken: a 5.8 ISM descriptor has no per-primitive shadow distance. The
measured numbers per step: `docs/VEHICLE_BUILD_SYSTEM.md` section 62. The per-pass GPU profile (LD8a; LD8b ran `-Series lean -Tag ld8b -MaxWaitMin 3 -Proceed`: two views runs, then hide_shots off and on):
`powershell -NoProfile -ExecutionPolicy Bypass -File Art\dressing\ld8_profile.ps1 [-Pairs 3]` (hide_shots dressing off
and on, then the biome views, each with `-GTProfileGPU`: after hide_11_track, hide_17_border_low, hide_21_rut_wet,
hide_29_ford_shallow, view_forest and view_thicket the run holds until the shader and asset compilers are empty, then
`ProfileGPU` dumps the pass tree to the log; a GPU cool-down guard waits before each run), then
`python Art\dressing\ld8_profile.py` -> `docs\landscape_migration\ld8_profile.json`, `ld8_profile\ld8_profile.md` and the
trimmed trees in `ld8_profile\`. `-GTProfileGPU` works on any hide_shots run (`-GTProfileCaptures=N`).

**Look dials for the style pass** (LD8a, LD8b; none of it is final art). The GT graphs' leaves are summer copies; the OW MIs,
the pack MIs and the OW graphs stay autumn and byte-unchanged. `Art\dressing\retint_summer.py` holds the one table
(`PALETTE`, per row: Beech 0.09 0.21 0.05, Birch 0.16 0.28 0.07, Oak 0.07 0.17 0.04, Fir 0.04 0.11 0.05, Bush 0.10 0.22
0.06, linear; `VALUE_STEP` 0.25 for the second / gradient colours; `TONES`, the per-tree ToneWarm/ToneCool shifts) and
its docstring the mapping onto each master's parameters. To retune: edit the table, `Art\dressing\retint_summer.bat
apply` (re-tints the copies and rewrites `Art\dressing\retint_summer_map.txt`), `create_biome_pcg.bat GT`,
`setup_dress_hide.bat`, the tick harness. `retint_summer.bat` alone is the read-only inventory
(`docs\landscape_migration\ld8_warm_materials.json`: every material the GT graphs spawn, its parent, each colour's hue).
The copies, in `/Game/GrandTour/Dressing/Materials/` (source -> copy):
- `M_OWFoliageMaster` children: `MI_OWFoliage_Beech{,_ToneWarm,_ToneCool}` -> `MI_GT_Leaf_Beech{,_ToneWarm,_ToneCool}_Summer`;
  the same for Birch and FirTree (-> `MI_GT_Leaf_Fir*`); on the OW bushes `MI_OWFoliage_Beech` / `_Birch` ->
  `MI_GT_Leaf_Bush_OWBeech_Summer` / `MI_GT_Leaf_Bush_OWBirch_Summer`;
- pack `M_Tree_Leaf` children: `MI_BirchTree_Leaf_01_Summer` (the birch bushes) -> `MI_GT_Leaf_Bush_PackBirch_Summer`,
  `MI_CoverPlants_01_Summer` -> `MI_GT_Leaf_Bush_CoverPlant_Summer` (the cover plants have no row; they take the bushes'),
  `MI_OakTree_Leaf_01_Summer` -> `MI_GT_Leaf_Oak_Summer`, `MI_OakTree_IvyLeaf_01_Summer` -> `MI_GT_Leaf_Oak_Ivy_Summer`
  (no oak grows on The Hide: no OW_ForestOak layer).
Trunk and bark MIs are not copied. The pack rocks (`M_Props`, brown) are warm by hue but are not leaves: left alone.
- The masters (LD8c): the pack masters lack the Voxels usage flag, so under `r.Nanite.AllowVoxels=1` the Nanite pack
  copies (the birch bushes) drew the default checker in game ("missing usage flag Voxels! Default Material will be used
  in game"). `retint_summer.py apply` keeps GrandTour copies `/Game/GrandTour/Dressing/Materials/Masters/M_GT_Tree_Leaf`
  and `M_GT_Tree_Bark` (Voxels, Nanite and ISM usage set), reparents every pack-derived `MI_GT_*` to them and gives the
  Nanite copies' bark `MI_GT_BirchTree_Bark_01_Summer`. The vendor masters and MIs are only read. The pack albedo moves
  only when it is warm (the cover plants); the birch bushes and the oaks keep the vendor Base Albedo Color.
- The grass (LD8b): `M_GT_Landscape`'s grass output wears `/Game/GrandTour/Dressing/Grass/LGT_GT_*`, copies of the 10
  OW grass types (`Art\dressing\gt_grass_copies.bat`, then `Art\dressing\ld2_landscape_material.bat`; the OW types are
  only read). `gt_grass_copies.py` `VARIETY_FLAGS` sets on every variety `bCastDynamicShadow` false, `bCastContactShadow`
  true and `bAffectDistanceFieldLighting` false - the values the OW types already had (LD8b found them so), so today the
  copies differ from the OW types only in name; their densities, meshes and cull distances are the style pass's dials.
- The small plants (LD8b, `OWCreateBiomePCGCommandlet.cpp`, GT only): Soft.Brush, Soft.Sapling and unclassed spawners get
  `bAffectDistanceFieldLighting` and `bAffectDynamicIndirectLighting` false on their descriptors (Young and Solid keep
  both); bushes and cover plants `WorldPositionOffsetDisableDistance` `GTSmallPlantWPODisableCm` (5000 cm). The report
  (`ld4_gt_graphs.json`) tags them `:noLumenDF` and `:wpo5000cm`.

**The leg's side.** The biome layout is the spec's `Biomes` (`FGTBiomeRule`, `DA_Terrain_Hide`; the C++ default is
`GTTerrain::HideSpec()`), splitting the off-road Scrub weight into `LI_<Layer>` layers with Scrub's physical material.
`AGTDressingExclusion` (editor only, tag `OWDressing.Exclude`) holds QueryOnly boxes over the route and alt routes
(half width + 4 m), the Mud/Ford sections (+10 m), the mud patches (+5 m) and every gameplay actor (+5 m; leg volumes
at their `Extent`, harvest nodes at their `GreyboxSize`: the sizes they take in the game). `gt.Look.Dressing 0/1`
(`-GTLookDressing=N`) hides the `GTBiome.*` / `OWBiome.*` actors and the grass.

**Vegetation physics** (`UGTVegetationSubsystem`, runtime). Every dial is in Project Settings > `UGTVegetationSettings`:
per class (Brush / Sapling / Young) the full-push tilt, break tilt, impact break speed, sustained-push hold, stiffness K,
class force cap (x m g) and debris mass; then the footprint pad (30 cm), push depth (50 cm), brush contact radius scale
(0.5 x max extent), minimum trunk radius (5 cm), hash cell (4 m), rise / recover tau (0.05 / 1.5 s), proxy pool (128),
total force cap (0.35 m g), the speed factor floor (0.3) and full speed (10 m/s), sustained push (0.9), debris impulse
scale (0.8), debris freeze (20 s) and debris cap (24). Console: `gt.Veg.Reindex` (rebuild the index from every
`GTVeg.Soft.*` ISM in the world; run it in a running game after regenerating in the editor), `gt.Veg.Stats` (the index,
active set, debris and the per-frame work). `gt.Look.Dressing 0` makes it inert and restores everything.

**Dressing The Hide, in order** (close the editor first; each a headless step with a report JSON):
1. **Spec:** `Art\dressing\setup_dress_hide.bat pushspec` rewrites `DA_Terrain_Hide` from `GTTerrain::HideSpec()` (the
   owner's edits to the asset are lost); without `pushspec` the asset is kept and must carry biome rules.
2. **Setup:** `Art\dressing\setup_dress_hide.bat` - `RebuildLandscape` through the map's builder (actors regrounded; a
   gameplay actor that comes back more than 1 cm off its height over the spec's ground is put back, over 1 m fails),
   `RVT_AM_01_Material` on the landscape plus one RVT volume over it, the exclusion rebuilt, five `GTHIDE_PCG_<X>`
   volumes (`GTBiome.<X>`, GenerateOnDemand, not partitioned), save. Rerunnable: it replaces its own `GTHIDE_*` actors.
   Report `docs\landscape_migration\ld6_hide_setup.json`.
3. **Generate:** `set GT_TICK_MAP=L_Leg03`, then `powershell -NoProfile -ExecutionPolicy Bypass -File
   Art\dressing\tick_harness.ps1 -Task C:\GrandTour\Art\dressing\tick_generate_only.py -Map /Game/GrandTour/Legs/L_Leg03`
   (the editor window shows; about 1.5 min warm). The task cleans every volume first (a map generated before reads
   "generated" at once, and the save caught the old output half replaced), then generates. Report
   `docs\landscape_migration\ld6_hide_generation.json`: instances per graph and class, the tree scale histogram, the
   collision and component-class checks.
4. **A running game** that was open during the regeneration: `gt.Veg.Reindex`.
5. **Check:** `bash Art/suite.sh route_clear` (`Art\route_clear_test.bat`: the swept 3 x 4 x 2 m corridor along the route
   and alt routes, the 5 m around the gameplay points).

Any later `RebuildLandscape` (the builder's Details button included) means steps 2-3 again: the generated instances
stay where the old ground was, and the setup's last log line says so. Other tools: `Art\dressing\veg_hide_drive.bat
[null]` (100 m through the thicket nearest the route, dressing on then off: frame, GPU, vegetation work),
`Art\dressing_views.bat` (four biome views, dressing on and off; since LD8a view_thicket looks from 15 m off the route
into the nearest Thicket-dominant ground), `Art\sky_shots.bat` (its clump spot now aims at the
nearest dressing plant when the spec has biomes).

## Pitfalls

From the source (full list, with file:line: `docs/landscape_migration/pitfalls_from_source.md`), the ones that bite
here:
- PCG generation and landscape edit-layer merges do nothing in a commandlet: they need a ticking editor (the harness).
- Git Bash rewrites `/Game/...` arguments; run Unreal from PowerShell or cmd. Never name a PowerShell variable
  `$script` (pass `"-Script=$py"`), never pipe UnrealEditor-Cmd into `Select-Object`.
- `unreal.log` never reaches stdout: every step writes a report JSON with a per-step `ok`. Gate on it; exit codes
  lie both ways.

Paid in this port:
- **Stage A, unity builds:** files git sees as modified compile outside the unity groups (adaptive unity), so two
  `.cpp` files with the same anonymous-namespace helper name build fine until the commit, then collide (C2084). After
  committing, touch a `.Build.cs` and rebuild to catch it.
- **Stage A, landscape under NullRHI:** 5.8 always has edit layers and their GPU merge never runs under NullRHI, so
  `build_toolkit_test_landscape` writes the final weightmaps on the CPU, then `PostEditChange` on each weightmap
  texture and `UpdateAllComponentMaterialInstances`. The 5.7+ `SetAlphaData` has no weight-adjust flags.
- **Stage B:** `-Script=` drops everything after the script path; pass script arguments in environment variables
  (`GT_AUDIT_TAG`, `GT_TOOLKIT_OVERWRITE`). Assets were byte-copied (identical paths, SHA-1 checked), not migrated.
- **Stage C, the verge commandlet:** a commandlet runs NullRHI even without `-NullRHI` (`FApp::CanEverRender()` is
  false), so the merge pump reports up-to-date at once and the read-back fails (min verge 0). The source recorded the
  same failure and moved to the in-editor script. `-AllowCommandletRendering` gives it a real RHI and it passes.
  The first such run took 8 min (shaders) and exited 1 because `BuildAll` logged "BuildGrassMapsNowForComponents()
  took too long" (grass maps, which the editor rebuilds); the second took 76 s and exited 0. The
  `LogOWPaintRoadVerge` read-back line is the gate.
- **Stage C, new_level:** `delete_asset` on the map returns True but leaves the `.umap`, and `new_level` then refuses
  the path. The setup's `overwrite` opens the map and destroys every actor instead.
- **Stage C, splines:** `set_editor_property` on a BP's spline component notifies, which reruns the construction
  script and replaces the component: the old handle reads 0 points. Set `spline_has_been_edited` ("Override
  Construction Script", so the points survive later reruns) with `PropertyAccessChangeNotifyMode.NEVER`, then
  re-fetch the component.
- **Stage C, PCGVolume:** `spawn_actor_from_class` gives it the box-volume factory's 200 cm cube brush; scale it by
  size / 200. Its brush ignores every collision channel.
- **LD6, the builder's ground trace:** `RebuildLandscape` measures each actor's height over whatever static is under it
  with a WorldStatic object query, and a PCG volume's brush answers it: the first rebuild of a dressed map put every
  leg actor 140 m under the ground (the volume's top face read as the old ground). The trace now skips volumes, the
  exclusion and `GTBiome.*` / `OWBiome.*` actors, and `setup_dress_hide.py` gates on a witness. A bog post
  (`Post_Bog_1_1`) still comes back 25.3 cm higher on every rebuild; the setup puts it back.
- **LD6, exclusion bounds:** `AGTWaterSheet`'s `SurfaceMesh` uses absolute location and has no sections in the editor,
  so its empty box sat at the world origin and the ford sheet's gameplay box grew to 1055 x 82 m; empty bounds are
  now left out. Leg volumes and harvest nodes are sized at BeginPlay (the editor holds the 1 m defaults), so the
  exclusion uses their `Extent` / `GreyboxSize`.
- **LD6, generation order:** the exclusion is built from where the gameplay actors stand at that moment; after a
  broken rebuild it excluded nothing round them. Always regenerate after the setup, never before.
- **LD7, collision in the game:** a PCG volume's brush and the exclusion's boxes answer WorldStatic object queries in an
  uncooked game (`-game`, PIE loads the editor-only exclusion too): the water field's bed trace, the leg volumes'
  marker trace and the tests' ground traces landed on a volume's top face 140 m up (the terrain test's "on the
  ground: 0", the water test's empty ford). The setup sets the volume brushes to NoCollision (PCG samples a volume
  through its own sceneless body) and the exclusion turns its boxes off in `BeginPlay`.
- **LD7, the terrain test and the trees:** step 3 sends the car flat out off the rally bend into the scenery; with the
  dressing it rolls on the trees there, and the damaged car then fails the bog escape and the raised ford. The terrain
  test runs with `-GTLookDressing=0`; the dressing has its own tests (`route_clear`, `veg`, `biome`).
- **LD7, thermal throttling voids perf runs:** after about four hours of back-to-back GPU runs the laptop GPU sat at
  86 C with `sw_thermal_slowdown` active (`nvidia-smi --query-gpu=temperature.gpu,clocks_event_reasons.active
  --format=csv`) and two `hide_shots` runs read 40-2000 ms frames. Check the temperature before a perf run and let the
  machine cool between sets; set aside any run whose steps read hundreds of ms.
- **Stage C, the tick harness:** Python cannot call `GameplayStatics.break_hit_result`; `HitResult.to_tuple()`
  runs the native break (location is the first Vector, the hit actor the first Actor). A save pumps Slate, so the
  post-tick callback fires again inside the step: guard it against re-entry ("generator already executing"). The
  first full-editor open ran 3.5 min; the next 45 s. The harness kills the editor if it has not quit 180 s after the
  task reports finished, and deletes the bootstrap in a `finally` either way.

## Editor / PIE checklist (for the owner; Claude judges no look)

Copied verbatim from manifest 9.E.

Open `L_OWToolkitTest`. The first open compiles many shaders, because Substrate converts every migrated material; let it finish.

1. **Layers.** The Paint panel lists the 13 OW layers with their layer infos. It also lists the 4 unpainted river layers from the material; that is expected and harmless.
2. **Biomes.** Each cell reads as its biome:
   - meadow, lush and dry differ in colour and grass;
   - the forest cells show generic, beech, birch, fir and oak;
   - rocks sit on the scree hill's steep faces;
   - firs and rocks cover the alpine hill, with a snow cap on top;
   - the bare cell is bare.
3. **Borders.** The 4 m cross-fades between cells read soft, with no hard seams or tiling stripes.
4. **Grass density.**
   - Compare the meadow grass and flowers per cell against your memory of the OWGameUE lab.
   - Check the grass pop-in ring distance.
   - There is no grass on road beds or verges.
5. **Trees.**
   - No double "puff". The variants are baked, so a leaf that swells or sways twice means WPO is still on their material.
   - The painterly trunk normals are intact.
   - Nanite foliage looks fine up close and far away.
   - No giant or tiny outliers.
6. **Roads.** Each of the three types has:
   - its bed carved along the spline;
   - a painted verge;
   - no trees or rocks on it;
   - its own dressing.

   Then move one spline point and click **Apply Bed & Verge** in Details: the carve follows. The verge stamp is additive, so the old strip stays painted.
7. **Cliff.** Cliff rocks line the scree hill's south base.
8. **RVT blend.** Ground cover and prop bases pick up the landscape colour. There is no black, white or smeared RVT (which would point to the volume bounds).
9. **Substrate.** Open `D:\Dev\OWGameUE` `L_OWDressingLab` side by side (read-only; don't save it). Compare the landscape, leaves and road MIs for colour or roughness shifts.
10. **Perf** (PIE, `stat unit`, `stat gpu`). Note the frame and GPU time standing in the oak forest cell, standing in the meadow cell, and driving across. Write the numbers down next to L_Proving's.
