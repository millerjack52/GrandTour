# Benmore terrain-wide vegetation

The existing playable map `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive` now uses a separate landscape material and Landscape Grass Types for terrain-wide coverage. `Art/play_benmore_roads.ps1` remains the launcher. The pre-cover map is preserved as `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeFullVegetation`.

Coverage spans the complete 2500 m square containing the user's 2240 x 2404 m selected site. Fine grass, Straw, Rust and Weathered tussocks share reproducible density masks derived from slope, elevation and broad patch variation. The moisture-style variation is artistic, not a hydrological survey. Road corridors, lake-height ground and steep rock faces have reduced or zero cover.

The vegetation uses the four actual meshes from `/Game/GrandTour/ArtTests/TussockStyle/L_TussockStyle`: `SM_TS_Straw`, `SM_TS_Rust`, `SM_TS_Weathered` and `SM_TS_Fine`. Their original mesh materials and vertex colours are retained, with no material override or extra tint. Shared art assets are not modified. All three authored LODs remain available.

The refined cover pass raises Fine grass density from 175 to 350 per 100 m², Straw from 28 to 70, Rust from 22 to 55, Weathered from 14 to 35, and distant Straw from 3 to 6. Density masks and global scalability still apply; these are maximum asset densities, not measured plant counts. The full-site coverage and road/water exclusions are unchanged.

The map-owned ground material now samples the existing Meadow Environment dry-grass albedo and grass normal at a 4.8 m repeat, with finer stylised grass detail at 1.6 m. Desaturated straw/soil colours, broad patch variation and normal detail break up exposed ground. The existing road texture blending remains in place. `M_Benmore_BeforeGroundDetail` preserves the previous ground material.

Vegetation spawns in landscape grass clusters near views instead of storing millions of placed actors. Fine grass has a nominal end cull distance of 110 m; primary tussock varieties 320–450 m. A sparse lowest-LOD Straw layer extends to 950 m. Foliage scalability can reduce density. The original opaque source material does not implement the previous custom dithered distance fade; grass uses LODs and cluster distance culling.

Those are asset settings before project scalability: the current shared project settings apply `grass.DensityScale=0.5` and `grass.CullDistanceScale=0.6`. This pass respects them; effective draw distances are 60% of the asset values. Coverage exists across the site and streams as the camera moves, rather than rendering every blade across the full tile simultaneously.

The former dense roadside-only grass group is replaced by this terrain-wide system; its stones and guide posts remain. This pass changes vegetation and landscape material, not terrain height or driving physics. Ordinary landscape grass has no blocking collision.

## Sources and rebuild

- `Art/tools/prepare_benmore_vegetation.py`: creates the south-up 2017Â² RGBA mask in `Art/Export/BenmoreVegetation`. RGB drives low grass, tussock and taller clumps; alpha records an artistic moisture variation.
- `Art/Unreal/setup_benmore_vegetation.py`: installs map-owned vegetation assets, assigns the full-cover material, and saves the driving map.
- `Art/Unreal/benmore_ground_detail.py`: shared ground-detail graph and density settings, also applied by full setup.
- `Art/Unreal/refine_benmore_cover.py`: updates the existing map material and grass types, recording `ground-refinement-report.json`.
- `Art/Unreal/use_benmore_tussock_style.py`: verifies the source study and updates the existing grass types without rebuilding coverage masks.
- `Art/Unreal/check_benmore_vegetation.py`: reloads the saved map and checks that grass clusters appear at four widely separated camera positions. Captures and observed editor frame intervals are written to `validation-report.json`; only `ok: true` confirms completion. Frame intervals are a local editor observation, not a shipping benchmark.

Re-run vegetation setup after rebuilding the roads with `setup_benmore_roads.py`, which assigns the road-only material. The coverage masks should be regenerated whenever the road masks or imported heights change.

## Verification

The source asset swap is recorded in `tussock-style-report.json`. The streaming check reloads the saved map and requires all four `SM_TS_*` varieties at each viewpoint, with populated grass clusters near the camera. Verification uses render-cluster bounds because this Unreal Python build does not expose GPU-backed grass instance totals through the ordinary instance-count API. `validation-report.json` records the latest results and local editor frame intervals; these are not a shipping benchmark.

The denser textured-ground pass passed all four saved-map streaming checks. Average local editor frame intervals were 25.9 ms at the terrace road, 26.3 ms in the northern hills, 29.2 ms on the eastern terrace and 20.8 ms in the southern hills (runtime viewport 1274 x 682). The first three were approximately 3–7 ms slower than the preceding sparse pass; the southern view was similar. This is a visual-quality increase with a measurable rendering cost, not an optimized shipping benchmark. Earlier captures and timings are preserved in `Art/Export/BenmoreVegetation/BeforeGroundDetail`.

Source terrain: LINZ Data Service / ToitÅ« Te Whenua Land Information New Zealand, CC BY 4.0. Original attribution remains in the Benmore full-site package.
