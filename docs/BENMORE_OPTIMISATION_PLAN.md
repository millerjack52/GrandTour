# Benmore Gaea review: optimisation plan

2026-10-10. Target map `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`
(the "Gaea review" level). This plan sits beside the other worker's
[BENMORE_PERFORMANCE_AUDIT.md](BENMORE_PERFORMANCE_AUDIT.md) and uses its
captures; it does not rewrite that document. Machine: RTX 4050 Laptop 6 GB,
Ryzen 7 8845HS, UE 5.8.0, DX12 SM6, Substrate, hardware Lumen, VSM, TSR.

## 1. What the captures say

Evidence: the one quiet stationary Ford capture
`Art/Export/BenmoreGaea/PerformanceRuns/20261010T183715641Z-a3afccf7`
(PIE, 1440x902, 100% screen percentage, 429 CSV frames) and its 224 MB
`timing.utrace`, exported headlessly with Unreal Insights (game, render and
GPU tracks, trace seconds 98-112, 402 frames). Also the memory dump in run
`20261010T184104341Z-836ce089` and the invalid shadow-pool run
`20261010T210112917Z-be6e0198`. Stationary, editor-inclusive, one camera:
driving numbers will differ, but the causes below are structural.

| Thread | Median per frame | Of which |
| --- | --- | --- |
| Frame | 36.6 ms (p95 42.6) | GPU-bound |
| GPU | 34.7 ms | table below |
| Game thread | 16.8 ms | 18.0 ms waiting for render/GPU; ~13 ms own work (section 2) |
| Render thread | ~12 ms work | 22 ms waiting on GPU |
| Local video memory | 5179 MB used / 5045 MB budget | over budget every frame |

GPU scopes per frame (exclusive, from the trace; CSV medians agree):

| GPU work | ms | Note |
| --- | --- | --- |
| Mesh draws (ParallelDraw) | 9.1 | CSV: Prepass 3.3, Basepass 5.0, ShadowDepths 1.4 |
| Lumen MeshCardCapture | 7.9 | 24.8 card captures every frame while nothing moves |
| TSR (Epic) | 2.6 | 200% history |
| Volumetric cloud shadow + cloud | 2.8 | already switched off in config, unmeasured since |
| RenderGraph misc | 1.9 | |
| Lumen GI (DiffuseIndirectAndAO) | 1.3-1.6 | GI is running (the audit's 0.02 ms gather was a sub-scope) |
| Shadow projection | 0.8-1.0 | |
| VSM page management | ~0.9 | Build / InitializePhysicalPages / MarkPages / PageAllocation |
| Lumen reflections (+ water) | 0.6 | |
| Slate UI | 0.4 | editor |
| Ray tracing scene + dynamic geometry | 0.3-0.6 | 12 skeletal cars refit every frame |
| Water (SLW prepass + draw) | 0.7 | |

The invalid shadow-pool run is still informative: with local memory 522 MB
over budget the frame was 60.7 ms and "GPU/Unaccounted" was 22 ms. Being
over the video memory budget roughly doubles the frame; that is the
"atrocious" experience, not a single expensive pass.

## 2. Causes, ranked by expected gain

### C1. Lumen surface cache churns on landscape grass (about 8 ms GPU)

24.8 Lumen card captures per frame, every frame, stationary. With hardware
Lumen a primitive is in the Lumen scene when it affects dynamic indirect
lighting AND is visible in ray tracing (engine `UpdateVisibleInLumenScene`).
The landscape grass components leave both at their defaults (true, true;
runtime inventory in the run's profile-report), so tens of thousands of
tussock instances get surface-cache cards inside the 200 m Lumen view
distance and the atlas never settles. The authored composition instances are
mostly excluded already (visible_in_ray_tracing False), except 2,400
Straw/Rust at 330 m and 240 scrubs. The software-tracing A/B in the audit
(LumenSceneUpdate 10.3 -> 0.19 ms, frame -22%) is this effect: software
Lumen needs distance fields and the grass has affect_distance_field_lighting
False, so the grass simply drops out of the Lumen scene.

### C2. Video memory over budget in PIE (about 1 GB recoverable; up to 20 ms)

From the resource dump: Nanite streaming pool 528 MB while Nanite root data
is 0.8 MB (the only Nanite content is four scrub meshes); VSM physical pools
2 x 512 MB (+2 x 85 MB HZB) at 4096 pages with a median 919 pages in use
(2048-page trial now in config, unvalidated); virtual-texture physical pool
255 MB; Lumen atlases about 700 MB listed; ray-tracing acceleration
structures 340 MB (twelve fleet cars at 137k-427k triangles each are the
bulk); TSR history 128 MB; GPUScene instance data 2 x 48 MB; RT_TrackPaint
32 MB; four uncompressed 2736x2554 site textures 27 MB each.

### C3. Spray, clump and rain pools recreate their render state every frame

`BatchUpdateInstancesTransforms(..., bMarkRenderStateDirty=true, ...)` in
GTSprayComponent.cpp (lines 540, 587), GTSprayArt.cpp (359, 411) and
GTRainEmitter.cpp (333, 337) ends in `MarkRenderStateDirty()` in UE 5.8
(InstancedStaticMesh.cpp 4530): a full proxy destroy/create. Trace: 74 batch
updates, 98 ISM bounds recomputes (0.57 ms), 63 streaming notifies and 221
GetUsedMaterials per frame on the game thread; RemovePrimitiveSceneInfos 0.43
ms plus swap/add on the render thread; GPU scene re-uploads; and because the
pools are Movable, affect indirect lighting and are visible in ray tracing,
each recreate invalidates Lumen cards and ray-tracing instances. The engine
sphere/plane meshes have distance fields, so this churn also survives
software Lumen. UE 5.8 already tracks per-instance changes
(`FPrimitiveInstanceDataManager::TransformChanged` marks the component's
render instances dirty), so the flag can simply be false.

### C4. Twelve parked fleet cars tick as if driven (3-4 ms game thread)

Per frame: 12 car ticks running all 15 component updates (about 3 ms
inclusive), 32 winch cable simulations (0.38 ms), 14 chase spring arms doing
collision sweeps, 38 vehicle skeletal mesh ticks (0.76 ms), 26 Niagara wheel
spray systems, 21 skin-cache dispatches and a ray-tracing BLAS refit for every
car. End-of-frame render updates are 2.0 ms largely from the same cars.

### C5. Editor overhead inside PIE (5-6 ms game thread, duplicated memory)

Slate prepass/paint/invalidation 4.5-5 ms, typed element data storage and
Mass 0.9 ms, the editor world ticking the landscape subsystem a second time,
SlateUI 0.4 ms GPU, and duplicated render pools in the dump. A standalone
game (`-game`) does not pay these. Performance judgements should be made in
standalone, with PIE as the convenience.

### C6. Landscape grass tick (1.4 ms, two worlds) and dressing draw cost (about 10 ms)

`ULandscapeSubsystem::Tick` + `UpdateGrass` cost 1.4 ms per frame while
stationary (0.7 ms in one world); `grass.TickInterval` exists. The draw cost
is instance-count driven: SceneCulling reports 0.6-1.25 M static instances
(five grass types at 350/70/55/35/6 per 100 m2, halved by DensityScale, cull
66-570 m, all casting shadows; plus 90k authored instances). The tussock
meshes are 2,660/896/336 triangles (Fine 600/200/80); the far LOD3 candidates
(48/24 triangles) exist in `Art/Export/BenmoreGaea/FarTussockTrial_20261010_v2`.

### C7. TSR at Epic (2.6 ms) and the terrain pixel cost (inside Basepass 5.0 ms)

Both are look decisions: TAA or TSR with 100% history, and the landscape
material (parallax mud, gravel PBR, painterly, ground detail) judged with the
shader-complexity view.

## 3. Stages

One agent per stage, one conceptual change each, everything reversible, no
Unreal launch while another editor or build holds the slot
(`Art/wait_unreal_free.ps1`). Timing runs happen in a quiet window; the
other worker's runner `Art/profile_benmore_rendering.ps1` (Isolation / Memory
/ Candidate modes) is the measuring tool, with the CSV + Insights export
described in section 4 as the attribution tool.

### BO1 Lumen scene membership (config + script, no code)

- `r.LumenScene.SurfaceCache.MeshCardsMinSize` from 10 to a value that drops
  grass clumps and spray spheres but keeps shrubs, rocks, willows and the
  landscape (start at 150; the threshold is the square of this in cm2 per
  card face). Provisional line in DefaultEngine.ini SystemSettings, commented.
- Script: set visible_in_ray_tracing False on the 2,400 Straw/Rust (330 m) and
  the 240 RT-visible scrub instances (GTVegetationSubsystem components in the
  review map), matching the rest of the dressing.
- Fallback only if captures remain high: `r.LumenScene.SurfaceCache.CardCapturesPerFrame`
  100 (caps cost, leaves stale cards).
- Gate: MeshCardCapture under 1 ms per frame and LumenSceneUpdate under 2 ms
  at Ford, Long_Vista and Lake_Mouth; water reflections unchanged to the owner
  (compare against `TracingMode_1.png`); no black patches on shrubs or banks.
- Expected: -7 to -9 ms GPU. Rollback: remove the CVar line, restore the flag.

### BO2 Pools stop recreating their proxies (code, builds on the uncommitted gt.Spray.SparseUpdates change)

- GTSprayComponent.cpp 540/587, GTSprayArt.cpp 359/411, GTRainEmitter.cpp
  333/337: `bMarkRenderStateDirty` false. GTSprayArt.cpp 494 and
  GTGravelStones.cpp 507/556: `MarkRenderStateDirty()` -> `MarkRenderInstancesDirty()`
  (custom data changed with the no-dirty overload is flushed by the same path).
- At pool creation (GTSprayComponent.cpp ~95, GTSprayArt.cpp ~224,
  GTRainEmitter.cpp ~110, GTGravelStones.cpp ~96): bAffectDynamicIndirectLighting,
  bVisibleInRayTracing, bAffectDistanceFieldLighting and bReceivesDecals false.
- Gate: spray, clumps, rain and pushed stones still move and tint (look,
  parked / spraying / draining / refilling, `gt.Spray.Art` on and off);
  RemovePrimitiveSceneInfos near 0 while spraying; the spray/audio and
  water regressions in Art/suite.sh pass; build with Unreal closed.
- Expected: -0.7 ms render thread, -0.8 ms game thread, no Lumen or RT
  invalidation from effects. Rollback: revert the patch.

### BO3 Parked cars go quiet (code)

- A "parked" state in AGTCarPawn: not player-controlled and the Chaos body
  asleep. Parked: actor tick interval 0.25 s with only Condition/Environment/
  Body state updated; ChaseArm tick off; winch cable tick off while stowed
  (GTWinchComponent.cpp 42); Niagara wheel spray deactivated; skeletal mesh
  tick off (physics asleep, bones static); restore everything on possession
  or when the body wakes. Optional measured extra: bVisibleInRayTracing false
  while parked (removes the per-frame BLAS refit; changes the car's own
  reflection in water).
- Gate: TickActors + EndOfFrameUpdates fall by at least 3 ms with 12 cars;
  "Get in" / exit-and-reenter on every fleet car still passes
  (`Art/Export/BenmoreFleet/Driving/runtime-report.json` checks); no handling
  change.
- Expected: -3 to -4 ms game thread, -0.3 ms GPU.

### BO4 Video memory under budget (config)

- `r.Nanite.Streaming.StreamingPoolSize=128` (0.8 MB of root data; watch
  the log for Nanite streaming-pool warnings).
- Keep `r.Shadow.Virtual.MaxPhysicalPages=2048` and validate it: VSM/FreePages
  minimum above 0 after warm-up, no missing shadows while driving.
- `sg.AntiAliasingQuality=2` or `r.TSR.History.ScreenPercentage=100` (-63 MB,
  about -1 ms; grass shimmer is the thing to look at).
- Find what allocates the 255 MB virtual-texture pool (`stat virtualtexturing`
  / VT pool listing); if nothing in the level streams VT, lower
  `[/Script/Engine.VirtualTexturePoolConfig] DefaultSizeInMegabyte` from 256.
- Gate: GPUMem/LocalUsedMB at or below 85% of the budget with 512 MB headroom
  at Ford, Long_Vista and Lake_Mouth, and through a 10-minute drive.
- Expected: about -1 GB in PIE (Nanite 400, VSM 512, TSR 63); the 20 ms
  paging penalty disappears.

### BO5 Grass tick and dressing draw cost (config + assets, owner look gate)

- `grass.TickInterval=4`.
- Grass types: bCastDynamicShadow false on DistantTussock, TallClumps and
  ShaggyTussock (the painterly look does not read 200-570 m grass shadows);
  install the LOD3 far clumps from FarTussockTrial v2; re-judge LowGrass
  density (350/100 m2 before the 0.5 scale) and the 570 m DistantTussock
  range from a moving camera.
- Measure per family with the runner's Isolation mode before and after.
- Expected: -2 to -4 ms GPU, -1 ms game thread. Gate: owner drives, no
  visible pop.

### BO6 Standalone measurement (no change)

Run the Ford/Long_Vista/Lake_Mouth captures and one drive in `-game` with the
same settings. This separates C5 and is the number the player gets.

### BO7 Lumen decision (owner, after BO1)

If Lumen still costs more than the 120 fps budget allows (GI 1.6 + reflections
0.6 + radiance cache + residual captures), A/B three looks on the water and
the banks: hardware Lumen with BO1; software Lumen (`r.Lumen.HardwareRayTracing=0`,
measured -22% frame in the audit); no Lumen (`r.DynamicGlobalIlluminationMethod=0`,
`r.ReflectionMethod=2`, `r.RayTracing=False`, which also frees the 340 MB of
acceleration structures and the per-frame RT scene work).

### BO8 Terrain shader and anti-aliasing (later, look decisions)

Shader-complexity pass on M_Gaea_Terrain and the water; TAA versus TSR.

## 4. Expected outcome and the 120 fps question

| State (Ford, stationary) | GPU | Game thread | Frame |
| --- | --- | --- | --- |
| Measured now (PIE, clouds on, 4096 pages) | 34.7 | 16.8 (18 waiting) | 36.6 ms |
| After BO1-BO4 (no look change beyond grass leaving the Lumen scene) | ~22 | ~12 PIE / ~7 standalone | ~22 ms, 45 fps |
| After BO5, BO8 | ~15-17 | | 60 fps plausible |

120 fps (8.3 ms) is not reachable with this scene content on this GPU at
1440x900 with VSM, Lumen and the current dressing density. It needs roughly
half the pixel cost (TSR upscaling from 60-70% screen percentage, no Lumen)
and a third of the dressing draw cost (far clumps as cheap LODs or cards,
shorter grass ranges, fewer instances). Those are owner decisions about the
look, so they are not staged here.

Measurement notes for whoever runs the window: the engine slot must be free
(`Art/wait_unreal_free.ps1`), the GPU quiet (no Ace7Game/GoWR; nvidia-smi
under 10% before launch) and cool (the captures above ran at 88 C). The
headless Insights export used here (no editor needed):

```
UnrealInsights.exe -OpenTraceFile="<run>/timing.utrace" -NoUI -AutoQuit -log -ABSLOG="<out>/i.log" -ExecOnAnalysisCompleteCmd="TimingInsights.ExportTimingEvents <out>/events.tsv -threads=GameThread,Render*,GPU* -columns=* -startTime=<s> -endTime=<s>"
```

Run it from a .cmd file so the quotes land after the `=` (a Git Bash quoted
argument is re-quoted in front of the dash and the command is silently
ignored). Thread names are `GameThread`, `RenderThread 0`, `GPU0-Graphics0`;
`TimingInsights.ExportThreads` and `ExportTimers` give the id tables.
