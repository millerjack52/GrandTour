"""setup_look_l6.py - the Unreal assets of Look stage L6 (docs/LOOK_PLAN.md L6, docs/VEHICLE_BUILD_SYSTEM.md section 57).

Run with Art\\setup_look_l6.bat (close the editor first; it writes .uasset files and saves L_Leg03). It builds:

- M_GT_Painterly (/Game/GrandTour/Materials): a fresh copy of M_GT_Environment every run (as setup_m6_hide.py copies it for
  the landscape), so the weather still wets it and its plain graph is M_GT_Environment's own: the BaseColor / Roughness
  parameters through MF_Weather (Porosity, CanPool) and the track-paint normal and WPO behind TrackStrength. One Custom node
  (PAINT_HLSL) is put between the parameters and MF_Weather and in front of the Normal pin; its three results meet the plain
  values in lerps on the `Surface` scalar (1 by default; UGTLookSubsystem sets it on a dynamic instance of every slot that
  wears this material from gt.Look.Surface), so Surface 0 hands MF_Weather and the Normal pin exactly the plain values, and
  the node itself returns at once on 0. Per pixel, from the mesh alone (no UV, no bake):
  (a) local colour: the instance's BaseColor, jittered per instance, posterised to three tones of value by a 3D world noise
      at ToneScaleCm - the bake's levels: tint x (1 - ToneStep), tint, and tint 0.175 of the way to the wear colour;
  (b) brush grain: stroke-shaped noise on the dominant world plane, GrainTileCm along x GrainTileCm / GrainStretch across,
      the noise's GrainCut tails light and dark: albedo x (1 +- GrainAlbedo), roughness -+ GrainRough;
  (c) edge wear from the mesh's local bounds (MeshHalfCm, a box, or the cylinder's rims with EdgeRound 1): within
      max(WearWidthCm, WearMinPx pixels) of an edge, broken by WearBreakup, the bake's wear tone (WearTint of the way to
      WearColour). The position, the normal and the axes are in "Instance & Particle Space": on a HISM "Local Space" is
      the component's (measured 2026-09-25: every face wore the wear tone), and the pixel footprint takes the View
      Property node's Tan(0.5 * Field Of View), so WearMinPx holds at any field of view;
  (d) the painted-dab normal: DabTile 0 the procedural dab (an oriented ellipse per cell of a DabCellCm x DabCellCm /
      DabAspect brick grid, each a flat facet tilted up to DabTiltDeg), DabTile 1 the baked tile T_GT_DabTile_N at
      DabTileCm, both at NormalStrength (M_GT_Painted's 0.5), faded to nothing at FadeCm;
  (e) roughness floored at RoughFloor; metallic and clear coat as the plain graph (none);
  (f) PerInstanceRandom: value +- JitterValue, hue +- JitterHueDeg;
  every number PROPOSED and UNMEASURED except those marked as the bake's (Art/Blender/gt_paint_preset.json, read here);
- T_GT_DabTile_N (/Game/GrandTour/Textures/Painted) from Art/Textures/Painted/T_GT_DabTile_N.png (bash Art/make_dab_tile.sh:
  a 2 x 2 m plane through GT Paint's Bake and the owner's OW Painterly Normal Baker), TC_Normalmap, sRGB off, no green flip
  (the project's convention); the engine's flat normal if the file is missing (logged);
- MI_GT_Painterly_Stone / _Rock / _Post (/Game/GrandTour/Materials/Painterly), each copying the parameters of the plain
  instance its kind wore (MI_Env_Greybox, MI_Env_Greybox, MI_Env_Marker): BaseColor, Roughness, Porosity, CanPool,
  TrackStrength; the post's EdgeRound 1; MeshHalfCm from the engine mesh's bounds;
- The Hide's dressing: L_Leg03 loaded, its AGTTerrainBuilder's RebuildDressing (the builder button's path) re-dresses the
  stones, the ford rocks (their own Rocks component since L6) and the posts from AGTTerrainDressing's C++ default paths,
  which point at the instances above; the level is saved. L_Proving is not touched (setup_m6_proving rebuilds it).
NullRHI compiles no HLSL: the shaders compile on the next rendered run (Art\\dressing_shots.bat). Log prefix SETUP_LOOK_L6.
"""
import json
import os

import unreal

PROJECT_DIR = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
MAT = "/Game/GrandTour/Materials"
ENV = MAT + "/M_GT_Environment"
MASTER = "M_GT_Painterly"
MI_DEST = MAT + "/Painterly"
TEX_DEST = "/Game/GrandTour/Textures/Painted"
TILE_FILE = os.path.join(PROJECT_DIR, "Art", "Textures", "Painted", "T_GT_DabTile_N.png")
TILE_ASSET = "T_GT_DabTile_N"
FLAT_NORMAL = "/Engine/EngineMaterials/FlatNormal"
PRESET_FILE = os.path.join(PROJECT_DIR, "Art", "Blender", "gt_paint_preset.json")
LEVEL = "/Game/GrandTour/Legs/L_Leg03"
TAG = "L6:"

# (kind, the plain instance it wore, edge shape 0 box / 1 round, the engine mesh)
KINDS = (("Stone", MAT + "/MI_Env_Greybox", 0.0, "/Engine/BasicShapes/Cube"),
         ("Rock", MAT + "/MI_Env_Greybox", 0.0, "/Engine/BasicShapes/Cube"),
         ("Post", MAT + "/MI_Env_Marker", 1.0, "/Engine/BasicShapes/Cylinder"))
COPY_SCALARS = ("Roughness", "Porosity", "CanPool", "TrackStrength")

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(msg):
    unreal.log("SETUP_LOOK_L6 " + msg)


def log_error(msg):
    unreal.log_error("SETUP_LOOK_L6 " + msg)


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_linear(value):
    v = value.lstrip("#")
    return tuple(srgb_to_linear(int(v[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


# ---- the numbers ---------------------------------------------------------------------------------------------------
preset = json.load(open(PRESET_FILE, encoding="utf-8"))
dab = preset.get("normal", {})
TONES = float(preset["tones"])
TONE_STEP = (1.0 + preset["wear_lighten"] - (1.0 - preset["grime_strength"])) / max(TONES - 1.0, 1.0)   # the bake's level spacing, 0.183
NUMBERS = [
    # name, value, what (the bake's numbers are read from the preset; the rest are PROPOSED, UNMEASURED)
    ("Surface", 1.0, "1 painted, 0 the plain graph (UGTLookSubsystem sets it from gt.Look.Surface)"),
    ("ToneStep", TONE_STEP, "the bake's: (1 + wear_lighten - (1 - grime_strength)) / (tones - 1)"),
    ("ToneLight", preset["wear_tint"] * 0.5, "the bake's light level: wear_tint x 1/2 of the way to wear_colour"),
    ("ToneScaleCm", preset["grain_scale_m"] * 100.0, "the bake's grain_scale, as the tone patches' noise scale"),
    ("ToneCut", 0.366, "the 3D noise's 25th percentile (simulated): 25 / 50 / 25 % dark / base / light"),
    ("GrainTileCm", 60.0, "proposed: a stroke's length scale"),
    ("GrainStretch", preset["grain_stretch"], "the bake's grain_stretch: 60 cm along, 12 across"),
    ("GrainCut", 0.256, "the 2D noise's 15th percentile (simulated): 15 % light, 15 % dark strokes"),
    ("GrainAlbedo", 0.08, "proposed"),
    ("GrainRough", 0.1, "proposed"),
    ("WearWidthCm", preset["wear_width_m"] * 100.0, "the bake's wear_width"),
    ("WearMinPx", 1.5, "proposed: the wear band never thinner than this many pixels"),
    ("WearBreakup", preset["wear_breakup"], "the bake's wear_breakup"),
    ("WearTint", preset["wear_tint"], "the bake's wear_tint"),
    ("EdgeRound", 0.0, "0 a box's edges, 1 a cylinder's rims (per instance)"),
    ("DabTile", 0.0, "0 the procedural dab, 1 the baked tile"),
    ("DabCellCm", dab.get("dab_length_cm", 55.0), "the bake's dab_length_cm"),
    ("DabAspect", dab.get("aspect", 2.0), "the bake's aspect"),
    ("DabCover", 1.3, "proposed: the ellipse's size against its cell (overlap)"),
    ("DabTiltDeg", dab.get("normal_jitter", 8.0), "the bake's normal_jitter"),
    ("DabRotDeg", dab.get("rot_jitter", 20.0), "the bake's rot_jitter"),
    ("DabTileCm", 200.0, "the plane's size: the tile's world size"),
    ("NormalStrength", 0.5, "M_GT_Painted's NormalStrength"),
    ("FadeCm", 4000.0, "proposed: the dab normal gone at 40 m"),
    ("RoughFloor", 0.75, "proposed"),
    ("JitterValue", 0.04, "proposed"),
    ("JitterHueDeg", 3.0, "proposed"),
]
WEAR_COLOUR = hex_linear(preset["wear_colour"])

PAINT_HLSL = r"""
struct FGTPaint
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
    float Noise2(float2 p, uint salt)
    {
        float2 i = floor(p);
        float2 f = p - i;
        f = f * f * (3.0 - 2.0 * f);
        int3 c = int3(int2(i), 0);
        float a = lerp(Rand(c, salt), Rand(c + int3(1, 0, 0), salt), f.x);
        float b = lerp(Rand(c + int3(0, 1, 0), salt), Rand(c + int3(1, 1, 0), salt), f.x);
        return lerp(a, b, f.y);
    }
};
FGTPaint G;
float3 n = VNormal;
float nl = length(n);
n = (nl > 1e-4) ? n / nl : float3(0.0, 0.0, 1.0);
NormalWS = n;
RoughOut = Rough;
if (Surface <= 0.0)
{
    return Tint;
}

// (f) per instance: the hue turned about the grey axis, then the value
float r1 = frac(InstRand * 1.0);
float r2 = frac(InstRand * 7.31 + 0.13);
float ang = radians((r1 * 2.0 - 1.0) * JitterHueDeg);
float3 k = float3(0.57735, 0.57735, 0.57735);
float ca = cos(ang);
float sa = sin(ang);
float3 tint = Tint * ca + cross(k, Tint) * sa + k * dot(k, Tint) * (1.0 - ca);
tint = saturate(max(tint, 0.0) * (1.0 + (r2 * 2.0 - 1.0) * JitterValue));

// the dominant world plane (a hard pick: a flat face keeps one plane), its axes on the surface
float3 an = abs(n);
float2 uv;
float3 U;
float3 V;
int plane;
if (an.z >= an.x && an.z >= an.y) { uv = WorldPos.xy; U = float3(1, 0, 0); V = float3(0, 1, 0); plane = 0; }
else if (an.x >= an.y) { uv = WorldPos.yz; U = float3(0, 1, 0); V = float3(0, 0, 1); plane = 1; }
else { uv = WorldPos.xz; U = float3(1, 0, 0); V = float3(0, 0, 1); plane = 2; }
float3 Ut = U - n * dot(U, n);
Ut = (dot(Ut, Ut) > 1e-6) ? normalize(Ut) : normalize(V - n * dot(V, n));
float3 Vt = cross(n, Ut);

// (a) the three tones of value (the bake's levels), from a 3D world noise
float tn = G.Noise3(WorldPos / max(ToneScaleCm, 1.0), 11u);
float3 col = tint;
if (tn < ToneCut) { col = tint * (1.0 - ToneStep); }
else if (tn > 1.0 - ToneCut) { col = lerp(tint, WearColour, ToneLight); }

// (b) the brush grain: binary light / dark strokes along U
float2 gp = float2(uv.x / max(GrainTileCm, 1.0), uv.y * max(GrainStretch, 1.0) / max(GrainTileCm, 1.0));
float gn = G.Noise2(gp, 23u);
float stroke = (gn > 1.0 - GrainCut) ? 1.0 : ((gn < GrainCut) ? -1.0 : 0.0);
col = saturate(col * (1.0 + stroke * GrainAlbedo));
float rough = max(RoughFloor, Rough - stroke * GrainRough);

// (c) the edge wear from the mesh's local bounds, in world cm
float3 sc = float3(length(AxisX), length(AxisY), length(AxisZ));
float3 ln = LocalNormal;
float lnl = length(ln);
ln = (lnl > 1e-6) ? ln / lnl : float3(0.0, 0.0, 1.0);
float3 ap = abs(LocalPos);
float3 dist = (MeshHalfCm - ap) * sc;
float edge = 1e6;
if (EdgeRound > 0.5)
{
    edge = (abs(ln.z) > 0.5) ? (MeshHalfCm.x - length(LocalPos.xy)) * sc.x : dist.z;
}
else
{
    if (abs(ln.x) < 0.5) { edge = min(edge, dist.x); }
    if (abs(ln.y) < 0.5) { edge = min(edge, dist.y); }
    if (abs(ln.z) < 0.5) { edge = min(edge, dist.z); }
}
float cmPerPx = Depth * 2.0 * HalfFov.y / max(ViewPx.y, 1.0);
float width = max(WearWidthCm, WearMinPx * cmPerPx);
float wn = G.Noise2(uv / max(width * 3.0, 0.5), 37u);
float wear = (edge < width * (1.0 - WearBreakup * wn)) ? 1.0 : 0.0;
col = lerp(col, lerp(tint, WearColour, WearTint), wear);
rough = lerp(rough, RoughFloor, wear);

// (d) the painted-dab normal
float3 dabN = n;
if (DabTile < 0.5)
{
    float cellL = max(DabCellCm, 1.0);
    float cellW = cellL / max(DabAspect, 0.1);
    float2 q = float2(uv.x / cellL, uv.y / cellW);
    float row = floor(q.y);
    float best = -1.0;
    float2 tilt = float2(0.0, 0.0);
    for (int dy = -1; dy <= 1; dy++)
    {
        float ry = row + dy;
        float off = frac(ry * 0.5);
        for (int dx = -1; dx <= 1; dx++)
        {
            float cx = floor(q.x - off) + dx;
            int3 cid = int3(int(cx), int(ry), plane);
            float h1 = G.Rand(cid, 41u);
            float h2 = G.Rand(cid, 43u);
            float h3 = G.Rand(cid, 47u);
            float h4 = G.Rand(cid, 53u);
            float h5 = G.Rand(cid, 59u);
            float h6 = G.Rand(cid, 61u);
            float2 c = float2(cx + off + 0.5 + (h1 - 0.5) * 0.7, ry + 0.5 + (h2 - 0.5) * 0.7);
            float2 d = (q - c) * float2(cellL, cellW);
            float a = radians((h3 * 2.0 - 1.0) * DabRotDeg);
            float2 e = float2(d.x * cos(a) + d.y * sin(a), -d.x * sin(a) + d.y * cos(a));
            float2 semi = 0.5 * max(DabCover, 0.1) * float2(cellL, cellW);
            float2 u2 = e / semi;
            if (dot(u2, u2) < 1.0 && h4 > best)
            {
                best = h4;
                float t = tan(radians(DabTiltDeg * h5));
                float phi = h6 * 6.2831853;
                tilt = t * float2(cos(phi), sin(phi));
            }
        }
    }
    dabN = normalize(n + tilt.x * Ut + tilt.y * Vt);
}
else
{
    float3 tt = Texture2DSample(DabTex, DabTexSampler, uv / max(DabTileCm, 1.0)).xyz * 2.0 - 1.0;
    dabN = normalize(tt.x * Ut + tt.y * Vt + max(tt.z, 0.05) * n);
}
float fade = saturate(1.0 - Depth / max(FadeCm, 1.0));
float3 outN = lerp(n, dabN, NormalStrength * fade);
float ol = length(outN);
NormalWS = (ol > 1e-4) ? outN / ol : n;
RoughOut = saturate(rough);
return col;
"""


# ---- helpers (setup_look_l1.py's) ------------------------------------------------------------------------------------
def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    for alt in names:
        if alt != in_name and alt.lower() == in_name.lower() and mel.connect_material_expressions(src, out_name, dst, alt):
            return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


def expr(m, cls, x, y, desc):
    e = mel.create_material_expression(m, cls, x, y)
    e.set_editor_property("desc", TAG + desc)
    return e


def scalar(m, name, value, x, y):
    e = expr(m, unreal.MaterialExpressionScalarParameter, x, y, name.lower())
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", value)
    e.set_editor_property("group", "Painterly")
    return e


def vector(m, name, rgb, x, y):
    e = expr(m, unreal.MaterialExpressionVectorParameter, x, y, name.lower())
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    e.set_editor_property("group", "Painterly")
    return e


def const3(m, rgb, x, y, desc):
    e = expr(m, unreal.MaterialExpressionConstant3Vector, x, y, desc)
    e.set_editor_property("constant", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    return e


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


# ---- the dab tile ----------------------------------------------------------------------------------------------------
def import_tile():
    if not os.path.isfile(TILE_FILE):
        log("no %s (bash Art/make_dab_tile.sh makes it): DabTex keeps the engine's flat normal" % TILE_FILE)
        return eal.load_asset(FLAT_NORMAL)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", TILE_FILE)
    task.set_editor_property("destination_path", TEX_DEST)
    task.set_editor_property("destination_name", TILE_ASSET)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    full = TEX_DEST + "/" + TILE_ASSET
    tex = eal.load_asset(full)
    if tex is None:
        raise SystemExit("the dab tile did not import to " + full)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("flip_green_channel", False)
    try:
        tex.post_edit_change()
    except Exception as error:
        log("note: post_edit_change unavailable (%s)" % error)
    eal.save_asset(full, only_if_is_dirty=False)
    log("%s <- %s (%.2f MB), TC_Normalmap, sRGB off, no green flip" % (full, TILE_FILE, os.path.getsize(TILE_FILE) / 1048576.0))
    return tex


# ---- the material ----------------------------------------------------------------------------------------------------
def enum_value(enum_cls, *names):
    for name in names:
        if hasattr(enum_cls, name):
            return getattr(enum_cls, name)
    raise SystemExit("none of %s in %s" % (names, enum_cls))


def build_master(tile):
    env = eal.load_asset(ENV)
    if env is None:
        raise SystemExit("missing " + ENV + " (run setup_m1_track, setup_m1_trackpaint and setup_m1_masters first)")
    full = MAT + "/" + MASTER
    for kind, _plain, _round, _mesh in KINDS:
        mi = MI_DEST + "/MI_GT_Painterly_" + kind
        if eal.does_asset_exist(mi):
            eal.delete_asset(mi)
    if eal.does_asset_exist(full):
        eal.delete_asset(full)
        if eal.does_asset_exist(full):
            raise SystemExit("could not delete the old " + full)
    if not eal.duplicate_asset(ENV, full):
        raise SystemExit("could not copy " + ENV + " to " + full)
    m = eal.load_asset(full)
    log("%s: a fresh copy of %s (%d expressions)" % (full, ENV, len(mel.get_material_expressions(m))))

    call = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
    if call is None or not isinstance(call, unreal.MaterialExpressionMaterialFunctionCall):
        raise SystemExit("the copy does not end in an MF_Weather call (run setup_m1_masters.bat)")
    base = param_node(m, unreal.MaterialExpressionVectorParameter, "BaseColor")
    rough = param_node(m, unreal.MaterialExpressionScalarParameter, "Roughness")
    if base is None or rough is None:
        raise SystemExit("the copy has no BaseColor / Roughness parameter")
    env_normal = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_NORMAL)
    env_normal_out = str(mel.get_material_property_input_node_output_name(m, unreal.MaterialProperty.MP_NORMAL)) if env_normal else ""
    log("plain graph: BaseColor %s and Roughness %s into %s; Normal <- %s.%r" % (
        base.get_name(), rough.get_name(), call.get_name(), env_normal.get_name() if env_normal else "(none: flat)", env_normal_out))

    x0, y0 = -2600, 900
    params = {}
    for i, (name, value, _what) in enumerate(NUMBERS):
        params[name] = scalar(m, name, float(value), x0 - 400, y0 + i * 60)
    wear_colour = vector(m, "WearColour", WEAR_COLOUR, x0 - 400, y0 + len(NUMBERS) * 60)
    mesh_half = vector(m, "MeshHalfCm", (50.0, 50.0, 50.0), x0 - 400, y0 + len(NUMBERS) * 60 + 150)
    dabtex = expr(m, unreal.MaterialExpressionTextureObjectParameter, x0 - 400, y0 + len(NUMBERS) * 60 + 300, "dabtex")
    dabtex.set_editor_property("parameter_name", "DabTex")
    dabtex.set_editor_property("texture", tile)
    dabtex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    dabtex.set_editor_property("group", "Painterly")

    wpos = expr(m, unreal.MaterialExpressionWorldPosition, x0, y0 - 600, "worldpos")
    vnorm = expr(m, unreal.MaterialExpressionVertexNormalWS, x0, y0 - 500, "vertexnormal")
    lpos = expr(m, unreal.MaterialExpressionTransformPosition, x0, y0 - 400, "localpos")
    lpos.set_editor_property("transform_source_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    lpos.set_editor_property("transform_type", unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)   # a HISM's Local is the component's
    connect(wpos, "", lpos, "")
    lnorm = expr(m, unreal.MaterialExpressionTransform, x0, y0 - 300, "localnormal")
    lnorm.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    lnorm.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_INSTANCE)
    connect(vnorm, "", lnorm, "")
    axes = []
    for i, axis in enumerate(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))):
        c = const3(m, axis, x0 - 200, y0 - 200 + i * 100, "axis%d" % i)
        t = expr(m, unreal.MaterialExpressionTransform, x0, y0 - 200 + i * 100, "axisws%d" % i)
        t.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE)
        t.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        connect(c, "", t, "")
        axes.append(t)
    depth = expr(m, unreal.MaterialExpressionPixelDepth, x0, y0 + 100, "pixeldepth")
    vsize = expr(m, unreal.MaterialExpressionViewSize, x0, y0 + 150, "viewsize")
    tan_half = getattr(getattr(unreal, "MaterialExposedViewProperty", None), "MEVP_TAN_HALF_FIELD_OF_VIEW", None)
    if tan_half is not None:
        # The View Property node, Tan(0.5 * Field Of View): (horizontal, vertical).
        fov = expr(m, unreal.MaterialExpressionViewProperty, x0, y0 + 200, "tanhalffov")
        fov.set_editor_property("property", tan_half)
        fov_what = "the View Property node's Tan(0.5 * Field Of View)"
    else:
        fov = expr(m, unreal.MaterialExpressionConstant2Vector, x0, y0 + 200, "tanhalffov")
        fov.set_editor_property("r", 1.0)
        fov.set_editor_property("g", 0.5625)
        fov_what = "a constant (1, 0.5625): no TanHalfFieldOfView node on this build"
    rand = expr(m, unreal.MaterialExpressionPerInstanceRandom, x0, y0 + 250, "instrand")

    custom = expr(m, unreal.MaterialExpressionCustom, x0 + 500, y0, "paint")
    custom.set_editor_property("description", "Look L6: the runtime painterly surface")
    custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    wiring = [("WorldPos", wpos, ""), ("VNormal", vnorm, ""), ("LocalPos", lpos, ""), ("LocalNormal", lnorm, ""),
              ("AxisX", axes[0], ""), ("AxisY", axes[1], ""), ("AxisZ", axes[2], ""), ("Depth", depth, ""),
              ("ViewPx", vsize, ""), ("HalfFov", fov, ""), ("InstRand", rand, ""), ("Tint", base, ""),
              ("Rough", rough, ""), ("WearColour", wear_colour, ""), ("MeshHalfCm", mesh_half, ""), ("DabTex", dabtex, "")]
    wiring += [(name, params[name], "") for name, _v, _w in NUMBERS]
    inputs = []
    for name, _src, _out in wiring:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        inputs.append(ci)
    custom.set_editor_property("inputs", inputs)
    outputs = []
    for name, kind in (("RoughOut", unreal.CustomMaterialOutputType.CMOT_FLOAT1), ("NormalWS", unreal.CustomMaterialOutputType.CMOT_FLOAT3)):
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", name)
        co.set_editor_property("output_type", kind)
        outputs.append(co)
    custom.set_editor_property("additional_outputs", outputs)
    custom.set_editor_property("code", PAINT_HLSL)
    for name, src, out in wiring:
        connect(src, out, custom, name)

    surface = params["Surface"]
    base_mix = expr(m, unreal.MaterialExpressionLinearInterpolate, x0 + 900, y0 - 100, "basemix")
    connect(base, "", base_mix, "A")
    connect(custom, "", base_mix, "B")
    connect(surface, "", base_mix, "Alpha")
    rough_mix = expr(m, unreal.MaterialExpressionLinearInterpolate, x0 + 900, y0 + 50, "roughmix")
    connect(rough, "", rough_mix, "A")
    connect(custom, "RoughOut", rough_mix, "B")
    connect(surface, "", rough_mix, "Alpha")
    connect(base_mix, "", call, "BaseColor")
    connect(rough_mix, "", call, "Roughness")
    to_tangent = expr(m, unreal.MaterialExpressionTransform, x0 + 900, y0 + 200, "normalts")
    to_tangent.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    to_tangent.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    connect(custom, "NormalWS", to_tangent, "")
    normal_mix = expr(m, unreal.MaterialExpressionLinearInterpolate, x0 + 1200, y0 + 200, "normalmix")
    if env_normal is not None:
        connect(env_normal, env_normal_out, normal_mix, "A")
    else:
        connect(const3(m, (0.0, 0.0, 1.0), x0 + 900, y0 + 350, "flatnormal"), "", normal_mix, "A")
    connect(to_tangent, "", normal_mix, "B")
    connect(surface, "", normal_mix, "Alpha")
    if not mel.connect_material_property(normal_mix, "", unreal.MaterialProperty.MP_NORMAL):
        raise SystemExit("could not connect the Normal pin")
    mel.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    compile_or_die(m)
    log("pixel footprint from PixelDepth, ViewSize and %s; %d inputs on the Custom node" % (fov_what, len(wiring)))
    for name, value, what in NUMBERS:
        log("  %-14s %8.3f  %s" % (name, value, what))
    log("  WearColour     %s linear (the bake's wear_colour %s)" % (", ".join("%.3f" % c for c in WEAR_COLOUR), preset["wear_colour"]))
    return m


def make_instances(master):
    made = {}
    for kind, plain_path, edge_round, mesh_path in KINDS:
        plain = eal.load_asset(plain_path)
        if plain is None:
            raise SystemExit("missing " + plain_path + " (run setup_m1_track.bat)")
        name = "MI_GT_Painterly_" + kind
        full = MI_DEST + "/" + name
        inst = tools.create_asset(name, MI_DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        if inst is None:
            raise SystemExit("could not create " + full)
        mel.set_material_instance_parent(inst, master)
        colour = mel.get_material_instance_vector_parameter_value(plain, "BaseColor")
        mel.set_material_instance_vector_parameter_value(inst, "BaseColor", colour)
        copied = ["BaseColor %.3f %.3f %.3f" % (colour.r, colour.g, colour.b)]
        for pname in COPY_SCALARS:
            value = mel.get_material_instance_scalar_parameter_value(plain, pname)
            mel.set_material_instance_scalar_parameter_value(inst, pname, value)
            copied.append("%s %.3f" % (pname, value))
        mel.set_material_instance_scalar_parameter_value(inst, "EdgeRound", edge_round)
        mesh = unreal.load_asset(mesh_path)
        half = unreal.Vector(50.0, 50.0, 50.0)
        if mesh is not None:
            bounds = mesh.get_bounds()
            half = bounds.box_extent
        mel.set_material_instance_vector_parameter_value(inst, "MeshHalfCm", unreal.LinearColor(half.x, half.y, half.z, 1.0))
        mel.update_material_instance(inst)
        eal.save_loaded_asset(inst)
        made[kind] = inst
        log("%s: parent %s, from %s (%s), EdgeRound %.0f, MeshHalfCm %.1f %.1f %.1f (%s)" % (
            full, master.get_name(), plain.get_name(), ", ".join(copied), edge_round, half.x, half.y, half.z, mesh_path))
    return made


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
    for comp_name, path_name in (("stones", "stone_material_path"), ("rocks", "rock_material_path"), ("posts", "post_material_path")):
        comp = dressing.get_editor_property(comp_name)
        mat = comp.get_material(0) if comp is not None else None
        log("  %s: %d instance(s), material %s (path %s)" % (comp_name, comp.get_instance_count() if comp else -1,
            mat.get_path_name() if mat else None, dressing.get_editor_property(path_name)))
        if mat is None or "MI_GT_Painterly_" not in mat.get_name():
            raise SystemExit("the %s do not wear their painterly instance" % comp_name)
    if not les.save_current_level():
        raise SystemExit("could not save " + LEVEL)
    log("saved " + LEVEL)


def run():
    tile = import_tile()
    master = build_master(tile)
    make_instances(master)
    redress()
    log("done")


run()
