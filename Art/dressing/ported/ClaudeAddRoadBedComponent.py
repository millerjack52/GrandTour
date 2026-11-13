"""Add UOWRoadBedComponent (the per-road "Apply Bed & Verge" Details
button) to the three typed road BPs. Run AFTER the C++ build that
introduces the component class (in GrandTour, unreal.OWRoadBedComponent
lives in the GrandTour runtime module; a CoreRedirect maps the old path).

RUN HEADLESS, EDITOR CLOSED (PowerShell):
  & 'C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe'
    C:\\GrandTour\\GrandTour.uproject -run=PythonScript
    "-Script=C:/GrandTour/Art/dressing/ported/ClaudeAddRoadBedComponent.py"
    -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"

Rerunnable (get-or-add). ADD-only: never deletes BP components (headless
deletion breaks event-graph references - paid pitfall).
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal

ROADS_DIR = "/Game/OWGame/Dev/DressingLab/Roads"
ROAD_BPS = [f"{ROADS_DIR}/BP_OWRoad",
            f"{ROADS_DIR}/BP_OWRoad_Dusty",
            f"{ROADS_DIR}/BP_OWRoad_Gravel"]

REPORT_PATH = Path(__file__).with_name("ClaudeAddRoadBedComponentReport.json")
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
                "ok": False, "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            unreal.log_error(f"ROADBEDCOMP {name}: {exc!r}")
            return None
    return decorate


def _has_component(sub, bp, cls):
    for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
        if obj is not None and isinstance(obj, cls):
            return True
    return False


def _add_to(bp_path):
    bp = unreal.load_asset(bp_path)
    if bp is None:
        raise RuntimeError(f"load failed: {bp_path}")
    cls = unreal.OWRoadBedComponent           # exists only after the build
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    added = False
    if not _has_component(sub, bp, cls):
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
        params = unreal.AddNewSubobjectParams(
            parent_handle=handles[0], new_class=cls, blueprint_context=bp)
        handle, fail = sub.add_new_subobject(params)
        if not unreal.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(handle):
            raise RuntimeError(f"add_new_subobject failed on {bp_path}: {fail}")
        added = True
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {bp_path}")
    status = str(bp.get_editor_property("status"))
    if "ERROR" in status:
        raise RuntimeError(f"{bp_path} compile status {status}")
    # read-back in the same session; the fresh-session proof is the
    # button appearing in the Details panel.
    if not _has_component(sub, bp, cls):
        raise RuntimeError(f"{bp_path}: component missing after add")
    return {"added" if added else "already_present": True, "compile": status}


for _p in ROAD_BPS:
    step(_p.rsplit("/", 1)[-1])(lambda p=_p: _add_to(p))

REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
unreal.log(f"ROADBEDCOMP report -> {REPORT_PATH}")
if not result["ok"]:
    raise RuntimeError("road-bed component add FAILED - see report")
