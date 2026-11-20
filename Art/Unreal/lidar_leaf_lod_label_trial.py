"""Apply the study mesh to its original component and keep each painted material."""

import json
from pathlib import Path

import unreal as u

root = Path(u.Paths.project_dir()).resolve()
record = json.loads((root / "Art/Export/LidarStudy/FloraWorld/leaf-lod-labels.json").read_text())
world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
trees = [
    c
    for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
    for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
    if c.static_mesh
    and c.static_mesh.get_path_name() == record["source"]
    and c.is_visible()
    and "FloraWorldCanopy" in {str(t) for t in c.component_tags}
]
(tree,) = trees
original = list(tree.get_materials())
assert [m.get_path_name() for m in original] == record["materials"]
instances = tree.get_instance_count()
assert tree.get_editor_property("override_min_lod") and tree.get_editor_property("min_lod") == 1
mesh = u.load_asset(record["mesh"])
expected = original + [s.material_interface for s in mesh.static_materials[len(original) :]]
assert len(expected) == 5
mobility = tree.mobility
tree.set_mobility(u.ComponentMobility.MOVABLE)
try:
    assert tree.set_static_mesh(mesh)
    for i, mat in enumerate(expected):
        tree.set_material(i, mat)
finally:
    tree.set_mobility(mobility)
assert tree.static_mesh == mesh and list(tree.get_materials()) == expected
assert tree.get_instance_count() == instances and tree.mobility == mobility
u.log(f"GT_D003_LOD_LABELS_BOUND lods=4 leaf_labels=2 instances={instances}")
