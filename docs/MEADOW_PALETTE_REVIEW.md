# Meadow palette and coverage: meadow-palette-02

The user supplied an Unreal screenshot with pale yellow grass and exposed gaps.
This revision increases coverage and uses a restrained straw, olive and earth
palette. Sun, exposure, camera and global look settings are unchanged.

## Coverage

Grass spacing changes from 0.72 to 0.66 metres. Each shared patch has two broader,
overlapping fans; the lower fan grows from 55% to 80% of the standing fan's size.
The patch has 20 folded blades instead of 24, reducing it from 120 to 100 triangles.

There are 10,914 patches, up from 9,249 (18.0%). Their total unculled triangle
count is 1,091,400, down from 1,109,880 (1.7%). The full scene has 13,595 dressing
instances, 31 source meshes and 151,406 source triangles. These are geometry
counts, not GPU timings: more instances and broader screen coverage can cost more
even when triangle totals are lower.

The five shared opaque meshes retain one material each, no collision, no shadow
casting, no ray tracing or distance-field contribution, and 25-42 m fade/cull.
The route and ford remain clear. Existing non-grass placements are unchanged.

## Palette and colour transfer

The first preview was too grey and uniform. The second uses olive blades beneath
warm straw, with sparse pale seed highlights. Larger tussocks and willow leaves
use related subdued colours. The meadow texture is tinted down and cooled so it
does not form a bright yellow layer between clumps. Road texture detail remains.

The FBX export now explicitly writes LINEAR vertex colours. Previously Blender's
default SRGB export encoded the authored linear values. Unreal's FBX path decodes
these into mesh-description linear colours, then StaticMeshBuilder encodes them
back into the byte colour buffer. LocalVertexFactory reads those bytes directly
as vertex colours without a final sRGB decode. Writing linear numeric values in
the FBX therefore supplies the intended values to the material in this pipeline.
Alpha, used for grass height and ground masks, stays linear throughout.

This applies only to the isolated RoadFordStyle exports. It does not change the
project's other exporters, shared materials, car or global colour management.
Binary FBX validation compares every exported grass RGBA value with the authored
linear values. All five meshes must match; the importer requires the manifest's
LINEAR encoding declaration.

## Review and validation

Blender previews retain the prior lighting and exposure. First-pass images and
the preceding revision are retained under `GrassIterations/palette-01` and
`GrassIterations/palette-before`. Final files are under `Art/Export/RoadFordStyle`.

Run `Art/validate_meadow.sh` to validate source geometry, terrain continuity,
non-grass placements, grass material slots and FBX colours, and to refresh
`GrassCoverage.blend`. Import with `Art/import_road_ford_style.sh` after the owner
has saved and closed Unreal. Import and runtime validation status is recorded
below; do not reuse earlier revisions' performance figures for this revision.

Source validation passed, including all five FBX colour comparisons. The owner
closed Unreal during the review; the meadow-palette-02 import then completed
successfully with 13,595 instances.

Four cooled ABBA runs (Off/On/On/Off), offscreen DX12 at 1440 x 900 and 100%
screen percentage, completed with no material errors or observed thermal-throttle
flags. Each contributes 550 warm frames (300..849). Grass visibility adds
0.2487 ms to the GPU base-pass median and 0.1015 ms to game-thread time in this
stationary driver-height view. The two grass-on GPU medians were 9.9920 and
9.0437 ms; total GPU/frame-time variation was too large to infer an exact total
grass cost or claim that adding grass improves performance. The negative total
GPU delta must not be advertised as a speedup. Kuwahara was disabled for both
variants, as in the previous benchmark; this is not a complete production-tour
performance guarantee. No Unreal screenshots were captured.

Raw runs and analysis are archived under `GrassIterations/palette-02/`; CSVs are
under `GrassIterations/performance/meadow_palette02_*`. The reviewed Blender
images are in `GrassIterations/palette-02/` as well.
