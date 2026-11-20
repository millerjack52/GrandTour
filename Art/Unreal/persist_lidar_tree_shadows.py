"""Persist the reviewed wind cutoff on this map's canopy and sapling components."""

import hashlib
import os
import json
import zipfile
from pathlib import Path

import unreal as u

MAP = "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy"
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Saved/LidarDrivingBaseline/route-shadow-review/install-check.json"
TAGS = {"FloraWorldCanopy", "FloraWorldSaplings"}


def digest_file(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def backup_map():
    source = ROOT / "Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap"
    with source.open("rb") as stream:
        original = digest_file(stream)
    backup_dir = Path(
        os.environ.get("GT_LIDAR_SHADOW_BACKUP_DIR", ROOT / "Saved/LidarTreeShadowBackup")
    )
    dest = backup_dir / (original + ".zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        temp = dest.with_suffix(".partial")
        with zipfile.ZipFile(
            temp, "w", zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True
        ) as archive:
            archive.write(source, source.name)
        with zipfile.ZipFile(temp) as archive, archive.open(source.name) as stream:
            if digest_file(stream) != original:
                raise IOError("Failed to verify the pre-change map backup")
        temp.replace(dest)
    else:
        with zipfile.ZipFile(dest) as archive, archive.open(source.name) as stream:
            assert digest_file(stream) == original, "Existing backup did not verify"
    return original


def selected(world):
    rows = {}
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        for component in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            tags = {str(tag) for tag in component.component_tags} & TAGS
            if not tags:
                continue
            key = (tags.pop(), component.static_mesh.get_path_name())
            if key in rows:
                raise RuntimeError(f"Duplicate canopy mesh in family {key}")
            rows[key] = component
    if {tag: sum(key[0] == tag for key in rows) for tag in TAGS} != {tag: 3 for tag in TAGS}:
        raise RuntimeError("Expected three reviewed canopy and three sapling groups")
    return rows


def describe(rows):
    snapshot = []
    for (family, mesh), component in sorted(rows.items()):
        count = component.get_instance_count()
        digest = hashlib.sha256()
        for index in range(0, count, max(1, count // 128)):
            transform = component.get_instance_transform(index, True)
            digest.update(
                repr(
                    (
                        transform.translation.to_tuple(),
                        transform.rotation.to_tuple(),
                        transform.scale3d.to_tuple(),
                    )
                ).encode()
            )
        snapshot.append(
            {
                "family": family,
                "mesh": mesh,
                "instances": count,
                "sample_transforms": digest.hexdigest(),
                "materials": [m.get_path_name() if m else None for m in component.get_materials()],
                "wind": component.evaluate_world_position_offset,
                "cast_shadow": component.get_editor_property("cast_shadow"),
            }
        )
    return snapshot


level = u.get_editor_subsystem(u.LevelEditorSubsystem)
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert level.load_level(MAP)
components = selected(editor.get_editor_world())
baseline = describe(components)
cutoffs = {c.world_position_offset_disable_distance for c in components.values()}
assert cutoffs in ({0}, {11000}), cutoffs
original_map = None
if cutoffs == {0}:
    original_map = backup_map()
    for comp in components.values():
        comp.modify()
        comp.set_world_position_offset_disable_distance(11000)
    del comp
    assert level.save_current_level()
del components
assert level.load_level("/Engine/Maps/Entry")
assert level.load_level(MAP)
components = selected(editor.get_editor_world())
assert all(c.world_position_offset_disable_distance == 11000 for c in components.values())
assert describe(components) == baseline
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(
        {"verified": True, "original_map_sha256": original_map, "groups": baseline}, indent=2
    )
)
u.log(
    "GT_SAVED_TREE_SHADOWS verified six persisted groups and original mesh/material/transform samples"
)
