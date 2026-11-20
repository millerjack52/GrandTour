"""Give the original D 003 leaf draws distinct names at the two playable geometry LODs."""

from array import array
import hashlib
import json
import os
from pathlib import Path

import unreal as u


def section_geometry(mesh, lod, section):
    pos, indices, normals, uvs, tangents = u.ProceduralMeshLibrary.get_section_from_static_mesh(
        mesh, lod, section
    )
    digest = hashlib.sha256(array("I", indices).tobytes())
    keys = set()
    for p, n, uv, t in zip(pos, normals, uvs, tangents, strict=True):
        attributes = (
            *p.to_tuple(),
            *n.to_tuple(),
            *uv.to_tuple(),
            *t.tangent_x.to_tuple(),
            t.flip_tangent_y,
        )
        digest.update(array("f", attributes).tobytes())
        keys.add(attributes)
    return dict(
        geometry_sha256=digest.hexdigest(),
        triangles=len(indices) // 3,
        vertices=len(pos),
        distinct_with_tangent_uv0=len(keys),
    )


root = Path(u.Paths.project_dir()).resolve()
base = "/Game/GrandTour/ArtTests/LidarStudy"
assets = u.EditorAssetLibrary
# The commandlet has no editor subsystem collection. The material-slot methods
# operate entirely on their mesh argument on the editor's main thread.
edit = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.get_default_object(
    u.StaticMeshEditorSubsystem
)
src = u.load_asset(base + "/FloraWorld/Canopy/SM_Canopy_1")
source_rows = json.loads(Path(os.environ["GT_LIDAR_NANITE_SOURCE_AUDIT"]).read_text())[
    "flora_settings"
]
(data,) = [
    s for s in source_rows if s["tags"] == "FloraWorldCanopy" and s["mesh"] == src.get_name()
]
materials = [u.load_asset(path) for path in data["materials"]]
(leaf_slot,) = [i for i, m in enumerate(materials) if m.get_name().startswith("MI_Path_Leaf_")]
version = hashlib.sha256(
    (
        root / "Content/GrandTour/ArtTests/LidarStudy/FloraWorld/Canopy/SM_Canopy_1.uasset"
    ).read_bytes()
).hexdigest()[:12]
folder = f"{base}/PerformanceStudy/LeafLodLabels/{version}"
assets.make_directory(folder)
dest = folder + "/SM_D003_LodLabels"
copy = (
    u.load_asset(dest)
    if assets.does_asset_exist(dest)
    else assets.duplicate_asset(src.get_path_name().split(".")[0], dest)
)
assert copy and copy != src and src.get_num_lods() == copy.get_num_lods() == 4
slots = list(copy.static_materials)
assert len(slots) in (3, 5)
indices = []
for lod in (1, 2):
    leaf = materials[leaf_slot]
    name = f"MI_D003_Leaf_LOD{lod}"
    path = folder + "/" + name
    label = (
        u.load_asset(path)
        if assets.does_asset_exist(path)
        else u.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew()
        )
    )
    assert label
    u.MaterialEditingLibrary.set_material_instance_parent(label, leaf)
    assert label.get_editor_property("parent") == leaf and assets.save_loaded_asset(label, False)
    index = len(materials) + lod - 1
    slot = u.StaticMaterial(material_interface=label, material_slot_name=name)
    if index == len(slots):
        slots.append(slot)
    else:
        slots[index] = slot
    (section,) = [
        i
        for i in range(src.get_num_sections(lod))
        if edit.get_lod_material_slot(src, lod, i) == leaf_slot
    ]
    indices.append((lod, section, index))
copy.set_editor_property("static_materials", slots)
for lod, section, index in indices:
    edit.set_lod_material_slot(copy, index, lod, section)
assert assets.save_loaded_asset(copy, False)
checks = []
for lod in range(4):
    assert src.get_num_sections(lod) == copy.get_num_sections(lod)
    for section in range(src.get_num_sections(lod)):
        original = section_geometry(src, lod, section)
        assert section_geometry(copy, lod, section) == original, (lod, section)
        old_slot = edit.get_lod_material_slot(src, lod, section)
        new_slot = edit.get_lod_material_slot(copy, lod, section)
        expected = next(
            (slot for level, part, slot in indices if (level, part) == (lod, section)), old_slot
        )
        assert new_slot == expected
        checks.append(
            dict(lod=lod, section=section, old_slot=old_slot, new_slot=new_slot, **original)
        )
report = dict(
    source=src.get_path_name(),
    mesh=copy.get_path_name(),
    materials=data["materials"],
    sections=checks,
)
(root / "Art/Export/LidarStudy/FloraWorld/leaf-lod-labels.json").write_text(
    json.dumps(report, indent=2)
)
u.log("GT_D003_LOD_LABELS_READY lods=4 leaf_labels=2")
