# LiDAR forest-access bend

The forest-floor pilot is saved in `/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy` on the first 42 m bend of the Logging mud track, between stations 27 and 69 m. Run `Art/Unreal/ForestAccessBend/Drive-ForestAccess.bat` to start the normal pickup and LiDAR quality preset at the approach. The ordinary `Play-LidarStudy.bat` also loads the edited map.

## What to look for

Drive past the stump and look along both shoulders. A partly buried Rock Master boulder sits on the wooded shoulder at station 48 m, 5.35 m from the road centre. Look inland beside it to see the folded fern leaflets, loose warm leaf litter and moss giving way to peat between the beds. The source boulder provides its UV-matched colour, roughness and tangent-space normal. A local material adds moss at the foot. Between the pickup and the tall trunks, two irregular groups of 11 differently sized F002 pines frame the turn. They use the installed FloraTrail pine, its three existing LODs and the bark and crown materials from the saved crown-form study. World-position animation is disabled on the instance batch. One broadleaf midstorey tree uses a local instance of the existing painted leaf material.

The layout replaces 171 noncolliding shrubs and repeated tussock, rush and fern instances within the bend. It regroups 149 existing grass and fern instances. Two opaque meshes carry the fitted relief and the folded foliage and litter. The latter contains 86 fern crowns and 1,042 fallen leaves. Their shapes, colours and positions are baked at authoring time. Ground vertices use one XY grid. Edges descend into the original terrain at roads and water. The packed peat texture carries fine height and cavities. A four-metre baked field separates moss cushions and warm leaf pockets. Small groups of bronze fern tips repeat the litter colour. Local replacement models have no collision. The original road, vehicle contact terrain, mud actors, water, lights and Fast shadow settings retain their existing configuration.

## Reproduce the comparison

From a full local project with the licensed assets installed, use PowerShell with Unreal Engine 5.8. Texture baking uses Python with Pillow and NumPy. The capture uses the existing LiDAR launcher, 1600×900 output and the map's 75% TSR preset. The pickup follows the same surveyed bend in low range. The moving comparison aligns frames by distance along the road. A separate inland camera alternates the relief, frond/litter and pine components on and off for six blocks of 96 frames, with 32 settling frames per block. Frame timing starts at station 27 m and ends at 69 m. Screenshots and the second, distance-sampled motion pass run outside that interval.

```powershell
Set-Location C:/GrandTour
$bend = './Art/Unreal/ForestAccessBend'
& "$bend/Run-ForestAccess.ps1"
& "$bend/Run-ForestAccess.ps1" -VerifyOnly
& "$bend/Capture-ForestAccess.ps1" -Stage baseline -SavedBaseline -Motion
& "$bend/Capture-ForestAccess.ps1" -Stage candidate -Motion
```

`-SavedBaseline` validates the original map backup against the build receipt, then launches a temporary copy with the same map name and play settings. It removes the temporary copy when Unreal exits. On a machine with the original, untouched map, capture a baseline directly with `-Stage baseline -Motion` before the first build. Use `compare.py BEFORE_RUN AFTER_RUN` to generate fixed-camera images, the matched drive and a frame-time summary in the candidate run directory.

The original map backup is `Saved/ForestAccessBend/BeforeForestAccess.umap`. Build and fresh-launch verification receipts are beside it. Each drive's images and original Unreal GPU timing CSV are in `Saved/ForestAccessBend/drives`. The repository carries the authoring source. Rendering uses the installed project assets.

## Driving review, 23 November 2026

In the matched pair `baseline-20261123-163803-575` and `candidate-20261123-164525-226`, the pickup traversed the complete bend in both worlds. The final save reloaded with 11 pines and the original terrain digest, `6AE1F9489CE5EC408044BFEC06A9FE25`. From the chase camera the stone and the pine groups mark the outside and inside edges of the turn. Looking inland shows the clearest change in depth, with low fern fans and stems rising from the moss in front of the taller trees. The smooth broad moss caps, bright shrubs beyond the pilot, and the relatively open opposite bank still differ visibly from the woodland reference.

| Time in milliseconds | Original drive | Final drive |
|---|---:|---:|
| Frame, median | 35.22 | 30.53 |
| Frame, 95th percentile | 38.93 | 33.40 |
| GPU, median | 34.40 | 29.92 |
| GPU base pass, median | 12.83 | 10.82 |
| GPU shadow depths, median | 2.79 | 2.58 |

An original-map repeat immediately after the final drive measured 33.76 ms median and 36.57 ms at the 95th percentile, with median GPU time of 32.92 ms. Across launches, original-map median frame times ranged from 30.39 to 38.33 ms. This variation limits attribution of the driving-time difference to the artwork. In the stationary inland view, the three adjacent visible-minus-hidden GPU pairs were −0.56, −0.34 and −0.47 ms for the two baked meshes and the pine group together. The corresponding median base-pass difference was −0.40 ms. The removed shrubs and earlier dressing stay fixed during this visibility test. The 16.67 ms target remains open.

Local review files in the final drive folder include `pickup-and-forest.jpg`, `matched-drive.webp`, `reference-and-bend.jpg`, `values.jpg`, `comparison.json` and the six unedited traces in `dressing-cost`.
