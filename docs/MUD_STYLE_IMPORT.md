# Approved mud 03 in Unreal

Source: `Art/Export/MudStyleStudy/03/MudStyleStudy.blend`.
Assets: `/Game/GrandTour/ArtTests/MudStyle`.
Updated levels:

- `/Game/GrandTour/ArtTests/TussockStyle/L_TussockStyle`
- `/Game/GrandTour/ArtTests/TussockStyle/L_TussockStyle_Overview`

The first road section now carries the approved warm clay faces, smoother worked
ruts, 141 angular clay clods, 296 earth-coated embedded stones and three shallow
pool surfaces. The full map continues beyond the Blender study's 26 m review
area; its remaining gravel, ford and grass are retained.

This imports the static art study. It does not change GTMudPatch, MudField,
runtime deformation, vehicle physics or simulated water. The rut geometry and
pool surfaces in these art maps remain static. Terrain uses complex collision;
small clods, pebbles and pool surfaces have no collision.

Four 2048px bakes transfer the approved raised clay and worked material colours
and DirectX tangent normals. A 6 m mirrored tile avoids hard texture boundaries.
UV2 holds mud coverage and wetness; UV3 holds rut coverage. Both preserve the
original gravel/meadow UVs and vertex colours. Roughness runs from 0.88 on dry
clay toward 0.48 in wet worked areas. The underlying approved gravel material
remains intact outside the mud mask.

Eight terrain meshes use Nanite. Detail meshes are instanced, with 7,082 total
instances across 14 components, including the retained gravel outside the mud.
The detail actor uses a static root so static instance components attach cleanly.
These are asset counts, not a performance benchmark.

Pre-import copies of both levels are saved at
`/Game/GrandTour/ArtTests/MudStyle/Before_L_TussockStyle` and
`/Game/GrandTour/ArtTests/MudStyle/Before_L_TussockStyle_Overview`.
The import is repeatable and replaces the previous mud detail actor.

Reproduce:

1. Run Blender with `Art/Blender/export_mud_style.py` (CPU bakes, four threads).
2. Run `Art/import_mud_style.ps1` with Unreal and games closed.
3. Run `Art/capture_mud_style.ps1` for runtime driver, detail and overview views.

Reports and screenshots are in `Art/Export/MudStyleUE`. The capture checks all
eight ground material assignments, four UV channels, instance counts and the
clean runtime post settings (Post 2, warp 0, Kuwahara 0).

Validation completed: import report and runtime capture report both return
`ok: true`. All eight meshes have four UV channels and the expected material;
the runtime actor has 14 instance components / 7,082 instances. Driver, close-up
and overview PNGs were visually inspected. Lighting is the existing Unreal
level sunlight, so the result is warmer with deeper shadows than the Blender
preview. No new GPU benchmark or vehicle/deformation test was run for this
static art import.

The capture log contains compile warnings for the older `M_GT_PostLook` and
`M_GT_PostKuwahara` shaders. Those effects remain disabled by the current look
settings; the imported `M_MS_Ground` material has no compile failure in the
fresh capture run. The older post shader errors were not changed by this task.
