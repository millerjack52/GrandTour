"""RD2 helper (Docs/RoadDressingRoundPlan.md): configure every
BP_SplineRoad_ME_01 actor in the OPEN level with the demo recipe - tile
meshes (the BP ships with EMPTY mesh slots and they are not instance-
editable in Details; python sets them anyway), Draw-in-RVT, width, and
one OW road-type MI per road (cycling Mud -> Dusty -> Gravel by Outliner
label order). The user draws/reshapes the splines; this script only sets
properties (author-in-editor doctrine).

REFERENCE ONLY in GrandTour (written for the source's dressing lab).

RUN IN-EDITOR with the map open (it acts on the OPEN level):
  py "C:/GrandTour/Art/dressing/ported/ClaudeSetupLabRoads.py"

Rerunnable: reapplies the recipe to however many road actors exist.
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


PACK = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment"
MESHES = {
    "Road Mesh": f"{PACK}/Meshes/SplineRoad/SM_SplineRoad_ME_01_Tile",
    "Road Mesh Start": f"{PACK}/Meshes/SplineRoad/SM_SplineRoad_ME_01_Start",
    "Road Mesh End": f"{PACK}/Meshes/SplineRoad/SM_SplineRoad_ME_01_End",
}
RVT = "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material"
TYPE_MIS = ["/Game/OWGame/Dev/DressingLab/Roads/MI_OWRoad_Mud",
            "/Game/OWGame/Dev/DressingLab/Roads/MI_OWRoad_Dusty",
            "/Game/OWGame/Dev/DressingLab/Roads/MI_OWRoad_Gravel"]
ROAD_WIDTH = 400.0

REPORT_PATH = Path(__file__).with_name("ClaudeSetupLabRoadsReport.json")

result = {"ok": True, "steps": {}}


def step(name):
    def decorate(func):
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": value}
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            unreal.log_error(f"LABROADS {name}: {exc!r}")
            return None

    return decorate


def _set(actor, member, value):
    """Set a BP variable trying space/underscore name variants; verify by
    read-back (silent-failure doctrine)."""
    last_exc = None
    for name in (member, member.replace(" ", "_")):
        try:
            actor.set_editor_property(name, value)
            got = actor.get_editor_property(name)
            if isinstance(value, unreal.Object):
                ok = got is not None and got.get_path_name() == value.get_path_name()
            else:
                ok = got == value
            if not ok:
                raise RuntimeError(f"read-back mismatch on {member}: {got}")
            return
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"could not set '{member}': {last_exc!r}")


@step("configure_roads")
def configure_roads():
    assets = {}
    for member, path in MESHES.items():
        assets[member] = unreal.load_asset(path)
        if assets[member] is None:
            raise RuntimeError(f"mesh load failed: {path}")
    rvt = unreal.load_asset(RVT)
    mis = [unreal.load_asset(p) for p in TYPE_MIS]
    if rvt is None or any(m is None for m in mis):
        raise RuntimeError("RVT or type MI failed to load")

    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    roads = sorted([a for a in actors_sub.get_all_level_actors()
                    if a.get_class().get_name() == "BP_SplineRoad_ME_01_C"],
                   key=lambda a: a.get_actor_label())
    if not roads:
        raise RuntimeError("no BP_SplineRoad_ME_01 actors in the open level")
    out = []
    for i, a in enumerate(roads):
        a.modify()
        for member, asset in assets.items():
            _set(a, member, asset)
        _set(a, "Draw in RVT", rvt)
        _set(a, "Road Width", ROAD_WIDTH)
        mi = mis[i % len(mis)]
        _set(a, "Road Material", mi)
        # Nudge the construction script (property sets alone can leave the
        # built tiles stale): re-register via a no-op transform poke.
        a.set_actor_location(a.get_actor_location(), False, False)
        out.append(f"{a.get_actor_label()}: meshes + RVT + width {ROAD_WIDTH} "
                   f"+ {mi.get_name()}")
    return out


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"lab road setup failed - see {REPORT_PATH}")
unreal.log("LABROADS configured - if tiles are not visible, nudge one spline "
           "point per road to force the construction script")
