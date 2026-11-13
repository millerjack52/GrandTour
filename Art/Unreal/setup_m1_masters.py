"""setup_m1_masters.py - every master material ends in MF_Weather, plus the two missing masters.

Run with Art\\setup_m1_masters.bat after setup_m1_track, setup_m1_cockpit, setup_m1_weather and
setup_m1_body (close the editor first). ARCHITECTURE 6d: five masters, each handing its result
through MF_Weather so wetness and snow are one global parameter.
- Creates M_GT_Foliage (BaseColor, Roughness, two-sided, a wind World Position Offset from
  MPC_Weather's WindStrength / WindDirection) and M_GT_Character (BaseColor, Roughness, usable on
  skeletal meshes) if they are missing.
- For M_GT_Environment, M_GT_Prop, M_GT_Glass, M_GT_Foliage and M_GT_Character: whatever feeds
  BaseColor and Roughness now goes through an MF_Weather call with a Porosity scalar parameter
  (the nodes are tagged "Weather:" in their description, so a re-run replaces them). M_GT_Vehicle
  already ends in MF_Weather (setup_m1_body) and is only checked. The environment master also
  feeds a CanPool scalar parameter (default 1) so puddles form on ground and nowhere else (M3).
- Sets Porosity on the environment instances (tarmac 0.3, dirt 0.9, mud 1.0, snow 0.6).
- Finishes by asserting that the BaseColor pin of all six masters is fed by MF_Weather.
The Substrate clear coat for the vehicle master stays deferred (its pins are not reachable from
Python). Nothing here compiles HLSL: run a test with `gpu` (or -GTProbeMaterial) for that.
"""
import unreal

MAT = "/Game/GrandTour/Materials"
TAG = "Weather:"
MASTERS = {   # name: default porosity
    "M_GT_Environment": 0.6,
    "M_GT_Prop": 0.1,
    "M_GT_Glass": 0.0,
    "M_GT_Foliage": 0.8,
    "M_GT_Character": 0.3,
}
INSTANCE_POROSITY = {"Tarmac": 0.3, "Dirt": 0.9, "Mud": 1.0, "Snow": 0.6, "Greybox": 0.2, "Marker": 0.2}

WIND_HLSL = """float phase = dot(WorldPos.xy, float2(0.01, 0.013)) + Time * 2.0;
float sway = sin(phase) * 15.0 * WindStrength;
return float3(WindDir.x, WindDir.y, 0.0) * sway;
"""

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log("SETUP_M1_MASTERS " + msg)


def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    for alt in names:
        if alt != in_name and mel.connect_material_expressions(src, out_name, dst, alt):
            return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


def compile_or_die(material):
    errors = [str(e) for e in mel.recompile_material(material)]
    eal.save_loaded_asset(material)
    if errors:
        for error in errors:
            unreal.log_error("SETUP_M1_MASTERS compile error in %s: %s" % (material.get_name(), error))
        raise SystemExit(material.get_name() + " failed to compile")


def scalar(material, name, value, x, y, tag=None):
    e = mel.create_material_expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", value)
    if tag:
        e.set_editor_property("desc", TAG + tag)
    return e


def vector(material, name, colour, x, y):
    e = mel.create_material_expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", unreal.LinearColor(*colour))
    return e


weather_full = MAT + "/MF_Weather"
if not eal.does_asset_exist(weather_full):
    raise SystemExit("missing " + weather_full + " (run Art/setup_m1_weather.bat first)")
weather = eal.load_asset(weather_full)
mpc = eal.load_asset(MAT + "/MPC_Weather")

# ---- the two missing masters ------------------------------------------------------------------
if not eal.does_asset_exist(MAT + "/M_GT_Foliage"):
    m = tools.create_asset("M_GT_Foliage", MAT, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("two_sided", True)
    base = vector(m, "BaseColor", (0.25, 0.35, 0.12, 1.0), -600, -200)
    rough = scalar(m, "Roughness", 0.8, -600, 0)
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # Wind: a world-position sine sway along the collection's wind, scaled by its strength.
    wpos = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -900, 300)
    time = mel.create_material_expression(m, unreal.MaterialExpressionTime, -900, 400)
    strength = mel.create_material_expression(m, unreal.MaterialExpressionCollectionParameter, -900, 500)
    strength.set_editor_property("collection", mpc)
    strength.set_editor_property("parameter_name", "WindStrength")
    direction = mel.create_material_expression(m, unreal.MaterialExpressionCollectionParameter, -900, 600)
    direction.set_editor_property("collection", mpc)
    direction.set_editor_property("parameter_name", "WindDirection")
    wind = mel.create_material_expression(m, unreal.MaterialExpressionCustom, -600, 400)
    wind.set_editor_property("description", "Wind sway")
    wind.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for name in ("WorldPos", "Time", "WindStrength", "WindDir"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        inputs.append(ci)
    wind.set_editor_property("inputs", inputs)
    wind.set_editor_property("code", WIND_HLSL)
    connect(wpos, "", wind, "WorldPos")
    connect(time, "", wind, "Time")
    connect(strength, "", wind, "WindStrength")
    connect(direction, "", wind, "WindDir")
    mel.connect_material_property(wind, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    compile_or_die(m)
    log("created M_GT_Foliage")

if not eal.does_asset_exist(MAT + "/M_GT_Character"):
    m = tools.create_asset("M_GT_Character", MAT, unreal.Material, unreal.MaterialFactoryNew())
    base = vector(m, "BaseColor", (0.5, 0.4, 0.3, 1.0), -600, -200)
    rough = scalar(m, "Roughness", 0.7, -600, 0)
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)   # the first-person arms
    compile_or_die(m)
    log("created M_GT_Character")


# ---- route every master through MF_Weather -----------------------------------------------------
def feeds_weather(master):
    node = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_BASE_COLOR)
    return node is not None and isinstance(node, unreal.MaterialExpressionMaterialFunctionCall) \
        and node.get_editor_property("material_function") == weather


for name, porosity in MASTERS.items():
    full = MAT + "/" + name
    if not eal.does_asset_exist(full):
        raise SystemExit("missing " + full + " (run the earlier setup bats first)")
    master = eal.load_asset(full)
    if feeds_weather(master):
        # Already routed on an earlier run: keep the call (its inputs feed it), refresh it from the
        # function so new inputs such as CanPool appear, and rebuild only the CanPool parameter.
        call = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_BASE_COLOR)
        call.set_material_function(weather)
        for e in list(mel.get_material_expressions(master)):
            if str(e.get_editor_property("desc")) == TAG + "canpool":
                mel.delete_material_expression(master, e)
        if name == "M_GT_Environment":
            pool = scalar(master, "CanPool", 1.0, 0, 550, "canpool")
            connect(pool, "", call, "CanPool")
        compile_or_die(master)
        log("%s: MF_Weather call refreshed%s" % (name, " with CanPool" if name == "M_GT_Environment" else ""))
        continue
    for e in list(mel.get_material_expressions(master)):
        if str(e.get_editor_property("desc")).startswith(TAG):
            mel.delete_material_expression(master, e)
    base_node = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_BASE_COLOR)
    base_out = mel.get_material_property_input_node_output_name(master, unreal.MaterialProperty.MP_BASE_COLOR)
    rough_node = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_ROUGHNESS)
    rough_out = mel.get_material_property_input_node_output_name(master, unreal.MaterialProperty.MP_ROUGHNESS)
    log("%s: BaseColor fed by %s, Roughness by %s" % (name, base_node.get_name() if base_node else None, rough_node.get_name() if rough_node else None))
    if base_node is None or rough_node is None:
        # Repair path: a property left disconnected (an interrupted earlier run) is re-fed from the
        # material's own BaseColor / Roughness parameter nodes.
        for e in mel.get_material_expressions(master):
            pname = str(e.get_editor_property("parameter_name")) if hasattr(e, "get_editor_property") and isinstance(e, (unreal.MaterialExpressionVectorParameter, unreal.MaterialExpressionScalarParameter)) else ""
            if base_node is None and pname == "BaseColor" and isinstance(e, unreal.MaterialExpressionVectorParameter):
                base_node, base_out = e, ""
            if rough_node is None and pname == "Roughness" and isinstance(e, unreal.MaterialExpressionScalarParameter):
                rough_node, rough_out = e, ""
        log("%s: repaired inputs: BaseColor <- %s, Roughness <- %s" % (name, base_node.get_name() if base_node else None, rough_node.get_name() if rough_node else None))
    if base_node is None:
        raise SystemExit(name + " has nothing on BaseColor and no BaseColor parameter to repair it from")
    call = mel.create_material_expression(master, unreal.MaterialExpressionMaterialFunctionCall, 200, 300)
    call.set_editor_property("desc", TAG + "call")
    if not call.set_material_function(weather):
        raise SystemExit("could not set MF_Weather on " + name)
    poro = scalar(master, "Porosity", porosity, 0, 450, "porosity")
    connect(base_node, str(base_out), call, "BaseColor")
    if rough_node is not None:
        connect(rough_node, str(rough_out), call, "Roughness")
    connect(poro, "", call, "Porosity")
    if name == "M_GT_Environment":
        pool = scalar(master, "CanPool", 1.0, 0, 550, "canpool")
        connect(pool, "", call, "CanPool")
    if not mel.connect_material_property(call, "BaseColor", unreal.MaterialProperty.MP_BASE_COLOR):
        raise SystemExit("could not connect weathered BaseColor on " + name)
    if not mel.connect_material_property(call, "Roughness", unreal.MaterialProperty.MP_ROUGHNESS):
        raise SystemExit("could not connect weathered Roughness on " + name)
    compile_or_die(master)
    log("%s: BaseColor and Roughness now go through MF_Weather (porosity %.1f)" % (name, porosity))

for name, porosity in INSTANCE_POROSITY.items():
    full = MAT + "/MI_Env_" + name
    if eal.does_asset_exist(full):
        inst = eal.load_asset(full)
        mel.set_material_instance_scalar_parameter_value(inst, "Porosity", porosity)
        mel.update_material_instance(inst)
        eal.save_loaded_asset(inst)

# ---- the rule: every master ends in MF_Weather ---------------------------------------------------
checked = 0
for name in list(MASTERS) + ["M_GT_Vehicle"]:
    master = eal.load_asset(MAT + "/" + name)
    if not feeds_weather(master):
        raise SystemExit(name + " does not end in MF_Weather")
    checked += 1
log("masters through MF_Weather: %d/%d" % (checked, len(MASTERS) + 1))
log("DONE")
