# Meadow flowers (detail pass 2026-07-28): tinted flower-clump grass built
# from MW pack stock - duplicated grass meshes wearing color-shifted MIs,
# bundled into LGT_OWMeadowFlowers. ClaudeSetupDressingLab.py wires the
# "MeadowFlowers" grass pin to OW_Meadow (run THIS script first, or the lab
# script's get-or-create makes a plain green duplicate instead).
#
# Headless run (editor CLOSED; PowerShell):
#   & 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
#     C:\GrandTour\GrandTour.uproject -run=PythonScript
#     "-Script=C:/GrandTour/Art/dressing/ported/ClaudeSetupMeadowFlowers.py"
#     -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"
#
# Soft-fails by design: if the MW grass material chain exposes no color/tint
# vector parameter, the report says so and NOTHING is created - flowers then
# need a bespoke material pass instead of a recolor.
import json
import traceback
from pathlib import Path

import unreal

REPORT_PATH = str(Path(__file__).with_name("ClaudeSetupMeadowFlowersReport.json"))

ASSET_DIR = "/Game/OWGame/Dev/DressingLab"
DONOR_LGT = ASSET_DIR + "/LGT_OWMeadowGrass"
SOURCE_MESHES = [
    "/Game/MWLandscapeAutoMaterial/Meshes/Plants/SM_MWAM_GrassA",
    "/Game/MWLandscapeAutoMaterial/Meshes/Plants/SM_MWAM_GrassB",
    "/Game/MWLandscapeAutoMaterial/Meshes/Plants/SM_MWAM_GrassC",
]
# (suffix, tint) - painterly flower-head colors, kept soft.
TINTS = [
    ("White", unreal.LinearColor(0.92, 0.92, 0.85, 1.0)),
    ("Yellow", unreal.LinearColor(0.95, 0.78, 0.22, 1.0)),
    ("Violet", unreal.LinearColor(0.58, 0.45, 0.85, 1.0)),
]
FLOWER_LGT = ASSET_DIR + "/LGT_OWMeadowFlowers"

report = {"ok": True, "steps": {}}
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary


def step(name):
    def deco(fn):
        def wrap(*a, **k):
            try:
                r = fn(*a, **k)
                report["steps"][name] = {"ok": True, "result": r}
                return r
            except Exception as exc:  # noqa: BLE001
                report["steps"][name] = {
                    "ok": False,
                    "error": "{}: {}".format(type(exc).__name__, exc),
                    "trace": traceback.format_exc(),
                }
                report["ok"] = False
                raise
        return wrap
    return deco


def base_material_of(mat_interface):
    m = mat_interface
    while isinstance(m, unreal.MaterialInstanceConstant):
        m = m.get_editor_property("parent")
    return m


@step("find_color_param")
def find_color_param():
    mesh = eal.load_asset(SOURCE_MESHES[0])
    if mesh is None:
        raise RuntimeError("MW grass mesh missing: " + SOURCE_MESHES[0])
    slot_mat = mesh.get_material(0)
    if slot_mat is None:
        raise RuntimeError("MW grass mesh has no material in slot 0")
    base = base_material_of(slot_mat)
    names = [str(n) for n in mel.get_vector_parameter_names(base)]
    # Tint EVERY color-ish param: on the MW master the albedo recolor is
    # MW_BaseColorCorrection while MW_SubSurfaceColor only shifts the SSS -
    # setting just the first pick left the clumps green (first run).
    picks = [n for n in names if "color" in n.lower() or "tint" in n.lower()]
    result = {"slot_material": slot_mat.get_path_name(),
              "base_material": base.get_path_name(),
              "vector_params": names, "picked": picks}
    if not picks:
        # Soft fail: report and stop - a recolor is not possible here.
        report["no_color_param"] = True
        raise RuntimeError("no color/tint vector parameter on the MW grass "
                           "material - flowers need a bespoke material pass")
    return result


@step("flower_meshes")
def flower_meshes(slot_mat_path, param_names):
    parent = eal.load_asset(slot_mat_path)
    made = []
    for (suffix, tint), src in zip(TINTS, SOURCE_MESHES):
        mi_path = "{}/MI_OWFlower_{}".format(ASSET_DIR, suffix)
        if not eal.does_asset_exist(mi_path):
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            mi = tools.create_asset("MI_OWFlower_" + suffix, ASSET_DIR,
                                    unreal.MaterialInstanceConstant,
                                    unreal.MaterialInstanceConstantFactoryNew())
            mel.set_material_instance_parent(mi, parent)
        else:
            mi = eal.load_asset(mi_path)
        for pn in param_names:
            mel.set_material_instance_vector_parameter_value(mi, pn, tint)
        eal.save_loaded_asset(mi, only_if_is_dirty=False)

        mesh_path = "{}/SM_OWFlowerClump_{}".format(ASSET_DIR, suffix)
        if not eal.does_asset_exist(mesh_path):
            if eal.duplicate_asset(src, mesh_path) is None:
                raise RuntimeError("duplicate_asset failed: " + mesh_path)
        mesh = eal.load_asset(mesh_path)
        mesh.set_material(0, mi)
        eal.save_loaded_asset(mesh, only_if_is_dirty=False)
        made.append(mesh_path)
    return made


@step("flower_grass_type")
def flower_grass_type(mesh_paths):
    if not eal.does_asset_exist(FLOWER_LGT):
        if eal.duplicate_asset(DONOR_LGT, FLOWER_LGT) is None:
            raise RuntimeError("duplicate_asset failed: " + FLOWER_LGT)
    lgt = eal.load_asset(FLOWER_LGT)
    varieties = lgt.get_editor_property("grass_varieties")
    tuned = []
    for i, gv in enumerate(varieties):
        gv.set_editor_property("grass_mesh",
                               eal.load_asset(mesh_paths[i % len(mesh_paths)]))
        for prop, val in (("grass_density", 25.0),
                          ("start_cull_distance", 3750),
                          ("end_cull_distance", 5000)):
            pp = gv.get_editor_property(prop)
            pp.set_editor_property("default", val)
            gv.set_editor_property(prop, pp)
        gv.set_editor_property("cast_dynamic_shadow", False)
        tuned.append(gv)
    lgt.set_editor_property("grass_varieties", tuned)
    lgt.modify()
    if not eal.save_loaded_asset(lgt, only_if_is_dirty=False):
        raise RuntimeError("save failed: " + FLOWER_LGT)
    return {"varieties": len(tuned), "meshes": mesh_paths}


try:
    info = find_color_param()
    meshes = flower_meshes(info["slot_material"], info["picked"])
    flower_grass_type(meshes)
finally:
    with open(REPORT_PATH, "w") as fh:
        json.dump(report, fh, indent=2)

if not report["ok"]:
    raise RuntimeError("ClaudeSetupMeadowFlowers failed; see report")
