"""Keep the painted bark formula and drive it with explicit instance coordinates."""

import hashlib
import json
from pathlib import Path
import sys

import unreal as u

root = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(root / "Art/Unreal"))
from benmore_river_life_materials import Graph

assets = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
study = "/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy"
folder = study + "/BarkCoordinates"
assets.make_directory(folder)
records = {}
space = u.MaterialPositionTransformSource
instance_space = space.TRANSFORMPOSSOURCE_INSTANCE
world_space = space.TRANSFORMPOSSOURCE_WORLD


def transform(graph, position, source, target):
    node = graph.node(
        u.MaterialExpressionTransformPosition, transform_source_type=source, transform_type=target
    )
    graph.wire(position, node, "")
    return node


for kind in range(3):
    mesh = u.load_asset(f"{study}/SM_NaniteRenderLod1_{kind}")
    assert mesh
    (wood,) = [
        s.material_interface
        for s in mesh.static_materials
        if "Path_Wood" in s.material_interface.get_name()
    ]
    chain = [wood]
    while isinstance(chain[-1], u.MaterialInstanceConstant):
        chain.append(chain[-1].get_editor_property("parent"))
    digest = hashlib.sha256(Path(__file__).read_bytes())
    for item in chain:
        package = item.get_path_name().split(".")[0]
        assert package.startswith(study + "/NanitePaint/")
        digest.update(
            (root / "Content" / package.removeprefix("/Game/")).with_suffix(".uasset").read_bytes()
        )
    version = digest.hexdigest()[:12]
    parent = None
    for index, item in enumerate(reversed(chain)):
        dest = f"{folder}/Bark_{kind}_{index}_{version}"
        new = not assets.does_asset_exist(dest)
        copy = (
            assets.duplicate_asset(item.get_path_name().split(".")[0], dest)
            if new
            else u.load_asset(dest)
        )
        assert copy and copy != item
        if new and parent is None:
            nodes = list(edit.get_material_expressions(copy))
            (moss,) = [
                n
                for n in nodes
                if isinstance(n, u.MaterialExpressionCustom)
                and "float moss=" in str(n.get_editor_property("code"))
            ]
            (bounds,) = [
                n
                for n in nodes
                if isinstance(n, u.MaterialExpressionBounds)
                and n.get_editor_property("desc") == "FloraReferenceVolumes"
            ]
            graph = Graph(copy, "LidarBarkInstanceCoordinates")
            world_position = graph.node(
                u.MaterialExpressionWorldPosition,
                world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS,
            )
            local = transform(graph, world_position, world_space, instance_space)
            normalized = graph.custom(
                ["P", "Lo", "Hi"], "return (P-Lo)/max(Hi-Lo,float3(.1,.1,.1));"
            )
            graph.wire(local, normalized, "P")
            graph.wire(bounds, normalized, "Lo", "Min")
            graph.wire(bounds, normalized, "Hi", "Max")
            origin = transform(graph, graph.vector([0.0, 0.0, 0.0]), instance_space, world_space)
            graph.wire(normalized, moss, "Q")
            graph.wire(origin, moss, "Centre")
            assert not edit.recompile_material(copy)
        elif new:
            edit.set_material_instance_parent(copy, parent)
        if new:
            assert assets.save_loaded_asset(copy, False)
        if parent:
            assert copy.get_editor_property("parent") == parent
        parent = copy
    records[mesh.get_name()] = dict(source=wood.get_path_name(), material=parent.get_path_name())
assert len(records) == 3
(root / "Art/Export/LidarStudy/FloraWorld/bark-coordinate-study.json").write_text(
    json.dumps(records, indent=2)
)
u.log("GT_BARK_COORDINATES_READY species=3")
