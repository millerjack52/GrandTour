"""setup_m1_weather.py - the weather parameter collection and MF_Weather, headless.

Run with Art\\setup_m1_weather.bat (close the editor first). Creates under /Game/GrandTour/Materials:
- MPC_Weather: the globals UGTWeatherSubsystem (M3) will write every frame, per ARCHITECTURE 6d:
  Wetness, RainIntensity, SnowAmount, WindStrength, Temperature (scalars), WindDirection and
  OcclusionBounds (vectors). Everything defaults to dry, still, 15 degrees.
- MF_Weather: the function every master material hands its result through. Inputs BaseColor,
  Roughness, Porosity (0 = paint, 1 = soil), LocalWetness and LocalSnow (a car's own spray) and
  CanPool (1 on ground that collects water: the environment master); reads the collection's
  Wetness, SnowAmount, OcclusionBounds and OcclusionEnabled and samples RT_RainOcclusion, the
  top-down depth the rain emitter captures (M3): global wetness and snow are masked to zero
  under cover. Darkens porous surfaces and drops roughness when wet, whitens upward-facing
  surfaces when snowy, and on pooling ground grows dark glossy puddles from a low-frequency
  value noise as the wetness rises. Outputs BaseColor, Roughness, Wet, Snow and Puddle.
- RT_RainOcclusion: 512 px RGBA16F depth target the capture writes into.
Safe to re-run: the function is rebuilt; collection parameters keep their ids.
"""
import unreal

MAT = "/Game/GrandTour/Materials"
MPC_NAME = "MPC_Weather"
MF_NAME = "MF_Weather"

RT_NAME = "RT_RainOcclusion"
RT_RESOLUTION = 512

# Inputs: BaseColor, Roughness, Porosity, LocalWetness, LocalSnow, CanPool, NormalWS, WorldPos,
# GlobalWetness, GlobalSnow, Occ (texture object), OccBounds (x, y, top z, half extent), OccEnabled.
HLSL = """// Rain occlusion: the emitter's top-down depth capture. open = 1 under the sky, 0 under cover.
float open = 1.0;
float2 uv = float2(0.5 + (WorldPos.y - OccBounds.y) / (2.0 * OccBounds.w), 0.5 - (WorldPos.x - OccBounds.x) / (2.0 * OccBounds.w));
if (OccEnabled > 0.5 && OccBounds.w > 1.0 && all(uv > 0.0) && all(uv < 1.0))
{
    float depth = Texture2DSampleLevel(Occ, OccSampler, uv, 0).r;
    float coverZ = OccBounds.z - depth;
    open = 1.0 - saturate((coverZ - WorldPos.z - 20.0) / 40.0);
}
float wet = saturate(GlobalWetness * open + LocalWetness);
float top = saturate(NormalWS.z);
float snow = saturate(GlobalSnow * open + LocalSnow) * top;
// Puddles: low-frequency value noise, in dips (CanPool), only where the sky can rain in, growing with the wetness.
float2 p = WorldPos.xy * 0.003;
float2 i = floor(p);
float2 f = frac(p);
f = f * f * (3.0 - 2.0 * f);
float a = frac(sin(dot(i, float2(12.9898, 78.233))) * 43758.5453);
float b = frac(sin(dot(i + float2(1.0, 0.0), float2(12.9898, 78.233))) * 43758.5453);
float c = frac(sin(dot(i + float2(0.0, 1.0), float2(12.9898, 78.233))) * 43758.5453);
float d = frac(sin(dot(i + float2(1.0, 1.0), float2(12.9898, 78.233))) * 43758.5453);
float n = lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
float fill = saturate(GlobalWetness * open * 1.6 - 0.25);
float puddle = smoothstep(0.66 - 0.3 * fill, 0.70 - 0.3 * fill, n) * top * saturate(CanPool) * step(0.001, fill);
float3 base = BaseColor * (1.0 - 0.5 * Porosity * wet);
float rough = lerp(Roughness, 0.15, wet * (0.6 + 0.4 * Porosity));
base = lerp(base, base * 0.45, puddle);
rough = lerp(rough, 0.03, puddle);
base = lerp(base, float3(0.92, 0.93, 0.95), snow);
rough = lerp(rough, 0.75, snow);
Wet = wet;
Snow = snow;
Puddle = puddle;
return float4(base, rough);
"""

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log("SETUP_M1_WEATHER " + msg)


def get_or_create(name, path, cls, factory):
    full = path + "/" + name
    asset = eal.load_asset(full) if eal.does_asset_exist(full) else None
    if asset is None:
        asset = tools.create_asset(name, path, cls, factory)
        if asset is None:
            raise SystemExit("could not create " + full)
        log("created " + full)
    return asset


def clear_function(mf):
    """delete_all_material_expressions_in_function skips every other node (delete while iterating); finish the job."""
    mel.delete_all_material_expressions_in_function(mf)
    for e in list(mel.get_material_function_expressions(mf)):
        mel.delete_material_expression_in_function(mf, e)
    left = mel.get_num_material_expressions_in_function(mf)
    if left:
        raise SystemExit("%d expressions survived clearing %s" % (left, mf.get_name()))


def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    for alt in names:
        if alt != in_name and mel.connect_material_expressions(src, out_name, dst, alt):
            log("connected %s -> %s.%r (asked for %r)" % (src.get_name(), dst.get_name(), alt, in_name))
            return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


def upsert(params, cls, name, value):
    for p in params:
        if str(p.get_editor_property("parameter_name")) == name:
            p.set_editor_property("default_value", value)
            return params
    p = cls()
    p.set_editor_property("parameter_name", name)
    p.set_editor_property("default_value", value)
    params.append(p)
    return params


# ---- MPC_Weather ------------------------------------------------------------------------------
mpc = get_or_create(MPC_NAME, MAT, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
scalars = list(mpc.get_editor_property("scalar_parameters"))
for name, value in (("Wetness", 0.0), ("RainIntensity", 0.0), ("SnowAmount", 0.0), ("WindStrength", 0.0), ("Temperature", 15.0), ("OcclusionEnabled", 0.0)):
    scalars = upsert(scalars, unreal.CollectionScalarParameter, name, value)
vectors = list(mpc.get_editor_property("vector_parameters"))
vectors = upsert(vectors, unreal.CollectionVectorParameter, "WindDirection", unreal.LinearColor(1.0, 0.0, 0.0, 0.0))
vectors = upsert(vectors, unreal.CollectionVectorParameter, "OcclusionBounds", unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
mpc.set_editor_property("scalar_parameters", scalars)
mpc.set_editor_property("vector_parameters", vectors)
eal.save_loaded_asset(mpc)
log("collection %s: scalars %s vectors %s" % (MPC_NAME, [str(n) for n in mpc.get_scalar_parameter_names()],
                                              [str(n) for n in mpc.get_vector_parameter_names()]))

# ---- RT_RainOcclusion -------------------------------------------------------------------------
rt = get_or_create(RT_NAME, MAT, unreal.TextureRenderTarget2D, unreal.TextureRenderTargetFactoryNew())
rt.set_editor_property("render_target_format", unreal.TextureRenderTargetFormat.RTF_RGBA16F)
rt.set_editor_property("size_x", RT_RESOLUTION)
rt.set_editor_property("size_y", RT_RESOLUTION)
rt.set_editor_property("clear_color", unreal.LinearColor(1000000.0, 0.0, 0.0, 1.0))   # far away = open sky until the first capture
rt.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
rt.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
rt.set_editor_property("srgb", False)
eal.save_loaded_asset(rt)
log("render target %s %dx%d" % (RT_NAME, RT_RESOLUTION, RT_RESOLUTION))

# ---- MF_Weather -------------------------------------------------------------------------------
mf_full = MAT + "/" + MF_NAME
if eal.does_asset_exist(mf_full):
    mf = eal.load_asset(mf_full)
    clear_function(mf)
    log("rebuilding " + mf_full)
else:
    mf = tools.create_asset(MF_NAME, MAT, unreal.MaterialFunction, unreal.MaterialFunctionFactoryNew())
    if mf is None:
        raise SystemExit("could not create " + mf_full)
    log("created " + mf_full)
mf.set_editor_property("description", "Global weather on any surface: wet darkening and gloss, snow on top. Every master ends with this.")


def fx(cls, x, y):
    return mel.create_material_expression_in_function(mf, cls, x, y)


def function_input(name, input_type, preview, x, y, priority):
    e = fx(unreal.MaterialExpressionFunctionInput, x, y)
    e.set_editor_property("input_name", name)
    e.set_editor_property("input_type", input_type)
    e.set_editor_property("sort_priority", priority)
    try:
        v = unreal.Vector4f()
        for key, value in zip(("x", "y", "z", "w"), preview):
            v.set_editor_property(key, value)
        e.set_editor_property("preview_value", v)
        e.set_editor_property("use_preview_value_as_default", True)
    except Exception as ex:
        unreal.log_warning("SETUP_M1_WEATHER preview for %s not set: %s" % (name, ex))
    return e


in_base = function_input("BaseColor", unreal.FunctionInputType.FUNCTION_INPUT_VECTOR3, (0.5, 0.5, 0.5, 0.0), -900, -250, 0)
in_rough = function_input("Roughness", unreal.FunctionInputType.FUNCTION_INPUT_SCALAR, (0.5, 0.0, 0.0, 0.0), -900, -100, 1)
in_poro = function_input("Porosity", unreal.FunctionInputType.FUNCTION_INPUT_SCALAR, (0.0, 0.0, 0.0, 0.0), -900, 50, 2)
in_wet = function_input("LocalWetness", unreal.FunctionInputType.FUNCTION_INPUT_SCALAR, (0.0, 0.0, 0.0, 0.0), -900, 200, 3)
in_snow = function_input("LocalSnow", unreal.FunctionInputType.FUNCTION_INPUT_SCALAR, (0.0, 0.0, 0.0, 0.0), -900, 350, 4)
in_pool = function_input("CanPool", unreal.FunctionInputType.FUNCTION_INPUT_SCALAR, (0.0, 0.0, 0.0, 0.0), -900, 450, 5)
vnormal = fx(unreal.MaterialExpressionVertexNormalWS, -900, 550)
wpos = fx(unreal.MaterialExpressionWorldPosition, -900, 650)
g_wet = fx(unreal.MaterialExpressionCollectionParameter, -900, 750)
g_wet.set_editor_property("collection", mpc)
g_wet.set_editor_property("parameter_name", "Wetness")
g_snow = fx(unreal.MaterialExpressionCollectionParameter, -900, 850)
g_snow.set_editor_property("collection", mpc)
g_snow.set_editor_property("parameter_name", "SnowAmount")
g_occ = fx(unreal.MaterialExpressionTextureObjectParameter, -900, 950)
g_occ.set_editor_property("parameter_name", "RainOcclusion")
g_occ.set_editor_property("texture", rt)
g_bounds = fx(unreal.MaterialExpressionCollectionParameter, -900, 1100)
g_bounds.set_editor_property("collection", mpc)
g_bounds.set_editor_property("parameter_name", "OcclusionBounds")
g_enabled = fx(unreal.MaterialExpressionCollectionParameter, -900, 1200)
g_enabled.set_editor_property("collection", mpc)
g_enabled.set_editor_property("parameter_name", "OcclusionEnabled")

custom = fx(unreal.MaterialExpressionCustom, -500, 200)
custom.set_editor_property("description", "Weather")
custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4)
inputs = []
for name in ("BaseColor", "Roughness", "Porosity", "LocalWetness", "LocalSnow", "CanPool", "NormalWS", "WorldPos", "GlobalWetness", "GlobalSnow", "Occ", "OccBounds", "OccEnabled"):
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", name)
    inputs.append(ci)
custom.set_editor_property("inputs", inputs)
extra = []
for name in ("Wet", "Snow", "Puddle"):
    co = unreal.CustomOutput()
    co.set_editor_property("output_name", name)
    co.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    extra.append(co)
custom.set_editor_property("additional_outputs", extra)
custom.set_editor_property("code", HLSL)

mask_rgb = fx(unreal.MaterialExpressionComponentMask, -200, 100)
mask_rgb.set_editor_property("r", True)
mask_rgb.set_editor_property("g", True)
mask_rgb.set_editor_property("b", True)
mask_rgb.set_editor_property("a", False)
mask_a = fx(unreal.MaterialExpressionComponentMask, -200, 250)
mask_a.set_editor_property("r", False)
mask_a.set_editor_property("g", False)
mask_a.set_editor_property("b", False)
mask_a.set_editor_property("a", True)
outputs = {}
for index, name in enumerate(("BaseColor", "Roughness", "Wet", "Snow", "Puddle")):
    out = fx(unreal.MaterialExpressionFunctionOutput, 100, 50 + 150 * index)
    out.set_editor_property("output_name", name)
    out.set_editor_property("sort_priority", index)
    outputs[name] = out

connect(in_base, "", custom, "BaseColor")
connect(in_rough, "", custom, "Roughness")
connect(in_poro, "", custom, "Porosity")
connect(in_wet, "", custom, "LocalWetness")
connect(in_snow, "", custom, "LocalSnow")
connect(in_pool, "", custom, "CanPool")
connect(vnormal, "", custom, "NormalWS")
connect(wpos, "", custom, "WorldPos")
connect(g_wet, "", custom, "GlobalWetness")
connect(g_snow, "", custom, "GlobalSnow")
connect(g_occ, "", custom, "Occ")
connect(g_bounds, "", custom, "OccBounds")
connect(g_enabled, "", custom, "OccEnabled")
connect(custom, "", mask_rgb, "")
connect(custom, "", mask_a, "")
connect(mask_rgb, "", outputs["BaseColor"], "")
connect(mask_a, "", outputs["Roughness"], "")
connect(custom, "Wet", outputs["Wet"], "")
connect(custom, "Snow", outputs["Snow"], "")
connect(custom, "Puddle", outputs["Puddle"], "")
mel.update_material_function(mf)
eal.save_loaded_asset(mf)
log("function %s: %d expressions" % (MF_NAME, mel.get_num_material_expressions_in_function(mf)))
log("DONE")
