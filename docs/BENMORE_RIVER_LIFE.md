# Benmore river life — staged implementation

## Target

Develop the Gaea review into a believable small Otago stream: quiet pools, broken shallow runs, occasional muddy margins, gravel bars, sheltered willows and readable crossings. Preserve the broad Gaea landforms and the existing roads. A local, shallow incision follows natural drainage where the imported blend left water spreading across the slopes. Keep soft banks on the Landscape so they remain compatible with the existing deformation system.

## Stages and checks

1. **Flow bake.** Run the existing conservative shallow-water authoring solver on the returned Gaea terrain, with small authored headwater discharges and the lake as outlet. Keep bed, depth and XY velocity data. Check water balance, downstream connection, convergence, road clearance and artificial boundary contact. Do not claim surveyed discharge or runtime water interaction.
2. **Water rendering.** Use the new velocity field for advection. Separate pool and riffle response; avoid a regular wave grid and continuous bright foam. Use depth-aware bed colour, restrained reflections and local turbulence. Inspect close and elevated views plus motion samples.
3. **Banks and planting.** Add irregular mineral bars, damp silt and mud pockets at selected bends, with open gaps and clusters of the existing willow variants and approved tussocks. Ground rocks and roots against the actual Landscape. No continuous raised bank mesh.
4. **Crossings.** Select a shallow ford and a separate small footbridge, connect approaches to the existing route, keep the ford free of blocking rocks/trees and fit the bridge ends to the ground. Use existing deformation profiles for limited crossing patches if the current runtime integration supports this without shared physics changes. Do not label untested vehicle/water interaction complete.
5. **Review and handoff.** Save the level, reload, verify the intended native heightfield and unchanged protected terrain/road placement hashes, inspect creek/ford/bridge/vista captures and document remaining runtime checks. This pass uses stationary setup checks; no driving, performance or timing suite.

## Ownership

Work in `Art/Export/BenmoreGaea/RiverLife`, new `benmore_river_life` authoring scripts and review-owned assets under `/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverLife`. Save an untouched copy of the current Gaea review before installation. Do not rebuild the original driving level or alter shared mud, snow, traction or terrain-generator C++ files. Never launch a second Unreal process; wait for the shared suite to finish.

## Progress

- Planning and system inspection complete.
- Offline flow bake and geometry validation passed. The last 200 simulated seconds changed visible depth by at most 1.28 mm and visible current by 0.00173 m/s; the outlet is still slowly storing water, so global convergence remains false.
- Riverbed incision changes 6,186 of 4,068,289 native samples, with a maximum cut of 1.094 m and no raised samples. Protected road/shore heights are unchanged.
- Ford: approximately 10 cm water depth and 0.60 m/s authored current at its centre. Its approach peaks at a 13.8% sampled grade. The footbridge spans approximately 8.55 m including deck overhang, with 1.5 m clear walking width.
- 31 willows, 100 bank rocks, 1,400 gravel details, 240 shrubs and 2,400 approved tussocks prepared. Placement respects channel and path clearances.
- Installed and saved in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`. The pre-pass backup is `L_Benmore_GaeaBeforeRiverLife` in the same folder. The original driving map remains unchanged.
- All 4,068,289 saved Landscape samples match the intended heightfield. Both road instance hashes are unchanged. Sampled rock/root support agrees with native collision to within 0.6 mm; the footbridge deck collision trace passed.
- Both existing CPU deformation patches initialize on native terrain, load their material and report zero ground misses. The focused live-capture retry passed, with distinct water frames 2.25 game seconds apart. No driving or water-force validation has been performed.
- The river-mouth bed uses 58,955 vertices from the same DEM. The scenery cutout now targets `Benmore_Hills_*`; the retired `Benmore_Backdrop_*` labels caused the old shoreline fix to miss the current terrain. The native Landscape remains unchanged by this repair.

## Technical decisions

- The existing 2D shallow-water solver supplies depth and downstream velocity. Headwater discharge is authored (0.8 cubic metres per second in total), not measured. This is an offline art bake, not a runtime river or flood model.
- The broad outlet basin continues to fill slowly. Global steady-state convergence is reported separately from suitability for a frozen visual bake. Visual stability checks measure visible depth and current drift over 200 simulated seconds; conservation, lake connection and dry artificial boundaries remain mandatory. Do not describe the catchment as fully converged if `converged` is false.
- Flow advection uses two overlapping phases so the shader can reset its texture coordinates without a visible jump. Depth and current speed distinguish calmer pools from broken shallow runs. References: [Valve water-flow presentation](https://cdn.akamai.steamstatic.com/apps/valve/2010/siggraph2010_vlachos_waterflow.pdf), [Unreal Single Layer Water](https://dev.epicgames.com/documentation/en-us/unreal-engine/single-layer-water-shading-model-in-unreal-engine).
- The ford has a gravel deformation profile capped at 3.5 cm, and a separate muddy approach capped at 7.5 cm. These use the existing CPU field and patch subsystem. The `Benmore_RL_CrossingProfiles` terrain builder is a **runtime profile provider only: never call Rebuild Landscape on it**, because the level uses an imported native heightfield.
- A timber footbridge is a pedestrian crossing. The ford is the vehicle crossing. Water depth/current forces are not yet connected to vehicle physics.
- Stationary SceneCapture images verify patch initialization and water animation. They have darker exposure and less streamed grass than the editor review cameras; use the editor captures to judge the planting. The water still has a broad bright sun reflection at some angles. Two motion samples confirm animation, not seamless phase transitions across a full loop.

## Next stages

1. Drive the ford to validate wheel contact, rut limits and transitions between the gravel and mud profiles. The existing subsystem trims overlapping patch boxes; inspect the full vehicle line before expanding these profiles.
2. Connect authored water depth/current to the existing vehicle-water system, then add crossing splashes and localized contact ripples. The current shader has no obstacle response to moving actors.
3. Reconcile the wider lake coverage and shoreline elevation with the regional terrain. The local mouth intersection is repaired, but the broad, flat background shoreline still needs work. Preserve the protected native road and shoreline samples unless deliberately re-authoring that region.
4. Refine selected hero bends with a few intentional bed stones, scour pockets and ambient stream audio after driving scale is confirmed.

## Authoring and evidence

- Offline: `Art/tools/bake_benmore_river_life.py`, `prepare_benmore_river_life.py`, `check_benmore_river_life_geometry.py`, `prepare_benmore_river_outlet.py`.
- Mesh source: `Art/Export/BenmoreGaea/RiverLife/Benmore_RiverLife.blend`, exported by `Art/Blender/export_benmore_river_life.py`.
- Unreal: `Art/benmore_river_life.ps1` guards the one-editor rule. Setup installs the main pass; the outlet refinement must also be applied after a full rebuild. The Polish mode is a bounded inspection session accepting only the three named river scripts through `review-command.json`; it quits after 20 idle minutes.
- Evidence is under `Art/Export/BenmoreGaea/RiverLife`: `completion-report.json` combines the successful offline, native-terrain, collision and focused runtime checks. The original `review-report.json` retains the failed camera API attempt as diagnostic history; `runtime-report.json` records the successful replacement capture. Flow, geometry, setup and outlet reports retain their individual results.

## Revision: moving water and rendering budget (2026-10-08)

The owner rejected the river as looking painted on and reported poor frame rate. The preceding first-pass checks established placement and an animated material, **not convincing moving water**. There is no `GTWaterSheet` connection in the RiverLife setup. Do not count changing normal-map pixels as a simulation acceptance test.

The existing `AGTWaterSheet` / `FGTWaterField` already supplies changing surface height, current, hull displacement, wind/rain and the vehicle water query. Reuse that system. Its present initialization, basin survey and boundary heads assume one nominal ford level; its GPU upload and solver also run every active sheet tick. Simply scaling that actor to the river or placing many always-running sheets is unsuitable.

The reference survey measures a 2.387 m surface drop over 36 m at the ford, and 3.563 m at the footbridge. A single level differs from the intended ford surface by up to 1.227 m. The current baked ford is only about 10 cm deep. These are sampled geometry facts, not frame-time or driving measurements.

### Implementation order

1. **Content audit and reversible rendering cuts.** Inspect the actual map's grass, instancing, LODs, shadow participation and water material graphs. Keep near-road silhouette and original asset instances. Reduce small-detail draw distances and replace repeated procedural normal calculations with the existing sourced water normal where a visual comparison supports it. Save a pre-budget map; clone materials/grass types into the review folder. No global Lumen/shadow/resolution reduction and no shared mud/vehicle tuning.
2. **One real simulation window at the ford.** Adapt the existing water field to initialize native bed, depth and face flux from reference data. The starting proposal is 48 x 24 m at 0.375 m cells: 8,192 cells. Per-cell reference surface and wetness must replace the one-level basin assumptions. Feed the window boundary from the mean flow, allow outgoing disturbances to leave, and count all imposed source/sink volume. A snapshot from a different solver is not guaranteed to be a steady state: validate/reconcile residuals with GTWaterField's friction/discretization before layering wakes over it. Do not hold all interior cells fixed, which would erase interaction.
3. **Use the simulated height in the mesh and the physics query.** Surface displacement, normals, depth tint and foam must read the same evolving field as the wheels/hull. Blend into the distant mean surface through an overlap band without double water, a moving level step or forces disappearing at the boundary. The initial pilot must show a disturbance propagating and moving downstream, a wake around an obstacle, and a quiet return after the disturbance.
4. **Activate a bounded window near the player.** Keep one 8,192-cell window active, with a second only during handoff (16,384 total). Carry overlapping cell state into the incoming window and initialize new cells from the reference. Use hysteresis, prewarming and bounded texture uploads; do not rebuild a large bed trace every frame. Keep distant water queries available through the baked reference. This scheduling and query fallback are not installed yet.
5. **Render the rest at distance-appropriate detail.** Near water uses the active simulation, intermediate reaches retain animated flow/depth/foam on cheaper geometry, and the far river/lake uses coarse tiles. Simulation resolution and visible mesh density are separate controls. Epic's [water mesh documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-meshing-system-and-surface-rendering-in-unreal-engine) describes camera-centred mesh LOD and a simpler far mesh; that rendering feature alone does not add interactive river simulation.
6. **Measure and tune on a quiet GPU.** The owner chose to continue without timings while God of War Ragnarok is running. No FPS gain is established by this pass. `Art/profile_benmore_rendering.ps1 -Run` is the prepared, not-yet-executed harness: fixed 1440 x 900, uncapped, 100% screen percentage, two stationary views, ABBA comparisons for water, landscape grass, instanced foliage and shadows. CSV records full GPU/pass and thread times. Its guard refuses an occupied editor or known game and invalidates results if a game starts during capture. Shader warmup, thermal state, screenshots and driving checks still belong in the eventual measurement review. Reference: [Epic CSV Profiler](https://dev.epicgames.com/documentation/unreal-engine/csv-profiler?application_version=4.27).

### Prepared reference data

`Art/tools/prepare_benmore_sim_reference.py` writes two bounded reference windows and `reference-report.json` under `Art/Export/BenmoreGaea/RiverScale`. Units are metres and metres/second, with explicit rotated axes. Dry cells carry the native bed. The 1.25 m mean-flow bake is resampled; the 0.375 m output grid does not create new hydraulic detail. These files are solver-integration inputs, not live simulation assets.

The saved-map content audit confirms **zero GTWaterSheet actors**, 5,557 composition shrubs drawing out to 2,100 m, and 17,278 additional composition tussocks out to 850 m. Those are placement counts and authored cull distances, not simultaneously drawn geometry or measured bottlenecks. Landscape grass and small road gravel already have LOD/cull/shadow controls; avoid blanket cuts that undo the long-vista work. The bank mask is zero over 99.24% of its texture area, so sampling its four detail maps across the whole Landscape is avoidable work. This percentage is terrain area, not a GPU savings estimate.

The first budget pass clones the terrain/water materials into `Gaea/RiverScale`: bank texture samples move inside a mask branch; river normals use four sourced-normal samples instead of eight procedural finite-difference field evaluations; the lake uses two normal samples with a real distance work skip. RiverLife's 1,400 small gravel instances fade between 50 and 110 m instead of 170 and 330 m. Existing road aggregate distances, grass density, shrub coverage, near geometry, lighting and vehicle tuning stay at their prior settings. `L_Benmore_BeforeRenderBudget` retains the previous map/material assignments. `budget-report.json` and paired Ford/Long_Vista images record the execution result; a successful asset pass is not an FPS result.

Execution: saved/reloaded successfully; all 90,353 authored instance transforms match their pre-pass hash. Before/after screenshots were inspected. The terrain/planting remain consistent; the cheaper water normal is calmer and does not resolve the painted-water complaint. Large bright reflections and lake speckling remain. The material graph logged temporary missing-Ripple-input warnings while rewiring; final recompile returned no errors, later captures rendered water, and saved-map reload added no shader compile failures. No live-water solver, driving run or performance capture was installed/run by this budget pass.

### Gates before promoting the simulation

- Preserve the existing ford/water regression tests and vehicle tuning.
- Measure reference-state drift, total volume and boundary flux; reject negative depth, bank leaks and numerical clamps under normal load.
- Test an impulse, stationary obstacle and moving hull, then a window handoff; compare animated captures over a full interval, not only two changed frames.
- Confirm water mesh and `UGTWaterSubsystem::Sample` agree on surface/depth/current across the overlap and outside the active window.
- Establish cost on a quiet machine before increasing cells, adding more windows or claiming a frame-rate improvement.

## Bounded live ford implementation (2026-10-08)

The first integration uses a **reduced, fixed-bank wave model around the baked mean**, inside `FGTWaterField`. It is not a full nonlinear river, flood or erosion simulation. A weighted offline projection removes interior discharge divergence on the actual 128 x 64 grid. The reference's height/pressure balance is retained; runtime pressure comes from changing water height and solid occupancy. Height and wave momentum advect with the mean current. No interior cell is reset to the reference. Only the outer four-metre absorbing band exchanges disturbance water with the unmodelled river; `RiverBoundaryM3` records that signed exchange. Dry reference banks remain fixed.

`prepare_benmore_live_reference.py` writes one packaged data asset payload and a binary fixture shared with native automation. The projection leaves maximum interior divergence below 1e-8 m3/s. A uniform 0.798 velocity scale bounds the fastest face at 1.5 m/s while preserving continuity; these are authored currents, not measured hydrology.

The opt-in `RiverReference` on `GTWaterSheet` bypasses the flat-level basin survey. The existing lids, water subsystem, hull/wheel queries, rain and volume-neutral wind forcing remain the integration points. The default ford path is unchanged. This pilot deliberately ignores catchment stage changes because its fixed-bank reference has no flood-stage bake. The deformable native Landscape and existing mud/gravel profiles are not rebuilt.

`RiverSurface` binds the transient field texture to the stream material. Its vertices displace toward the field's sampled surface, with a 3.5 m transition at the window edges. Depth/current and surface-gradient normals also sample the field. No duplicate water sheet is added. Local conforming refinement around the crossing raises the whole stream from 22,247 to 31,176 triangles, preserving every original vertex and surface plane. Elsewhere the mesh retains its original density. At sampled interior triangle centres, reference surface error falls from 3.07 cm to 0.40 cm at the 95th percentile (worst sampled error 4.50 -> 2.18 cm). This is a geometric accuracy check, not a timing result. Centre-sample texture/query agreement does not prove continuous agreement at every triangle or at the transition.

Simulation wakes within 100 m and sleeps after eight seconds beyond 140 m, retaining the reference appearance and reference queries within its footprint. This is **one fixed crossing**, not a travelling window or full-river interaction. Queries outside the window, overlapping-state handoff, and a moving window remain later stages. A quiet-machine driving and profiling pass is still required before promoting or expanding it.

Validation tools: `Art/benmore_live_river.ps1 -Mode Test` runs the native CPU automation; `-Mode Install` backs up to `L_Benmore_BeforeLiveRiver`, installs and reloads the review map, then captures a fixed-time editor disturbance preview. Both refuse an occupied Unreal process. The stationary preview manually advances simulation time; it is not a runtime frame-rate or vehicle-force test. Installation and test results must be read from their fresh reports before claiming completion.

Native build succeeded. `GrandTour.Water.RiverReference` passed: legacy still-water behaviour, 60-second sloping-reference stability, conserved impulse propagation, moving-lid displacement and quiet return, actual Benmore reference stability, dry-bank exclusion, and texture/physics centre-sample agreement. Synthetic moving-lid crest 3.46 cm; worst impulse volume-accounting residual 0.00000825 m3; return error 0.000004 m. Actual Benmore pulse reached a probe two metres downstream (3.14 mm response); mass residual 0.00000362 m3. No flux limiter fired in the synthetic cases. These are fixed-step CPU checks, not driving or performance measurements.

Installation completed and the saved review map reloaded successfully. Actor `Benmore_RS_LiveFord` references the packaged `DA_RS_FordReference` and the refined `SM_RS_StreamLive`. All 90,353 placed-instance transforms retain hash `2a4413d553fbba0c1677c85e2d515cd205640d6f1280992ea8b892a2d8fa7fdb`; the original driving map retains SHA256 `9d806868d3d3465e6f5a6147118deed564327b8dcbd4bcee1b392bc952c9ef5b`. The initial installer stopped on a Python rain-property name before saving the map; that was corrected, and subsequent installation/reload and capture passed.

The fixed-time editor preview reports surface 1585.327 -> 1587.110 cm half a simulated second after the test impulse, with reference current approximately 0.527 m/s downstream. `LiveFord_Rest.png`, `LiveFord_Disturbance.png`, and `LiveFord_Propagation.png` were inspected. The material's near specular/roughness response was revised after the first captures looked too matte; `LiveFord_MatteBefore.png` preserves that comparison. Final capture/import logs contain no shader compile errors. The surface reads more clearly through reflection, although broad bands in the baked channel and the wider river shape remain visible and need further art/hydrology work. Small wakes are subtle in still captures; these images do not establish a convincing full-loop animation or vehicle behaviour.

An additional seam survey found all 38 wet edge probes covered by the continuous original mesh. The reference height differs from the baked edge mesh by a median 0.52 cm and maximum 3.30 cm. The shader blends this correction over 3.5 m, so there is no second-sheet gap, but mesh/query approximation in that band remains a driving-validation item. No moving-window handoff, full-river query fallback, runtime driving check or clean-machine FPS measurement is claimed complete.

## Whole-water follow-up — 2026-10-08

The fixed ford pilot is superseded in the review map by `Benmore_RS_WaterDomain`. `DA_RS_WaterDomain` stores the river/outlet's world surface, depth and current, plus the existing regional lake coverage. The lake now answers the same water subsystem queries used by the hull and tyres. The original mud/rut-water implementation is unchanged. The distant lake mask is the original 10 m coverage raster; it is not surveyed underwater bathymetry.

One 96 x 96 grid at 62.5 cm spacing follows the local player: a 60 m square, capped at 9,216 cells regardless of river length or lake area. The grid moves in aligned 10 m blocks. Overlapping heights, face fluxes, disturbance momentum, lids and pending solid stamps are retained; disturbance volume leaving the window is counted. Newly exposed cells start at the authored mean. A teleport deliberately leaves the old distant wake behind. This is a single-player interaction budget, not independent simultaneous windows for multiple distant vehicles.

The solver advances shallow-water disturbances around the prescribed mean. It removes the resampled mean's divergence from the perturbation continuity equation, preventing interpolation error from becoming a water source. It does not re-solve the catchment, erode banks, flood new terrain or dynamically recompute the bake's mean flow. In deep lake coverage it uses an effective 1.5 m wave layer for a bounded timestep; buoyancy queries still use the world water elevation above the queried ground/hull point. This is not a deep-water ocean simulation. The 62.5 cm grid resamples the 1.25 m bake and adds interaction resolution, not hydrological detail.

Rendering uses one nearby procedural mesh, with an exactly matching rectangular cutout in the static river, outlet and lake materials. No overlapping full-size second water surface is drawn. Outside the window, baked water remains visible and queryable. Local depth, current, wave height and gradient normals use the same field. Dry mesh vertices receive nearest-wet elevations to avoid shoreline triangles being pulled down to an unrelated dry-cell/lake height. The offline water elevation is smoothed independently of the bed, with limited corrections (-4.5 to +11.5 cm in the prepared river cells). Native Landscape heights, roads and all 90,353 placed-instance transforms are preserved.

Authoring: `prepare_benmore_water_domain.py`, `export_benmore_domain_mesh.py`, `benmore_domain_material.py`, `install_benmore_water_domain.py`. `Art/benmore_water_domain.ps1` provides `Test`, `Install` and stationary PIE `Runtime` modes. It refuses an occupied Unreal process; timing mode also refuses other games/Blender. Backup: `L_Benmore_BeforeWaterDomain`.

Initial native validation passed both `GrandTour.Water.RiverReference` and `GrandTour.Water.MovingDomain`: 40,047 wet river/outlet/lake samples had zero mean-height query mismatches; a 10 m window shift retained 7,680 synthetic wet cells, with maximum overlap height change 0.0000076 cm; pending hull stamps survived relocation. The first saved-map reload passed and preserved instance hash `2a4413d553fbba0c1677c85e2d515cd205640d6f1280992ea8b892a2d8fa7fdb`. A fixed-time actor preview retained an impulse at 1590.90698 cm across a 20 m shift exactly. These are coverage/handoff checks, not a vehicle driving validation. See `domain-install-report.json` and `domain-runtime-report.json` for the final visual/runtime outcomes; do not infer a passing runtime result merely from the presence of its harness.

### Direction from the Spintires references

The user supplied Pavel Zagrebelnyy's [2013 rendering/simulation article](https://www.gamedeveloper.com/programming/rendering-and-simulation-in-offroad-driving-game) and [2017 MudRunner article](https://www.gamedeveloper.com/programming/mud-and-water-of-spintires-mudrunner). The latter describes nearby active blocks, a baked continuous water surface and current field, separate geometric waves, propagated foam and stirred sediment, and splash/wet-decal layers. It also precombines animated texture detail to reduce water shader arithmetic. These are references for our design, not evidence that our current implementation reproduces their appearance or cost.

The moving bounded field and packaged mean-water domain are implemented. **Advected foam, persistent stirred sediment and new splash/wet-bank effects are not implemented by this pass.** Existing baked foam potential is only a material input; it is not a transported wake.

The next visual pass should proceed in this order:

1. Correct the river-mouth coverage and water/ground intersections. The final mouth preview still shows uneven, angular shallows outside the detailed native Landscape. Identical river/lake optical coefficients remove one shading mismatch but cannot fix that geometry. Inspect a continuous reach at driving height before adding effects.
2. Add bounded foam and sediment state around the vehicle, carried by the existing current. Generate it from immersed moving wheels/hull and local disturbance, not a uniform white fringe. Keep visual concentration separate from water volume and vehicle forces; retain it through aligned window shifts, fade it at distant boundaries, and verify advection/decay and unchanged physics.
3. Add limited splash particles and briefly wet bank/stone surfaces, gated by immersion and relative speed. Keep the deformable Landscape and Claude's mud work as the owners of terrain deformation; these visuals must not become a competing terrain surface.
4. Profile the complete crossing, including upload, rendering, overdraw and window shifts. Precombine repeatable wave/foam detail if material cost warrants it. Compare the same camera and settings with each effect disabled; do not infer performance gains from a smaller texture or cell count alone.

The fixed-bank solver does not redirect the baked mean around newly placed rocks or move water into newly excavated bank cells. Those are separate hydrology/deformation integrations, not effects that foam can supply. A local cosmetic field is the immediate visual target; a full catchment fluid replacement is not part of this implementation.

### Whole-water runtime outcome

The stationary PIE validation passed at the ford and the lake on 2026-10-08. A test impulse changed the river surface from 1585.851 to 1592.155 cm and the lake from 60.149 to 65.651 cm. Both remained queryable after moving the player's pawn between them. These are impulse and relocation checks, **not a driven vehicle crossing**. The final install/save/reload also passed. All placed-instance transforms and the original driving-map SHA256 above remain unchanged.

The quiet-machine capture used the RTX 4050 Laptop GPU, DX12, uncapped frames and 100% screen percentage. Unreal supplied an actual **1274 x 682** viewport despite a 1440 x 900 request; use the actual size when comparing. The first harness attempts stopped before measurements on viewport/API assumptions; the final fresh `domain-runtime-report.json` has `ok: true` and `timings_valid: true`.

| Stationary view | Frame median / p95 | GPU median | Water solver mean / worst |
| --- | --- | --- | --- |
| Ford | 47.50 / 55.91 ms | 45.95 ms | 1.60 / 5.08 ms |
| Lake | 32.15 / 46.29 ms | 32.70 ms | 1.87 / 5.30 ms |

CSV windows were eight seconds; solver counters cover those windows plus the three-second CSV finalization delay. There were no solver time deficits or substep clamps in these measurement intervals. Warmup/relocation did produce coarse frames, and the ford run recorded one earlier frame beyond its 0.25 s accumulator bound. This does not establish a hitch-free driving result. RenderThreadTime was effectively zero in this capture and is not used as a useful CPU timing signal.

The recorded GPU scopes identify `LumenSceneUpdate` as the largest entry: medians 15.94 ms at the ford and 15.10 ms at the lake. The ford also records Basepass 7.40 ms and Prepass 5.85 ms. The two named water scopes are about 0.25 + 0.58 ms at the ford and 0.23 + 0.61 ms at the lake. Scopes can overlap and omit shared work; these numbers do **not** isolate the total cost attributable to water. `domain-runtime-gpu-scopes.json` preserves the breakdown. The next performance experiment should isolate Lumen scene updates and vegetation/material draw cost with paired captures before expanding the water solver. No before/after FPS gain is claimed from this baseline.

## MudRunner-inspired bounded water detail — 2026-10-08

This pass adapts the referenced separation of authored flow, local disturbances and transported cosmetic state. It does not port MudRunner's renderer or replace the existing CPU vehicle-water model with GPU physics. A small CPU field avoids a GPU readback dependency for the current physics queries; its actual cost is a validation gate, not assumed to be cheap merely because the grid is small.

The reference-wave kernel now iterates fixed wet cells, caches the authored face velocities, and evaluates absorbing-boundary exponentials once per distinct edge distance/timestep. Its physical timestep stays at 60 Hz. No traction, buoyancy, mud or vehicle tuning values change. The moving field is still at most 96 x 96 cells over 60 x 60 m, regardless of map size.

An opt-in passive field stores foam and suspended-sediment concentrations, transported by the existing water velocity. Occupancy changes from immersed solids create foam and shallow sediment; an immersed solid in a current can also produce a small foam source. The first pass does not have wheel-angular-speed-specific agitation or new splash particles. Foam decays on a four-second timescale and sediment on twelve seconds. Concentrations are bounded, masked to wet cells, retained on aligned window shifts, and faded over the outside three metres. They never write water depth, flux, terrain or vehicle forces. This is a visual concentration model, not a sediment-mass/erosion simulation.

Cosmetic updates run at most 30 Hz, with at most 0.1 simulated seconds per visual update after a hitch. The shader uses one additional nearby texture lookup, reusing the existing sourced water normal for breakup; no new generated art texture or multi-octave procedural noise is added. Sediment changes underwater scattering/absorption; foam changes surface colour, opacity and roughness. Static distant water keeps the baked flow and cheaper shading. The 96 x 96 BGRA8 detail texture is 36 KiB; existing half-float height/depth/velocity is 72 KiB. Combined uploads are capped at 30 Hz by default (3.16 MiB/s of pixel payload, excluding API overhead and immediate window shifts). Physics and the material's scrolling detail remain independent of that upload cap.

Controls: `gt.Water.Domain.Detail` defaults to 1 and switches cosmetic updates/sampling for comparison; `gt.Water.Domain.UploadHz` defaults to 30, clamped 15–60. Neither affects legacy fords/rut water. `GTWater/DomainTick` includes local field work and texture-upload submission; `GTWater/DetailMs` and `GTWater/ActiveCells` record the cosmetic update and fixed wet-cell count. The runtime harness uses on/off/off/on captures at one unchanged lake camera to assess incremental cosmetic cost. This is not a total-water or whole-game benchmark.

The final source build and all three native water tests passed. The visual transport test moved its foam centre 240.01 cm in four seconds at 0.6 m/s, retained 0.36788 of foam under its four-second decay, and left the no-detail control's water heights bit-for-bit identical. Fixed dry banks, bounded finite concentrations, solid-source generation, reset and visual-state relocation passed. Existing reference-wave mass/stability and whole-domain coverage tests still pass. Install/save/reload passed with the same 90,353-instance hash. `BeforeDetail_domain-runtime-report.json` and `BeforeDetail_Domain_Ford.png` preserve the earlier baseline. `L_Benmore_BeforeWaterDetail` plus each domain material's `_BeforeDetail` copy are the install backups. The river-mouth geometry remains a separate unresolved art task.

The first pictures were too subtle. A material-only revision exposes `FoamGain=4` and `SedimentGain=2`, and raises the sediment scattering/absorption response so it can be seen in a shallow crossing. `Detail_Rest.png`, `Detail_Wake.png` and `Detail_Wake4s.png` were inspected: the immediate wake has a visible brown suspended cloud, with a much weaker/displaced cloud after four seconds. Foam remains restrained; this does not establish finished splash/whitewater art. Over the fixed water ROI (450,450)-(1100,850), mean absolute RGB change from rest is 5.81/255 for the immediate wake and 1.64/255 at +4 s; 14.37% and 0.33% of pixels respectively change by more than 20 in a channel. Wind/reflection differences are not isolated by that pixel comparison. See `detail-pixel-review.json` and `detail-polish-report.json`. This is a scripted immersed-footprint preview, not a driven-car demonstration.

The first performance capture (`detail-first-runtime-report.json`, before the material-strength adjustment) passed at the same 1274 x 682 viewport. Full `GTWater/GameThread/DomainTick` medians/p95s were 0.692/0.893 ms at the ford (1,487 active cells) and 0.852/1.372 ms at the coastal lake (4,656 active cells). Solver stepping alone averaged 0.417 and 0.713 ms per stepping frame; do not turn the earlier-to-current difference into an isolated FPS claim because frame rate and total GPU load differ. No deficit or substep clamps occurred during these measurement intervals.

The coastal-lake detail on/off/off/on medians were 0.938, 0.806, 0.838, 0.946 ms for DomainTick: approximately 0.12 ms incremental CPU cost from paired averages. GPU SingleLayerWater medians were 0.675, 0.676, 0.689, 0.704 ms; variation is larger than a clear cosmetic-cost signal, so no GPU speedup/zero-cost claim is made. The final capture below uses the stronger material and adds a completely wet open-lake grid (9,216 cells).

Legacy regression: `Art/suite.sh terrain water` returned one pass and one failure. **Water passed** (298 s), including current, wave/solid interactions and rain/stage checks. **Terrain failed at the documented step-11 rut-exit gate**: held exit reached 6 m in 5.9 s versus 4.0 s without hold. Its ordinary ford, raised-water flooding, downstream drift, floating wheel load and winch-recovery checks passed. Step 10's old crest-band output is report-only, not an additional failed gate. No mud/vehicle tuning was changed to mask the rut-exit failure. Copies are preserved as `Art/Export/BenmoreGaea/RiverScale/detail-terrain-regression.log` and `detail-water-regression.log`; this is not a claim that the complete shared-project suite is green. Terrain and water were the stage's targeted regressions; no duplicate full shared-project suite was launched alongside the other ongoing agent's work.

### Final material and maximum wet-grid capture

`domain-runtime-report.json` completed at 16:24 local time with `ok: true`, `timings_valid: true`, actual viewport 1274 x 682, DX12 on the RTX 4050 Laptop GPU. No monitored game/Blender load invalidated the run. These are short stationary PIE captures, not packaged-build or driven-vehicle results. DomainTick includes local stepping, cosmetics and upload submission, but not all vehicle queries, rendering or render-thread upload completion.

| View | Wet cells | DomainTick median / p95 / max | Whole-frame median | SingleLayerWater GPU median |
| --- | ---: | ---: | ---: | ---: |
| Ford | 1,487 | 0.651 / 0.842 / 0.897 ms | 35.06 ms | 0.503 ms |
| Coastal lake | 4,656 | 0.866 / 1.307 / 1.479 ms | 25.44 ms | 0.554 ms |
| Open lake, full grid | 9,216 | 1.718 / 2.432 / 3.362 ms | 28.64 ms | 0.780 ms |

Solver stepping averaged 0.389, 0.691 and 1.366 ms respectively, with all 661/662 requested steps run and no interval substep clamps or time deficits. The ford field's lifetime counters include two coarse/dropped warmup frames outside the measurement interval, so this does not establish hitch-free startup. LumenSceneUpdate medians remain 11.39, 11.11 and 12.71 ms. Water depth-prepass medians were about 0.19–0.21 ms. Individual scopes omit shared work and must not be treated as an isolated total-water GPU cost or an additive frame breakdown.

The full-grid detail on/off/off/on DomainTick medians were 1.7192, 1.62445, 1.5683 and 1.7556 ms: paired averages differ by **0.141 ms**. The dedicated cosmetic scope was about 0.189 ms median while enabled. These differ because the captures include variable fixed-step counts and other field work. SingleLayerWater GPU medians were 0.78295, 0.78025, 0.79005 and 0.7956 ms: approximately 0.004 ms paired difference, below capture variability. No zero-cost GPU or overall FPS-improvement claim is supported.

Sixteen aligned 10 m focus moves at 0.5 s intervals kept all 9,216 cells wet and retained 7,680 overlapping cells per shift. DomainTick measured 1.818 ms median, 2.672 ms p95 and **4.246 ms maximum** across the movement capture. That peak includes window rebuilding and is a remaining optimization target if a tighter CPU budget is required; the test teleports the focus and does not verify vehicle handling or absence of a visible seam while driving. Whole-frame median/max were 29.73/41.74 ms. The measured scene remains GPU-limited; isolate Lumen/vegetation before increasing simulation resolution or adding more active windows.

## Water clarity and visible current — 2026-10-08

**Review status: rejected by the user.** The captures below establish that the material changed, not that it delivers the requested current. The amplified rain-ring pattern is the wrong ambient-wave basis. See the reference audit at the end of this document before making further appearance changes.

The user found the water too clear and still. This material-only revision gives undisturbed water a mineral-bearing base instead of waiting for vehicle sediment to tint it, and strengthens the existing sourced ripple layers. Native water/vehicle physics, the grid and upload frequency are unchanged. Both local and static river/lake surfaces share the optics to preserve their match.

`WaterTurbidity=1` changes scattering from (0.00025, 0.00060, 0.00045) to (0.0052, 0.0065, 0.0055), and absorption from (0.003, 0.0015, 0.001) to (0.016, 0.010, 0.006). Opacity changes from 0.085–0.175 to 0.14–0.28 before foam/sediment/facing modulation. Depth attenuation still permits shallower edges to reveal the bed. `SurfaceMotion=1` raises the normal strength from 0.025–0.065 to 2.0–5.0 (combined XY slope capped at +/-0.32), uses a 2.6 m first-layer tile instead of 3.8 m, and lets the broad layer follow the same current. The cosmetic wind drift increases from (0.025, 0.009) to (0.12, 0.055) m/s. Small current-dependent highlight/foam flecks reuse the existing normal sample. This is sourced-texture shader animation, not additional fluid simulation or new procedural noise. Texture sample count is unchanged.

The first gain adjustment (0.085–0.22) made the water cloudier but left motion too subtle: over the water ROI, a 0.75-second material-clock change moved mean RGB by only 0.54/255, with no pixels changing by more than 10 in a channel. Inspecting the source `Art/Textures/Water/rain_ripples/others_0028_normal_directx_2k.png` explained why: signed RG standard deviation is only 0.0185/0.0187 before filtering and approximately 0.0094/0.0095 after an indicative 256-pixel resample. The revised gain above compensates for this source. A restrained facing term from these same moving samples modulates colour, scattering, opacity and roughness, following the existing ford material's lesson about weak normal-only motion under a broad sky. It is art-directed surface shading, not a new physical wave-height measurement. `Appearance_Ford_OpticsOnly.png` preserves the first result.

Setting both controls to zero provides an in-shader comparison with the previous appearance. `WaterTimeOverride=-1` normally uses the material clock; nonnegative values are only for repeatable captured phases. `Art/benmore_water_domain.ps1 -Mode Appearance` saves/reloads the two owned master materials, captures Ford/Upstream/Lake comparisons and a clock-sampled motion sequence, then provides a same-view ABBA timing capture. `-SkipTimings` runs only the visual/save/reload checks. Backups are the two masters' `_BeforeTurbidity` copies. Screenshot completion is checked by fresh file timestamps; the first attempt stopped early on a two-second screenshot wait, before any image was ready.

Final save/reload and capture validation passed (`appearance-report.json`, 16:49 local); the log contains no shader compile errors. Ford, Upstream and Lake before/after images and the Ford material-clock phases were inspected. The Ford shows a cloudier blue/green body, readable bed near the shallow edge, and more pronounced ripple highlights. Over the fixed water ROI (1020,520)-(1380,780), before/after mean RGB changes from (86.87,76.78,56.64) to (71.30,74.15,64.46); mean absolute change is 9.43/255 and 19.47% of pixels change by more than 20 in a channel. A 0.75-second phase change now gives 2.04/255 mean change with 2.76% of pixels over 10, versus 0.54/255 and zero in the first optics-only pass. Adjacent eighth-second phases average 1.60/255 change. These are pixel differences, not direct opacity or animation-quality measurements; reflections/foliage are not isolated. `appearance-pixel-review.json` records the calculation and `Appearance_Flow_Preview.gif` is a two-second, eight-fps clock-sampled preview, with a reset at its loop boundary. It is not a driven simulation clip.

The lake camera exposed a rectangular local/static coverage/join artifact and inappropriate dry-looking background coverage. It is visible with both comparison settings, so this revision did not establish clean lake coverage. Record it separately from the improved Ford material; do not present the lake capture as a finished lake or claim that matching optical parameters alone guarantee a seamless surface. Upstream still has a broad bright sky reflection. Existing authored instance placement and the native Landscape are untouched; the original driving map still has SHA256 `9d806868d3d3465e6f5a6147118deed564327b8dcbd4bcee1b392bc952c9ef5b`.

God of War is active for this revision, so its GPU timing is deliberately deferred under the user's earlier instruction to keep working without timings. `timings_valid` is false and no performance result is claimed. The previous quiet-machine numbers above are not measurements of these revised optics. No C++ or vehicle/terrain physics changed; validation was Python parsing, actual material compile/save/reload, and rendered comparisons/motion pixels. The concurrent shared terrain run passed at 16:38, but it is not a test of this new material and no new native-test pass is claimed.

## Spintires reference audit and corrected implementation order — 2026-10-08

Status: source/code/capture review completed after the user rejected the appearance pass. This is a replacement implementation plan, not an installed renderer revision. No build, new capture, benchmark or driven validation belongs to this audit. Claude's `check_mud_variants.py` owns the running Unreal process; GoWR is also active.

### Source findings

The [2013 Spintires article](https://www.gamedeveloper.com/programming/rendering-and-simulation-in-offroad-driving-game) describes an empirical texture simulation: opacity, flow disturbance and foam, with ping-pong propagation and damping. Its author calls the spline-restricted water geometry a poor choice.

The [2017 MudRunner article](https://www.gamedeveloper.com/programming/mud-and-water-of-spintires-mudrunner) replaces runtime ribbons with a continuous built surface. Its diagrams show a precombined animated texture: RG normals, B wave height, A foam. Direction and speed discretization produces four blended samples. Separate CPU wave/wheel-flow meshes augment the surface. Local GPU simulation packs R height offset, GB dynamic flow and A foam, with mud in a second logical texture; each is ping-ponged. Vehicle immersion and motion drive effects.

Do not conflate the two versions' red channels. The article does not specify an offline flipbook as the only precombine method. Its GPU texture reading does not imply GPU-to-CPU readback. It supplies no measured budget for our Unreal scene.

### What our current code actually does

| Area | Evidence in this project | Consequence |
| --- | --- | --- |
| Ambient surface | `Art/Unreal/benmore_domain_material.py` samples `T_GT_Water_N`, a sourced rain-ring normal, with reset/crossfade advection. There is no precombined animated wave-height/foam field. | Turning `SurfaceMotion` up makes the rings conspicuous. It does not supply evolving, directional surface relief. |
| Geometry | The same material's WPO only uses the live field height on the local surface. The distant surface has no ambient height displacement. The local mesh is on the existing 62.5 cm grid. | Any new wave spectrum must respect mesh resolution; sub-metre detail cannot be represented as accurate geometry by that grid. |
| Near/far continuity | The shader switches local velocity/depth to `live.ba`/`live.g`, and static values to the baked map. The local simulation uses a depth capped at 1.5 m. `Appearance_Lake_After.png` also visibly has a rectangular surface break and extensive brown background coverage. | Identical optical coefficients do not guarantee matching depth, height, masks or coverage. The exact coverage defect remains to be isolated; do not attribute all of it to depth mismatch. |
| Local interaction | `GTWaterRiver.cpp` carries wave disturbances around prescribed mean flow. `GTWaterRiverDetail.cpp` transports and decays foam/silt on the CPU, sourced from occupancy changes. | Retain these useful systems as the baseline. They are not a full catchment fluid model; static banks and newly placed obstacles are not automatically re-solved. |
| Spray | `GTSprayComponent.cpp` already has water droplets from wheels and a bow-spray path. The water rate uses vehicle translation speed/depth; the existing slipping-wheel branch elsewhere is for ground-material spray. | Do not claim that spray is absent or create a duplicate emitter. Inspect its actual result, then integrate wheel-relative motion and current where appropriate. |
| Wakes | The local height field can respond to hull/wheel occupancy, but the Benmore pass has no separate shaped wheel-flow/bow-wave geometry. | A scripted rectangular footprint preview cannot validate a convincing vehicle crossing. |
| Cost | The earlier quiet-machine full-grid measurement was 1.718 ms median DomainTick, 2.432 ms p95, with a 4.246 ms peak during window moves. | Avoid multiplying active grids. A GPU cosmetic path is a candidate to measure, not an automatic performance win. Those values do not benchmark the rejected optics or a future renderer. |

### Implementation stages and gates

1. **Channel, riverbed and continuous surface first.** The user explicitly rejects the outline, bed shape and bed texture as well as the water shader. The morphology addendum below expands this gate: author a representative reach with a changing channel section and bed material zones, then rebake the mean water data from that bed. Use the existing ford, upstream bend, lake mouth and open-lake views. Add coverage/mean-height/depth debug modes. Compare the static surface alone, local replacement alone, and their join with waves disabled. Distinguish physical effective depth from optical depth. Resolve gaps, overlap, exposed rectangles and bank intersections before tuning wave colour. Capture the same stationary views and a focus move across a 10 m window shift. Gate: convincing bare bed and calm surface at driving height, no visible window rectangle or uncovered intended water, native deformability retained. Protect original driving map and roads; re-seat only the placements affected by deliberate bed edits and record their changes.

2. **Coordinated ambient waves.** Replace the amplified rain-ring layer with one shared precombine pass for wave height, its matching slopes and foam breakup. Start with a small fixed-resolution render target updated once for the scene, independent of water area; profile the resolution/update rate rather than choosing a final budget from intuition. This pass is numerical/procedural wave data, explicitly distinct from painting a new art texture. Any imported art maps still require sourced/licensed assets. Both near and distant water use one world phase and the same authored flow. Interpolate neighbouring fixed direction/speed bases; transform sampled slopes back into world space before blending. My technical inference is that fixed bases avoid the coordinate twisting caused by continuously rotating UVs across a varying current. Count vertex and pixel fetches plus the prepass, not just the four surface samples. Band-limit geometric waves for the 62.5 cm grid, leave shorter waves in normals, fade height at shores, and use compatible distant LODs. Gate: fixed-camera motion has evolving crests moving along the bend, no rain-ring character or reset pulse, and continuity survives a window shift.

3. **Localized foam and sediment.** Keep the existing transported fields as a control. Improve sources using wheel/hull immersion and relative water motion, including spinning wheels, with bed/material eligibility for sediment. Separate thin surface foam from an underwater silt cloud; clear shallows and disturbed water should differ for a reason. Preserve state through window shifts. Prototype a bounded GPU cosmetic update only after the source/transport result is right, keeping vehicle queries and buoyancy independent of it. Gate: disturbance travels downstream, decays, stays out of dry cells, and does not change physical height/force results. Compare CPU and GPU paths including upload/submission and render cost before selecting one.

4. **Vehicle and bank interaction.** Reuse existing spray plumbing and add a small capped set of shaped bow/wheel wave meshes if the field alone lacks the needed silhouette. Tie them to current-relative motion and immersion; fade them with distance and inactivity. Connect limited wet-bank/stone effects to existing terrain/mud ownership. Gate: actual driven entry, stationary wheelspin, crossing, exit and wake decay, from driver and external views. Require motion captures, not only stills or a material-clock GIF.

5. **Scale and profile.** Apply the accepted surface to the river/lake domain, then audit legacy ford/rut-water consumers before calling it "all water." Keep active simulation bounded as the map grows. Measure identical effect-off/effect-on views on a quiet machine: total frame, DomainTick, shift spikes, uploads, water rendering and overdraw. The previous scene's Lumen/vegetation bottleneck remains a separate target. No 60 fps promise or GPU speedup is established by this plan.

Stage 1 is the next implementation gate. Stage 2 supplies the missing ambient water character; stages 3 and 4 provide interaction. Raising tint, foam gain or rain-normal gain again is not a substitute for those gates. The original optical pass remains installed pending replacement; its `_BeforeTurbidity` backups and comparison controls remain available.

### Channel form and riverbed addendum — user feedback, 2026-10-08

The water outline, mean surface shape, native bed cross-section and bed texture all require improvement. This is structural river authoring before the wave-renderer pass. Do not treat the task as a request for more opacity, uniformly deeper water, generic noise displacement or taller bank berms.

**User clarification: realism, not greater depth.** Keep the existing depth and ford profile as the baseline. Remove deeper pockets or a deeper central channel as improvement targets. Prioritize believable contours, continuous water/ground intersections, bank transitions, embedded aggregate, material scale and coherent sediment patches. Any local geometry refinement serves those features; it is not a general lowering of the bed or raising of the water.

**Current evidence.** `Art/tools/audit_benmore_channel_shape.py` is a read-only survey. It writes `Art/Export/BenmoreGaea/RiverScale/ChannelAudit/channel-audit.json` and `Channel_Audit.png`; the height source remains byte-identical. The figure's vertical axes are exaggerated and differ between sections. It is not an Unreal screenshot or a proposed finished shape.

- The current native wet domain has 7,403 source cells. Depth p10/median/p90 is 4.65/12.81/41.38 cm; 64.55% is below 20 cm. These are saved mean-domain values, not surveyed river depths or evidence that the river needs deepening. Keep them as baseline diagnostics; improve the visible bed itself.
- Sampled wetted widths are 4.90 m at the ford, 6.15 m at the selected upstream bend and 4.30 m at the bridge. Mean-surface transverse ranges are 1.64, 13.83 and 10.62 cm respectively. A bend can physically have transverse slope; these values are inspection targets, not automatic proof of invalid hydraulics. Inspect cross-channel tilt together with along-channel grade and current.
- `bake_benmore_river_life.py` applies a similar rounded incision: nominal half-width 3.0–4.2 m, a repeated longitudinal offset, and closest-point selection from drainage samples computed on a roughly 3.75 m grid. It does not project onto continuous line segments. This can imprint sampled-point bulges; the diagnostic wet-footprint plot shows a repeating pattern worth isolating. Use continuous segment distance and interpolated station/profile data before adding authored variation.
- `prepare_benmore_water_domain.py` modestly smooths a 1.25 m mean-surface grid and clips geometry with a binary wet mask. It cannot create new channel structure or recover a detailed shoreline from resampling. Surface tessellation should be independent from hydraulic resolution; use interpolated depth/shore contours and adapt geometry to bends, banks and grade changes.
- `M_RS_Terrain`'s builder reuses loose road-gravel and clay maps at one 6.2 m tile scale. Its gravel colour is reduced to luminance times a fixed mineral tint; ecology weights are mostly distance/patch masks. It lacks distinct coarse bed, depositional shelf, fine silt and damp-edge zones. The local deformation material must receive the same revised surface rules to avoid a rectangular texture transition at the crossing.

**Rebuild target (our art direction, not a surveyed reconstruction).** Establish one 100–150 m reach around the existing ford and a bend as the first comparison, retaining the current depth baseline and traversable ford profile. Remove sampled-point scalloping and awkward shoreline triangles, then refine width transitions, gently sloped gravel shelves and locally sharper bank edges where the existing bend supports them. Organize embedded stones and fine sediment into coherent shallow runs and sheltered patches. Existing quieter/deeper areas may receive different surface treatment without excavating new pools. Keep long views, low banks and native deformability. Judge the result by natural shape, material scale and water/bed integration, not increased depth or a larger channel.

This design uses the distinction between pools, riffles and runs described by [USGS channel-unit guidance](https://water.usgs.gov/nawqa/protocols/OFR-93-408/habit5.html). Bed material should have coherent patches rather than uniform scatter; [USGS-hosted gravel-bed research](https://www.usgs.gov/publications/effects-hydraulic-roughness-surface-textures-gravel-bed-rivers) relates texture variation to channel roughness and local features. These sources support the general design logic, not exact New Zealand grain sizes, dimensions or discharge.

**Bed appearance.** Use sourced, licensed river-gravel/cobble and fine sediment maps with matching normals/height and checked world scale. Preserve restrained grey/tan stone colour variation under the existing grounded painterly palette. Put coarser embedded stones in selected shallow runs, mixed gravel on shelves, fines in sheltered pockets, and a narrow uneven damp transition at the waterline. Larger silhouette stones need a small, grounded, distance-limited instance set. POM may provide nearby aggregate relief after a cost comparison; it cannot replace channel depth, stone silhouette or collision. Avoid an evenly spaced line of rocks along both banks.

**Dependency order.** (a) Prepare a separate native-heightfield candidate and a masked delta for the pilot reach; preserve road heights and record affected plant/stone supports. (b) Inspect the bare bed and calm water, including longitudinal and transverse sections. (c) Rebake water surface/depth/current, coverage and bed/deposition masks together; do not reuse the old flow field over a changed bed. (d) Update the review map, native collision/deformation samples, crossing material and affected asset grounding together. (e) Validate water/terrain query agreement, continuous joins, ford driving and visual scale; only then proceed with stage 2's coordinated waves. Static bank meshes must not replace the deformable native bed. The existing fixed-bank local solver still does not simulate arbitrary bank excavation or floodplain expansion.

This addendum and survey are implemented. The following pilot is prepared; its installation and visual gate are recorded separately below.

### Channel pilot — existing depth baseline, 2026-10-08

Prepared `Art/tools/prepare_benmore_channel_pilot.py`, `Art/Blender/export_benmore_channel_pilot.py`, `Art/Unreal/benmore_channel_pilot_materials.py`, `Art/Unreal/install_benmore_channel_pilot.py` and `Art/benmore_channel_pilot.ps1`. The bounded reach is X −725 to −550 m, Y 105 to 310 m. Its data masks use 25 cm spacing. This first pass preserves the native heightfield and hydraulic bake, so it requires no replacement flow bake. It refines the existing water mesh against the same wet-weight interpolation used by the runtime query and trims shore intersections against the native bed. Original vertices outside the bounds are unchanged. This improves tessellation/intersection fidelity; it does not reauthor the drainage line or remove every coarse-domain outline feature.

The surface grows from 21,460 to 69,961 triangles, with refinement confined to the pilot. All coordinates are finite and triangle areas are positive. Maximum correction to an original water vertex is 11.453 cm, toward the unchanged hydraulic query surface. The physical depth baseline does not change. Native heightfile SHA256 remains `34675cde7d8a2f8758dfd92ec814a823c6b1ddfa10c3bc626a19292140279c30`; hydraulic bake remains `6cde89f3e5554c154382f2a6ef7ecf63aa9ebf04aee890a87e1ce426b4970e57`.

Bed detail uses the unmodified CC0 [Poly Haven river small rocks](https://polyhaven.com/a/river_small_rocks) diffuse, DirectX normal and roughness maps at their published 2.9 m repeat; the source manifest records URLs and checked MD5s in `Art/Textures/RiverBed`. Geographic zones derive coarse aggregate, sheltered fines, wetness and influence from the existing bed/current and shore distance. The colour retains mineral variation rather than only fixed-tint luminance. Fine repeat, normals and roughness detail fade from 35 to 100 m; samples outside the pilot mask are skipped. The same appearance wrapper is prepared for native Landscape and the existing deformable crossing material, retaining the deformation WPO and profile constants.

550 decorative 7–19 cm aggregate instances are prepared, flattened and seated by bottom-vertex supports against the native bed. They exclude the ford's 13 m radius and existing approach/path mask. Four instance groups have no collision, shadows or distance-field contribution, with culling from 50 to 110 m. These are local visual stones, not new driving obstacles or a replacement for deformable ground.

**Installed and checked:** `BENMORE_CHANNEL_PILOT_OK`. Material compilation, map save/reload and eight matched Ford/Bed/bare-bed/Reach stills passed. All 90,353 existing authored instance transforms retain SHA256 `2a4413d553fbba0c1677c85e2d515cd205640d6f1280992ea8b892a2d8fa7fdb`. Four static water query locations (ford, bed, bridge, lake) and eight native collision supports match exactly after reload. Both crossing profiles reference `M_CP_DeformField`; their movement/deformation settings were preserved. All 550 stones were seated with sampled bottom vertices below native ground: greatest basal gap −0.70 cm. The original driving map retains SHA256 `9d806868d3d3465e6f5a6147118deed564327b8dcbd4bcee1b392bc952c9ef5b`. Evidence is in `ChannelPilot/install-report.json`, `pixel-report.json` and `Channel_Comparison.png`.

**Pixel/visual review:** the bare-bed ROI's luma standard deviation rises from 0.04336 to 0.07001, and mean adjacent horizontal pixel difference from 0.00746 to 0.01573. The water-visible Bed ROI rises from 0.00389 to 0.00906 in adjacent pixel difference. These are still-image measurements only. The reviewed renders show grain relief and sparse embedded stones in place of the formerly smoother uniform bed. They also confirm that the larger repeated shoreline scallops remain. Refining the mesh and projecting it onto the unchanged physical surface does not fix native bank contours. The lake's pre-existing coverage/optics defect and ring-like water normals remain visible. Do not describe this pilot as finished river morphology, believable ambient flow, an accepted visual gate or a measured speedup.

The first launch failed before installation because UE 5.8 retained a standalone duplicate World while loading its backup. The runner now creates new map backups through `save_map`; a fresh process with the preserved backup completed successfully. The shared mud session was never stopped. A second shared mud-variants session started after the successful river capture, blocking further in-engine work. An experiment that would trim the visible shallow-water film was discarded: hiding part of the water cannot repair the bank geometry. The prepared files again match the installed report exactly.

**Native-shape follow-up:** the candidate, matching bake, import and support checks are now completed in the continuous-channel stage below. This material pilot itself did not change native C++ code or vehicle constants and did not include a C++ rebuild, driving regression or GPU timings. The new MudRunner-style ambient height/normal/foam renderer remains a subsequent stage.

### Continuous native channel — removing point-stamp banks, 2026-10-08

The user's repeated "line of circles" feedback was an actual native-heightfield problem. The old carve measured distance to individual drainage samples and selected their nearest floor target, leaving overlapping disc cuts. `find_benmore_channel_alignment.py` recovered the original sampling phase (i=0, j=1 on the 3.75 m drainage grid); reconstructing the old carve then matched every saved native sample. This exact reconstruction is the baseline, rather than a fresh drainage trace with a different phase.

`reshape_benmore_channel.py` now projects samples onto continuous line segments and interpolates the original longitudinal floor targets. It retains the original nominal half-width rule, 0.7 m core and maximum original incision of 1.09375 m; there are no new deeper profile targets or raised berms. Ford and footbridge protection uses cross-channel strips with a longitudinal blend. Their sampled cross-sections across ±11 m are exactly unchanged, as are protected roads. The native candidate changes 5,733 of 4,068,289 samples over 8,816.19 m². Local signed terrain deltas span −0.6875 to +0.25 m, with median −0.0625 m; these reshape bank/inter-sample contours, not a new deeper channel target. Residual incision-width variation above 10 cm, excluding the protected crossing, falls from 0.73353 to 0.04190 m RMS after a 10 m station filter (94.29% reduction). This geometric measure is not an artistic acceptance gate.

The matching conservative shallow-water bake warm-started the previous state and advanced another 5,200 simulated seconds over 455,227 active cells. Original inflow (0.8 m³/s), lake level (0.60 m), Manning coefficient (0.055) and bounded runtime solver settings remain. `flow-report.json` reports converged/stable, connected to the lake, no artificial wet corridor edge, conservation residual −2.55e−11 m³ and maximum depth/velocity drift over 200 simulated seconds of 0.00254 m / 0.00762 m/s. This is an offline mean-flow bake; no catchment-wide runtime simulation was added.

`prepare_benmore_channel_shape.py` rebuilds mean/depth/current, bed/shore/ecology masks and geometry together. The surface follows the new river-wet contour and its intersection with native ground; lake-only coverage is excluded from river geometry. Runtime wet-weight interpolation is used at mesh vertices (stored query error 0 m). River/outlet meshes contain 50,248 / 30,356 triangles at 0.625 / 1.25 m spacing, with finite coordinates and positive areas. The new ford water surface is 2.657 cm lower, leaving 7.543 cm depth over the unchanged 15.751125 m native ground. Do not report physical water depths as unchanged: rebaking changes them even though the original bed profile targets and crossing ground are retained.

**Installed and reloaded:** `BENMORE_CHANNEL_SHAPE_OK`, in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`; backup `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeChannelShape`. Owned assets are under `Gaea/ChannelShape`, including the matched water domain, surface meshes, Landscape/deformation materials and crossing profiles. The existing sourced CC0 aggregate remains the art input; only geographic data masks were rebuilt. Native Landscape and the live deformation material/WPO remain active. Both mud/gravel deformation profiles retain their previous values. All 90,903 authored instances retain exact XY/count signatures; 57,808 road instances retain full transforms. Re-seated 700 affected plants/stones vertically against native triangle support, with no sampled basal gap (at least 0.7 cm embedding). No instances were added or removed. Rotation difference is zero; scale round-trip difference is 1.78e−15.

All 4,068,289 reloaded packed native samples match SHA256 `d2706ef14458f2915a8357a76d78effde2647bcf0d549693a9f9f6cc08e59fa5`. The maximum of 33 native collision support errors is 0.0811 cm. Ford/bed/bridge/lake coverage queries pass. The original driving map hash remains `9d806868d3d3465e6f5a6147118deed564327b8dcbd4bcee1b392bc952c9ef5b`; no C++ or tuned movement/deformation constants changed.

**Actual visual evidence:** twelve Unreal before/after stills include wet overhead, bare overhead, reach, bed and ford views. Inspected overhead/bare/reach images show continuous banks in place of the repeated disc edges. `sample_benmore_channel_shape.py` writes `pixel-report.json`; mean absolute RGB changes are 18.93/255 in Plan, 13.82/255 in Plan_Bare and 16.82/255 in Bed_Bare. Cameras and water clock match, but exposure, vegetation motion and shadows were not frozen, so these pixel differences do not isolate geometry or measure realism. `Bank_Shape_Comparison.png` is the compact actual-render comparison; `Channel_Shape_Comparison.png` includes the other views. A pre-existing vertical shading seam remains in the overhead views, including bare bed; its cause is not isolated. Circular water normals and the lake coverage/optics defect remain. The route still follows the original drainage line; this does not finish natural channel variety or the ambient-flow appearance.

**Tests and open gates:** native import/collision/save/reload, offline geometry/flow checks and still sampler passed. The required `bash Art/suite.sh terrain` ran once before importing this review-map change and returned `FAIL terrain`: forward bog escape (6.5 m in 12 s) and the documented step-11 held-rut-exit gate failed; ford/water gates passed. These are on the independent existing test map, not a driven Benmore validation. Its result is preserved in `ChannelShape/terrain-regression.txt`; do not tune existing movement to make it pass. No C++ module changed, so no rebuild/additional module tests were needed. Shared mud sessions were allowed to finish before this stage's single editor; their end-of-session suite ownership was not duplicated. Owner driving, continuous-join inspection, water-normal/ambient-wave replacement, shading seam/lake repair, artistic acceptance and quiet-machine timings remain open. No FPS or measured speedup claim.

**Reproduction/evidence:** `Art/benmore_channel_shape.ps1` supports `-WaitForShared`, `-BaselineOnly` and `-VerifyOnly`; normal retries start from the backup to avoid double-applying support offsets. Supporting scripts: `Art/tools/{find_benmore_channel_alignment,reshape_benmore_channel,check_benmore_channel_shape,prepare_benmore_channel_shape,sample_benmore_channel_shape}.py`, `Art/Blender/export_benmore_channel_shape.py`, `Art/Unreal/install_benmore_channel_shape.py`. Reports, packed heights, matching bake/domain and renders are in `Art/Export/BenmoreGaea/ChannelShape`. Subsequent work should start from the installed review level, not re-run the old point-stamp RiverLife carve.

### User correction and river-system diagnosis — 2026-10-08

The user considers the continuous channel too straight and neither a convincing river nor a stream, and asks why Gaea did not supply the channel. They explicitly require understanding rivers/creeks before another claimed solution. The proposed arbitrary bend/width patch was stopped before any new terrain, assets, bake or map changes. Stage 87 only corrects point-stamp continuity; its river morphology is not accepted. The authoritative next gate is the diagnosis/reconstruction below, not lateral sine offsets on the existing cut.

**Read-only evidence:** `Art/tools/audit_benmore_river_provenance.py`, reports and `Gaea_vs_Current_Channel.png` under `Art/Export/BenmoreGaea/review/RiverProvenance`. The figure is a terrain/mask data visualization, not a new Unreal render or a replacement design. It shows the returned Gaea river footprint in blue, the later priority-flood paths in orange and the resulting additional native cut in a separate panel. The Gaea starter actually contains a Rivers node; the issue was not simply omission of river generation.

- The saved Rivers node receives the Erosion2 terrain and headwater mask. Its Out is blended with the original terrain at Ratio 0.5 through the catchment mask. M_Rivers, M_Depth and H_WaterSurface are exported directly from Rivers, before that blend. The return converter additionally multiplies terrain delta by (1-protect). Water and final ground therefore cease to describe the same geometric result. At selected river samples (M_Rivers >0.5, edit >0.3, protect <0.5), raw Gaea surface minus imported ground has median +0.721 m, p90 +4.492 m, extrema −2.139 / +5.876 m. This is not a request to make water that deep or a calibrated flow prediction.
- Archived raw channel inspection is from the exact same build: H_InputCheck, H_Eroded, H_WaterSurface, M_Rivers and M_Depth TIFF hashes match the returned files. Raw surface minus raw Rivers bed is median +0.00480 m, p90 +0.03888 m, with some negative/edge values after native resampling. It still needs consistency checks; it is not directly usable as a finished gameplay water domain. Gaea M_Depth ×512 has median 0.01383 m over the same mask selection. None of these values is a verified real regional creek depth.
- Later `bake_benmore_river_life.py` ran a separate priority-flood parent-path trace at 3.75 m grid spacing and cut an authored floor/width profile along it. This algorithm routes to an outlet; it does not compute sediment transport, lateral migration or a natural bankfull corridor. The installed continuous carve mostly follows that path, not Gaea's network. Only 3.581% of the additional >10 cm cut area overlaps Gaea's selected river mask. Main path samples have median 22.45 m distance to that mask. This is the central integration mistake.
- The 299.4 m crossing reach is almost straight: length/direct endpoint distance 1.00125, mean authored profile grade 6.80%. Upper/lower main reaches are about 12.98% / 1.61% mean grade. These measurements suggest different reach treatments; they do not prove a waterbody classification. Existing ford placement follows the later path and does not coincide with the blue Gaea course in the diagnostic. Crossing positions must be reconciled with the chosen course rather than forcing natural drainage through an incidental old placement.
- The conservative shallow-water solver computes water over a fixed bed. A successful/stable bake proves numerical flow properties, not that channel morphology is natural. Foam/sediment appearance fields do not model erosion/deposition of the riverbed. The 2048 Gaea build over 2.5 km has 1.221 m raster spacing, and the native grid is 1.240 m; a few-metre creek is only a few cells across. Do not expect that raster alone to provide small stone/shelf detail.

The audit verifies the candidate height, current channel height, review map and original drive-map hashes remain unchanged. No Unreal session, terrain regression, native build or performance timing was run for this read-only diagnosis. Current stage-87 assets remain installed pending a replacement that passes the gates below.

**What the system needs to describe:** separate the surrounding drainage valley, the wider bankfull gravel/erosion corridor, the narrower water footprint at the chosen flow, and local bars/bank transitions. A stream's banks should not simply be two parallel edges of its current water mesh. Different constrained/steep and open/low-gradient reaches require different morphology. The [NIWA river morphology guidance](https://webstatic.niwa.co.nz/library/NIWAsts53.pdf) identifies discharge, gradient and substrate as interacting controls for gravel-bed streams and rivers; braiding additionally requires a suitable sediment/flow setting. It is not appropriate to turn this small headwater course into a braided river solely because the wider region contains them. Use a regional reach reference and actual terrain constraints to choose the target.

**Replacement stages and gates:**

1. **Establish the course and reach type.** Inspect the original DEM, Gaea's tributaries/valleys, slope changes, outlet and a regional gravel-creek reference. Identify one representative 100–150 m reach and its wider gravel corridor. Record the reference, dimensions, intended flow stage and channel units as art targets, with any inferred features labelled. Resolve crossing locations against this course. Gate: course/corridor plan and bare bed sections make sense before water shading. Do not invent periodic bends or claim surveyed drainage from an art parameter.
2. **Make Gaea the coherent channel source.** Create a separate graph study in which protected general erosion/blending is resolved before the final Rivers result. Export the final channel bed, Rivers footprint, surface/depth and deposition maps from the same final channel state. Roads/boundaries/outlet remain constraints; if the resulting channel intersects one, flag and design the crossing rather than blend away the bed underneath an unchanged water export. Any subsequent bed protection or gameplay change invalidates the associated raw surface/depth until recomputed. Gate: source/build hashes, datum/orientation, mask alignment, native profile sections, no blocked/out-of-domain outlet or floating water. Preserve the user's graph and returned files.
3. **Validate one creek in a separate Unreal study.** Preserve the approved Gaea channel course/topology. Refine bankfull corridor, gravel shelves, bed-material zones and locally meaningful obstruction detail where the raster cannot carry it; use sourced aggregate and retain native deformable ground. Permit necessary repositioning of crossing/dressing assets and report it. Gate: same-camera dry/wet overhead, bank-height and driving views show the complete channel/corridor relationship; inspect grounding, plant exclusions, native collision and crossing/deformation. Static side meshes cannot replace the deformable bed. This is an explicit visual gate, not passed by a smooth outline metric.
4. **Bake and render matching water.** Place source discharge on verified inlets of the chosen network and rebake on the exact final native bed; export mean/depth/current/coverage, wet masks and material zones together. Make every render/query consumer use this same version. Then implement coordinated surface waves/normals/foam and interaction on the existing bounded local window. Gate: inlet-to-lake coverage/joins, mass/stability, bed/query agreement and moving/driven captures. Wider shape remains baked; no full-world live morphodynamic solver is proposed.
5. **Scale only after the reach works.** Reuse the validated data contract for tributaries, creek, river and lake transitions. Check resolution/LOD/material cost, inactive simulation sleep, overdraw and exact shared-machine profiling conditions. Gates: owner-driven crossing and quiet-machine timings. Tuned vehicle/mud physics remain untouched.

The division is consistent with the [Gaea Rivers documentation](https://docs.gaea.app/reference/nodes/simulate/rivers.html): it supplies generated pathways and changes terrain; Headwaters controls their origin. [MudRunner's own rendering/simulation account](https://www.gamedeveloper.com/programming/mud-and-water-of-spintires-mudrunner) describes authored varying-width curves baked into a continuous surface/flow texture, with separate local interaction simulation. It does not demonstrate automatically evolving a realistic river channel through its inexpensive runtime water effects. Neither source makes the present appearance an accepted result.

## 89. Benmore Gaea creek course and native gravel banks (2026-10-08)

Regional direction is shallow runs, an uneven grey gravel corridor and inside bars, with a single channel and tributary joins in narrow hillside reaches. References: [DOC Project River Recovery](https://www.doc.govt.nz/documents/conservation/land-and-freshwater/Freshwater/PRR/prr-strategic-plan-2006-2012.pdf), [DOC upper Waitaki vegetation study](https://www.doc.govt.nz/documents/conservation/land-and-freshwater/Freshwater/braided-river-vegetation.pdf), and [ORC Manuherekia instream habitat assessment](https://orc.govt.nz/media/15449/instream-habitat-and-minimum-flow-requirements-in-the-manuherekia-river-2016.pdf). This is a regional art interpretation, not a surveyed watercourse reconstruction.

The separate `review/CoherentCreek/Benmore_PairedCreek.terrain` applies protected erosion before Rivers and exports bed/surface/depth/mask from the same final Rivers node. Gaea 2.3.0.1 Swarm built successfully. Its raw Rivers Out raises some ground by about 9 m and was rejected for direct import. Mask-confined extraction instead restores Gaea's upper course, resampled at 2 m with about 4 m raster smoothing. Native cross-sections refine the protected original terrain with asymmetric inside shelves, tighter outside banks and no raised berm. The retired upper trench is restored. The tested lower outlet remains west of X=-875 m and joins near X=-843 m, where course separation is under 3 m, through a 65 m transition. This avoids forcing raw Gaea channels across protected road/shoreline grades. Earlier full-Gaea lower-route trials were rejected and never imported. This is authored bank geometry, not sediment transport or bank migration.

Installed in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`, with backup `L_Benmore_BeforeGaeaCreek` and owned assets under `Gaea/GaeaCreek`. All 4,068,289 reloaded packed native samples match `0b9c495fdca8599bd4e1b7d03c6c72ddfc2e2244f97166b12442069e61de9d9a`; 11,856 samples changed from stage 87. Maximum cut below original terrain is 1.15625 m; this is terrain cut, not water depth. All 33 native collision checks pass, maximum error 0.07391 cm. Ford/bridge/bed/lake queries cover their points and match the baked/rendered mean surface. Ford/bridge/bed water depths are 20.15 / 16.16 / 21.49 cm; these differ from the prior locations/bake, so do not claim unchanged physical depths. Native Landscape, live deformation material and WPO remain active, and existing deformation profile values are unchanged. Vehicle/mud/snow tuning and original `L_Benmore_Drive` hash remain unchanged.

Re-seated 1,654 affected supports vertically against native triangle geometry; maximum sampled basal gap is -0.7 cm. Relocated 4,721 review-owned tree/rock/gravel/shrub/tussock/aggregate instances to the new banks, embedded at least 1.5 cm. The ford moved from (-661.25,177.5) m to (-675,223.75) m, about 48.25 m; the footbridge moved about 2.8 m to (-403.75,437.5) m and its deck/ramps were rebuilt against the banks. Authored instance count remains 90,903. All 57,808 road instances retain full transforms. Geographic vegetation/wet/crossing masks were rebuilt; no new generated art. Bed art remains sourced CC0 Poly Haven river_small_rocks with an authored 78% neutral grey mix (cool tint RGB 1.08/1.10/1.12, gain 1.20).

The existing conservative fixed-bed solver was rebaked on the exact quantized native bed with the existing authored 0.8 m3/s total discharge. At 4,200 simulated seconds the visible channel is stable over a 200 s window: maximum depth drift 0.001964 m and velocity drift 0.004610 m/s, conservation residual -3.73e-11 m3, positivity correction zero, connected to the lake, no artificial wet corridor edge. **Discharge is not fully converged:** final outflow 0.73927 m3/s versus inflow 0.8 m3/s, with storage continuing outside the visible channel. `flow-report.json` deliberately retains `converged:false`. The installed time-averaged fixed-bed bake is a stable visual reference, not catchment hydrologic equilibrium or a calibrated regional river. Offline pruning retains 50 m around wet water/course, removed only 1.056e-9 m3 and leaves 268,362 offline cells; runtime interaction remains 9,216 cells, 60 m span, 0.625 m spacing. River/outlet static surfaces contain 56,753 / 29,791 triangles, sampled at 0.625 / 1.25 m, with finite geometry, positive areas and zero stored mean-surface/query error.

Twelve same-camera Unreal before/after stills were captured, including wet/bare overhead, reach, bed and ford. Inspected overhead views show the winding course in place of the straight trench; bank views show the broader uneven gravel shelves. The river/gravel are still an owner-review candidate, not accepted realism. A fresh-load render exposed black water from serialized editor-preview dynamic material overrides whose field/detail textures are transient. The installer now restores asset parents and clears preview sections before saving; VerifyOnly saves clean parents, reloads, verifies those parents, then captures and discards transient preview overrides. Final clean-load parent checks and wet renders passed. A 6 m optical blend between baked and local depth/current, with local foam/sediment faded at the same boundary, provides a gradual optical transition at the local-window perimeter; remaining shading changes are still visible in the bank views. Geometry/query/physical solver are unchanged. No added texture samples. Still sampler passes: mean absolute RGB changes Plan 14.04/255, Plan_Bare 10.17/255, Reach 19.76/255, Bed_Bare 28.49/255, Ford 18.79/255. Cameras and water clock match; exposure/vegetation are not completely frozen, so pixel differences do not isolate shape or measure realism. `Gaea_Bank_Comparison.png` is the compact actual-render comparison; `Gaea_Creek_Comparison.png` contains five view pairs.

Required `bash Art/suite.sh terrain` ran once: **FAIL on held-rut exit (step 11)** on its independent test map; ford/water/float/carry/winch gates passed. Result retained in `GaeaCreek/terrain-regression.txt`; tuned physics were not altered to get a pass. No native C++ change or additional module rebuild/tests for this asset/material stage. Shared editor tests were allowed to finish; no second Unreal process or duplicate shared full suite. Owner-driven crossing/bridge approaches, Gaea/outlet join inspection, discharge equilibrium, regional art acceptance, inherited circular ripple normals, lake/shading defects and quiet-machine FPS/GPU profiling remain open. No driving-feel, runtime performance or measured speedup claim.

Scripts: `Art/tools/{prepare_benmore_gaea_creek,build_benmore_gaea_creek,prepare_benmore_gaea_creek_assets,sample_benmore_gaea_creek}.py`, `Art/Blender/export_benmore_gaea_creek.py`, `Art/Unreal/install_benmore_gaea_creek.py`, `Art/benmore_gaea_creek.ps1`. The existing bake helper `reshape_benmore_channel.py` gains a backward-compatible optional initial-state directory. Normal installation operates in the destination World with a separate backup and rejects an already-installed course; after a saved install, use `Art/benmore_gaea_creek.ps1 -WaitForShared -VerifyOnly` for material/capture verification rather than re-seating again. Graph study/contract/network files are under `review/CoherentCreek`; packed native height, baked flow/domain, geometry, masks, placements, install/pixel reports and renders are under `Art/Export/BenmoreGaea/GaeaCreek`. The original user Gaea graph/returned files are preserved.

## 90. Whole-course correction after shape rejection (2026-10-08)

**Owner verdict after installation: rejected as unnatural.** The technical results
below remain valid; they do not establish that this channel has a convincing shape.
See the morphology research and isolated experiment following this section.

The user rejected stage 89 as straighter and not good enough. Its import/flow checks did not establish artistic acceptance. A whole-course audit found about 600 m of retained near-straight lower outlet. Stage 90 replaces that retained route and the middle course, rather than smoothing a short reach again.

Gaea headwaters and tributary junctions remain. Authored world-space controls set larger, unequal middle/lower bends, joined by chord-parametric splines, with asymmetric inside gravel shelves and tighter outside banks. This is a regional art interpretation, not an exact Gaea lower-course extraction, a surveyed watercourse or automatic meander simulation. Regional context: [ORC Kakanui/Kauru channel morphology](https://www.orc.govt.nz/media/3841/channel-morphology-and-sedimentation-in-the-kakanui-and-kauru-river-north-otago.pdf) and [DOC upper Waitaki vegetation study](https://www.doc.govt.nz/documents/conservation/land-and-freshwater/Freshwater/braided-river-vegetation.pdf). The complete main path is 1873.31 m. Retired creek cuts are restored; dry/wet/gravel/mud/vegetation masks and existing bank assets follow the new corridor.

Native Landscape remains deformable. 26,501 samples changed from stage 89; all 4,068,289 reloaded packed samples match `a89e743fe49a971afe77545fa075a6b2d0390ecb9b706b9fc78b51b6c02f2812`. Roads retain native heights and all 57,808 instance transforms (`3e7d265a6140af39cfe5f1333095935ee2a1d70e25639d0f52a0bd259726d784`). Maximum native cut below original terrain is 2.50000 m: this is terrain excavation adapting to transverse slope, not a deeper-water target. No raised berm or native static riverbed overlay. The channel has a broader shallow floor and a minimum downhill bed grade to prevent backwater spilling into the downslope route. Old shoreline protection is released only near the revised mouth. The existing scenery apron at X<=-1250 m was rebuilt from the same exterior solver bed to remove its raised outlet sill; native terrain is not replaced. Native collision checks: 33, maximum error 0.09775 cm; exterior-apron checks: 2, maximum error 0.00000 cm. A shared geographic gravel atlas adds 267 exterior columns while retaining every native mask pixel byte-for-byte. The sourced CC0 gravel wrapper also shades the apron, blending geographic zones over 15 m at the join; the native material retains its sample count, while the apron gains the existing aggregate samples. This has no measured GPU-cost result.

At 4400 simulated seconds, 200 s maximum visible depth/velocity drift is 0.000024 m / 0.000085 m/s; conservation residual -9.64e-11 m3, positivity correction zero, lake-connected and zero artificial wet-edge cells. Final outflow 0.79926 against authored inflow 0.8 m3/s; `converged:true`. This is a conservative fixed-bed bake, not regional hydrologic calibration, erosion or sediment transport. Runtime interaction remains 9,216 cells over 60 m at 0.625 m spacing; no additional catchment-wide runtime simulation. River/outlet surfaces contain 65,343 / 21,888 triangles, sampled at 0.625 / 1.25 m. Shared bed/mean/current/masks give finite positive geometry and zero stored surface-query error. Ford/bridge/bed depths are 12.85 / 9.70 / 24.48 cm at their updated points; do not claim unchanged physical depths.

Installed in `L_Benmore_GaeaReview`, with backup `L_Benmore_BeforeCourseRevision` and owned assets under `Gaea/CourseRevision`. Re-seated 2,487 affected supports, then relocated 4,721 review-owned bank instances and removed 3 ordinary plants from wet ground. Reconciled ford/profile route, footbridge and ramps. Deformation profile values, live field material/WPO and original `L_Benmore_Drive` hash remain unchanged. This stage does not edit tuned vehicle/mud/snow code. Sourced CC0 gravel is retained; added image masks are geographic data, not generated art. Clean asset water parents are saved and verified after reload, avoiding transient editor-preview materials.

Actual Unreal captures include whole-course and lower-reach comparisons, plus wet/bare plan, reach, bed and ford. `FullCourse_Comparison.png` and `Lower_Comparison.png` compare identical cameras before/after; the pixel sampler reports changed images, not realism or speed. Fresh renders caught an atlas-coordinate bug that clipped water: the wider UVs now apply only to gravel-zone lookup; shoreline/deformation masks retain native coordinates, with a material-source assertion. Failed captures are archived under `rejected-water-mask-coordinates`; final wet and bare views were inspected again after correction. Water clock matches, but exposure/vegetation are not completely frozen. The wider view is the review basis; artistic acceptance is still the owner's. Required `bash Art/suite.sh terrain` ran once and **PASS** (270 s) on the independent existing test map. No tuned physics was changed to force a pass. No new C++ build required. Shared tests were allowed to finish before the single-editor import. Driving/bridge approaches, moving-water joins and quiet-machine FPS/GPU profiling remain unverified. Inherited ripple-normal and shading limitations remain. No accepted-realism, driving-feel or measured-performance claim.

Controls: `build_benmore_course_revision.py --prepare --seconds …` (fresh solve), `--resume --seconds …` (unchanged bed only); `prepare_benmore_gaea_creek_assets.py --course-revision`; Blender `export_benmore_gaea_creek.py -- --course-revision`; `Art/benmore_gaea_creek.ps1 -WaitForShared -CourseRevision`. After a saved install, use `-VerifyOnly` rather than re-seat twice. `prepare_benmore_course_outlet.py` keeps the exterior bed/mask aligned. Failed conveyance/bend/sill candidates are archived and were not installed. Data audits are labelled separately from actual Unreal renders. Reports and captures: `Art/Export/BenmoreGaea/CourseRevision`.

### Shape research after stage 90 rejection (2026-10-08)

Request: "it does not look natural. find put how to do the shpaew!" Research,
code/terrain diagnosis and a separate geometry experiment are complete. **The
installed level has not been corrected by this work.** Do not rerun the stage-90
control-point generator and describe additional bends as a morphology fix.

#### Why the installed result reads as a trench

`build_benmore_course_revision.py` uses one chord-parametric spline for the middle
and lower course. Both banks follow signed distance to that spline. Curvature
widens the inside shelf, but it does not produce independent bank shapes, discrete
bar bodies or a watercourse moving within a larger active gravel bed. The central
70 percent of the half-wet-width is flat, and a sequential minimum downhill bed
grade removes longitudinal pool/riffle relief. Our conservative shallow-water
bake has a fixed bed: it cannot migrate banks, transport gravel or form these
features. Successful discharge/conservation checks prove flow consistency only.

The previous integration retained Gaea headwaters/junctions, then authored a new
middle/lower spline and cross section. The visible trench is not a direct import
of Gaea's complete bed morphology. Increasing its sinuosity repeats that mistake.

The read-only native-terrain audit measures the following pre-incision grades
along the installed path, excluding clamped samples beyond X=-1250 m:

| Path station (m) | Reach-average grade | Design hypothesis to verify against terrain |
| --- | --- | --- |
| 0-300 | 14.53% | Confined rocky headwater/cascade |
| 300-600 | 8.11% | Rocky cascade with local sediment pockets |
| 600-900 | 4.78% | Step-pool/rocky run transition |
| 900-1200 | 1.89% | Riffle/run transition |
| 1200-1500 | 1.07% | Alluvial bars and pool/riffle relief |
| 1500-1734.52 | 0.86% | Wider gravel bed approaching the lake |

These are design hypotheses, not a surveyed stream classification. The slope
bands come from [Buffington et al. (2004)](https://www.fs.usda.gov/rm/pubs_other/rmrs_2004_buffington_j002.pdf),
whose Pacific Northwest thresholds require local validation. Confinement,
substrate, sediment supply and obstructions also matter. Aerial sinuosity alone
is not an acceptance metric. Large gravel-river forms must not be copied at
unchanged scale into the steep headwaters of this small authored catchment.

#### Regional evidence and the construction method

Inspected complete relevant PDF figures, including their captions and available
scale information:

- [ORC Lower Lindis flow/braiding study (2017)](https://www.orc.govt.nz/media/15692/relationships-between-flow-and-channel-braiding-in-the-lower-lindis-river-dean-olsen.pdf),
  Figure 1 (PDF page 2): one gravel corridor contains a changing number of narrow
  water threads and exposed bars. This figure has no metric scale; do not claim
  measured widths from it. Its morphology is an analogue, not a surveyed copy of
  our site or a hydrologic calibration for the authored 0.8 m3/s flow.
- [ORC Cardrona morphology (2016)](https://www.orc.govt.nz/media/4368/2015-cardrona-river-channel-morphology.pdf),
  Figure 2 (PDF page 13) has a scale bar; Figures 20-21 (PDF page 32) show irregular
  gravel cross sections with the low-flow channel occupying only part of the
  wider bed. The report describes steep bedrock upper reaches and a wider lower
  valley with single-thread/braided transitions. It is a larger river analogue.
- [ORC Kakanui/Kauru morphology (2010)](https://www.orc.govt.nz/media/3841/channel-morphology-and-sedimentation-in-the-kakanui-and-kauru-river-north-otago.pdf),
  Figure 2.5B (PDF page 22): channel migration, exposed gravel and partial braids
  vary between reaches and dates; river training/vegetation/gravel extraction are
  additional controls, so every photographed bank is not an untouched template.
- [USGS river channel bars](https://pubs.usgs.gov/pp/0422l/report.pdf) and
  [channel patterns](https://pubs.usgs.gov/publication/pp282B): bar/pool/riffle bed
  relief and bankfull discharge are part of channel form. Present low flow does
  not define the whole gravel footprint.

The next level correction is a bed-first construction with explicit components:

1. Use the pre-incision terrain and Gaea drainage network to identify each valley
   floor, confinement changes and tributary/fan entry. Retire the arbitrary
   stage-90 middle/lower controls. Fit reach envelopes within terrain and the
   protected-road clearance; do not route broad meanders across steep side slopes.
2. Author the two gravel-bed boundaries independently, with expansion,
   contraction, erosion scarps and irregular vegetated margins. Keep the outer
   soil bank distinct from the edge of today's water. Derive the active footprint
   from these boundaries, not a constant buffer around a water spline.
3. Preserve/shape discrete elongated gravel bars and short abandoned chutes. Put
   a primary low-flow groove against alternating margins; use occasional short
   split/rejoin sections only where the lower bed has space. Set local riffle
   crests and shallow scour relief. No higher/deeper-water target is required.
   Avoid periodic bends, identical islands and circular stamping.
4. Keep those forms in native deformable Landscape. At the current 1.240079 m
   spacing, a tiny branch below a few cells cannot carry a convincing collision
   shape. Resolve primary geometry at that scale; use gravel materials/embedded
   stones for finer detail. Do not disguise missing bed shape with a static native
   bed overlay or use a finer flow grid as proof of finer terrain geometry.
5. Quantize the final terrain first. Rebake depth, mean surface and currents over
   that exact floor. Clip rendered water to the resulting occupancy, including
   wet/dry margins around bars. Use the same bed for geometry, crossings, query
   and masks; do not paint a full-width ribbon on top of an unrelated bed.
6. Reconcile crossings, shore materials and existing bank placements against
   that terrain. Match lower soil, dry coarse gravel, wet aggregate and local
   finer deposits to the geomorphic features. Check the lake join separately.
7. Review bare-bed and wet overhead, oblique and ground views against regional
   references before claiming the shape is fixed. Numerical flow checks remain
   necessary but are separate from the owner's visual acceptance.

[Gaea Rivers](https://docs.gaea.app/reference/nodes/simulate/rivers) can create
connected downhill pathways and control valley width/headwaters.
[Erosion2](https://docs.gaea.app/reference/nodes/simulate/erosion2) documents
sediment transport/deposition controls, including Bed Load. They are useful for
the valley and sediment scaffold. Preserve their complete terrain/mask outputs
where usable rather than reducing everything to a line. Our paired graph already
keeps bed/surface outputs together; raw Gaea terrain still needs road/height/grade
validation. No Gaea setting is asserted to guarantee Otago bars or bank migration.
[Anastomosis](https://docs.gaea.app/reference/nodes/simulate/anastomosis) is described
as interconnected downcutting and is not proof of a sediment-deposition solution.

A fully automatic shape simulation would need coupled sediment erosion,
deposition and bank adjustment, not just our present fixed-bed water solver.
[Stochastic Geomorphological Transport (SIGGRAPH 2026)](https://erosiv.studio/publications/stochastic-geomorphological-transport)
is a relevant research direction, but it has not been installed or validated here.
The official geotransport repository contains core transport examples rather than
the complete erosion application. Do not promise a drop-in replacement.

#### Isolated geometry/flow experiment completed

`Art/tools/study_benmore_river_morphology.py --audit --study-seconds 1200` writes
only `Art/Export/BenmoreGaea/review/MorphologyResearch`. It implements independent
gravel-bank controls, three tapered bar bodies, an offset primary groove, one
secondary split/rejoin and local longitudinal bedform relief. It interprets
Lindis channel anatomy; **240 m length and all metric dimensions are study
choices**, because its source figure lacks scale. It is not a digitized survey,
the installed Benmore course, a sediment simulation or an accepted art result.

The geometry uses 1.240079 m cells and 1/64 m height quantization. Water occupancy
is solved from that floor with the existing conservative solver. At 1200 s,
outflow is 0.799975 against inflow 0.8 m3/s; 200 s depth/velocity drift is
0.00004087 m / 0.00015617 m/s. Mass residual -6.82e-13 m3, positivity correction
zero, inlet/outlet connected and zero wet artificial side-edge cells. Visible
depth median is 0.14629 m (95th percentile 0.35256 m); these are experiment values,
not retained level depths or a new deeper-water target. Cross-channel samples
show two wet threads at stations 30/70/108 m and one at 146/175/210 m.
Finite-volume face fluxes confirm actual flow in both branches: near X=30 m,
the secondary/primary carry approximately 0.0781/0.7196 m3/s; complete face
discharge is 0.80002 m3/s. The small remainder is shallow water below the
25 mm wet-display threshold. Oblique transects and grid-aligned flux sections
can intersect the joining channels differently; their thread counts are not
identical near the confluence.

`Channel_Anatomy_Study.png` shows authored bed anatomy above and solved occupancy
below; `Reach_Diagnosis.png` maps the actual terrain audit. Both are diagnostic
figures, not Unreal screenshots. `anatomy-study.npz` retains geometry and solved
fields; reports retain assumptions and provenance. Quantitative gates establish
only numerical viability of this geometry experiment.

CourseRevision height, flow, controls and pre-incision terrain hashes remain
unchanged. No level/binary assets, Gaea source graph, runtime fluid settings or
tuned vehicle/mud/snow code were edited; no Unreal instance or engine regression
suite was launched for this read-only audit/offline experiment. Actual mapping,
import, crossings, driving and performance validation remain work for the next
level correction. Runtime should continue using baked large-scale water and the
existing bounded local interaction field.


## 92. Native bed-first morphology installed (2026-10-09)

Owner authorized applying the morphology study after rejecting stage 90's
regular ribbon. Target: `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`;
assets and exports in `Gaea/Morphology` and `Art/Export/BenmoreGaea/Morphology`.
Backup: `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeMorphology`.
This is an authored regional interpretation using Gaea's drainage, not a surveyed
Otago reconstruction or a sediment/bank-migration simulation. Owner visual and
driving acceptance remain open.

- Bed: retire the stage 90 middle/lower S-bend controls; retain Gaea's valley and
  tributary topology. Gravel margins use separate controls from the low-flow
  groove. Five tapered bar bodies, two unequal short split/rejoin grooves,
  attached point bars, narrowing reaches and shallow local riffle/scour relief.
  Native 2017-square Landscape at 1.240079 m spacing,
  1/64 m height quantization. Maximum incision below pre-incision terrain
  1.90625 m; 31134 samples changed
  relative to stage 90. This is bed seating, not a deeper-water target.
- Bake: final terrain is quantized first. A **cold start**, initially dry native
  creek with only the lake wet, receives 0.36/0.22/0.22 m3/s at three sources.
  6000 simulated seconds; outflow
  0.79989274 against inflow 0.8 m3/s. Mass residual
  5.09e-11 m3, positivity correction zero. Last 200 s visible
  depth/velocity drift 6.86e-07 m /
  8.48e-05 m/s. Lake connected, zero artificial
  boundary cells over 5 cm; maximum boundary film 0.00999 m.
  Offline grid 155760 cells, 35 m valley radius and at least 19 m
  beyond the widest gravel bank. This is a bounded creek bake, not hillside runoff.
- Water depth (native river wet cells): median 0.11898 m, p95
  0.33213 m, maximum 0.45312 m. Stage 90 was 0.14935 / 0.36507 /
  0.53497 m. Sampled sections include actual flowing splits. Their interpolated
  discharge estimates are diagnostics, not conservative face flux measurements.
- Exact bed match: 0.0 m error between baked
  floor and native triangle interpolation. Saved/reloaded Landscape checksum
  `eb27dbd5a904d44f0a27e0dba032d114d465387f8c856f45892df518f79efae6`. Geometry, wetness, materials, water queries and
  crossing placement share this bed. No static native riverbed replacement.
  The existing scenery apron alone is rebuilt outside X=-1250 m.
- Materials/placements: retain sourced CC0 mineral textures; geographic bar and
  rocky-reach masks keep coarse gravel on dry deposits. Place review-owned bank
  vegetation outside the active gravel bed. Re-seat 3310 supports and relocate
  4721 review-owned bank instances; remove
  28 ordinary plants from water. Rebuild the
  bridge and approaches. Ford query depth 0.22011 m.
  Road transforms/count, original Drive map checksum and all tuned crossing
  deformation values pass preservation checks. Deform WPO remains connected.
- Runtime: existing 9216-cell / 60 m / 0.625 m local interaction field retained.
  No runtime C++/vehicle/mud/snow tuning or new map-wide live fluid simulation.
  Native water mesh 59923 triangles; outlet
  21893. These counts are not a frame-time claim.

**Visual check:** Inspected actual Unreal Ford, Reach, Lower, Lower_Bare, Bars, BarGround and FullCourse captures. The whole-course view shows Gaea-aligned narrow headwaters and tributaries, then wider lower reaches with unequal split/rejoin sections. The lower wet and bare views show an elongated exposed gravel bar separating two grooves; the ground view shows water rejoining around its tip. Remaining visible issues: the grey gravel border is still too uniform in places, shore edges show native-grid stepping from overhead, and the inherited reflective surface / circular ripple pattern still needs a water-rendering pass. These are visual observations, not a claim of finished naturalism, animation quality, driving feel or performance.

Actual Unreal images are `FullCourse_After.png`, `Lower_After.png`,
`Bars_After.png`, `Bars_Bare_After.png`, `BarGround_After.png`, plus the same
before cameras and Ford/Bed/Reach/Plan views. `pixel-report.json` and
`Gaea_Creek_Comparison.png` compare those captures at a fixed water clock.
Bars mean absolute RGB change 17.23/255;
BarGround 24.47/255.
These establish image changes, not aesthetic acceptance or animation quality.

**Validation:** Python compile, conservative solver gates, exact-floor check,
Unreal import/save/reload, native collision supports, outlet collision,
water coverage/query agreement, WPO and preservation checks passed.
`bash Art/suite.sh terrain` ran once (296 s): **FAIL**, documented step 11 rut-exit
gate: held 6 m in 5.8 s vs down-ruts 5.6 s; "slower than down the ruts 0".
No tuned physics changed or attempted fix for that standing failure. Evidence
in `terrain-regression.json` / `Saved/Logs/terrain_test.log`. No extra module
tests/build: no C++ modules changed. No Benmore driven acceptance or FPS profile.

**Implementation:** `Art/tools/build_benmore_morphology.py`,
`check_benmore_morphology.py`; `--morphology` in the existing packer, Blender
exporter and sampler; `-Morphology` in `Art/benmore_gaea_creek.ps1` / installer.
Fresh build: generator `--prepare --cold-start --seconds 6000`, checker, packer,
Blender exporter, installer, then sampler. A failed settle must resume and pass
before packing. After successful installation use `-VerifyOnly`, not a second
normal install that would re-seat placements again.

**Lessons:** numerical convergence did not establish natural shape. Early
analytic/warm starts and weak junction/turn transitions created off-channel
puddles and films. Correct endpoint extents, terrain seating and final cold-start
validation replaced those attempts; rejected reports are retained. Rendered
water is clipped from solved occupancy, never a bank-width ribbon. Existing
ambient water shading/animation and final owner look/drive review remain open.


## 93. Benmore shoreline and sediment refinement (2026-10-09)

Owner said stage 92 was looking better and authorized continuing. Preserve that
accepted native morphology; this stage changes shoreline rendering and material
transitions in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`.
Owned outputs/assets: `Art/Export/BenmoreGaea/ShoreRefinement`, `Gaea/ShoreRefinement`.
Backup: `Gaea/L_Benmore_BeforeShoreRefinement`.

- A 0.625 m signed coverage atlas and matching clipped render meshes reconstruct
  the existing hydraulic occupancy against the native triangle floor. The
  smoothed coverage is bounded to preserve narrow channels. At the validation
  sample spacing the offline mask removes 6.23% of old coverage,
  maximum retreat 0.884 m; added coverage is zero.
  It does not deepen the river or alter the native heights. Surface vertex means
  still use the accepted wet-weighted baked height, with no height offset.
- The local surface uses the same shore atlas, with a bounded visual rim to avoid
  reproducing its 0.625 m occupancy-cell edges. Interior live wet/dry clipping,
  wakes and field WPO remain. This is render reconstruction, not higher-resolution
  physical wetness: vehicle depth/current queries and the serialized domain asset
  are unchanged. The rim is not a new shoreline flooding/erosion simulation.
- Sediment data separates low wet gravel, dry bar cores and higher soil margins
  using height above water, current speed and the existing bar/rock masks. The
  uniform 78% grey mix/gain is replaced with a 42–76% mineral-neutral tint,
  lighter clean gravel and stronger wet darkening. Existing sourced CC0 mineral
  albedo/normal/roughness remain;
  no generated art textures. Ecology path/vegetation channels remain identical.
- Native Landscape R16 SHA after save/reload:
  `eb27dbd5a904d44f0a27e0dba032d114d465387f8c856f45892df518f79efae6`.
  All authored instance transforms/counts, road transforms, tracked deformation
  settings, water-domain asset bytes, fixed-point queries, local solver settings
  and original Drive map SHA compare equal before/after. Deformation WPO stays
  connected. No C++ or tuned physics edits; no new native static bed overlay.
- Runtime simulation remains 9216 cells / 60 m / 0.625 m. Static native surface is
  68183 triangles (stage 92: 59923); outlet
  21893 (unchanged). This visual pass is not a measured
  performance improvement. No FPS or Benmore driven acceptance claim.

**Actual visual inspection:** Inspected the final actual Unreal Ford, Bars, BarGround and FullCourse captures against the pre-pass views, plus the first-iteration Lower view. The large cell-shaped steps along the near water edge are reduced; the grey border is less continuous, the dry bar is lighter than the damp shore, and the higher margins return toward the surrounding warm soil. Both lower branches and their rejoin remain visible, with the accepted whole-course route retained. Some angular shoreline segments remain at distant bends/bar tips. Broad sky reflections and the inherited circular rain-ripple normal still make parts of the water read too much like a quiet pond. Sourced mineral grain remains visible close up but is not a finished large-stone bed treatment. Sky/cloud and vegetation wind animation were not frozen, so changes to lighting/leaf silhouettes in the paired captures are not evidence of asset edits. Still renders do not establish animation, vehicle interaction or FPS quality.

**Validation:** source hashes and reconstruction bounds, Python compilation,
Unreal material compilation/import/save/reload, native/apron collision support,
unchanged native R16, unchanged placement/query/domain/physics checks passed.
Fixed-camera Before/After images use the same water clock. Pixel differences:
Bars 5.64/255; BarGround
12.27/255. These quantify changes,
not artistic acceptance; sky/cloud animation was not frozen and can affect pixel
comparisons away from the river. `bash Art/suite.sh terrain` ran once (268 s),
**FAIL** at the documented step 11 held rut-exit gate (5.7 s vs 5.5 s down-ruts;
"slower than down the ruts 0"). The run preceded importing this visual-only pass.
No physics adjustment or repeated run to chase that standing failure.

**Reproduction:** `Art/tools/prepare_benmore_shore.py`, Blender background
`Art/Blender/export_benmore_shore.py`, `Art/benmore_shore.ps1`, then
`Art/tools/sample_benmore_shore.py`. The installer reuses guarded library helpers
from `install_benmore_gaea_creek.py`, whose direct-run entry point is now guarded.
After installation, use `-ReviewOnly` for a material/capture retry. Never rerun the
stage 92 normal terrain installer on this revision. Evidence: prepare/install/
pixel/terrain-regression reports, nine paired engine renders, visual-review.txt.

**Remaining:** ambient flow-normal choice and specular/riffle response, visually
reviewed moving-water sequences, Benmore driving and actual frame-time profiling.
Current owner acknowledgement applies to stage 92; this pass awaits their review.


### 2026-10-09 — river wave geometry installed (stage 94)

`docs/VEHICLE_BUILD_SYSTEM.md` stage 94 now records installed current-aligned
height/slope/foam waves, real shallow river relief and a finer outlet render
mesh. Build, GPU readback, preservation, save/reload, fixed-step impulse and
three CPU water regressions passed. Terrain, tuned physics and placements are
unchanged. Actual motion and shallow-angle captures are in
`Art/Export/BenmoreGaea/FlowWaves/`. Owner visual acceptance, driven wakes and
performance measurement remain open. The coarse lake still has normal-only
ambient waves; geometric lake relief needs a bounded render grid. No FPS claim.

### 2026-10-09 — vehicle spray and wake visibility (stage 95)

Implemented dedicated water spray cards (short broken fans, droplets and sparse
mist), relative-current wheel/bow emission, stronger local aeration and extra
surface relief. The follow-up adds a curved hull pressure ridge and widening wake
arms in the existing local detail texture. No new simulation grid, no terrain or
handling retuning; water particles stay capped at 120. Rendering controls and
reproduction are in `docs/VEHICLE_BUILD_SYSTEM.md` section 95. Build and four CPU
water tests passed. Installation/reload preserves authored instances, roads,
domain data, deformation profiles and physical queries. Final capture/inspection
results are recorded in `Art/Export/BenmoreGaea/WaterInteraction`.

Owner visual/drive acceptance and performance remain open. The reconstructed
crest is a visual model, not resolved fluid breakup. The dry-ground dust circles
and the coarse lake's normal-only ambient waves remain separate limitations.

Stage 95 final checks: spray/audio PASS; terrain retains the documented held-rut-exit
failure (5.3 s held exit versus 5.8 s down-ruts). Its water/buoyancy/current and winch
gates pass. A GPU crash interrupted one capture under memory pressure; the shorter
960 x 600 final-material retry passed. Final preview: WaterInteraction/WakeFinish/AlongRiver.gif.
Foam is more conspicuous but still broad in places. Owner acceptance and performance
remain open; full evidence is in WaterInteraction/verification-summary.json and visual-review.txt.
