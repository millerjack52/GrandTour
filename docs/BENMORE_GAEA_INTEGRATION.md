# Benmore Gaea return — Unreal review

The approved Gaea 2 study has been imported into:

`/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`

The existing `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive` map remains unchanged. The review has its own terrain material, creek material, textures and water mesh. Shared production meshes and materials were not rebuilt.

## Changes in the review

- Imported the protected Gaea heightfield into the existing Landscape, keeping the original extent, transform and height encoding.
- Removed the six old raised bank meshes and six old water segments from this map.
- Added a narrow, terrain-fitted creek surface following the Gaea channel mask in the editable catchment. Added damp gravel/soil colour near the creek while retaining the established terrain and road material treatment.
- Restored the pre-river vegetation density outside the new channels so the retired river strip can regrow. Cleared 18 authored shrub instances from the new watercourse.
- Re-seated 1,120 existing shrub instances and 28 static actors against the changed ground.
- Repositioned the existing river dressing along the new channels: 2,300 approved tussocks, 1,700 gravel stones, 150 shrubs, 45 larger rocks and 10 trees. Reused the same meshes, scales, rotations and materials.
- Retained the road layout, gravel, verge dressing, backdrop and lake. Removed the lake material's exclusion for the retired water segments.

## Validation

The imported Unreal heightmap matches all **4,068,289** candidate samples exactly. Its SHA-256 is recorded in `Art/Export/BenmoreGaea/integration/unreal-import-report.json`.

Both road instance groups have identical counts and complete transform hashes before and after the import: **5,704** road aggregate instances and **52,104** verge instances.

The import performed **185 native Landscape collision checks**, with a maximum difference from the expected triangle heights of **0.954 mm**. Repositioned bank meshes use their low vertices for grounding rather than just their origin. Recorded bank basal samples are embedded by 6.5 cm.

The creek has 19,210 vertices and 25,890 triangles after softening the raster-mask edges. All mesh vertices and triangle centres were checked against the exact Landscape triangles. Surface clearance is 6.5–13.1 cm, and its conservative minimum distance from a road edge is 140 m. There is no raised bank geometry in the new channel system.

Saved-level verification completed on 2026-10-08 after the creek refinement. All 4,068,289 height samples still match exactly after reloading, and 62 additional native collision samples have a maximum error of 0.954 mm. The original map hash is unchanged. The final editor run exited normally. Results are recorded in `integration/unreal-review-report.json` and `integration/water-refinement-report.json`. These are static editor checks, not driving or performance tests.

The three final captures were visually reviewed: `integration/Creek_Close.png`, `integration/Creek_Reach.png` and `integration/Long_Vista.png`. The banks sit against the revised landform without the old raised strips, and the existing vista composition is retained. Water remains a preview: strong reflection in the sun-facing reach, simple shoreline transitions and visible ripple repetition need further art work alongside the final flow bake.

## Current water scope

This is a **shallow visual water preview fitted to the approved terrain**, with animated ripples. It is not a new hydraulic simulation or a vehicle water volume. The ripple direction follows the ground gradient; it is not a claim of physically computed flow speed.

The Gaea surface and depth exports precede the protective terrain blend. Using the raw water surface directly would leave some reaches metres above the final ground, so the review uses a separately fitted surface. The former hydraulic bake cannot be reused unchanged after this terrain revision.

Water is limited to the edited catchment. The lake outlets and fade at the study boundary still need deliberate design before a final hydraulic rebake. Runtime deformable gravel is unaffected; its base terrain can be updated against the revised Landscape during integration.

## Review locations

The saved map opens looking toward the creek reach. Named cameras:

- `Benmore_Gaea_Camera_Creek_Close`
- `Benmore_Gaea_Camera_Creek_Reach`
- `Benmore_Gaea_Camera_Long_Vista`

Inspect the new bed and banks first, then the wider vegetation pattern. The final water pass should follow approval of this imported landform, including how each outlet reaches the lake.

Open the map through Unreal's Content Browser under `GrandTour/Demo/BenmoreRoads/Gaea`, or run `Art/open_benmore_gaea.ps1` when the shared Unreal editor/test suite has finished. The launcher checks for an existing editor or active test suite before opening the review.

## Rebuild tools

- `Art/tools/convert_benmore_gaea.py`: validates the returned reference and creates the protected candidate.
- `Art/tools/prepare_benmore_gaea_integration.py`: generates preview water geometry, masks and replacement bank positions.
- `Art/tools/check_benmore_gaea_integration.py`: checks surface/terrain clearance, winding, dimensions and road clearance.
- `Art/Blender/export_benmore_gaea_water.py`: exports the water mesh using the established Unreal axes.
- `Art/Unreal/benmore_gaea_materials.py`: creates review-owned material variants.
- `Art/Unreal/import_benmore_gaea.py`: imports the terrain, re-seats dressing and checks native collision.
- `Art/Unreal/check_benmore_gaea_review.py`: reloads the saved map, checks persistence and captures static editor views without PIE.
- `Art/import_benmore_gaea.ps1 -ReviewOnly`: launches those saved-level checks, with a guard against concurrent Unreal processes.
- `Art/import_benmore_gaea.ps1 -FinishPreview`: refreshes only the review water assets, saves and runs the same saved-level checks/captures.

The importer refuses to overwrite an already completed review automatically. For another Gaea revision, make a new version or explicitly arrange a rebuild of the review map. Do not rerun the old Benmore road setup to import this terrain.
