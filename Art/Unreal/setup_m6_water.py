"""setup_m6_water.py - the two water materials: M_GT_MudWater (the water standing in the ruts,
docs/MUD_ONE_SURFACE_PLAN.md stage G) and M_GT_Water (a ford's simulated surface, docs/WATER_PLAN.md
stages W1, WS1, WS2 and W4: the depth tint, the sourced ripple normal carried by the field's own flow, and the foam).

Run with Art\\setup_m6_water.bat (close the editor first). The order is setup_m6_textures, THIS, setup_m6_mud,
setup_m6_hide: this script only needs MPC_TrackPaint's RT_TrackPaint as a linear default for its texture parameter,
and AGTMudPatch loads the material it builds by path at runtime.

What it builds. AGTMudPatch lays a second grid over its box, WaterMesh, the same vertices as the mud mesh but at the
ground plus the section's WaterTableCm (-25 cm by default since stage J3, -20 until then: the water table sits 25 cm
under the undisturbed ground, so a 30 cm rut holds about 5 cm of water and untouched mud holds none). The weather
lifts the whole sheet by
WetTableLiftCm x wetness, as AGTWaterSheet lifts a ford. This material is what that grid wears:

- Translucent, two-sided, its own master (water does not get wet: it stays outside MF_Weather, as M_GT_Water does),
  with the surface forward-shading translucency lighting mode so the sky reflects in it.
- It reads the patch's own field texture (MudField, R the mud height in metres) inside PatchMin / PatchSize, exactly
  as M_GT_Mud does, and the water's depth at a pixel is WaterTableCm minus that height, in cm. Where the mud stands
  above the table the depth is negative and the pixel's opacity is 0: only the cells below the water draw, so there
  is no sheet over the flat mud and no plane per bog - the surface follows the ground, cell by cell.
- The look is build_water_material's (setup_m6_hide.py: a colour, a roughness, an opacity) with the depth and the
  fresnel added: the tint goes from ShallowColor to DeepColor over DeepCm of water, the opacity from ShallowOpacity
  to DeepOpacity with FresnelOpacity more at a grazing angle, and the roughness falls to the gloss at that angle.
  The colour is brown and not the ford's blue-green: this is the water that stands in a wheel rut.

The mesh's translucency sort priority is set in AGTMudPatch (above the mud mesh's). Nothing here touches the mud's
shape, the physics or the camera; the physics half of stage G (a wheel's water depth inside a patch) is built behind
UGTMudSubsystem::bRutWaterPhysics and is off. Rebuilt from scratch every run; safe to re-run.
"""
import unreal

MAT = "/Game/GrandTour/Materials"
TERRAIN = "/Game/GrandTour/Terrain"
MATERIAL = "M_GT_MudWater"

# The water table's own default; AGTMudPatch pushes the section's WaterTableCm (plus the weather's lift) onto the
# instance every time it moves, so this is only what the master shows on its own.
WATER_TABLE_CM = -25.0   # stage J3 (2026-09-16): -20 until then, lowered on the user's "the waterline needs to be lowered a bit, maybe by half"
# The tint: mud water, not the ford's blue-green. Shallow over a rut floor a centimetre under the table, deep at DeepCm.
SHALLOW_COLOR = (0.100, 0.085, 0.060)
DEEP_COLOR = (0.018, 0.014, 0.010)
DEEP_CM = 12.0
# The opacity: thin at the rim, nearly solid where it is deep, and more of it at a grazing angle (the fresnel).
SHALLOW_OPACITY = 0.35
DEEP_OPACITY = 0.92
FRESNEL_OPACITY = 0.35
# The gloss. 0.05 is the ford water's roughness; a grazing angle takes it to GLOSS_ROUGHNESS, which is what puts the
# sky in the water.
WATER_ROUGHNESS = 0.06
GLOSS_ROUGHNESS = 0.02
# How fast the sheet fades in at the water's edge (the cell where the mud crosses the table), cm of depth.
EDGE_FADE_CM = 1.0

# Inputs: WorldPos, PatchMin, PatchSize, Tex, TableCm, ShallowColor, DeepColor, DeepCm, ShallowOpacity, DeepOpacity,
# FresnelOpacity, Rough, GlossRough, EdgeFadeCm, CameraVec, VertexNormal.
# Outputs: BaseColor (main), Opacity, Rough.
# Texture2DSampleLevel (not Texture2DSample) for the field, as M_GT_Mud does: it is a transient texture with one mip
# and no gradients worth taking.
WATER_HLSL = """float2 uv = saturate((WorldPos.xy - PatchMin.xy) / max(PatchSize.xy, 1.0));
float4 s = Texture2DSampleLevel(Tex, TexSampler, uv, 0);
float mudCm = s.r * 100.0;
float d = TableCm - mudCm;                       // cm of water standing over the mud at this pixel
float deep = saturate(d / max(DeepCm, 0.5));
float edge = saturate(d / max(EdgeFadeCm, 0.05));  // 0 wherever the mud is at or above the table: no sheet on flat mud
float3 n = normalize(VertexNormal.xyz);
float3 v = normalize(CameraVec.xyz);
float fres = pow(1.0 - saturate(abs(dot(n, v))), 5.0);
float3 col = lerp(ShallowColor.rgb, DeepColor.rgb, deep);
float a = saturate(lerp(ShallowOpacity, DeepOpacity, deep) + FresnelOpacity * fres) * edge;
Opacity = a;
Rough = lerp(Rough_, GlossRough, fres);
return col;
"""

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def log(msg):
    unreal.log("SETUP_M6_WATER " + msg)


def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


def custom(m, desc, inputs, code, x, y, outputs=()):
    node = mel.create_material_expression(m, unreal.MaterialExpressionCustom, x, y)
    node.set_editor_property("description", desc)
    node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    ins = []
    for name in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        ins.append(ci)
    node.set_editor_property("inputs", ins)
    outs = []
    for name, kind in outputs:
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", name)
        co.set_editor_property("output_type", kind)
        outs.append(co)
    node.set_editor_property("additional_outputs", outs)
    node.set_editor_property("code", code)
    return node


def scalar(m, name, value, x, y):
    e = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", value)
    return e


def vector(m, name, colour, x, y):
    e = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", unreal.LinearColor(*colour))
    return e


rt_full = TERRAIN + "/RT_TrackPaint"
if not eal.does_asset_exist(rt_full):
    raise SystemExit("missing " + rt_full + " (run Art/setup_m1_trackpaint.bat first); the field parameter needs a linear default")
rt = eal.load_asset(rt_full)

mat_full = MAT + "/" + MATERIAL
if eal.does_asset_exist(mat_full):
    eal.delete_asset(mat_full)
m = tools.create_asset(MATERIAL, MAT, unreal.Material, unreal.MaterialFactoryNew())
if m is None:
    raise SystemExit("could not create " + mat_full)
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property("two_sided", True)
# The sky in the water: the default volumetric translucency lighting takes no specular at all, so the sheet would be a
# flat tint. Surface forward shading gives it the sky light's reflection, which is the whole point of a puddle.
# 5.8's Python spells "Surface ForwardShading" TLM_SURFACE_PER_PIXEL_LIGHTING (the C++ enumerator's name, not the
# editor's label), so the mode is looked up by name over the candidates and what was actually set is logged.
lighting = "default (volumetric, no specular)"
available = [n for n in dir(unreal.TranslucencyLightingMode) if n.startswith("TLM_")]
for candidate in ("TLM_SURFACE_PER_PIXEL_LIGHTING", "TLM_SURFACE_FORWARD_SHADING", "TLM_SURFACE"):
    mode = getattr(unreal.TranslucencyLightingMode, candidate, None)
    if mode is None:
        continue
    try:
        m.set_editor_property("translucency_lighting_mode", mode)
        lighting = candidate
        break
    except Exception as error:
        unreal.log_warning("SETUP_M6_WATER could not set the translucency lighting mode to %s (%s)" % (candidate, error))
if lighting.startswith("default"):
    unreal.log_warning("SETUP_M6_WATER no surface translucency lighting mode among %s; the sheet takes no specular and the sky will not show in it" % available)
log("translucency lighting mode %s (of %s)" % (lighting, available))

wpos = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -1100, -300)
wpos.set_editor_property("world_position_shader_offset", unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
patch_min = vector(m, "PatchMin", (0.0, 0.0, 0.0, 0.0), -1100, -150)
patch_size = vector(m, "PatchSize", (100.0, 100.0, 0.0, 0.0), -1100, 0)
tex = mel.create_material_expression(m, unreal.MaterialExpressionTextureObjectParameter, -1100, 150)
tex.set_editor_property("parameter_name", "MudField")
tex.set_editor_property("texture", rt)
tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
table = scalar(m, "WaterTableCm", WATER_TABLE_CM, -1100, 300)
shallow = vector(m, "ShallowColor", SHALLOW_COLOR + (1.0,), -1100, 400)
deep = vector(m, "DeepColor", DEEP_COLOR + (1.0,), -1100, 550)
deep_cm = scalar(m, "WaterDeepCm", DEEP_CM, -1100, 700)
shallow_op = scalar(m, "ShallowOpacity", SHALLOW_OPACITY, -1100, 800)
deep_op = scalar(m, "DeepOpacity", DEEP_OPACITY, -1100, 900)
fresnel_op = scalar(m, "FresnelOpacity", FRESNEL_OPACITY, -1100, 1000)
rough = scalar(m, "WaterRoughness", WATER_ROUGHNESS, -1100, 1100)
gloss = scalar(m, "GlossRoughness", GLOSS_ROUGHNESS, -1100, 1200)
edge = scalar(m, "EdgeFadeCm", EDGE_FADE_CM, -1100, 1300)
camera = mel.create_material_expression(m, unreal.MaterialExpressionCameraVectorWS, -1100, 1400)
vnormal = mel.create_material_expression(m, unreal.MaterialExpressionVertexNormalWS, -1100, 1500)

surface = custom(m, "Mud water (PS)",
                 ("WorldPos", "PatchMin", "PatchSize", "Tex", "TableCm", "ShallowColor", "DeepColor", "DeepCm",
                  "ShallowOpacity", "DeepOpacity", "FresnelOpacity", "Rough_", "GlossRough", "EdgeFadeCm",
                  "CameraVec", "VertexNormal"),
                 WATER_HLSL, -600, 200,
                 outputs=(("Opacity", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
                          ("Rough", unreal.CustomMaterialOutputType.CMOT_FLOAT1)))

for node, name in ((wpos, "WorldPos"), (patch_min, "PatchMin"), (patch_size, "PatchSize"), (tex, "Tex"), (table, "TableCm"),
                   (shallow, "ShallowColor"), (deep, "DeepColor"), (deep_cm, "DeepCm"),
                   (shallow_op, "ShallowOpacity"), (deep_op, "DeepOpacity"), (fresnel_op, "FresnelOpacity"),
                   (rough, "Rough_"), (gloss, "GlossRough"), (edge, "EdgeFadeCm"),
                   (camera, "CameraVec"), (vnormal, "VertexNormal")):
    connect(node, "", surface, name)

for node, out_name, prop in ((surface, "", unreal.MaterialProperty.MP_BASE_COLOR),
                             (surface, "Opacity", unreal.MaterialProperty.MP_OPACITY),
                             (surface, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)):
    if not mel.connect_material_property(node, out_name, prop):
        raise SystemExit("could not connect %s.%r to %s" % (node.get_name(), out_name, prop))

errors = [str(e) for e in mel.recompile_material(m)]
eal.save_loaded_asset(m)
if errors:
    for error in errors:
        unreal.log_error("SETUP_M6_WATER " + error)
    raise SystemExit(MATERIAL + " has compile errors")
log("%s: translucent, two-sided, lighting %s, %d expressions; the depth is WaterTableCm (%.1f cm, the section's own on the "
    "instance) over MudField's height inside PatchMin/PatchSize, and a pixel whose mud stands above the table is fully "
    "transparent (EdgeFadeCm %.1f), so only the ruts hold water"
    % (MATERIAL, lighting, mel.get_num_material_expressions(m), WATER_TABLE_CM, EDGE_FADE_CM))
log("water look: tint %.3f %.3f %.3f shallow -> %.3f %.3f %.3f over WaterDeepCm %.0f cm, opacity %.2f -> %.2f with "
    "FresnelOpacity %.2f at a grazing angle, roughness %.2f -> %.2f there (the sky); derived from build_water_material's "
    "ford sheet (setup_m6_hide.py), tinted brown because this is rut water"
    % (SHALLOW_COLOR + DEEP_COLOR + (DEEP_CM, SHALLOW_OPACITY, DEEP_OPACITY, FRESNEL_OPACITY, WATER_ROUGHNESS, GLOSS_ROUGHNESS)))


# ---- M_GT_Water: a ford's sheet (docs/WATER_PLAN.md, stages W1, WS1, WS2 and W4) -----------------------
# Built here since W1 (it was built once, and only if missing, by build_water_material in setup_m6_hide.py, so a
# change to it never reached the asset). Rebuilt from scratch every run like M_GT_MudWater above.
#
# AGTWaterSheet owns an FGTWaterField, a shallow-water height field over the ford's footprint, and lays a procedural
# grid at the field's cells; every frame it uploads the field into a half-float RGBA texture and sets it here as
# FieldTex with the field's own frame: FieldMin (the world XY of its origin corner), FieldSize (its span in cm),
# FieldAxisX and FieldAxisY (the grid is rotated so its X runs along the flow) and FieldTexels. The texture's
# channels (AGTWaterSheet::FieldTexel) are
#   R  the surface's height over the water level, cm   -> the vertex shader's displacement, WS2's crest shading
#   G  the water column, cm (the depth plus a solid's lid) -> W4's depth tint and opacity, and the dry mask
#   B  the cell's flow along the field's X, cm/s        -> W4: what pans the ripple normal
#   A  the same along its Y, cm/s
#
# - The vertex shader displaces Z by R, so the mesh IS the simulated surface: the current, a ring spreading from a
#   disturbance and its reflection off the banks are all the field's, not a panning texture's.
# - The pixel shader takes the surface's own slope from the texture's finite differences one texel each way, scaled
#   by NormalGainCm, adds W4's ripple tilt to it and hands the sum over as a world-space normal (tangent_space_normal
#   cleared - the grid has no useful tangent basis of its own).
# - Opacity is masked by G: a cell with less than DryCutCm of water draws nothing, so the sheet stops at the
#   waterline instead of lying flat over the banks.
#
# W4, the look (this is the stage the user asked for: "getting the color/opacity of the water correct"):
# - COLOUR AND OPACITY BY DEPTH, M_GT_MudWater's pattern above with its own numbers and the depth read per pixel out
#   of the field's G channel and not from a DepthFade node - the field knows how deep it is, the scene depth only
#   knows how far away the bed is. Silty upland river, not a pool: ShallowColor -> DeepColor over WaterDeepCm,
#   ShallowOpacity -> DeepOpacity with FresnelOpacity more at a grazing angle, WaterRoughness falling to
#   GlossRoughness there (the sky).
# - THE RIPPLE NORMAL CARRIED BY THE FLOW. A sourced CC0 water normal (RippleTex, T_GT_Water_N, see
#   Art/Textures/Water/SOURCE.txt), sampled twice per layer along the local velocity with the phases half a period
#   apart and cross-faded on a sawtooth of FlowPeriodS - the flow-map technique, so the ripples ride the current
#   instead of stretching with it. Two layers, WaterTileCm and WaterTileCm2, the second at NormalStrength and
#   FlowTexScale2 of the first. Where the water is standing they drift at StillDriftCmPerS so still water is not
#   frozen. Only the RG channels are read and used as a slope: a normal-compressed texture has no usable B in the
#   shader, and a slope is what the field's own finite differences already are.
# - FOAM FROM THE SIMULATED SURFACE. Three mechanisms, the largest winning: the shallows (G under FoamDepthCm, so the
#   banks and the ring around anything standing in the water), the steep surface (the field's own slope over
#   FoamSlope: the bow wave's crest, a ring's front) and the fast water (B/A over FoamSpeedCmPerS). Broken up by a
#   two-octave hashed value noise at FoamNoiseCm that drifts with the flow. Foam takes the colour to FoamColor, the
#   opacity to 1 and the roughness to FoamRoughness. The noise is procedural, which the plan allows here.
# - WS2's height and slope shading is KEPT as multipliers on top (CrestColorGain, SlopeShadeGain, CrestOpacityGain),
#   because that is what makes the motion at rest visible at all: a normal tilt on a glossy translucent sheet under
#   a flat sky moved 0.50 % of the bank picture's pixels before it went in, and 10.45 % after.
FORD_ROUGHNESS = 0.08          # W4: W1's 0.05, opened a little now that the ripple normal has something to do
GLOSS_ROUGHNESS = 0.03         # at a grazing angle (the sky in the water)
SHALLOW_COLOR = (0.10, 0.13, 0.10)     # a silty upland river seen through a hand's depth of it
DEEP_COLOR = (0.02, 0.035, 0.03)       # and what it comes to when you cannot see the bed
# REVERTED 2026-09-18. A follow-up raised these to 70 / 0.45 / 0.45 and added a wet-bed darkening and a refraction
# pin; the user drove it and said "Revert it, that seems to have messed up the physics of the water", so the whole
# follow-up is out and W4's shipped numbers stand. The one finding worth keeping is in VEHICLE_BUILD_SYSTEM 45:
# refraction was connected, both of 5.8's modes were measured on a frozen on/off picture pair, and BOTH moved
# 0.00-0.02 % of the box, because the engine's distortion offset is bounded by the gap between the surface and what is
# behind it and a ford's bed is 18 cm down. It is a dead end at this depth; it does not come back.
WATER_DEEP_CM = 120.0                  # the depth at which the tint has reached DeepColor
SHALLOW_OPACITY = 0.25
DEEP_OPACITY = 0.85
FRESNEL_OPACITY = 0.30
NORMAL_GAIN_CM = 1.0    # the gain on the finite-difference slope; AGTWaterSheet pushes its own onto the instance
DRY_CUT_CM = 1.0        # water shallower than this draws nothing
# WS2's follow-up: the surface has to SHOW that it moves. W1 learned this once already - a normal tilt on a
# roughness-0.05 translucent sheet under a flat sky moves almost no pixels (2.76 % then, 0.50 % for WS2's wind) - so
# the simulated height itself shades the water: the colour and the opacity ride on FieldTex.r (cm over the level) and
# a slope term rides on the same finite-difference normal against a fixed light.
CREST_COLOR_GAIN = 0.25    # x the base colour per cm of height, clamped 0.5..1.6
SLOPE_SHADE_GAIN = 0.6     # the same clamp, from the normal's tilt toward a fixed light
CREST_OPACITY_GAIN = 0.1   # + opacity per cm of height, saturated
# W4's ripple (the sourced normal, panned by the field's own velocity).
WATER_TILE_CM = 200.0       # the first layer's tile
WATER_TILE_2_CM = 450.0     # the second's
NORMAL_STRENGTH = 0.6       # the second layer's weight
RIPPLE_GAIN = 1.0           # the master on both layers' slope (0 takes the ripple off and leaves the field's own)
FLOW_TEX_SCALE = 1.0        # how much of the water's own speed carries the first layer
FLOW_TEX_SCALE_2 = 0.6      # and the second
FLOW_PERIOD_S = 2.0         # the cross-fade's period: a sample is never panned more than half of this
STILL_DRIFT_CM_PER_S = 8.0  # what carries the ripple where the water is standing, so it is not frozen
# W4's foam. Two of the three thresholds are not the plan's, and both were measured on the ford pictures: at the
# plan's FoamSlope 0.15 and FoamSpeedCmPerS 120 the foam painted the WHOLE channel - hide_25's water box read
# 41.19 % of its pixels over 200 in the brightest channel against 1.88 % in the same box with the flow and the wind
# off, and hide_24's 42.26 % - because this ford's own current is 143 cm/s where the route crosses (over the plan's
# 120) and WS2's wind puts 1.5 cm of roughness on 25 cm cells, which is a finite-difference slope of about
# 0.04 cm/cm against a threshold of 0.15. So both were set above what a drivable crossing does on its own: white
# water is faster and steeper than a ford you can drive through, and the user lowers them by name to get rapids.
FOAM_DEPTH_CM = 12.0        # under this much water it foams (the banks, and anything standing in the water)
FOAM_SLOPE = 0.6            # cm of surface per cm of ground: a 20 cm bow crest over a 25 cm cell is 0.8, the wind's own ripple 0.04
FOAM_SPEED_CM_PER_S = 250.0 # and where the water runs faster than this (this ford runs 143 at the crossing)
FOAM_NOISE_CM = 80.0        # the noise that breaks it up, drifting with the flow
FOAM_COLOR = (0.7, 0.7, 0.68)
FOAM_ROUGHNESS = 0.6

# Inputs: WorldPos (offsets excluded), FieldMin, FieldSize, AxisX, AxisY, Tex.
# Output: the world-space offset, which is only ever in Z.
FORD_WPO_HLSL = """float2 d = WorldPos.xy - FieldMin.xy;
float2 local = float2(dot(d, AxisX.xy), dot(d, AxisY.xy));
float2 uv = saturate(local / max(FieldSize.xy, 1.0));
float h = Texture2DSampleLevel(Tex, TexSampler, uv, 0).r;
return float3(0.0, 0.0, h);
"""

# The pixel shader. Main output: the world-space normal (the field's own slope plus the ripple's tilt).
# Additional outputs: Color (the depth tint, WS2's shade and the foam), OpacityOut (already masked by the dry cut),
# Rough (the fresnel gloss and the foam) and Foam (the mask itself, for a diagnostic).
FORD_SURFACE_HLSL = """float2 d = WorldPos.xy - FieldMin.xy;
float2 local = float2(dot(d, AxisX.xy), dot(d, AxisY.xy));
float2 uv = saturate(local / max(FieldSize.xy, 1.0));
float2 texels = max(Texels.xy, 1.0);
float2 texel = 1.0 / texels;
float4 here = Texture2DSampleLevel(Tex, TexSampler, uv, 0);
float hx0 = Texture2DSampleLevel(Tex, TexSampler, saturate(uv - float2(texel.x, 0.0)), 0).r;
float hx1 = Texture2DSampleLevel(Tex, TexSampler, saturate(uv + float2(texel.x, 0.0)), 0).r;
float hy0 = Texture2DSampleLevel(Tex, TexSampler, saturate(uv - float2(0.0, texel.y)), 0).r;
float hy1 = Texture2DSampleLevel(Tex, TexSampler, saturate(uv + float2(0.0, texel.y)), 0).r;
float cellX = max(FieldSize.x / texels.x, 1.0);
float cellY = max(FieldSize.y / texels.y, 1.0);
float gx = (hx1 - hx0) / (2.0 * cellX) * NormalGain;
float gy = (hy1 - hy0) / (2.0 * cellY) * NormalGain;
float2 fieldSlope = float2(gx, gy);          // the simulated surface's own slope, in the field's axes
float mask = saturate(here.g / max(DryCut, 0.05));
Mask = mask;

// ---- the flow that carries the ripple: the cell's own velocity, cm/s, in the field's axes ----
float2 vel = float2(here.b, here.a);
float speed = length(vel);
// standing water still drifts, or the ripple is a frozen photograph of one
float2 flow = vel + float2(0.60, 0.80) * StillDrift * (1.0 - saturate(speed / max(StillDrift, 0.01)));

// ---- two layers of the sourced normal, each sampled twice half a period apart and cross-faded (a flow map) ----
float phase = Time / max(FlowPeriod, 0.05);
float f0 = frac(phase);
float f1 = frac(phase + 0.5);
float w = abs(1.0 - 2.0 * f0);
float2 slope = 0.0;
for (int layer = 0; layer < 2; ++layer)
{
	float tile = max(layer == 0 ? Tile1 : Tile2, 1.0);
	float2 carry = flow * (layer == 0 ? FlowScale : FlowScale2);
	float2 base = local / tile;
	float2 p0 = base - carry * ((f0 - 0.5) * max(FlowPeriod, 0.05)) / tile;
	float2 p1 = base - carry * ((f1 - 0.5) * max(FlowPeriod, 0.05)) / tile;
	// only RG: a normal-compressed texture's B is not usable in the shader, and RG IS the slope
	float2 t0 = Texture2DSample(Ripple, RippleSampler, p0).rg * 2.0 - 1.0;
	float2 t1 = Texture2DSample(Ripple, RippleSampler, p1).rg * 2.0 - 1.0;
	slope += lerp(t0, t1, w) * (layer == 0 ? 1.0 : Strength);
}
slope.y = -slope.y;                      // the source is DirectX convention (green down)
slope *= RippleGain * mask;              // no ripples on a dry cell
float2 total = fieldSlope + slope;
float2 grad = AxisX.xy * total.x + AxisY.xy * total.y;
float3 n = normalize(float3(-grad.x, -grad.y, 1.0));

// ---- WS2's shading, kept: the surface's own height and its tilt toward a fixed light ----
float3 L = normalize(float3(0.40, -0.25, 0.88));
float tilt = dot(n, L) - L.z;
float shade = clamp(1.0 + CrestColor * here.r + SlopeShade * tilt, 0.5, 1.6);

// ---- W4: the colour and the opacity by the field's own depth ----
float depthCm = max(here.g, 0.0);
float deep = saturate(depthCm / max(DeepCm, 1.0));
float3 col = lerp(ShallowColor.rgb, DeepColor.rgb, deep) * shade;
float3 v = normalize(CameraVec.xyz);
float fres = pow(1.0 - saturate(abs(dot(n, v))), 5.0);
float a = saturate(lerp(ShallowOpacity, DeepOpacity, deep) + FresnelOpacity * fres + CrestOpacity * here.r);
float rough = lerp(Rough_, GlossRough, fres);

// ---- W4: the foam, from the simulated surface ----
float foamShallow = 1.0 - saturate(depthCm / max(FoamDepth, 0.5));
float foamSlope = saturate(length(fieldSlope) / max(FoamSlopeAsk, 0.01));
float foamSpeed = saturate((speed - FoamSpeed) / max(FoamSpeed, 1.0));
float foam = saturate(max(foamShallow, max(foamSlope, foamSpeed)));
// two octaves of hashed value noise, drifting with the water so the foam is not painted on the bed
float2 q = (local - flow * Time) / max(FoamNoise, 1.0);
float noise = 0.0;
float amp = 1.0;
float norm = 0.0;
for (int octave = 0; octave < 2; ++octave)
{
	float2 cell = floor(q);
	float2 f = frac(q);
	f = f * f * (3.0 - 2.0 * f);
	float h00 = frac(sin(dot(cell + float2(0.0, 0.0), float2(12.9898, 78.233))) * 43758.5453);
	float h10 = frac(sin(dot(cell + float2(1.0, 0.0), float2(12.9898, 78.233))) * 43758.5453);
	float h01 = frac(sin(dot(cell + float2(0.0, 1.0), float2(12.9898, 78.233))) * 43758.5453);
	float h11 = frac(sin(dot(cell + float2(1.0, 1.0), float2(12.9898, 78.233))) * 43758.5453);
	noise += amp * lerp(lerp(h00, h10, f.x), lerp(h01, h11, f.x), f.y);
	norm += amp;
	amp *= 0.5;
	q *= 2.6;
}
noise = noise / max(norm, 0.001);
foam = saturate(foam * (0.25 + 1.25 * noise));
Foam = foam;
col = lerp(col, FoamColor.rgb, foam);
a = lerp(a, 1.0, foam);
rough = lerp(rough, FoamRough, foam);

Color = col;
OpacityOut = a * mask;
Rough = rough;
return n;
"""

FORD_MATERIAL = "M_GT_Water"
RIPPLE_TEXTURE = "/Game/GrandTour/Textures/Water/T_GT_Water_N"
ford_full = MAT + "/" + FORD_MATERIAL
if not eal.does_asset_exist(RIPPLE_TEXTURE):
    raise SystemExit("missing " + RIPPLE_TEXTURE + " (run Art/setup_m6_textures.bat first, which imports the CC0 "
                     "water normal from Art/Textures/Water; see that folder's SOURCE.txt). W4's ripple has no texture "
                     "to sample and a normal-compressed parameter cannot take a linear-colour default.")
ripple = eal.load_asset(RIPPLE_TEXTURE)
if eal.does_asset_exist(ford_full):
    eal.delete_asset(ford_full)
w = tools.create_asset(FORD_MATERIAL, MAT, unreal.Material, unreal.MaterialFactoryNew())
if w is None:
    raise SystemExit("could not create " + ford_full)
w.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
w.set_editor_property("two_sided", True)
ford_lighting = "default (volumetric, no specular)"
for candidate in ("TLM_SURFACE_PER_PIXEL_LIGHTING", "TLM_SURFACE_FORWARD_SHADING", "TLM_SURFACE"):
    mode = getattr(unreal.TranslucencyLightingMode, candidate, None)
    if mode is None:
        continue
    try:
        w.set_editor_property("translucency_lighting_mode", mode)
        ford_lighting = candidate
        break
    except Exception as error:
        unreal.log_warning("SETUP_M6_WATER could not set %s's translucency lighting mode to %s (%s)" % (FORD_MATERIAL, candidate, error))
# The normal comes out of the field's own frame, which is a world-space frame, so the material is told its normal is
# already in world space.
ford_space = "world"
try:
    w.set_editor_property("tangent_space_normal", False)
except Exception as error:
    ford_space = "tangent (could not clear tangent_space_normal: %s)" % error
    unreal.log_warning("SETUP_M6_WATER " + ford_space)

# NO REFRACTION (reverted 2026-09-18, the user: "Revert it, that seems to have messed up the physics of the water").
# The material's refraction_method is left at its default and MP_REFRACTION is not connected. It was built both ways
# and measured, and it is a dead end at this depth, which is why it is not coming back: on a frozen on/off picture
# pair RM_PIXEL_NORMAL_OFFSET moved 0.00 % of the box by more than 12 of 255 (mean change 1.28, biggest 9) and
# RM_INDEX_OF_REFRACTION 0.02 % (mean 2.01, biggest 17). The engine's distortion offset is bounded by how far the
# refracting surface stands in front of what is behind it, and over a ford's bed that gap is the water's own 18 cm,
# so the bend is a fraction of a pixel whatever the mode.

ford_wpos = mel.create_material_expression(w, unreal.MaterialExpressionWorldPosition, -1400, 200)
ford_wpos.set_editor_property("world_position_shader_offset", unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
field_min = vector(w, "FieldMin", (0.0, 0.0, 0.0, 0.0), -1400, 350)
field_size = vector(w, "FieldSize", (100.0, 100.0, 0.0, 0.0), -1400, 500)
field_axis_x = vector(w, "FieldAxisX", (1.0, 0.0, 0.0, 0.0), -1400, 650)
field_axis_y = vector(w, "FieldAxisY", (0.0, 1.0, 0.0, 0.0), -1400, 800)
field_texels = vector(w, "FieldTexels", (128.0, 128.0, 0.0, 0.0), -1400, 950)
field_tex = mel.create_material_expression(w, unreal.MaterialExpressionTextureObjectParameter, -1400, 1100)
field_tex.set_editor_property("parameter_name", "FieldTex")
field_tex.set_editor_property("texture", rt)
field_tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
normal_gain = scalar(w, "NormalGainCm", NORMAL_GAIN_CM, -1400, 1250)
dry_cut = scalar(w, "DryCutCm", DRY_CUT_CM, -1400, 1400)
crest_colour_gain = scalar(w, "CrestColorGain", CREST_COLOR_GAIN, -1400, 1550)
slope_shade_gain = scalar(w, "SlopeShadeGain", SLOPE_SHADE_GAIN, -1400, 1700)
crest_opacity_gain = scalar(w, "CrestOpacityGain", CREST_OPACITY_GAIN, -1400, 1850)
# W4: the depth tint and the opacity
shallow_col = vector(w, "ShallowColor", SHALLOW_COLOR + (1.0,), -1900, -300)
deep_col = vector(w, "DeepColor", DEEP_COLOR + (1.0,), -1900, -150)
water_deep_cm = scalar(w, "WaterDeepCm", WATER_DEEP_CM, -1900, 0)
shallow_op = scalar(w, "ShallowOpacity", SHALLOW_OPACITY, -1900, 150)
deep_op = scalar(w, "DeepOpacity", DEEP_OPACITY, -1900, 300)
fresnel_op = scalar(w, "FresnelOpacity", FRESNEL_OPACITY, -1900, 450)
ford_rough = scalar(w, "WaterRoughness", FORD_ROUGHNESS, -1900, 600)
gloss_rough = scalar(w, "GlossRoughness", GLOSS_ROUGHNESS, -1900, 750)
# W4: the ripple
ripple_tex = mel.create_material_expression(w, unreal.MaterialExpressionTextureObjectParameter, -1900, 900)
ripple_tex.set_editor_property("parameter_name", "RippleTex")
ripple_tex.set_editor_property("texture", ripple)
ripple_tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
tile1 = scalar(w, "WaterTileCm", WATER_TILE_CM, -1900, 1050)
tile2 = scalar(w, "WaterTileCm2", WATER_TILE_2_CM, -1900, 1200)
normal_strength = scalar(w, "NormalStrength", NORMAL_STRENGTH, -1900, 1350)
ripple_gain = scalar(w, "RippleGain", RIPPLE_GAIN, -1900, 1500)
flow_scale = scalar(w, "FlowTexScale", FLOW_TEX_SCALE, -1900, 1650)
flow_scale2 = scalar(w, "FlowTexScale2", FLOW_TEX_SCALE_2, -1900, 1800)
flow_period = scalar(w, "FlowPeriodS", FLOW_PERIOD_S, -1900, 1950)
still_drift = scalar(w, "StillDriftCmPerS", STILL_DRIFT_CM_PER_S, -1900, 2100)
# W4: the foam
foam_depth = scalar(w, "FoamDepthCm", FOAM_DEPTH_CM, -2400, -300)
foam_slope = scalar(w, "FoamSlope", FOAM_SLOPE, -2400, -150)
foam_speed = scalar(w, "FoamSpeedCmPerS", FOAM_SPEED_CM_PER_S, -2400, 0)
foam_noise = scalar(w, "FoamNoiseCm", FOAM_NOISE_CM, -2400, 150)
foam_col = vector(w, "FoamColor", FOAM_COLOR + (1.0,), -2400, 300)
foam_rough = scalar(w, "FoamRoughness", FOAM_ROUGHNESS, -2400, 450)
ford_camera = mel.create_material_expression(w, unreal.MaterialExpressionCameraVectorWS, -2400, 600)
ford_time = mel.create_material_expression(w, unreal.MaterialExpressionTime, -2400, 750)

displace = custom(w, "Water surface displace (VS)",
                  ("WorldPos", "FieldMin", "FieldSize", "AxisX", "AxisY", "Tex"),
                  FORD_WPO_HLSL, -900, 200)
surface = custom(w, "Water surface (PS)",
                 ("WorldPos", "FieldMin", "FieldSize", "AxisX", "AxisY", "Texels", "Tex", "NormalGain", "DryCut",
                  "CrestColor", "SlopeShade", "CrestOpacity",
                  "ShallowColor", "DeepColor", "DeepCm", "ShallowOpacity", "DeepOpacity", "FresnelOpacity",
                  "Rough_", "GlossRough",
                  "Ripple", "Tile1", "Tile2", "Strength", "RippleGain", "FlowScale", "FlowScale2", "FlowPeriod",
                  "StillDrift",
                  "FoamDepth", "FoamSlopeAsk", "FoamSpeed", "FoamNoise", "FoamColor", "FoamRough",
                  "CameraVec", "Time"),
                 FORD_SURFACE_HLSL, -900, 700,
                 outputs=(("Mask", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
                          ("Color", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
                          ("OpacityOut", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
                          ("Rough", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
                          ("Foam", unreal.CustomMaterialOutputType.CMOT_FLOAT1)))

for node, name in ((ford_wpos, "WorldPos"), (field_min, "FieldMin"), (field_size, "FieldSize"),
                   (field_axis_x, "AxisX"), (field_axis_y, "AxisY"), (field_tex, "Tex")):
    connect(node, "", displace, name)
for node, name in ((ford_wpos, "WorldPos"), (field_min, "FieldMin"), (field_size, "FieldSize"),
                   (field_axis_x, "AxisX"), (field_axis_y, "AxisY"), (field_texels, "Texels"),
                   (field_tex, "Tex"), (normal_gain, "NormalGain"), (dry_cut, "DryCut"),
                   (crest_colour_gain, "CrestColor"), (slope_shade_gain, "SlopeShade"),
                   (crest_opacity_gain, "CrestOpacity"),
                   (shallow_col, "ShallowColor"), (deep_col, "DeepColor"), (water_deep_cm, "DeepCm"),
                   (shallow_op, "ShallowOpacity"), (deep_op, "DeepOpacity"), (fresnel_op, "FresnelOpacity"),
                   (ford_rough, "Rough_"), (gloss_rough, "GlossRough"),
                   (ripple_tex, "Ripple"), (tile1, "Tile1"), (tile2, "Tile2"), (normal_strength, "Strength"),
                   (ripple_gain, "RippleGain"), (flow_scale, "FlowScale"), (flow_scale2, "FlowScale2"),
                   (flow_period, "FlowPeriod"), (still_drift, "StillDrift"),
                   (foam_depth, "FoamDepth"), (foam_slope, "FoamSlopeAsk"), (foam_speed, "FoamSpeed"),
                   (foam_noise, "FoamNoise"), (foam_col, "FoamColor"), (foam_rough, "FoamRough"),
                   (ford_camera, "CameraVec"), (ford_time, "Time")):
    connect(node, "", surface, name)

# The colour, the opacity and the roughness all come out of the one node already finished (the depth tint x WS2's
# shade, then the foam over it), and the opacity is already masked, so a cell with no water in it draws nothing.
for node, out_name, prop in ((surface, "Color", unreal.MaterialProperty.MP_BASE_COLOR),
                             (surface, "Rough", unreal.MaterialProperty.MP_ROUGHNESS),
                             (surface, "OpacityOut", unreal.MaterialProperty.MP_OPACITY),
                             (surface, "", unreal.MaterialProperty.MP_NORMAL),
                             (displace, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)):
    if not mel.connect_material_property(node, out_name, prop):
        raise SystemExit("could not connect %s.%r to %s" % (node.get_name(), out_name, prop))

ford_errors = [str(e) for e in mel.recompile_material(w)]
eal.save_loaded_asset(w)
if ford_errors:
    for error in ford_errors:
        unreal.log_error("SETUP_M6_WATER " + error)
    raise SystemExit(FORD_MATERIAL + " has compile errors")
log("%s: translucent, two-sided, lighting %s, normal in %s space, %d expressions. WS1: the vertex shader displaces Z "
    "by FieldTex.r (the simulated surface over the water level, cm) inside FieldMin/FieldSize along "
    "FieldAxisX/FieldAxisY, the pixel shader takes its world normal from that texture's finite differences one texel "
    "each way at NormalGainCm %.2f, and FieldTex.g (the water column in cm) masks the opacity under DryCutCm %.1f. "
    "AGTWaterSheet uploads the texture and sets every parameter on its own instance every frame."
    % (FORD_MATERIAL, ford_lighting, ford_space, mel.get_num_material_expressions(w), NORMAL_GAIN_CM, DRY_CUT_CM))
log("water look W4: depth tint ShallowColor%.3f %.3f %.3f -> DeepColor %.3f %.3f %.3f over WaterDeepCm %.0f cm read"
    "from FieldTex.g per pixel (not a DepthFade node: the field knows the depth), opacity ShallowOpacity %.2f -> "
    "DeepOpacity %.2f with FresnelOpacity %.2f at a grazing angle, roughness WaterRoughness %.2f -> GlossRoughness "
    "%.2f there; WS2's own shading kept on top as multipliers (CrestColorGain %.2f per cm, SlopeShadeGain %.2f, "
    "CrestOpacityGain %.2f per cm)"
    % (SHALLOW_COLOR + DEEP_COLOR + (WATER_DEEP_CM, SHALLOW_OPACITY, DEEP_OPACITY, FRESNEL_OPACITY, FORD_ROUGHNESS,
       GLOSS_ROUGHNESS, CREST_COLOR_GAIN, SLOPE_SHADE_GAIN, CREST_OPACITY_GAIN)))
log("water ripple W4: RippleTex %s (sourced CC0, Art/Textures/Water/SOURCE.txt), two layers at WaterTileCm %.0f and "
    "WaterTileCm2 %.0f cm, the second at NormalStrength %.2f, both a flow map - two samples panned along FieldTex.b/a "
    "(the cell's flow in the field's axes, cm/s) at FlowTexScale %.2f and FlowTexScale2 %.2f, half a period apart and "
    "cross-faded on a sawtooth of FlowPeriodS %.1f s - drifting at StillDriftCmPerS %.0f where the water stands, "
    "masked off the dry cells, RippleGain %.2f on the pair, added to the field's own slope before the normal"
    % (RIPPLE_TEXTURE, WATER_TILE_CM, WATER_TILE_2_CM, NORMAL_STRENGTH, FLOW_TEX_SCALE, FLOW_TEX_SCALE_2,
       FLOW_PERIOD_S, STILL_DRIFT_CM_PER_S, RIPPLE_GAIN))
log("water foam W4: the largest of the shallows (FoamDepthCm %.0f), the steep surface (FoamSlope %.2f cm/cm of the "
    "field's own slope) and the fast water (FoamSpeedCmPerS %.0f), broken up by two octaves of hashed value noise at "
    "FoamNoiseCm %.0f drifting with the flow (procedural, as the plan allows); it takes the colour to FoamColor "
    "%.2f %.2f %.2f, the opacity to 1 and the roughness to FoamRoughness %.2f"
    % (FOAM_DEPTH_CM, FOAM_SLOPE, FOAM_SPEED_CM_PER_S, FOAM_NOISE_CM, FOAM_COLOR[0], FOAM_COLOR[1], FOAM_COLOR[2],
       FOAM_ROUGHNESS))
log("done")
