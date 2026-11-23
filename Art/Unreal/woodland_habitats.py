"""Editor entry point for the LiDAR woodland community authoring pass."""

from array import array
import json
import os
from pathlib import Path
import sys
import traceback
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(root / "Art/Unreal"))
out = root / "Saved/WoodlandHabitats"
base = "/Game/GrandTour/ArtTests/LidarStudy"
stage = os.environ["GT_HABITAT_STAGE"]
receipt = dict(run=os.environ["GT_HABITAT_RUN"], ok=False)
try:
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert levels.load_level(base + "/L_LidarStudy")
    rows = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    if stage == "Prepare":
        xy = array("f")
        owners = {}
        for a in rows:
            label = a.get_actor_label()
            if label == "LidarStudy_FloraWorld_Canopy":
                for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                    if c.visible and not c.hidden_in_game and c.static_mesh:
                        for i in range(c.get_instance_count()):
                            p = c.get_instance_transform(i, True).translation
                            xy.extend((p.x, p.y))
            if isinstance(a, u.LandscapeProxy):
                owners["terrain"] = a.landscape_material.get_path_name()
            if isinstance(a, u.GTProceduralGround):
                owners["relief"] = a.relief_material.get_path_name()
            if isinstance(a, u.GTMudRunnerVisual):
                owners["detail"] = a.material.get_path_name()
        assert len(xy) > 2000
        with (out / "canopy.xy").open("wb") as f:
            xy.tofile(f)
        receipt.update(canopy=len(xy) // 2, ground_materials=owners)
    else:
        import woodland_community

        receipt.update(woodland_community.run(root, out, rows, levels, stage))
    receipt["ok"] = True
except Exception:
    receipt["error"] = traceback.format_exc()
    raise
finally:
    (out / (stage + ".json")).write_text(json.dumps(receipt, indent=2))
