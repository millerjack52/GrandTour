# LiDAR tree geometry and shadow culling

The original three mature tree groups have a minimum conventional mesh LOD of 1. The previous Nanite copies were built from LOD0. On study-only meshes the new test extracts the built triangles, normals, tangents, UVs and material IDs from the original rendering LOD1. Unreal accepted 18,691, 22,447 and 27,432 triangles respectively. Each copy uses the same two drawn material slots and painted material inheritance as the previous Nanite test. The original tree textures, saplings and distant geometry are used in all distance-split comparisons. The 150 m run changes only the range of the near trees relative to the 55 m version.

## Matched deep-bog driving

All four standalone games repeated the same 11.65 m of simulated driving, with all 17 pickup positions matching exactly. The 192-frame measurement starts after shader warm-up and the 100-frame shadow-cache settling interval. Output is 1600 x 900 at 75% TSR. These are fixed-time, offscreen comparisons with the full map, deformable ground, water, pickup and audio.

| Trees | Mean frame | p95 frame | Average fps | Conventional base pass | Motion vectors | Shadow drawing | Nanite visibility | GPU clock |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 49.77 ms | 55.78 ms | 20.09 | 14.19 ms | 9.75 ms | 12.58 ms | 0.33 ms | 1590 MHz |
| Previous near geometry, 55 m | 44.72 ms | 47.79 ms | 22.36 | 12.79 ms | 8.65 ms | 9.88 ms | 0.87 ms | 1665 MHz |
| Playable first LOD, 55 m | 43.02 ms | 47.34 ms | 23.24 | 12.47 ms | 8.49 ms | 9.53 ms | 0.84 ms | 1665 MHz |
| Playable first LOD, 150 m | 37.05 ms | 39.52 ms | 26.99 | 7.29 ms | 4.67 ms | 8.23 ms | 2.82 ms | 1500 MHz |

At 55 m the revised geometry saved 1.70 ms against the earlier painted trees. Both tests recorded a median 1665 MHz. Extending the range to 150 m reduced the surface and velocity passes. Nanite visibility rose from 0.33 ms in the original to 2.82 ms at 150 m. Nanite surface shading rose from 0.13 to 0.43 ms alongside the reduction in the conventional base pass. Against the original, the 150 m run saved 12.72 ms of mean frame time on this replay. The original ran at 1590 MHz and the 150 m trial at 1500 MHz. Thermal throttling was active.

## Appearance at driving distance

Each film contains five six-second checkpoint drives, 240 frame pairs and 65 matched vehicle positions. Samples use the same equipment and fixed camera timing. Forest-access dust, water and individual grass blades varied across independent launches. The close trunk at the bog approach and the paddock skyline can be checked separately from these differences.

| Region | Repeat original | Earlier 55 m | Playable LOD at 55 m | Playable LOD at 150 m |
| --- | ---: | ---: | ---: | ---: |
| Paddock skyline | 0.15 | 0.15 | 0.15 | 4.97 |
| Bog approach, right trunk | 0.07 | 4.50 | 4.50 | 4.50 |
| Deep bog, grass blades | 13.68 | 3.69 | 13.90 | 3.71 |

Values are mean absolute differences in brightness on a 255-level scale at fixed native-resolution crops. The earlier geometry and revised near geometry both shifted the nearby bark greener than the corresponding original frame. A repeated original provides the independent variation in the first numerical column. At 150 m the paddock trees also changed shape. A lower crown dropped out of the silhouette, revealing a gap and darkening the treeline. The worst 96-pixel paddock patch differed by 14.23 brightness levels. The 55 m and 150 m trials both fail the appearance gate. The saved v10 profile remains active.

Reproduce the geometry from the existing painted-tree study assets by running `Art/Unreal/prepare_lidar_render_lod_study.py`. Apply `-NearTreeMetres 55 -RenderLodTrees` or `-NearTreeMetres 150 -RenderLodTrees` to the saved fixed bog replay or route film. The full comparison films and original image crops are under `D:/GrandTourAssets/Reviews/Lidar60/lod1-route-review` and `D:/GrandTourAssets/Reviews/Lidar60/lod1-150-route-review`. [Measurement record](LIDAR_TREE_RENDER_LOD_AND_SHADOW_CULLING.json).

## Which draws cost time in the deep bog

Unreal captured two graphics frames at different points in the 11.65 m bog replay, with the original trees and materials. Individual draw timers account for 17.60 of 18.12 ms in the first base pass and 17.17 of 17.80 ms in the second. The figures below are graphics work on those instrumented frames. Instrumentation and laptop clock changes affect the absolute times.

| Original draw | Frame 711 | Frame 775 |
| --- | ---: | ---: |
| Tree D 003 leaves, base pass | 9.06 ms | 8.99 ms |
| Tree D 003 leaves, velocity | 6.11 ms | 6.24 ms |
| Tree D 003 leaves, shadows | 3.09 ms | 3.07 ms |
| Other two mature leaf materials combined, base pass | 2.58 ms | 2.30 ms |
| Three mature bark materials combined, base pass | 3.06 ms | 3.17 ms |
| Fine detail material, base pass | 1.59 ms | 1.45 ms |
| Three painted fern meshes combined, shadows | 3.95 ms | 4.14 ms |

Tree D 003's leaf material alone accounted for roughly half of each base pass. This places the repeated cost on a specific material and mesh. The draw timer includes vertex processing, rasterization and pixel shading. It cannot separate those costs. The section totals include all LODs drawn with that material. The engine identifies the fine-detail draw's material but supplies no mesh name. Run the saved `basemoving` drive with `-MaterialDrawStudy` to produce the full per-material and mesh tables.

## Cause of the green bark

The pickup and camera were held at the same position and game time during four treatments. The original and fast trees each used their painted moss at its original strength of 0.52 and with that layer temporarily disabled. Each state had two settled captures. The reference patch on the right trunk was 96 × 96 output pixels. The renderer's base-colour and normal buffers were read at their native 1200 × 675 resolution.

With the painted layer active, the fast trees raised green by 5.80 levels in the lit image and 1.66 in the base colour. With moss disabled on both versions, the mean absolute RGB difference fell from 2.72 to 0.05 in the lit image and from 0.77 to 0.07 in base colour. Switching moss off had almost no effect on the original trunk at this position. The fast renderer was putting moss on a part of the trunk that the original left bare. Roughness and material occlusion matched. A small normal-buffer difference remained with moss disabled. This result isolates placement of the painted moss as the cause of this local green shift.

Use `-ShadowStudy barkbuffers -ShadowCandidate saved` for the held comparison. The original frames, ten buffer views per capture and `bark-moss-comparison.png` are under `D:/GrandTourAssets/Reviews/Lidar60/sweep74_bark_channels`.

### Using the original tree's coordinate system

A 55 m study variant computes the painted moss from the bark pixel's undeformed instance-space position and the explicit world position of that instance's origin. It keeps the original moss formula, local bounds, textures and 0.52 strength. Unreal verified the new material on all three nearby tree groups with zero material fallbacks. At the moving bog approach the trunk's green difference from the original changed from +6.436 to −0.246 on a 255-level scale. Mean absolute brightness difference fell from 4.498 to 0.399. Repeating the original gave 0.069. The paddock skyline differed by 0.144, compared with 0.153 on the repeated original. The native crops are in `D:/GrandTourAssets/Reviews/Lidar60/bark-coordinate-route-review/tree-and-grass-crops.png`.

Use `Art/Unreal/prepare_lidar_bark_coordinates.py` after preparing the playable LOD copies, then add `-BarkCoordinates` to `-NearTreeMetres 55 -RenderLodTrees`. The setting applies to the near-tree copies for that drive.

The corrected variant still fails the driving appearance check. At 5.0 seconds into forest access (frame `r140`), a sunlit gap between trunks in the upper canopy becomes dark. The fixed 96 × 96 region at (864, 40) differs by 42.48 brightness levels on this run and 42.41 on the earlier near-tree variant. Independent runs with the original trees differ by 0.35 and 0.72 in the same region. The comparison used the upper part of all 48 access frames to find differences shared by both fast-tree runs. The selected crop is clear of the truck and tyre dust. See `forest-access-crown-crops.png` beside the other bark comparison images.

In the separate 192-frame bog replay the corrected variant averaged 14.64 fps, with a 72.62 ms p95 and a median GPU clock of 1050 MHz. All 17 positions matched the original bog replay. The earlier 55 m trial ran at 1665 MHz, so these figures do not establish the cost of the bark change itself. The failed access image rules out making this version the default.

## Occlusion of moving shadow casters

The saved tree renderer was used for all three bog drives. Unreal can build a second depth hierarchy for moving shadow casters. This skips work hidden behind other casters while retaining the sun, leaf wind, shadow resolution and material programs. The logged shadow depth pool grew from 42.69 to 85.38 MiB. All 17 vehicle positions matched across three 192-frame drives. Thermal throttling was active throughout.

| Second shadow hierarchy | Mean frame | p95 frame | Shadow drawing | Average fps | Median GPU clock |
| --- | ---: | ---: | ---: | ---: | ---: |
| On | 53.91 ms | 58.37 ms | 12.15 ms | 18.55 | 1410 MHz |
| Off, saved control | 58.07 ms | 64.50 ms | 14.76 ms | 17.22 | 1335 MHz |
| On, repeat | 57.05 ms | 61.62 ms | 12.73 ms | 17.53 | 1275 MHz |

Shadow drawing improved by 2.03–2.60 ms on this fixed replay. The repeat had a lower GPU clock than the control and saved 1.03 ms over the whole frame. These three short offscreen drives establish a bog comparison only.

The moving visual comparison used 240 frame pairs and 65 matching vehicle positions across five checkpoints. Mean brightness difference was 0.14 in the paddock, 0.19 at the river and 0.18 on the bog approach, on a 255-level scale. At forest access it reached 4.64, with visibly different tyre-dust clouds across launches. The deep bog also showed variation in individual grass blades. The side-by-side film is in `D:/GrandTourAssets/Reviews/Lidar60/dynamic-shadow-route-review/lidar-route-shadows.mp4`.

### First full game-window comparison

Both games used the native player with editor scripting disabled, 1600 × 900 output, the saved 75% TSR setting, audio, driving physics and the same workshop equipment. The game window had focus throughout the 300-frame window at every checkpoint. FPS and p95 below include moving frames only, with the driver in the pickup at more than 0.5 m/s. The vehicle's actual elapsed-time trajectory can differ across these launches.

| Checkpoint | Moving frames off / on | FPS off / on | p95 frame off / on | GPU clock off / on |
| --- | ---: | ---: | ---: | ---: |
| Paddock | 298 / 298 | 19.56 / 19.72 | 67.48 / 60.59 ms | 1245 / 1140 MHz |
| Forest access | 294 / 175 | 13.20 / 14.52 | 103.75 / 78.65 ms | 855 / 930 MHz |
| River | 185 / 0 | 14.33 / unmeasured | 90.23 ms / unmeasured | 795 / 795 MHz |
| Bog approach | 137 / 0 | 11.04 / unmeasured | 101.95 ms / unmeasured | 780 / 788 MHz |
| Deep bog | 249 / 210 | 10.95 / 11.10 | 98.51 / 97.49 ms | 795 / 780 MHz |

The candidate pickup covered zero distance at the river and bog approach. Those two stationary windows cannot establish driving performance. At forest access the pickup covered 54.54 m with the original and 40.56 m with the candidate, limiting direct comparison there. Every recorded moving frame exceeded 16.67 ms.
