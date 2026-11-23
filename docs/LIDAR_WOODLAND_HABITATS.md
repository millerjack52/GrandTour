# LiDAR woodland habitats

The forest floor, the fine grass drawn around the player, and the placement of existing ferns, shrubs and rocks use a common map of growing conditions. The first study covers 10.478 km² of eligible woodland. The approved tree groups, forest-access landmark and hand-composed river reveal have their own ownership.

## Art direction

Tyler Smith describes establishing geology first, considering downhill erosion and layering clumps of forest-floor foliage over a tiled ground surface. Here, rock groups follow local contours, ferns occupy sheltered beds and a separate litter texture carries detail through the openings. Smith's sunset forest is also our reference for the arrangement of silhouettes through depth. This study uses the project's existing daylight. [Pacific Northwest forest breakdown](https://80.lv/articles/take-a-walk-in-a-stylized-pacific-northwest-forest-visualized-in-3d) · [Sunset forest](https://80.lv/articles/open-world-stylized-sunset-forest-scene-made-with-ue5)

David Holland uses broad, smooth colour changes across grass clusters and a relatively simple colour map on individual plants. In LiDAR the grass and soil both sample the same woodland boundary. Fine grass thins under sheltered canopy and returns in openings and irregular lengths of verge. [Meadows breakdown](https://80.lv/articles/meadows-creating-stylized-nature-in-ue4)

## Inputs and scale

The offline bake combines the live canopy positions, mapped woodland, terrain height, local slope and curvature, road centre lines and water domains. Its four channels encode woodland influence, suitability for moss and ferns, exposed mineral ground and grass openings. The largest variation runs over approximately 29 m. Local variation breaks up patch edges down to roughly 5 m. A separate 2.4 m litter tile contains individually folded leaves. The forest floor keeps the value and large normals of the ground beneath it.

The placement pass groups existing decorative instances into irregular beds and stone runs. Rock groups orient along contours, compress vertically and intersect the sampled terrain. New positions and footprints must clear the road, water and the protected boulder. Previously composed plant positions at the bend and reveal are reserved. Grass streaming reads a bilinear density map when generating cells. Other maps can supply their own density map. Without one their grass multiplier is one. The LiDAR asset and actor selection lives in the Unreal adapter.

All five woodland rock families recover large mineral planes from their own colour maps and layer directional brush shapes over them. Shaded faces take a muted slate colour, with warmer stone on the broad faces. Moss favours upward-facing planes. The normal map carries reduced close relief. Moss on the forest floor uses connected cushion shapes from the same painted texture. The 15 previously authored river ledges use a map-local copy of their original finish with instanced rendering enabled.

To attribute an objectionable shape, set `GT_WOODLAND_IDENTIFY=1` alongside the woodland review flag. The game holds the inland camera and hides one nearby instanced mesh family per capture. At Riverside the stacks of flat green polygons disappeared with `SM_NZ_LeafLitter_A`. Its slot used the site's green bush material. The local replacement spreads 34 folded brown and ochre leaves over the footprint, with three mesh detail levels. The teal and orange frond silhouettes persisted without the litter. The fern, flowering shrub and small plant families now use their source alpha shapes and a shared olive pigment treatment with broader marks across each plant.

| Existing instance group | Instances repositioned |
|---|---:|
| Ferns | 118,413 |
| Ground grass | 58,720 |
| Shrubs | 28,572 |
| Rocks | 4,074 |

These figures exclude streamed grass blades. They measure the reach of the rule and say nothing about frame time.

## Reproduce or iterate

Use the live project's installed content, LiDAR place exports, revision 9 forest-access placement receipt and terrain Python environment. Run one Unreal or Blender renderer at a time. Build the native optional grass density reader before opening the map.

```powershell
& ./Art/build_guarded.ps1
& ./Art/run_woodland_habitats.ps1 -Stage Prepare
& ./Art/run_woodland_habitats.ps1 -Stage Install -BackupDirectory D:/GrandTourGitHub/LocalReviewBackups/WoodlandHabitats
& ./Art/run_woodland_habitats.ps1 -Stage Verify
```

The installer checksums a full copy of the starting map and records its absolute path in `Saved/WoodlandHabitats/placement.json`. Candidate materials and textures live in the map's own `WoodlandHabitats/v1` package folder. To adjust pigment, litter or rendered grass density in the installed study, rerun the offline bake if needed and use `-Stage Surface`, then `-Stage Verify`. This updates the surface without redistributing the forest again. For changes to the geography or clustering rules, start a separate study copy from the pre-habitat map and use a fresh `-Revision` number. The installer rejects stacking two distributions.

## Driving review

The review uses the pickup path in `Saved/ForestAccessBend/drives/candidate-20261123-183634-460/drive.json`. Set `GT_WOODLAND_FIELD_REVIEW=1` and run `Art/Unreal/ForestAccessBend/Capture-ForestAccess.ps1 -Stage candidate -RiverApproach -VisualOnly -ReplayDrive <recording>` on each version. This records 34 driver-height positions from 6 to 72 m, four road and river views, and three additional views on Riverside access. The replay moves the scenery streaming source along the recorded trajectory. It measures visual continuity. Vehicle dynamics and timings require separate drives.

Use `Art/tools/review_woodland_habitats.py --before <run> --after <run> --out <folder> --encoder <ffmpeg>` to check the recording hash and camera poses, pair the frames and export the comparison. Open `Play-LidarStudy.bat` for normal play or `Art/Unreal/ForestAccessBend/Drive-ForestAccess.bat` to start at the bend.

For ground colour and normal edits alone, use `-Stage GroundPaint`. This recompiles the map's existing woodland materials. A fresh game replay is required to check the shipping-style shader permutations. The review rejects a capture if the runtime log reports that one of the study materials fell back to Unreal's default.

The user's Riverside screenshot matches `candidate-20261123-193636-963/bush-interior.png` pixel for pixel. Two sample points on the pale band in that view fell in the exposed-mineral channel. A repeating moss mask inherited from the old floor still contributed to surface height and occlusion there. The woodland material now retires that close pattern at its source. The existing far-distance average still applies. Use the paired crops in `forest-floor-detail.jpg` for the foreground and the matched replay for the driving view.

The saved candidate replay is `candidate-20261123-210956-101`. The woodland floor samples smaller brush shapes inside the moss patches and uses the same moss boundary for pigment and shaded relief on soil and on stone. The game comparison pairs 34 positions on the recorded pickup path and three fixed Riverside views. The most visible improvements at Riverside are the disappearance of polygonal litter piles and white mineral flecks, and the shift from orange to cream on the sunlit fronds. The exposed stones still read soft along some edges and the fern fans repeat. Frame times were deferred for this iteration.

The screenshot-specific film and crops are in `Saved/WoodlandHabitats/Review/ForestFloor`. The comparison in the parent directory starts from the pre-habitat map. An earlier capture stopped during the final Riverside view when the graphics driver reported a device loss. Its incomplete sequence was excluded.
