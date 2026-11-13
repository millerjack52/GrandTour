"""setup_look_l3.py - the Unreal assets of Look stage L3 (docs/LOOK_PLAN.md L3, docs/VEHICLE_BUILD_SYSTEM.md section 58).

Run with Art\\setup_look_l3.bat (close the editor first; it writes .uasset files and saves L_Leg03). In order:

- setup_look_l2.py, run first as it stands: M_GT_PostLook carries the L3 haze behind its Haze scalar (default 0; the one
  change L3 made to setup_look_l2.py), so a re-run of either script builds the same post material.
- M_GT_Sky (/Game/GrandTour/Materials) + MI_GT_Sky (/Game/GrandTour/Materials/Look): the painted sky UGTLookSubsystem puts
  on its transient 10 km dome. Unlit, TRANSLUCENT in the Before-DOF pass (it renders into scene colour before the post
  chain, so the band pass reads it as the sky it covers: no depth written), two-sided, Apply Fogging off. One Custom node
  on the view direction d: the horizon weight (1 - max(d.z, 0)) ^ HorizonPow between Zenith and Horizon; clouds where a
  3D value noise at CloudCell (plus RaggedAmp x a second at a fifth of it) at d + CloudOffset passes the cut that covers
  CloudCover of the upper sky (the noise's quantiles, simulated: CLOUD_CUTS); CloudLight, or CloudShade where the point
  ShadeDrop below is clear; the whole x LitX x SunRef x SkyScale. The runtime sets CloudCover, SkyScale, SunRef, LitX and
  CloudOffset every tick on a dynamic instance.
- M_GT_FoliageCard (/Game/GrandTour/Materials) + MI_GT_FoliageCard_Scrub (/Game/GrandTour/Materials/Foliage): a fresh copy
  of M_GT_Foliage every run (two-sided, its wind World Position Offset on MPC_Weather, its MF_Weather call), made Masked,
  with the InstancedStaticMeshes usage, one Custom node in front of MF_Weather: the PLACEHOLDER blade fan (or the
  CardMask texture with UseCardMask 1), three tones per blade at L6's ToneStep, L6's per-instance jitter, the normal
  lerped toward world up by UpBlend, and behind DabNormal L6's procedural dab.
- The Hide's dressing: L_Leg03 loaded, its AGTTerrainBuilder's RebuildDressing (the builder button's path) re-dresses the
  stones, rocks, posts and the new foliage from AGTTerrainDressing's C++ defaults; the level is saved. L_Proving is not
  touched.
Every number is PROPOSED and UNMEASURED except where it says it is L2's, L6's or M_GT_Foliage's. NullRHI compiles no HLSL:
the shaders compile on the next rendered run (Art\\sky_shots.bat). Log prefix SETUP_LOOK_L3.
"""
import os
import runpy

import unreal

PROJECT_DIR = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
MAT = "/Game/GrandTour/Materials"
LOOK_DEST = MAT + "/Look"
FOLIAGE_DEST = MAT + "/Foliage"
FOLIAGE = MAT + "/M_GT_Foliage"
SKY = "M_GT_Sky"
CARD = "M_GT_FoliageCard"
LEVEL = "/Game/GrandTour/Legs/L_Leg03"
WHITE = "/Engine/EngineResources/WhiteSquareTexture"
TAG = "L3:"

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(msg):
    unreal.log("SETUP_LOOK_L3 " + msg)


def log_error(msg):
    unreal.log_error("SETUP_LOOK_L3 " + msg)


# The value noise's cut against the covered share of the upper sky, CloudCover 0, 0.1 .. 1: the (1 - cover) quantile of
# noise(d / 0.333) + 0.12 x (noise(d / 0.0667) - 0.5) over the upper hemisphere, uniform in solid angle (2 million
# samples of a smoothstep value noise, the same lattice statistics as the hash below); the ends pushed past the range.
CLOUD_CUTS = (1.10, 0.747, 0.666, 0.605, 0.551, 0.500, 0.449, 0.395, 0.333, 0.252, -0.10)

SKY_NUMBERS = [
    # name, value, what (PROPOSED, UNMEASURED unless it says otherwise)
    ("HorizonPow", 3.0, "the horizon weight (1 - sin elevation) ^ this; the owner's first named set (2026-09-26; the first build 1.5)"),
    ("CloudCover", 0.1, "the covered share of the upper sky (the runtime sets the weather state's)"),
    ("CloudCell", 0.333, "the blob noise's cell, direction units: a sixth of the sky's 2-unit width"),
    ("RaggedAmp", 0.12, "the ragged edge: a second noise at a fifth of the cell, this strong"),
    ("ShadeDrop", 0.08, "the underside: a cloud pixel whose point this far below is clear sky"),
    ("LitX", 0.75, "L2's: the band pass shows a paint at X = LitX this bright (the runtime sets it)"),
    ("SunRef", 8.0 / 3.14159265, "the sun's lux / pi (the runtime sets it every tick, as for the band pass)"),
    ("SkyScale", 1.0, "the weather state's SkyScale (the runtime sets it)"),
]
SKY_COLOURS = [
    ("Zenith", (0.04, 0.10, 0.45), "linear, the references' flat cobalt; the owner's first named set (2026-09-26; the first build 0.10 0.22 0.55)"),
    ("Horizon", (0.62, 0.72, 0.86), "linear"),
    ("CloudLight", (0.92, 0.92, 0.90), "linear, the lit side of a cloud"),
    ("CloudShade", (0.70, 0.74, 0.84), "linear, a cloud's underside"),
    ("CloudOffset", (0.0, 0.0, 0.0), "the drift, direction units (the runtime advances it 0.002 a second along the wind)"),
]

NOISE_STRUCT = r"""
struct FGTNoise
{
    uint Hash(uint3 v)
    {
        v = v * 1664525u + 1013904223u;
        v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
        v ^= v >> 16u;
        v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
        return v.x ^ v.y ^ v.z;
    }
    float Rand(int3 c, uint salt)
    {
        return float(Hash(uint3(c + 65536) + uint3(salt, salt * 7u, salt * 13u)) & 0xFFFFFFu) / 16777216.0;
    }
    float Noise3(float3 p, uint salt)
    {
        float3 i = floor(p);
        float3 f = p - i;
        f = f * f * (3.0 - 2.0 * f);
        int3 c = int3(i);
        float a = lerp(Rand(c, salt), Rand(c + int3(1, 0, 0), salt), f.x);
        float b = lerp(Rand(c + int3(0, 1, 0), salt), Rand(c + int3(1, 1, 0), salt), f.x);
        float d = lerp(Rand(c + int3(0, 0, 1), salt), Rand(c + int3(1, 0, 1), salt), f.x);
        float e = lerp(Rand(c + int3(0, 1, 1), salt), Rand(c + int3(1, 1, 1), salt), f.x);
        return lerp(lerp(a, b, f.y), lerp(d, e, f.y), f.z);
    }
};
FGTNoise G;
"""

SKY_HLSL = NOISE_STRUCT + r"""
// Look stage L3 (VEHICLE_BUILD_SYSTEM 58): the painted sky on the dome. d is the view direction (the camera vector points
// from the pixel to the eye), so the gradient and the clouds follow the eye, not the dome's facets.
float3 d = -CamVec;
float dl = length(d);
d = (dl > 1e-6) ? d / dl : float3(0.0, 0.0, 1.0);
float e = max(d.z, 0.0);
float h = pow(saturate(1.0 - e), max(HorizonPow, 0.01));
float3 col = lerp(Zenith, Horizon, h);
float Cuts[11] = { %CUTS% };
float ci = saturate(CloudCover) * 10.0;
int k = min((int)floor(ci), 9);
float cut = lerp(Cuts[k], Cuts[k + 1], ci - (float)k);
float cell = max(CloudCell, 1e-3);
float3 p = d + CloudOffset;
float n = G.Noise3(p / cell, 71u) + RaggedAmp * (G.Noise3(p / (cell * 0.2), 73u) - 0.5);
if (d.z > 0.0 && n > cut)
{
    float3 q = p - float3(0.0, 0.0, ShadeDrop);
    float nq = G.Noise3(q / cell, 71u) + RaggedAmp * (G.Noise3(q / (cell * 0.2), 73u) - 0.5);
    col = (nq > cut) ? CloudLight : CloudShade;
}
return col * LitX * SunRef * SkyScale;
""".replace("%CUTS%", ", ".join("%.3f" % c for c in CLOUD_CUTS))

CARD_NUMBERS = [
    ("UseCardMask", 0.0, "0 the PLACEHOLDER blade fan, 1 the CardMask texture (R mask, G tone: the owner's card)"),
    ("Blades", 5.0, "the placeholder fan's blades"),
    ("BladeLenMin", 0.7, "a blade's length, of the card's height, at least"),
    ("BladeHalfW", 0.09, "a blade's widest half-width, of the card's width"),
    ("BladeLeanDeg", 30.0, "the outer blades' lean"),
    ("ToneStep", 0.183, "L6's (the bake's level spacing)"),
    ("ToneShare", 0.25, "the dark and the light tone's share of the blades each (25 / 50 / 25 %)"),
    ("JitterValue", 0.04, "L6's"),
    ("JitterHueDeg", 3.0, "L6's"),
    ("UpBlend", 0.7, "the normal lerped this far toward world up: a clump lights as one mass"),
    ("DabNormal", 0.0, "1 L6's procedural dab normal on the card's plane (chosen by the clump picture pair)"),
    ("DabCellCm", 55.0, "L6's (the bake's dab_length_cm)"),
    ("DabAspect", 2.0, "L6's"),
    ("DabCover", 1.3, "L6's"),
    ("DabTiltDeg", 8.0, "L6's"),
    ("DabRotDeg", 20.0, "L6's"),
    ("NormalStrength", 0.5, "M_GT_Painted's, as L6"),
    ("FadeCm", 4000.0, "L6's: the dab gone at 40 m"),
]

CARD_HLSL = NOISE_STRUCT + r"""
// Look stage L3 (VEHICLE_BUILD_SYSTEM 58): the foliage card. The card is the engine's plane stood up (local x across,
// local y up or down by the roll, -50..50 cm); p is the pixel on it in card-height units from the foot's middle.
float3 n = VNormal;
float nl = length(n);
n = (nl > 1e-4) ? n / nl : float3(0.0, 0.0, 1.0);
float wCm = max(length(AxisX), 1e-3) * 100.0;
float hCm = max(length(AxisY), 1e-3) * 100.0;
float upSign = (AxisY.z >= 0.0) ? 1.0 : -1.0;
float2 p = float2(LocalPos.x / 100.0 * wCm / hCm, LocalPos.y * upSign / 100.0 + 0.5);

// L6's per-instance jitter: the hue turned about the grey axis, then the value
float r1 = frac(InstRand * 1.0);
float r2 = frac(InstRand * 7.31 + 0.13);
float ang = radians((r1 * 2.0 - 1.0) * JitterHueDeg);
float3 ax = float3(0.57735, 0.57735, 0.57735);
float ca = cos(ang);
float sa = sin(ang);
float3 tint = Tint * ca + cross(ax, Tint) * sa + ax * dot(ax, Tint) * (1.0 - ca);
tint = saturate(max(tint, 0.0) * (1.0 + (r2 * 2.0 - 1.0) * JitterValue));

float mask = 0.0;
float tone = 0.0;
int3 inst = int3(int(InstRand * 16777216.0), 0, 0);
if (UseCardMask > 0.5)
{
    float4 t = Texture2DSample(CardTex, CardTexSampler, UV);
    mask = t.r;
    tone = (t.g < 0.33) ? -1.0 : ((t.g > 0.66) ? 1.0 : 0.0);
}
else
{
    // the PLACEHOLDER: a fan of blades from the foot, each an ellipse tapered to the top (widest a third of the way up)
    int count = clamp((int)Blades, 1, 9);
    float halfW = BladeHalfW * wCm / hCm;
    for (int b = 0; b < count; b++)
    {
        float fb = (count > 1) ? (float)b / (float)(count - 1) * 2.0 - 1.0 : 0.0;
        float lean = radians(fb * BladeLeanDeg + (G.Rand(inst + int3(0, b, 0), 11u) - 0.5) * 16.0);
        float len = lerp(BladeLenMin, 1.0, G.Rand(inst + int3(0, b, 0), 13u));
        float2 a = float2(sin(lean), cos(lean));
        float2 q = p - float2(fb * 0.06, 0.0);
        float s = dot(q, a) / len;
        float across = abs(q.x * a.y - q.y * a.x);
        float w = halfW * 2.598 * sqrt(saturate(s)) * saturate(1.0 - s);
        if (s >= 0.0 && s <= 1.0 && across < w)
        {
            mask = 1.0;
            float tr = G.Rand(inst + int3(0, b, 0), 17u);
            tone = (tr < ToneShare) ? -1.0 : ((tr > 1.0 - ToneShare) ? 1.0 : 0.0);
        }
    }
}
MaskOut = mask;
float3 col = saturate(tint * (1.0 + tone * ToneStep));

// the normal: toward world up, so a clump lights as one mass under the band pass
float3 nb = normalize(lerp(n, float3(0.0, 0.0, 1.0), saturate(UpBlend)));
float3 outN = nb;
if (DabNormal > 0.5)
{
    // L6's procedural dab (VEHICLE_BUILD_SYSTEM 57 (d)) on the card's plane, cm
    float3 Ut = normalize(AxisX);
    float3 Vt = normalize(AxisY) * upSign;
    float2 uv = float2(LocalPos.x / 100.0 * wCm, (LocalPos.y * upSign / 100.0 + 0.5) * hCm);
    float cellL = max(DabCellCm, 1.0);
    float cellW = cellL / max(DabAspect, 0.1);
    float2 qd = float2(uv.x / cellL, uv.y / cellW);
    float row = floor(qd.y);
    float best = -1.0;
    float2 tilt = float2(0.0, 0.0);
    for (int dy = -1; dy <= 1; dy++)
    {
        float ry = row + dy;
        float off = frac(ry * 0.5);
        for (int dx = -1; dx <= 1; dx++)
        {
            float cx = floor(qd.x - off) + dx;
            int3 cid = int3(int(cx), int(ry), 3);
            float h1 = G.Rand(cid, 41u);
            float h2 = G.Rand(cid, 43u);
            float h3 = G.Rand(cid, 47u);
            float h4 = G.Rand(cid, 53u);
            float h5 = G.Rand(cid, 59u);
            float h6 = G.Rand(cid, 61u);
            float2 c = float2(cx + off + 0.5 + (h1 - 0.5) * 0.7, ry + 0.5 + (h2 - 0.5) * 0.7);
            float2 dd = (qd - c) * float2(cellL, cellW);
            float aa = radians((h3 * 2.0 - 1.0) * DabRotDeg);
            float2 ee = float2(dd.x * cos(aa) + dd.y * sin(aa), -dd.x * sin(aa) + dd.y * cos(aa));
            float2 semi = 0.5 * max(DabCover, 0.1) * float2(cellL, cellW);
            float2 u2 = ee / semi;
            if (dot(u2, u2) < 1.0 && h4 > best)
            {
                best = h4;
                float tt = tan(radians(DabTiltDeg * h5));
                float phi = h6 * 6.2831853;
                tilt = tt * float2(cos(phi), sin(phi));
            }
        }
    }
    float3 dabN = normalize(nb + tilt.x * Ut + tilt.y * Vt);
    float fade = saturate(1.0 - Depth / max(FadeCm, 1.0));
    outN = normalize(lerp(nb, dabN, NormalStrength * fade));
}
NormalWS = outN;
return col;
"""


# ---- helpers (setup_look_l6.py's) ------------------------------------------------------------------------------------
def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (
        src.get_name(), out_name, dst.get_name(), in_name, [str(n) for n in mel.get_material_expression_input_names(dst)]))


def expr(m, cls, x, y, desc):
    e = mel.create_material_expression(m, cls, x, y)
    e.set_editor_property("desc", TAG + desc)
    return e


def scalar(m, name, value, x, y, group):
    e = expr(m, unreal.MaterialExpressionScalarParameter, x, y, name.lower())
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", value)
    e.set_editor_property("group", group)
    return e


def vector(m, name, rgb, x, y, group):
    e = expr(m, unreal.MaterialExpressionVectorParameter, x, y, name.lower())
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    e.set_editor_property("group", group)
    return e


def enum_value(enum_cls, *names):
    for name in names:
        if hasattr(enum_cls, name):
            return getattr(enum_cls, name)
    raise SystemExit("no %s among %s (have %s)" % (enum_cls.__name__, names, [n for n in dir(enum_cls) if n.isupper()]))


def compile_or_die(material):
    errors = [str(e) for e in mel.recompile_material(material)]
    eal.save_loaded_asset(material)
    if errors:
        for error in errors:
            log_error("compile error in %s: %s" % (material.get_name(), error))
        raise SystemExit(material.get_name() + " failed to compile")
    log("%s translated (NullRHI: the HLSL compiles on the next rendered run)" % material.get_name())


def param_node(m, cls, name):
    for e in mel.get_material_expressions(m):
        if isinstance(e, cls) and str(e.get_editor_property("parameter_name")) == name:
            return e
    return None


def custom_node(m, x, y, desc, code, wiring, outputs):
    custom = expr(m, unreal.MaterialExpressionCustom, x, y, desc)
    custom.set_editor_property("description", desc)
    custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for name, _src, _out in wiring:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        inputs.append(ci)
    custom.set_editor_property("inputs", inputs)
    extra = []
    for name, kind in outputs:
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", name)
        co.set_editor_property("output_type", kind)
        extra.append(co)
    custom.set_editor_property("additional_outputs", extra)
    custom.set_editor_property("code", code)
    for name, src, out in wiring:
        connect(src, out, custom, name)
    return custom


def make_instance(name, dest, parent, scalars=(), vectors=()):
    full = dest + "/" + name
    if eal.does_asset_exist(full):
        eal.delete_asset(full)
    inst = tools.create_asset(name, dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if inst is None:
        raise SystemExit("could not create " + full)
    mel.set_material_instance_parent(inst, parent)
    for pname, value in scalars:
        mel.set_material_instance_scalar_parameter_value(inst, pname, value)
    for pname, rgb in vectors:
        mel.set_material_instance_vector_parameter_value(inst, pname, unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    mel.update_material_instance(inst)
    eal.save_loaded_asset(inst)
    log("instance %s (parent %s)%s" % (full, parent.get_name(), "".join(
        [", %s %.3f" % s for s in scalars] + [", %s %.3f %.3f %.3f" % (v[0], v[1][0], v[1][1], v[1][2]) for v in vectors])))
    return inst


# ---- the sky ---------------------------------------------------------------------------------------------------------
def build_sky():
    full = MAT + "/" + SKY
    if eal.does_asset_exist(LOOK_DEST + "/MI_GT_Sky"):
        eal.delete_asset(LOOK_DEST + "/MI_GT_Sky")
    if eal.does_asset_exist(full):
        m = eal.load_asset(full)
        mel.delete_all_material_expressions(m)
        log("rebuilding " + full)
    else:
        m = tools.create_asset(SKY, MAT, unreal.Material, unreal.MaterialFactoryNew())
        if m is None:
            raise SystemExit("could not create " + full)
        log("created " + full)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("translucency_pass", enum_value(unreal.MaterialTranslucencyPass, "MTP_BEFORE_DOF"))
    m.set_editor_property("use_translucency_vertex_fog", False)   # "Apply Fogging": no height fog, no aerial perspective
    m.set_editor_property("apply_cloud_fogging", False)
    m.set_editor_property("is_sky", False)   # an IsSky mesh would make the real-time sky capture render it alone
    x0, y0 = -1400, -300
    wiring = []
    cam = expr(m, unreal.MaterialExpressionCameraVectorWS, x0, y0 - 150, "cameravector")
    wiring.append(("CamVec", cam, ""))
    for i, (name, value, _what) in enumerate(SKY_NUMBERS):
        wiring.append((name, scalar(m, name, float(value), x0, y0 + i * 70, "Sky"), ""))
    for i, (name, rgb, _what) in enumerate(SKY_COLOURS):
        wiring.append((name, vector(m, name, rgb, x0, y0 + (len(SKY_NUMBERS) + i) * 70 + 40, "Sky"), ""))
    custom = custom_node(m, x0 + 600, y0, "Look L3: the painted sky", SKY_HLSL, wiring, [])
    if not mel.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise SystemExit("could not connect the sky's emissive")
    one = expr(m, unreal.MaterialExpressionConstant, x0 + 600, y0 + 300, "opacity")
    one.set_editor_property("r", 1.0)
    mel.connect_material_property(one, "", unreal.MaterialProperty.MP_OPACITY)
    compile_or_die(m)
    log("%s: blend %s, shading %s, two-sided %s, pass %s, fogging %s, sky %s" % (
        SKY, m.get_editor_property("blend_mode"), m.get_editor_property("shading_model"), m.get_editor_property("two_sided"),
        m.get_editor_property("translucency_pass"), m.get_editor_property("use_translucency_vertex_fog"), m.get_editor_property("is_sky")))
    for name, value, what in SKY_NUMBERS:
        log("  %-11s %8.3f  %s" % (name, value, what))
    for name, rgb, what in SKY_COLOURS:
        log("  %-11s %.2f %.2f %.2f  %s" % (name, rgb[0], rgb[1], rgb[2], what))
    log("  cuts (CloudCover 0, 0.1 .. 1): " + ", ".join("%.3f" % c for c in CLOUD_CUTS))
    make_instance("MI_GT_Sky", LOOK_DEST, m)
    return m


# ---- the foliage card ------------------------------------------------------------------------------------------------
def build_card():
    full = MAT + "/" + CARD
    inst_full = FOLIAGE_DEST + "/MI_GT_FoliageCard_Scrub"
    if eal.does_asset_exist(inst_full):
        eal.delete_asset(inst_full)
    if eal.does_asset_exist(full):
        eal.delete_asset(full)
        if eal.does_asset_exist(full):
            raise SystemExit("could not delete the old " + full)
    if not eal.duplicate_asset(FOLIAGE, full):
        raise SystemExit("could not copy " + FOLIAGE + " to " + full + " (run setup_m1_masters.bat)")
    m = eal.load_asset(full)
    log("%s: a fresh copy of %s (%d expressions, two-sided %s)" % (full, FOLIAGE, len(mel.get_material_expressions(m)), m.get_editor_property("two_sided")))
    call = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
    if call is None or not isinstance(call, unreal.MaterialExpressionMaterialFunctionCall):
        raise SystemExit("the copy does not end in an MF_Weather call (run setup_m1_masters.bat)")
    wpo = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    base = param_node(m, unreal.MaterialExpressionVectorParameter, "BaseColor")
    if base is None:
        raise SystemExit("the copy has no BaseColor parameter")
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("opacity_mask_clip_value", 0.5)
    m.set_editor_property("two_sided", True)

    x0, y0 = -2600, 900
    wiring = []
    vnorm = expr(m, unreal.MaterialExpressionVertexNormalWS, x0, y0 - 600, "vertexnormal")
    wpos = expr(m, unreal.MaterialExpressionWorldPosition, x0 - 300, y0 - 500, "worldpos")
    lpos = expr(m, unreal.MaterialExpressionTransformPosition, x0, y0 - 500, "localpos")
    lpos.set_editor_property("transform_source_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    lpos.set_editor_property("transform_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
    connect(wpos, "", lpos, "")
    axes = []
    for i, axis in enumerate(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))):
        c = expr(m, unreal.MaterialExpressionConstant3Vector, x0 - 300, y0 - 350 + i * 100, "axis%d" % i)
        c.set_editor_property("constant", unreal.LinearColor(axis[0], axis[1], axis[2], 1.0))
        t = expr(m, unreal.MaterialExpressionTransform, x0, y0 - 350 + i * 100, "axisws%d" % i)
        t.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE)
        t.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        connect(c, "", t, "")
        axes.append(t)
    rand = expr(m, unreal.MaterialExpressionPerInstanceRandom, x0, y0 - 150, "instrand")
    uv = expr(m, unreal.MaterialExpressionTextureCoordinate, x0, y0 - 80, "uv")
    depth = expr(m, unreal.MaterialExpressionPixelDepth, x0, y0 - 20, "pixeldepth")
    tex = expr(m, unreal.MaterialExpressionTextureObjectParameter, x0, y0 + 60, "cardtex")
    tex.set_editor_property("parameter_name", "CardMask")
    white = unreal.load_asset(WHITE)
    if white is not None:
        tex.set_editor_property("texture", white)
    tex.set_editor_property("group", "Card")
    wiring += [("VNormal", vnorm, ""), ("LocalPos", lpos, ""), ("AxisX", axes[0], ""), ("AxisY", axes[1], ""),
               ("InstRand", rand, ""), ("UV", uv, ""), ("Depth", depth, ""), ("CardTex", tex, ""), ("Tint", base, "")]
    for i, (name, value, _what) in enumerate(CARD_NUMBERS):
        wiring.append((name, scalar(m, name, float(value), x0 - 400, y0 + 200 + i * 60, "Card"), ""))
    custom = custom_node(m, x0 + 500, y0, "Look L3: the foliage card", CARD_HLSL, wiring,
                         [("MaskOut", unreal.CustomMaterialOutputType.CMOT_FLOAT1), ("NormalWS", unreal.CustomMaterialOutputType.CMOT_FLOAT3)])
    connect(custom, "", call, "BaseColor")
    if not mel.connect_material_property(custom, "MaskOut", unreal.MaterialProperty.MP_OPACITY_MASK):
        raise SystemExit("could not connect the opacity mask")
    to_tangent = expr(m, unreal.MaterialExpressionTransform, x0 + 900, y0 + 200, "normalts")
    to_tangent.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    to_tangent.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    connect(custom, "NormalWS", to_tangent, "")
    if not mel.connect_material_property(to_tangent, "", unreal.MaterialProperty.MP_NORMAL):
        raise SystemExit("could not connect the Normal pin")
    zero = expr(m, unreal.MaterialExpressionConstant, x0 + 900, y0 + 350, "specular")
    zero.set_editor_property("r", 0.0)
    mel.connect_material_property(zero, "", unreal.MaterialProperty.MP_SPECULAR)
    mel.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    compile_or_die(m)
    log("%s: blend %s, clip %.2f, two-sided %s, wind WPO %s, MF_Weather %s" % (
        CARD, m.get_editor_property("blend_mode"), m.get_editor_property("opacity_mask_clip_value"), m.get_editor_property("two_sided"),
        wpo.get_name() if wpo else "NONE", call.get_name()))
    for name, value, what in CARD_NUMBERS:
        log("  %-14s %8.3f  %s" % (name, value, what))
    # The Scrub tint: the owner's first named set (2026-09-26; the first build 0.18 0.32 0.12, lighter than the grass).
    make_instance("MI_GT_FoliageCard_Scrub", FOLIAGE_DEST, m, scalars=(("Roughness", 0.9),), vectors=(("BaseColor", (0.08, 0.20, 0.06)),))
    return m


# ---- The Hide's dressing ---------------------------------------------------------------------------------------------
def redress():
    if not les.load_level(LEVEL):
        raise SystemExit("could not load " + LEVEL)
    builder = None
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if isinstance(actor, unreal.GTTerrainBuilder):
            builder = actor
            break
    if builder is None:
        raise SystemExit(LEVEL + " has no GTTerrainBuilder (run setup_m6_hide.bat)")
    count = builder.rebuild_dressing()
    dressing = builder.get_editor_property("dressing")
    if dressing is None or count <= 0:
        raise SystemExit("the dressing did not rebuild: " + str(builder.get_editor_property("last_message")))
    log("%s re-dressed by the builder: %d instances; %s" % (LEVEL, count, dressing.get_editor_property("last_message")))
    for comp_name, path_name in (("stones", "stone_material_path"), ("rocks", "rock_material_path"), ("posts", "post_material_path"),
                                 ("foliage", "foliage_material_path")):
        comp = dressing.get_editor_property(comp_name)
        mat = comp.get_material(0) if comp is not None else None
        log("  %s: %d instance(s), material %s (path %s)" % (comp_name, comp.get_instance_count() if comp else -1,
            mat.get_path_name() if mat else None, dressing.get_editor_property(path_name)))
    foliage = dressing.get_editor_property("foliage")
    if foliage is None or foliage.get_instance_count() <= 0:
        raise SystemExit("no foliage placed")
    mat = foliage.get_material(0)
    if mat is None or "MI_GT_FoliageCard_" not in mat.get_name():
        raise SystemExit("the foliage does not wear its card instance")
    if not les.save_current_level():
        raise SystemExit("could not save " + LEVEL)
    log("saved " + LEVEL)


def run():
    l2 = os.path.join(PROJECT_DIR, "Art", "Unreal", "setup_look_l2.py")
    log("running " + l2 + " first (M_GT_PostLook with the haze)")
    runpy.run_path(l2, run_name="setup_look_l2")
    build_sky()
    build_card()
    redress()
    log("done")


run()
