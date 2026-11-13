"""setup_look_l2.py - the Unreal assets of Look stage L2 (docs/LOOK_PLAN.md L2, docs/VEHICLE_BUILD_SYSTEM.md section 56).

Run with Art\\setup_look_l2.bat (close the editor first; it writes .uasset files). It builds two post-process materials
in /Game/GrandTour/Materials and an instance of each in /Game/GrandTour/Materials/Look:

- M_GT_PostLook (+ MI_GT_PostLook): the band pass, at Scene Color Before DOF, priority 0. Per pixel: a low-amplitude
  stroke-noise warp of the lookup (WarpPx at 1080p, strokes StrokeLenPx x StrokeWidthPx along a slowly turning
  direction, screen-anchored); the light amount = luma(SceneColor) / PreExposure / max(luma(BaseColor), BaseGuard),
  divided by SunRef (the sun's lux / pi, set every frame by UGTLookSubsystem) so 1 is a surface square to the sun;
  2 or 3 bands (Bands) with a smoothstep terminator Soft wide at T1 (and T2); recomposed as BaseColor x ShadowTint,
  MidTint = lerp(ShadowTint, LitTint, MidMix) or LitTint, times (X / the band's typical X) ^ InBand clamped 0.7-1.3
  (the light variation kept inside a band, so the painted-normal dabs can read), times LitX x SunRef (the radiance of a
  surface at X = LitX under this sun, so the exposure shows the bands and the sky alike); then the lifted blacks: Lift + (1 - Lift) x colour, written
  / Exposure (a before-tonemap post material's output is multiplied by PreExposure and shown x Exposure / PreExposure;
  measured with the calibration patches) so it shows as written whatever the exposure; the scene passes through
  / PreExposure. Custom
  stencil > 0 (the water sheets 1, the dashboard 2), the sky (SceneDepth > SkyDepthCm) and any surface whose BaseColor
  luma is under BaseGuard (nothing to recompose; the follow-up of 2026-09-24) pass through; the sky and the base-less
  pixels get the warp and the lift, the stencilled pixels neither. Translucency After DOF (the default, and M_GT_Water's,
  M_GT_MudWater's and the glass's) is composited after this pass, so the water never reaches it.
  DebugMode (gt.Look.Debug): 1 BaseColor as the GBuffer holds it (the Substrate probe), 2 the light amount in
  eight colour classes (log2 bins of x: black < 1/32, blue, cyan, green, yellow, red, magenta, white >= 2), 3 the
  exclusions (stencil 1 blue, stencil 2 magenta, sky cyan, the rest grey), 4 the pass-through picture with the exposure
  left automatic by UGTLookSubsystem, 5 as 2 in linear bins of 0.1 (black < 0.1 ... magenta 0.6-0.7, white >= 0.7);
  6 flags at the warped lookup (red BaseColor luma under BaseGuard, green sky, blue a lit scene; the follow-up's probe);
  Look stage L3 (VEHICLE_BUILD_SYSTEM 58) adds the haze behind Haze (default 0 here; UGTLookSubsystem sets it from
  gt.Look.Haze): a = saturate((depth - HazeStartCm) / (HazeEndCm - HazeStartCm)); on the displayed colour after the
  recomposition (a banded pixel, or a base-less pass-through) and before the lift, the saturation falls to
  lerp(1, HazeSat, a) of itself and HazeTint x LitX x SunRef is mixed in to HazeMix x a; the sky and stencilled pixels
  never; Haze 0 skips the block. setup_look_l3.py runs this script first, so either builds the same material;
  modes 2-5 draw three calibration patches (0.5 written x
  PreExposure / Exposure, / Exposure, raw) at the bottom left and
  an exposure bar in the top 12 rows: white where the column is under (log2(PreExposure) + 16) / 32 of the width
  (rows 0-5) and (log2(Exposure) + 16) / 32 (rows 6-11), Exposure the EyeAdaptation node's value.
- M_GT_PostKuwahara (+ MI_GT_PostKuwahara): the anisotropic Kuwahara filter (Kyprianidis 2009, polynomial sector
  weights), Before DOF, priority 10 (after the band pass: lower priorities run first). The structure tensor from
  central differences over a 5 x 5 luma window, Gaussian weighted; 8 sectors; an ellipse RadiusPx (at 1080p) x
  (Alpha + A) / Alpha along the edge; sharpness Q; Zeta the sector overlap. Stencilled pixels pass through.
Every number is PROPOSED and UNMEASURED against the owner's look; the runtime values come from UGTLookSubsystem's
weather sets (Source/GrandTour/Look/GTLookSubsystem.cpp), which set these parameters on dynamic instances every frame.
NullRHI compiles no HLSL: the materials' shaders compile on the first rendered run (a picture .bat).
Safe to re-run. Log prefix SETUP_LOOK_L2.
"""
import unreal

MAT = "/Game/GrandTour/Materials"
MI_DEST = MAT + "/Look"
LOOK = "M_GT_PostLook"
KUWA = "M_GT_PostKuwahara"

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log("SETUP_LOOK_L2 " + msg)


def log_error(msg):
    unreal.log_error("SETUP_LOOK_L2 " + msg)


# The shared helpers: a struct so the code can hold functions (a Custom node's body is one function).
HELPERS = r"""
struct FGTLook
{
    float Hash(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
    float Noise(float2 p)
    {
        float2 i = floor(p); float2 f = frac(p); f = f * f * (3.0 - 2.0 * f);
        float a = Hash(i); float b = Hash(i + float2(1, 0)); float c = Hash(i + float2(0, 1)); float d = Hash(i + float2(1, 1));
        return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y) * 2.0 - 1.0;
    }
    float4 Fetch(float2 VUV, uint Id) { return SceneTextureLookup(ClampSceneTextureUV(ViewportUVToSceneTextureUV(VUV, Id), Id), Id, false); }
    float Luma(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }
};
FGTLook G;
float2 VUV = GetViewportUV(Parameters);
float2 Pix = GetPixelPosition(Parameters);
float2 Inv = PostProcessOutput_ViewportSizeInverse;
float S1080 = max((1.0 / Inv.y) / 1080.0, 0.1);
float Stencil = G.Fetch(VUV, 25).r;
float3 Scene0 = G.Fetch(VUV, 14).rgb;
"""

LOOK_HLSL = HELPERS + r"""
float Dummy = (PPI0.r + BaseC.r + Depth0.r + Sten0.r) * 0.0;
// A post material before the tonemapper has its output multiplied by View.PreExposure (PostProcessMaterialShaders.usf)
// and the tonemapper then shows it x Exposure / PreExposure: so a colour meant to show as D is written D / Exposure
// (ToScene; measured with the calibration patches below, VEHICLE_BUILD_SYSTEM 56) and the scene, which arrives
// pre-exposed, passes through / PreExposure (FromPre).
float ToScene = 1.0 / max(Exposure, 1e-8);
float FromPre = 1.0 / max(View.PreExposure, 1e-8);
float3 Result;
float3 Mid = lerp(ShadowTint, LitTint, MidMix);
// Look stage L3 (VEHICLE_BUILD_SYSTEM 58): the haze, on a displayed colour: the saturation down to lerp(1, HazeSat, a)
// of itself, then the lit haze tint mixed in to HazeMix x a, a from the depth (none before HazeStartCm, full at HazeEndCm).
struct FGTHaze
{
    float3 Apply(float3 C, float A, float Sat, float Mix, float3 Tint)
    {
        float L = dot(C, float3(0.2126, 0.7152, 0.0722));
        C = lerp(float3(L, L, L), C, lerp(1.0, Sat, A));
        return lerp(C, Tint, Mix * A);
    }
};
FGTHaze Hz;
float3 HazeLit = HazeTint * LitX * SunRef * Exposure;
if (Stencil > 0.5)
{
    Result = Scene0 * FromPre;
    if (DebugMode > 2.5 && DebugMode < 3.5) Result = ((Stencil < 1.5) ? float3(0, 0, 1) : float3(1, 0, 1)) * ToScene;
}
else
{
    float2 Q = Pix / S1080;
    float Ang = G.Noise(Q / 180.0 + 7.1) * 3.14159265;
    float2 Dir = float2(cos(Ang), sin(Ang));
    float2 Nrm = float2(-Dir.y, Dir.x);
    float2 SQ = float2(dot(Q, Dir) / max(StrokeLenPx, 1.0), dot(Q, Nrm) / max(StrokeWidthPx, 1.0));
    float2 W = float2(G.Noise(SQ), G.Noise(SQ + float2(17.3, 5.9))) * WarpPx * S1080;
    float2 WUV = VUV + W * Inv;
    if (DebugMode > 0.5 && DebugMode < 5.5) WUV = VUV;
    float3 Scene = G.Fetch(WUV, 14).rgb;
    float3 Base = G.Fetch(WUV, 5).rgb;
    float SceneDepthCm = G.Fetch(WUV, 1).r;
    bool bSky = SceneDepthCm > SkyDepthCm;
    float X = G.Luma(Scene) / max(View.PreExposure, 1e-8) / max(G.Luma(Base), BaseGuard) / max(SunRef, 1e-6);
    // Follow-up 2026-09-24 (VEHICLE_BUILD_SYSTEM 56): a surface nearer than the sky with no BaseColor (luma under
    // BaseGuard) cannot be recomposed - BaseColor x tint is black - so it passes through unbanded like the sky. Measured:
    // 28.6 % of hide_10's far-ridge box and 3.8 % of its crest box, drawn as a black jagged strip before this line.
    bool bNoBase = G.Luma(Base) < BaseGuard;
    float HazeA = saturate((SceneDepthCm - HazeStartCm) / max(HazeEndCm - HazeStartCm, 1.0));
    if (bSky || bNoBase)
    {
        Result = Scene * FromPre + Lift * ToScene * (1.0 - saturate(G.Luma(Scene) * FromPre / ToScene));
        if (Haze > 0.5 && !bSky)
        {
            // L3: a base-less surface (the far ridge's band) takes the haze too, in displayed units, then the same lift.
            float3 Dp = Hz.Apply(Scene * FromPre / ToScene, HazeA, HazeSat, HazeMix, HazeLit);
            Result = Dp * ToScene + Lift * ToScene * (1.0 - saturate(G.Luma(Dp)));
        }
    }
    else
    {
        float H = max(Soft, 1e-4) * 0.5;
        float B1 = smoothstep(T1 - H, T1 + H, X);
        float B2 = smoothstep(T2 - H, T2 + H, X);
        float3 Tint = (Bands < 2.5) ? lerp(ShadowTint, LitTint, B1) : lerp(lerp(ShadowTint, Mid, B1), LitTint, B2);
        // InBand keeps that power of the light variation inside a band (0 = flat bands): lit X around 0.75, shadow
        // around 0.06 (both measured on the Hide and L_Proving, VEHICLE_BUILD_SYSTEM 56), the mid band between the cuts.
        float XRef = (Bands < 2.5) ? lerp(0.06, LitX, B1) : lerp(lerp(0.06, 0.5 * (T1 + T2), B1), LitX, B2);
        float Mod = clamp(pow(max(X, 1e-4) / XRef, InBand), 0.7, 1.3);
        // The recomposed colour is the radiance of a surface at X = LitX under this sun, times the tint: the exposure
        // shows it like any lit pixel, so EV100 is one brightness for the bands and the sky together.
        float3 D0 = Base * Tint * Mod * LitX * SunRef * Exposure;
        if (Haze > 0.5)
        {
            D0 = Hz.Apply(D0, HazeA, HazeSat, HazeMix, HazeLit);   // L3: after the tints, before the lift
        }
        Result = (Lift + (1.0 - Lift) * D0) * ToScene;
    }
    if (DebugMode > 0.5 && DebugMode < 1.5) Result = Base * ToScene;
    if (DebugMode > 5.5)
    {
        // The follow-up probe (2026-09-24): flags at the warped lookup - red BaseColor luma under BaseGuard, green the sky
        // by depth, blue the scene brighter than 0.05 as shown.
        Result = float3(G.Luma(Base) < BaseGuard ? 1.0 : 0.0, bSky ? 1.0 : 0.0, G.Luma(Scene) * FromPre / ToScene > 0.05 ? 1.0 : 0.0) * ToScene;
    }
    else if ((DebugMode > 1.5 && DebugMode < 2.5) || DebugMode > 4.5)
    {
        float3 Pal[8] = { float3(0, 0, 0), float3(0, 0, 1), float3(0, 1, 1), float3(0, 1, 0), float3(1, 1, 0), float3(1, 0, 0), float3(1, 0, 1), float3(1, 1, 1) };
        int K = (DebugMode > 4.5) ? (int)clamp(floor(X / 0.1), 0.0, 7.0) : (int)clamp(floor(log2(max(X, 1e-6)) + 6.0), 0.0, 7.0);
        Result = (bSky ? float3(0.5, 0.5, 0.5) : Pal[K]) * ToScene;
    }
    if (DebugMode > 2.5 && DebugMode < 3.5) Result = (bSky ? float3(0, 1, 1) : float3(0.3, 0.3, 0.3)) * ToScene;
    if (DebugMode > 3.5 && DebugMode < 4.5) Result = Scene * FromPre;
}
if (DebugMode > 1.5 && Pix.y < 12.0 * S1080)
{
    float Bar = (log2(max(View.PreExposure, 1e-12)) + 16.0) / 32.0;
    float Bar2 = (log2(max(Exposure, 1e-12)) + 16.0) / 32.0;
    Result = ((Pix.y < 6.0 * S1080 ? Pix.x * Inv.x < Bar : Pix.x * Inv.x < Bar2) ? float3(1, 1, 1) : float3(0, 0, 0)) * ToScene;
}
// Calibration patches (debug 2-4): three 40 px squares at the bottom left holding 0.5 written three ways:
// x PreExposure / Exposure, / Exposure, and raw.
if (DebugMode > 1.5 && Pix.y > (1.0 / Inv.y) - 40.0 && Pix.x < 120.0)
{
    float Wv = (Pix.x < 40.0) ? 0.5 * ToScene : ((Pix.x < 80.0) ? 0.5 / max(Exposure, 1e-8) : 0.5);
    Result = float3(Wv, Wv, Wv);
}
return Result + Dummy;
"""

KUWA_HLSL = HELPERS + r"""
float Dummy = (PPI0.r + Sten0.r) * 0.0;
float FromPre = 1.0 / max(View.PreExposure, 1e-8);
if (Stencil > 0.5 || RadiusPx <= 0.0) return Scene0 * FromPre + Dummy;
// Filter in displayed units (the input arrives pre-exposed; the output is multiplied by PreExposure and shown
// x Exposure / PreExposure, as in M_GT_PostLook), so Q means the same at any exposure.
float FromScene = max(Exposure, 1e-8) * FromPre;
float ToScene = 1.0 / max(Exposure, 1e-8);
float Lum[25];
[unroll] for (int j0 = -2; j0 <= 2; ++j0)
    [unroll] for (int i0 = -2; i0 <= 2; ++i0)
        Lum[(j0 + 2) * 5 + (i0 + 2)] = G.Luma(min(G.Fetch(VUV + float2(i0, j0) * Inv, 14).rgb * FromScene, 4.0));
float E = 0, F = 0, Gy = 0;
[unroll] for (int j1 = -1; j1 <= 1; ++j1)
    [unroll] for (int i1 = -1; i1 <= 1; ++i1)
    {
        float Gx = Lum[(j1 + 2) * 5 + (i1 + 3)] - Lum[(j1 + 2) * 5 + (i1 + 1)];
        float Gv = Lum[(j1 + 3) * 5 + (i1 + 2)] - Lum[(j1 + 1) * 5 + (i1 + 2)];
        float Wt = (i1 == 0 && j1 == 0) ? 4.0 : ((i1 == 0 || j1 == 0) ? 2.0 : 1.0);
        E += Gx * Gx * Wt; F += Gx * Gv * Wt; Gy += Gv * Gv * Wt;
    }
float Root = sqrt(max((E - Gy) * (E - Gy) + 4.0 * F * F, 0.0));
float L1 = 0.5 * (E + Gy + Root);
float L2 = 0.5 * (E + Gy - Root);
float2 T = float2(L1 - E, -F);
T = (dot(T, T) > 1e-12) ? normalize(T) : float2(0, 1);
float Phi = -atan2(T.y, T.x);
float A = (L1 + L2 > 1e-8) ? (L1 - L2) / (L1 + L2) : 0.0;
float R = RadiusPx * S1080;
float Ea = R * clamp((Alpha + A) / Alpha, 0.1, 2.0);
float Eb = R * clamp(Alpha / (Alpha + A), 0.1, 2.0);
float Cp = cos(Phi); float Sp = sin(Phi);
int MaxX = min((int)ceil(sqrt(Ea * Ea * Cp * Cp + Eb * Eb * Sp * Sp)), 12);
int MaxY = min((int)ceil(sqrt(Ea * Ea * Sp * Sp + Eb * Eb * Cp * Cp)), 12);
float Eta = (Zeta + cos(3.14159265 / 8.0)) / (sin(3.14159265 / 8.0) * sin(3.14159265 / 8.0));
float4 M[8]; float3 S[8];
[unroll] for (int k0 = 0; k0 < 8; ++k0) { M[k0] = 0; S[k0] = 0; }
[loop] for (int j = -MaxY; j <= MaxY; ++j)
{
    [loop] for (int i = -MaxX; i <= MaxX; ++i)
    {
        float2 V = float2((Cp * i - Sp * j) / Ea, (Sp * i + Cp * j) / Eb);
        float D2 = dot(V, V);
        if (D2 > 1.0) continue;
        float3 C = min(G.Fetch(VUV + float2(i, j) * Inv, 14).rgb * FromScene, 8.0);
        float Wk[8]; float Sum = 0; float Z; float Vxx; float Vyy;
        Vxx = Zeta - Eta * V.x * V.x; Vyy = Zeta - Eta * V.y * V.y;
        Z = max(0, V.y + Vxx); Wk[0] = Z * Z;
        Z = max(0, -V.x + Vyy); Wk[2] = Z * Z;
        Z = max(0, -V.y + Vxx); Wk[4] = Z * Z;
        Z = max(0, V.x + Vyy); Wk[6] = Z * Z;
        float2 V2 = 0.70710678 * float2(V.x - V.y, V.x + V.y);
        Vxx = Zeta - Eta * V2.x * V2.x; Vyy = Zeta - Eta * V2.y * V2.y;
        Z = max(0, V2.y + Vxx); Wk[1] = Z * Z;
        Z = max(0, -V2.x + Vyy); Wk[3] = Z * Z;
        Z = max(0, -V2.y + Vxx); Wk[5] = Z * Z;
        Z = max(0, V2.x + Vyy); Wk[7] = Z * Z;
        [unroll] for (int k1 = 0; k1 < 8; ++k1) Sum += Wk[k1];
        float Gw = exp(-2.0 * D2) / max(Sum, 1e-6);
        [unroll] for (int k2 = 0; k2 < 8; ++k2) { float Wg = Wk[k2] * Gw; M[k2] += float4(C * Wg, Wg); S[k2] += C * C * Wg; }
    }
}
float4 O = 0;
[unroll] for (int k3 = 0; k3 < 8; ++k3)
{
    if (M[k3].w > 1e-6)
    {
        float3 Mean = M[k3].rgb / M[k3].w;
        float3 Var = abs(S[k3] / M[k3].w - Mean * Mean);
        float Wq = 1.0 / (1.0 + pow(255.0 * (Var.r + Var.g + Var.b), 0.5 * Q));
        O += float4(Mean * Wq, Wq);
    }
}
return ((O.w > 1e-8) ? O.rgb / O.w * ToScene : Scene0 * FromPre) + Dummy;
"""

# name -> default (float or (r, g, b)); the runtime sets them all every frame from the weather set.
LOOK_PARAMS = [
    ("Bands", 3.0), ("T1", 0.3), ("T2", 0.65), ("Soft", 0.08), ("MidMix", 0.6),
    ("InBand", 0.25), ("LitTint", (1.0, 0.96, 0.88)), ("ShadowTint", (0.55, 0.62, 0.80)), ("Lift", (0.012, 0.014, 0.020)),
    ("WarpPx", 1.5), ("StrokeLenPx", 24.0), ("StrokeWidthPx", 5.0),
    ("LitX", 0.75), ("SunRef", 8.0 / 3.14159265), ("BaseGuard", 0.02), ("SkyDepthCm", 5.0e6), ("DebugMode", 0.0),
    # Look stage L3 (VEHICLE_BUILD_SYSTEM 58): the haze, off in the master (the runtime sets Haze from gt.Look.Haze, and
    # the other haze numbers from UGTLookSubsystem's own, kept equal to these). HazeEndCm 120000 and HazeMix 0.15 are the
    # owner's first named set (2026-09-26; the first build's 60000 and 0.35); still the owner's to move.
    ("Haze", 0.0), ("HazeStartCm", 6000.0), ("HazeEndCm", 120000.0), ("HazeSat", 0.5), ("HazeMix", 0.15),
    ("HazeTint", (0.70, 0.78, 0.90)),
]
KUWA_PARAMS = [("RadiusPx", 4.0), ("Q", 8.0), ("Alpha", 1.0), ("Zeta", 0.33)]


def enum_value(enum_cls, *names):
    for name in names:
        if hasattr(enum_cls, name):
            return getattr(enum_cls, name)
    raise SystemExit("no %s among %s (have %s)" % (enum_cls.__name__, names, [n for n in dir(enum_cls) if n.isupper()]))


def fresh_material(name):
    full = MAT + "/" + name
    if eal.does_asset_exist(full):
        m = eal.load_asset(full)
        mel.delete_all_material_expressions(m)
        log("rebuilding " + full)
    else:
        m = tools.create_asset(name, MAT, unreal.Material, unreal.MaterialFactoryNew())
        if m is None:
            raise SystemExit("could not create " + full)
        log("created " + full)
    return m


def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (
        src.get_name(), out_name, dst.get_name(), in_name, [str(n) for n in mel.get_material_expression_input_names(dst)]))


def build_post(name, code, params, textures, priority, exposure_pin=False):
    m = fresh_material(name)
    m.set_editor_property("material_domain", enum_value(unreal.MaterialDomain, "MD_POST_PROCESS"))
    m.set_editor_property("blendable_location", enum_value(unreal.BlendableLocation, "BL_SCENE_COLOR_BEFORE_DOF", "BL_BEFORE_DOF"))
    m.set_editor_property("blendable_priority", priority)
    m.set_editor_property("is_blendable", False)
    custom = mel.create_material_expression(m, unreal.MaterialExpressionCustom, -300, 0)
    custom.set_editor_property("description", name)
    custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for pin, _ in textures:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", pin)
        inputs.append(ci)
    if exposure_pin:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", "Exposure")
        inputs.append(ci)
    for pname, _ in params:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", pname)
        inputs.append(ci)
    custom.set_editor_property("inputs", inputs)
    custom.set_editor_property("code", code)
    y = -400
    if exposure_pin:
        eye = mel.create_material_expression(m, unreal.MaterialExpressionEyeAdaptation, -900, -520)
        connect(eye, "", custom, "Exposure")
    for pin, tex_id in textures:
        st = mel.create_material_expression(m, unreal.MaterialExpressionSceneTexture, -900, y)
        st.set_editor_property("scene_texture_id", tex_id)
        connect(st, "Color", custom, pin)
        y += 120
    for pname, default in params:
        if isinstance(default, tuple):
            e = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -700, y)
            e.set_editor_property("default_value", unreal.LinearColor(default[0], default[1], default[2], 1.0))
        else:
            e = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -700, y)
            e.set_editor_property("default_value", default)
        e.set_editor_property("parameter_name", pname)
        connect(e, "", custom, pname)
        y += 90
    mel.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    errors = [str(e) for e in mel.recompile_material(m)]
    eal.save_loaded_asset(m)
    for error in errors:
        log_error("compile error in %s: %s" % (name, error))
    log("%s built: domain %s, location %s, priority %d, %d inputs (%d parameters), %s" % (
        name, m.get_editor_property("material_domain"), m.get_editor_property("blendable_location"), priority,
        len(inputs), len(params), "errors %d" % len(errors) if errors else "no errors reported (NullRHI compiles no HLSL)"))
    return m


def build_instance(name, parent):
    full = MI_DEST + "/" + name
    if eal.does_asset_exist(full):
        inst = eal.load_asset(full)
    else:
        inst = tools.create_asset(name, MI_DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        if inst is None:
            raise SystemExit("could not create " + full)
    mel.set_material_instance_parent(inst, parent)
    eal.save_loaded_asset(inst)
    log("instance " + full)


STI = unreal.SceneTextureId
ppi0 = enum_value(STI, "PPI_POST_PROCESS_INPUT0")
look = build_post(LOOK, LOOK_HLSL, LOOK_PARAMS, [
    ("PPI0", ppi0), ("BaseC", enum_value(STI, "PPI_BASE_COLOR")), ("Depth0", enum_value(STI, "PPI_SCENE_DEPTH")),
    ("Sten0", enum_value(STI, "PPI_CUSTOM_STENCIL"))], 0, exposure_pin=True)
kuwa = build_post(KUWA, KUWA_HLSL, KUWA_PARAMS, [("PPI0", ppi0), ("Sten0", enum_value(STI, "PPI_CUSTOM_STENCIL"))], 10, exposure_pin=True)
build_instance("MI_GT_PostLook", look)
build_instance("MI_GT_PostKuwahara", kuwa)
log("DONE")
