"""RD1 of Docs/RoadDressingRoundPlan.md: author the OW road-type MI
library under /Game/OWGame/Dev/DressingLab/Roads (duplicate-then-edit
from the pack mud MI; vendor untouched). Types are DATA - edit the
TYPES table, rerun.

RUN HEADLESS with the editor CLOSED (asset creation; PowerShell):
  & 'C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe'
    C:\\GrandTour\\GrandTour.uproject -run=PythonScript
    "-Script=C:/GrandTour/Art/dressing/ported/ClaudeAuthorRoadTypes.py"
    -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"
Fresh-session verify: ClaudeVerifyRoadTypes.py (same folder)

Recipes per RD0 audit: dusty = mud N/H + lifted warm tint + rougher +
tighter noise dissolve; gravel = tiling rock albedo at high UV scale
(EXPERIMENTAL - user judges, swap-cheap).
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


PACK = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment"
DONOR = f"{PACK}/Materials/Instances/SplineRoad/MI_SplineRoad_ME_Mud_01"
OUT_DIR_PATH = "/Game/OWGame/Dev/DressingLab/Roads"

MUD_A = f"{PACK}/Textures/SplineRoad/T_SplineRoad_ME_Mud_01_A"
MUD_N = f"{PACK}/Textures/SplineRoad/T_SplineRoad_ME_Mud_01_N"
MUD_R = f"{PACK}/Textures/SplineRoad/T_SplineRoad_ME_Mud_01_R"
MUD_H = f"{PACK}/Textures/SplineRoad/T_SplineRoad_ME_Mud_01_H"
ROCK_A = f"{PACK}/Textures/Rocks/T_Rock_01_A"

# name -> dict(textures={param: path}, scalars={param: value},
#              vectors={param: (r,g,b,a)}[, donor=<duplicate source>])
TYPES = {
    "MI_OWRoad_Mud": dict(     # pack baseline, our copy = stable handle
        textures={}, scalars={}, vectors={}),
    # RL1 (Docs/RoadLookRoundPlan.md): landscape-SPLINE-segment material
    # for the user-drawn deformed road bed. Duplicate of the pack's
    # MI_SplineLandscape_ME_01 (parent = M_SplineRoad_ME_01 per RD0),
    # params as-is initially - the user tunes it on their spline.
    "MI_OWRoadBed": dict(
        donor=(f"{PACK}/Materials/Instances/SplineRoad/"
               "MI_SplineLandscape_ME_01"),
        textures={}, scalars={}, vectors={}),
    "MI_OWRoad_Dusty": dict(
        textures={},           # keeps mud N/R/H; albedo stays mud, tint lifts it
        scalars={"Base Roughness Intensity": 1.3,
                 "Mask Noise UV Scale": 2.0,
                 "Base UV Scale X": 1.2, "Base UV Scale Y": 1.2},
        vectors={"Base Albedo Tint": (0.75, 0.68, 0.55, 0.0),
                 "Base Albedo Tint Edge": (0.70, 0.64, 0.52, 0.0)}),
    "MI_OWRoad_Gravel": dict(
        textures={"Base Albedo": ROCK_A},
        scalars={"Base UV Scale X": 3.0, "Base UV Scale Y": 3.0,
                 "Base Roughness Intensity": 1.15,
                 "Mask Noise UV Scale": 1.5},
        vectors={"Base Albedo Tint": (0.55, 0.55, 0.55, 0.0),
                 "Base Albedo Tint Edge": (0.50, 0.50, 0.50, 0.0)}),
}

REPORT_PATH = Path(__file__).with_name("ClaudeAuthorRoadTypesReport.json")

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
            unreal.log_error(f"ROADTYPES {name}: {exc!r}")
            return None

    return decorate


@step("author_types")
def author_types():
    lib = unreal.MaterialEditingLibrary
    eal = unreal.EditorAssetLibrary
    out = {}
    for name, spec in TYPES.items():
        path = f"{OUT_DIR_PATH}/{name}"
        if not eal.does_asset_exist(path):
            if eal.duplicate_asset(spec.get("donor", DONOR), path) is None:
                raise RuntimeError(f"duplicate_asset failed for {name} "
                                   "(editor open?)")
        mi = unreal.load_asset(path)
        if not isinstance(mi, unreal.MaterialInstanceConstant):
            raise RuntimeError(f"{name}: not a MaterialInstanceConstant")
        # PITFALL (UE 5.8, paid 2026-07-28): the MaterialEditingLibrary
        # set_material_instance_*_parameter_value functions return False
        # UNCONDITIONALLY (engine bug: bResult never set true). Never
        # branch on the return - set, then verify by read-back.
        for pn, tex_path in spec["textures"].items():
            tex = unreal.load_asset(tex_path)
            if tex is None:
                raise RuntimeError(f"{name}: texture load failed {tex_path}")
            lib.set_material_instance_texture_parameter_value(mi, pn, tex)
            got = lib.get_material_instance_texture_parameter_value(mi, pn)
            if got is None or got.get_path_name().split(".")[0] != tex_path:
                raise RuntimeError(f"{name}: texture read-back failed: {pn} = {got}")
        for pn, v in spec["scalars"].items():
            lib.set_material_instance_scalar_parameter_value(mi, pn, float(v))
            got = float(lib.get_material_instance_scalar_parameter_value(mi, pn))
            if abs(got - float(v)) > 1e-3:
                raise RuntimeError(f"{name}: scalar read-back failed: {pn} = {got}")
        for pn, v in spec["vectors"].items():
            col = unreal.LinearColor(r=v[0], g=v[1], b=v[2], a=v[3])
            lib.set_material_instance_vector_parameter_value(mi, pn, col)
            g = lib.get_material_instance_vector_parameter_value(mi, pn)
            if any(abs(a - b) > 1e-3 for a, b in zip((g.r, g.g, g.b, g.a), v)):
                raise RuntimeError(f"{name}: vector read-back failed: {pn} = {g}")
        lib.update_material_instance(mi)
        if not eal.save_loaded_asset(mi, only_if_is_dirty=False):
            raise RuntimeError(f"save failed for {name}")
        out[name] = f"{path} saved ({len(spec['textures'])} tex, " \
                    f"{len(spec['scalars'])} scalar, {len(spec['vectors'])} vector overrides)"
    return out


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
unreal.log(f"ROADTYPES report -> {REPORT_PATH}")
if not result["ok"]:
    raise RuntimeError("road type authoring had failed steps - read the report")
