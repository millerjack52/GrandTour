# LiDAR visibility and canopy driving costs

LiDAR preset v10 lets Unreal test individual instances against the depth already drawn for the view. On five timed route sections it reduced average frame time and the 95th-percentile frame time. The larger gain came at forest access. The 60 fps target requires 16.67 ms for the entire frame.

## Real-time route runs

Both games started from the v9 dry-weather fix. Only the per-instance depth test differed. The optional extra occlusion queries were off. Both runs used the RTX 4050 Laptop on AC power, 1600 × 900 output, 75% TSR, game audio, the same map and the same native module. Each checkpoint includes 300 measured frames in the offscreen standalone game. The truck traveled different distances because the simulation used elapsed time. The matched-distance columns cover the same initial travel at each location.

| Section | v9 fps | v10 fps | v9 → v10 p95 frame time | Matched distance | v9 → v10 fps at matched distance |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fine-grass paddock | 25.11 | 28.77 | 45.70 → 39.92 ms | 12 m | 26.38 → 28.76 |
| Forest access | 17.03 | 24.34 | 63.02 → 47.34 ms | 12 m | 16.58 → 24.04 |
| River margin | 23.24 | 27.02 | 58.28 → 47.57 ms | 1 m | 26.99 → 29.27 |
| Bog approach | 17.06 | 20.96 | 62.01 → 53.73 ms | 2 m | 17.21 → 20.79 |
| Deep bog | 18.09 | 20.68 | 60.63 → 54.30 ms | 1 m | 18.15 → 20.59 |

Both runs reached the laptop's thermal limit. Late in the candidate run the GPU was frequently at 1575–1665 MHz. Forest access still had a 666 ms hitch (561 ms in the original). These short checkpoint drives establish a reproducible improvement. Foreground presentation, a continuous route and sustained 60 fps remain open.

## Appearance in motion

Two separate games repeated the five six-second checkpoint drives with fixed simulation time. All 65 sampled pickup positions matched. The paired video contains 240 pairs of native driving frames. It compares the previous shelter capture and visibility logic against the combined dry capture and conservative visibility changes. Forest-access tyre dust varied between games, including between two historical controls. Held views at the same game time, position and camera orientation isolated the rendering change. The mean absolute brightness difference on a 255-level scale was 0.004 at the deep bog, 0.042 at forest access and 0.193 in the paddock. Repeating the original setting gave 0.006, 0.038 and 0.198 respectively.

The largest deep-bog moving difference was a patch of fine grass. A separate historical default frame reproduced the candidate patch at the same instant. At the river margin the worst local difference followed the water edge. The tree outlines, shaded verge and vehicle contact held up in the paired views. An additional query mode removed a visible grass patch in its driving test. The preset explicitly uses the conservative mode.

An independent launch through the normal LiDAR player entry point read back the active per-instance depth test, disabled extra queries, clear weather and zero shelter captures. It used the saved v10 profile and exited cleanly. This configuration check ran offscreen.

Local review files are in `D:/GrandTourAssets/Reviews/Lidar60/route-hzb-review`. The comparison film is `lidar-route-visibility.mp4`. The previous preset is saved locally as `D:/GrandTourAssets/Reviews/Lidar60/lidar_performance_v9.json`. To recover the previous visibility policy for a controlled run, pass `-StudySettings 'r.InstanceCulling.OcclusionCull 0'`.

## Where the remaining time goes

With conservative visibility, the full bog scene took 42.67 ms of GPU time on the repeatable 11.65 m replay. Surface shading cost 12.56 ms, motion and depth 8.69 ms, and shadow drawing 11.07 ms. The first Nanite experiment opened gaps in sapling crowns. Unreal later reported that its painted materials lacked the required Nanite shader usage flag. Its 31.67 fps result includes fallback material rendering and cannot measure the cost of the intended trees. The coarser near-tree trial reached 28.25 fps and the original reached 22.88 fps. All 17 sampled truck positions agreed. The playable preset retains the original tree geometry and materials. See [the corrected painted-tree replay](LIDAR_FOREGROUND_AND_PAINTED_TREES.md).

A parked test hid the six tree groups to isolate the rest of the scene. The GPU still needed 20.17–21.62 ms. Also hiding the ground dressing brought one window to 17.03 ms, including a reduction in shadow drawing from roughly 5.2–5.6 ms to 2.62 ms. Also hiding terrain in a separate window gave 17.29 ms. Those removals change what is visible and the shadow cache. The last restored control was still rebuilding shadow pages. These figures guide further work on the canopy, ground-plant shadows and terrain. They cannot be added to predict a production frame time.

The native timings, frame-time tails, hitches and visual comparisons are recorded in [the measurement file](LIDAR_VISIBILITY_AND_TREE_COSTS.json).
