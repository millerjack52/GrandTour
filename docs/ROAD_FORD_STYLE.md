# Road and ford style assembly

The owner accepted the initial road benchmark on 2026-09-28 and asked to move on.
This next assembly retains its gravel, stone and tussock vocabulary and adds a
72 m route through a small stream crossing. The original L_RoadBenchmark stays
available for comparison.

## Open and rebuild

- Unreal: `/Game/GrandTour/ArtTests/RoadFordStyle/L_RoadFordStyle`.
- Blender: `Art/Export/RoadFordStyle/RoadFordStyle.blend`.
- Blender previews: `Ford_driver_view.png`, `Ford_overview.png`,
  `Mud_approach_detail.png`, `Dry_road_driver_view.png`, and `Road_verge_detail.png`
  in the same output folder.
- From the repository root in Git Bash: `bash Art/road_ford_style.sh`, then
  `bash Art/import_road_ford_style.sh` with Unreal closed.
- For offline Blender work while Unreal is open, use
  `bash Art/road_ford_blender_preview.sh`. This only changes source files, exports
  and Blender renders; it does not load or save Unreal assets.
- Generator: `Art/Blender/build_road_ford_style.py`.
- Importer: `Art/Unreal/setup_road_ford_style.py`.

The generator appends the accepted benchmark's source meshes and materials into
a fresh Blender scene. It needs that packed RoadBenchmark.blend file. It never
saves over it. Rebuilding replaces the generated RoadFordStyle output; preserve
manual edits in a separate source file. Binary exports and renders are ignored
by Git and need separate preservation.

## New work

- Dry gravel entry, a depressed and rutted muddy approach, ford bed and exit.
- A single terrain material spans road, gravel shoulders and banks. Vertex RGB
  carries the authored gravel/soil/vegetation palette, including moisture colour;
  alpha controls texture and normal detail strength. Both Blender and Unreal use
  these channels. This replaces the previous separate road/bank shaders.
- Irregular verge width, softened edge transitions, wandering compacted wheel
  paths, eight loose-gravel deposits, exposed earth patches, three shallow
  depressions and intermittent edge erosion.
- Smaller grass clusters intrude into the gravel and occasional centre tufts
  interrupt the road. Fine stones cluster at the authored gravel deposits.
- Gravel shoulders, rising tussock banks and a faceted distant ridge.
- Three flattened ford-rock variants and a weathered crossing-marker post.
- Scattered aggregate, clustered bank stones and vegetation. The central ford
  line is kept clear of large rocks.
- Static teal water with sparse directional highlight strokes for composition.

The assembly is approximately 72 by 64 m before the far-ground/backdrop meshes.
The central road mesh is 4.6 m wide; its visible gravel edge varies independently
and blends into the shoulders and banks. The four
route meshes divide at 26, 39 and 47 m. These are proposed art-layout dimensions,
not edits to the tuned vehicle, terrain or water systems.

## Validation and limitations

Review images are rendered in Blender. The generated manifest records source
mesh triangles, material slots and every placement. The Unreal import report
records imported bounds, instance counts and save success; the importer checks
that the first road section measures 26 m.

The variation revision exports 22 meshes (79,996 source triangles before
instancing) and 2,613 instances. The previous assembly had 66,172 triangles and
1,533 instances. Extra shoulder subdivisions support continuous colour blending;
the extra instances are small gravel and verge/centre tufts. These counts are
not a performance result. Blender driver-height and close-up renders were
inspected for surface variation and the road-to-bank transition. Earlier renders
and the source blend are preserved in `ReviewBeforeVariation` in the output folder.

**Mud and water are static art previews.** The approach has the existing Mud
physical material, but it does not deform. The water has no collision and is not
a GTWaterSheet; it does not simulate, buoy or drag the car. Marker posts are
ordinary collision meshes, not functional winch anchors. The existing simulation
systems still need to be connected in a subsequent integration pass.

The isolated materials use instancing/Nanite flags. The assembly uses saved ISM
placements, not a new PCG graph. Final painterly-post appearance, driving feel,
performance and simulation integration have not been verified. No Unreal capture
is required for this modelling review. Shared material issues recorded in
ROAD_BENCHMARK.md remain outside this work.

Texture source: the same CC0 Poly Haven gravel maps documented in
`Art/Textures/RoadBenchmark/SOURCE.txt`; no new external texture source.

## Colour contrast revision

`colour-contrast-01` increases the separation between pale warm wheel paths,
darker earth and mud, olive/ochre banks, golden tussocks and blue-slate stones.
Geometry and placement are unchanged. Material colours are stored in the
manifest, including overrides for the inherited stone and grass materials, so
the importer applies the palette as well as the terrain vertex colours.

Blender ambient strength changes from 0.6 to 0.28 and exposure from +0.65 to 0.
A separate camera-visible cobalt sky keeps sky colour independent of ambient
fill. AgX Medium High Contrast is selected when available. These are Blender
review settings, not changes to Unreal's fixed exposure or global lighting.

Earlier images/source and the previous import report are preserved under
`ReviewBeforeColour`. The source manifest's revision and the import report's
source_revision distinguish prepared exports from an applied Unreal import.
Unreal was open during preparation and closed before the import was started.
Final appearance in Unreal remains unverified; the review images are Blender
renders, and the exposure/fill changes apply only to that review scene.

## Riverbank vegetation revision

`riverbank-vegetation-01` adds two willow and two scrub models, with six trees and
62 scrub instances around the ford. All previous 2,613 placements were compared
against the preserved manifest and match. The current assembly has 26 meshes and
2,681 instances. The new models, source library and collision verification are
documented in [RIVERBANK_ASSETS.md](RIVERBANK_ASSETS.md).

`riverbank-refined-04` supersedes those first vegetation models after four Blender
review/revision passes. The level still has 26 meshes and 2,681 unchanged instance
placements. See [TREE_ITERATION_REVIEW.md](TREE_ITERATION_REVIEW.md) for the visual
critiques, final geometry counts and verified collision import.

## Grass coverage revision

`grass-coverage-02` adds 9,238 short grass patches beneath the existing tussocks.
The source uses five shared opaque meshes and one material, with feathered road
and water boundaries. Previous dressing placements are unchanged. The imported
level now contains 31 source meshes and 11,919 instances. Grass fades/culls over
25–42 m and has no collision or shadow casting. See
[GRASS_COVERAGE.md](GRASS_COVERAGE.md) for the Blender review iterations, runtime
settings and controlled performance measurements.

The user rejected that grass appearance. `grass-reference-05` replaces it with
folded golden tussock fans and a painted meadow underlayer, after three further
Blender revisions against the original concepts. The current level contains
9,249 new grass patches (11,930 instances total); each shared grass mesh is now
120 triangles. See [GRASS_REFERENCE_REVIEW.md](GRASS_REFERENCE_REVIEW.md).

`ground-painted-02` adds painted gravel and meadow colour maps, stronger dusty
wheel paths and darker soil while preserving geometry and placements. See
[GROUND_MATERIAL_REVIEW.md](GROUND_MATERIAL_REVIEW.md) for the Blender iterations,
texture scales, UV-mask contract and validation limits.

`ground-smooth-03` removes face-based colour variation and preserves continuous
terrain normals through FBX import so the ground no longer advertises its grid.

`meadow-palette-02` adds fuller grass fans and a restrained straw/olive palette,
and fixes the FBX vertex-colour transfer. See [MEADOW_PALETTE_REVIEW.md](MEADOW_PALETTE_REVIEW.md)
for source validation, counts and Unreal verification status.

`meadow-fine-03` removes the green grass family and combines broad dry tussocks
with slender blades at the same patch and triangle counts. See
[FINE_GRASS_REVIEW.md](FINE_GRASS_REVIEW.md).

`meadow-variety-04` replaces the single repeating coverage shape with four meadow
forms and closer, clustered placement. See [GRASS_VARIETY_REVIEW.md](GRASS_VARIETY_REVIEW.md).
