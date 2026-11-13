# Approved tussock study imported to Unreal

Main review map: `/Game/GrandTour/ArtTests/TussockStyle/L_TussockStyle`.
The approved gravel road revision 04 is now integrated into this map; see
`docs/GRAVEL_ROAD_IMPORT.md`. Reapply its importer after rebuilding this base scene.
An overview-start variant is `L_TussockStyle_Overview` in the same folder.
The existing road/ford scene and dense renderer comparison maps are preserved.

Source is the user-approved Blender art study
`Art/Export/TussockStyleStudy/07/TussockStyleStudy.blend`.
The four source mesh datablocks are exported unchanged at LOD0, including their
vertex palette and artist normals. Centimetre conversion is performed only on
export copies. The original Blender file is never saved by the exporter.

| Mesh | LOD0 triangles | LOD1 | LOD2 |
| --- | ---: | ---: | ---: |
| SM_TS_Straw | 2660 | 896 | 336 |
| SM_TS_Rust | 2660 | 896 | 336 |
| SM_TS_Weathered | 2660 | 896 | 336 |
| SM_TS_Fine | 600 | 200 | 80 |

Lower LODs retain complete distributed blades rather than collapsing arbitrary
triangles. Their ribbons widen modestly to help preserve coverage. Screen-size
thresholds are 1 / 0.08 / 0.025. Nanite is disabled for this authored-LOD version.

`M_TS_Grass` is opaque, two-sided foliage with vertex colour driving base and
subsurface colour. Instance usage is enabled. Blender's diffuse/transmission
preview is approximated by Unreal's foliage shading model. Engine captures
remain the reference for final lighting; Blender is used for asset review.

The map uses four ISM components under `TS_ApprovedTussock`, with 19,262 instances
spread across the existing ford terrain. The planting uses larger straw/rust
groups and occasional weathered crowns, with fine grass beneath. Road/river
masks, slope alignment and feathered edges are retained. The three crown
components now cast shadows; the fine-grass component does not. No grass collision,
distance-field lighting contribution or ray-tracing visibility;
no hard component distance cutoff. These are static test-map placements, not a
new PCG graph or wind/interaction implementation.

## Build and checks

- `bash Art/export_tussock_style.sh`: twelve FBXs and placement manifest.
- `Art/setup_tussock_style.ps1`: four mesh assets, material and two maps.
- `Art/capture_tussock_style.ps1`: runtime driver/overview image review.
- `Art/profile_tussock_style.ps1`: one stationary performance run per view.
- `Art/analyse_tussock_style.py`: warm-sample statistics and thermal flags.

Reports and images: `Art/Export/TussockStyle/`.
Import succeeded and verifies all material slots, three LODs and thresholds.
Both engine captures were inspected: meshes/materials are present, the new
colour groups are visible, and the coverage continues into the distant banks.
Review PNGs are camera-constrained to 1440 x 810; the benchmark uses 1440 x 900.
The default runtime look is now fixed exposure without custom screen filters.
The automation screenshot shader precompile still reports failures on the
pre-existing root-folder post-look/Kuwahara materials; the new grass material
imports successfully. Runtime captures assert mode 2, zero warp, Kuwahara off,
and no post-process material blendables in either runtime volume.

## Clean lighting update (2026-09-29)

The owner requested more lighting depth and removal of the grainy, low-resolution
screen effect. The previously active band pass included a 1.5-pixel stroke warp.
`gt.Look.Post=2` and `gt.Look.WarpScale=0` are now the source and project-config
defaults. Kuwahara and film grain were already off. Fixed exposure is retained;
mode 2 now respects authored sun softness instead of forcing a hard sun.
This default change applies across gameplay maps. Surface paint and mesh colours
are retained. The custom distance haze in the disabled band pass is also absent.

Only the two tussock review maps receive the authored lighting adjustment:
sun intensity 10.5, pitch -27, yaw -58, source angle 1.5 degrees, temperature
5800 K; skylight intensity 0.65. Larger crowns cast shadows to ground their
shapes; fine grass remains shadowless. A first pass with sky intensity 0.35
produced excessive dark mottling in the overview and was softened before review.

`Art/update_tussock_lighting.ps1` updates the saved maps without reimporting grass.
`Art/Unreal/tussock_style_lighting.py` is also called by the full setup script so
reimporting preserves these choices. The C++ build passed. Both runtime review
views were captured; `capture-report.json` verifies the disabled screen filters.
Pre-change images and performance results are preserved in
`Art/Export/TussockStyle/before-lighting/`.

## Initial performance check

RTX 4050 laptop, DX12, 1440 x 900, 100% screen percentage, uncapped rendering,
GPU cooldown before each run. One run per view, 550 warm frames (300-849), with
no thermal-throttling flags recorded. Both runs exited successfully without
material/runtime compilation errors in the standalone game logs.

| View | GPU median | GPU p95 | Frame median | Frame p95 |
| --- | ---: | ---: | ---: | ---: |
| Driver | 13.05 ms | 15.21 ms | 14.17 ms | 28.92 ms |
| Overview | 13.15 ms | 15.07 ms | 14.50 ms | 27.76 ms |

Median local GPU memory was about 3.70 GB, with 93 reported draw calls. These
are full-scene figures, not an incremental cost measurement for grass. The
driver GPU median is higher than the earlier prototype's single 10.65 ms run;
the models and planting density have changed, so no zero-cost claim is made.
These checks do not establish locked 60 fps, in-motion LOD transition quality,
or complete driving performance. Raw CSVs, telemetry and statistics are saved
under `Art/Export/TussockStyle/before-lighting/performance`.

## Performance after clean lighting

Same two stationary views and sampling method, at 1440 x 900 / 100% screen
percentage on DX12. Both runs completed without standalone material/runtime
errors or recorded thermal-throttling flags.

| View | GPU median | GPU p95 | Frame median | Frame p95 |
| --- | ---: | ---: | ---: | ---: |
| Driver | 13.32 ms | 15.72 ms | 14.06 ms | 29.18 ms |
| Overview | 13.41 ms | 15.08 ms | 14.20 ms | 27.56 ms |

GPU medians are approximately 0.26 ms higher than the initial runs. This is the
net result of removing the screen pass and changing lighting/shadows, not an
isolated shadow-cost measurement, and single-run variation remains. Median
reported draw calls increased from 93 to 101. The frame p95 still exceeds
16.67 ms; these results do not establish locked 60 fps or driving performance.
Current CSVs, telemetry and analysis are in `Art/Export/TussockStyle/performance`.
