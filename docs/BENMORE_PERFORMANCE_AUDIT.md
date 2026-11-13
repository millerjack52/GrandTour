# Benmore performance audit and staged plan

Started 2026-10-09, America/Edmonton. This document retains the initial audit
and subsequent dated experiments; earlier pauses and proposed settings are
historical, not the current authorization or installed configuration.

Current instruction (2026-10-10): the owner has left the computer available and
requests at least 80 FPS. **Sustained 80 FPS is not yet verified.** The latest
completed driving capture reached a Ford median of 11.7703 ms but p99 of
15.9671 ms, missing the 12.5 ms acceptance threshold. Native-resolution play
also remains below target. Stationary comparisons at reduced internal scale
are diagnostic and do not certify this objective. Continue protecting the
single-Unreal/build slot and unrelated shared-project work.

Target: UE 5.8.0, `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`.
The owner accepts the stage-95 bow waves, trailing wake and spray. That is the
visual baseline. Older reports saying owner acceptance is pending are historical;
they do not override this acceptance. Finer foam is subsequent work.

## Findings and evidence limits

No engine launch, build, benchmark, runtime setting change, asset save or source
optimization was performed for the initial audit. The project is extensively dirty,
including untracked water sources/assets and unrelated active work. HEAD alone
does not identify the installed baseline. No applicable AGENTS.md was found in
the project or at C:\AGENTS.md.

Machine inspection found a Ryzen 7 8845HS (8 cores/16 threads), approximately
31.3 GiB usable RAM, and RTX 4050 Laptop GPU with 6141 MiB VRAM. Installed engine
Build.version reports 5.8.0 / changelist 55116800. During initial inspection,
NVIDIA reported 2169 MiB used, 100% utilization and 88 C; Ace7Game.exe was running.
An UnrealEditor-Cmd terrain test was active with NullRHI. NullRHI still occupies
the shared Unreal/build slot and cannot provide GPU timings. These are snapshots,
not thermal-limit diagnoses or a measurement of Grand Tour's current GPU usage.
The owner chose to finish this audit and profile later. No applications were closed.

The retained crash log reports DXGI_ERROR_DEVICE_RESET, local usage 4605.57 MB
against a local budget of 1822.02 MB (about 2.53 times budget). It also contains
asset-compilation memory-limit warnings. Memory pressure is established; the
sole cause of device removal is not. The successful shorter 960x600 retry does
not establish stability at the intended play resolution. NVIDIA device-wide
free memory and the process's changing WDDM/DXGI local budget are different
quantities. Win32_VideoController's approximately 4 GB AdapterRAM result is not
the card's capacity; use the NVIDIA-reported 6 GB and runtime budget telemetry.

Evidence read: VEHICLE_BUILD_SYSTEM sections 94-95; BENMORE_RIVER_LIFE and
WATER_PLAN guidance/history; WaterInteraction visual-review.txt,
verification-summary.json, install-report.json and capture-gpu-crash.log;
the named C++/material implementation; earlier RiverScale audit/profile artifacts.
WakeFinish/AlongRiver_07.png was inspected: the accepted interaction remains the
reference, including broad pale foam patches that the later detail pass can refine.
Sampled, paused GIF/image sequences have no runtime-FPS evidential value.

### Whole-scene leads, not a current bottleneck ranking

| Area | Evidence | What must be measured now |
| --- | --- | --- |
| Vegetation and geometry | Historical content-audit.json records 5,557 composition shrubs with 2,100 m end cull and 17,278 composition tussocks with 850 m end cull. Shrubs cast shadows; these tussocks already do not. Both groups already excluded ray tracing in that audit. Tussocks have three LODs; willow LOD0 counts range roughly 73k-232k triangles, with later LOD triangle fields unavailable. | Fresh runtime instance visibility, selected LODs/Nanite state, masked overdraw, draw submission, bounds, grass streaming and motion/WPO costs. Counts are placed instances, not simultaneous draws. Do not repeat exclusions already installed. |
| Lumen | Config requests Lumen GI/reflections, distance fields and ray-tracing support. Old GPU reports place LumenSceneUpdate ahead of named water passes. | Actual hardware/software tracing mode, scene/cache updates, instance overlap, distance-field updates, GI and reflections separately. r.RayTracing=True does not prove Lumen HWRT is active. |
| Shadows | Virtual shadow maps enabled; vegetation and displaced geometry are investigation candidates. | Shadow depths/projection, page allocation/cache invalidation and WPO contribution, including moving camera and wind. |
| Terrain/materials | Bank-texture branch optimization and small-gravel culling were already installed historically. Current scene adds shore/wave/interaction material generations. Grass scales in Config are already density 0.5 and cull distance 0.6. | Actual saved material parents, base/prepass costs, Landscape LOD, texture samples, WPO, road/gravel cost and runtime CVar provenance. Do not claim old changes as new savings. |
| Memory/streaming | Crash budget overrun; extensive authored scene plus ray tracing, VSM, Lumen and transient targets. No current per-resource inventory. | Textures, meshes/Nanite, render targets, shadow pools, Lumen/distance fields, RT acceleration structures, residency evictions and editor overhead. Disk asset size is not VRAM residency. |
| Water rendering | Native river 68,183 and outlet 87,572 triangles documented by stage 94; one shared ambient precombine. Water is SingleLayerWater; spray is separate lit translucency. | Water depth/main passes, WPO/normal samples, ambient draw/mip generation, overlap and screen coverage. Named water passes omit shared work. |
| Vehicle effects | Water pool capped at 120; lit per-pixel spray cards with procedural masks and depth fade. PushTransforms batches every pool slot, including inactive slots, for every effect kind each update. | Spray/mud/dust/snow/steam CPU integration and submission, allocations, traces, translucency overdraw and lighting. A particle cap does not cap pixel cost. |

Historical timing artifacts need provenance repair before quoting them as a series.
`BeforeDetail_domain-runtime-report.json` matches the older documentation's ford
47.50 ms frame median and lake 32.15 ms. The current file named
`domain-runtime-report.json` instead contains ford 35.06 ms, lake 25.44 ms and
OpenLake 28.64 ms at **1274x682**, including later detail experiments. The separate
GPU-scope summary records LumenSceneUpdate 15.94/15.10 ms at ford/lake and appears
to describe the earlier capture. Do not combine these into one run or subtract
them to claim a speedup. Their short stationary windows predate accepted stages
94-95. Near-zero RenderThreadTime in the old CSVs is a missing/usefully invalid
signal, not evidence that rendering submission costs nothing.

### Current water implementation

- GTWaterDomainSheet.cpp retains one 96x96 grid, 60 m span, 62.5 cm cells. It
  recentres on a 10 m lattice, reconstructs reference arrays and copies overlap.
  Recentring also forces binding/uploads and ambient update. Profile this as a
  potential hitch separately from steady stepping. The dry-cell early return
  happens after window movement and ambient work.
- FieldTexture is RGBA16F (72 KiB); RiverDetailTexture is BGRA8 (36 KiB).
  Default combined upload payload is about 3.16 MiB/s at 30 Hz, excluding
  forced moves and API/allocator overhead. Both allocate upload buffers/regions;
  asynchronous ownership must be preserved if staging buffers are later reused.
- GTWaterAmbient.cpp creates one 256x256 RGBA16F target: 0.5 MiB base level,
  approximately 0.67 MiB with the full mip chain, excluding RHI overhead. It
  clears/draws at 30 Hz and updates material bindings/clock. This is small
  storage, but draw submission, wave math and mip generation still need timing.
- Cosmetic wake height uses detail B, quarter-centimetre encoding; at most four
  sources expire within 1.2 seconds. Bounded near-car raster loops include
  exponential ridge evaluation. Existing GTWater DomainTick covers CPU work and
  upload submission, not GPU completion. DetailMs covers only transported detail.
- The pixel material adds four neighbouring detail samples for wake normals.
  Foam uses two procedural noise scales at 3.2 and 7.36 units per metre: nominal
  lattice spacing about 31 cm and 14 cm, not guaranteed visible feature diameters.
  The coarse concentration field supplies coverage; fine appearance already has
  an independent rendering path. No larger simulation is needed just to test
  finer foam.
- Turning InteractionSpray off stops emission; particles take time to die.
  InteractionTrails off leaves transported history. Domain.Detail off is not
  a total-water off switch: physical height, wake packing/raster work and uploads
  can remain. Ambient off is a rendering ablation, not a production proposal.

## Stage 0: freeze the baseline and repair measurement coverage

Before the later profiling window, agree exclusive ownership of the project
engine/build slot with the owner and Claude. A process check alone is not a lock;
use a shared acquisition convention honored by both workers, then recheck processes
immediately before launch/build. Never launch a second Unreal editor, game or
commandlet, including NullRHI tests. Never build while Unreal is running. Do not
send messages to other chats or close applications without user authorization.

Create a fresh, timestamped baseline bundle after shared edits settle: HEAD, full
dirty diff/status, hashes and copies of affected untracked files, map and dependent
materials/meshes/textures, build/binary identity, driver, hardware, runtime settings,
and accepted reference captures. Audit hashes are an observation, not a restorable
backup. The old BeforeWaterInteraction map predates the accepted appearance and
is not this optimization rollback point. If anything changes during capture,
invalidate the affected run and re-baseline rather than overwriting another agent.

Repair or replace the old profiling runner before use:

1. Its narrow game allowlist misses Ace7Game. Record the full GPU-client/process
   inventory and utilization, detect unexpected workload throughout capture, and
   coordinate a quiet window. Do not infer quiet merely from known process names.
2. It selects water by M_RL/M_RS material names; current water uses
   WaterInteraction/M_GC_DomainRiver and DomainLake. Discover actual domain surfaces
   and the runtime local mesh; verify the count and actual hide/restore result.
   Visibility ablation must leave water physics running.
3. InstancedFoliage/InstancedGrass show flags may not isolate custom ISM/HISM
   composition actors. Enumerate actual actor/components and verify membership.
4. It has only Ford and Long_Vista, no pawn and 10-second CSV windows. Add lake,
   dense vegetation and real vehicle routes. Retain GTWater and vehicle counters:
   the existing analyser explicitly keeps GTMud but drops GTWater. Add p99,
   frame-threshold counts and run metadata; retain all raw CSV/trace files.
5. Assert actual viewport and internal resolution. The earlier requested
   1440x900 became 1274x682. Validate Game/Render/RHI/GPU tracks; reject missing,
   near-zero invalid tracks. Check shader/PSO completion and streaming convergence,
   not just elapsed sleep or ShaderCompileWorker CPU activity.

Stage 0 changes only instrumentation. Demonstrate instrumentation overhead with
matched trace-on/off samples; keep heavy allocation traces and debug overlays
outside primary timing windows. Revert instrumentation separately if necessary.

## Stage 1: representative baseline protocol

Provisional reference configuration: this RTX 4050 laptop, plugged in with fixed
power mode, DX12/SM6, **actual 1440x900 at 100% internal resolution**, current visual
settings, fixed vehicle/loadout and unchanged handling. Record AA/TSR mode,
scalability, screen percentage, dynamic resolution, frame cap, VSync, weather,
time/exposure, camera/FOV, driver and engine/build identity. Disable VSync/cap and
dynamic resolution only in the ephemeral benchmark configuration and record prior
values. Do not lower the visual preset or screen percentage silently.

Use one consistent Development standalone game process for primary timing if the
current runnable build supports it; otherwise use one PIE editor process and label
results editor-inclusive. Do not pool PIE and standalone measurements. Later verify
the winning configuration in the intended playable build. Keep audio/gameplay
representative and identical across comparisons.

| Case | Reproducible setup to record | Coverage |
| --- | --- | --- |
| Vegetation drive | Ground/chase camera route through dense approved tussock/willow planting; save exact start pose, waypoints, input trace and speed envelope after surveying the current map | Streaming, masks, wind/WPO, shadows, collision/game-thread work and submission |
| Long vista | Resolve Benmore_RL_Camera_Long_Vista, export transform/FOV; hold then repeat a fixed smooth pan and road approach | Far vegetation, terrain, Lumen/RT, shadows, sky/clouds and streaming |
| River | Resolve current ford/crossing data used by check_benmore_water_interaction.py; repeat crawl, normal crossing, reverse and along-river travel; chase and driver view | Entry/exit, accepted bow/wake/spray, water update spikes, wet/dry transitions |
| Lake | Near-shore camera plus open-lake fully wet window; fixed shoreline drive and controlled window-boundary traversals, recorded separately from normal driving | Large water coverage/reflections, 9,216 wet cells, recenter hitches, memory residency |

Exact route transforms remain to be surveyed in the reserved window; do not invent
them from old screenshots. Warm each route once, then wait until shaders/streaming
settle and clocks/temperature are stable. Log at least 60 seconds of preflight
telemetry; reserve cooling time after the other game. Sustained GPU saturation by
Grand Tour during its own run is expected, unlike saturation by another game.

Capture three independent 60-second continuous runs per main case after warmup.
For short crossing maneuvers, capture at least ten repetitions; keep reset/teleport
intervals separately marked, retaining them in raw evidence. Never pause, capture
high-resolution screenshots, force a fixed timestep or dump memory within a primary
timing interval. Record actual trajectory/speed and reject mismatched routes by a
declared tolerance, not because their timings look bad. Use wall-clock frame data.
Keep a separate cold traversal and a 10-minute repeated-route residency/stability run.

Collect frame, Game, Render and RHI thread median/p95/p99; GPU critical-path frame
time and pass breakdown; frames over 33.33/50/100 ms; stalls with trace bookmarks;
draw/triangle/visible-instance counts; water solver/detail/upload/recenter and
spray counters; solver clamp/deficit counts. Use CSV plus Timing Insights CPU/GPU,
frame, task and bookmark tracks. Add narrow scopes only where missing. Inspect
waits and async overlap: do not sum all threads or nested/async GPU scopes.

For memory, sample process local usage **and DXGI budget** over time, NVIDIA
device totals, process private bytes/working set and system commit. Capture
streaming wanted/resident/non-streaming/safety-pool figures, virtual texture pools,
RHI/render-resource inventory and transient allocations. Use stat streaming,
stat RHI and memreport -full/resource inspection outside timing windows. Take
separate startup-to-route Memory Insights traces with matching symbols and
`-trace=default,memory,metadata,assetmetadata`; CPU allocation traces are not a
replacement for GPU residency measurement. Correlate evictions/budget drops and
stream-in work with hitches. Do not increase texture pool size to hide a warning
when total residency already exceeds the process budget.

Baseline is accepted as repeatable when all tracks and locations exist, no external
load or compile work intrudes, and three run medians differ by <=5% and p95s by
<=10%. Otherwise diagnose variance before judging optimizations. A repeatable slow
baseline is still valid. A crash, resolution mismatch or pressure from another
application is not. Preserve invalid runs with an explicit reason.

## Proposed targets and stage gates

These are proposed engineering targets, not achieved results or FPS promises.

| Gate | Proposed criterion at the reference configuration |
| --- | --- |
| Stability and memory first | No device removal, residency-budget overrun, sustained streaming-pool over-budget state or recurring eviction thrash in all cases and the 10-minute loop. Keep local usage <=85% of current budget with at least 512 MiB headroom; both conditions apply. After warmup, investigate retained CPU/GPU growth >5% between identical loop endpoints. |
| First playable milestone | Per-case frame p95 <=33.33 ms, p99 <=50 ms; fewer than 0.1% of warm frames >100 ms. This is a 30-fps floor milestone, not the final objective. |
| Intermediate 60-fps milestone | Per-case frame p95 <=16.67 ms, p99 <=25 ms; GPU p95 <=15 ms and Game/Render/RHI active-work p95 <=12 ms each. Thread budgets overlap and are not additive. |
| Owner's current 120-fps objective | Frame p99 <=1000/120 ms (8.333 ms) in each representative driving case at the recorded reference viewport and 100% screen percentage, repeated three times, then confirmed through the 10-minute route. Memory/stability and accepted-water appearance gates still apply. Stationary measurements alone cannot certify this target. Feasibility remains unverified. |
| Promote a performance stage | At least max(0.5 ms, 5%) improvement in the targeted frame/GPU/CPU bottleneck median or p95, beyond measured baseline variance; or >=256 MiB reproducible residency saving for a memory stage. No other representative case worsens by >max(0.5 ms, 3%). Report smaller scoped wins as such, not FPS gains. |
| Physical/visual preservation | Same domain/terrain/road/deformation data and physical queries; no solver deficits/clamps introduced; grid/span/rates and 120-particle cap retained. Compare matched images and continuous motion for bow prominence, widening wake, spray, shallow banks, distant silhouettes and reflections. Owner acceptance takes precedence over pixel-difference scores. |

If a change is visually good but its speed effect is below noise, do not call it a
performance win. If a memory change alters streaming convergence, rewarm before
comparison. Do not exclude unexplained hitches from percentiles.

## Ranked experiments and implementation stages

Ranking is provisional expected value based on the audit. Current traces may
reorder it. For each candidate run baseline/candidate/candidate/baseline (ABBA),
with settled caches and identical route; repeat three paired blocks for promotion.
Feature-off experiments estimate contribution and often alter shared work; their
deltas are not guaranteed production savings or additive across features.

| Order | Small candidate stage, after identifying its cost | Likely benefit | Visual impact / effort | Rollback |
| --- | --- | --- | --- | --- |
| 1 | Fix demonstrated memory/residency offenders: unintended loaded assets, oversized distant texture mips, wrong streaming flags, duplicate/transient resources or excessive measured pools. Change one resource family at a time. | Potentially very high stability/hitch benefit; average FPS unknown | Low if waste; medium if texture LODs change / medium | Restore exact asset/config copies and reload the process |
| 2 | Vegetation/geometry participation: validate LODs, reduce only visually negligible distant detail, constrain distant wind/WPO and measured distance-field/RT participation. Preserve planting transforms and near-road density. Compare small named groups. | High potential for base/prepass, scene updates and submission | Low-medium; far silhouette/pop risk / medium | Restore cloned mesh/material/grass/component settings |
| 3 | Lumen: first remove measured unnecessary scene/cache invalidation or negligible contributors; then separately test a local quality/update budget or HWRT/SWRT comparison if warranted. Include clouds/sky update work if traces rank it highly. | High potential based on historical leads | Medium-high for light/reflection changes / medium | Restore runtime values; restart when required; retain original assets |
| 4 | VSM: reduce proven distant small-detail shadow work or WPO-driven invalidation, with near-car/tree shadows preserved. Do not blanket-disable shadows. | Medium-high if shadow/cache costs dominate | Low-medium for selective cuts / medium | Restore each component shadow/WPO setting and original CVars |
| 5 | Terrain, roads and water pixel/mesh work: measure actual branches and derivatives; skip unused detail, use distance-appropriate sampling/LOD and avoid overlap while preserving deformation WPO and shoreline continuity. Old bank/gravel cuts may already be present. | Medium; potentially high at large screen coverage | Low-medium / medium-high | Duplicate material/mesh variants; restore bindings from baseline |
| 6 | Water CPU/upload/ambient: only after scoped evidence, reduce redundant binding/allocation and recenter work; keep async upload lifetime safe and the shared target/rates intact first. Separately test lower cosmetic update rates only if justified by visible motion comparisons. | Likely small steady-state; possible hitch benefit | Low for redundant work; medium for rate changes / medium | Revert only this source patch and rebuild with Unreal closed |
| 7 | Vehicle effects: skip unchanged empty-pool submissions, batch custom data if measured useful, then test economical spray shader masking/lighting. Keep emission appearance, lifetime distribution and pool cap. | Small CPU potential; GPU depends on overdraw | Low for idle path, medium for shader changes / medium | Restore scoped source/material patch |
| 8 | Fine foam appearance, once the agreed performance milestone and memory gates pass | Visual benefit; strictly budgeted | Intended visible refinement / low-medium | Restore accepted foam material, independently of performance stages |

Diagnostic ablations must cover vegetation, VSM, Lumen GI/reflections, terrain
detail, water visibility, ambient precombine and vehicle effects separately.
Add 100% versus lower internal-resolution runs only as a labelled fill-rate
diagnostic; do not count them as same-quality gains. SingleLayerWater and lit
spray translucency need separate captures. Wait for particles/trails and lighting
caches to settle, or start each comparison from the same seeded state.

After each promoted stage, archive a new known-good bundle and rerun all four
representative cases. Apply one conceptual change at a time, with reversible
runtime/asset variants before shared source edits. Do not restore the whole dirty
repository, whole historical map, or unrelated files. Compare hashes before any
rollback; if another worker touched a file, merge the owned change instead.

When C++ water changes justify it, build once with Unreal closed, run the four
water CPU regressions and the applicable terrain/module tests sequentially. Spray
changes additionally require spray/audio regression. Material/runner-only changes
need compile/save/reload, protected-state checks and image/motion comparison rather
than unrelated physics reruns. The known rut-exit comparison remains reported as
a failure; water/buoyancy/current/winch gates must not regress. Never retune vehicle
handling, traction or buoyancy to satisfy the tests. Coordinate the existing
end-of-session full-suite policy with the other worker; do not duplicate it.

## Fine foam stage

Retain the transported 96x96 concentration as coverage and the accepted signed-B
height reconstruction. First test finer irregular breakup and a sharper,
derivative-filtered threshold in the existing pixel branch. Aim for recognizable
roughly 5-15 cm near-camera flecks, with occasional broader patches and stable
distance filtering; dimensions are a visual proposal, not simulation cell sizes.
Compare reusing an existing suitable detail texture against the present procedural
noise before adding samples/octaves or a new texture. Any new art texture should
follow the project's sourced-texture rules. Do not increase grid size, coverage,
ambient RT resolution or particle count for this stage.

Preserve foam placement/transport, bow/wake relief and spray; do not stretch the
mask by multiplying spatially varying velocity by absolute time (the rejected
stripe failure). Verify stationary close-ups, driver/chase motion, reverse, shallow
entry/exit and distance transitions at the reference resolution. Require no
obvious tiling, contour stripes, shimmer, flattened wake or revived shiny disks.
Budget incremental GPU p95 <=0.2 ms in the worst water view, no measurable CPU
regression beyond noise, and unchanged simulation/resource dimensions. If the
measurement cannot resolve 0.2 ms, report it as unresolved and extend paired
sampling rather than declare the detail free. Keep the accepted material as the
instant rollback variant; request visual judgment on the actual paired result.

## Deliverables for the next profiling window

One timestamped folder per run with manifest, process/settings/temperature and
budget telemetry, exact cameras/routes, raw CSV and .utrace, separate memory
inventory, images captured outside timing, validity reasons and per-case summary.
The comparison table must include median/p95/p99 and residency peaks for both
baseline and candidate, the changed settings/files, measured variance, visual
review and explicit promote/reject decision. No current baseline cells are filled
with old timings.

Official references checked against current Epic UE 5.8 documentation:

- [Unreal Insights](https://dev.epicgames.com/documentation/unreal-engine/unreal-insights-in-unreal-engine): CPU/GPU trace analysis.
- [Memory Insights](https://dev.epicgames.com/documentation/unreal-engine/memory-insights-in-unreal-engine): allocation tracing from process startup and asset metadata.
- [Texture streaming metrics](https://dev.epicgames.com/documentation/unreal-engine/texture-streaming-metrics-in-unreal-engine): streaming pools and update work.
- [Lumen performance guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-performance-guide-for-unreal-engine): trace mode, scene participation, update and reflection tradeoffs.
- [Virtual shadow maps](https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine): caching, invalidation and shadow profiling.

## Documentation review requested by the owner

Reviewed 2026-10-09. These are documented mechanisms and proposed experiments,
not newly measured Grand Tour bottlenecks. Profiling remains deferred. No runtime
or asset changes were made during this review. The original audit-snapshot.json
intentionally retains the hash of the earlier report version.

### Reading order and application to Benmore

| Read | Documented point | Application / next evidence |
| --- | --- | --- |
| [Timing Insights](https://dev.epicgames.com/documentation/en-us/unreal-engine/timing-insights-in-unreal-engine) | Frame, CPU/GPU and thread timelines support multi-frame investigation. | Use these timelines to distinguish active work, waits and hitches; retain CSV as supplementary numerical export, not the only source of attribution. |
| [Render Resource Viewer](https://dev.epicgames.com/documentation/unreal-engine/render-resource-viewer-in-unreal-engine) | Shows a snapshot of GPU resource allocations, including sizes and owners. | Sort allocations at vegetation, vista, ford and lake; inspect the largest owners. Refresh between locations. It is not a live WDDM residency/budget trace, so pair it with the budget telemetry already planned. |
| [Texture Streaming Metrics](https://dev.epicgames.com/documentation/unreal-engine/texture-streaming-metrics-in-unreal-engine) | Streaming demand, pool accounting and update work have distinct metrics. | Distinguish a texture streaming-pool shortage from total local-budget pressure. Record wanted versus resident mips and changing non-streaming allocations before choosing texture reductions or pool adjustments. |
| [Lumen Performance Guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-performance-guide-for-unreal-engine) | Scene participation, overlapping instances and tracing mode affect cost; moving static distance-field contributors can invalidate cached work. | Establish actual tracing mode first. Investigate what drives LumenSceneUpdate, including incorrect mobility/render-state churn, then isolate scene updates, GI and reflections. Small vegetation may already be excluded: verify runtime membership. |
| [Virtual Shadow Maps: caching and deformation](https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine) | Animated/deformed casters invalidate cached pages; enlarged bounds can multiply affected pages. | Inspect Cached Page and ShadowCasters visualizations with a stationary camera and during driving. Identify expensive actors, bounds and distant animation before changing shadow resolution. |
| [Working with Nanite-enabled content](https://dev.epicgames.com/documentation/unreal-engine/working-with-naniteenabled-content) | Aggregate foliage, overdraw and masked cards need special consideration; simply enabling Nanite does not ensure a speedup. | Classify current tussock, shrub and willow assets by opaque/masked geometry, LOD/Nanite state, overdraw and materials. Compare one representative cloned asset at identical placement and coverage. |
| [Nanite Foliage, UE 5.8](https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-foliage) | The experimental pipeline combines assemblies, voxels and skinning; each addresses different geometry/storage/animation costs. | A global voxel CVar does not establish that existing assets use this pipeline. Inspect asset configuration before proposing conversion. Preserve the approved planting and silhouette in any isolated trial. |

### Refinements to the staged plan

1. **Add a foliage cost inventory before culling changes.** For each dominant
   asset family record material blend mode, selected representation/LOD, material
   count, wind method, bounds, WPO disable distance, shadow/RT/distance-field
   participation and measured pass contribution. This may reveal unnecessary
   work that can be removed while retaining planting density.
2. **Test distant animation separately from vegetation visibility.** If shadow
   invalidation is significant, compare a bounded animation-distance change before
   reducing distant vegetation. Do not mark animated objects Static/Rigid merely
   to suppress invalidation: an apparently faster result can have stale shadows.
3. **Treat Nanite Foliage conversion as an optional asset experiment.** Start with
   one cloned willow or tussock family only if current profiling warrants it.
   The 5.8 documentation notes voxelization uses vertex-color alpha for shading
   data; audit existing alpha usage before conversion. Include build/storage,
   resident memory, motion and distant silhouette in its acceptance checks.
4. **Separate content fixes from quality presets.** Epic's Lumen budgets are
   platform/scalability targets, not guaranteed timings on this laptop. A preset
   change can alter reflection method and GI, so record the actual technique as
   well as the quality number. Try measured scene-participation/cache fixes first.
5. **Keep the tool choice appropriate to this GPU.** AMD's
   [Unreal performance guide](https://gpuopen.com/learn/unreal-engine-performance-guide/)
   supplies useful repeatability, build-overhead and fixed-camera advice. Its
   Radeon-specific profiling workflow is not the workflow for the RTX 4050.
   Start with Unreal Insights. Use NVIDIA
   [Nsight Graphics GPU Trace](https://docs.nvidia.com/nsight-graphics/UserGuide/gpu-trace-overview.html)
   only if a dominant GPU pass needs deeper hardware/stall analysis. No external
   profiler installation or driver change has been performed.

The documentation strengthens the case for investigating vegetation, Lumen and
shadow interactions before changing the accepted water work. It does not yet
establish which one dominates this scene. There is no documentation-based reason
to increase the water grid or particle pool for the planned fine-foam pass.

## Instrumentation repair: offline implementation

2026-10-09. Updated Art/profile_benmore_rendering.ps1 and its Unreal Python runner;
originals are preserved in Art/Export/BenmoreGaea/PerformanceHarnessBackup_2026-10-09.
Added Art/tools/benmore_profile_metrics.py and seven offline regression checks.

- Launcher now recognizes Ace Combat 7 and Steam-library executables, checks
  Unreal/build occupancy, samples a quiet GPU before launch, and creates unique
  run folders with manifests, GPU telemetry, logs and a timing trace. It does
  not close existing applications. Its mutex only serializes this runner; other
  workers still need to honor the reserved window.
- Water isolation uses the domain's actual surface references plus its local
  mesh instead of obsolete material names. Authored vegetation is enumerated by
  mesh family instead of relying on the foliage show flag. Added the existing
  Lake_Mouth camera, recorded camera transforms, and 60-second capture windows.
- CSV analysis retains all numeric counters, including water and local GPU
  budget/usage, and adds p99, hitch counts and frame-paired memory headroom.
  It handles UE's changing trailing counter columns and flags missing/near-zero
  CPU timings instead of reporting them as free work.
- Seven offline tests and Python/PowerShell syntax checks passed. Reanalysis of
  the historical 246-frame ford CSV reproduced its 35.06165 ms median and found
  only 315.336 MB minimum local headroom (93.61% peak budget usage). This is old
  evidence, not a new performance baseline or speedup.
- The process guard was exercised with -CheckOnly and correctly refused the
  occupied slot. At that check two existing UnrealEditor processes were present;
  neither was launched by this work. No build or Unreal capture was started.

Remaining: live validation of the revised Unreal API paths, shader/streaming
convergence and unknown external workload detection; repeatable real-car routes;
the full CPU/GPU/memory baseline; measured optimization stages. The repaired
runner remains explicitly a stationary renderer-isolation tool. It does not
establish driving performance or a completed baseline. No gameplay/material
optimization has been promoted yet.

## Foliage and rendering follow-up — 2026-10-09 local time

The following are source/setup-report findings, not fresh GPU measurements.
Runtime overrides, actual selected LODs and pass timings still need validation.

| System | Concrete evidence | Implication |
| --- | --- | --- |
| Composition shrubs | BenmoreComposition/setup-report.json records 5,557 instances. setup_benmore_composition.py sets cull start/end to 1,400/2,100 m, shadows on, distance-field/RT participation off. Three mesh LODs use reduction fractions 1/.60/.32. | Isolate this group and its shadows independently. Inspect whether the lowest LOD remains expensive at distance before reducing visible planting. |
| Composition tussocks | Same report records 17,278 instances across nine bands. Setup uses 520/850 m culling, shadows/DF/RT off, and the painterly material override. | Landscape grass scalability does not automatically fix this separate composition layer. Test its cost separately; preserve nearby coverage. |
| Landscape grass | DefaultEngine.ini already sets density .5 and cull scale .6. The variety setup already disables dynamic shadows and DF lighting; contact shadows remain enabled. | Do not claim these existing reductions as new wins. Compare runtime grass inventory at each camera and identify overlap with composition planting. |
| Material work | setup_benmore_painterly.py overrides both grass varieties and relevant component materials. FOLIAGE in benmore_painterly_surface.py evaluates four broad world-space value-noise fields for pigment variation. | The original cheap vertex-colour material is not sufficient evidence of current shading cost. Evaluate moving broad pigment variation to per-instance data or vertex interpolation, keeping root/tip colour and the palette, if BasePass measurements justify it. More vertex work is not automatically cheaper for distant dense geometry. |
| Fade behaviour | Authored tussock materials are opaque and their setup graphs do not consume PerInstanceFadeAmount. No wind/WPO is authored in these graphs. | Cull-start distance alone does not provide a smooth visual fade. Prefer LOD work before aggressive range cuts; inspect motion for hard popping. Generic masked-card and wind recommendations are not established fixes here. |
| Instancing | GTVegetationSubsystem::AddTaggedInstances creates static ISM components, grouped by mesh and band; these are not automatically HISM components. | Record actual component class and selected LOD/culling behaviour. Do not promise a benefit from an ISM-to-HISM or Nanite conversion without comparing it. |

### Candidate order after the baseline

1. **Distant foliage geometry/LOD:** high potential, low-to-medium visual risk,
   medium effort. Preserve transforms, near-car geometry and planting density.
   First compare composition shrubs, tussocks and landscape grass separately;
   then change one family's distant representation/LOD thresholds. Check moving
   silhouettes and pop-in at both sides of each transition.
2. **Shrub shadow work:** medium potential pending measurement, medium visual
   risk, low effort for diagnosis. The test disables only composition shrub
   shadows. It does not prescribe shipping with those shadows disabled. If the
   delta matters, retain close shadows and test a distance-aware solution.
3. **Painterly foliage shader:** medium potential pending BasePass attribution,
   low-to-medium visual risk, medium effort. Trial a cloned material preserving
   geographic pigment and root/tip colours. Compare interpolation/storage cost
   against the existing pixel shading; do not modify the shared material first.
4. **Lumen and clouds:** potentially high, medium-to-high visual risk, low effort
   for diagnosis and medium effort for a targeted fix. Isolate GI, reflections
   and volumetric clouds independently. Examine the existing LumenSceneUpdate
   lead in a fresh trace; disabling GI changes dependencies, not just one pass.
   Keep sky, water reflection and bank appearance in subsequent visual checks.

Apply the stage gates above: improvement beyond baseline variance and at least
max(0.5 ms, 5%) at the bottleneck, no material regression elsewhere, and preserved
appearance in motion. Keep each asset trial cloned and each runtime setting
restorable. No candidate above has yet been measured or promoted.

### Prepared diagnostics and actual run status

- The guarded runner now accepts Views and Features, allowing short targeted
  ABBA tests instead of always running every category. Added composition shrubs,
  composition tussocks, shrub-only shadows, Lumen GI/reflections and clouds.
  Original settings are restored for the final A sample; the test process exits
  without saving map or asset changes. Already-disabled CVars are reported as
  skipped. Diagnostic deltas include dependencies and must not be added together.
- Added a runtime inventory of component class, instance count, material bindings,
  culling, shadows, DF/RT participation, authored LOD metadata and Nanite state.
  Per-camera generated landscape grass is inventoried after warmup. Base material
  properties are labelled separately from instance overrides and actual shader
  cost. These runtime API paths still require a successful live validation.
- Added ABBA summaries with separate baseline drift and disabled-repeat spread;
  an apparent improvement smaller than either is not flagged as a screening win.
  A diagnostic win is never automatically marked ready for promotion. Ten offline
  tests pass, plus Python and PowerShell syntax checks.
- Input checks now include the loaded project DLLs and a Content asset
  size/timestamp inventory, in addition to the source/config/map hashes. This
  catches ordinary shared-project edits; it is not an atomic snapshot or backup.
- Run `20261010T031848408Z-c7b58d50` launched one editor and exited on the required
  resolution assertion: actual 1274x682, requested 1440x900. No timings were
  accepted. Engine source shows the offscreen virtual desktop starts from
  r.SetRes (1280x720 default). The harness now requests a larger virtual desktop
  before opening PIE, while retaining exact viewport assertions. That repair is
  not yet live-validated.
- Retry `20261010T032410252Z-e145bc8e` stopped during preflight because Claude's
  Art/build.sh/UnrealBuildTool/compiler work started. No editor was launched by
  that retry and no application was closed. Further profiling needs an exclusive
  shared-project window; an idle process snapshot is not a reservation.

Example targeted command for that window (stationary isolation, not a full
driving benchmark):

```powershell
& C:\GrandTour\Art\profile_benmore_rendering.ps1 -Run -Mode Isolation -Views Ford -Features composition_shrubs,composition_tussocks,landscape_grass,shrub_shadows -CaptureSeconds 30
```

First validate the baseline mode and viewport repair, then run this isolation.
Repeat promising results at Long_Vista and Lake_Mouth and on actual driving
routes before promoting an optimization. Accepted water effects and vehicle
handling remain the visual/behavioural baseline; bank and finer-foam work follows
the performance stages.

## Capture findings and profiling stop — 2026-10-10

The owner reserved a quiet window, then explicitly instructed: "Finish this
capture and stop profiling." Profiling is now stopped. The diagnostic editor
exited at 18:45:12 UTC; process inspection confirmed no Unreal editor remained.
No further run was launched. Runtime tracing overrides disappeared with that
process; no rendering preset, map or material change was saved by these tests.
The final hardware-tracing restoration sample did **not** complete.

### Evidence status

- `Art/Export/BenmoreGaea/PerformanceRuns/20261010T183715641Z-a3afccf7`:
  one 15-second stationary Ford capture, 429 frames. The runner stopped because
  local GPU usage exceeded its budget. This is useful evidence of the current
  stressed scene, not a passed baseline or optimization comparison.
- `Art/Export/BenmoreGaea/PerformanceRuns/20261010T184104341Z-836ce089`:
  memory dump and two 15-second tracing-mode samples. Planned ABBA repetition
  stopped after A/B when the workload guard detected `GoWR.exe`, PID 17364,
  at 18:45:09 UTC. The runner marked the entire run invalid. The earlier A/B
  observations below are retained as provisional diagnostics, not a certified
  speedup. No other application was closed.
- Both used the actual PIE viewport **1440 x 902**, requested 1440 x 900,
  100% screen percentage, uncapped and VSync off. The harness now explicitly
  records and checks that small viewport difference. These are real CSV frame
  timings, not screenshot/GIF playback rates.
- These were stationary renderer tests with GameModeBase, not driving tests.
  Persistent scene vehicles remain present. Vegetation driving, long vistas,
  river traversal and the lake still lack a complete comparable baseline.
  Thermal/clock variability also remains uncontrolled; telemetry reached 88 C.

### Observed costs

The first quiet capture measured frame median **36.61 ms**, p95 **42.64 ms**,
GPU median **34.71 ms**, and GameThread median **16.76 ms**. Render/RHI summary
counters near zero are unsuitable for attribution and require trace inspection.
Local usage median was **5178.71 MB** against **5045.50 MB** median budget,
with minimum frame-paired headroom **-287.77 MB**; all 429 frames exceeded budget.
Memory pressure therefore exists even without the previously competing game.

Largest relevant GPU scope medians in that capture: LumenSceneUpdate 10.31 ms,
Basepass 4.97 ms, Prepass 3.31 ms, TSR 2.41 ms, cloud shadows 2.22 ms,
ShadowDepths 1.36 ms, LumenReflections 0.53 ms and SingleLayerWater 0.48 ms.
Scopes may nest or overlap; do not sum these numbers. SingleLayerWater is only
one water rendering scope and does not measure all simulation or vehicle effects.
The evidence prioritizes Lumen and residency investigation; foliage's share of
Basepass/Prepass is still unmeasured.

| Provisional tracing diagnostic | Frame median / p95 | GPU median | LumenSceneUpdate median | Minimum local headroom |
| --- | --- | --- | --- | --- |
| Original hardware tracing, 379 frames | 40.22 / 54.47 ms | 38.82 ms | 11.11 ms | -292.21 MB |
| Software tracing, 471 frames | 31.44 / 36.16 ms | 29.59 ms | 0.19 ms | +42.48 MB |

The single A/B shows approximately 22% lower median frame time, but lacks the
return-to-baseline and repeat samples. Software tracing also visibly changes
the water reflections in `TracingMode_0.png` versus `TracingMode_1.png`, and
still fails the memory-headroom gate. Time/clouds were not frozen for those
screenshots. **Do not promote this global switch as the optimization.**

### Memory allocation leads

The second run's `editor.log` contains `rhi.DumpMemory`,
`rhi.DumpResourceMemory 80`, and `ListTextures` output. It lists two 512 MB
virtual-shadow physical pools, two 85.375 MB shadow HZB pools, a 528 MB Nanite
cluster-page resource, a 255 MB virtual-texture physical resource, an 84.375 MB
TSR history and multiple 64–72.25 MB Lumen resources. The aggregate ray-tracing
acceleration-structure statistic was 340.014 MB. Listed resident content
textures totalled approximately 617.56 MB, so content texture resolution alone
does not explain the roughly 5 GB local usage.

These allocations are investigation leads, not additive resident VRAM totals:
resource listings can include reserved, duplicated and aliased resources.
In particular the 17,804.812 MB uncommitted reserved-buffer figure is virtual
reservation, not physical GPU usage. Duplicate pools suggest checking editor
and PIE render overhead; they do not prove two active rendering views each frame.

### Next stages, pending a future profiling window

1. **Separate editor overhead and recover memory headroom.** Compare with editor
   viewport realtime disabled, then a comparable single game view. Inspect
   shadow-pool allocation/occupancy before reducing pool capacity. High likely
   value given measured budget overruns; low effort for diagnosis, potentially
   visible shadow damage if capacity is cut blindly. Require the existing
   <=85% budget / >=512 MiB headroom gate, with no page-overflow artifacts.
2. **Narrow the Lumen change while retaining water reflections.** Investigate
   card capture/update work and GI separately from reflections. High potential
   based on measured scope cost, medium implementation/visual risk. Require
   repeatable improvement beyond drift and at least max(0.5 ms, 5%) at the
   bottleneck, plus unchanged accepted water appearance in motion.
3. **Attribute foliage and material work.** Isolate composition shrubs,
   tussocks and landscape grass, then investigate expensive distant geometry
   and painterly shading. Basepass/Prepass justify investigation but do not
   establish foliage as the culprit. Current runtime inventory reports Nanite
   enabled on composition scrub meshes, superseding older setup assumptions.
   LOD API calls made in PIE returned -1/empty editor-only metadata; those fields
   are unavailable, not proof of missing LODs. Collect them before PIE next time.
4. **Check persistent vehicle CPU work.** The newly placed fleet and per-car
   tick paths merit attribution; no cost delta was measured. Do not alter
   handling, buoyancy, traction or sleep thresholds to satisfy performance gates.

Each stage must retain its original runtime values or an explicit asset copy
as rollback, compare one change at a time, and pass the existing frame-time,
memory and visual gates across all four representative cases. No optimization
was promoted from this capture. Bank appearance and finer foam remain later
work, with the existing interaction grid and accepted bow/wake/spray preserved.

## Grass/detail and VRAM follow-up — 2026-10-10 (offline)

Owner requested reducing VRAM and examining how details such as grass render.
No editor, game, build or profiling run was launched for this follow-up. The
following comes from existing capture artifacts, project/UE 5.8 source and Epic
documentation. The earlier instruction to stop profiling remains in effect.

### Concrete detail costs to investigate

`Art/Export/BenmoreGaea/PerformanceAudit_2026-10-10/foliage-summary.json` groups
the saved runtime component inventory. This covers authored instances, not
generated landscape grass or the subset actually rendered at the Ford camera.

- 17,278 composition Straw/Rust tussocks have 850 m end culling, shadows off,
  ray-tracing visibility off and Nanite off. Their export manifest records
  2,660 / 896 / 336 triangles across three LODs. These are authored source
  triangle counts; actual installed/selected LODs still need verification.
- 13,034 Fine tussocks have 180 m end culling. Fine's source LODs are
  600 / 200 / 80 triangles. Another 3,659 Straw/Weathered instances use 180 m.
- 5,557 composition shrubs have 2,100 m end culling, cast shadows, and use
  Nanite. Changing conventional LOD settings is not sufficient evidence of
  changing their active Nanite geometry cost.
- A separate 2,400 Straw/Rust instances at 330 m have ray-tracing visibility
  enabled despite shadows being disabled. Check their reflection contribution
  before removing it. Most other grass already excludes both shadow and RT
  work, so those exclusions are not new optimization wins.
- Authored tussock components bind `M_Painterly_Tussock`. Its broad 42–115 m
  pigment field currently evaluates four value-noise calls in pixel shading.
  Those calls are arithmetic, not four texture fetches. This is a shading-time
  candidate; moving the calculation does not by itself recover substantial VRAM.

Preserve dense near-car grass. Trial a much simpler distant clump LOD and a
transition into terrain coverage rather than retaining hundreds of triangles
per tiny distant clump. Distances must come from projected size and moving
visual comparisons; an 850 m configured range does not mean all those instances
are currently drawn. Instancing already shares mesh data: triangle count times
instance count is not a valid estimate of resident mesh memory. Culling alone
also does not necessarily release loaded mesh/texture resources.

### Specific memory candidates

| Candidate | Evidence and potential | Risk and required comparison |
| --- | --- | --- |
| Shadow pool sizing | Log sets MaxPhysicalPages=4096. UE 5.8 allocates two array layers per physical pool (static/dynamic); 4096 x 128 x 128 x 4 bytes x 2 = 512 MiB per pool, matching two named resources in the dump. 2048 pages would nominally save 256 MiB per pool if both remain allocated. | Pool occupancy/overflow stats and moving shadow review are required. This is an allocation calculation, not measured residency savings; duplicate resources may be different scene lifetimes. Do not add their sizes indiscriminately. |
| Editor/PIE duplication | Repeated shadow, Lumen and instance resources. | Compare equivalent single game view and editor realtime disabled, then actual residency. Merely pausing editor rendering may retain allocations. |
| TSR history | Log sets r.TSR.History.ScreenPercentage=200. The colour history is 84.375 MiB. At 100%, this resource's nominal pixel storage is one quarter (about 63.3 MiB less). | Grass is a sensitive temporal-AA case. Check shimmer and motion stability; this leaves scene/output resolution unchanged but reduces history quality. |
| Permanent site textures | Four 2736x2554 RGBA resources are about 26.75 MiB each, uncompressed, one mip, nonstreaming: CompositionZones, CoverStructure, FineHillNormal and GeographicZones. Several 2017-sized masks are about 15.875 MiB each. | Trace live references and data semantics before compression, mip changes or removal. Road coordinates, ecology weights and normals cannot share a blanket compression policy. Usage Count=0 is not proof that an asset is safe to delete. |

The installed engine uses ImmediateCommit for its reserved VSM allocation when
supported, so the word Reserved does not mean this pool is entirely virtual
and free. Conversely the dump's general reserved-buffer totals still cannot be
treated as resident usage. Engine references: VirtualShadowMapArray.cpp lines
173 and 2419; VirtualShadowMapCacheManager.cpp lines 1094–1126; BaseScalability.ini
sets Epic shadows to 4096 pages and Epic AA history to 200%.

Use roughly **4 GB local usage** as the first working reduction target when the
available budget is around 5 GB, while retaining the stricter <=85% budget and
>=512 MiB headroom conditions. This is a proposed target, not a demonstrated
fit or an arbitrary streaming-pool cap. Validate across the four locations and
the sustained driving loop; no permanent setting was reduced in this follow-up.

### Prepared changes and their limits

- Added `Art/Unreal/benmore_foliage_detail_trial.py`. It validates the current
  shader, refuses an existing destination, and can create an unassigned clone
  under PerformanceTrials. Only the scalar geographic coverage moves through
  VertexInterpolator; pixel root/tip palette, lighting and source material
  remain intact. No extra texture or render target is introduced. The extra
  vertex arithmetic and interpolator may lose on dense distant geometry, so
  measure both Basepass and Prepass and review interpolated colour before use.
- The builder was **not executed in Unreal**; no candidate asset is installed.
  Syntax and source-split checks passed. Shader compilation, Nanite/ISM support,
  interpolator precision, visual comparison and runtime performance are pending.
  Rollback after a later trial is restoring original component material bindings;
  the original material is never edited by this builder.
- Repaired the profiler to collect authored LOD metadata before PIE and reuse
  it in runtime inventories, rather than recording editor API sentinel -1 as a
  real LOD count. Uncollected meshes are explicitly marked unavailable. Runtime
  validation of this change is pending; the ten offline metrics tests pass.

Relevant primary documentation: [Epic's Virtual Shadow Maps guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine)
describes pool sizing and occupancy stats; [Nanite foliage](https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage)
describes UE 5.8's foliage representation options. These are candidates to
evaluate, not evidence that a wholesale conversion or quality reduction helps
this scene. Priority remains memory residency, then attributed detail costs,
with the accepted water appearance preserved.

### Authorized first memory comparison — prepared, slot occupied

The owner's subsequent "go ahead" authorizes continuing staged implementation
and comparison. Preflight found `GoWR.exe` PID 17364 and `UnrealEditor.exe`
PID 19980, with device-wide GPU utilization at 99% and 5774 MiB used. The editor
command line identifies `check_live_mud_drive.py`, a separate automated check.
Neither process was closed; no second editor or build was launched. A request
to clear the shared slot is pending. This occupancy snapshot is not a benchmark.

The guarded runner now accepts `-MemoryProbe shadow_pool` (default),
`tsr_history`, or `lumen_hardware_raytracing` in Memory mode. The first stage is
only `r.Shadow.Virtual.MaxPhysicalPages` 4096 -> 2048, keeping hardware Lumen,
water, grass density and handling at baseline. It records explicit baseline and
candidate CVar values, respects CaptureSeconds, captures A/B images and resource
dumps outside timed windows, and requires GPU budget telemetry. The shadow trial
enables the UE 5.8 VSM CSV category and rejects absent `VSM/FreePages` telemetry
or negative free pages. Candidate headroom is recorded separately from whether
the diagnostic completed; neither implies visual approval or promotion.

Original CVar values are now restored on normal completion and error paths,
with readback recorded before the owned editor exits. Source/API review found
that UE 5.8 exposes `csvcategory VSM enable`; counters include VSM/FreePages.
The updated live path remains untested while the slot is occupied. Python and
PowerShell syntax checks and ten offline CSV tests pass.

First command when the slot is clear (not executed during preparation):

```powershell
& C:\GrandTour\Art\profile_benmore_rendering.ps1 -Run -Mode Memory -MemoryProbe shadow_pool -Views Ford -CaptureSeconds 30
```

Retain the 2048-page setting only after repeatable residency savings, no page
overflow, acceptable moving shadows and the established full-scene gates.
Otherwise restore 4096 and investigate duplicated scene allocations before
cutting shadow capacity further. No persistent rendering change has been applied.

### First shadow-capacity attempt — 2026-10-10, 15:01–15:05 MDT

After the owner closed God of War, the slot initially had no Unreal/build
process and GPU memory was 476 MiB. The guarded run
`20261010T210112917Z-be6e0198` launched one editor. It collected only the original
4096-page sample, then stopped before applying 2048. Runtime restoration readback
confirmed 4096 and the owned editor exited. No map/config/asset change was saved.

Two evidence-format issues were exposed: Unreal emitted duplicate auxiliary
`FMsgLogf/FMsgLogfCount` CSV columns, and one of 486 frames had a simultaneous
zero local budget/usage reading. The parser now keeps duplicate auxiliary series
separately by occurrence, still rejects duplicate critical timings/budgets,
preserves every frame timing, and labels zero-pair memory readings unavailable.
Missing memory coverage prevents a passed memory gate; it is never treated as
free VRAM. Sixteen offline tests pass, including independent duplicate values,
critical-name rejection, memory gaps and incomplete comparison handling.

The original failed report is preserved. `offline-reanalysis.json` contains
the recoverable observations and explicitly marks the comparison invalid:
frame median 60.71 ms, GPU median 56.31 ms, local headroom at worst -521.85 MB,
485/485 available memory samples over budget, one unavailable sample.
VSM/FreePages median is 3177 of the configured 4096; its minimum includes zero,
so the median alone cannot certify a smaller pool. This justifies testing
capacity, not silently assuming the full scene fits in 2048 pages.

The final guard also found six mud/terrain source files changed by other work
during the capture. Source/DLL/input guard rules were not relaxed to accept it.
After this editor exited, Claude launched a build and then another Unreal
commandlet. No retry was launched into that occupied slot. A request to pause
Claude's Unreal/build work is pending; God of War closure is already confirmed.

### Owner's in-play warning screenshot — 2026-10-10

The supplied screenshot reports video memory 573.785 MB over budget and cached
Lumen/real-time sky lighting clipping at exposure EV 13.2, outside [-8,12]. These
are separate issues. The screenshot is evidence of residency pressure, not a
frame-time measurement or proof of a specific cause for that overrun.

Applied `r.EyeAdaptation.CachedLightingPreExposure=8` under SystemSettings in
DefaultEngine.ini. Installed UE 5.8 source (PostProcessEyeAdaptation.cpp lines
201–208 and 249–251) defines this as a storage pre-exposure offset and explicitly
documents 8 as covering [-4,16]. This contains Benmore's reported 13.2 and the
existing weather presets (-2.0 through 0.25). Camera EV, sunlight intensity,
water materials and rendering quality settings are unchanged. This correction
does not claim a memory or FPS benefit. Remove this one CVar line to roll back;
do not restore the entire dirty config from Git.

The existing interactive Unreal editor (PID 6056) was left open. No remote Python
editor endpoint was discoverable, so this config edit has not been applied to
that already-running session. It takes effect on next editor launch, or the
same CVar can be entered in its console now. Visual/cache-refresh verification
is pending; range validation was checked against engine source and project
weather preset values. The 2048-page shadow capacity trial remains unpromoted.

### Memory stage 1 config trial applied — 2026-10-10

Following the owner's repeated request to act on the atrocious performance,
added `r.Shadow.Virtual.MaxPhysicalPages=2048` to DefaultEngine.ini SystemSettings
as a **provisional, reversible trial**, not a validated/passed optimization.
This is the first persistent memory-budget candidate. It takes effect on next
launch; it was not injected into the existing mud-variant check (PID 4588).
No editor was closed or launched and no build was run by this change.

Evidence for trying it: the recorded 4096-page setting, the 512 MiB per-pool
allocation formula, the two listed pools, 3177 free pages at the captured median,
and the owner's 574 MB over-budget screenshot. This evidence does not establish
the worst-case shadow-page requirement. Expected per-pool allocation reduction
is 256 MiB; actual process residency savings and FPS remain unmeasured. Existing
hardware Lumen, water, foliage density/culling and resolution settings remain
unchanged by this trial. Missing shadows, increased shadow instability or a page
overflow require rollback, even if memory usage falls.

Rollback: remove only the MaxPhysicalPages override and its stage-1 comments,
or temporarily enter `r.Shadow.Virtual.MaxPhysicalPages 4096` in the console.
Do not revert unrelated config changes. The separate cached-light exposure
correction can remain.

The runner now accepts an explicit MemoryReference so it can load the trial
config, compare against the historical 4096-page reference, and restore the
loaded value on completion/error. Next command in a clear shared slot:

```powershell
& C:\GrandTour\Art\profile_benmore_rendering.ps1 -Run -Mode Memory -MemoryProbe shadow_pool -MemoryReference 4096 -Views Ford -CaptureSeconds 30
```

Config placement and Python/PowerShell syntax pass. Live comparison and visual
checks are still pending; there is no claim that Benmore now runs smoothly.

### Additional detail work completed offline — 2026-10-10

Built actual far-grass candidates in
`Art/Export/BenmoreGaea/FarTussockTrial_20261010_v2`, using a fresh output directory
and leaving the approved Blender library and all Unreal assets unchanged.

| Mesh family | Existing source LOD2 | New LOD3 candidate | Triangle reduction at that LOD |
| --- | --- | --- | --- |
| Straw / Rust / Weathered | 336 | 48 | 85.7% |
| Fine | 80 | 24 | 70% |

The exporter retains complete blades, reduces longitudinal segments and widens
the retained blades in proportion to their reduced count. The first candidate
looked too sparse in the geometry review; v2 increases retained blade width.
Its surface area is approximately 84–90% of the prior LOD2, but surface area is
not a substitute for projected coverage or a moving-camera visual check.
The proposed extra LOD threshold is 0.008 screen size. Existing LOD0–2 geometry
and thresholds are preserved by the prepared clone importer; no near-car detail
or planting transforms/density are reduced.

New files:
- `Art/Blender/export_benmore_far_tussock.py`: isolated FBX export plus review.
- `Art/Blender/verify_benmore_far_tussock.py`: FBX import round-trip checks.
- `Art/Unreal/benmore_far_tussock_trial.py`: creates unassigned, unsaved mesh clones
  with the extra LOD, refuses existing destinations and verifies old LOD vertex
  counts, screen thresholds and material bindings before returning candidates.

All four v2 FBXs round-trip with correct metre bounds, exact triangle counts,
UVs and vertex colours present. Original Blender source hash is unchanged.
`geometry-review.png` and `far-tussock-review.blend` show LOD2 above LOD3. These
are geometric reviews, not Unreal look approval, screenshot FPS, or proof of
runtime improvement. Import into Unreal and its visual/performance validation
remain pending while the separate mud-variant check occupies the engine slot.
Additional LOD data can slightly increase mesh storage; this work targets
distant geometry cost, not the large renderer-pool VRAM allocations directly.

Added optional `-DisableEditorViewportRealtime` to the profiling runner. It
requests a LevelEditorSubsystem realtime override before PIE and removes only
that override on finish/error, preserving the underlying editor preference.
It is off by default, recorded in the report when requested, and must be compared
separately from the shadow-pool trial. Disabling editor rendering does not prove
its resources were freed. Python/PowerShell syntax and all sixteen offline CSV
tests pass; this new live API path is not yet exercised.

Remaining high-value candidates, in order after validating the shadow trial:
1. Determine editor/PIE overhead using the explicit control above; confirm in a
   single game view before describing memory as a shipping-game requirement.
2. Compare Lumen GI High versus Epic while keeping hardware tracing and reflection
   settings fixed. The measured 10–11 ms scene-update scope justifies investigation;
   GI scalability is not guaranteed to remove that particular cost. Reject changes
   that lose accepted water reflections, bank lighting or stable indirect light.
3. Compare the new grass LOD and vertex-pigment material as separate changes.
   Accept only a measurable geometry/Basepass benefit beyond variance, with no
   visible popping or coverage loss through repeated transitions.
4. Trial TSR history 200 -> 100 separately. The observed 84.375 MiB colour history
   would nominally become about 21.1 MiB, not a multi-gigabyte saving. Review grass
   shimmer and fine water detail. Epic's [TSR guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/temporal-super-resolution-in-unreal-engine)
   documents the 200% history's quality purpose; do not treat it as free waste.
5. Inspect live references and precision needs of nonstreaming site textures;
   selectively compress/stream ordinary visual data while retaining exact masks
   where coordinates, terrain or vegetation generation depend on their values.

No further global renderer quality cuts were stacked onto the provisional
shadow setting during this offline work. Persistent game runtime changes remain
the cache exposure correction and the unvalidated 2048-page shadow-pool trial.

### Volumetric clouds disabled at owner's request — 2026-10-10

Owner explicitly stated volumetric clouds are not needed. Added
`r.VolumetricCloud=0` to DefaultEngine.ini SystemSettings. This is an approved
feature removal, separate from the provisional shadow-pool trial. The sky dome,
SkyAtmosphere, sun, skylight and distance haze remain configured. Cloud shapes
and their contribution to shadows/reflections will naturally disappear; water
simulation, bow/wake/spray, materials and hardware Lumen settings are untouched.

Installed UE 5.8 VolumetricCloudRendering.cpp documents this runtime toggle as
ignoring VolumetricCloud components; ShouldRenderVolumetricCloud checks it.
Cloud shadow/AO availability also depends on initialized volumetric cloud data.
The earlier quiet Ford capture measured approximately 2.22 ms in the cloud-shadow
scope and 0.52 ms in the cloud scope. Those are attribution leads, not a promised
additive frame-time saving. A fresh timing/VRAM delta has not been measured.

No cloud actor/material assets were deleted, and shader support was not disabled
globally, avoiding an unnecessary shader rebuild. Referenced cloud textures may
remain loaded; do not claim this switch releases all cloud asset memory.
The existing separate Unreal test was left running. The default applies on next
editor/game launch; the equivalent current-session console command is
`r.VolumetricCloud 0`. Removing the override (or console value 1) reverses it.
Validation: one override under the correct section and the installed engine's
render-path guards checked. Live visual and performance checks remain pending.

### Code-only continuation toward 120 FPS — 2026-10-10

Owner explicitly requested code work now and tests later while another Unreal
mud test and Ace Combat 7 occupied the machine. No Unreal launch, build, live
capture or regression run was performed in this continuation. Python AST and
PowerShell syntax parsing passed; C++ compilation and all functional/runtime
validation remain deferred. No 120-FPS result is claimed.

Implemented a rendering-submission optimization in GTSprayComponent.cpp/.h:
`gt.Spray.SparseUpdates=1` submits the live particle prefix plus the previously
visible prefix that must be hidden after expiry. The remaining hidden tail is
left alone. Once the last particles retire, idle emitters stop submitting
transforms. Successful submissions update the remembered live count; failed
submissions retain it for retry. Existing RemoveAtSwap compaction, spawn rates,
random numbers, integration, deposition, camera-facing water shapes, custom
opacity/family values and particle limits are preserved. A Timing Insights scope
`GTSpray_PushTransforms` permits later attribution. UE 5.8's installed ISM API
supports the const TArrayView overload used here; no temporary array is allocated.

The corresponding small change in GTSprayArt.cpp skips all eight clump-pool
uploads only after the mud pool is empty and its preceding draw was cleared.
The nonempty-to-empty transition still runs the original clear; art-mode toggles
retain the original path. Active clump shape, colour, orientation and deposition
are unchanged. Claude's other spray/mud work was retained. This reduces known
redundant work, but its contribution to frame time is not yet measured.

Rollback after the next build: `gt.Spray.SparseUpdates 0` restores full-pool
submissions and empty-clump updates. Return to 1 to enable the new path. No build
was attempted against the running editor. Before promotion, compare 0/1/1/0
while parked, spraying, draining the pools to empty, refilling, recycling a full
pool, and toggling `gt.Spray.Art`; check for ghosts and retained water shape,
opacity, muddy tint and clump appearance. Re-run the existing spray/audio and
water regressions after building in a clear slot. Do not alter handling gates.

Added `Art/Unreal/benmore_performance_stages.py` and Candidate mode in the guarded
profiling runner. These wire the previously separate builders into reversible
PIE comparisons; they do not install optimized foliage into the saved demo map:

| Stage | Implementation | Required later acceptance |
| --- | --- | --- |
| foliage_far_lod | Builds unsaved clones from the verified v2 FBXs, appends LOD3, swaps exact authored tussock bindings in PIE, retains instance counts and near LODs. | Measurable geometry benefit, continuous driving review of coverage and transitions. |
| foliage_vertex_colour | Builds the isolated pigment material, replaces only exact base-material bindings; material instances and their overrides are excluded. | Lower shading cost without visible palette/coverage changes or new interpolation artefacts. |
| lumen_lighting_updates | Direct lighting update factor 64 and radiosity 128, with any already cheaper loaded override preserved. | Faster measured lighting work, acceptable moving-light/occlusion response, water/bank comparison. |
| spray_sparse_updates | Reference 0 versus candidate 1 after the C++ change is built; restores the actually loaded value afterward. | Equivalent effects through pool retirement/refill and a measured submission reduction; whole-frame benefit must be separately established. |

The narrower Lumen stage is intentional: UE 5.8 BaseScalability's whole High GI
preset also changes ray-tracing scene build mode, hit-lighting allowance and
foliage backface diffuse shading. This stage changes only the fraction of surface
cache texels lit per frame (engine source defines texels = atlas texels / factor).
It may not reduce the earlier 10–11 ms LumenSceneUpdate scope; inspect the measured
scope instead of predicting a win. Hardware tracing/reflections remain fixed.

Each stage runs reference/candidate/candidate/reference, records runtime bindings,
checks protected settings and viewport, rejects over-budget/incomplete telemetry,
waits for shader workers outside captures, and attempts rollback on failure.
Candidate helper sources and FBX/manifest inputs join the run's input hashes.
Both original and candidate foliage resources remain loaded for all samples;
the resulting memory figures include that overhead and are not shipping-memory
estimates. Dynamic landscape-generated grass is excluded from the initial swaps.
A separate installation and moving-camera review remain necessary before saving
any foliage changes into the demo.

Deferred commands (one at a time, only after the slot is clear; the spray stage
also requires a completed build while Unreal is closed):

```powershell
& C:\GrandTour\Art\profile_benmore_rendering.ps1 -Run -Mode Candidate -Stage foliage_far_lod -Views Long_Vista -CaptureSeconds 30
& C:\GrandTour\Art\profile_benmore_rendering.ps1 -Run -Mode Candidate -Stage foliage_vertex_colour -Views Ford -CaptureSeconds 30
& C:\GrandTour\Art\profile_benmore_rendering.ps1 -Run -Mode Candidate -Stage lumen_lighting_updates -Views Ford -CaptureSeconds 30
& C:\GrandTour\Art\profile_benmore_rendering.ps1 -Run -Mode Candidate -Stage spray_sparse_updates -Views Ford -CaptureSeconds 30
```

These stationary comparisons rank candidates. Continuous driving through dense
vegetation, long vistas, the crossing and the lake is still required to establish
120 FPS. The report now explicitly records 120 FPS / 8.333 ms as the target and
keeps `target_verified=false` for this stationary runner.

## 2026-10-10 evening: resumed work, 80 FPS target

The owner's latest request sets the target to at least 80 FPS (12.5 ms/frame).
The earlier 120 FPS target remains historical. No 80 FPS result is established.

Build `Saved/Logs/benmore_perf_build_20261010_1932.txt` succeeded. The first
build exposed a unity-build name collision between relief and snow helpers;
renaming the local relief helper to ReliefStatsPercentile fixed it without
changing arithmetic. The fresh regression log
`Saved/Logs/benmore_perf_regression_20261010_1932.log` records five passing CPU
tests: Spray.Art and Water.InteractionVisuals, MovingDomain, PassiveDetail and
RiverReference. The rendered spray transitions and spray/audio driving gate
still require validation. Added GTVehicle CSV/Timing Insights scopes do not
change vehicle update order or physics.

Claude's BO1 asset changes and BO2 instance-update changes were already present
and are retained; see BENMORE_OPTIMISATION_PLAN.md and BO1/bo1-report.json.
They are part of the new baseline, alongside the cloud/pre-exposure/shadow-pool
settings and sparse spray updates. Cross-run improvement must not be attributed
to just one change. The profiling runner now reserves the shared named mutex
before waiting, and wait_unreal_free.ps1 observes that reservation. This prevents
cooperative queued tests from taking the gap during the quiet GPU preflight.
Direct launchers still need coordination. No other worker's process was closed.

Valid quiet stationary river baseline:
`Art/Export/BenmoreGaea/PerformanceRuns/20261011T014412921Z-c3b5e95f`.
1440x902 actual viewport, 100% screen percentage, uncapped, 1,165 frames.
Median frame 25.2439 ms (~39.6 FPS), p95 30.1662 ms, p99 33.6613 ms.
Median GPU 24.2871 ms. Minimum local-memory headroom 258.4805 MB, peak usage
94.868% of the available budget, no over-budget or unknown samples. Every frame
misses the proposed 15%/512 MB headroom target. This is not a driving benchmark.

Measured GPU scope medians (overlap is possible; do not sum): Basepass 5.5755 ms,
Prepass 3.9384 ms, TSR 2.992 ms, deferred lighting 1.5234 ms, shadow depths
1.4803 ms, shadow projection 0.9749 ms, Lumen reflections 0.556 ms, single-layer
water 0.4588 ms, LumenSceneUpdate 0.1686 ms. The previous Lumen scene-update
bottleneck is much smaller in this combined current state. Prioritize grass
geometry/shading and memory headroom before further Lumen quality cuts.

Candidate support now includes unsaved Nanite clones with Preserve Area, plus
landscape grass variety references regenerated outside capture windows instead
of unsafe live swaps of GPU-owned grass components. Runtime component counts,
material/mesh bindings and screenshots must pass before accepting a result;
zero CPU instance counts are not evidence that landscape grass is absent.
The provisional real-controls driving helper is not yet integrated or validated.

Nanite memory ABBA completed successfully at Ford:
`PerformanceRuns/20261011T014803072Z-b38cc2f4`. Verified actual pool sizes
512/128/128/512 MB; visible streaming data stayed at 4 MB. The RHI cluster page
buffer changed from 528 to 144 MB. Local-budget minimum headroom was
296.53/553.79/558.79/332.60 MB. No window exceeded the local budget, but all
still missed the 15% headroom criterion. Reference/candidate mean-of-window
frame medians were 26.3507/26.8899 ms; baseline drift was 1.7844 ms. There is
no demonstrated FPS benefit. The two 960x600 screenshots retain matching
vegetation, terrain and water/reflection coverage by inspection; moving views
and other locations remain unverified. Pool size was restored to 512, not
promoted globally.

Sustained GPU telemetry also shows a thermal limitation: the run reached
86-87 C with clocks falling to 1785-1875 MHz near its end. A later read-only
NVIDIA query, during Claude's mud test, explicitly reported active software
thermal slowdown at 87 C. Final comparisons must include warmed sustained
operation; a cold-start FPS peak would not establish the owner's target.

The first far-LOD preparation run (`20261011T015354970Z-e37a585c`) stopped before
PIE/timings: FBX import appended a material slot and the preservation assertion
caught it. The importer now remaps the single new LOD section to the retained
material slot, removes the unused imported slot, and checks near-LOD section
bindings. No source foliage assets or map were saved by that failed trial.

## Standalone confirmation and ongoing trials — 2026-10-10 evening

The current owner target is 80 FPS (12.5 ms), superseding the historical 120 FPS
request. It has NOT been achieved. Valid standalone ABBA capture
`PerformanceRuns/20261011T023311982Z-261cd63e` ran the normal game at the saved
1600x900 output resolution, 100% internal screen percentage, with audio enabled.
TSR history 200/100/100/200 yielded median frame times
22.03945/22.9159/23.8616/25.8946 ms. Reference drift (3.85515 ms) exceeds the
apparent aggregate improvement: there is no established total-FPS gain.
TSR scope medians were 2.7032/2.03/2.14/3.33 ms. Local usage fell from about
4363.86 MB to 4276.36 MB (87.5 MB), with no over-budget or unknown samples.
All windows still failed the proposed memory headroom criterion. The 1600x900
reference/candidate stills retain grass, terrain and water coverage by inspection;
animated reconstruction/aliasing remains unverified. History restored to 200.

The uncooked standalone process uses less memory than PIE, but the observed
saving is about 400 MB, not evidence that an extra editor render accounts for
most GPU time. Sustained thermal slowdown remains a confounder; subsequent
comparisons now warm for 120 seconds before the first window.

Far-LOD trials recovered two harness issues: FBX material-slot remapping and
runtime swaps of static authored components. One trial was interrupted by
external Blender rendering and is explicitly invalid. No foliage candidate has
been installed. A reduced-curve LOD2 trial retains every blade and the original
LOD transition, reducing 336 to 144 triangles (Fine 80 to 40); its source-space
area is over 90% of reference. LOD0/1 are unchanged. These geometry statistics
are not proof of equivalent rendered coverage. Files are in
`TussockSegments_20261011T023511Z`; runtime and moving-image verification remain.

The guarded standalone runner now supports real-control driving routes and
independent memory/rendering comparisons, with every timed frame retained.
Driving routes are provisional and reject stalls, rollovers, corridor departures
and a river route with no water spray. No handling settings are modified.
`target_verified` remains false until representative sustained driving succeeds.

Lumen atlas ABBA completed with guard success:
`PerformanceRuns/20261011T025036380Z-3a0c8195`. At 4096/2048/2048/4096,
allocated/capacity pages were 35/1024, 34/256, 34/256, 34/1024.
Median frames were 25.7413/26.1923/26.5959/27.28385 ms; minimum local
headroom 504.91/807.41/742.27/502.90 MB. No FPS gain is established.
Reference/candidate 1600x900 images were inspected: matching terrain/grass
and reflection coverage; different water animation phase. Card texel detail
is retained while capacity changes. Other viewpoints and driving remain gates.

Provisional configuration now combines the individually measured memory
stages: `r.LumenScene.SurfaceCache.AtlasSize=2048`,
`r.Nanite.Streaming.StreamingPoolSize=128`, and
`r.TSR.History.ScreenPercentage=100`. Remove exactly those three overrides
to restore defaults 4096/512/200. These are memory/reconstruction trials,
not a claim of 80 FPS or validation for other maps. No grass density, water
simulation resolution, water shader, particle count or vehicle handling changed.

Nanite grass with Preserve Area completed a valid ABBA trial at Ford:
`PerformanceRuns/20261011T025921373Z-b35d8bbe`.
Frame medians 24.99165/19.0447/19.11455/26.44435 ms, conventional base pass
5.7738/1.5531/1.55335/6.18725 ms and prepass
4.15445/0.1805/0.1805/4.43115 ms. This is a substantial repeated gain, with
runtime grass-component count checks passing. It is still below 80 FPS and the
960x600 comparison shows objectionable bright speckling in distant grass.
Not installed. A separate Voxelize candidate is being evaluated. Existing
project `r.Nanite.AllowVoxels=1` already supports it; engine RenderUtils.cpp
confirms support when either AllowVoxels or Nanite.Foliage is enabled.
Epic describes the aggregate-geometry representation in its UE 5.8 guide:
https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-foliage
This is an experimental path and requires visual/performance validation here;
no prediction from that documentation is treated as a benchmark result.

Voxel grass trial `PerformanceRuns/20261011T030752256Z-6493b337` completed its
capture but FAILED visual acceptance: much of the grass rendered black, with
a missing Voxels material usage warning. Do not promote or cite its timings
as an equivalent-image improvement. It restored the original meshes and saved
no source assets. The following plain Nanite trial avoids that experimental
path and Preserve Area's distant enlargement; assess it independently.

Plain Nanite grass trial `PerformanceRuns/20261011T031552530Z-d678d977` passed
its capture guards and stationary image review. Mean-of-window frame medians
26.55245 ms reference / 18.95155 ms candidate: 7.6009 ms (28.63%) saved,
versus 1.9796 ms reference drift and 0.0209 ms candidate repeat difference.
The near foliage and water appearance remain comparable; distant grass is
less enlarged than Preserve Area. Moving-camera review is still required.

Installed on the four shared `ArtTests/TussockStyle/SM_TS_*` meshes (Fine,
Rust, Straw, Weathered), with Nanite enabled and ShapePreservation=None.
`Art/Export/BenmoreGaea/NaniteInstall_20261011T033519914Z/install-report.json`
records all four successful saves, before/after hashes and exact package
backups. No map or material assets were saved. The operation changes Nanite
settings only; the imported source geometry is not edited. Unreal regenerates
LOD0 render resources for its fallback, so their vertex counts legitimately
change. Original conventional LOD screen thresholds are explicitly restored;
authored material interfaces and slot identities are checked separately from
derived UV-density metadata. Earlier guarded attempts saved no packages,
confirmed by matching their original hashes.

Rollback: with every Unreal process closed and the profiling mutex available,
verify each current package still matches its recorded after_sha256 before
copying that package's backup over it. Stop for review if a hash differs so a
later shared-project edit is not overwritten. Restore exactly these four files;
never reset the repository. Global grass density/culling and water/handling
settings remain unchanged. The 80 FPS target is not yet verified.

### Driving and spray upload follow-up — 2026-10-10 evening

Real Ford drive `PerformanceRuns/20261011T035643955Z-b2e8afd6` used the normal
game, audio and vehicle controls, at 1600x900 output with adaptive 50–75%
rendering and an 85 FPS cap. It recorded 2,440 frames in approximately 30 seconds,
91.02 m travelled and up to 119 water particles. Frame median/p95/p99 were
11.7686/14.3197/15.9729 ms. Actual render scale averaged 50.0207%, mostly at
its lower bound. Minimum local memory headroom was 1,568.73 MB. Memory passed;
smoothness failed. The average exceeding 80 FPS does not establish the target.
The GPU was thermally limited at 86–89 C. No applications or hardware settings
were changed to disguise that sustained condition.

Generated-grass shadow ABBA `PerformanceRuns/20261011T040804799Z-9fe0bae3`
verified caster removal/restoration and unchanged generated component counts.
Mean frame medians were 12.2992 ms reference and 12.41935 ms candidate;
reference drift was 0.6624 ms. Rejected: no measured gain. Grass shadows remain.

Inspection found `PushWaterMud` still rewriting five custom-data channels for
every allocated water slot on every vehicle each frame. It now follows the live
prefix plus the previous prefix, retiring expired slots once. The existing
`gt.Spray.SparseUpdates 0` restores full uploads. Emission, integration, opacity,
family, colour, physics and particle limits are unchanged. New regression
`GrandTour.Spray.RenderUploads` compares full and sparse custom data through
empty, growing, shrinking, compacted, full and refilled pools, including untouched
opacity/family channels. Build `benmore_upload_build_20261010_221702.txt`
succeeded; this regression, Spray.Art and all four water CPU regressions passed
in `benmore_upload_regression_20261010_221702.log`. Runtime benefit remains to
be measured separately.

Standalone after installing plain Nanite grass and the three memory stages:
`PerformanceRuns/20261011T033535549Z-611819e6`, 1600x900 output, screen
percentage 100/75/75/100. Frame medians 19.3724/14.5508/14.5982/19.56135 ms;
p99 23.1665/17.7918/18.1154/23.352 ms. Minimum local headroom was 1530.57 MB
at native and 1673.43 MB at 75%; visible Nanite data max 4.375 MB, pool 128 MB.
The native reference is now around 51-52 FPS and the 75% candidate around
68.6 FPS by inverse median, not the requested 80 FPS. The 1600x900 candidate
still preserves recognizable near grass, terrain and water/reflection detail;
no claim of equivalent native-resolution sharpness. The override restored to
100 and no persistent render-scale setting was installed from this comparison.

Shadow-resolution comparison at a fixed 60% render scale:
`PerformanceRuns/20261011T034316458Z-ef4e9cd4` tested directional VSM bias
-1.5/0/0/-1.5. Frame medians 12.4033/12.47965/12.6667/12.86455 ms; p99
15.6221/15.7477/15.7540/15.9381 ms. Aggregate saving only 0.06075 ms versus
0.46125 ms baseline drift: rejected for lack of material benefit. Bias restored
to -1.5, not installed. The 60% render scale was a test override only.

The next driving run tests adaptive resolution within 50-75% at 1600x900 output,
a 11.5 ms dynamic-resolution budget and 85 FPS frame limit. CSV must report the
actual DynamicResolutionPercentage within bounds; reading a CVar alone is not
proof that adaptation runs. Full GPU trace/per-pass capture is omitted for this
acceptance-oriented run; retain every frame and memory/Nanite counters. Its FPS
must not be presented as a like-for-like trace-enabled A/B result. The normal
vehicle, controls, game mode, HUD and audio remain active. Static captures now
apply the ordinary brakes to the possessed car to prevent it rolling downhill
while the camera is detached. Physics parameters are untouched.

### Continued driving evidence — 2026-10-10 late evening

`PerformanceRuns/20261011T042902217Z-1d51f48e` measured the sparse custom-data
upload build. Ford completed 91.00 m: median/p99 about 12.56/18.05 ms; vegetation
completed 186.29 m: about 15.81/19.36 ms. Spray CPU median at Ford was
1.00 ms versus 1.535 ms in the earlier drive, but whole frames did not improve.
This is a successive build comparison, not an isolated ABBA attribution. The
Long_Vista route failed its lateral corridor check on the steep hillside; no
handling parameters were changed. Lake was not reached. DDC maintenance also
overlapped the Ford window, so do not treat that window as a clean steady-state
comparison. Its recorded slow frames are retained.

`UpdateArt` also eagerly activated and rewrote Niagara parameters on every
wheel even when all three fine-emission rates were zero. New
`gt.Spray.LazyFineActivation=1` leaves an inactive system idle until it has a
positive rate. Already active systems retain their updates and particle tails;
no lifetime cutoff or particle-count reduction is introduced. Parameters are
populated before activation. Diagnostic launch velocity/rates still update.
Set the CVar to 0 before a fresh game session to restore eager activation;
toggling it after systems have already activated cannot recreate the lazy start.
CPU water spray, its random stream and bow/wake simulation are unchanged.

Build `benmore_lazy_build_20261010_223718.txt` succeeded; Spray.Art and
Spray.RenderUploads passed in `benmore_lazy_regression_20261010_223718.log`.
Ford drive `PerformanceRuns/20261011T043748403Z-c5c14c99` completed 90.73 m:
frame median/p99 11.7703/15.9671 ms; spray CPU median 0.1702 ms, vehicle tick
0.75 ms and render-thread Niagara 0.06 ms. The frame target still fails. Local
headroom was at least 1699.64 MB among available samples, but one of 2437 samples
was unavailable. The memory completeness gate failed, and this is not a full
baseline. The harness now records such gaps and finishes remaining cases;
the final memory gate still requires complete telemetry. VSM CSV counters are
enabled on following runs to check shadow-pool occupancy explicitly.

The Ferrari missing-skeletal-material-usage warnings totalled 42 at startup and
did not continue in the capture; no ongoing logging bottleneck was established.
No unrelated Ferrari asset was changed. The prepared willow-Nanite stage uses
unsaved clones of the four conventional willow meshes and restores exact runtime
bindings; it is not installed. Coarse shadow, Nanite pixel-error and TSR-update
quality comparisons are also trials, with starting CVars restored afterward.

The 240-second initial warmup exposed pre-capture drift on the road approach:
`PerformanceRuns/20261011T044911229Z-c41303eb` failed the route corridor check
before a useful driving sample completed. The driver is now re-placed after
warmup and allowed normal suspension/contact settling before measurement.
No placement, pausing or forced motion occurs inside the measured window.

Willow trial `PerformanceRuns/20261011T050518189Z-c8040097` completed its
ABBA windows but failed visual/shader acceptance. Its leaf materials lacked
Nanite usage, so Unreal used fallback materials. Ford's apparent 0.187 ms
and vista's 0.252 ms reductions are NOT equivalent-image performance wins.
No willow assets were installed. Future Nanite candidates explicitly prepare
and verify material usage before PIE, without saving those trial changes.

The same audit found three pre-existing Nanite scrub materials missing that
usage flag in standalone play. Their flags are now persisted, with no graph,
palette, mesh or map edits. Exact package backups and before/after hashes are
in `Art/Export/BenmoreGaea/NaniteUsage_20261011T051937538Z/install-report.json`.
All three saves and graph checks passed. Subsequent benchmarks use this corrected
setup; earlier standalone captures contained fallback scrub materials and are
not final visual-acceptance evidence. Rollback requires all Unreal processes
closed and matching current/recorded after hashes before restoring only these
three backed-up packages. The separate Ferrari audit confirmed M_GT_Vehicle
lacks skeletal usage; it was recorded, not changed in this operation.

### Further shadow attribution, October 10 late evening

Normal-game stationary road comparison
`PerformanceRuns/20261011T052023227Z-52dcc0f4` tested
`r.Shadow.Virtual.NonNanite.IncludeInCoarsePages` 1/0/0/1 at 1600x900,
fixed 60% internal scale. Reference/candidate mean window medians were
14.4296/14.3300 ms: 0.0996 ms saved, below 0.2245 ms reference drift.
Rejected; the original value was restored. This is not an 80 FPS result.
The former strict runner flagged seven source-only edits made during this run;
DLLs, settings, helpers and content remained unchanged. Use it only as
diagnostic evidence for the fingerprinted loaded binary. The runner now records
unbuilt source edits separately; builds and runtime-input changes still
invalidate captures, and a subsequent build requires new validation.

VSM counters in that road view showed approximately 509 requested pages,
1539 free pages in the 2048-page pool, 489 dynamically invalidated pages and
zero statically invalidated pages. ShadowDepths cost approximately 1.8 ms.
This motivates invalidation attribution, not another blind pool reduction.

`PerformanceRuns/20261011T053405863Z-61e302e1` temporarily changed landscape
component shadow-cache behavior Auto/Rigid/Rigid/Auto, with render proxies
refreshed outside captures and exact original properties restored afterward.
This was diagnostic only: disabling deformation-shadow invalidations globally
would not be a correctness-preserving fix. Reference/candidate mean medians
were 14.1704/14.22055 ms; invalidated pages stayed near 488 and ShadowDepths
near 1.78 ms. Rejected. No landscape shadow defaults or terrain code changed.

The next runner revision supports separate sequential ABBA CVar experiments in
one process. Each value is restored and verified before the next experiment;
only the initial warmup is shared. Per-stage screenshots and CSVs remain
distinct. This reduces repeated startup work without combining candidate
changes or treating stationary results as driving acceptance.

Further engine-source inspection corrects the initial invalidation hypothesis:
UE 5.8 defaults `r.Shadow.Virtual.UseReceiverMaskDirectional` to true
(`VirtualShadowMapClipmap.cpp`, lines 160-164). Its physical-page management
shader explicitly marks dynamic pages uncached when receiver masks are used,
because those pages may be incomplete (`VirtualShadowMapPhysicalPageManagement.usf`,
lines 373-377); these pages increment `DYNAMIC_INVALIDATED_PAGES` at lines 412-415.
Thus the observed count alone does not establish a material/WPO defect or
unnecessary geometry redraws. No landscape or shadow-cache fix is justified by
that counter. A receiver-mask comparison would be a separate rendering-path
tradeoff, with actual GPU timings and moving-shadow checks required.

Sequential normal-game ABBA run
`PerformanceRuns/20261011T054519133Z-c5f0b57a` completed all 32 stationary
windows at 1600x900 / fixed 60% internal scale. It used the fresh shared build
completed at 23:44, not the earlier lazy-spray-only DLL. All settings were
restored. None of these trials justified a default change:

| Candidate | Road frame saving / reference drift | Ford frame saving / reference drift |
| --- | --- | --- |
| Nanite MaxPixelsPerEdge 1 -> 2 | 0.105 / 0.228 ms | 0.023 / 0.195 ms |
| TSR History.UpdateQuality 3 -> 2 | -0.010 / 0.162 ms | 0.086 / 0.027 ms |
| Skeletal ray-tracing LOD bias 0 -> 1 | 0.043 / 0.067 ms | -0.051 / 0.028 ms |
| Landscape ray-tracing LOD bias 0 -> 1 | 0.028 / 0.062 ms | 0.107 / 0.266 ms |

Landscape ray-tracing geometry got cheaper within its named pass (road roughly
0.81 -> 0.62 ms; Ford roughly 0.47 -> 0.16 ms), but the full-frame gain did not
meet acceptance. Do not add overlapping GPU scope savings or promote a pass-only
win as FPS. The first 24 windows had at least 1646 MB local headroom, zero
over-budget frames and complete memory telemetry. This is stationary evidence;
moving road attribution remains necessary.

The game runner now supports `CompareDriving`: the same real-control route
is re-placed only outside each ABBA capture. It records actual trajectory,
distance and fine-particle counts/rates. Differences in route, residual effects,
weather/material state and clocks must be inspected; these are game runs, not
deterministic replays. Full-frame data is retained, and screenshots remain
outside the measurement windows. New candidate controls for gravel POM,
receiver masks, grass density and fine spray are diagnostic only, with exact
starting settings restored. None is installed by adding a trial.

### Subsequent moving-road attribution (11 October)

`PerformanceRuns/20261011T062542250Z-2d8598cf` completed four 30-second real
road drives (185.3-186.0 m each), fine spray enabled/disabled/disabled/enabled.
At 1600x900 output and fixed 50% internal scale, the mean of reference frame
medians was 15.16255 ms versus 15.255 ms with fine spray disabled. No benefit;
restore verified at `gt.Spray.Fine=1`. Every window had complete memory telemetry,
zero over-budget frames and at least 1700 MB local budget headroom. This road
route emitted no fine Niagara particles, so it is not an active-emission stress
test. Frame p99 ranged 18.51-21.19 ms. The 80 FPS target remains unverified.

The first 32-window CVar sweep had one unavailable memory sample in its last
stage; the complete first 24 windows cited above remain valid. Do not describe
all 32 as having complete memory telemetry.

`VehicleUsage_20261011T063904937Z/install-report.json` records the backup and
hashes for a flag-only repair of `M_GT_Vehicle`: enable skeletal mesh usage.
The package saved successfully and graph identity/custom code were unchanged.
The subsequent optional LOD audit failed because `lod_info` is not exposed on
UE 5.8's Python SkeletalMesh. Thus the report's `ok=false` does not mean the
material save was rolled back. No map, mesh, skeleton or physics asset saved.
The helper now uses the supported LOD vertex/section APIs. The flag fix is
correctness work, not a measured performance improvement. To undo, close every
Unreal process, require the current package SHA to match `after_sha256`, then
restore only that package from its backup; stop if another worker edited it.

The current four-stage sweep isolates probe spacing, density, gravel parallax
and receiver masks. Epic's [Lumen performance guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-performance-guide-for-unreal-engine)
and this installation's `Engine/Config/BaseScalability.ini` identify probe
spacing as a primary final-gather control. Preserve hardware water reflections
while testing GI controls. No new rendering defaults follow from documentation
alone; timing, visual and driving comparisons are required.

`PerformanceRuns/20261011T063941391Z-181022f8` completed the four-stage sweep:
32 stationary windows, normal standalone game/audio, 1600x900 output, fixed
60% internal resolution. All four controls restored exactly. Reference drift
is the difference between the two reference window medians, not a confidence
interval. These are screening results; no changes were promoted.

| Candidate | Road saving / drift (ms) | Ford saving / drift (ms) |
| --- | --- | --- |
| Gather spacing 16 -> 32 | 0.12 / 0.35 | 0.38 / 0.16 |
| Grass density 0.5 -> 0.35 | 0.23 / 0.33 | 0.23 / 0.05 |
| Gravel POM Enabled 1 -> 0 | 0.08 / 0.09 | 0.00 / 0.03 |
| Directional receiver masks on -> off | 0.01 / 0.12 | approximately 0 / 0.02 |

Zero over-budget frames; minimum recorded local headroom 1740.6 MB. One
memory sample in the first road reference window was unavailable, so the
complete-telemetry gate does not pass for the entire run. GPU thermal slowdown
was independently reported active by nvidia-smi (86-88 C, about 1665 MHz and
28-34 W in sustained captures). BatteryStatus reported AC power, 96% charge.
No hardware/power/fan controls were changed. Screenshots at density 0.35
showed broadly retained roadside cover, but the road frame gain did not exceed
reference drift and is insufficient to justify a global reduction.

The next diagnostic helper, `benmore_render_controls.py`, supports a reversible
bundle of UE 5.8 High opaque-GI settings and unsaved visibility attribution for
parked cars / authored tussocks. Visibility tests are never shipping candidates.
The profiler records actual runtime skeletal LOD selection outside measurement
windows. All these new controls still require an executed comparison; adding
support does not install the candidate or establish a saving.

`VehicleAudit_20261011T072120941Z/install-report.json` completed the supported
LOD/material audit. The skeletal material usage fix persisted; before/after
hashes matched and no asset was saved by this audit. The actual landscape
uses `Gaea/ShoreRefinement/M_GC_Terrain`, not `M_Gaea_Terrain`; compiler estimates
are 1090 pixel instructions and 19 pixel texture samples. The domain water
materials estimate 1306 pixel instructions; these counts do not establish GPU
cost and are not reasons to degrade water first. All five referenced painterly
grass types enable density scaling and point to the installed Nanite meshes.
Several fleet LOD2s remain large (Prado 121674 vertices, CraftedUtility 171414,
Pathfinder2002 230735). Imported LOD counts are not proof of runtime selection.

The successfully exported trace statistics are in
`PerformanceRuns/20261011T053405863Z-61e302e1/Analysis_20261011T071955360Z/`.
The 300-315 s interval overlaps the initial warmed road reference. Graphics and
compute queues overlap, and the timer export includes duplicated timer names;
do not sum its durations into frame time. It exposes a `ContrastAdaptiveShading`
scope (~2.75 ms mean duration) and the larger async Lumen gather scopes that
were absent from the simple CSV view. These scopes may include synchronization,
so their duration is not a promised saving. This installation's
`Engine/Config/Windows/BaseWindowsEngine.ini` enables software VRS and
contrast-adaptive shading. The new comparison tests that path, High opaque GI,
and irradiance-field final gathering separately, leaving hardware reflections
and water/spray controls intact.

`analyse_benmore_trace.ps1` holds the shared reservation, waits for its owned
Insights process, and exports response-file paths using forward slashes (the
Insights command parser consumes backslashes as escapes). The earlier failed
exports remain identified by their logs; only the verified CSV files above
are used. No external applications were closed.

### 2026-10-11: GI screening and shared-slot correction

Run `20261011T072323804Z-b00cb7a6` completed the road ABBA comparisons at
1600x900 output / fixed 60% internal resolution. Contrast-adaptive VRS removal
saved 0.267 ms against 0.638 ms reference drift; High opaque GI saved 0.037 ms;
irradiance-field final gathering saved 0.381 ms (2.66%). None meets the
promotion threshold. Original settings were restored. The 80 FPS target is
still unverified. Runtime telemetry selected skeletal LOD2 on the eleven
three-LOD fleet meshes, and LOD0 on both one-LOD Range Rovers.

The all-thread export in `Analysis_20261011T074514745Z` of the earlier
`20261011T053405863Z-61e302e1` trace exposes GPU occlusion-query waits inside
visibility workers and render-thread `ProcessVisibilityTasks`. Do not call
these waits CPU computation or assume removing the wait removes GPU work.
Epic documents this synchronization and a Development STATS accounting issue:
https://issues.unrealengine.com/issue/UE-320688 and
https://forums.unrealengine.com/t/inconsistent-sync-wait-related-to-occlusion-culling/2604964.
The next comparison omits detailed CPU/GPU tracing and per-pass GPU CSV stats.
This checks instrumentation overhead; lighter measurement is not a content fix.

The first lightweight attempt, `20261011T074716202Z-6a54787f`, was invalidated
when an external UBT process started during startup. No performance data is
accepted. A startup-error cleanup hole left our headless game alive before
`capture()` assigned its world; normal window-close returned false. Only the
verified owned capture PID 6984 was stopped, and `finish()` now resolves the
loaded game world on this path so it can issue normal `quit`.
`Art/build.sh` now calls `Art/build_guarded.ps1`, which holds the same named
reservation throughout UBT, checks editor/build processes, and refuses a busy
slot. The busy-slot refusal was executed and returned 2 without invoking UBT.
This closes the check/launch race for this shared build entry point. Direct
external launchers must still honor the reservation. No user app was closed.

### Parked-fleet attribution (lightweight capture)

`20261011T075126886Z-d353a6d2` completed with audio, 1600x900 output,
fixed 60% resolution, and no Insights trace / per-pass GPU CSV collection.
Road ABBA medians for the full fleet / hidden parked fleet / hidden / full:
13.954 / 12.104 / 12.132 / 14.267 ms. The ~1.99 ms mean difference exceeds
0.313 ms reference drift. This is an upper bound on the contribution of all
parked vehicle rendering, not permission to hide cars in the shipped map.
The lighter reference still misses 80 FPS, so tracing overhead is not the
main explanation. The new build also means this is not a controlled isolated
comparison of profiling instrumentation against the previous build.

The authored-tussock visibility ABBA medians were 14.285 / 14.252 / 14.019 /
14.415 ms. This small difference does not pass the promotion gate. Coverage
and all actor/component visibility were restored; no map was saved.

`GTRenderOptimisationLibrary` provides editor-script access to the UE 5.8
skeletal LOD settings through supported C++ APIs. Build
`Saved/Logs/benmore_far_lod_build_20261011T080502806Z.txt` succeeded in 31.70 s,
with Unreal closed. The appended LOD3 trial targets the five audited fleet
meshes with over 90,000 vertices in LOD2, retaining imported LOD0-2. Its
screen-size threshold is initially 0.000001, so automatic normal selection is
inactive. A reversible runtime forced-LOD comparison is prepared; neither the
new distance threshold nor temporal AA has been accepted as a default.

The first trial launcher failed before any asset edits because an editor-only
material-slot field required get_editor_property. The corrected retry is
recorded separately. Each successful mesh save must have its own original
package backup, before/after hashes, and unchanged near-LOD/material/skeleton/
physics checks. Review the saved rows before a rollback; never overwrite a
package whose hash has changed since the recorded trial save.

`FleetLODTrial_20261011T080724682Z/install-report.json` completed successfully.
The five additional LOD3 vertex counts are CraftedUtility 19,719, Impreza2003
19,938, Panda1990 19,942, Pathfinder2002 18,795, and Prado 19,994: 98,388 total
versus 764,648 in their existing LOD2s. This is an 87.13% geometry reduction,
not an FPS claim. All five imported LOD0-2 vertex/section counts and screen
sizes, material slots, skeleton and physics bindings matched their snapshots.
Every added LOD3 screen threshold was verified at approximately 0.000001.
The packages therefore remain in an inactive trial state pending comparison.
Use `Art/rollback_benmore_fleet_lods.ps1 -Report <install-report.json>` with
Unreal/build work closed to restore only those five packages; it verifies all
current and backup hashes before copying any package.

### Enabled fleet distance LODs; temporal AA rejected

`20261011T081406067Z-1e6f7ece` completed the isolated road tests with all cars
visible. Fleet LOD ABBA medians were 13.651 / 12.712 / 12.857 / 14.170 ms,
saving 1.126 ms (8.10%) against 0.519 ms reference drift. The five candidate
meshes reported predicted LOD3 / forced LOD4, confirming that they actually
rendered the intended geometry. Full-size images retained distant silhouettes
and colours. This is a stationary gain, not yet a moving-route gain.

`FleetLODPromote_20261011T082813270Z/install-report.json` successfully enabled
those additional LODs at screen size 0.20. Their original LOD0-2 screen sizes
remain 1.0 / 0.5 / 0.25. All four LOD vertex/section counts remained unchanged
through this threshold-only promotion; material, skeleton and physics bindings
were checked again. No map or handling asset was saved. This report contains
original pre-trial package backups and current hashes, so the rollback helper
should now be given this **promotion** report, rather than the older trial
report. Normal automatic LOD selection and driving remain to be verified.

The separate temporal-AA ABBA medians were 14.252 / 13.583 / 13.204 / 14.664 ms.
Despite its ~1.06 ms saving, the candidate screenshot visibly loses fine grass
and distant vehicle detail. It was restored to TSR (method 4) and is not a new
default. Renderer resolution also remains unchanged in project configuration;
60% in these captures is a diagnostic override only.

A fresh moving-road ABBA run tests generated-grass shadows and directional
receiver masks separately with the enabled distance LODs. Earlier stationary
shadow tests did not establish a gain; movement generates new shadow pages,
so their result is not assumed to apply. The driving grass check records start
and end component counts and verifies that newly generated components obey the
shadow setting. It allows legitimate streaming changes, while retaining all
frames, route checks and shadow-state checks.

WMI reports a 2560x1440 display on the NVIDIA adapter and 1920x1080 on the AMD
adapter. The existing 1600x900 performance captures do not establish 80 FPS at
either display's native resolution. The 80 FPS target remains unverified.

### Automatic distance-LOD and moving grass-shadow verification

In `20261011T083707599Z-478dbd68`, all five promoted fleet meshes report
predicted LOD3 with forced LOD0 (automatic selection). The four completed
grass-shadow moving windows cover 185.4-185.8 m each. Their ABBA medians are
15.598 / 15.562 / 15.840 / 15.676 ms; p99 is 18.777 / 18.582 / 20.837 /
19.159 ms. Disabling grass shadows does not improve this route. Keep the
original shadows. The independent receiver-mask experiment saved 0.182 ms
against 0.126 ms reference drift, below the screening threshold. Both original
settings were restored. All eight windows passed the memory-headroom gate and
failed the 80 FPS frame-time gate.

The next lighting comparisons should distinguish surface-cache lighting update
cadence from disabling diffuse GI. UE 5.8's `LumenSceneLighting.cpp` defines
texels updated per frame as surface-cache texels divided by UpdateFactor;
testing DirectLighting and Radiosity factors of 128 therefore reduces update
work without disabling GI or changing reflection technique. Check moving light
response and reject delayed lighting/ghosting even if timing improves.

Separately, `r.Lumen.DiffuseIndirect.Allow=0` is a reversible diagnostic while
hardware Lumen reflections remain enabled. Epic documents standalone Lumen
reflections with hardware ray tracing and automatic hit lighting. This may
alter ambient lighting and increase reflection shading cost, so neither a gain
nor visual equivalence is assumed. Compare road and ford, restore between
windows, and review water/bank lighting before any default change.

The follow-up `20261011T085456849Z-75485fe5` uses 1920x1080 output, fixed 60%
internal resolution and normal driving. It tests diffuse GI independently of
128/128 cache update factors. These settings remain capture-only. A first
untimed water review failed at a Python property lookup before driving;
`WaterVisual_20261011T085412322Z` is not a passed visual check. The revised
helper uses exact reflected C++ names and records live water material bindings
during driving as well as before it. No simulation setting was changed.

Further attribution leads: the prior saved inventory identifies 31 conventional
willows, four meshes with LOD0 vertex counts 148,699-550,917 and LOD thresholds
1/.18/.065/.02. Their older Nanite trial is invalid because of fallback leaf
materials (documented above). Any repeat must use the repaired usage preparation
and inspect rendered foliage; do not treat this lead as a measured saving.

The 1080p graphics-queue snapshots show substantial TSR rejection/history and
motion-blur work. They are single-frame attribution samples, not averages or
additive savings. Candidate follow-ups are motion blur off, directional SMRT
samples 8 to 4 if still loaded at 8, and the NVIDIA TSR 16-bit permutation.
UE 5.8 defaults `r.TSR.16BitVALU.Nvidia` to 0; Epic previously documented an
RTX 20-series driver corruption issue. Test only on the current RTX 4050,
check actual VALU=16bit event selection and image correctness, and never promote
it globally for all NVIDIA adapters from this machine's result alone.

### 1080p lighting results and restored defaults

`20261011T085456849Z-75485fe5` completed all 16 driving windows with unchanged
runtime inputs and passed the memory gate (minimum local headroom 1,538.52 MB,
no unknown or over-budget samples). All frame-time gates still fail.
Disabling diffuse GI saved 0.735 ms on the road (below its 5% screening
threshold) and 1.261 ms at the ford. Full-size images show darker vehicle
shadows/interiors. It remains a diagnostic, not a default. The 128/128 cache
cadence saved only 0.052 ms on the road and 0.093 ms at the ford. Original
diffuse GI and 32/64 lighting update factors were restored.

Read-only `MaterialAudit_20261011T092341353Z/audit-report.json` verifies all
four audited material package hashes unchanged. Landscape has 256 components,
automatic LOD (-1), zero component bias, default distribution settings and
Nanite disabled. The actual terrain graph has 101 expressions, 68 reachable
from the inspected shading/WPO/mask roots. Gravel POM is connected to the
already-tested collection, and the earlier bank texture branch is present.
Willow shaders have no WPO connection and currently lack Nanite usage flags.
The audit lists both ordinary static components and instanced tree groups;
their counts must not be equated with simultaneously visible trees.

`WaterVisual_20261011T092404349Z` passed normal-control ford traversal and
material/emission checks at native 1600x900: WakeDetailReady/FieldActive/
DetailEnabled were 1, water spray peaked at its retained 120 cap and bow rate
at 17.9 droplets/s in the 2-second samples. Chase images show disturbed water.
These paused images are not timing evidence. Inspection found the side-camera
requests remained on the previous chase POV while paused; a corrected repeat
enables full player-controller ticks during pause and asserts the camera's
actual location before accepting side images. This is a review-helper issue,
not proof of missing runtime bow waves.

### October 11 afternoon checkpoint: user confirms smoother play

The user reports that Benmore is running "much much better". Preserve the
installed improvements as the current play baseline. This feedback is not a
measured sustained-80-FPS result.

`20261011T092600978Z-4d3c7640` was interrupted: it has 12 completed windows in
`profile-progress.json`, but no final report or completed runtime-input guard.
Its completed willow visibility windows have medians
18.173/16.905/16.997/17.960 ms (reference/candidate/candidate/reference), an
approximately 1.12 ms diagnostic difference. Treat this as provisional
attribution, not evidence for installing an asset change. Instanced RT LOD2
showed no benefit. Windows Modern Standby occurred at 03:54:07 and again at
03:56:36, with intervening temperature/clock changes; the motion-blur comparison
is unsuitable for promotion. TSR 16-bit testing never completed.

New isolated willow preparation and runtime-swap helpers were written and
syntax/API inspected, but no WillowTrial package report exists: no willow
conversion was installed. The queued corrected water review, expanded static
mesh audit and rendered fine-spray check also have no new outputs. Their prior
validation limitations remain. At the afternoon checkpoint another Unreal
process is running check_deformable_gravel.py; no second editor was launched,
no build was run, and no application was closed.
