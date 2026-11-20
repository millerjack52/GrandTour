"""Make study-only painted Nanite trees from the conventional renderer's first playable LOD."""

import hashlib
import json
from pathlib import Path

import unreal as u


root = Path(u.Paths.project_dir()).resolve()
base = "/Game/GrandTour/ArtTests/LidarStudy"
study = base + "/PerformanceStudy"
assets = u.EditorAssetLibrary
geo = u.GeometryScript_AssetUtils
read = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA, lod_index=1)
summary = []

for kind in range(3):
    source_path = f"{base}/FloraWorld/Canopy/SM_Canopy_{kind}"
    paint_path = f"{study}/SM_NanitePainted_{kind}"
    dest = f"{study}/SM_NaniteRenderLod1_{kind}"
    source, paint = u.load_asset(source_path), u.load_asset(paint_path)
    assert (
        source
        and paint
        and not source.get_editor_property("nanite_settings").enabled
        and paint.get_editor_property("nanite_settings").enabled
    )
    expected = source.get_num_triangles(1)
    _, indices, _, result = geo.get_section_material_list_from_static_mesh(source, read)
    assert result == u.GeometryScriptOutcomePins.SUCCESS
    # The query appends the unused far billboard slot after the drawn sections.
    slots = list(indices)[: source.get_num_sections(1)]
    assert expected > 0 and len(slots) == 2 and len(set(slots)) == 2, (
        source.get_name(),
        expected,
        slots,
        source.get_num_sections(1),
    )
    digest = hashlib.sha256()
    for path in (source_path, paint_path):
        digest.update(
            (root / "Content" / path.removeprefix("/Game/")).with_suffix(".uasset").read_bytes()
        )
    signature = digest.hexdigest()
    tree = (
        u.load_asset(dest)
        if assets.does_asset_exist(dest)
        else assets.duplicate_asset(paint_path, dest)
    )
    assert tree and tree.get_path_name().split(".")[0] == dest
    if assets.get_metadata_tag(tree, "RenderLod1Source") != signature:
        dynamic, outcome = geo.copy_mesh_from_static_mesh_v2(
            source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), read, False
        )
        assert (
            outcome == u.GeometryScriptOutcomePins.SUCCESS
            and dynamic.get_triangle_count() == expected
        )
        _, outcome = geo.copy_mesh_to_static_mesh(
            dynamic,
            tree,
            u.GeometryScriptCopyMeshToAssetOptions(),
            u.GeometryScriptMeshWriteLOD(),
            False,
        )
        assert outcome == u.GeometryScriptOutcomePins.SUCCESS
        tree.set_editor_property("static_materials", paint.static_materials)
        assert tree.get_static_mesh_description(0).get_triangle_count() == expected
        assets.set_metadata_tag(tree, "RenderLod1Source", signature)
        assert assets.save_loaded_asset(tree, False)
    assert (
        tree.get_editor_property("nanite_settings").enabled
        and tree.get_static_mesh_description(0).get_triangle_count() == expected
    )
    _, indices, _, result = geo.get_section_material_list_from_static_mesh(
        tree, u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL)
    )
    assert result == u.GeometryScriptOutcomePins.SUCCESS and list(indices)[: len(slots)] == slots
    assert [s.material_interface for s in tree.static_materials] == [
        s.material_interface for s in paint.static_materials
    ]
    summary.append(
        dict(
            species=kind,
            original_lod0=source.get_num_triangles(0),
            render_lod1=expected,
            slots=slots,
            signature=signature,
        )
    )

output = root / "Art/Export/LidarStudy/FloraWorld/render-lod-study.json"
output.write_text(json.dumps(summary, indent=2))
u.log("GT_RENDER_LOD_PREPARED species=3")
