"""setup_m1_cockpit.py - the prop master material the greybox dashboard needs, headless.

Run with Art\\setup_m1_cockpit.bat (close the editor first). Creates
/Game/GrandTour/Materials/M_GT_Prop with BaseColor, Roughness, EmissiveColor and EmissiveStrength
parameters (emissive = colour x strength). UGTDashboardComponent makes dynamic instances of it
for dial faces, needles, warning lights, the dash slab and the steering wheel. This is the
"props" master of the planned set; MF_Weather goes in here later like the environment master.
Safe to re-run: an existing material is left alone.
"""
import unreal

MAT_PATH = "/Game/GrandTour/Materials"
NAME = "M_GT_Prop"

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log("SETUP_M1_COCKPIT " + msg)


full = MAT_PATH + "/" + NAME
if eal.does_asset_exist(full):
    log("exists, leaving it alone: " + full)
else:
    master = tools.create_asset(NAME, MAT_PATH, unreal.Material, unreal.MaterialFactoryNew())
    if master is None:
        raise SystemExit("could not create " + full)
    base = mel.create_material_expression(master, unreal.MaterialExpressionVectorParameter, -500, -100)
    base.set_editor_property("parameter_name", "BaseColor")
    base.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
    rough = mel.create_material_expression(master, unreal.MaterialExpressionScalarParameter, -500, 100)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.6)
    ecol = mel.create_material_expression(master, unreal.MaterialExpressionVectorParameter, -700, 300)
    ecol.set_editor_property("parameter_name", "EmissiveColor")
    ecol.set_editor_property("default_value", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    estr = mel.create_material_expression(master, unreal.MaterialExpressionScalarParameter, -700, 450)
    estr.set_editor_property("parameter_name", "EmissiveStrength")
    estr.set_editor_property("default_value", 0.0)
    mul = mel.create_material_expression(master, unreal.MaterialExpressionMultiply, -400, 350)
    if not mel.connect_material_expressions(ecol, "", mul, "A"):
        raise SystemExit("could not connect EmissiveColor")
    if not mel.connect_material_expressions(estr, "", mul, "B"):
        raise SystemExit("could not connect EmissiveStrength")
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(master)
    eal.save_loaded_asset(master)
    log("created " + full)
# The spray component draws mud blobs as instanced spheres with this material; the usage flag is
# set on every run so an older asset picks it up.
master = eal.load_asset(full)
mel.set_base_material_usage(master, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
eal.save_loaded_asset(master)
log("instanced static mesh usage set")
log("DONE")
