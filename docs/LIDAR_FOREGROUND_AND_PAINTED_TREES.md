# Foreground LiDAR driving and painted-tree rendering

The saved v10 profile missed the 16.67 ms frame budget at each of the three usable foreground driving checkpoints on the RTX 4050 laptop. The 143.871 Hz desktop was active and the swap chain reported 1600 × 900 throughout. TSR used the saved 75% setting. These are short checkpoint drives with normal audio and vehicle physics.

| Checkpoint | Distance | Engine fps | Engine p95 | Engine p99 | Longest frame | Observed display fps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fine-grass paddock | 41.02 m | 35.55 | 34.54 ms | 59.11 ms | 79.39 ms | 35.37 |
| Forest access | 37.04 m | 29.68 | 40.00 ms | 41.97 ms | 49.87 ms | 29.70 |
| River margin | 6.45 m | 28.12 | 46.18 ms | 57.56 ms | 648.84 ms | 27.92 |

The game window had focus for all 300 samples per checkpoint. The display column uses intervals between consecutive observed presentation IDs. The paddock and river observations each had one discontinuity. The forest access window had complete coverage after removing eight boundary frames per end. The median observation cost was 16.5 microseconds. The workshop opened during the final two checkpoints and the vehicle stopped. Those windows are excluded. A separate continuous drive on the wooded track stalled after 4.27 m of net road progress. The truck had four wheels in contact at the median and was moving faster than 0.5 m/s in only 26.1% of telemetry samples.

An earlier launch using the same nominal resolution opened at 1280 × 720 because of saved window settings and desktop DPI scaling. Test the actual target with `Art/profile_lidar_play.ps1 -ForegroundDrive -TargetWindow -ShadowStudy routetime -ShadowCandidate saved -Label <unique-label> -EvidenceRoot <folder>`. The runner checks the actual viewport. Process the output with `Art/tools/lidar_shadow_study.py analyze <run-folder>` and `Art/tools/lidar_presentation.py <run-folder>`. Native presentation sampling also records possession, workshop state and vehicle speed in newer captures.

## Painted-tree test

All three mature tree species used duplicate materials with the full source instance inheritance, two-sided leaf shading, painted colours, wind and original textures. Only the copies enable the Nanite shader usage. The saplings used the original meshes. After shader warm-up Unreal confirmed six live tree groups, three Nanite groups, all six drawn Nanite sections bound to their intended materials and zero material fallbacks. The original Nanite trial used fallback materials and lacked this check.

The corrected mature-tree replay covered 11.65 m at the deep-bog checkpoint, 192 measured frames and 17 sampled pickup positions. It reached 50.51 fps with 21.10 ms p95. GPU work averaged 18.83 ms, with surface shading at 2.44 ms, motion vectors at 1.39 ms and shadow drawing at 4.68 ms. The conventional replay from an earlier thermal cycle reached 20.98 fps. Shader warm-up and GPU clock differed, which prevents attributing that entire difference to the trees.

Five fixed-time drives produced 240 pairs of images and 65 matching pickup positions. A distant paddock crown opened up and its trunks darkened. The worst 96-pixel paddock patch differed by 15.24 brightness levels out of 255. Forest-access dust and a fitted snorkel on the comparison truck also affected the image differences. Changing all mature trees fails the appearance gate. The playable profile retains the original trees.

To reproduce with locally installed art, run the Unreal Python asset preparation scripts `prepare_lidar_tree_gpu_study.py` and `prepare_lidar_nanite_paint_study.py` in order. For the second script set `GT_LIDAR_NANITE_SOURCE_AUDIT` to a conventional saved-route caster inventory. Then run the profile script with `-ShadowStudy basemoving -ShadowCandidate saved -BaseFamily mature_tree_paint`. The same options with `-ShadowStudy routefilm` capture the drive. Local comparison footage is under `D:/GrandTourAssets/Reviews/Lidar60/painted-route-review`.

The [measurement file](LIDAR_FOREGROUND_AND_PAINTED_TREES.json) includes per-section frame-time tails, presentation gaps, GPU timings, map and profile hashes, and the stalled continuous-drive record.
