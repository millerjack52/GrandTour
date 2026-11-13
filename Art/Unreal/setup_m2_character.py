"""setup_m2_character.py - the on-foot content, headless.

Run with Art\\setup_m2_character.bat (close the editor first).
- Copies the Epic mannequin the first-person arms use (SKM_Manny_Simple, its skeleton, physics
  asset, materials, textures, the pistol aim pose and the unarmed idle) from the engine's
  template resources into Content/Characters/Mannequins, keeping Epic's /Game/Characters paths so
  the package references resolve. About 60 MB. Skipped for files that already exist.
- Writes the on-foot input assets (IA_Move ... IA_Transfer, IMC_OnFoot) and rewrites the
  driving ones (IMC_Driving now carries IA_Exit and IA_Reel) under /Game/GrandTour/Input, and the
  three tool data assets DA_Tool_Cutter / PryBar / RepairKit under /Game/GrandTour/Tools, all
  from the C++ defaults (UGTVehicleSetupLibrary). Safe to re-run: assets are rewritten.
"""
import os
import shutil

import unreal

ENGINE_MANNEQUINS = r"C:\Program Files\Epic Games\UE_5.8\Templates\TemplateResources\High\Characters\Content\Mannequins"
PROJECT_MANNEQUINS = os.path.join(unreal.Paths.project_content_dir(), "Characters", "Mannequins")
FILES = [
    r"Meshes\SKM_Manny_Simple.uasset",
    r"Meshes\SK_Mannequin.uasset",
    r"Rigs\PA_Mannequin.uasset",
    r"Rigs\CR_Mannequin_Body.uasset",
    r"Materials\M_Mannequin.uasset",
    r"Materials\Manny\MI_Manny_01_New.uasset",
    r"Materials\Manny\MI_Manny_02_New.uasset",
    r"Textures\Manny\T_Manny_01_BN.uasset",
    r"Textures\Manny\T_Manny_01_D.uasset",
    r"Textures\Manny\T_Manny_01_MRA.uasset",
    r"Textures\Manny\T_Manny_02_BN.uasset",
    r"Textures\Manny\T_Manny_02_D.uasset",
    r"Textures\Manny\T_Manny_02_MRA.uasset",
    r"Textures\Manny\T_Manny_02_N.uasset",
    r"Textures\Shared\T_UE_Logo_M.uasset",
    r"Anims\Pistol\MF_Pistol_Idle_ADS.uasset",
    r"Anims\Unarmed\MM_Idle.uasset",
]
INPUT_FOLDER = "/Game/GrandTour/Input"
TOOL_FOLDER = "/Game/GrandTour/Tools"
lib = unreal.GTVehicleSetupLibrary
eal = unreal.EditorAssetLibrary


def log(msg):
    unreal.log("SETUP_M2_CHARACTER " + msg)


# ---- mannequin ------------------------------------------------------------------------------
copied = 0
missing = []
for rel in FILES:
    src = os.path.join(ENGINE_MANNEQUINS, rel)
    dst = os.path.join(PROJECT_MANNEQUINS, rel)
    if not os.path.isfile(src):
        missing.append(rel)
        continue
    if os.path.isfile(dst):
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    copied += 1
log("copied %d mannequin files into %s (%d already there, %d missing in the engine)" % (copied, PROJECT_MANNEQUINS, len(FILES) - copied - len(missing), len(missing)))
for rel in missing:
    unreal.log_warning("SETUP_M2_CHARACTER missing in the engine: " + rel)

registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(["/Game/Characters"], True)
mesh = eal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
pose = eal.load_asset("/Game/Characters/Mannequins/Anims/Pistol/MF_Pistol_Idle_ADS")
if mesh is None or pose is None:
    raise SystemExit("mannequin mesh or pose failed to load after the copy")
skeleton = mesh.get_editor_property("skeleton")
log("arms mesh %s skeleton %s materials %d; pose %s" % (mesh.get_name(), skeleton.get_name() if skeleton else None,
                                                        len(mesh.get_editor_property("materials")), pose.get_name()))

# ---- input and tools ------------------------------------------------------------------------
saved_foot = lib.create_on_foot_input_assets(INPUT_FOLDER)
log("on-foot input assets saved: %d (expected 13)" % saved_foot)
saved_drive = lib.create_driving_input_assets(INPUT_FOLDER)
log("driving input assets rewritten: %d (expected 8)" % saved_drive)
saved_tools = lib.create_tool_assets(TOOL_FOLDER)
log("tool assets saved: %d (expected 3)" % saved_tools)
if saved_foot < 13 or saved_drive < 8 or saved_tools < 3:
    raise SystemExit("asset writing fell short")
imc_foot = eal.load_asset(INPUT_FOLDER + "/IMC_OnFoot")
imc_drive = eal.load_asset(INPUT_FOLDER + "/IMC_Driving")
log("IMC_OnFoot has %d mappings, IMC_Driving %d" % (lib.get_mapping_count(imc_foot), lib.get_mapping_count(imc_drive)))
if lib.get_mapping_count(imc_foot) < 24 or lib.get_mapping_count(imc_drive) < 19:
    raise SystemExit("mapping contexts are missing mappings")
for name in ("DA_Tool_Cutter", "DA_Tool_PryBar", "DA_Tool_RepairKit"):
    tool = eal.load_asset(TOOL_FOLDER + "/" + name)
    if tool is None:
        raise SystemExit("missing " + name)
    log("%s: %s grants %s" % (name, tool.get_editor_property("display_name"), tool.get_editor_property("granted_tag")))
log("DONE")
