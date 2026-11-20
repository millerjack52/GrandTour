"""Apply the corrected bark coordinates only to the temporary near-tree groups."""

import json
from pathlib import Path

import unreal as u

world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
root = Path(u.Paths.project_dir()).resolve()
records = json.loads(
    (root / "Art/Export/LidarStudy/FloraWorld/bark-coordinate-study.json").read_text()
)
changes = []
for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
    for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        if "TrialNearCanopy" not in {str(t) for t in comp.component_tags}:
            continue
        name = comp.static_mesh.get_name()
        record = records[name]
        (slot,) = [
            i
            for i, mat in enumerate(comp.get_materials())
            if mat.get_path_name() == record["source"]
        ]
        mat = u.load_asset(record["material"])
        strength = mat.get_scalar_parameter_value("BarkMossStrength")
        assert strength > 0 and strength == comp.get_material(slot).get_scalar_parameter_value(
            "BarkMossStrength"
        )
        changes.append((comp, slot, mat, strength))
assert len(changes) == 3 and len({c.static_mesh.get_name() for c, _, _, _ in changes}) == 3
for comp, slot, mat, strength in changes:
    comp.set_material(slot, mat)
    assert comp.get_material(slot) == mat
    u.log(f"GT_BARK_COORDINATE_BIND mesh={comp.static_mesh.get_name()} source_strength={strength}")
