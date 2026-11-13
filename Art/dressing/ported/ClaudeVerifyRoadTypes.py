"""Fresh-session verify for ClaudeAuthorRoadTypes.py (RD1): loads each
OW road-type MI cold and asserts parent + every authored override
matches the spec table. Run in a SEPARATE session from the author run.
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal

# EXPECTED mirrors the TYPES table in ClaudeAuthorRoadTypes.py (the
# author script executes on import, so it cannot be imported for its
# constants). Round rule: change TYPES there -> mirror here, same
# two-file doctrine as the tune/hookup pairs.

PACK = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment"
PARENT = f"{PACK}/Materials/Masters/M_SplineRoad_ME_01"
OUT_DIR_PATH = "/Game/OWGame/Dev/DressingLab/Roads"

EXPECTED = {
    "MI_OWRoad_Mud": dict(textures={}, scalars={}, vectors={}),
    # RL1: bed MI duplicated from MI_SplineLandscape_ME_01, which RD0
    # verified is ALSO parented to M_SplineRoad_ME_01 - same parent check.
    "MI_OWRoadBed": dict(textures={}, scalars={}, vectors={}),
    "MI_OWRoad_Dusty": dict(
        textures={},
        scalars={"Base Roughness Intensity": 1.3, "Mask Noise UV Scale": 2.0,
                 "Base UV Scale X": 1.2, "Base UV Scale Y": 1.2},
        vectors={"Base Albedo Tint": (0.75, 0.68, 0.55, 0.0),
                 "Base Albedo Tint Edge": (0.70, 0.64, 0.52, 0.0)}),
    "MI_OWRoad_Gravel": dict(
        textures={"Base Albedo": f"{PACK}/Textures/Rocks/T_Rock_01_A"},
        scalars={"Base UV Scale X": 3.0, "Base UV Scale Y": 3.0,
                 "Base Roughness Intensity": 1.15, "Mask Noise UV Scale": 1.5},
        vectors={"Base Albedo Tint": (0.55, 0.55, 0.55, 0.0),
                 "Base Albedo Tint Edge": (0.50, 0.50, 0.50, 0.0)}),
}

REPORT_PATH = Path(__file__).with_name("ClaudeVerifyRoadTypesReport.json")

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
            unreal.log_error(f"ROADVERIFY {name}: {exc!r}")
            return None

    return decorate


def _make_step(mi_name, spec):
    @step(mi_name)
    def _check():
        lib = unreal.MaterialEditingLibrary
        mi = unreal.load_asset(f"{OUT_DIR_PATH}/{mi_name}")
        if not isinstance(mi, unreal.MaterialInstanceConstant):
            raise RuntimeError("missing or wrong type on disk")
        parent = mi.get_editor_property("parent")
        if parent is None or parent.get_path_name().split(".")[0] != PARENT:
            raise RuntimeError(f"parent mismatch: {parent}")
        for pn, tex_path in spec["textures"].items():
            t = lib.get_material_instance_texture_parameter_value(mi, pn)
            got = t.get_path_name().split(".")[0] if t else None
            if got != tex_path:
                raise RuntimeError(f"texture {pn}: {got} != {tex_path}")
        for pn, want in spec["scalars"].items():
            got = float(lib.get_material_instance_scalar_parameter_value(mi, pn))
            if abs(got - want) > 1e-3:
                raise RuntimeError(f"scalar {pn}: {got} != {want}")
        for pn, want in spec["vectors"].items():
            v = lib.get_material_instance_vector_parameter_value(mi, pn)
            got = (v.r, v.g, v.b, v.a)
            if any(abs(g - w) > 1e-3 for g, w in zip(got, want)):
                raise RuntimeError(f"vector {pn}: {got} != {want}")
        return "parent + all overrides verified"
    return _check


for _name, _s in EXPECTED.items():
    _make_step(_name, _s)

REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
unreal.log(f"ROADVERIFY report -> {REPORT_PATH}")
if not result["ok"]:
    raise RuntimeError("road type verify FAILED - read the report")
