# Ground material revision: ground-painted-02

## Smooth terrain follow-up: ground-smooth-03

The user accepted the richer textures but rejected visible tessellation. The
per-face meadow tint has been removed: shared vertices now carry identical
colours on every adjoining face. Terrain normals are evaluated from the same
continuous height function on every ground chunk, including shared boundaries.
The importer explicitly preserves those normals for the nine terrain meshes.
The distant ridge also uses smooth shading and broad continuous colour variation
instead of flat faces and random vertex brightness.
Painted textures, material sample count, geometry and dressing stay unchanged.
`ground-validation.json` checks smooth shading, custom normals, shared-boundary
normal agreement and continuous corner colours as well as the existing counts.

The road/ford style level now uses full-colour painted gravel and meadow textures
instead of compressing photographic gravel into a faint greyscale modulation.
Cool slate and warm beige stones sit over dark umber earth. The bank underlayer
contains golden matted straw, olive patches and exposed soil. Compacted wheel
paths are lighter and smoother than the loose gravel between and beside them.

## Review

The first Blender pass made stones too large and the wheel paths too weak.
Pass 2 halves the gravel texture footprint and strengthens the dusty tracks.
Dry-road, verge and muddy-approach renders were inspected with the previous
lighting, exposure and geometry unchanged. This is a material revision;
the full scene is still subject to further art review.

Blender previews and source: `Art/Export/RoadFordStyle/`.
Before images: `GroundIterations/baseline/`; first pass: `GroundIterations/pass-01/`.
Level: `/Game/GrandTour/ArtTests/RoadFordStyle/L_RoadFordStyle`.

## Reproducible material contract

- Two generated RGB textures in `Art/Textures/GroundPainterly/`, with original
  prompts in `provenance.json`. Original images are 1254 x 1254. Unreal stretches
  them to a power-of-two size, capped at 2048, with streaming and mipmaps.
- UV0: continuous 3-metre coordinates across the assembled terrain pieces.
  The gravel traverses its texture in approximately 1.5 m; meadow in 3 m.
- Mirror wrapping makes tile boundaries continuous. A gentle coordinate warp
  softens straight repeat boundaries; it does not eliminate all repetition.
- UV1: meadow blend in U and wetness in V. Unreal's FBX importer flips V, so
  the Unreal shader decodes moisture as `1 - UV1.y`.
- Vertex RGB: broad neutral colour variation. Vertex alpha: loose-gravel mask
  used to lighten/smooth the compacted tracks.
- Wetness darkens the approach and reduces roughness. This remains a static
  material preview, not integration with the deformable mud/water systems.
- Existing gravel normal provides subtle fine grain. It is not a baked normal
  matching the new painted stones; those shapes are primarily colour detail.

## Validation and cost

Blender validation confirms all 11,930 instance placements and all 31 source-mesh
triangle counts match the preceding grass-reference-05 assembly (151,506 source
triangles). Nine terrain pieces retain both UV channels with masks in 0..1.
The import reports ground-painted-02 and successfully saves the style level.

The shader uses three texture samples: two colour maps and the existing normal.
That is one more sample than the previous ground shader, with no new geometry,
instances or shadow casters. Runtime performance delta has not been measured;
previous grass A/B timings must not be presented as measurements of this shader.
`Art/smoke_ground_material.ps1` runs the existing stationary benchmark copy with
the shared updated assets, DX12 at 1440 x 900, without capturing screenshots.
The known unrelated Kuwahara post effect is disabled for this smoke check.
The 600-frame DX12 smoke run passed with exit code 0 and no material compile
errors (`Saved/Logs/ground_material_smoke.log`). This verifies compilation and
runtime loading, not visual equivalence between Blender and Unreal.

Build: `Art/road_ford_blender_preview.sh`, then `Art/import_road_ford_style.sh`.
Validation: run Blender on `RoadFordStyle.blend` with
`Art/Blender/validate_ground_material.py`.
