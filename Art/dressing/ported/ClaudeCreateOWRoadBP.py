"""RD2 fix (Docs/RoadDressingRoundPlan.md): the vendor BP_SplineRoad_ME_01
ships with EMPTY mesh slots that are NOT instance-editable (set_editor_property
refuses them on instances - CPF_DisableEditOnInstance). Vendor edits are
forbidden, so: duplicate the BP into /Game/OWGame and bake the demo recipe
into OUR copy's class defaults. Roads dragged from BP_OWRoad spawn complete;
Road Material / Road Width remain per-instance (they ARE instance-editable).

RUN IN-EDITOR:  py "C:/GrandTour/Art/dressing/ported/ClaudeCreateOWRoadBP.py"
Rerunnable (get-or-create; defaults reapplied every run).
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


PACK = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment"
DONOR_BP = f"{PACK}/Blueprints/BP_SplineRoad_ME_01"
ROADS_DIR = "/Game/OWGame/Dev/DressingLab/Roads"
OW_BP = f"{ROADS_DIR}/BP_OWRoad"

DEFAULTS = {
    "Road Mesh": f"{PACK}/Meshes/SplineRoad/SM_SplineRoad_ME_01_Tile",
    "Road Mesh Start": f"{PACK}/Meshes/SplineRoad/SM_SplineRoad_ME_01_Start",
    "Road Mesh End": f"{PACK}/Meshes/SplineRoad/SM_SplineRoad_ME_01_End",
    # Demo recipe: the road draws EXCLUSIVELY into the RVT and the
    # landscape displays the composite back (feedback-off sample - see
    # ClaudeSetupDressingLab.py lab_material). Draw in RVT = None was the
    # interim main-pass fallback; with the display path fixed, the RVT
    # route is the pack-intended one and roads melt into the ground.
    "Draw in RVT": "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material",
    "Road Material": f"{ROADS_DIR}/MI_OWRoad_Mud",
}
SCALAR_DEFAULTS = {"Road Width": 400.0, "Road Length": 400.0}

# RL2 v2 (typed road dressing, user 2026-07-29): road TYPE = which BP you
# drag. Dusty/Gravel are sibling DUPLICATES of BP_OWRoad (NOT children -
# PCG's ByClass getter is IsA-based, PCGActorSelector.cpp:100, so child
# classes would also match the parent's getter and double-dress). Each
# bakes its type MI into the CDO; PCG_OWRoad keys a dressing recipe off
# each class. Per-instance "Road Material" overrides still retint a road,
# but DRESSING follows the BP class.
TYPED_BPS = {
    f"{ROADS_DIR}/BP_OWRoad_Dusty": f"{ROADS_DIR}/MI_OWRoad_Dusty",
    f"{ROADS_DIR}/BP_OWRoad_Gravel": f"{ROADS_DIR}/MI_OWRoad_Gravel",
}

REPORT_PATH = Path(__file__).with_name("ClaudeCreateOWRoadBPReport.json")

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
            unreal.log_error(f"OWROADBP {name}: {exc!r}")
            return None

    return decorate


def _set_cdo(cdo, member, value):
    last_exc = None
    for name in (member, member.replace(" ", "_")):
        try:
            cdo.set_editor_property(name, value)
            got = cdo.get_editor_property(name)
            if value is None:
                ok = got is None
            elif isinstance(value, unreal.Object):
                ok = got is not None and got.get_path_name() == value.get_path_name()
            else:
                ok = abs(float(got) - float(value)) < 1e-3
            if not ok:
                raise RuntimeError(f"read-back mismatch: {got}")
            return name
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"CDO set failed for '{member}': {last_exc!r}")


def _author_road_bp(bp_path, donor_path, defaults):
    eal = unreal.EditorAssetLibrary
    if not eal.does_asset_exist(bp_path):
        if eal.duplicate_asset(donor_path, bp_path) is None:
            raise RuntimeError(f"duplicate_asset failed for {bp_path}")
    bp = unreal.load_asset(bp_path)
    cdo = unreal.get_default_object(bp.generated_class())
    applied = {}
    for member, path in defaults.items():
        asset = None
        if path is not None:
            asset = unreal.load_asset(path)
            if asset is None:
                raise RuntimeError(f"asset load failed: {path}")
        applied[member] = _set_cdo(cdo, member, asset)
    for member, v in SCALAR_DEFAULTS.items():
        applied[member] = _set_cdo(cdo, member, v)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    if not eal.save_loaded_asset(bp, only_if_is_dirty=False):
        raise RuntimeError(f"save failed for {bp_path}")
    status = str(bp.get_editor_property("status"))
    if "ERROR" in status:
        raise RuntimeError(f"{bp_path} compile status {status}")
    return {"applied": applied, "compile_status": status}


@step("create_ow_road_bp")
def create_ow_road_bp():
    return _author_road_bp(OW_BP, DONOR_BP, DEFAULTS)


@step("create_typed_road_bps")
def create_typed_road_bps():
    out = {}
    for bp_path, mi_path in TYPED_BPS.items():
        defaults = dict(DEFAULTS)
        defaults["Road Material"] = mi_path
        # Duplicate OUR baked BP (not the vendor) so the demo recipe
        # carries over even if the vendor donor changes.
        out[bp_path] = _author_road_bp(bp_path, OW_BP, defaults)
    return out


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"BP_OWRoad creation failed - see {REPORT_PATH}")
unreal.log("OWROADBP ready: drag /Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad "
           "into the level - tiles appear as soon as the spline is > 4m")
