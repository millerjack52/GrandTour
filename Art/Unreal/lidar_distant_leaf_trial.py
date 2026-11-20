"""Swap only the leaf wind output beyond its tested zero-displacement distance."""

import json
import math
from pathlib import Path

import unreal as u

root = Path(u.Paths.project_dir()).resolve()
records = json.loads((root / "Art/Export/LidarStudy/FloraWorld/static-leaf-study.json").read_text())
world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
distance_scale = u.SystemLibrary.get_console_variable_float_value("r.ViewDistanceScale")
if u.SystemLibrary.get_console_variable_int_value("r.ViewDistanceScale.ApplySecondaryScale"):
    distance_scale *= u.SystemLibrary.get_console_variable_float_value(
        "r.ViewDistanceScale.SecondaryScale"
    )
changes = []
for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
    for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        tags = {str(t) for t in comp.component_tags}
        if "FloraWorldCanopy" not in tags or "TrialNearCanopy" in tags or not comp.is_visible():
            continue
        mesh = comp.static_mesh
        material = records[mesh.get_name()]
        (slot,) = [
            i for i, m in enumerate(comp.get_materials()) if m.get_path_name() == material["source"]
        ]
        start_cm = comp.get_editor_property("instance_min_draw_distance")
        assert comp.get_editor_property("instance_end_cull_distance") > start_cm > 5500
        extent = mesh.get_bounds().box_extent
        max_radius = 0
        for i in range(comp.get_instance_count()):
            scale = comp.get_instance_transform(i, world_space=True).scale3d
            radius = math.sqrt(
                (extent.x * scale.x) ** 2 + (extent.y * scale.y) ** 2 + (extent.z * scale.z) ** 2
            )
            max_radius = max(max_radius, radius)
        nearest = start_cm * distance_scale - max_radius
        assert nearest > 5500, (mesh.get_name(), nearest, max_radius)
        static = u.load_asset(material["material"])
        assert static
        changes.append((comp, slot, static))
        u.log(f"GT_STATIC_LEAF_MARGIN mesh={mesh.get_name()} nearest_vertex_cm={nearest:.1f}")
assert len(changes) == 3
for comp, slot, static in changes:
    comp.set_material(slot, static)
    comp.set_evaluate_world_position_offset(False)
    assert comp.get_material(slot) == static
u.log("GT_STATIC_LEAF_RANGE groups=3")
