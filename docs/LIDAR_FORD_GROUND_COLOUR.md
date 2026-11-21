# Baked ground colour variation at the LiDAR ford

The v12 LiDAR ford uses two 2048 × 2048 colour tiles for loose and packed gravel. This trial varied the brightness of the painted stones and added three scales of seamless mottling to those tiles before import. The original texture coordinates, normal maps, roughness, deformation, placement and shaders provided both comparisons. The trial existed only in the running game. Normal play uses the original gravel.

The strongest visible difference is along the narrow gravel strip beside the pickup. The upper bank still reads as a smooth green slope from the driving camera. More contrast in the gravel tile alone has limited reach. Broader moss and damp-earth patches belong in the bank's own colour treatment. [Actual Unreal comparison](D:/GrandTourAssets/Reviews/Lidar60/ford-ground-colour/ford-ground-comparison.jpg)

## Measured cost

Four fresh Unreal sessions ran the same short throttle-and-steer input at the river checkpoint, in the order shown below. Each measured 192 moving frames at 1600 × 900 with 75% TSR on the RTX 4050 Laptop. The pickup advanced 3.03–3.04 m. The largest position difference across 17 corresponding samples was 5.2 cm.

| Gravel | Mean frame | p95 frame | Mean GPU | GPU base pass | Average fps |
| --- | ---: | ---: | ---: | ---: | ---: |
| Trial 1 | 20.254 ms | 21.936 ms | 19.189 ms | 4.485 ms | 49.37 |
| Original 1 | 20.720 ms | 24.459 ms | 19.230 ms | 4.532 ms | 48.26 |
| Original 2 | 20.318 ms | 21.429 ms | 19.287 ms | 4.542 ms | 49.22 |
| Trial 2 | 20.593 ms | 22.480 ms | 19.479 ms | 4.589 ms | 48.56 |

The base pass averaged 4.537 ms with either texture. Average whole-frame time was 20.52 ms for the original and 20.42 ms for the trial. The repeats varied more than this difference. Both texture arrays reported DXT1 and 5,636,096 bytes for the full mip chain. The pilot adds zero shader samples and zero geometry. Whole-route frame pacing and other maps remain untested. [Timing data and positions](D:/GrandTourAssets/Reviews/Lidar60/ford-ground-colour/results.json)

## Reproduce the colour bake

Run `python Art/tools/bake_ground_colour_variation.py <source-colour.png> <candidate-colour.png>` for each tile. The LiDAR inputs were `Art/Export/GravelDG1/T_GV_LooseColor.png` and `T_GV_PackedColor.png` with seed 711. The tool takes an RGB or RGBA sRGB tile from any asset set and preserves its dimensions and alpha. Import the candidate with its source's compression, mip settings and colour space. Match the tile's physical scale and review it on the receiving map. The LiDAR loose-gravel variation at a 32 × 32 downsample rose from 6.09 to 18.11 levels of luminance standard deviation while mean luminance stayed at 137.65/255 in the source images.
