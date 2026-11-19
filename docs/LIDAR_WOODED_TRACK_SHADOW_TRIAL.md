# Wooded mud track shadow trial

## Driving result

Two stock and two trial drives used matched sections of the logging track. Each row pools rendered frames across the two runs per setting. The first trial enabled the settings in a warmed session. The second enabled them when starting the game. The entry distances come from interpolating pickup position samples.

| Section | Stock shadow | Trial shadow | Saving | Stock to trial FPS | Stock to trial frame time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Track approach, first 12 m | 57.7 ms | 13.0 ms | 44.7 ms (77%) | 8.1 to 12.8 | 122.8 to 78.0 ms |
| Deep mud, first 1.5 m | 52.8 ms | 12.7 ms | 40.1 ms (76%) | 8.9 to 14.5 | 112.3 to 69.0 ms |

For the equal elapsed-time check, the first eight seconds of throttle gave the following results.

- Approach measured 8.3 to 13.2 fps. Shadows measured 57.2 to 12.9 ms.
- Bog measured 8.9 to 14.8 fps. Shadows measured 52.7 to 12.8 ms.

Across timing runs, GPU telemetry medians during throttle ranged from 87.5 to 88.5 degrees C and 1650 to 1665 MHz. Thermal and simulation variability affect individual FPS values. The GPU shadow pass shows the same large saving on each repeat.

The remaining base pass took 24.2 to 27.4 ms and the velocity pass took 16.2 to 18.0 ms. Both are candidates for the next isolation test. Sustained 60 fps requires a total frame budget of 16.7 ms.

## Visual result

The two uninterrupted takes cover 15.4 m. All nine sampled pickup positions coincide. The dappled shade across the track, the contact under the truck, the bordering foliage and the sunlit opening remain visually consistent. Across 96 moving frame pairs the average absolute brightness change in the main scene crop was 0.23 levels out of 255. In the most different frame 0.42% of the cropped pixels differed by more than eight levels. In the four separate paused same-position comparisons, the maximum was 0.013%. The HUD and screen edges are excluded from these measurements. Fine temporal differences remain. This judgment covers this chase camera, direction, day lighting and track section. A whole-route and wind-angle check is still needed before enabling the trial by default.

Detailed per-run timings, restored controls, camera checks, hardware conditions and visual measurements are in [the results file](LIDAR_WOODED_TRACK_SHADOW_RESULTS.json). The local review files are `Saved/LidarDrivingBaseline/wooded-shadow-review/wooded-mud-drive.mp4` and `matched-track.jpg` in the same directory.

## What was drawing the shadows

In the previous three-run LiDAR baseline, the wooded mud track averaged 52.0 ms in shadow depths. A separate frame capture measured 50.2 ms rasterizing non-Nanite virtual shadows in 1,404 draws. The new test starts at the same checkpoint on the saved fine-grass map, in the normal pickup and chase camera.

Disabling only the tree-group shadow casters reduced the stationary shadow pass from 33.2 ms to 4.4 ms. Restoring all casters later in that run gave 40.5 ms. The exposed ground and trunks turned sunlit. Draws changed from 1,447 to 1,418. Disabling the road and mud mesh group cut the count to 816 but left 37.4 ms of shadow work. Disabling the landscape and ground-flora groups separately produced no comparable saving. The vehicle-labeled group covered two wheel arch components. The other 29 pickup components were in the mixed remainder group, so this isolation does not give a whole-vehicle shadow cost. Groups were tested sequentially while the laptop warmed, so small differences between groups cannot be assigned to an individual asset.

Unreal reported roughly 58 requested pages, 58 static cached pages, 51 invalidated dynamic pages and about 1,895 empty pages during the first control. The page pool had capacity. Ignoring movement-driven page invalidation as a diagnostic made no improvement. Disabling the directional receiver mask made the pass slower. All those switches were restored.

The three main canopy and three sapling instance groups allow vertex displacement at unlimited distance. Their actual leaf shaders fade motion from 25 to 55 m. The bark and far impostor materials sampled in this study have no vertex displacement input. In the installed UE 5.8 shader, a caster that remains eligible for world-position offset cannot use the static cache path for that clipmap, even when its material produces zero displacement. A rigid invalidation policy alone does not change that eligibility test.

## Candidate

Set the six canopy and sapling groups' displacement cutoff to 110 m, allowing clearance beyond the leaf shader's 55 m fade for the crown radius. Set the directional shadow clipmap displacement bias to -3, which retains animated geometry on the near shadow levels and allows farther canopy shadows to be cached. Baseline shadow resolution, ray count, mesh LODs, materials, leaf wind, collision and foliage density are used throughout. The audited baseline had no shadow-casting static mesh components with an existing positive displacement cutoff. The player trial applies to the LiDAR game world for that launch.

Changing eligibility mid-session produced a misleading bright band up the track. The test therefore explicitly discarded and rebuilt the shadow cache when switching treatments for same-pose checks. Starting a fresh game with the candidate is tested separately. With a rebuilt cache at the same stationary site, shadows measured 53.3 ms initially, 12.8 ms with the candidate and 53.2 ms after restoration. A gentler clipmap bias of -1 measured 22.3 ms. Lowering shadow resolution by a full step measured 44.4 ms and multiplying the regular shadow LOD distance by two measured 41.8 ms.

## Measurement and reproduction

Standalone DX12 Unreal 5.8, saved LiDAR v7 preset, 1600x900 output, fixed TSR 75%, VSync off, 120 fps cap and normal game audio. The Ryzen 7 8845HS / RTX 4050 Laptop GPU machine ran on AC. One renderer at a time. Timing runs use normal elapsed time. Each drive uses 75% throttle. Actual pickup positions were recorded every ten frames. Each timing comparison covers the first eight elapsed seconds of throttle at the mud checkpoint and on a surveyed approach about 18 m farther back on the same logging track. The final frame crossing eight seconds is included. Travel is interpolated between position samples. Frame times are engine intervals from offscreen standalone play.

The visual take uses a separate fixed 24 Hz simulation and saves every other rendered frame for eight seconds. Both halves play at the same 12 samples per second so playback speed cannot be mistaken for a performance result. A second pass switches settings at four paused points reached by the moving pickup. The checks compare camera transform, pickup position and game time, along with baseline repeats to judge temporal noise. Near wind, truck contact, canopy shade, the bank and the sunlit opening are reviewed in the game images.

## Reviewing and repeating the test

Open `Play-LidarStudy-TreeShadowTrial.bat` in the project root to start the pickup at the wooded mud checkpoint with the trial active. For the stock comparison, run `Art/open_lidar_study.ps1 -Play -WoodedTrack`. The player launcher was also checked independently with capture and exit switches. It applied the trial to six groups at frame zero, placed the pickup at the mud checkpoint and produced the expected 1600x900 game view. Each opens a separate game session. Close the first before starting the second.

From PowerShell in the project root, use unique labels for each timing run. The profiler writes the measurement and schedule under `Saved/LidarDrivingBaseline/<label>`. After the game exits, analyze the capture with the supplied Python script.

```powershell
.\Art\profile_lidar_play.ps1 -Label woods_stock_01 -ShadowStudy drive -ShadowCandidate baseline
python Art/tools/lidar_shadow_study.py analyze Saved/LidarDrivingBaseline/woods_stock_01
.\Art\profile_lidar_play.ps1 -Label woods_trial_01 -ShadowStudy drive -ShadowCandidate tree110
python Art/tools/lidar_shadow_study.py analyze Saved/LidarDrivingBaseline/woods_trial_01
```

Use `-ShadowStudy diagnose` for the caster isolation and `-ShadowStudy rebuild` for the cache-rebuilt stationary comparisons. To recreate the footage, repeat the two driving commands with `-ShadowStudy visual` and new labels. Analyze each run, then pass the stock directory, the trial directory and an output directory to `Art/tools/compare_lidar_shadow_drive.py`. The comparison requires Pillow, NumPy and imageio-ffmpeg. Raw captures and the local side-by-side video are kept under `Saved/LidarDrivingBaseline`.
