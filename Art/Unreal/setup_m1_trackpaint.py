"""setup_m1_trackpaint.py - tyre-track render target, parameter collection and material function, headless.

Run with Art\\setup_m1_trackpaint.bat (close the editor first; run setup_m1_track.bat before it so
M_GT_Environment and its instances exist). Creates under /Game/GrandTour/Terrain:
- RT_TrackPaint: 2048 x 2048 RGBA16f render target that UGTTrackPaintSubsystem draws tyre tracks
  into (R = rut depth, saturated to 0..1 by the material) and the environment master samples.
- MPC_TrackPaint: TrackOrigin (window centre x, y, window size cm, resolution) and TrackDepthCm,
  written by the subsystem whenever the window moves.
And under /Game/GrandTour/Materials:
- MF_TrackPaint: samples the target at the pixel's world XY and outputs RutDepth, NormalWS (a
  finite-difference rut normal in world space) and Displacement (world-space offset in cm). This
  function is the only place that changes if the displacement approach changes (ARCHITECTURE 6a).
- Wires it into M_GT_Environment (Normal and World Position Offset) behind a TrackStrength scalar
  parameter gated by the surface facing up, and sets TrackStrength 0 on the tarmac, greybox and
  marker instances so only soft ground shows ruts.
Safe to re-run: the function is rebuilt from scratch, the master's track-paint nodes (tagged in
their description) are replaced, collection parameters keep their ids.
"""
import unreal

TERRAIN = "/Game/GrandTour/Terrain"
MAT = "/Game/GrandTour/Materials"
RT_NAME = "RT_TrackPaint"
MPC_NAME = "MPC_TrackPaint"
MF_NAME = "MF_TrackPaint"
MASTER = "M_GT_Environment"
RESOLUTION = 2048        # a multiple of UGTTrackPaintSubsystem's 256-cell grid
WINDOW_CM = 12800.0
DEPTH_CM = 12.0
TAG = "TrackPaint:"      # description prefix on the nodes this script owns in the master

# One sample plus four neighbours. SampleLevel so the same code compiles in the vertex shader
# (World Position Offset) and the pixel shader (Normal). Origin = (centre x, y, size cm, pixels).
# Pixel (0, 0) is the window's min corner, matching UGTTrackPaintSubsystem::WorldToPixel.
HLSL = """float2 uv = (WorldPos.xy - Origin.xy) / Origin.z + 0.5;
float inside = (uv.x > 0.0 && uv.x < 1.0 && uv.y > 0.0 && uv.y < 1.0) ? 1.0 : 0.0;
float2 t = float2(1.0 / Origin.w, 0.0);
float d  = saturate(Texture2DSampleLevel(Tex, TexSampler, uv, 0).r);
float dx = saturate(Texture2DSampleLevel(Tex, TexSampler, uv + t.xy, 0).r) - saturate(Texture2DSampleLevel(Tex, TexSampler, uv - t.xy, 0).r);
float dy = saturate(Texture2DSampleLevel(Tex, TexSampler, uv + t.yx, 0).r) - saturate(Texture2DSampleLevel(Tex, TexSampler, uv - t.yx, 0).r);
float s = saturate(Strength) * inside;
float span = 2.0 * Origin.z / Origin.w;
float3 n = normalize(float3(dx * DepthCm / span, dy * DepthCm / span, 1.0));
float depth = d * s;
Displacement = float3(0.0, 0.0, -depth * DepthCm);
return float4(normalize(lerp(float3(0.0, 0.0, 1.0), n, s)), depth);
"""

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log("SETUP_M1_TRACKPAINT " + msg)


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
    """connect_material_expressions by pin name, falling back to the node's first input."""
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    for alt in names:
        if alt != in_name and mel.connect_material_expressions(src, out_name, dst, alt):
            log("connected %s -> %s.%r (asked for %r)" % (src.get_name(), dst.get_name(), alt, in_name))
            return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


# ---- render target ------------------------------------------------------------------------
rt = get_or_create(RT_NAME, TERRAIN, unreal.TextureRenderTarget2D, unreal.TextureRenderTargetFactoryNew())
rt.set_editor_property("render_target_format", unreal.TextureRenderTargetFormat.RTF_RGBA16F)
rt.set_editor_property("size_x", RESOLUTION)
rt.set_editor_property("size_y", RESOLUTION)
rt.set_editor_property("clear_color", unreal.LinearColor(0.0, 0.0, 0.0, 1.0))
rt.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
rt.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
rt.set_editor_property("srgb", False)
eal.save_loaded_asset(rt)
log("render target %s %dx%d %s" % (RT_NAME, rt.get_editor_property("size_x"), rt.get_editor_property("size_y"),
                                   rt.get_editor_property("render_target_format")))

# ---- parameter collection -----------------------------------------------------------------
mpc = get_or_create(MPC_NAME, TERRAIN, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())


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


scalars = upsert(list(mpc.get_editor_property("scalar_parameters")), unreal.CollectionScalarParameter, "TrackDepthCm", DEPTH_CM)
vectors = upsert(list(mpc.get_editor_property("vector_parameters")), unreal.CollectionVectorParameter, "TrackOrigin",
                 unreal.LinearColor(0.0, 0.0, WINDOW_CM, float(RESOLUTION)))
mpc.set_editor_property("scalar_parameters", scalars)
mpc.set_editor_property("vector_parameters", vectors)
eal.save_loaded_asset(mpc)
log("collection %s: scalars %s vectors %s" % (MPC_NAME, [str(n) for n in mpc.get_scalar_parameter_names()],
                                              [str(n) for n in mpc.get_vector_parameter_names()]))

# ---- material function ----------------------------------------------------------------------
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
mf.set_editor_property("description", "Tyre-track ruts from RT_TrackPaint: RutDepth, NormalWS, Displacement (cm).")


def fx(cls, x, y):
    return mel.create_material_expression_in_function(mf, cls, x, y)


strength_in = fx(unreal.MaterialExpressionFunctionInput, -900, -200)
strength_in.set_editor_property("input_name", "Strength")
strength_in.set_editor_property("input_type", unreal.FunctionInputType.FUNCTION_INPUT_SCALAR)
try:
    preview = unreal.Vector4f()
    preview.set_editor_property("x", 1.0)
    strength_in.set_editor_property("preview_value", preview)
    strength_in.set_editor_property("use_preview_value_as_default", True)
except Exception as e:  # cosmetic: the master always connects it
    unreal.log_warning("SETUP_M1_TRACKPAINT preview value not set: %s" % e)

wpos = fx(unreal.MaterialExpressionWorldPosition, -900, 0)
origin = fx(unreal.MaterialExpressionCollectionParameter, -900, 150)
origin.set_editor_property("collection", mpc)
origin.set_editor_property("parameter_name", "TrackOrigin")
depth = fx(unreal.MaterialExpressionCollectionParameter, -900, 300)
depth.set_editor_property("collection", mpc)
depth.set_editor_property("parameter_name", "TrackDepthCm")
tex = fx(unreal.MaterialExpressionTextureObjectParameter, -900, 450)
tex.set_editor_property("parameter_name", "TrackRT")
tex.set_editor_property("texture", rt)
tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)

custom = fx(unreal.MaterialExpressionCustom, -500, 0)
custom.set_editor_property("description", "TrackPaint sample")
custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4)
inputs = []
for name in ("WorldPos", "Origin", "DepthCm", "Tex", "Strength"):
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", name)
    inputs.append(ci)
custom.set_editor_property("inputs", inputs)
disp_out = unreal.CustomOutput()
disp_out.set_editor_property("output_name", "Displacement")
disp_out.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
custom.set_editor_property("additional_outputs", [disp_out])
custom.set_editor_property("code", HLSL)

mask_n = fx(unreal.MaterialExpressionComponentMask, -200, -50)
mask_n.set_editor_property("r", True)
mask_n.set_editor_property("g", True)
mask_n.set_editor_property("b", True)
mask_n.set_editor_property("a", False)
mask_d = fx(unreal.MaterialExpressionComponentMask, -200, 100)
mask_d.set_editor_property("r", False)
mask_d.set_editor_property("g", False)
mask_d.set_editor_property("b", False)
mask_d.set_editor_property("a", True)

outputs = {}
for index, name in enumerate(("NormalWS", "RutDepth", "Displacement")):
    out = fx(unreal.MaterialExpressionFunctionOutput, 100, -50 + 150 * index)
    out.set_editor_property("output_name", name)
    out.set_editor_property("sort_priority", index)
    outputs[name] = out

connect(wpos, "", custom, "WorldPos")
connect(origin, "", custom, "Origin")
connect(depth, "", custom, "DepthCm")
connect(tex, "", custom, "Tex")
connect(strength_in, "", custom, "Strength")
connect(custom, "", mask_n, "")
connect(custom, "", mask_d, "")
connect(mask_n, "", outputs["NormalWS"], "")
connect(mask_d, "", outputs["RutDepth"], "")
connect(custom, "Displacement", outputs["Displacement"], "")
mel.update_material_function(mf)
eal.save_loaded_asset(mf)
log("function %s: %d expressions" % (MF_NAME, mel.get_num_material_expressions_in_function(mf)))

# ---- master material ------------------------------------------------------------------------
master_full = MAT + "/" + MASTER
if not eal.does_asset_exist(master_full):
    raise SystemExit("missing " + master_full + " (run Art/setup_m1_track.bat first)")
master = eal.load_asset(master_full)
removed = 0
for expression in list(mel.get_material_expressions(master)):
    if str(expression.get_editor_property("desc")).startswith(TAG):
        mel.delete_material_expression(master, expression)
        removed += 1
if removed:
    log("removed %d old track-paint nodes from %s" % (removed, MASTER))


def mx(cls, x, y, tag):
    expression = mel.create_material_expression(master, cls, x, y)
    expression.set_editor_property("desc", TAG + tag)
    return expression


strength = mx(unreal.MaterialExpressionScalarParameter, -900, 550, "strength")
strength.set_editor_property("parameter_name", "TrackStrength")
strength.set_editor_property("default_value", 1.0)
vertex_normal = mx(unreal.MaterialExpressionVertexNormalWS, -900, 700, "vertexnormal")
up = mx(unreal.MaterialExpressionComponentMask, -750, 700, "up")
up.set_editor_property("r", False)
up.set_editor_property("g", False)
up.set_editor_property("b", True)
up.set_editor_property("a", False)
up_sat = mx(unreal.MaterialExpressionSaturate, -620, 700, "upsat")
gate = mx(unreal.MaterialExpressionMultiply, -500, 600, "gate")
call = mx(unreal.MaterialExpressionMaterialFunctionCall, -350, 600, "call")
if not call.set_material_function(mf):
    raise SystemExit("could not set MF_TrackPaint on the function call")
xform = mx(unreal.MaterialExpressionTransform, -100, 560, "tangent")
xform.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
xform.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)

connect(strength, "", gate, "A")
connect(vertex_normal, "", up, "")
connect(up, "", up_sat, "")
connect(up_sat, "", gate, "B")
connect(gate, "", call, "Strength")
connect(call, "NormalWS", xform, "")
if not mel.connect_material_property(xform, "", unreal.MaterialProperty.MP_NORMAL):
    raise SystemExit("could not connect Normal")
if not mel.connect_material_property(call, "Displacement", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
    raise SystemExit("could not connect World Position Offset")
errors = [str(e) for e in mel.recompile_material(master)]
eal.save_loaded_asset(master)
if errors:
    for error in errors:
        unreal.log_error("SETUP_M1_TRACKPAINT compile error: " + error)
    raise SystemExit("%s failed to compile" % MASTER)
log("wired MF_TrackPaint into %s (no compile errors)" % MASTER)

# ---- instances: only soft ground shows ruts -----------------------------------------------
for name, value in (("Tarmac", 0.0), ("Greybox", 0.0), ("Marker", 0.0), ("Dirt", 1.0), ("Mud", 1.0), ("Snow", 1.0)):
    full = MAT + "/MI_Env_" + name
    if not eal.does_asset_exist(full):
        unreal.log_warning("SETUP_M1_TRACKPAINT missing instance " + full)
        continue
    inst = eal.load_asset(full)
    mel.set_material_instance_scalar_parameter_value(inst, "TrackStrength", value)
    mel.update_material_instance(inst)
    eal.save_loaded_asset(inst)
log("TrackStrength set on the environment instances")
log("DONE")
