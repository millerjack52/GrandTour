# Physical relief on the LiDAR riverbanks

The first gravel colour trial moved no ground. The attractive fitted bank occupies approximately 22 × 16 m. Extending that mesh and its planting down the river would increase the amount of scenery to store and render. Instancing can group draws, while visible triangles, masked foliage and shadow casters still cost time.

## Terrain treatment

The candidate reshapes the existing landscape grid during authoring. The inputs are an ordered river course with water levels, the terrain heights, a river occupancy mask and a protected-area mask. It follows bends and treats the two banks independently. Broad shelves taper along the river, hollows sit below their lips, and uphill shoulders blend into the original landform. The slope across the bank determines how much earth to cut or raise. The same seed reproduces a section when building the entire river.

The LiDAR adapter protects the wet footprint, the attached gravel point, fitted bank skin, ponds, road corridors and existing physical road tiles. This keeps ford depths, authored bank sections and wheel-contact terrain out of the bake. The pilot uses the existing 1.835 m vertex spacing. Its forms are several metres across. The heightfield has the same dimensions and encoding. The process adds no actors, triangles, material samples or per-frame generator. Changed silhouettes, occlusion and shadow coverage can still change measured frame times.

## Evidence

The original heightfield was reconstructed from the open Unreal level. Its MD5 matched the engine's native terrain readback across all 2017 × 2017 vertices. The local Place inputs came from the archived staged preparation ending in b3e07b7b-635d-4333-addc-2ed21209dd67 and the road-tile and fitted-mesh bounds came from the open map. Check the current water and road inputs again before installing a permanent change.

| Check | Result |
| --- | --- |
| Both sides of a continuous 380 m pilot, stations 3140–3520 m | 2,859 existing vertices changed, 1,380 on one side and 1,479 on the other. |
| Physical amplitude | Median absolute change 20.5 cm, 90th percentile 64.1 cm. Range −61 to +162 cm. |
| Protected vertices | Every protected and wet vertex kept its original encoded height. |
| Transfer and repeatability | Two grid spacings passed a curved-channel regression test. Repeating the LiDAR bake reproduced its encoded deltas. Baking the 7.13 km course changed 69,074 existing vertices. The interior of the pilot matched the whole-course result. |
| First iteration in Unreal | Partial. The initial terrain import passed native readback. Fixed views of the opposite bank and next bend showed too little change on the visible slope. The revised bake brings the shelf toward the lower bank and uses the local slope. |
| Revised geometry | Cross-sections from the encoded original and revised heightfields verify a changed bank profile. The gameplay appearance, plant contacts and terrain LOD transitions still require a drive. |
| Performance | Unverified. The stock pickup travelled 5.7 m in Play in Editor. A separate game started during testing, leaving about 1 GB of commit headroom. The session ended before the candidate drive. The gravel colour timings apply only to the earlier colour trial. |

## Run the candidate

`Art/lidar_place.ps1 -Mode BankReliefPreview` uses the installed editor, the existing terrain preparation Python, and the project's prepared LiDAR Place directory. Set `GT_BANK_PLACE` to a staged Place directory when the normal export volume is offline. The default selection is the 380 m pilot. `GT_BANK_REACH_M` accepts two stations in metres or `all` for the whole course. The editor writes original and candidate R16 files, masks, a report and three pairs of fixed-camera screenshots to a fresh folder under `Saved/LidarBankRelief`. The saved driving map remains the baseline.

For another map, invoke `Art/tools/bake_riverbank_relief.py --help`. Supply the receiving terrain's origin, vertex spacing, encoding, water-surface polyline in metres and masks on its vertex grid. The wet mask must include every vertex of a quad touching water. Use the original heightfield as the source for each rebuild.

## From candidate to driving default

1. Compare the revised shape from the checkpoint at pickup height, looking across the river and around the next undressed bend. Repeat with normal foliage and neutral terrain shading, then drive both directions. Look for interrupted shelves, visible changes in slope and parallax past the bank. Reject a smooth raised ribbon, repeating ledges, or relief that disappears at the driving LOD.
2. At the same points, compare physics traces with the intended heights. Inspect exposed roots, buried plants and gaps beneath stones. Use the baked surface to re-seat affected vegetation in the authoring pass, retaining XY, species, scale and grouping. Validate tile seams, water occupancy, depth and wheel contact at the crossing. Keep hand dressing for distinctive roots, debris or individual rock exposures.
3. Run unchanged and candidate pickup drives in stock–candidate–candidate–stock order on the RTX 4050 at the saved standalone resolution and settings. Match vehicle path, camera and speed. Record mean and p95 frame time, GPU base pass, shadows, terrain draws and memory. Compare against stock repeat variation and the 16.67 ms frame budget. Repeat on the longer river route to catch streaming or LOD spikes.
4. After those gates pass, apply the verified terrain delta to the map's authoring heightfield before road generation and vegetation placement. Preserve the source DEM, baked exclusions and existing placements as reproducible inputs. Reopen the saved candidate and repeat the drive before promoting it.
