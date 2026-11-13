# Approved gravel imported to Unreal

Source: `Art/Export/GravelRoadStudy/04/GravelRoadStudy.blend`.
Maps: `/Game/GrandTour/ArtTests/TussockStyle/L_TussockStyle` and its
`L_TussockStyle_Overview` variant. New assets live in
`/Game/GrandTour/ArtTests/GravelRoad`.

The approved procedural Blender surface is baked as two colour/DirectX-normal
pairs (loose aggregate and compacted tracks), each 2048 square over a 6 m patch.
Unreal blends them using the existing wheel-wear channel. Mirrored tiling avoids
texture-boundary seams, with normal signs corrected for reflected tiles. This
preserves the visual vocabulary and scale; it is not an exact world-coordinate
copy of every procedural chip. Existing meadow and moisture masks blend into the
previous bank and wet-ground materials. The global screen filters remain off.

Eight full-size terrain meshes retain their existing continuous normals and add
the approved shallow gravel ridges. Relief fades out over the last 2 m approaching
the mud/ford and back in over 2 m on the exit. Existing terrain collision profiles
and physical-material overrides are retained; pebble instances have no collision.
The ford's mud/water remain the pre-existing static art preview, not a newly
connected simulation.

Four stone meshes (33/38/33/38 triangles) use 9,523 instances under
`GR_ApprovedGravel`, vertex-colour shading, and cast shadows. They do not contribute
distance fields or ray tracing and have no hard distance cutoff. Earlier loose
stone components are hidden in these two maps so they do not double up. Grass,
trees, camera positions and lighting remain unchanged. The road meshes use Nanite;
the tiny stones use conventional instancing.

## Rebuild

1. Run Blender in background with `Art/Blender/export_gravel_road.py`. This bakes
   textures and exports road meshes, copying stone FBXs and reconciling placements
   at the wet-road transition. It does not save over the approved Blender study.
2. With the editor and other games closed, run `Art/import_gravel_road.ps1`.
3. Run `Art/capture_gravel_road.ps1` for runtime driver and overview review.
4. Run `Art/profile_tussock_style.ps1`, then `Art/analyse_tussock_style.py`.

If the full tussock setup is rebuilt, rerun the gravel importer afterward.
The importer preserves map backups at `GravelRoad/Before_L_TussockStyle` and
`GravelRoad/Before_L_TussockStyle_Overview` on its first application.
Before-import images and performance data are archived in
`Art/Export/GravelRoadUE/before-import`. Current exports, import/capture reports
and review images are in `Art/Export/GravelRoadUE`.

The runtime capture checks four gravel components / 9,523 instances, eight terrain
material assignments, fixed-exposure mode 2 and zero custom post blendables.
Visual inspection is still required: material connections can be structurally
present while their appearance is wrong. An initial black-stone connection was
caught in the first capture and corrected before final review.

## Validation and performance

Both final runtime captures were inspected. The baked painted detail, worn paths,
loose-stone colours and shadows are visible; the new material does not show a
checker fallback. Import verifies a 26 m first road section and eight replacements
per map. Runtime validates all gravel instances, material assignments and disabled
screen filters. No C++ changes were needed for this import.

RTX 4050 Laptop, DX12, 1440 x 900, 100% screen percentage, uncapped. One stationary
run per view; 550 warm samples (frames 300–849), cooldown before each run. Final
standalone logs passed the material/runtime error guard. Neither run recorded
thermal-throttling flags.

| View | GPU median | GPU p95 | Frame median | Frame p95 |
| --- | ---: | ---: | ---: | ---: |
| Driver | 13.68 ms | 15.64 ms | 15.19 ms | 28.61 ms |
| Overview | 12.34 ms | 13.99 ms | 5.78 ms | 46.67 ms |

The driver GPU median is +0.37 ms against the archived 13.32 ms pre-import run.
The overview has a wide frame-time distribution; its smaller GPU median should
not be interpreted as a proven performance improvement. Frame-time percentiles
do not establish locked 60 fps, and these runs do not test driving or isolate
individual material/shadow cost. Current CSVs, telemetry and analysis are copied
to `Art/Export/GravelRoadUE/performance`; the original harness output remains in
`Art/Export/TussockStyle/performance`.
