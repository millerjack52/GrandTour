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
