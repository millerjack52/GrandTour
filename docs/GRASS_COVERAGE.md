# Grass coverage study

**Revision status:** The user rejected the appearance of `grass-coverage-02`.
The original build/performance record below is historical, not visual approval.
The follow-up is documented in `GRASS_REFERENCE_REVIEW.md` and uses the recovered
environment concept images in `Art/References/Environment` as explicit targets.

The grass is in `/Game/GrandTour/ArtTests/RoadFordStyle/L_RoadFordStyle`.
This is the isolated 72 m road/ford style map, with an additional far-ground
extension. It is not yet deployed across The Hide or the other gameplay maps.

## Appearance and construction

The existing tall tussocks sit above a continuous layer of short ribbon grass.
The gravel route and water remain open. Coverage thins irregularly at shoulders
and banks, rather than stopping at a straight line. Five slope variants seat
the roots on the bank gradient; placements use deterministic jitter.

Two Blender review passes are preserved in
`Art/Export/RoadFordStyle/GrassIterations`. Pass 1 filled the banks but its broad
blades looked chunky and the boundaries were abrupt. Pass 2 narrows the blades,
feathers coverage and reduces clump size beside gravel/water. The approved road,
tree and rock assets/placements are preserved. The latest full scene is
`Art/Export/RoadFordStyle/RoadFordStyle.blend`. Reusable prototypes are also
packed in `GrassCoverage.blend` beside it, with individual FBX exports.

Source: `Art/Blender/grass_coverage.py`, invoked by
`Art/Blender/build_road_ford_style.py`. There are five shared 198-triangle meshes,
66 blades each, one material, and 9,238 new patch instances. No new textures.
The entire assembled level now has 31 source meshes and 11,919 instances.

## Runtime cost controls

- Opaque geometric blades: no alpha-tested cards or translucent blending.
- Five instanced components, one vertex-colour material.
- Collision removed from grass meshes; instances have NoCollision.
- Grass shadow casting, distance-field lighting participation and ray-tracing
  visibility disabled. Existing tree/tussock/rock settings are unchanged.
- Tiny grass meshes use conventional instancing, not Nanite. Other assets retain
  their existing Nanite settings.
- Instance fade starts at 25 m, fully culled at 42 m. A small vertex-only offset
  sinks each blade into its root height as it fades, avoiding masked overdraw.
- No wind, interaction tick, runtime spawning, or simulation on the carpet.

The coloured ground and larger tussocks provide distant coverage. Blender
review images show all modelled grass; Unreal applies the distance fade/cull.
These are finite test-map settings, not proof of cost on a region-sized map.

## Rebuild and profiling

Run `Art/road_ford_blender_preview.sh` using Git Bash for modelling/rendering,
then `Art/import_road_ford_style.sh` with Unreal closed. The import report records
grass counts, cull distances, shadow and Nanite settings.

`Art/Unreal/setup_grass_benchmark.py` creates separate On/Off map copies with a
stationary default pawn at driver height. Only new carpet visibility changes;
the test uses the same road, old dressing, camera, lights and materials.
`Art/profile_grass.ps1` runs an Off/On/On/Off sequence at 1440 x 900, DX12,
100% screen percentage, uncapped, offscreen, with CSV GPU/frame measurements.
It takes no Unreal screenshots. GPU temperature/clock state is recorded.
The existing Kuwahara pass is disabled equally in both modes because its shared
material has a known compilation issue. The other runtime look systems remain.
This isolates grass cost; it does not certify the complete driving frame budget.

## Measured result, 2026-09-28

Four cooled runs completed on the RTX 4050 laptop (Off/On/On/Off), 900 frames
each. Analysis uses frames 300 through 849: 550 steady-state samples per run.
CSV metadata verifies 1440 x 900 and D3D12. No thermal slowdown flags were
observed in the final series. The earlier 2,200-frame series reached thermal
slowdown and is explicitly excluded; its run records are retained as invalid.

| Metric | Grass off | Grass on | Difference |
|---|---:|---:|---:|
| GPU time, average of run medians | 9.347 ms | 9.014 ms | -0.332 ms |
| Opaque base pass, average of run medians | 0.012 ms | 0.305 ms | +0.293 ms |
| Game thread, average of run medians | 1.864 ms | 2.009 ms | +0.144 ms |
| Mean frame time, averaged across runs | 11.215 ms | 10.473 ms | -0.742 ms |
| RHI draw calls, median | 66 | 76 | +10 |

The grass has a measurable rendering cost of roughly 0.3 ms in the opaque pass.
No total GPU/frame regression was observed in this view. The lower totals do
**not** establish that grass improves performance or costs nothing: coverage
changes work in other passes, and standalone run timing varies. Frame-time
medians show alternating queue behaviour, so mean frame time is reported here.
This is a stationary driver-height benchmark with Kuwahara disabled, not a
moving drive test or a guarantee for all views, weather, resolutions and maps.

Evidence: `grass-performance.json`, `grass-profile-runs.json`, raw CSV files in
`GrassIterations/performance`, and `Saved/Logs/grass_cooled_*.log`.
The import succeeded as `grass-coverage-02`; the report verifies all five
components and their culling/shadow/Nanite settings. All previous 2,681 dressing
placements compare identical to the baseline. This version met the measured
cost goal, but the user subsequently rejected its appearance. Full-map
deployment still needs a representative driving profile and visual acceptance.
