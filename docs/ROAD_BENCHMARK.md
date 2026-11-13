# Road modelling benchmark

An initial 24 m curved road study for the Mackenzie-inspired painterly style test.
This is a geometry and surface calibration asset, not an approved art target or
a finished playable leg. Review captures are made in Blender. Use Unreal later
when judging the integrated surface shader, post processing, lighting and driving.
Blender previews do not establish parity with Lumen or the game's painterly post.

## Files and rebuilding

- Source scene: `Art/Export/RoadBenchmark/RoadBenchmark.blend` (packed textures).
- Generator: `Art/Blender/build_road_benchmark.py`.
- Rebuild from the project root with Git Bash: `bash Art/road_benchmark.sh`.
- Blender outputs: `Driver_height_135cm.png`, `Road_geometry_review.png`, and
  `Surface_detail.png`, alongside nine FBX files and `manifest.json`.
- Optional headless Unreal import: `bash Art/import_road_benchmark.sh`.
- Isolated destination: `/Game/GrandTour/ArtTests/RoadBenchmark/L_RoadBenchmark`.
- Import evidence: `Art/Export/RoadBenchmark/unreal-import-report.json`.

The scripts generate their own scene and assets. Do not run the generator over
manual edits: save a separate copy first. Git ignores the blend, FBX, image and
Unreal binaries; preserve those files separately when transferring the study.
Texture download URLs, hashes and licences are in `Art/Textures/RoadBenchmark`.

## What the study contains

The road is 4.6 m wide, with a shallow crown, wheel depressions spaced for the
car's 1.568 m track, small corrugations and a gradual rise. Road and shoulder
boundaries use matching longitudinal vertices to avoid cracks. Material masks
blend fine gravel in the wheel paths into coarser gravel and olive shoulders.

The nine source meshes comprise the road, two shoulders, three angular stone
variants and three grass tufts. There are 436 placed instances: 320 small stones,
12 larger collision stones, 100 verge tufts and four centre tufts. The road and
shoulders have collision and use the existing Dirt physical material in Unreal.
Small dressing has no collision. These are draft proportions and distributions.

## Review and remaining work

Inspect at driver's height and close range, as well as from above. Judge the
readability of wheel paths, texture scale, irregular shoulders, stone silhouette,
grass density and whether the surface suggests a useful driving line. The current
study still needs artistic refinement: less uniform scattering, stronger authored
surface variation, and better grass shapes. Add regional terrain context only
after the road treatment holds up on its own.

The Blender material is a restricted-palette proxy using CC0 Poly Haven gravel
maps. The scratch Unreal material uses a simpler colour remap. Neither is proof
that the final M_GT_Painterly treatment is complete. Driving behaviour, collision
feel, performance and final in-engine appearance remain unverified.

An earlier optional Unreal capture attempt failed. Its images and capture report
are not acceptance evidence. The existing M_GT_PostKuwahara shader reported an
undeclared PostProcessOutput_ViewportSizeInverse, and the capture callback timed
out. The reentrancy fix in the optional capture helper has not been retested.
The existing M_GT_Environment also has its instanced-static-mesh usage flag off;
the isolated benchmark materials enable that flag but do not fix the shared one.

No vehicle tuning or existing level is part of this study.
