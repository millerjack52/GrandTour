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

### Fresh starts and held views

Two fresh game windows at the river covered 6.14 m and 6.11 m with the original and candidate shadow settings. The 145 and 137 moving frames averaged 20.69 and 24.47 fps. Their p95 times were 68.22 and 56.34 ms and their p99 times were 76.47 and 63.50 ms. Median GPU clocks were 1328 and 1380 MHz. At the bog approach the pickup advanced only 0.33 and 0.61 m. Ten and sixteen moving frames are insufficient for a driving tail comparison there. Use `-DriveCheckpoint river` or `-DriveCheckpoint bog_entry` with the native foreground test for a fresh start.

Ten held driving views covered two locations in each of the five checkpoints. Each switched from original shadow culling to the second hierarchy and back at the same camera transform, pickup transform and game time. Across the ten holds the largest 96-pixel patch difference was 1.71 brightness levels, against 1.90 after restoring the original. The largest mean scene difference was 1.09 on the 255-level scale. The largest fraction of any scene changing by over eight levels was 0.076%. The native comparison board is `D:/GrandTourAssets/Reviews/Lidar60/dynamic-shadow-route-review/held-pairs.jpg`. Use `-ShadowStudy shadowdepthhold -ShadowCandidate saved` to reproduce the captures.

### Forest access while moving and after settling

The sunlit patch missing in the moving near-tree film came back in the held view. With normal shadows active the mean absolute RGB difference between the two settled crops was 0.26 levels. Disabling shadows for both reduced this to 0.25. The settled base-colour and depth differences were 0.09 and 0.02. This held test installed the fast trees after the camera stopped. It cannot explain the earlier moving difference or establish visual parity. The native stills and moving crops are in `D:/GrandTourAssets/Reviews/Lidar60/bark-coordinate-route-review/forest-access-moving-and-settled.jpg`.

### Which painted leaves cost time

The original Tree D 003 geometry was duplicated for a study. Two children of the same painted leaf material gave its first and second playable detail levels independent timer names. A per-section digest matched the source positions, triangle indices, normals, tangents and UV0 at all four mesh detail levels. The game drew the original instance group through the conventional renderer. The numbers below are GPU busy milliseconds from the named leaf draws in two instrumented, moving deep-bog frames.

| Pass | First playable LOD, frames 711 / 775 | Second playable LOD, frames 711 / 775 |
| --- | ---: | ---: |
| Surface shading | 7.44 / 7.51 | 0.40 / 0.95 |
| Motion vectors | 5.06 / 5.49 | 0.24 / 0.53 |
| Shadows | 2.81 / 2.86 | 0.00 / 0.00 |

The first playable leaf section had 32,626 referenced vertices, of which 16,597 were distinct by position, normal, tangent and UV0. Its 18,912 triangles are unchanged. This identifies a candidate for reusing vertex work. These counts do not establish a speedup. To repeat the split timers, run `Art/Unreal/prepare_lidar_leaf_lod_labels.py` with the source caster audit in `GT_LIDAR_NANITE_SOURCE_AUDIT`, then add `-LabelTreeLods -MaterialDrawStudy` to the saved moving bog replay.

## Repeated shadow timing across the five checkpoints

Three independently launched games drove the same simulated route sections with shadow culling on, off and on. All 130 sampled pickup positions matched. Each run contained 300 measured frames at each checkpoint. The pickup traveled 42.31 m in the paddock, 37.23 m at forest access, 6.78 m at the river, 1.42 m on the bog approach and 17.52 m in the bog. The test kept 1600 × 900 output, 75% TSR, sound, physics, the original trees and the same saved equipment. The table shows elapsed frame times from the offscreen game. Each triple lists the original followed by the two candidate runs.

| Location | Mean fps | p95 frame time, ms | Mean shadow drawing, ms | Median GPU clock, MHz |
| --- | ---: | ---: | ---: | ---: |
| Paddock | 18.12 / 20.72 / 15.89 | 66.86 / 67.90 / 70.14 | 6.50 / 5.81 / 7.63 | 1050 / 1260 / 810 |
| Forest access | 13.85 / 14.88 / 14.39 | 83.28 / 90.81 / 82.24 | 21.29 / 18.21 / 18.61 | 825 / 908 / 810 |
| River margin | 12.72 / 16.87 / 14.32 | 104.24 / 75.91 / 88.98 | 29.02 / 14.85 / 17.82 | 675 / 780 / 630 |
| Bog approach | 11.09 / 11.51 / 10.10 | 97.59 / 107.24 / 109.35 | 24.64 / 22.12 / 25.05 | 765 / 788 / 713 |
| Deep bog | 11.13 / 11.14 / 11.11 | 99.21 / 98.20 / 99.58 | 22.19 / 18.32 / 18.63 | 795 / 780 / 765 |

Pooling the five equal-size windows gave 12.95 fps with the original and 14.23 and 12.78 fps with the candidate. Pooled p95 rose from 95.74 to 97.41 and 103.51 ms. Pooled p99 fell from 120.40 to 117.79 and 114.27 ms. Five of the 4,500 measured frames met the 16.67 ms budget, all in the deep bog. The GPU was thermally limited on AC power. The river benefit repeated even with a lower GPU clock. Deep-bog shadow work fell on both repeats, with essentially the same deep-bog frame rate. The route-wide tail result and the extra 42.69 MiB of shadow memory do not justify changing the saved v10 default.

Reproduce with `-ShadowStudy routetime -ShadowCandidate saved -WarmTrees -FixedRouteReplay` and `-StudySettings 'r.Shadow.Virtual.DynamicHZB 1'` or `0`. The measurements, including p99 by checkpoint, are under `dynamic_shadow_fixed_route` in the accompanying JSON.

## Restoring the moving patch of sunlight

Two more games repeated the paddock and forest-access drives. For the access section both rebuilt the virtual shadow maps every frame. Across 26 pickup positions their trajectories matched the normal cached films. At access frame 40 the brightness difference between original and accelerated trees fell from 41.95 with ordinary caching to 2.33 without caching. Rebuilding the shadows changed the original tree crop by 1.98 levels and the accelerated crop by 42.01. This isolates the shadow cache as a contributor to the dark patch while driving. It does not establish that all other tree differences have the same cause. Rebuilding every shadow frame is a diagnostic and carries a substantial cost.

The next 55 m variant retains caching. Three ordinary, full-range tree components cast shadows through the source geometry and painted cutouts. Separate near and far components draw the trees visible to the camera. This lets the sun keep the same casters as the pickup crosses the rendering boundary. All 146,197 original mature tree transforms are represented in the three shadow groups. The saplings use the saved rendering path. The playable map and preset have their original hashes.

In a new 240-pair driving film all 65 recorded pickup positions matched the original. The forest-access crop differed by 1.46 brightness levels with the original casters, compared with 41.95 using the earlier accelerated casters. The bog bark crop differed by 0.40, the paddock skyline by 0.15 and the close grass by 3.22. A full-frame scan against two earlier original-tree drives found its largest remaining difference in the bottom-left tyre dust at access. In the other four locations the worst 96-pixel region in excess of both repeats measured 0.18–1.08 levels. The native film is `D:/GrandTourAssets/Reviews/Lidar60/original-caster-route-review/lidar-route-trees.mp4`. The four-way cache comparison is `D:/GrandTourAssets/Reviews/Lidar60/bark-coordinate-route-review/forest-access-shadow-cache.jpg`.

Use `-ShadowStudy accesscache` for the uncached moving isolation. With `-ShadowCandidate saved`, add `-NearTreeMetres 55 -RenderLodTrees -BarkCoordinates -OriginalTreeShadows` to the normal route film or moving bog comparison to test the retained shadow casters.

### Deep-bog cost with the original casters

All 17 pickup positions matched across three 192-frame deep-bog drives covering 11.65 m. Two candidate runs bracketed the original. The mean-frame saving was 3.95 ms in the first comparison and 0.32 ms in the repeat. The GPU ran faster than the original on both. The first run had a slower p99 frame despite its higher mean fps. This is insufficient evidence for a playable default.

| Trees and shadows | FPS | Mean / p95 / p99 frame, ms | Base / velocity / shadow, ms | Median GPU clock |
| --- | ---: | ---: | ---: | ---: |
| Accelerated trees, original casters | 17.89 | 55.89 / 59.84 / 78.86 | 15.42 / 10.47 / 14.37 | 1395 MHz |
| Original | 16.71 | 59.84 / 64.45 / 70.77 | 17.44 / 12.12 / 15.10 | 1275 MHz |
| Accelerated trees, original casters, repeat | 16.80 | 59.52 / 64.02 / 69.96 | 16.70 / 11.35 / 15.20 | 1298 MHz |

### Why the leaf vertices stay separate

Tracing the active material graph found the second set of texture coordinates, UV1, connected to the painted colour atlas. That sample feeds the leaves' base colour, subsurface colour and ambient occlusion. The opacity mask uses the default UV0 and wind uses neither set. Merging vertices solely by position, tangent basis, vertex colour and UV0 would lose painted surface information. The trial stopped before replacing the source mesh.

The original index order also has little room for a conventional vertex-cache reorder. A software model retaining the last 32 referenced vertices counted 32,626 misses for 32,626 distinct vertices at the first playable leaf LOD, and 17,897 for 17,897 at the second. This is an index-locality measurement. The GPU's actual cache policy can differ. Reproduce the connected graph and counts with `Art/Unreal/lidar_leaf_inputs.py` and an output path in `GT_LIDAR_LEAF_INPUT_REPORT`.

### Forest-access tyre dust

At the 55 m range the biggest moving difference was a tyre plume in the lower left of access frame 25. Two independent games repeated the same 26 pickup positions with particle drawing temporarily hidden for the access section. The shadow cache was active in both. In the plume's 96 × 96 crop the difference fell from 77.18 to 0.16 brightness levels. The sunlit gap in frame 40 differed by 0.88 with particles hidden and 1.46 with normal particles. Across 48 access frames the largest 96 × 96 difference with particles hidden was 2.76, on the pickup body in frame 35. The normal game and the five-checkpoint comparison film include the particles. Run `-ShadowStudy accessparticles` on each tree configuration and compare the ordinary and particle-hidden pairs with `Art/tools/lidar_access_particle_comparison.py`.

### Normal game-window drives from the wet shelf

The test driver can now start from the map's ordinary fourth checkpoint, rest the tyres on the road, then steer and use the pedals. It backs off the accelerator when the wheels slip. The player vehicle, drivetrain, terrain and mud simulation keep their saved settings. The first original-tree drive covered 100.68 m and reached the end of the measured track. A fresh original-tree repeat covered 101.02 m and reached the same end. The 55 m candidate stalled after 53.90 m of total movement, including four recovery manoeuvres. Two earlier checkpoint-placement tests without grounded wheels are excluded.

All three pickups drove through the same first 40 surveyed metres between road stations 2240 and 2280. The comparison uses their first forward passage, while in the foreground driving view and moving faster than 0.5 m/s. The paths within the road and physics timing vary between runs. Road and display clocks aligned within 4.1–23.4 ms across the two section markers. One frame was excluded at each interval boundary.

| Trees | Moving frames on shared 40 m | FPS | p95 | p99 | Longest frame | GPU clock at ≥90% utilisation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 679 | 14.89 | 83.70 ms | 99.45 ms | 115.69 ms | 1140 MHz |
| Accelerated inside 55 m, original shadow casters | 688 | 13.29 | 98.24 ms | 121.57 ms | 341.74 ms | 1080 MHz |
| Original repeat | 791 | 13.05 | 94.20 ms | 117.64 ms | 167.72 ms | 1020 MHz |

Every measured moving frame exceeded 16.67 ms. The candidate's mean sits between the two originals, and its p95 and p99 were worse than both originals. The current default stays in place. Over their full deep-bog sections the two originals measured 13.96 and 12.67 fps. The saved records include per-section tails, hitches, foreground coverage, display gaps and per-10-metre comparisons. Use `-ShadowStudy linkeddrive -ShadowCandidate saved -ForegroundDrive -TargetWindow -LinkedStart bog530`. Run `Art/tools/lidar_presentation.py <run> --stations 2240 2250 2260 2270 2280` for the shared-distance measurements.

### Extending the corrected tree rendering to 150 metres

A separate 240-frame comparison kept the original trees casting shadows and extended accelerated drawing to 150 m. All 65 pickup positions matched. The original problem region on the paddock skyline differed by 0.65 brightness levels, down from 4.97 in the earlier 150 m test. The forest-access sunlight differed by 1.68 and the close bog bark by 0.40. The wider scan still found small changes to distant foliage between trunks. At paddock frame 27 its worst 96 × 96 region differed by 2.40 against 0.17 in the original repeats. At bog-approach frame 22, a small sky opening behind the trunks changed, with a 2.36 difference against 0.15 in the repeats. The native crops and footage are in `D:/GrandTourAssets/Reviews/Lidar60/original-caster-150m-review`.

## First forward passage across 95 metres

The 150 m candidate covered 109.56 m including recovery manoeuvres, then stalled about two metres short of the measured track end. Both original runs reached the end. All three pickups crossed road stations 2240 and 2335. Each comparison below includes only foreground driving frames on the first forward passage between those stations, above 0.5 m/s. The runs varied in wheel tracks, speed and GPU clock.

| Rendering | Moving frames | FPS | p95 / p99 / longest frame | GPU / surface / velocity / shadow drawing |
| --- | ---: | ---: | ---: | ---: |
| Original | 1444 | 14.03 | 87.70 / 103.06 / 146.52 ms | 69.57 / 19.39 / 14.30 / 19.68 ms |
| 150 m with original casters | 1451 | 14.99 | 82.85 / 106.86 / 176.32 ms | 64.48 / 11.78 / 8.22 / 22.40 ms |
| Original repeat | 1542 | 12.71 | 93.52 / 110.87 / 167.72 ms | 76.69 / 21.71 / 15.91 / 21.67 ms |

Nanite visibility and surface shading together cost 4.92 ms in the 150 m trial. All three runs exceeded the 16.67 ms budget on every moving frame. The mean and p95 improved against both originals, while the candidate's worst frame was longer. Its largest remaining individual GPU pass was drawing shadows. Native foliage and dust remained visible throughout. The 150 m setting stays experimental.

## Matching the tree detail level to the driving view

Five independent locations in one fixed replay measured the renderer's padded local tree bounds, actual instance transforms and camera projection at 5.875 seconds into each drive. The original detail choice depends on the projected size of a tree, which varies with its height. The counts below include bounds touching the view frustum before occlusion. They describe potential draws.

| Location | Original LOD1 within 55 m | Original LOD1 within 110 m | Original LOD1 / LOD2 within 150 m |
| --- | ---: | ---: | ---: |
| Paddock | 0 | 59 | 152 / 22 |
| Forest access | 106 | 241 | 332 / 16 |
| River | 37 | 228 | 352 / 13 |
| Bog approach | 133 | 374 | 571 / 29 |
| Deep bog | 119 | 354 | 526 / 13 |

All the counted trees inside 110 m used LOD1. No counted tree inside 150 m used the far billboard. Extending a uniform 150 m replacement puts some of the smaller trees on different geometry from the source. These counts alone cannot identify which individual leaf covers a particular output pixel. The diagnostic uses the engine's packed mesh thresholds and the active driving camera's LOD scale. Reproduce it with `-ShadowStudy routetime -ShadowCandidate saved -WarmTrees -FixedRouteReplay -TreeSizeAudit`.

A further study splits the visible trees using each instance's original bounds and the current chase-view projection. It rounds each transition down to the next 10 m interval and caps the experimental range at 210 m. The original renderer chooses the geometry beyond that interval. Full-range original shadow casters still cover all 146,197 mature trees. The native bog run verified 33 distance groups, 69 visible renderer proxies and zero fallback materials. Every instance keeps its source placement and random seed. Use `-SizeMatchedTrees -NearTreeMetres 210 -RenderLodTrees -BarkCoordinates -OriginalTreeShadows` with a saved driving comparison. Other camera modes and view sizes require independent validation.

The size-based trial finished the real wet-shelf drive, covering 100.82 m without a recovery manoeuvre. Across the shared 95 m it measured 14.67 fps on 1,410 moving frames, with 84.84 ms p95, 104.24 ms p99 and a 136.17 ms maximum. The two originals measured 14.03 and 12.71 fps. Every moving frame exceeded the 60 fps budget. In the candidate the surface pass cost 11.03 ms, velocity 7.90 ms and shadow drawing 23.39 ms. The GPU took 65.78 ms and the game thread 10.80 ms. The separate 192-frame fixed bog replay measured 23.81 fps with 50.35 ms p95. The moving game-window measurements determine the result for this road.

The 240-frame film matched all 65 original pickup positions. In the paddock frame-27 foliage patch the size-based version reduced the difference from 2.40 to 0.40 levels. The original repeat differed by 0.16. The small sky opening at the bog approach still changed. The patch differed by 2.52 levels, against 2.36 with the fixed range and 0.14 in the original repeat. The close grass difference of 13.69 was comparable to the original repeat's 13.68. The four-column image at `D:/GrandTourAssets/Reviews/Lidar60/size-matched-review/sky-and-ground.jpg` shows the two original runs, fixed-range trial and size-based trial. The remaining crown difference and frame times keep the size-based trial outside the saved configuration.

A second launch on the same build with the original trees reproduced all 17 pickup positions in the short bog replay. It measured 14.74 fps with a 67.84 ms mean and 73.43 ms p95. The size-based trial measured 23.81 fps with a 42.01 ms mean and 50.35 ms p95. The GPU ran at median clocks of 1125 and 1470 MHz respectively and reached 89 �C in both runs. The 95 m game-window trials above show the smaller gain under normal driving.

All five sections of the size-based film were also scanned for local differences using overlapping 96-pixel squares. The forest-access maximum fell on a tyre cloud. Away from forest access the largest excess over the two original controls was 2.38 brightness levels in the same bog-approach opening. The 30-second film and the five-location crop sheet are in `D:/GrandTourAssets/Reviews/Lidar60/size-matched-review/`.

A separate particle isolation used the fixed 150 m version and original trees at 26 matching pickup positions. In forest-access frame 137 the bright tyre cloud differed by 80.52 levels during ordinary driving and 0.23 with particles hidden for the diagnostic. The frame-140 sunlit gap differed by 1.68 and 0.88 respectively. Across all 48 isolated forest-access pairs the largest 96-pixel patch differed by 2.17. This experiment isolates the fixed-range version. The size-based film retained the normal particles.

## Replacing the full-range shadow casters

The original mature trees use different meshes as they recede. This trial gave the three species a full-range Nanite shadow copy of their first playable mesh. It kept the visible size-based trees, original far appearance materials, 146,197 mature tree placements and the pickup's chase camera. Unreal verified the three new shadow proxies and their painted materials on the render thread. Both shadow modes used identical pickup positions at 17 points in the 11.65 m bog replay.

| Bog replay | Mean fps | Mean / p95 / p99 frame, ms | Base / velocity / shadow, ms | Median GPU clock |
| --- | ---: | ---: | ---: | ---: |
| Original shadow geometry | 20.83 | 48.01 / 53.15 / 61.61 | 7.76 / 4.88 / 16.19 | 1245 MHz |
| New full-range shadow geometry | 26.72 | 37.43 / 51.28 / 53.22 | 7.71 / 4.90 / 4.65 | 1320 MHz |

The foreground pickup crossed the same 95 m from road station 2240 to 2335 in both modes. With original shadows it averaged 14.67 fps, with p95 at 84.84 ms and p99 at 104.24 ms. With the full-range shadow copy it averaged 20.68 fps across 1,586 moving frames. The mean took 48.35 ms, p95 took 62.08 ms, p99 took 75.34 ms and the maximum reached 146.92 ms. Mean shadow drawing fell from 23.39 to 5.86 ms. The full-range trial travelled 112.17 m including reverse manoeuvres and stalled at road station 2337.12, about 3.4 m short of the measured route end. Every moving frame on the shared stretch exceeded the 16.67 ms budget.

The 240-pair film reproduced all 65 pickup positions. In paddock frame 19 a 96-pixel patch on the distant crowns differed by 17.25 brightness levels between the two shadow modes. The canopy became visibly darker. The original shadow geometry preserved the sunlit crowns at that distance. This visual failure rules out the full-range version as the playable default. The crops are in `D:/GrandTourAssets/Reviews/Lidar60/stable-nanite-shadow-review/early-sky.jpg`. The separate forest-access dust cloud varies across ordinary launches.

## Longer original drives

Two fresh foreground runs used the saved forest, pickup, grass, water, mud physics and 1600 × 900 camera. The wooded-track drive used the player's First Hollow checkpoint. It physically travelled 35.12 m with three attempts to reverse out, reached road station 1926.85 and stalled. Across its first uninterrupted 20 m between stations 1905 and 1925 the 309 moving frames averaged 14.63 fps. The p95 was 88.04 ms, the p99 was 108.08 ms and shadow drawing averaged 18.90 ms.

The Riverside access drive physically travelled 934.88 m and reached station 1681.42. An earlier original run reached station 1681.32. On the same first forward 850 m between stations 800 and 1650, the new run averaged 11.93 fps over 2,777 moving frames with p95 at 115.26 ms and p99 at 133.88 ms. The earlier run averaged 14.44 fps over 2,773 moving frames with p95 at 98.39 ms and p99 at 110.12 ms. All 3,457 presentation samples of the new run retained window focus. Both pickups stalled before the end of Riverside access at station 1695.78. Neither run crossed the 14.75 m gap to the start of the separate logging road.

### Testing the original far shadow distance

The runtime mesh audit read the section flags on all three source trees. Both real mesh levels cast from both bark and leaves. Each far billboard has eight triangles and its shadow flag is off. The distance experiment used the source renderer's padded bounds, per-tree size and chase-camera projection to approximate that final transition in 5 m increments. It verified 111 shadow groups spanning 225–420 m, all 146,197 mature trees and zero fallback materials.

The 11.65 m bog replay averaged 26.33 fps with a 37.98 ms mean, 40.79 ms p95, 41.83 ms p99 and 4.66 ms for shadow drawing. The GPU reached 89 °C at a median 1170 MHz. The movie matched all 65 pickup positions across five checkpoints. Matching the cutoff made almost no difference to the lost sunlight. In paddock frame 19 the full-range and bounded trials both differed from the original by 17.40 brightness levels. In frame 27 they differed by 14.19 and 14.18. The original-shadow version differed by 1.00 and 0.91 in those same patches. This rules out the missing final distance cutoff as the sole explanation. The native comparison is in `D:/GrandTourAssets/Reviews/Lidar60/matched-shadow-review/shadow-distance-driving.jpg`.

Two instrumented frames with the bounded shadow trial had conventional base passes of 7.10 and 9.38 ms. Tree D 003's remaining conventional leaves took 0.85 and 1.78 ms, down from roughly 9 ms in the earlier instrumented original. The fine ground-detail material took 1.49 and 1.74 ms. Nanite visibility and surface work are separate from those conventional draws. The physical foreground result for the full-range experiment and the visual failures of both shadow variants remain the basis of the default decision.

Use `-StableNaniteShadows` on the size-matched tree trial to reproduce the full-range case, or add `-MatchShadowRange` to reproduce the bounded case. The baseline measurements above used the original playable v10 profile.
