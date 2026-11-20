# LiDAR route shadow validation and base-pass isolation

The revised shadows are active in the normal LiDAR game. Across five checkpoints, shadow time fell by 67-74%. Original and revised forest-access frames agreed within the variation seen when repeating the original setting. The largest remaining base-pass cost in the deep bog is surface rendering for the canopy, particularly Flora Paint Tree D 003.

## Route measurements

One fresh game per setting on the RTX 4050 Laptop GPU. The timed runs used the saved v7 profile at 1600x900, fixed TSR 75%, ordinary audio, the normal chase camera and 80% throttle. Measurements use logical standalone GPU and frame timings. Raw captures remain in `Saved/LidarDrivingBaseline/route_time_A` and `route_time_B`. The first eight seconds at a checkpoint and the common distances below tell the same story. Each row below compares the same first portion of track, using interpolated positions.

| Checkpoint | Distance | Shadow GPU ms, original to fix | Saving | Driving fps, original to fix |
| --- | ---: | ---: | ---: | ---: |
| Fine-grass paddock | 12 m | 13.7 to 4.5 | 9.2 ms (67%) | 17.9 to 21.9 |
| Forest access | 12 m | 36.2 to 10.1 | 26.1 ms (72%) | 10.0 to 13.9 |
| River margin | 1 m | 46.8 to 15.0 | 31.8 ms (68%) | 12.4 to 20.8 |
| Deep-bog approach | 2 m | 52.0 to 14.2 | 37.8 ms (73%) | 9.3 to 13.9 |
| Deep-bog checkpoint | 1 m | 52.6 to 13.8 | 38.8 ms (74%) | 9.2 to 13.7 |

On the previously tested wooded track, two runs per setting saved 40.1 ms in the deep mud and 44.7 ms on the approach. [Wooded track trial](LIDAR_WOODED_TRACK_SHADOW_TRIAL.md).

## Visual comparison

Every short take uses a fixed 24 Hz simulation. The comparison records eight samples per simulated second for six seconds at each of five starting points. Both games use the same steering, throttle, chase camera, quality and random seed. Paired driving positions agree exactly at all 65 sampled points. The pickup traveled 19.3 m in the paddock, 37.8 m at forest access, 2.5 m at the river margin, 3.4 m on the bog approach and 7.3 m at the bog checkpoint. The separate time trials above use normal elapsed time. Each route section starts at its named checkpoint.

The largest discrepancy between independent driving takes was windblown tyre dust at forest access. At its peak 46.6% of pixels in the main scene crop differed by more than eight luma levels. The worst-location image shows the difference across the dust plume at the bottom of the view. That percentage includes independent particle variation. Holding the camera, truck and simulation time in the same game isolates the shade under that plume.

Both longer drives ran for 30 simulated seconds per setting. The paddock covered 84.95 m and forest access covered 36.45 m, with coincident pickup positions at all 61 samples on each drive. The comparison saved two frames per simulated second. At forest access the independently simulated dust plumes again differed. The crown silhouettes, lit trunks and verge shade held together on approach.

At two forest-access positions, the test paused the pickup and alternated original, trial and restored original shadows. Each switch rebuilt and settled the shadow cache. The first position includes the dust plume in front of the chase camera. The second faces sunlit trunks and shaded understory. Truck position, camera position, rotation and game time matched within the recorded tolerances. Mean absolute luma differences in the main scene crop were 0.36 and 1.11 levels out of 255. The original-to-restored-original comparisons were 0.39 and 1.25 levels. At most 0.027% of the scene pixels differed by more than eight levels in either trial comparison. Two held paddock positions also passed. The held capture ended in the river section after completing those four positions. The river and both deep-bog views are covered by independent driving takes.

## Installed default

LiDAR preset v8 sets the directional shadow clipmap displacement bias to -3. The six saved canopy and sapling groups use a 110 m displacement cutoff. The original leaf wind fades out at 55 m. The wooded-track comparison documents the cache behavior. Reloading the map in Unreal verified six component settings, all six instance counts (159,227 total), materials, wind flags, shadow casting and sampled transforms. A separate run through the normal player launcher then confirmed the six 110 m settings and the active -3 bias in the game world. The verification script only read the settings. A second launcher run with the historical switch verified all six original zero-distance settings and the original +3 bias. Both games captured the normal chase view and exited cleanly.

The normal launcher is `Play-LidarStudy.bat`. For the historical control, run `Art/open_lidar_study.ps1 -Play -StockTreeShadows`. On an installation with the previous map, run `Art/Unreal/persist_lidar_tree_shadows.py` in the Unreal editor before using the v8 profile. The migration makes a verified compressed backup, saves the LiDAR map, reloads it and checks the authored data. Rebuilding the FloraWorld tree groups also sets the cutoff. On the test machine, the verified original map backup is in `D:/GrandTourAssets/Reviews/LidarRouteShadows/MapBackup`.

Comparison video, native paired images and measurements are under `Saved/LidarDrivingBaseline/route-shadow-review`. The four raw driving capture folders retain their original paths through directory junctions to `D:/GrandTourAssets/Reviews/LidarRouteShadows/RawCaptures`. Those files were copied and hash-verified individually.

## Deep-bog base pass

The original 26.40 ms reading was the first eight elapsed seconds of a normal drive through checkpoint bog552 with the revised shadows. The pickup moved about 4.93 m. For isolation we replayed 192 simulation frames at 24 Hz, from the same checkpoint, in six fresh games. Each covered 11.65 m at 80% throttle. All 17 sampled pickup positions matched exactly. GPU timestamps measure actual rendering time. Screenshots and material draw-event instrumentation were off during the moving windows. The opening and closing default controls differed by 0.55 ms in base-pass time. These drives explain the ranking of costs in this stand of trees. The different paths through the bog preclude assigning the original 26.40 ms to individual draws exactly.

| 11.65 m drive | Mean base pass | p95 base pass | Saving against both default controls |
| --- | ---: | ---: | ---: |
| Normal scene, opening control | 21.84 ms | 24.38 ms | |
| All six tree groups omitted from surface rendering | 4.90 ms | 5.68 ms | 16.94–17.48 ms |
| Only Tree D 003 omitted from surface rendering | 10.94 ms | 12.19 ms | 10.89–11.44 ms |
| Only the overhead rain capture disabled | 17.98 ms | 18.31 ms | 3.85–4.40 ms |
| Only tree wind evaluation disabled | 22.28 ms | 24.68 ms | Within control variation |
| Normal scene, closing control | 22.38 ms | 24.82 ms | |

The tree tests suppressed main-pass draws on the selected instances and preserved their transforms, depth contribution and collision. The silhouettes are visible in the diagnostic image. Every override was temporary. The Tree D 003 result is part of the all-tree result. Some of the same trees are drawn again for the rain system, so these savings overlap. The full default GPU frame took 61.57–63.12 ms on the matched replay. A 60 fps frame allows 16.67 ms for the entire frame.

A separate parked bog capture identified the leaf material on `SM_Canopy_1`, sourced from `SM_Path_FP_Tree_D_003`. Its individually reported leaf draws totaled 6.77 ms in the 14.10 ms driver-view base pass. The same leaves accounted for 1.92 ms in the rain view's 4.72 ms base pass on that frame. These are instrumented single-frame observations. The moving table shows the corresponding independently measured costs. The rain emitter follows the player and refreshes its 512 × 512 overhead depth capture after movement or on a timer, including during the clear-weather drive. See [the capture update](../Source/GrandTour/Weather/GTRainEmitter.cpp).

In the parked component sweep, omitting all six tree groups saved 12.87 ms. Omitting fine grass saved 0.40 ms, other ground dressing 1.39 ms and the terrain group 1.22 ms against interpolated neighboring default runs. Small differences are sensitive to drift. At 50% internal render scale the tree difference was still 12.10 ms. A separate unrestricted approach attempt at this checkpoint stalled and is recorded as stationary. Only the six verified moving runs contribute to the driving table.

The next visual-preserving test is to skip the overhead capture in dry weather and check its first wet frame, shelter transitions and any consumer of the depth texture. For the larger tree cost, isolate geometry detail level and masked leaf-card coverage on Tree D 003. Compare close silhouettes, middle-distance crown density and canopy transitions in the moving chase view. The data do not yet separate vertex cost from overlapping leaf pixels or material shading.

## Reproduce the isolation

Run one fresh standalone game per case. Give each run a new label. The example measures the expensive tree variant. Replace `canopy_1` with `control`, `trees`, `rain_capture` or `tree_wind` and finish with a second control.

```powershell
.\Art\profile_lidar_play.ps1 -Label bog_variant_replay -ShadowStudy basemoving -ShadowCandidate saved -BaseFamily canopy_1
python Art/tools/lidar_shadow_study.py analyze Saved/LidarDrivingBaseline/bog_variant_replay
```

For the visual comparison, use `boundaryfilm` with `baseline` and `saved`, analyze each, then pass the two run directories and an output directory to `Art/tools/compare_lidar_route_shadows.py`. The `routefilm` mode covers five positions. The `routehold` mode rebuilds shadows at a frozen pose in the same game. For a partial held capture, supply `--held <run directory> --held-sections paddock_mid access` to the comparison.

[Full measurements, frame timings, scene hashes, hardware conditions and driving positions](LIDAR_ROUTE_SHADOWS_AND_BASE_PASS.json). The local comparison folder contains `lidar-boundary-shadows.mp4`, `lidar-route-shadows.mp4`, `forest-access-verified.jpg` and `bog-base-pass.jpg`.
