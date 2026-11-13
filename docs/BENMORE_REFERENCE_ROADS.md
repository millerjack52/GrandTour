# Benmore photo-reference road and palette pass

The gravel now also has a close-range parallax pass; see [BENMORE_GRAVEL_POM.md](BENMORE_GRAVEL_POM.md) for height sources, controls and verification.

Road shoulders now also have patchy soil/gravel shading and instanced stones and TussockStyle grass; see [BENMORE_ROAD_VERGES.md](BENMORE_ROAD_VERGES.md).

The latest [physical relief pass](BENMORE_VERGE_RELIEF.md) adds interrupted banks and shallow drainage hollows to the landscape around those shoulders.

The user's five area photographs are preserved in `Art/References/Environment/BenmoreUserPhotos`. The first image guides the graded terrace-road surface; the fourth guides rougher hillside gravel. Images two, three and five guide the muted grey-brown hills, restrained olive vegetation and dry straw grass. These images guide material character and colour relationships, not surveyed road alignment or exact colour calibration across different lighting conditions.

The current driving map uses neutral grey-taupe compacted gravel, coarse loose aggregate along the centre and shoulders, and gently wandering compact wheel paths. Road-relative coordinates keep these bands aligned through bends. Their widths vary between the existing terrace loop and hillside branch. The road edges gain modest irregularity through the surface shader. This pass does not reshape terrain, cut banks or change the physical road profile.

The former low-contrast painted gravel samples are replaced for this map by existing project gravel textures with paired DirectX normal maps. Small 2.5–8.5 cm stone instances add close-range relief, concentrated away from the wheel paths. The 5,704 stones have no collision and cull at 70 m. Hills blend toward desaturated grey-brown exposed ground with elevation and slope, while gentler terraces retain the dry-grass palette. Approved TussockStyle colours and willow shapes are retained.

## Assets and rebuild

- `Art/tools/prepare_benmore_reference_roads.py` saves the user photos, generates a 2017² south-up road coordinate texture and deterministic small-stone placements.
- `Art/Unreal/benmore_reference_surface.py` builds the road/terrain shading. Compact gravel repeats over 4 m; loose gravel now repeats over 8 m for larger stones that read from the driving camera. The coordinate texture encodes signed lateral distance over a 32 m range and road half-width, allowing narrower wheel paths than a pre-painted one-metre raster mask would support.
- `Art/Unreal/setup_benmore_reference_roads.py` imports map-owned textures, updates the landscape material, installs aggregate instances and saves the driving map.
- `Art/Unreal/benmore_ground_detail.py` reapplies this reference surface on future full-cover rebuilds when the reference-coordinate asset exists.
- `Art/Unreal/check_benmore_reference_roads.py` reloads the saved map, verifies aggregate counts/non-collision, checks vegetation streaming and captures terrace, hillside and close surface views.

The previous ground material is saved under `/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/M_Benmore_BeforeReferenceRoads`. Shared road studies and source texture files are unchanged. This is a first surface/palette match; road bank geometry, drainage, corrugation and survey alignment require separate work.

Source texture provenance is retained in `Art/Textures/RoadBenchmark/SOURCE.txt` and its download manifests. Terrain attribution remains in `BENMORE_FULL_SITE.md`. Setup/capture reports and review images are in `Art/Export/BenmoreReferenceRoads`; require `ok: true` for successful validation.

Final saved-map validation on 2026-10-07 passed in all three views: 5,704 aggregate instances, all non-colliding, and all four approved tussock meshes streaming near the cameras. The final reload log had no shader compilation errors. The captures still show smooth road profiles and broad, relatively uniform distant hills; this pass establishes surface detail and colour direction, rather than a finished match to the reference terrain.
