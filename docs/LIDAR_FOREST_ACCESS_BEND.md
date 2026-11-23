# LiDAR forest-access bend

The forest-floor pilot is saved in `/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy` on the first 42 m bend of the Logging mud track, between stations 27 and 69 m. Run `Art/Unreal/ForestAccessBend/Drive-ForestAccess.bat` to start the normal pickup and LiDAR quality preset at the approach. The ordinary `Play-LidarStudy.bat` also loads the edited map.

## What to look for

Drive past the stump and look along both shoulders. A partly buried Rock Master boulder sits on the wooded shoulder at station 48 m, 5.35 m from the road centre. Look inland beside it to see the folded fern leaflets, loose warm leaf litter and moss giving way to peat between the beds. The source boulder provides its UV-matched colour, roughness and tangent-space normal. A local material places the same moss pigment used on the ground along upward-facing stone shelves. Between the pickup and the tall trunks, two irregular groups of 11 differently sized F002 pines frame the turn. They use the installed FloraTrail pine, its three existing LODs and the bark and crown materials from the saved crown-form study. World-position animation is disabled on the instance batch. One broadleaf midstorey tree uses a local instance of the existing painted leaf material.

The layout replaces 171 noncolliding shrubs and repeated tussock, rush and fern instances within the bend. It regroups 149 existing grass and fern instances. Two opaque meshes carry the fitted relief and the folded foliage and litter. The latter contains 86 fern crowns and 1,042 fallen leaves. Their shapes, colours and positions are baked at authoring time. Ground vertices use one XY grid. Edges descend into the original terrain at roads and water. The packed peat texture carries fine height and cavities. The current ground material separates moss colonies from peat using baked vertex coverage, local slope and a tiling brush texture at two physical scales. Short folded grass fans are baked into the same opaque draw as the fronds and litter. Small groups of bronze fern tips repeat the litter colour. Local replacement models have no collision. The original road, vehicle contact terrain, mud actors, water, lights and Fast shadow settings retain their existing configuration.

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

## Original bend comparison, 23 November 2026

In the matched pair `baseline-20261123-163803-575` and `candidate-20261123-164525-226`, the pickup traversed the complete bend in both worlds. The final save reloaded with 11 pines and the original terrain digest, `6AE1F9489CE5EC408044BFEC06A9FE25`. From the chase camera the stone and the pine groups mark the outside and inside edges of the turn. Looking inland shows the clearest change in depth, with low fern fans and stems rising from the moss in front of the taller trees. The smooth broad moss caps, bright shrubs beyond the pilot, and the relatively open opposite bank still differ visibly from the woodland reference.

| Time in milliseconds | Original drive | Final drive |
|---|---:|---:|
| Frame, median | 35.22 | 30.53 |
| Frame, 95th percentile | 38.93 | 33.40 |
| GPU, median | 34.40 | 29.92 |
| GPU base pass, median | 12.83 | 10.82 |
| GPU shadow depths, median | 2.79 | 2.58 |

An original-map repeat immediately after the final drive measured 33.76 ms median and 36.57 ms at the 95th percentile, with median GPU time of 32.92 ms. Across launches, original-map median frame times ranged from 30.39 to 38.33 ms. This variation limits attribution of the driving-time difference to the artwork. In the stationary inland view, the three adjacent visible-minus-hidden GPU pairs were −0.56, −0.34 and −0.47 ms for the two baked meshes and the pine group together. The corresponding median base-pass difference was −0.40 ms. The removed shrubs and earlier dressing stay fixed during this visibility test. The 16.67 ms target remains open.

Local review files in the revision 5 drive folder include `pickup-and-forest.jpg`, `matched-drive.webp`, `reference-and-bend.jpg`, `values.jpg`, `comparison.json` and the six unedited traces in `dressing-cost`.

## Meadows surface comparison

The user's frame matches the fixed inland camera. In the same running game, hiding the shoulder relief removed the broad green sheet immediately. Hiding every native moss hummock left the sheet in place. Repeat the isolation by setting `$env:GT_BEND_ISOLATE_MOSS='1'` before a candidate capture and clearing it afterward.

Revision 6 lowers and divides the relief, grows moss along shelves on the landmark rock, and adds 370 grass fans in groups to the existing opaque frond/litter mesh. There are 8,544 shoulder triangles and 81,893 foliage/litter triangles. The earlier fern and litter populations were retained. Each grass group shares pigment and lean. A single broadleaf uses a local crown-normal adjustment. The original 11 pines still use the previously accepted crown material.

A first surface test improved the outline but left too much connected moss in the centre. The final shader uses the same 512 px shoot texture at 72 cm for the tips and 2.8 m for the colony boundaries with exposed peat between them. The second sample costs one additional texture lookup per shaded shoulder pixel. The stone keeps its source colour, normal and roughness with moss concentrated on upper ledges.

Use `Capture-ForestAccess.ps1 -Stage candidate -Motion -SunsetStudy` to record the daylight drive, then compare saved daylight and temporary low sun in three fixed views. The sunset study runs after timing, in the standalone game process. The map keeps its daylight setting. The next landscape-scale trial and the verified texture-pack resources are in [forest art direction](LIDAR_SUNSET_FOREST_DIRECTION.md) and the [reference guide](FOREST_ART_REFERENCE_GUIDE.md).

### Saved result and timing

The direct comparison uses the previous saved bend (`candidate-20261123-165743-960`) and the final material (`candidate-20261123-171052-185`). Both use the same LiDAR settings and a real pickup. The fixed camera shows exposed peat running through the former green sheet, short grass groups crossing its edges, and rock ledges picking up the same green. The trial broadleaf differs little even at its close camera. The mature canopy and distant shrub silhouettes still need a change in shape or grouping.

| Daylight drive, milliseconds | Previous bend | Revised bend |
|---|---:|---:|
| Median frame | 30.86 | 33.21 |
| 95th-percentile frame | 34.47 | 37.62 |
| Median GPU | 29.99 | 32.43 |
| Median GPU base pass | 10.95 | 12.00 |
| Median GPU shadow depths | 2.57 | 2.70 |

The final drive was 2.35 ms slower at the median. Two runs of the intervening material revision also differed across launches (31.23 and 35.15 ms). In the fixed inland camera, the median of three adjacent visible-minus-hidden GPU pairs for the combined relief, foliage and pines was −0.77 ms in the previous bend and −0.18 ms in the revision. This check includes the occlusion those objects provide. Attribution of the full driving delta remains open; route-wide 60 fps remains unverified.

The final fresh load checked material revision 4, 370 grouped grass fans and terrain digest `6AE1F9489CE5EC408044BFEC06A9FE25`. The comparison media, six individual GPU traces and raw driving CSV are in the final run folder under `Saved/ForestAccessBend/drives`. The separate recoverable pre-Meadows map, local assets and receipts are in `D:/GrandTourGitHub/LocalReviewBackups/ForestAccessBeforeMeadows` on the authoring machine.
