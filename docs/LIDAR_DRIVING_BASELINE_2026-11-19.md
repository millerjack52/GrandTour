# LiDAR driving baseline, 19 November 2026

## Measured result

Across three standalone runs, 3,288 moving frames covered 225.6 seconds of sampled movement. They averaged **14.6 fps**. The median frame took 61.5 ms, p95 113.7 ms, p99 119.7 ms and the worst 255.3 ms. **99.97%** exceeded the 16.667 ms budget. The GPU averaged 66.7 ms, the game thread 10.7 ms, the render thread 13.0 ms and the RHI thread 6.0 ms. Render-thread p95 was 17.3 ms.

Of the moving frames, 3,284 exceeded 33.3 ms, 2,671 exceeded 50 ms and 407 exceeded 100 ms. These counts include consecutive slow frames. The wider throttle sample including stopped vehicles had 11,235 frames across 853.3 seconds, averaging 13.2 fps. Equal frame counts per throttle section give the slowest sections more elapsed time. The pooled result describes this sampling mix.

| Section | Travel per run, m (A / B / C) | Moving frames | Moving fps | Moving p95, ms | All throttle fps |
|---|---|---:|---:|---:|---:|
| Fine-grass paddock | 72.9 / 83.1 / 83.0 | 1647 | 18.9 | 64.8 | 18.5 |
| Forest access | 54.8 / 38.8 / 34.9 | 597 | 11.7 | 100.8 | 13.7 |
| Wooded mud track | 4.1 / 4.0 / 3.8 | 447 | 9.2 | 120.3 | 9.6 |
| River margin | 6.5 / 7.1 / 3.8 | 597 | 15.6 | 77.0 | 14.9 |
| Deep bog | 0.0 / 0.0 / 0.0 | 0 | Stationary | â€” | 12.3 |

| Run | Moving seconds | Moving fps | Moving p95, ms |
|---|---:|---:|---:|
| lidar_drive_A | 77.3 | 15.5 | 109.2 |
| lidar_drive_B | 82.5 | 14.5 | 113.3 |
| lidar_drive_C | 65.8 | 13.6 | 118.8 |

## Where the GPU spends its time

Mean GPU milliseconds across all throttle frames in each section. The surface pass draws opaque and masked materials. The velocity pass supplies motion vectors for temporal rendering. The draw count includes passes throughout the frame.

| Section | GPU total | Shadow depths | Surface pass | Velocity | Draws/frame | Primitives/frame |
|---|---:|---:|---:|---:|---:|---:|
| Fine-grass paddock | 52.3 | 15.6 | 14.3 | 9.6 | 2,945 | 3.25 million |
| Forest access | 71.5 | 31.1 | 15.1 | 11.2 | 2,591 | 2.69 million |
| Wooded mud track | 102.5 | 52.0 | 21.7 | 14.8 | 2,897 | 2.80 million |
| River margin | 66.0 | 34.9 | 10.5 | 7.1 | 2,280 | 2.61 million |
| Deep bog | 80.1 | 38.8 | 17.5 | 12.2 | 1,813 | 2.61 million |

[The machine-readable results](LIDAR_DRIVING_BASELINE_2026-11-19.json) include the full percentiles, counts over budget, raw mean GPU costs and streaming counters for both sampling methods. Per-run reports and CSVs are preserved locally.


## Test conditions

The visual baseline is the saved fine-grass LiDAR map from `97af1f1`. The test uses the normal pickup, chase camera, HUD, audio, vehicle physics, terrain deformation, grass and water. The game runs in standalone mode using the installed Unreal 5.8 editor executable with DX12. The v7 play preset sets TSR to 75%, disables dynamic resolution and VSync, and caps at 120 fps. Each starting view has a normal 1600×900 gameplay screenshot. The comparison target is 16.667 ms per frame.

The laptop runs Windows 11 build 26200 on AC power using the Balanced power scheme, with a Ryzen 7 8845HS, 32 GB RAM and GeForce RTX 4050 Laptop GPU, NVIDIA driver 616.56. The player-facing launcher is `Play-LidarStudy.bat`. This benchmark renders offscreen and reports Unreal's logical frame intervals. Display presentation, input latency and packaged-build performance need separate measurement.

| Input | SHA-256 |
|---|---|
| Saved LiDAR map | `4af178bf4c88dec6feb823daeba3b2b45e3eb1740f0ac0b8607524413f1fced6` |
| v7 quality preset | `9d6412474695435ca1cd928542ebf88ae2f957239aa027b172310b9c4938d318` |
| Loaded project module | `8ff157dea769da55488186574f5912dd934900475ad790c54be32f6920400491` |

## Route and timing

Each fresh game visits five starting points in the same order. The game settles for 500 frames per location before 75% throttle. A screenshot at +280 verifies the view. The measured interval runs from +501 through +1249. Teleports, view captures, setup and the post-drive probe dump sit outside that interval. All slow frames inside it count. The native subsystem probe starts 20 frames before throttle and ends just after release, so its averages cover a slightly wider window.

Six position samples per location establish actual horizontal progress. Each roughly 150-frame interval counts toward moving results only when the sampled endpoints are at least one metre apart. This is a coarse measure of motion. It can include wheel slip or part of a stop. Summed straight-line steps give a lower bound for travel along bends. Frame-based throttle duration produces different distances when frame rate or vehicle contact changes. Stalled sections are valuable evidence of the scene cost of a bogged vehicle. A continuous timed drive and a full river crossing need separate coverage.

All 77 hardware samples taken during throttle windows showed 97–99% GPU utilization and 85–88°C. Median utilization was 99% and median clock was 1,665 MHz. NVIDIA reported software thermal slowdown in all 57 timed-window samples with that flag available (runs B and C). Run A had a separate positive slowdown snapshot. The laptop stayed on AC power. Future comparisons should match this warmed condition.

The wooded mud track stayed at 100% of requested texture data loaded throughout its timing windows. Forest access averaged 99.7% and briefly reached 87.4%. Ordinary streaming and hitches during driving remain in the measurements. At the river, the largest individually instrumented native CPU subsystem was the water-domain update, averaging 2.2–2.6 ms per probe frame across the three runs.

Run A–C each finished normally and produced five 1600×900 game views, 30 pawn positions and 6,950 CSV frames. Runs B and C also reported a 1200×680 pooled scene-colour allocation, consistent with 75% of 1600×900 and render-target alignment. The profiler's recording folder was redirected to the local drive because its usual drive was offline. A prior startup with no CSV was excluded.

## First optimization experiment

A separate GPU event capture immediately after run C's wooded-mud timing window recorded a 99.26 ms graphics-queue frame. Shadow depths took 53.33 ms. Within that, non-Nanite virtual shadow maps took 52.47 ms. Rasterizing the shadow casters took **50.23 ms across 1,404 draws**. Culling the per-page draw commands took 2.17 ms. These are nested timings from a single frame. The same frame spent 19.76 ms in the base pass and 13.39 ms drawing opaque motion vectors.

1. Reproduce the wooded-mud view and compare cached, newly exposed and invalidated virtual shadow-map pages with the camera stationary, then moving. Attribute caster draws to the actual tree, ground-cover, terrain and vehicle components. The event tree names the rendering path but does not identify the meshes or prove a cache fault.
2. Trial one correction against the largest verified contributor. If static geometry is invalidating otherwise reusable pages, correct those bounds or update notifications. If a distant mesh or an overlapping representation is doing redundant shadow work, test that family in isolation. Preserve the moving shadow and contact of foliage close to the truck. Compare the saved starting views and a moving chase-camera clip, then repeat these drive windows at the same quality.
3. Profile the base and velocity passes next. The wooded-mud base pass by itself exceeds the entire frame budget. For motion vectors, identify costly draws and check which materials actually displace vertices. Preserve vectors where leaf wind, grass contact and vehicle motion need them for temporal reconstruction.

Run A also recorded a 255.3 ms paddock frame. The preceding logical frame contains a 247.9 ms game-thread event wait while the GPU timer remained near 43 ms. The CSV leaves the wait's owner unresolved. Record a focused CPU scheduling trace on that traversal if the hitch repeats.

## Limits and follow-up tests

The run monitors native mud, water, vehicle and grass work and keeps normal texture streaming active. Individual CPU timers overlap or nest, and GPU pass averages describe work across different frames and views. An isolated pass cost is an opportunity to investigate. It cannot be claimed as recoverable time.

Use the same pickup, views, quality preset and thermal state for candidate comparisons. For shadow changes, compare the near-contact shadows under the car and grass, moving leaf shadows, under-canopy depth and distant canopy silhouettes. For motion-vector changes, compare fine blades and leaves during camera turns for smearing, ghost trails or popping. Keep a candidate only after the measured frame saving and the visual checks both pass.

After the first controlled candidate, run a continuous foreground drive linking the open paddock, forest and water. Record presentation timing, time/distance checkpoints and repeated crossings after extended play. That test will cover high-speed streaming, successful water traversal, long-session heat and perceived smoothness.

## Reproduce

Run these from the project root with Unreal and Blender closed. Use unique labels so each capture has its own evidence folder.

```powershell
.\Art\profile_lidar_play.ps1 -DrivingBaseline -Label drive_repeat_01
python .\Art\tools\analyze_lidar_driving_baseline.py drive_repeat_01
```

For a pooled comparison, pass multiple completed labels to the analyzer. It writes per-run and pooled JSON under `Saved/LidarDrivingBaseline`, including all throttle frames, movement-filtered frames, per-location GPU passes, frame percentiles, draw and streaming counters, hitch counts and native scope costs. The launch report records the raw CSV path in `Saved_LidarDrive/Profiling/CSV`. Native probe dumps sit one directory above it. Logs, unedited starting views and GPU samples stay in each run folder. These local diagnostics include project visuals and are excluded from the source commit.
