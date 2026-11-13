# Grand Tour shrub library

Twelve stylized shrubs in six families, with upright A and broader, leaning B forms.
These are art-directed shrubs rather than botanical species reconstructions.
The palette follows the existing grounded, painterly vegetation direction.

| Family | Role | Approximate height above pivot, A / B |
| --- | --- | --- |
| Sage Cushion | Low, grey-green banks and roadside cover | 0.68 / 0.58 m |
| Broadleaf | Dense green bushes and sheltered ground | 1.40 / 1.18 m |
| River Lance | Tall, open, narrow-leaved river scrub | 2.22 / 1.79 m |
| Golden Bloom | Small yellow flowering accents | 1.09 / 0.95 m |
| Rust Thicket | Warm autumn/brown foliage | 1.54 / 1.31 m |
| Dry Scrub | Sparse leaves and exposed woody branches | 1.14 / 0.99 m |

## Files and use

- Editable source: `Art/Export/ShrubLibrary/v01/GrandTour_ShrubLibrary.blend`.
- The source scene has twelve marked Blender assets arranged for browsing;
  a separate scene contains the rendered review layout.
- 36 FBX and 36 GLB files: twelve variants with three LODs each.
- `manifest.json` records exact triangle counts, dimensions and variant names.
- `Shrub_Library_Overview.png` and `Shrub_Library_Angle.png` show actual meshes.
- Unreal destination: `/Game/GrandTour/Environment/Shrubs/v01`.

The pivot is at ground level. Roots extend about 7 cm beneath it to help seat
the meshes on terrain. FBX exports use the project's centimetre convention;
GLB and Blender geometry use metres. All assets use a single material slot,
linear vertex colours, opaque modeled leaves, and two-sided foliage shading.
UVs are local surface coordinates, deliberately overlapping; they are not
unique baking/lightmap UVs. No external textures are required.

Add the `SM_SH_*` meshes to the Foliage tool or use as static meshes/instances.
Small scale variation and random yaw help break repetition. Sparse and flowering
forms work as accents among the denser shrubs. There is no blocking collision.
No gameplay map is modified by the importer.

## LODs and verification

The LODs keep the major branch structure and distributed whole shoots, with
larger leaves at lower detail to retain coverage. Unreal screen-size thresholds
are 1.0, 0.18 and 0.065; Nanite is disabled for this authored-LOD version.
LOD0 ranges from 7,792 to 24,000 triangles. Consult the manifest for every LOD.

`validation-report.json` records all 36 FBX round trips: exact triangle counts,
dimensions within 1 mm, zero export translation, vertex colours, UV presence,
one material slot, and finite coordinates. Triangle counts decrease across LODs.
`unreal-import-report.json` records engine import, material assignment, three
LODs and measured engine dimensions. Only an `ok: true` report confirms import.

The mesh library has been visually reviewed in Blender. Wind, collision-based
interaction, PCG placement, engine lighting review and dense-scene performance
are not included or validated. LOD thresholds are initial settings and should
be reviewed at the intended planting density and camera distance.

## Rebuild

Run Blender 5.1 with `--background --factory-startup --python` and
`Art/Blender/build_shrub_library.py`, followed by
`Art/Blender/validate_shrub_library.py`. The factory startup avoids third-party
add-ons. The generator overwrites its v01 outputs; save hand-edited work as a
separate revision before rebuilding.

With the Unreal editor closed, run `Art/import_shrub_library.ps1`. The importer
requires the full editor's StaticMeshEditorSubsystem, not a Python commandlet.
It only writes assets in the dedicated shrub v01 content folder.
