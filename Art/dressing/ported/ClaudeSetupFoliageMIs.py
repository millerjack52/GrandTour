"""Create OWGame-owned material instances for the Kasyanik trees + dump params.

RUN IN-EDITOR: py "C:/GrandTour/Art/dressing/ported/ClaudeSetupFoliageMIs.py"

Vendor rule: MM_Foliage/MM_Trunk and the MI_* originals under /Game/Materials
are never edited. This script DUPLICATES the six species MIs into
/Game/OWGame/Dev/DressingLab/TreeMIs/ (duplicates keep their parent master, so
all of the master's exposed parameters stay live) and dumps every exposed
parameter name + current value into the report so the color knobs are known.

Tuning then happens on MI_OW* ONLY - open one, drag sliders, watch a placed
tree that uses it update live.
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


VENDOR_MI_DIR = "/Game/Materials/MaterialInstances"
OWN_DIR = "/Game/OWGame/Dev/DressingLab/TreeMIs"
SPECIES = ["Beech", "Birch", "FirTree"]
KINDS = ["Foliage", "Trunk"]
MASTERS = ["/Game/Materials/MM_Foliage", "/Game/Materials/MM_Trunk"]
REPORT_PATH = Path(__file__).with_name("ClaudeSetupFoliageMIsReport.json")

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
            unreal.log_error(f"FOLIAGE_MI {name}: {exc!r}")
            return None

    return decorate


@step("master_parameters")
def master_parameters():
    """Dump every parameter the masters expose (these appear on all MIs)."""
    mel = unreal.MaterialEditingLibrary
    out = {}
    for path in MASTERS:
        mat = unreal.load_asset(path)
        if mat is None:
            raise RuntimeError(f"missing master {path}")
        out[path] = {
            "vector": [str(n) for n in mel.get_vector_parameter_names(mat)],
            "scalar": [str(n) for n in mel.get_scalar_parameter_names(mat)],
            "texture": [str(n) for n in mel.get_texture_parameter_names(mat)],
        }
    return out


@step("duplicate_mis")
def duplicate_mis():
    made = []
    for kind in KINDS:
        for species in SPECIES:
            src = f"{VENDOR_MI_DIR}/MI_{kind}_{species}"
            dst = f"{OWN_DIR}/MI_OW{kind}_{species}"
            if not unreal.EditorAssetLibrary.does_asset_exist(dst):
                if unreal.EditorAssetLibrary.duplicate_asset(src, dst) is None:
                    raise RuntimeError(f"duplicate failed: {src} -> {dst}")
            unreal.EditorAssetLibrary.save_asset(dst, only_if_is_dirty=False)
            made.append(dst)
    return made


@step("mi_current_values")
def mi_current_values():
    """Record each new MI's overridden values so tuning starts from knowns."""
    out = {}
    for kind in KINDS:
        for species in SPECIES:
            mi = unreal.load_asset(f"{OWN_DIR}/MI_OW{kind}_{species}")
            if mi is None:
                continue
            vals = {}
            for spv in mi.get_editor_property("scalar_parameter_values"):
                info = spv.get_editor_property("parameter_info")
                vals[str(info.get_editor_property("name"))] = round(
                    float(spv.get_editor_property("parameter_value")), 4)
            for vpv in mi.get_editor_property("vector_parameter_values"):
                info = vpv.get_editor_property("parameter_info")
                c = vpv.get_editor_property("parameter_value")
                vals[str(info.get_editor_property("name"))] = [
                    round(float(c.r), 4), round(float(c.g), 4),
                    round(float(c.b), 4), round(float(c.a), 4)]
            out[f"MI_OW{kind}_{species}"] = vals
    return out


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log("FOLIAGE_MI complete - OW-owned tree MIs ready in " + OWN_DIR)
