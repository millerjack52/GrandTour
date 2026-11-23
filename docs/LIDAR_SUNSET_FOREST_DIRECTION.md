# Forest art direction for the LiDAR study

Tyler Smith’s open-world conifer forest is the overall visual target. In the two wide renders, dark irregular trees frame an opening onto cooler, progressively softer ridges. Most of the warmth sits on the peaks and cloud edges. In the playable forest footage the floor is quieter, with a few distinct trunks, rocks and grass silhouettes close to the player. The equivalent view on LiDAR is the moment the pickup turns out of the woods and sees the far bank or paddock tree line. [Sunset forest and playable footage](https://80.lv/articles/open-world-stylized-sunset-forest-scene-made-with-ue5)

David Holland’s *Meadows* supplies the close-range treatment. He paints identifiable grass silhouettes, varies neighbouring clumps together, transfers enclosing normals to tree cards and controls moss on upward-facing stone with a painted mask. His bright meadow palette belongs to his scene. On LiDAR, the same techniques can give the darker woodland a clear silhouette and a detailed ground surface. [Meadows breakdown](https://80.lv/articles/meadows-creating-stylized-nature-in-ue4)

## The first three comparisons

| Priority | Change to test | What the driver should see |
|---|---|---|
| 1. Compose a view through a stand | Use the existing heightfield and pickup sightline to place a near group with an uneven edge, a staggered group across the turn and a gap onto existing distant trees. Redistribute existing visual instances within the trial area. Keep collision-bearing trees in place. Expose a different slice of the distant slope on entry and exit. | At 320 pixels wide, near trunks, the middle canopy and the distant landform should read as three layers. The driver should see through the forest briefly without seeing an empty strip. |
| 2. Give the trees a characteristic outline | Test one asymmetrical conifer with an exposed leader, uneven branch lengths, spaces between needle masses and a fuller side toward the opening. Repeat the test on one native broadleaf. Bake broad lighting normals by branch group and carry the silhouette into each LOD and distant tree card. | At pickup height, the two species should be recognisable in silhouette. A lit branch mass should hold together on approach, and the skyline should survive the LOD change in motion. |
| 3. Connect the ground to the landform | Use slope, shelter and drainage to place linked moss patches, peat, litter and existing grass. Concentrate grass where the canopy opens. Give rock shelves an exposed mineral face and an upward-growing moss edge. Leave readable bare ground between colonies. | From the bank the moss should follow the ground and rock. From the cab the verge should describe the bend. The wheel line and the river edge should stay readable. |

Smith describes shaping land around boulders, composing mid-distance gaps and using separate texture coordinates for individual leaves and whole-tree gradients in his **earlier Pacific Northwest forest**. These are documented methods for that project and candidate techniques for GrandTour. The sunset feature establishes the visual target. [Smith’s forest breakdown](https://80.lv/articles/take-a-walk-in-a-stylized-pacific-northwest-forest-visualized-in-3d)

## Light, scale and cost

Judge the stand first under the saved daylight. Compare a low warm sun from the same bend and open viewpoint. Keep shadow detail in the near olive grass, a cooler middle slope, and a small area of distant warmth. Treat the sky and the distant ridge as a pair. A bright horizon behind every tree would flatten the same layers we want to see.

Implement the layout as reusable stand and edge rules driven by terrain, local canopy and road clearance. Assign roles such as canopy, sapling, groundcover and exposed rock so another map can supply its own species. Carry broad colour and height in mesh data or the existing grass field. Use instancing and distance representations for the repeated shapes. Keep detailed rock and ground normals where the pickup can approach.

## What the first lighting comparison showed

In the running game, the directional sun moved from 24° to 11° above the horizon and from yaw −80° to 54°. The test used 4,050 K and 28,140 intensity, with the saved skylight, fog and exposure. Compared from the same three cameras, the low sun gives the open ridge a clean silhouette and removes the bright strip across the track. The grass also turns a fairly uniform brown-gold and the sky above the ridge is largely empty. On the bend the opposite trees still form a fairly even row. The normal-tuned broadleaf carries almost the same silhouette as before. Composition, branch shape and cool distant land are the strongest next trials. The saved daytime sun remains available for judging each one.

Review the wooded approach, river opening and open skyline from the same cameras. Compare the normal pickup drive in both directions. Check near detail, reduced greyscale silhouettes, transitions to distant foliage, median and 95th-percentile frame time, base pass and shadows. Confirm any cost difference with interleaved repeats. A measured 16.67 ms frame budget is the 60 fps target.
