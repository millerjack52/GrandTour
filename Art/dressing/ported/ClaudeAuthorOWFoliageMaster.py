# OW painterly foliage/trunk MASTERS (2026-07-28, agreed next session after
# the swiss-cheese fix): duplicate the vendor Kasyanik masters into /Game/OWGame
# and surgically rewire ONLY:
#   - WorldPositionOffset -> one bounded Custom-HLSL sway (replaces the whole
#     vendor WPO subgraph: SimpleGrassWind world-position phase = the distance
#     bob, and the isFluffy puff = baked into geometry since 2026-07-28).
#     Offset depends only on height-in-bounds, Time and PerInstanceRandom phase
#     (never absolute world position), is amplitude-clamped, and fades to zero
#     by camera distance IN THE MATERIAL (per-vertex - sidesteps the ISM
#     granularity failure of the descriptor 40m fence).
#   - Foliage BaseColor/SubsurfaceColor -> PerInstanceRandom hue/sat/val jitter
#     inserted after the existing "hasGradientColor" switch (pixel-side vendor
#     look otherwise untouched; jitter is 0 on non-instanced placed actors).
# Trunk and foliage get the IDENTICAL sway (same params) so canopy blobs and
# branches move coherently. Then reparent every MI under TreeMIs whose parent
# is a vendor master. Vendor originals are never edited (VENDOR RULE).
#
# Headless run (editor CLOSED - deletes/creates assets; PowerShell):
#   & 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
#     C:\GrandTour\GrandTour.uproject -run=PythonScript
#     "-Script=C:/GrandTour/Art/dressing/ported/ClaudeAuthorOWFoliageMaster.py"
#     -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"
# NullRHI does NOT compile shaders: HLSL errors only surface in a real-RHI
# session ("Failed to compile Material") - the user's editor reopen is the
# compile gate; grep their log if anything renders as the default grid.
import json
import traceback
from pathlib import Path

import unreal

REPORT_PATH = str(Path(__file__).with_name("ClaudeAuthorOWFoliageMasterReport.json"))

VENDOR_FOLIAGE = "/Game/Materials/MM_Foliage"
VENDOR_TRUNK = "/Game/Materials/MM_Trunk"
MASTER_DIR = "/Game/OWGame/Dev/DressingLab/Masters"
FOLIAGE_MASTER = MASTER_DIR + "/M_OWFoliageMaster"
TRUNK_MASTER = MASTER_DIR + "/M_OWTrunkMaster"
MI_DIR = "/Game/OWGame/Dev/DressingLab/TreeMIs"
MPC_PATH = "/Game/Materials/MaterialParameterCollection/MPC_GlobalWind"

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


# Bounded painterly sway. Inputs are pre-subtracted in the graph so no LWC
# types reach the Custom node. All locals assigned on every path (HLSL
# branch-scope doctrine); normalize guarded (coincident wind dir = up).
SWAY_HLSL = """float3 up = float3(0.0, 0.0, 1.0);
float3 wd = WindDir.xyz;
float3 dir = wd - up * dot(wd, up);
float dl = length(dir);
dir = (dl > 1e-4) ? (dir / dl) : float3(0.0, 1.0, 0.0);
float3 side = cross(up, dir);
float hf = saturate((RelPos.z + 0.5 * Bounds.z) / max(Bounds.z, 1.0));
float bend = hf * hf;
float ph = Rand * 6.28318;
float t = T * Speed;
float gust = 0.7 + 0.3 * sin(t * 0.37 + ph * 1.7);
float3 off = dir * (sin(t + ph) * gust)
           + side * (sin(t * 0.83 + ph * 2.3) * 0.35);
off *= Amp * bend * saturate(WindInt + 0.25);
off *= 1.0 - smoothstep(FadeStart, FadeEnd, length(CamRel));
float m = length(off);
off = (m > MaxOff) ? (off * (MaxOff / m)) : off;
return off;"""

# Per-instance hue/sat/val jitter (iq HSV round-trip). Rand==0 (placed,
# non-instanced actors) shifts DOWN slightly via (Rand-0.5); acceptable -
# spawned-forest instancing is the design target.
HUE_HLSL = """float3 c = max(Color.rgb, 0.0);
float mx = max(c.r, max(c.g, c.b));
float mn = min(c.r, min(c.g, c.b));
float d = mx - mn;
float h = 0.0;
if (d > 1e-5)
{
    if (mx == c.r)      h = frac(((c.g - c.b) / d) / 6.0 + 1.0);
    else if (mx == c.g) h = ((c.b - c.r) / d + 2.0) / 6.0;
    else                h = ((c.r - c.g) / d + 4.0) / 6.0;
}
float s = (mx > 1e-5) ? (d / mx) : 0.0;
float r = Rand - 0.5;
h = frac(h + r * 2.0 * HueAmt + 1.0);
s = saturate(s * (1.0 + r * 2.0 * SatAmt));
float v = mx * (1.0 + r * 2.0 * ValAmt);
float3 p = abs(frac(h + float3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
return v * lerp(float3(1.0, 1.0, 1.0), saturate(p - 1.0), s);"""


def make_custom(mat, code, desc, input_names, x, y):
    node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, x, y)
    node.set_editor_property("code", code)
    node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    node.set_editor_property("description", desc)
    inputs = []
    for n in input_names:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        inputs.append(ci)
    node.set_editor_property("inputs", inputs)
    return node


def make_scalar_param(mat, name, default, group, x, y):
    p = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
    p.set_editor_property("parameter_name", name)
    p.set_editor_property("default_value", default)
    p.set_editor_property("group", group)
    return p


@step("duplicate_masters")
def duplicate_masters():
    out = {}
    for src, dst in ((VENDOR_FOLIAGE, FOLIAGE_MASTER), (VENDOR_TRUNK, TRUNK_MASTER)):
        if eal.does_asset_exist(dst):
            if not eal.delete_asset(dst):
                raise RuntimeError("delete_asset failed for " + dst)
        dup = eal.duplicate_asset(src, dst)
        if dup is None:
            raise RuntimeError("duplicate_asset returned None for " + dst)
        out[dst] = "duplicated"
    return out


@step("wire_sway")
def wire_sway():
    mpc = eal.load_asset(MPC_PATH)
    if mpc is None:
        raise RuntimeError("MPC_GlobalWind failed to load")
    out = {}
    for path in (FOLIAGE_MASTER, TRUNK_MASTER):
        mat = eal.load_asset(path)
        if mat is None:
            raise RuntimeError("master failed to load: " + path)
        # New nodes live far below the vendor graph (Y >= 2200).
        wp = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -2200, 2200)
        obj = mel.create_material_expression(mat, unreal.MaterialExpressionObjectPositionWS, -2200, 2320)
        cam = mel.create_material_expression(mat, unreal.MaterialExpressionCameraPositionWS, -2200, 2440)
        rel = mel.create_material_expression(mat, unreal.MaterialExpressionSubtract, -1950, 2240)
        camrel = mel.create_material_expression(mat, unreal.MaterialExpressionSubtract, -1950, 2400)
        mel.connect_material_expressions(wp, "", rel, "A")
        mel.connect_material_expressions(obj, "", rel, "B")
        mel.connect_material_expressions(wp, "", camrel, "A")
        mel.connect_material_expressions(cam, "", camrel, "B")
        bounds = mel.create_material_expression(mat, unreal.MaterialExpressionObjectBounds, -1950, 2540)
        rand = mel.create_material_expression(mat, unreal.MaterialExpressionPerInstanceRandom, -1950, 2660)
        time = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1950, 2760)
        winddir = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1950, 2860)
        winddir.set_editor_property("collection", mpc)
        winddir.set_editor_property("parameter_name", "WindDirection")
        windint = mel.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, -1950, 2980)
        windint.set_editor_property("collection", mpc)
        windint.set_editor_property("parameter_name", "WindIntensity")
        amp = make_scalar_param(mat, "SwayAmplitude", 15.0, "OWSway", -1700, 2200)
        speed = make_scalar_param(mat, "SwaySpeed", 1.1, "OWSway", -1700, 2300)
        fstart = make_scalar_param(mat, "SwayFadeStart", 3500.0, "OWSway", -1700, 2400)
        fend = make_scalar_param(mat, "SwayFadeEnd", 7000.0, "OWSway", -1700, 2500)
        moff = make_scalar_param(mat, "SwayMaxOffset", 25.0, "OWSway", -1700, 2600)
        sway = make_custom(mat, SWAY_HLSL, "OW painterly sway (bounded, camera-faded)",
                           ["RelPos", "CamRel", "Bounds", "Rand", "T",
                            "WindDir", "WindInt", "Amp", "Speed",
                            "FadeStart", "FadeEnd", "MaxOff"], -1400, 2400)
        for src, pin in ((rel, "RelPos"), (camrel, "CamRel"), (bounds, "Bounds"),
                         (rand, "Rand"), (time, "T"), (winddir, "WindDir"),
                         (windint, "WindInt"), (amp, "Amp"), (speed, "Speed"),
                         (fstart, "FadeStart"), (fend, "FadeEnd"), (moff, "MaxOff")):
            if not mel.connect_material_expressions(src, "", sway, pin):
                raise RuntimeError("connect failed: {} -> {} on {}".format(pin, "sway", path))
        if not mel.connect_material_property(sway, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
            raise RuntimeError("WPO rewire failed on " + path)
        out[path] = "sway wired"
    return out


@step("wire_hue")
def wire_hue():
    mat = eal.load_asset(FOLIAGE_MASTER)
    exprs = mel.get_material_expressions(mat)
    switch = None
    sss = None
    for e in exprs:
        if isinstance(e, unreal.MaterialExpressionStaticSwitchParameter) \
                and str(e.get_editor_property("parameter_name")) == "hasGradientColor":
            switch = e
        if isinstance(e, unreal.MaterialExpressionVectorParameter) \
                and str(e.get_editor_property("parameter_name")) == "SubsurfaceColor":
            sss = e
    if switch is None or sss is None:
        raise RuntimeError("vendor nodes not found (switch={}, sss={})".format(switch, sss))
    rand = mel.create_material_expression(mat, unreal.MaterialExpressionPerInstanceRandom, -300, 2200)
    hue_amt = make_scalar_param(mat, "PerTreeHueJitter", 0.05, "OWVariation", -300, 2300)
    sat_amt = make_scalar_param(mat, "PerTreeSatJitter", 0.08, "OWVariation", -300, 2400)
    val_amt = make_scalar_param(mat, "PerTreeValJitter", 0.12, "OWVariation", -300, 2500)
    done = []
    for src, prop, y in ((switch, unreal.MaterialProperty.MP_BASE_COLOR, 2250),
                         (sss, unreal.MaterialProperty.MP_SUBSURFACE_COLOR, 2550)):
        hue = make_custom(mat, HUE_HLSL, "OW per-instance hue jitter",
                          ["Color", "Rand", "HueAmt", "SatAmt", "ValAmt"], -50, y)
        for s, pin in ((src, "Color"), (rand, "Rand"), (hue_amt, "HueAmt"),
                       (sat_amt, "SatAmt"), (val_amt, "ValAmt")):
            if not mel.connect_material_expressions(s, "", hue, pin):
                raise RuntimeError("hue connect failed: " + pin)
        if not mel.connect_material_property(hue, "", prop):
            raise RuntimeError("hue property rewire failed: " + str(prop))
        done.append(str(prop))
    return done


@step("compile_and_save")
def compile_and_save():
    out = {}
    for path in (FOLIAGE_MASTER, TRUNK_MASTER):
        mat = eal.load_asset(path)
        mel.recompile_material(mat)
        if not eal.save_loaded_asset(mat):
            raise RuntimeError("save failed: " + path)
        out[path] = str(mat.get_editor_property("blend_mode"))
    # Duplicate-of-masked stays masked; the paid trap is opaque->masked flips.
    if "MASKED" not in out[FOLIAGE_MASTER].upper():
        raise RuntimeError("foliage master lost BLEND_Masked: " + out[FOLIAGE_MASTER])
    return out


@step("reparent_mis")
def reparent_mis():
    foliage_master = eal.load_asset(FOLIAGE_MASTER)
    trunk_master = eal.load_asset(TRUNK_MASTER)
    moved = {"foliage": [], "trunk": [], "untouched": []}
    for ap in eal.list_assets(MI_DIR, recursive=False, include_folder=False):
        mi = eal.load_asset(ap)
        if not isinstance(mi, unreal.MaterialInstanceConstant):
            continue
        parent = mi.get_editor_property("parent")
        pname = parent.get_path_name() if parent else ""
        if pname.startswith(VENDOR_FOLIAGE):
            mel.set_material_instance_parent(mi, foliage_master)
            key = "foliage"
        elif pname.startswith(VENDOR_TRUNK):
            mel.set_material_instance_parent(mi, trunk_master)
            key = "trunk"
        else:
            moved["untouched"].append(mi.get_name())
            continue
        # only_if_is_dirty=False: the parent swap does NOT reliably dirty the
        # package - the default save silently skipped all 21 MIs on the first
        # run (fresh-session verify caught vendor parents still on disk).
        if not eal.save_loaded_asset(mi, only_if_is_dirty=False):
            raise RuntimeError("MI save failed: " + ap)
        moved[key].append(mi.get_name())
    if not moved["foliage"] or not moved["trunk"]:
        raise RuntimeError("reparent found no vendor-parented MIs: " + json.dumps(moved))
    return moved


@step("verify")
def verify():
    out = {}
    for path, want_customs in ((FOLIAGE_MASTER, 3), (TRUNK_MASTER, 1)):
        mat = eal.load_asset(path)
        customs = [e for e in mel.get_material_expressions(mat)
                   if isinstance(e, unreal.MaterialExpressionCustom)]
        if len(customs) != want_customs:
            raise RuntimeError("{}: {} custom nodes, wanted {}".format(
                path, len(customs), want_customs))
        amp = mel.get_material_default_scalar_parameter_value(mat, "SwayAmplitude")
        if abs(amp - 15.0) > 1e-3:
            raise RuntimeError("{}: SwayAmplitude default {} != 15".format(path, amp))
        out[path] = {"customs": len(customs), "sway_amplitude": amp}
    # Same-session parameter reads through a just-edited parent are not
    # trustworthy (stale cache); the puff-bake contract ruling belongs to
    # ClaudeVerifyOWFoliageMaster.py in a FRESH session.
    return out


try:
    duplicate_masters()
    wire_sway()
    wire_hue()
    compile_and_save()
    reparent_mis()
    verify()
finally:
    with open(REPORT_PATH, "w") as fh:
        json.dump(report, fh, indent=2)

if not report["ok"]:
    raise RuntimeError("ClaudeAuthorOWFoliageMaster failed; see report")
