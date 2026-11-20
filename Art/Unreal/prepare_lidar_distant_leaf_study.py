"""Build study-only leaf materials for the region beyond the authored wind fade."""

import hashlib
import json
import os
from pathlib import Path

import unreal as u


root = Path(u.Paths.project_dir()).resolve()
audit = json.loads(Path(os.environ["GT_LIDAR_NANITE_SOURCE_AUDIT"]).read_text())
canopy = [row for row in audit["flora_settings"] if row["tags"] == "FloraWorldCanopy"]
assets = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
dest = "/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy/StaticDistantLeaves"
assets.make_directory(dest)
prop = u.MaterialProperty.MP_WORLD_POSITION_OFFSET
results = {}

for tree in canopy:
    species = tree["mesh"]
    (leaf,) = [path for path in tree["materials"] if "/MI_Path_Leaf_" in path]
    source = u.load_asset(leaf)
    ancestors = [source]
    while isinstance(ancestors[-1], u.MaterialInstanceConstant):
        ancestors.append(ancestors[-1].get_editor_property("parent"))
    master = ancestors[-1]
    wind = edit.get_material_property_input_node(master, prop)
    assert isinstance(wind, u.MaterialExpressionCustom)
    code = "".join(wind.get_editor_property("code").split())
    assert "1-smoothstep(2500.,5500.,distance(P,Camera))" in code and code.endswith(
        "*gust*Amount*fade;"
    )
    paths = [asset.get_path_name().split(".")[0] for asset in reversed(ancestors)]
    digest = hashlib.sha256()
    for path in paths:
        assert path.startswith("/Game/GrandTour/ArtTests/LidarStudy/")
        package = (root / "Content" / path.removeprefix("/Game/")).with_suffix(".uasset")
        digest.update(package.read_bytes())
    version = digest.hexdigest()[:12]
    parent = None
    for i, path in enumerate(paths):
        name = f"{dest}/{species}_{version}_{i}"
        copy = (
            u.load_asset(name)
            if assets.does_asset_exist(name)
            else assets.duplicate_asset(path, name)
        )
        assert copy and copy.get_path_name().split(".")[0] == name
        if parent is None:
            if edit.get_material_property_input_node(copy, prop):
                assert edit.disconnect_material_property(copy, prop)
                assert not edit.recompile_material(copy)
            assert not edit.get_material_property_input_node(copy, prop)
        else:
            edit.set_material_instance_parent(copy, parent)
        assert assets.save_loaded_asset(copy, False)
        parent = copy
    results[species] = dict(source=source.get_path_name(), material=parent.get_path_name())
assert set(results) == {f"SM_Canopy_{kind}" for kind in range(3)}
output = root / "Art/Export/LidarStudy/FloraWorld/static-leaf-study.json"
output.write_text(json.dumps(results, indent=2))
u.log("GT_STATIC_LEAVES_READY species=3")
