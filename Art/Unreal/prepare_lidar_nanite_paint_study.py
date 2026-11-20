"""Compile the map's actual tree materials on separate Nanite study packages."""

import hashlib
import json
import os
from pathlib import Path

import unreal as u


root = Path(u.Paths.project_dir()).resolve()
base = "/Game/GrandTour/ArtTests/LidarStudy"
folder = base + "/PerformanceStudy"
assets = u.EditorAssetLibrary
editing = u.MaterialEditingLibrary
assets.make_directory(folder + "/NanitePaint")
source_report = json.loads(Path(os.environ["GT_LIDAR_NANITE_SOURCE_AUDIT"]).read_text())
copies = {}


def copy_paint(source):
    key = source.get_path_name().split(".")[0]
    if key in copies:
        return copies[key]
    assert key.startswith(base + "/")
    parent = (
        copy_paint(source.get_editor_property("parent"))
        if isinstance(source, u.MaterialInstanceConstant)
        else None
    )
    package = (root / "Content" / key.removeprefix("/Game/")).with_suffix(".uasset")
    version = hashlib.sha256(
        package.read_bytes() + (parent.get_path_name().encode() if parent else b"")
    ).hexdigest()[:12]
    dest = f"{folder}/NanitePaint/{source.get_name()}_{version}"
    copy = (
        u.load_asset(dest) if assets.does_asset_exist(dest) else assets.duplicate_asset(key, dest)
    )
    assert copy and copy != source
    if parent:
        editing.set_material_instance_parent(copy, parent)
        editing.set_material_usage_override(copy, u.MaterialUsage.MATUSAGE_NANITE, True, True)
    else:
        assert isinstance(copy, u.Material)
        editing.set_material_usage(copy, u.MaterialUsage.MATUSAGE_NANITE)
        assert copy.get_editor_property("used_with_nanite")
    assert assets.save_loaded_asset(copy, False)
    copies[key] = copy
    return copy


trees = [c for c in source_report["flora_settings"] if c["tags"] == "FloraWorldCanopy"]
assert {c["mesh"] for c in trees} == {f"SM_Canopy_{k}" for k in range(3)}
for tree in trees:
    kind = tree["mesh"].split("_")[-1]
    src = f"{folder}/SM_NaniteTrial_{kind}"
    dest = f"{folder}/SM_NanitePainted_{kind}"
    mesh = (
        u.load_asset(dest) if assets.does_asset_exist(dest) else assets.duplicate_asset(src, dest)
    )
    assert (
        mesh
        and mesh.get_editor_property("nanite_settings").enabled
        and mesh.get_path_name().startswith(folder + "/")
    )
    slots = list(mesh.static_materials)
    assert len(slots) == len(tree["materials"]) == 3
    for slot, source_name in zip(slots, tree["materials"]):
        material = copy_paint(u.load_asset(source_name))
        slot.material_interface = material
    mesh.set_editor_property("static_materials", slots)
    assert assets.save_loaded_asset(mesh, False)
    assert all(
        "/PerformanceStudy/NanitePaint/" in slot.material_interface.get_path_name()
        for slot in mesh.static_materials
    )
u.log(f"GT_NANITE_PAINT_READY species={len(trees)} packages={len(copies)}")
