"""Build shadow-only copies of the first playable tree meshes without Nanite area preservation."""

import hashlib
import json
from pathlib import Path

import unreal as u


root = Path(u.Paths.project_dir()).resolve()
folder = "/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy"
sources = [f"{folder}/SM_NaniteRenderLod1_{i}" for i in range(3)]
digest = hashlib.sha256(Path(__file__).read_bytes())
for path in sources:
    package = (root / "Content" / path.removeprefix("/Game/")).with_suffix(".uasset")
    digest.update(package.read_bytes())
version = digest.hexdigest()[:12]
target = f"{folder}/ShadowShape/{version}"
assets = u.EditorAssetLibrary
assets.make_directory(target)
records = []
for path in sources:
    original = u.load_asset(path)
    source_settings = original.get_editor_property("nanite_settings")
    assert source_settings.enabled and source_settings.shape_preservation == u.NaniteShapePreservation.PRESERVE_AREA
    dest = f"{target}/{original.get_name()}"
    tree = u.load_asset(dest) if assets.does_asset_exist(dest) else assets.duplicate_asset(path, dest)
    assert tree and tree != original
    settings = tree.get_editor_property("nanite_settings")
    if settings.shape_preservation != u.NaniteShapePreservation.NONE:
        settings.shape_preservation = u.NaniteShapePreservation.NONE
        tree.set_editor_property("nanite_settings", settings)
        assert assets.save_loaded_asset(tree, False)
    result = tree.get_editor_property("nanite_settings")
    assert result.enabled and result.shape_preservation == u.NaniteShapePreservation.NONE
    triangles = tree.get_static_mesh_description(0).get_triangle_count()
    assert triangles > 0 and triangles == original.get_static_mesh_description(0).get_triangle_count()
    assert [s.material_interface for s in tree.static_materials] == [s.material_interface for s in original.static_materials]
    records.append(dict(source=path, shadow=dest, source_triangles=triangles))
manifest = root / "Art/Export/LidarStudy/FloraWorld/shadow-shape-study.json"
manifest.write_text(json.dumps(dict(version=version, meshes=records), indent=2) + "\n")
u.log(f"GT_SHADOW_SHAPE_BUILT version={version} species={len(records)}")
