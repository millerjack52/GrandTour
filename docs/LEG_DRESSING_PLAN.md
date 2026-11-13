# Leg dressing plan: the OW toolkit on GrandTour legs

Written by Fable, 2026-09-27. Status: **approved 2026-09-27** ("go with your recommendations. Ensure a range of tree scales, and allow for dense vegetation which can be affected by the car physically"). Build stages LD1-LD7, in agent order per section 8.

This plan wires the OW landscape toolkit (docs/LandscapeToolkit.md, VEHICLE_BUILD_SYSTEM section 59) into the legs.

---

## 1. What the legs are today

| map | ground | notes |
|---|---|---|
| L_Leg01 / 02 / 04 / 05 | greybox floor boxes, no landscape | need terrain specs first (BACKLOG:63): out of scope |
| **L_Leg03 The Hide** | spec-built, 2017² verts (about 2 km square), heights -22..92 m, `M_GT_Landscape`, 1.63 km route, fords, bogs | the pilot; Clear weather |
| L_Proving | spec-built, 378 m, `M_GT_Landscape` | stays undressed (test ground) |

What the game depends on:
- **Grip.** Driving grip comes from each layer info's physical material (`GTTractionComponent.cpp:144-161`), and Scrub drives as `PM_Dirt` (`GTVehicleSetupLibrary.cpp:628-636`). A layer with no physical material drives as **Tarmac**.
- **Ground material.** `M_GT_Landscape` carries `MF_Weather`, `MF_TrackPaint` and the mud-patch holes, and uses both of its MPCs.
- **Rebuild.** Everything is rebuilt from one editable `FGTTerrainSpec` (`RebuildLandscape`).
- **Collision today.** The OW PCG spawners set **`NoCollision` on every instance** (`OWCreateBiomePCGCommandlet.cpp:299`). As ported, the car drives through every tree and rock.
- **Tree scales today.** PCG transforms run 1.0-1.5 (XY) and 1.0-1.7 (Z); the tree variants add prescales of 1.0-2.45 (`OWCreateTreeVariantsCommandlet.cpp:58-100`). There are no saplings or young trees; the only small woody meshes are bushes (0.7-0.85) and stumps.

## 2. The approach

1. **The ground stays GrandTour's.**
   - The spec gains **biome rules** that split only the off-road (Scrub) weight into biome layers: the 10 OW names plus a GrandTour **`Thicket`** layer.
   - Each biome layer info gets the off-road physical material (`PM_Dirt`), so driving on the ground is unchanged.
   - `M_GT_Landscape` gets a tinted row per biome, the OW grass output and an RVT output. The MPC count stays at 2.
2. **GrandTour graph variants.** The biome commandlet gains `-Variant=GT`. It builds **`PCG_GT_Forest/Meadow/Scree/Alpine/Brush`** into `/Game/GrandTour/Dressing/PCG/` from the same builders; their baselines are the tuned OW values, which stage B verified as baked. On top of those, the GT variants add:
   - **size classes** for trees;
   - **physical classes** (solid / soft / none) per spawner;
   - a **dense brush** graph on `Thicket`;
   - **forest understorey**.

   The OW graphs, `tune_meadow_look` and `L_OWToolkitTest` stay untouched.
3. **Solid vegetation** (mature trees, dead trees, stumps, logs, rocks) blocks with simple collision. The tree variants are regenerated with a **trunk capsule** (canopy never blocks).
4. **Soft vegetation** (bushes, cover plants, saplings, young trees) has no physics bodies. A runtime **`UGTVegetationSubsystem`** keeps a spatial hash of those instances and does three things when the car pushes through:
   - **bends** each instance visually (per-instance tilt with a spring back);
   - **resists** the car with forces;
   - **snaps** saplings and young trees into physics debris above a speed.
5. **Exclusions.** GrandTour tells PCG where not to dress through the toolkit's tag exclusion (`OWDressing.Exclude`, any actor with primitive bounds). The source is a spec-built, editor-only box actor covering the route, alt routes, fords, mud and bog, gameplay points and interactables.

## 3. Stages

Rules: `docs/LandscapeMigrationManifest.md` 9.0, plus:
- `bash Art/suite.sh` once per stage;
- touch a `.Build.cs` and rebuild after committing (the unity trap);
- one Unreal process at a time;
- Opus executes and Fable judges.

### LD1. Biome rules in the spec (C++)

- **`FGTBiomeRule`** in `Terrain/GTTerrainGenerator.h`. Fields:
  - `FName Layer`;
  - `MinHeightM`, `MaxHeightM`, `FadeM`;
  - `MinSlopeDeg`, `MaxSlopeDeg`, `FadeDeg`;
  - `NoiseWavelengthM`, `NoiseMin`, `NoiseMax`, `NoiseFade`, `Seed`.

  A zero means "no limit". A noise band (min and max) lets one rule describe a ring, such as a forest edge.
  - **As built (650e0cd):** noise goes through a normal-CDF remap, so it is uniform. A band `a..b` therefore covers about `(b - a)` of the land before the other limits.
  - **LD1b (added 2026-09-27):** each rule also gets `SectionKinds` (a bitmask of `FGTRouteSection` kinds) and `MaxSectionDistM`. When set, the mask is 1 within that distance of any route section of those kinds and fades over `FadeM` beyond it.
- **`FGTTerrainSpec::Biomes`** (`TArray<FGTBiomeRule>`) and `FName FallbackBiome`. Empty means exactly today's behaviour.
- **Layer indices.** The six GrandTour layers keep indices 0-5, and biome layers are appended at 6 and up, in rule order.
  - At each vertex, the off-road weight is redistributed by priority compositing: `w_i = mask_i * Π_{j<i}(1 - mask_j)`, the remainder goes to `FallbackBiome`, and the result is normalised to the old off-road weight.
  - `LayerAt` keeps returning 0-5 (a biome counts as its off-road parent). A new `BiomeAt` returns the biome name.
- **`BuildLegLandscape`** writes `LI_<Layer>` (e.g. `LI_OW_Meadow`, `LI_Thicket`) into the leg layer folder, with LayerName = the rule's layer and the off-road layer's physical material.
- **Tests.** `terrain` and `hide` pass unchanged. A new headless check covers:
  - the Hide spec with no biomes gives a hash of heights and weights identical to today;
  - with biomes: heights and layers 0-3 and 5 are byte-identical, and at every vertex the biome weights sum to the old Scrub weight (±1).

### LD2. The ground rows (Python, `Art/Unreal/setup_m6_hide.py` `build_landscape_material()` `:258`)

- **Rows.** One row per biome name: Meadow, MeadowLush, MeadowDry, Forest, ForestBeech, ForestBirch, ForestFir, ForestOak, Scree, Alpine and Thicket.
  - Every row reuses an existing painterly sample: Scrub's `T_GT_Grass`, or Dirt's `T_GT_Dirt` for Scree and Alpine.
  - Each row is graded by the OW tint for that layer (`Art/dressing/ported/ClaudeSetupDressingLab.py:70`). Thicket uses the MeadowLush tint × 0.8.
  - Roughness and porosity come from the parent row. **No new texture samples** (21 today).
- **Grass output.** `LandscapeGrassOutput` with the 12 OW entries (`docs/landscape_migration/closure_summary.md:193`) keyed on the OW layers, plus Thicket keyed to `LGT_OWMeadowLushGrass`.
- **RVT.** An RVT output with the attributes `M_OWDressingLab` writes, into `RVT_AM_01_Material`.
- **Checks:**
  - The MPC count stays at 2.
  - `proving_test` passes, and the `proving_shots` pictures look unchanged; Fable looks at them.
  - A real compile check: a `-game` run with the material force-loaded, grepped for "Failed to compile".

### LD3. Exclusions, wind, switch (C++)

- **`AGTDressingExclusion`**: editor-only, tagged `OWDressing.Exclude`, with a CallInEditor `RebuildFromSpec`. It holds `UBoxComponent`s set QueryOnly, ignoring every channel, hidden in game:
  - Route and alt routes: oriented boxes every 10 m. Half-width is the road half-width × width scale + `DressingRouteClearM` 4 m; alt routes use `HalfWidthM` + 4 m. Height 10 m.
  - Mud and Ford sections: their extent plus 10 m. `MudPatchBoxCm` and `DeformPatchBoxCm`: plus 5 m.
  - Gameplay: `AGTLegStart`, `AGTCheckpoint` and `AGTExtractionZone`; every actor with an interaction component or interface (harvest, loot, stations); and actors labelled `Hide_*`, `Roof_*`, `Marker_*` or `Water_*`. Each gets its bounds plus 5 m.
- **Wind.** `GTWeatherSubsystem` also writes `MPC_GlobalWind` (`WindIntensity`, `WindDirection`) from GrandTour's wind. Calibrate so Clear's `WindStrength` gives the MPC's default intensity, and record the numbers.
- **`gt.Look.Dressing`** (0/1, default 1). It hides and disables collision on actors tagged `OWBiome.*`/`GTBiome.*`, sets `grass.Enable` to match, and turns off `UGTVegetationSubsystem`. `hide_shots` cycles it like `gt.Look.Foliage` (`GTM6TestRunner.cpp:7165`).
- **L3 cards.** `AGTTerrainDressing` places no L3 placeholder cards when the spec has biomes. Specs without biomes (L_Proving) keep them. Update `hide` tests that expect 3000 clumps.

### LD4. GT graph variants, tree sizes, collision (C++ editor module)

#### Tree variants

`OWCreateTreeVariantsCommandlet` regenerates every variant with **simple collision**:
- One **trunk capsule** on each tree, dead tree and stump. The capsule is sized from the trunk island the commandlet already isolates: radius at 1 m height, and it runs from the base to the first branch or 50% of the height, whichever is lower.
- Bushes get no shapes.
- Set `CollisionTraceFlag = UseSimpleAsComplex`, so canopy triangles never block a trace.

Guard: per variant, the vertex and triangle counts and materials must equal the migrated mesh; only the collision may change.

#### Commandlet variant mode

Add `-Variant=GT` to `OWCreateBiomePCGCommandlet`. It writes `PCG_GT_*` into `/Game/GrandTour/Dressing/PCG/`, and the OW output stays unchanged.

**Spawner classes.** Every spawner entry gets a physical class. The class sets the collision profile and a component tag the runtime reads:

| class | meshes | collision | tag |
|---|---|---|---|
| Solid | mature/veteran/dead trees, stumps, logs, rocks, boulders | `BlockAll` | `GTVeg.Solid` |
| Soft.Brush | bushes (`SM_OWBush_*`, `SM_BirchBush_01..05_Summer`), cover plants (`SM_CoverPlant_01..04_Summer`) | `NoCollision` | `GTVeg.Soft.Brush` |
| Soft.Sapling | tree variants at size class Sapling | `NoCollision` | `GTVeg.Soft.Sapling` |
| Soft.Young | tree variants at size class Young | `NoCollision` | `GTVeg.Soft.Young` |
| None | flowers, grass tufts, mushrooms, ground cover | `NoCollision` | none |

If a Solid vendor mesh has **no simple collision**, list it and set it to `NoCollision`; don't edit vendor assets. Fable decides the rest.

**Tree size classes.** These apply to every tree stream in the Forest and Alpine graphs:
1. After the existing transform, an attribute-noise node sets `$Density` to U(0,1).
2. Three density bands split the stream into classes:

| class | share | scale (uniform) | Z jitter | physical class |
|---|---|---|---|---|
| Sapling | 0-0.18 | 0.25-0.45 | 1.0-1.15 | Soft.Sapling |
| Young | 0.18-0.40 | 0.45-0.80 | 1.0-1.15 | Soft.Young |
| Mature | 0.40-1.0 | the existing ranges (× variant prescale) | as now | Solid |

- Saplings and young trees use only the non-giant, non-ancient, non-dead variants.
- The result spans about 0.25× to 2.45× of the base trees.
- Log a histogram of the spawned scales per class in the generation report.

**Forest understorey.** New soft-brush streams in `PCG_GT_Forest`, under every forest layer weight above 0.5: bushes at 0.02/m² (scale 0.7-1.3) and cover plants at 0.04/m².

**`PCG_GT_Brush`** (new; reads `Thicket`):

| stream | where | density | scale | class |
|---|---|---|---|---|
| bushes | weight > 0.5 | 0.08/m² | 0.7-1.4 | Soft.Brush |
| bushes | weight 0.2-0.5 | 0.03/m² | 0.7-1.4 | Soft.Brush |
| saplings | weight > 0.4 | 0.03/m² | 0.25-0.45 | Soft.Sapling |
| young trees | weight > 0.6 | 0.008/m² | 0.45-0.8 | Soft.Young |
| cover plants | weight > 0.3 | 0.10/m² | as now | Soft.Brush |

Every stream goes through the same exclusions and a slope band of 0.8-1.0.

**Tests.**
- The node counts of the GT variants against the OW graphs match the listed additions.
- Generate on `L_OWToolkitTest`'s landscape in a scratch copy map (never the OW test map). Report the per-class counts and the scale histogram.
- A trunk-capsule check: every solid tree mesh has exactly 1 capsule; no bush has any.

### LD5. Vegetation physics (C++ runtime) and its test

**`UGTVegetationSubsystem`** (world subsystem):
- At BeginPlay it indexes every ISM whose component tag starts with `GTVeg.Soft.`. For each instance it stores:
  - the base position;
  - a radius (the mesh's XY bounds radius × instance scale × 0.5; for trees, trunk radius = 0.05 × height);
  - the height;
  - the class.

  These go into a 2D spatial hash with 4 m cells.
- A car probe (`UGTVegetationProbeComponent` on `AGTCarPawn`) runs per physics tick. It queries the hash with the car's footprint OBB (the body bounds + 0.3 m).

**Model** (all numbers are dials in one settings struct, and the owner's feel pass tunes them):
- **Contact.** The instance base sits inside the OBB expanded by its radius, at intrusion depth `d`. Push fraction `p = saturate(d / 0.5 m)`.
- **Bend.**
  - Direction: the car's horizontal velocity (below 0.5 m/s: away from the car's centreline).
  - Target tilt `θ = θmax × p`. Tilt rises with τ 0.05 s, and after contact springs back with τ 1.5 s.
  - **Revised 2026-09-27 (proxy swap).** Pack meshes spawn as HISMs, and updating an instance every frame would rebuild the tree every frame. So a bending instance is hidden in its ISM/HISM (one batched update per component per frame) and drawn by a pooled movable `UStaticMeshComponent` proxy. The proxy carries the tilt and the spring back.
  - When the tilt is back under 1°, the instance transform is restored and the proxy returns to the pool. A snapping instance hands its proxy to the debris actor.
  - The pool, which is also the active set, is capped at 128; the oldest recover first.
  - LD4 soft classes are forced to plain `UInstancedStaticMeshComponent`, never HISM.
  - The bend is driven as a rotation about the instance base.
- **Resist.** A force on the car's body of `-v̂ × K × p`, summed over contacts and capped at 0.35 × m g (about 7.2 kN at 2100 kg).
- **Snap** (saplings and young trees only). When `θ ≥ θbreak` and the car's speed is at least `vbreak`:
  - hide the instance (scale 0);
  - spawn a debris actor: a capsule root that simulates physics, with the mesh attached and no collision;
  - give the debris the impulse `m_debris × v_car × 0.8`, and apply the opposite impulse to the car.
  - Debris freezes when it sleeps or after 20 s. At most 24 debris actors exist; the oldest frozen one converts to a no-collision ISM instance.
  - Snaps last for the run and are not saved.

| class | θmax | θbreak | vbreak | K | m_debris |
|---|---|---|---|---|---|
| Brush | 75° | never | never | 1500 N | none |
| Sapling | 70° | 40° | 2.5 m/s | 5000 N | 30 kg |
| Young | 45° | 35° | 7 m/s (25 km/h) | 16000 N | 150 kg |

With these numbers a young tree holds a crawling car and snaps under a determined one.

**Test map.** `/Game/GrandTour/Test/L_VegTest`, flat, built by a setup script. It has:
- a 20 × 20 m brush patch;
- a sapling row;
- a young-tree row;
- one mature tree, all as tagged ISMs of the real meshes;
- the default game mode.

**Test** `Art/veg_test.bat` (`-GTVegTest`, `-game -NullRHI`), added to the suite. The test runner drives the car. It passes when all of these hold:
1. **Brush at 40 km/h:** more than 20 instances bend beyond 20° while in contact; all are back under 5° within 6 s after; the speed loss over 20 m is between 10% and 45%.
2. **Saplings at 8 km/h:** no snaps, and the car is slowed. **At 30 km/h:** at least one snap.
3. **Young trees at 10 km/h:** no snap, and the car is held (speed under 1 m/s within 3 s). **At 45 km/h:** a snap.
4. **Mature tree at 20 km/h:** a stop (under 1 m/s within 1 s of contact), with the car centre never closer than the trunk radius to the trunk axis.
5. **Clean-up:** the active set is 0 and there are at most 24 debris actors, 10 s after the last contact.

#### LD5 v2 (Fable, 2026-09-27, after the first veg_test run)

**What the v1 run showed:**
- With a speed-hold driver, the brush cost only 4% over 20 m, because the hold floored the throttle. With the pedal fixed, or coasting, the car stopped within 20 m.
- A sapling row held the car at 8 km/h.
- A young tree could never be pushed over at a crawl; in the scratch thicket the car got stuck after 28 m.
- Frame time pushing through the patch rose from 15.5 to 25.1 ms. The patch was 1 plant/m², 12x a real thicket, and the moving proxies cast shadows.

**Model changes** (every value is a dial):

| change | v1 | v2 |
|---|---|---|
| Brush contact radius | as built | `0.5 x max(ext.X, ext.Y) x scaleXY`: only the inner half of the canopy resists |
| Sapling and Young contact radius | as built | trunk capsule radius x scaleXY (minimum 5 cm) |
| Resist | `K x p` | `F = K x p x s(v)`, with `s(v) = 0.3 + 0.7 x saturate(abs(v) / 10 m/s)` (crawling through brush is easier than ramming it) |
| Per-class caps on the summed force | none | Brush 0.15 mg, Sapling 0.20 mg, Young 0.35 mg |
| Total cap | 0.35 mg | 0.35 mg |
| Sapling K | 5000 | 2500 |
| Snap | the impact rule | the impact rule (`θ ≥ θbreak` and `v ≥ vbreak`) **or** a sustained push (`θ ≥ θbreak` and `p ≥ 0.9` held for `tHold`: Sapling 0.5 s, Young 2.0 s), so a crawling car can push a young tree over |
| Proxy shadows | cast | the proxy casts **no shadow** while bending (the restored instance keeps its own) |
| `PCG_GT_Brush` young trees | 0.008/m² | 0.004/m² |

**Test changes:**
- **Driver.** Hold the target speed on the approach. At first contact, lock the pedal at the mean hold value of the 2 s before contact (the "steady pedal"). Cases say when to switch to full throttle.
- **Brush patch.** 30 x 20 m at the thicket-core composition: bushes 0.08/m² (SM_OWBush_* and SM_BirchBush_*) plus cover plants 0.10/m².
- **Case 1.** 40 km/h, steady pedal:
  - at least 50% of the instances whose contact circle the car's box crossed bend past 20°;
  - all of them are back under 5° within 6 s;
  - the speed loss over the first 20 m is 15-60%.
- **Case 1b** (information only): the same patch at full throttle.
- **Case 2.** Saplings at 8 km/h, steady pedal: the car is never held (its lowest speed stays at 2 km/h or above) and reaches the end of the row. At 30 km/h, at least one impact snap.
- **Case 3.** Young trees at 10 km/h, steady pedal: the car is held (under 1 m/s within 3 s). Then full throttle: the tree snaps within 4 s. At 45 km/h, an impact snap.
- **Cases 4 and 5:** unchanged.
- **Case 6** (gpu), the new patch at 30 km/h: tentative bands are pushing through at most +3.0 ms GPU over `gt.Look.Dressing 0`, and parked and viewing at most +2.0 ms.
- **Scratch probe:** rerun it and report the distance made in 40 s at a 30 km/h hold.

**LD5 v2 result (2026-09-27):**
- Every band passed except case 2 at 8 km/h. The v1 test layout ran the 8 saplings *along* the lane 2 m apart: 4 saplings per 8 m of path, about 10x a thicket's 0.03/m² along one line. That bled the car to 0.5 km/h, though it reached the end.
  - **Fix: the sapling row runs across the lane** (8 saplings, 2 m apart, perpendicular to travel), so the car meets 1-2 of them. The numbers are unchanged.
- **Case 6** (tentative bands; kept for LD7, not tuned here):
  - pushing through: +4.09 ms GPU (15.40 vs 11.30);
  - parked and viewing: +2.21 ms (12.50 vs 10.29).
- **Scratch probe:** 100 m in 17.2 s, lowest speed 16.1 km/h (v1 got stuck at 28 m).

### LD6. Dress The Hide

- **Palette.** The biome rules go into `MakeHideTerrainSpec` (D2 plus Thicket, below) and are pushed to `DA_Terrain_Hide`.
- **Setup.** `Art/dressing/setup_dress_hide.py` + `.bat`:
  1. `RebuildLandscape`.
  2. Assign the landscape RVT and place an RVT volume over the landscape.
  3. `AGTDressingExclusion.RebuildFromSpec`.
  4. Place five `PCGVolume`s over the landscape bounds (GT Forest/Meadow/Scree/Alpine/Brush), tagged `GTBiome.<X>`, GenerateOnDemand, not partitioned.
  5. Save.
- **Generate.** Run `tick_harness.ps1` with a generate-only task, then save. Report instances per biome and class, the scale histogram and the generation time.
- **Rebuild order.** Any later `RebuildLandscape` means the harness must run again. The setup script's last log line says so.

### LD7. Tests, numbers, pictures, gate

- **Route clearance** (`-game -NullRHI` on L_Leg03):
  - Every 2 m along the route and each alt route, sweep a 3 × 4 × 2 m box. It must hit **0** Solid instances, and the hash must hold **0** Soft instances inside the swept box.
  - There is no vegetation of any class within 5 m of the start, the checkpoints, the extraction zone or any interactable.
  - The test joins the suite.
- **Suite.** The full suite passes, including `veg`, `dressing_toolkit` and the `hide` tests.
- **Perf.** `hide_shots` with `gt.Look.Dressing` at 0 and 1, 3 runs.
  - **Budget: +2.0 ms mean at 1280x720** (the baseline is about 15.4-16.5 ms). The water must stay far above its 15 fps cliff.
  - Also log the vegetation subsystem's tick time while driving through the thicket nearest the route (budget: 0.3 ms).
  - **Cut order if over budget** (revised 2026-09-27: free levers first, content cuts after, the look-changing Nanite voxel switch last). Measure after each step, and stop as soon as the budget holds:
    1. Nanite passthrough copies of the soft-class pack meshes (`SM_BirchBush_*`, `SM_CoverPlant_*`), made through the tree-variant commandlet's passthrough mechanism. Plus an HISM vs plain-ISM A/B for the soft classes; keep the faster one, provided the proxy swap still works on it.
    2. Tree shadows at distance (per-class shadow cull distance on the solid trees).
    3. Grass cull distances.
    4. Grass density (`grass.DensityScale` or LGT density).
    5. Brush and understorey density (the `PCG_GT_*` dials).
    6. Forest coverage (the spec noise band).
    7. `r.Nanite.AllowVoxels 0`.
- **Pictures.** `hide_shots` with the dressing on and off. Fable looks at them first and claims nothing about the look.
- **Gate:** the owner drives The Hide: look, feel (brush, saplings, young trees, a mature tree), and perf.

### LD8. Undo the no-gain cuts, summer retint, GPU profile (approved 2026-09-28)

Owner, 2026-09-28: "go with LD8 first, retint the trees to summer - keep in mind we are going to have to do a style/visual refinement at some point."

**Principle.** Every look value this stage sets (the summer tints, the per-species values) lives in one small set of GrandTour-owned assets plus one table in the build script. The later style/visual refinement pass can then retune them in one place. None of these values is final art.

#### LD8a (one agent)

1. **Undo the LD7 cuts that measured no gain.** Keep cut 1 (Nanite pack copies), cut 3 (grass cull ×0.6) and cut 4 (grass density ×0.5).
   - Cut 5, brush and understorey density: back to the LD4 values.
   - Cut 6, forest noise: back to 0.70-1 (about 27%).
   - Cut 7: `r.Nanite.AllowVoxels=1` again.
2. **Summer retint (GT graphs only; the OW MIs and `L_OWToolkitTest` stay autumn).**
   - **List what's warm.** For every mesh+material that `PCG_GT_*` spawns, read its leaf colour parameters (`M_OWFoliageMaster` MIs: the Color vector params that feed BaseColor/SubsurfaceColor through the per-instance hue jitter) and report the hue of each. Check the pack MIs and the Nanite pack copies too.
   - **Make summer copies.** For each warm leaf material, create a summer child MI in `/Game/GrandTour/Dressing/Materials/`: `MI_GT_Leaf_<Species>_Summer`, the same parent, every parameter copied, and only the leaf colour params changed. Point the GT graph spawner entries at them through the descriptor's OverrideMaterials. Trunk and bark MIs stay.
   - **Summer palette** (linear RGB). These are dials, placed near the GT grass value (the L3 cards sit at 0.08 0.20 0.06). If a material has a second, gradient colour, set it to the same hue at about ±25% value.

     | species | leaf colour |
     |---|---|
     | Beech | 0.09 0.21 0.05 |
     | Birch | 0.16 0.28 0.07 |
     | Oak | 0.07 0.17 0.04 |
     | Fir | 0.04 0.11 0.05 |
     | bushes | 0.10 0.22 0.06 |

   - **Hand-off for the style pass.** The table lives in one script (`Art/dressing/retint_summer.py`). Record the MI list in `docs/LandscapeToolkit.md` under "Look dials for the style pass".
   - If the leaf colour is not driven by a parameter (texture only), stop and report.
3. **Rebuild.** Rebuild the GT graphs, rerun `setup_dress_hide`, then the tick harness. Report instances per class, and the coverage table, which should be back to Forest+Fir about 27%.
4. **GPU profile** (the heart of LD8a). In `-game -RenderOffScreen`, after shaders, the asset compilers and eye adaptation have settled, run `ProfileGPU` and parse the top-level passes with their ms from the log.
   - **Views:** hide_11_track, hide_17_border_low, hide_21_rut_wet, hide_29_ford_shallow, view_forest, and a fixed view_thicket. The fixed view looks from a point at least 15 m off the route into the nearest Thicket-dominant ground.
   - **Captures:** dressing on and off, 3 captures per view per state, with the median per pass. Keep the GPU cool-down guard from LD7.
   - **Output:** a table of pass × (off, on, delta), per view and on average, plus the 5 passes that grow most. Also record Nanite and instance stats if available (`NaniteStats` or equivalent), and the grass instance count.
   - Report only; **no fixes.** Fable chooses the fixes from the data.
5. **Checks and commit.** Run the suite for `veg`, `route_clear`, `biome` and `dressing_toolkit`, then commit. Take pictures for Fable: overview, track, forest, thicket and hilltop, dressing on.

#### LD8b (decided 2026-09-28 from the LD8a profile, commit 0a0faaf)

**LD8a in brief:**
- The reverts are in: 130,495 instances, forest 27.1%, voxels back on. The summer retint uses 15 `MI_GT_Leaf_*_Summer` materials, and the OW content is SHA-1 untouched.
- Overall cost: +3.95 ms frame, +3.85 ms GPU.

**Profile delta** (on minus off, mean over 6 views):

| pass | delta |
|---|---|
| Lumen DiffuseIndirectAndAO (async) | +2.46 |
| ShadowDepths | +1.55 (track +3.2, ford_shallow +2.7, forest +3.8) |
| Nanite::VisBuffer | +0.80 |
| LumenSceneLighting | +0.65 |
| BasePass | +0.64 (+1.4 on the grass-heavy views, 110-150k grass instances) |

**One fix bundle,** then one measurement:
1. **Grass shadows.** GrandTour copies of the 10 OW grass types go in `/Game/GrandTour/Dressing/Grass/LGT_GT_*`, with every variety set to dynamic shadow off, contact shadow on and `AffectDistanceFieldLighting` off. The `M_GT_Landscape` grass output points at the copies (via the material step). The OW grass types stay untouched. These copies are look dials for the style pass.
2. **Small plants out of Lumen and the distance fields.** Soft.Brush, Soft.Sapling and None get `bAffectDistanceFieldLighting=false` and `bAffectDynamicIndirectLighting=false`, set in the GT spawner descriptors. Soft.Young and Solid keep both.
3. **Wind cut-off.** Bushes and cover plants get a `WorldPositionOffsetDisableDistance` of 5000 cm.
4. **Measure** in 4 launches:
   - 2 views runs, with dressing on/off toggled per shot inside each run, and a ProfileGPU per view;
   - 1 hide_shots run with dressing off and 1 with it on, for the GTPERF budget metric.

   The cool-down guard waits at most 3 min, then proceeds and records the temperature.
5. **Pass condition:** the hide_shots mean delta is at most +2.0 ms. If it's over, report and stop; the owner drives and decides.
6. **View fix:** `view_thicket` sits 12 m from a thicket edge and looks at it.
7. **Pictures (dressing on):** overview, track, forest, thicket, hilltop and ford.
8. **Tests:** only the targeted suite (`veg`, `route_clear`, `biome`, `dressing_toolkit`); these are rendering flags only. Then docs (a section 62 addendum and the LandscapeToolkit look dials) and a commit.

#### LD8c (Fable, 2026-09-28, from the LD8b pictures and numbers)

**What LD8b showed:**
- The bundle measured no gain: +4.85 ms, over budget. The grass already had its shadows off, and the Lumen and distance-field flags left DiffuseIndirectAndAO at +2.46. The GPU throttled at 86-88 °C.
- In the pictures, some near bushes render the **default checker material**. The likely cause: the Nanite pack copies (LD7 cut 1) use vendor masters without the Nanite usage flag, so in game they fall back to the default material. That also makes cut 1's -4.3 ms suspect.
- Other bushes render **purple-grey**. The pack birch-bush retint rescaled Base Albedo Color although the albedo was already green (126°).

**Fix:**
1. **Confirm the cause.** Grep the `-game` logs for materials falling back to the default (Nanite or ISM usage), and list them.
2. **GrandTour master copies, not vendor edits.** Copy each affected master into `/Game/GrandTour/Dressing/Materials/Masters/` with the needed usage flags set (`bUsedWithNanite`, `bUsedWithInstancedStaticMeshes`). Reparent the `MI_GT_Leaf_*_Summer` MIs, and any other GT MI on those meshes, to the copies. Where a Nanite pack copy has no GT MI, give it one.
3. **Pack birch-bush retint.** Restore Base Albedo Color to the vendor value. Only the warm subsurface and tint colours change. Update `retint_summer.py` to match.
4. **Remeasure honestly.** Regenerate. Take one `hide_shots` run with dressing off and one with it on. Take the pictures (overview, track, forest, thicket, hilltop, ford). Grep the logs to confirm that no dressing material falls back.
5. **Then stop.** Run the targeted suite and commit. Perf is reported as measured, with no more cuts; the owner drives and decides. Any further perf work goes to M7 performance / the style pass.

## 4. Not in this plan

- **Legs 1, 2, 4, 5.** They need terrain specs first (BACKLOG:63). After that, dressing one is a palette plus LD6's script.
- **Weather on OW foliage** (wet and snow). It waits for the first Rain or Snow leg with terrain.
- **Grass flattening under tyres** (LGT grass reading `RT_TrackPaint`). It needs an edit to the grass material; a later dial.
- **On-foot bending of bushes.** Same subsystem, a later dial.
- **Winch anchoring on trees.** Worth a note, since mature trees now have trunk capsules.
- **OW road dressing on GT routes.** Needs a width-aware road graph.
- **Dressing L_Proving.**

## 5. Decisions (approved 2026-09-27)

- **D1:** GrandTour's painterly grass and dirt graded with the OW tints.
- **D2:** The Hide palette, rules in order (soft edges; all dials):

  | # | layer | rule |
  |---|---|---|
  | 1 | OW_Scree | slope ≥ 32° |
  | 2 | OW_Alpine | height ≥ 75 m |
  | 3 | OW_ForestFir | forest mask and height ≥ 45 m |
  | 4 | OW_Forest | forest mask: noise of wavelength 300 m within **0.70-1** (uniform, about 30%), slope < 25° (revised 2026-09-27; 0.55 gave 43%) |
  | 5 | **Thicket** | forest-edge ring: the same 300 m noise within **0.64-0.70** (about 6%); plus riparian brush within **40 m of any Ford or Mud route section** (`SectionKinds` Ford+Mud, `MaxSectionDistM` 40, `FadeM` 10) with noise of wavelength 80 m within 0.4-1. Target: Thicket at most about 8% of off-road land (revised 2026-09-27; "height < 3 m" took the whole valley, 19%) |
  | 6 | OW_MeadowLush | height < 5 m |
  | 7 | OW_MeadowDry | noise of wavelength 150 m within 0.65-1 |
  | 8 | fallback | OW_Meadow |

  **Rule order, revised after LD1b (2026-09-27):** the riparian Thicket rule (within 40 m of Ford/Mud sections) is evaluated **after Alpine and before ForestFir/Forest**. The Hide's fords and bog sit inside the forest noise, so under Forest's priority that rule painted 0%. The forest-edge ring keeps its place after Forest. LD1b as built: Forest+Fir 27.3%, Thicket 5.6%, MeadowLush 18.1%, MeadowDry 16.3%, Meadow 29.7%, Scree 2.3%, Alpine 0.5%.

- **D3:** Retire the L3 placeholder cards where the biomes grow.
- **D4:** Perf budget +2.0 ms mean on `hide_shots` at 1280x720, plus 0.3 ms for the vegetation tick.
- **D5:** Only The Hide now.
- **New requirement:** a range of tree scales (LD4 size classes, about 0.25×-2.45×).
- **New requirement:** dense vegetation the car affects physically (Thicket, the understorey and the LD5 model). The model's numbers are the owner's feel dials.

## 6. Costs and unknowns

- **PCG volume.** About 4 km² with brush: forest ~10-15k and brush tens of thousands of instances (Nanite ISMs). Generation time and map size are unmeasured.
- **Physics bodies.** Solid trees mean one static capsule body per instance, likely 5-10k. The Chaos broadphase cost is measured in LD7.
- **Bending cost.** Instance transform updates on large ISMs: the frame cost of `MarkRenderStateDirty` on a component with many instances is measured in LD5; the probe logs its own time.
- **Debris.** Debris physics is capped at 24.
- **Damage.** Mature trees are hard obstacles and damage the car's body through the existing hit path. Intended, and the owner judges the fun.
- **Shader compile.** Layer combinations (up to 13 layers on The Hide) mean more shader permutations to compile.
- **Substrate.** The foliage is Substrate-converted and its look hasn't been judged yet.
- **Snow rows.** The Alpine snow rows read `OW_Snow`, but GrandTour's gameplay layer is `Snow`, so they don't fire on legs (accepted).
- **Ticking pass.** The editor window shows on screen during LD4's scratch generation and LD6's generation.

## 7. Files touched (for the agents)

- **Runtime (`Source/GrandTour`):**
  - `Terrain/GTTerrainGenerator.*` and `Terrain/GTTerrainDressing.*`
  - `Vehicle/GTVehicleSetupLibrary.*`
  - `Weather/GTWeatherSubsystem.*`
  - the look cvar owner
  - new `Dressing/GTDressingExclusion.*`, `Dressing/GTVegetationSubsystem.*`, `Dressing/GTVegetationProbeComponent.*`
  - the car pawn, where it adds the probe
  - the test runners
- **Editor module (`Source/GrandTourEditor/Private/Dressing`):** `OWCreateBiomePCGCommandlet.*` and `OWCreateTreeVariantsCommandlet.*`.
- **Python:** `Art/Unreal/setup_m6_hide.py` (the material and the Hide spec push) and new `Art/dressing/*` scripts.

## 8. Agent order

| agent | stages | runs Unreal |
|---|---|---|
| 1 | LD1 + LD3 (all runtime C++ except the vegetation physics), one build | the build, then `terrain` and `hide` tests |
| 2 | LD2 (material) | the material builder, `proving` checks |
| 3 | LD4 (tree variants + GT graph variants) | the commandlets, the scratch generation |
| 4 | LD5 (vegetation physics + `L_VegTest` + `veg_test`) | the build, the test |
| 5 | LD6 + LD7 (dress The Hide, clearance test, suite, perf, pictures) | everything; ends at the owner gate |

Strictly one after another: each needs the previous stage's build or assets. Fable writes each agent's execute-only brief from this file.

## 9. Owner gate checklist (The Hide, after LD7)

Open L_Leg03 and drive. `gt.Look.Dressing 0/1` toggles all the dressing.

1. **Route.** Nothing stands on the road or the alt route. The shoulders are clear. The start, checkpoints, extraction zone and interactables have open ground around them.
2. **Biomes.** Forest, meadow, lush low ground, dry patches and scree/alpine hilltops read as distinct places. Thickets sit on forest edges and by the fords.
3. **Tree sizes.** Saplings, young, mature and veteran trees mix naturally, with no visible size banding.
4. **Thicket at 30-40 km/h.** Bushes bend and spring back. The car slows but pushes through, and full throttle powers through.
5. **Saplings.** Crawl into one: it bends, then goes over after a short push. Hit one at speed: it snaps and flies.
6. **Young tree.** Crawl into it: it holds you. Full throttle: it goes over after about 1.5 s. Ram it at 45 km/h: it snaps.
7. **Mature tree.** It stops you dead, with body damage through the normal hit path.
8. **Bending colour.** A bending plant is drawn by a stand-in without per-instance variation. Look for a colour pop at the moment it starts bending.
9. **Grass.** Check the density, the pop-in ring, and that there is no grass on paving or in fords.
10. **Perf.** Run `stat unit` / `stat gpu` in the oak/forest, a thicket and the meadow, with the dressing on and off. Note the numbers.
11. **Dials.** All the vegetation physics numbers are in `UGTVegetationSettings` (Project Settings); the biome layout is in `DA_Terrain_Hide`'s Biomes.
