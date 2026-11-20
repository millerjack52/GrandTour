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

## Nearby painted trees and the original skyline

The 55 m experiment uses the painted Nanite meshes for the three mature species close to the camera. Beyond that distance the original renderer draws the original trees. Both representations use the same instance transforms and random seeds. The Nanite build changed the bounding centre of two meshes by 91 cm and 129 cm. The test aligns both distance checks to the original centre and encloses both sets of bounds. Unreal requires a nonzero far limit to enable the minimum draw distance. The native renderer reported the expected ranges for all three pairs, the original sapling distances, all nine scene proxies and zero fallback materials.

| Warmed deep-bog replay | Average fps | Mean frame | p95 frame | GPU shadow | GPU surface | GPU velocity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 55 m painted trees | 20.81 | 48.05 ms | 67.38 ms | 16.94 ms | 11.26 ms | 7.63 ms |
| 55 m split with original trees on both sides | 16.86 | 59.30 ms | 87.61 ms | 24.29 ms | 13.00 ms | 9.08 ms |
| Original, without the split | 17.23 | 58.05 ms | 85.30 ms | 23.34 ms | 13.14 ms | 9.10 ms |
| 55 m painted trees, repeat | 18.53 | 53.95 ms | 77.08 ms | 19.22 ms | 12.68 ms | 8.63 ms |

All four runs covered the same 11.65 m and all 17 sampled positions agreed. Thermal throttling was active. The two nearby-tree runs saved 4.10�10.00 ms in mean frame time against the original in this sequence. Both missed the frame budget. The range-split control cost 1.25 ms more than the original on this test.

Two fresh fixed-time drives used the same saved equipment and the same native build. All 65 sampled vehicle positions agreed across 240 pairs of driving frames. In the paddock the average brightness difference was 0.13 on a 255-level scale. The strongest local difference fell to 0.48, compared with 15.24 when the trial replaced all mature trees. The crown and trunk separation in the skyline returned. In the bog approach a nearby trunk shifted greener and darker. At the deep-bog checkpoint the worst difference was on grass blades. Moving tyre dust obscured the largest forest-access difference. The nearby variant remains experimental.

Reproduce with the saved profile, `-ShadowStudy basemoving -NearTreeMetres 55`. Add `-NearTreeControl` for the conventional split or use only `-WarmTrees` for the unsplit control. All runs need a unique label and `-ShadowCandidate saved`. The local film, colour crops and greyscale driving frames are in `D:/GrandTourAssets/Reviews/Lidar60/near55-route-review`.
