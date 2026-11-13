"""D0+D1 of Docs/WorldDressingPlan.md: dressing lab map, biome paint layers,
grass types, layer-tint material with live grass, lighting rig.

REGEN-ONLY in GrandTour: it DELETES and rebuilds M_OWDressingLab and respawns
the lighting rig, so it stomps the migrated state. Do not run it by default.

RUN IN-EDITOR: py "C:/GrandTour/Art/dressing/ported/ClaudeSetupDressingLab.py" [/Game/Map/Path]
(map defaults to MAP below; the first argv entry starting with /Game/ overrides it)

Two-pass flow (script is rerunnable, run it before AND after the import):
  1st run: creates/loads the map + all assets + lighting, then reports
           "IMPORT LANDSCAPE NOW" with the exact dialog values.
  User:    in the source project this was Landscape mode -> Manage ->
           Import from File (DressingLab_Height.r16, not carried over),
           Section Size 63x63 quads, Sections/Component 2x2,
           Components 16x16, Location (0,0,0), Scale (100,100,100).
           In GrandTour the landscape comes from
           OWToolkitSetupLibrary.BuildToolkitTestLandscape instead.
  2nd run: finds the Landscape, assigns the material + the layer infos.

Then: Landscape mode -> Paint -> pick a layer and paint. Meadow/forest grass
appears live as you paint (D1 gate). Type layers (OW_ForestBeech/Birch/Fir/
Oak) paint a forest TYPE: PCG_OWForest spawns that species there, and brush
opacity sets tree density (heavy above 0.85 weight, dense 0.55-0.85, sparse
0.15-0.55). OW_ForestOak is pure ANGRY MESH pack oaks (pack stumps/logs, no
fir deadfall). New layers need their layer infos created once in the Paint
panel (Weight-Blended), same as the original four.

GrandTour port: 13 layers. The source's four extra bed/wet layers and their
material resolve were removed, so a regeneration can never re-add them.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback

import unreal


# Map this script opens (or creates). Override: the first argv entry that
# starts with /Game/.
MAP = "/Game/GrandTour/Test/L_OWToolkitTest"
for _arg in getattr(sys, "argv", [])[1:]:
    if _arg.startswith("/Game/"):
        MAP = _arg
        break
MAP_NAME = MAP.rsplit("/", 1)[-1]
ASSET_DIR = "/Game/OWGame/Dev/DressingLab"
PREFIX = "DRESSLAB_"

# D2.5: OW_Forest = mixed forest (grove logic); the three OW_Forest<Species>
# layers are paint-a-TYPE layers consumed by PCG_OWForest species streams.
# All weight-blended, so painting a type pushes OW_Forest down in place -
# no double-spawn at full strength; partial blends read as transitions.
LAYERS = ["OW_Meadow", "OW_MeadowLush", "OW_MeadowDry",
          "OW_Forest", "OW_ForestBeech", "OW_ForestBirch",
          "OW_ForestFir", "OW_ForestOak", "OW_Scree",
          # RD2 (RoadDressingRoundPlan): dirt verge painted along roads -
          # NO grass-type rows on purpose (suppresses carpet at the road)
          # and its tint feeds the RVT, shading verge grass bases + dabs
          # toward dirt.
          "OW_RoadVerge", "OW_Bare",
          # RC-A alpine round (user 2026-07-30): high-altitude biomes.
          # OW_Alpine = hardy rocky meadow; OW_Snow = snowfield, NO grass
          # pins by design (weight-blend pushes grass layers down).
          "OW_Alpine", "OW_Snow"]
LAYER_TINTS = {
    "OW_Meadow":      (0.13, 0.30, 0.10),
    # MF2 meadow types: lush = diorama/hero saturated green; dry = pale
    # straw scrubland (reads distinctly in the paint preview).
    "OW_MeadowLush":  (0.10, 0.28, 0.08),
    "OW_MeadowDry":   (0.30, 0.28, 0.12),
    "OW_RoadVerge":   (0.22, 0.16, 0.10),
    "OW_Forest":      (0.05, 0.15, 0.06),
    "OW_ForestBeech": (0.08, 0.16, 0.04),
    "OW_ForestBirch": (0.10, 0.19, 0.08),
    "OW_ForestFir":   (0.03, 0.12, 0.07),
    # Pack-oak forest (user 2026-07-28): pure ANGRY MESH oaks, warm olive
    # tint to read distinctly from Beech/Birch in the paint preview.
    "OW_ForestOak":   (0.14, 0.18, 0.04),
    "OW_Scree":       (0.32, 0.30, 0.28),
    "OW_Bare":        (0.42, 0.34, 0.22),
    # Alpine: cold desaturated khaki (grade ~0.87/0.87/0.6 on DryGrass);
    # Snow: near-neutral, faintly cool grade on the pack snow albedo.
    "OW_Alpine":      (0.26, 0.26, 0.18),
    "OW_Snow":        (0.30, 0.31, 0.33),
}
DONOR_LAYER_INFO = ("/Game/MWLandscapeAutoMaterial/Maps/Source/"
                    "LandscapeAutoMaterial_Example_sharedassets/RemoveFoliage_LayerInfo")
DONOR_GRASS_TYPE = "/Game/MWLandscapeAutoMaterial/Procedurals/LGT_MWAM_Grass"

# (asset name, grass pin name, density per 10m2, end cull cm, feeds-from layer)
# The three type layers reuse LGT_OWForestFloor (get-or-create dedupes the
# asset; pins must be unique) so typed forest keeps the same floor as mixed.
GRASS_TYPES = [
    ("LGT_OWMeadowGrass", "MeadowGrass", 250.0, 8000, "OW_Meadow"),
    # ALL LGT varieties are owned by ClaudeHookupMeadowPack.py (AM1 + MF2/
    # MF3: it get-or-creates and repoints every LGT below). This script only
    # wires the paint pins; densities here are creation-time fallbacks.
    ("LGT_OWMeadowFlowers", "MeadowFlowers", 25.0, 5000, "OW_Meadow"),
    # Dry-patch round (user 2026-07-29: "grass everywhere, with some
    # patches of dead/dry grass, controllable"): the standard meadow
    # carpet is split by a world-space noise mask - green carpet where
    # the mask is low, this dry pin (reusing the MF2 dry LGT) where it is
    # high. Live controls: M_OWDressingLab scalar params
    # OWDryPatchNoiseScale (patch size) + OWDryPatchAmount (coverage).
    ("LGT_OWMeadowDryGrass", "MeadowDryPatches", 100.0, 6500, "OW_Meadow"),
    # MF2 meadow types.
    ("LGT_OWMeadowLushGrass", "MeadowLushGrass", 250.0, 8000, "OW_MeadowLush"),
    ("LGT_OWMeadowLushFlowers", "MeadowLushFlowers", 25.0, 6000, "OW_MeadowLush"),
    ("LGT_OWMeadowDryGrass", "MeadowDryGrass", 100.0, 6500, "OW_MeadowDry"),
    # Mixed forest keeps the shared floor; MF3 gives each TYPE its own.
    ("LGT_OWForestFloor", "ForestFloor", 60.0, 5000, "OW_Forest"),
    ("LGT_OWFloorDeciduous", "ForestFloorBeech", 60.0, 5000, "OW_ForestBeech"),
    ("LGT_OWFloorDeciduous", "ForestFloorBirch", 60.0, 5000, "OW_ForestBirch"),
    ("LGT_OWFloorFir", "ForestFloorFir", 60.0, 5000, "OW_ForestFir"),
    ("LGT_OWFloorOak", "ForestFloorOak", 60.0, 5000, "OW_ForestOak"),
    # RC-A: hardy alpine tufts; OW_Snow deliberately has NO grass pin.
    ("LGT_OWAlpineGrass", "AlpineGrass", 60.0, 6500, "OW_Alpine"),
]

# MF3 noise masks: pins in PATCH_PINS get world-space simplex clumping
# (~20m features), pins in DRIFT_PINS get broader drifts (~33m). Meadow
# grass CARPET pins stay unmasked - patches there read as mange.
PATCH_PINS = {"ForestFloor", "ForestFloorBeech", "ForestFloorBirch",
              "ForestFloorFir", "ForestFloorOak"}
DRIFT_PINS = {"MeadowFlowers", "MeadowLushFlowers"}

REPORT_PATH = Path(__file__).with_name("ClaudeSetupDressingLabReport.json")

result = {"ok": True, "steps": {}}


def step(name):
    def decorate(func):
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": str(value)}
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            unreal.log_error(f"DRESSLAB {name}: {exc!r}")
            return None

    return decorate


@step("open_or_create_map")
def open_or_create_map():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world and world.get_name() == MAP_NAME:
        return "already open"
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    else:
        world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
        if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
            raise RuntimeError(f"could not save new map at {MAP}")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_name() != MAP_NAME:
        raise RuntimeError(f"map open failed, current world: {world}")
    return MAP


# NOTE (paid 2026-07-27): LandscapeLayerInfoObject.LayerName is READ-ONLY via
# python, so layer infos CANNOT be authored by script. The supported flow is
# the Paint panel: Target Layers > "Create Layers From Assigned Materials",
# then per-layer "Create Layer Info" (Weight-Blended) with Default Layer Asset
# Path pointed at ASSET_DIR. This script therefore only reports their state.
@step("layer_infos_check")
def layer_infos_check():
    found = [f"{ASSET_DIR}/{a}" for a in
             unreal.EditorAssetLibrary.list_assets(ASSET_DIR, recursive=False)
             if "LayerInfo" in a or a.startswith("LI_")]
    return found or "none yet - create via Paint panel (see NOTE above)"


@step("grass_types")
def grass_types():
    made = []
    for asset_name, _pin, density, end_cull, _layer in GRASS_TYPES:
        dest = f"{ASSET_DIR}/{asset_name}"
        if unreal.EditorAssetLibrary.does_asset_exist(dest):
            # AM1 (Docs/MeadowPackIntegrationPlan.md, 2026-07-28): existing
            # LGT varieties are owned by ClaudeHookupMeadowPack.py (pack
            # meshes, PER-VARIETY densities). Reruns here must not stomp
            # them back to this table's uniform tuning - the GRASS_TYPES
            # density/cull values below are creation-time fallbacks only.
            made.append(f"{dest} (exists - varieties owned by "
                        "ClaudeHookupMeadowPack.py, untouched)")
            continue
        if unreal.EditorAssetLibrary.duplicate_asset(DONOR_GRASS_TYPE, dest) is None:
            raise RuntimeError(f"duplicate_asset failed for {dest}")
        lgt = unreal.load_asset(dest)
        varieties = lgt.get_editor_property("grass_varieties")
        tuned = []
        for gv in varieties:
            # Per-variety perf policy (D4 table): density knob, hard cull,
            # never shadows. Per-platform structs: set the 'default' field.
            for prop, val in (("grass_density", float(density)),
                              ("start_cull_distance", int(end_cull * 0.75)),
                              ("end_cull_distance", int(end_cull))):
                pp = gv.get_editor_property(prop)
                pp.set_editor_property("default", val)
                gv.set_editor_property(prop, pp)
            gv.set_editor_property("cast_dynamic_shadow", False)
            tuned.append(gv)
        lgt.set_editor_property("grass_varieties", tuned)
        lgt.modify()
        unreal.EditorAssetLibrary.save_loaded_asset(lgt)
        made.append(f"{dest} ({len(tuned)} varieties)")
    return made


@step("lab_material")
def lab_material():
    mat_path = f"{ASSET_DIR}/M_OWDressingLab"
    if unreal.EditorAssetLibrary.does_asset_exist(mat_path):
        if not unreal.EditorAssetLibrary.delete_asset(mat_path):
            raise RuntimeError("could not delete old lab material - close its tab")
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset("M_OWDressingLab", ASSET_DIR, unreal.Material,
                             unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary

    # Most wiring in this script discards the connect result. Material
    # CONNECTIONS cannot be read back from python (FExpressionInput members are
    # protected - docs/landscape_migration/pitfalls_from_source.md), but
    # connect_material_expressions DOES return truthfully
    # (MaterialEditingLibrary.cpp:938), so the grass kill wiring is gated on
    # it. A silently-unconnected mask would read exactly like a working one
    # until grass survived on a road verge.
    def conn(src, src_out, dst, dst_in):
        if not mel.connect_material_expressions(src, src_out, dst, dst_in):
            raise RuntimeError(
                f"connect failed: {src.get_name()}.{src_out or '<out0>'} -> "
                f"{dst.get_name()}.{dst_in or '<in0>'}")
        return dst

    # GT round (user 2026-07-30): pack Landscape ground TEXTURES replace
    # the flat tints (recipe decoded from M_Landscape_MeadowEnvironment_01
    # T3D + MI dump, done in the source project): UV = WorldPosition.xy /
    # 5000 * UVScale; demo grass tiles at UV 6 (~8.3m), mud UV 2, cliffs
    # UV 1. The texture carries the color; LAYER_TINTS become hue GRADES
    # (x GRADE_GAIN, chosen so the meadow tint ~= neutral - forest floors
    # stay proportionally darker). Live knobs: OWGroundUVScale (global
    # tile density) and OWGroundTexBlend (0 = old flat tints, 1 =
    # textured; A/B slider). Vendor textures referenced only.
    pack_ls = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Landscape"
    wp = mel.create_material_expression(
        mat, unreal.MaterialExpressionWorldPosition, -1980, -300)
    mask_xy = mel.create_material_expression(
        mat, unreal.MaterialExpressionComponentMask, -1860, -300)
    mask_xy.set_editor_property("r", True)
    mask_xy.set_editor_property("g", True)
    mask_xy.set_editor_property("b", False)
    mask_xy.set_editor_property("a", False)
    mel.connect_material_expressions(wp, "", mask_xy, "")
    div = mel.create_material_expression(
        mat, unreal.MaterialExpressionDivide, -1740, -300)
    div.set_editor_property("const_b", 5000.0)
    mel.connect_material_expressions(mask_xy, "", div, "A")
    uv_scale = mel.create_material_expression(
        mat, unreal.MaterialExpressionScalarParameter, -1740, -160)
    uv_scale.set_editor_property("parameter_name", "OWGroundUVScale")
    uv_scale.set_editor_property("default_value", 6.0)
    uv_base = mel.create_material_expression(
        mat, unreal.MaterialExpressionMultiply, -1620, -300)
    mel.connect_material_expressions(div, "", uv_base, "A")
    mel.connect_material_expressions(uv_scale, "", uv_base, "B")

    # texture key -> (albedo path, UV factor relative to the grass scale)
    ground_tex = {
        "Grass":    (f"{pack_ls}/T_Landscape_Grass_01_A", 1.0),
        "DryGrass": (f"{pack_ls}/T_Landscape_DryGrass_01_A", 1.0),
        "Cliffs":   (f"{pack_ls}/T_Landscape_Cliffs_01_A", 1.0 / 6.0),
        "Mud":      (f"{pack_ls}/T_Landscape_Mud_01_A", 2.0 / 6.0),
        "Snow":     (f"{pack_ls}/T_Landscape_Snow_01_A", 4.0 / 6.0),
    }
    layer_ground = {
        "OW_MeadowDry": "DryGrass",
        "OW_Scree": "Cliffs",
        "OW_RoadVerge": "Mud",
        "OW_Bare": "Mud",
        "OW_Alpine": "DryGrass",
        "OW_Snow": "Snow",
    }  # every other layer samples Grass
    tex_samples = {}
    for ti, (key, (tex_path, factor)) in enumerate(ground_tex.items()):
        uv_node = uv_base
        if factor != 1.0:
            fmul = mel.create_material_expression(
                mat, unreal.MaterialExpressionMultiply, -1500, -300 + ti * 120)
            fmul.set_editor_property("const_b", float(factor))
            mel.connect_material_expressions(uv_base, "", fmul, "A")
            uv_node = fmul
        tex = unreal.load_asset(tex_path)
        if tex is None:
            raise RuntimeError(f"ground texture failed to load: {tex_path}")
        ts = mel.create_material_expression(
            mat, unreal.MaterialExpressionTextureSample, -1380, -300 + ti * 160)
        ts.set_editor_property("texture", tex)
        mel.connect_material_expressions(uv_node, "", ts, "UVs")
        tex_samples[key] = ts
    tex_blend = mel.create_material_expression(
        mat, unreal.MaterialExpressionScalarParameter, -1380, 400)
    tex_blend.set_editor_property("parameter_name", "OWGroundTexBlend")
    tex_blend.set_editor_property("default_value", 1.0)
    GRADE_GAIN = 10.0 / 3.0  # meadow max channel 0.30 -> ~1.0 neutral

    # BaseColor = sum(layer_sample_i * lerp(flat_tint_i, tex * grade_i,
    # OWGroundTexBlend)) - fixed pins, no dynamic-pin LayerBlend needed.
    prev_add = None
    samples = {}
    wiring = {}               # report facts (asserted below + written to the report)
    for i, layer in enumerate(LAYERS):
        y = i * 260
        sample = mel.create_material_expression(
            mat, unreal.MaterialExpressionLandscapeLayerSample, -1000, y)
        sample.set_editor_property("parameter_name", layer)
        sample.set_editor_property("preview_weight", 1.0 if i == 0 else 0.0)
        samples[layer] = sample
        r, g, b = LAYER_TINTS[layer]
        tint = mel.create_material_expression(
            mat, unreal.MaterialExpressionConstant3Vector, -1000, y + 120)
        tint.set_editor_property("constant", unreal.LinearColor(r, g, b, 1.0))
        grade = mel.create_material_expression(
            mat, unreal.MaterialExpressionConstant3Vector, -1000, y + 180)
        grade.set_editor_property("constant", unreal.LinearColor(
            r * GRADE_GAIN, g * GRADE_GAIN, b * GRADE_GAIN, 1.0))
        graded_tex = mel.create_material_expression(
            mat, unreal.MaterialExpressionMultiply, -880, y + 120)
        mel.connect_material_expressions(
            tex_samples[layer_ground.get(layer, "Grass")], "", graded_tex, "A")
        mel.connect_material_expressions(grade, "", graded_tex, "B")
        ground_lerp = mel.create_material_expression(
            mat, unreal.MaterialExpressionLinearInterpolate, -790, y + 60)
        mel.connect_material_expressions(tint, "", ground_lerp, "A")
        mel.connect_material_expressions(graded_tex, "", ground_lerp, "B")
        mel.connect_material_expressions(tex_blend, "", ground_lerp, "Alpha")

        mul = mel.create_material_expression(
            mat, unreal.MaterialExpressionMultiply, -700, y)
        mel.connect_material_expressions(sample, "", mul, "A")
        mel.connect_material_expressions(ground_lerp, "", mul, "B")
        if prev_add is None:
            prev_add = mul
        else:
            add = mel.create_material_expression(
                mat, unreal.MaterialExpressionAdd, -420 + i * 40, y)
            mel.connect_material_expressions(prev_add, "", add, "A")
            mel.connect_material_expressions(mul, "", add, "B")
            prev_add = add
    # Ground DISPLAYS the RVT composite (pack-landscape architecture:
    # write tint sum into the RVT below, roads overwrite texels at higher
    # sort priority, read the composite back for BaseColor - this is what
    # makes RVT roads visible and melted-in). CRITICAL, copied from the
    # pack's working sample node (M_Landscape_MeadowEnvironment_01 T3D):
    # bEnableFeedback=FALSE - a material that writes an RVT while
    # feedback-sampling it loops and renders BLACK (paid 2026-07-28/29,
    # black-landscape incident), and MaterialType set EXPLICITLY.
    rvt_sample = mel.create_material_expression(
        mat, unreal.MaterialExpressionRuntimeVirtualTextureSample, -180, -400)
    rvt_asset = unreal.load_asset(
        "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material")
    if rvt_asset is None:
        raise RuntimeError("pack RVT_AM_01_Material failed to load")
    rvt_sample.set_editor_property("virtual_texture", rvt_asset)
    rvt_sample.set_editor_property(
        "material_type",
        unreal.RuntimeVirtualTextureMaterialType.BASE_COLOR_NORMAL_SPECULAR)
    rvt_sample.set_editor_property("enable_feedback", False)
    if rvt_sample.get_editor_property("enable_feedback"):
        raise RuntimeError("enable_feedback read-back still True")
    mel.connect_material_property(rvt_sample, "BaseColor",
                                  unreal.MaterialProperty.MP_BASE_COLOR)

    # RL0 (Docs/RoadLookRoundPlan.md): the pack landscape master wires the
    # SAME sample's Roughness (OutputIndex 2) and Normal (OutputIndex 3)
    # into its material outputs - dropping them was why RVT roads read
    # flat (mud N/R maps never displayed). Copy the pack recipe exactly
    # (M_Landscape_MeadowEnvironment_01 T3D): MipValueMode=RVTMVM_MipBias
    # fed by a live scalar param, direct Roughness/Normal display wiring,
    # and bTangentSpaceNormal=False on the MATERIAL (RVT normals are
    # world-space; T3D line 2220).
    mip_enum_used = None
    for enum_name in ("RVTMVM_MIP_BIAS", "MIP_BIAS", "RVTMVM_MIPBIAS"):
        mode = getattr(unreal.RuntimeVirtualTextureMipValueMode, enum_name, None)
        if mode is not None:
            mip_enum_used = enum_name
            rvt_sample.set_editor_property("mip_value_mode", mode)
            break
    if mip_enum_used is None:
        raise RuntimeError(
            "no MipBias entry found on RuntimeVirtualTextureMipValueMode: "
            + repr([n for n in dir(unreal.RuntimeVirtualTextureMipValueMode)
                    if not n.startswith("_")]))
    mip_bias = mel.create_material_expression(
        mat, unreal.MaterialExpressionScalarParameter, -420, -560)
    mip_bias.set_editor_property("parameter_name", "OWRVTMipBias")
    # The pack ships "RVT MipValue" = -2.0 (T3D line 1806), but on the
    # lab's 2016m full-coverage volume ANY negative bias exhausts VRAM on
    # the dev box (measured, RTX 4050: bias 0 = clean, -1 = 451MB over
    # budget, -2 = 490MB over; the warning is SCREEN-ONLY, never logged).
    # The overrun's first casualty is the biggest instance pool - the
    # meadow grass CARPET vanished while small pools (flowers) survived
    # (paid 2026-07-29). 0.0 is the only measured-clean value; sharper
    # road texels need the working-volume route (plan escalation), NOT
    # this knob.
    mip_bias.set_editor_property("default_value", 0.0)
    mel.connect_material_expressions(mip_bias, "", rvt_sample, "MipValue")
    mel.connect_material_property(rvt_sample, "Roughness",
                                  unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(rvt_sample, "Normal",
                                  unreal.MaterialProperty.MP_NORMAL)
    mat.set_editor_property("tangent_space_normal", False)
    if mat.get_editor_property("tangent_space_normal"):
        raise RuntimeError("tangent_space_normal read-back still True")

    # RL0: the 0.9 constant no longer drives the DISPLAY roughness (the
    # RVT sample does, so road R maps show); it still feeds the RVT WRITE
    # below so grass areas stay matte in the composite.
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -420, -200)
    rough.set_editor_property("r", 0.9)

    # RV1 (Docs/RVTGroundRoundPlan.md): write the same painted-tint sum
    # into the pack's RVT so pack grass blade-bases tint to the ground
    # color (M_Grass samples RVT_AM_01_Material). Additive node - the
    # normal BaseColor path above is unchanged. RL0 adds VertexNormalWS ->
    # Normal so the ground writes a valid flat world-space normal and
    # road normal maps overwrite it in the composite.
    rvt_out = mel.create_material_expression(
        mat, unreal.MaterialExpressionRuntimeVirtualTextureOutput, 300, 900)
    mel.connect_material_expressions(prev_add, "", rvt_out, "BaseColor")
    mel.connect_material_expressions(rough, "", rvt_out, "Roughness")
    vtx_normal = mel.create_material_expression(
        mat, unreal.MaterialExpressionVertexNormalWS, 100, 1000)
    mel.connect_material_expressions(vtx_normal, "", rvt_out, "Normal")

    # MF3: two world-space simplex noise chains multiply selected grass
    # pins so forest floors clump and flowers drift (references read as
    # patches, not carpet). Noise Scale property stays 1.0; the feature
    # size is the live scalar param multiplying world position (0.0005 ->
    # ~20m patches, 0.0003 -> ~33m drifts). Power sharpens the mask.
    def noise_chain(param_name, default_scale, exponent, y):
        wpos = mel.create_material_expression(
            mat, unreal.MaterialExpressionWorldPosition, -1000, y)
        scale = mel.create_material_expression(
            mat, unreal.MaterialExpressionScalarParameter, -1000, y + 140)
        scale.set_editor_property("parameter_name", param_name)
        scale.set_editor_property("default_value", default_scale)
        pos_mul = mel.create_material_expression(
            mat, unreal.MaterialExpressionMultiply, -820, y)
        mel.connect_material_expressions(wpos, "", pos_mul, "A")
        mel.connect_material_expressions(scale, "", pos_mul, "B")
        noise = mel.create_material_expression(
            mat, unreal.MaterialExpressionNoise, -660, y)
        noise.set_editor_property("scale", 1.0)
        noise.set_editor_property("output_min", 0.0)
        noise.set_editor_property("output_max", 1.0)
        noise.set_editor_property("levels", 2)
        noise.set_editor_property("turbulence", False)
        mel.connect_material_expressions(pos_mul, "", noise, "Position")
        power = mel.create_material_expression(
            mat, unreal.MaterialExpressionPower, -480, y)
        power.set_editor_property("const_exponent", exponent)
        mel.connect_material_expressions(noise, "", power, "Base")
        return power

    patch_mask = noise_chain("OWPatchNoiseScale", 0.0005, 2.0, 1400)
    drift_mask = noise_chain("OWDriftNoiseScale", 0.0003, 2.5, 1700)

    # Dry-patch mask (user 2026-07-29): m = saturate(noise^2 * 2*Amount).
    # OWDryPatchAmount 0 = solid green carpet, 0.5 = powered noise as-is,
    # 1.0 = saturated dry patches. Green carpet gets (1 - m) so the two
    # carpets tile the meadow instead of stacking.
    dry_noise = noise_chain("OWDryPatchNoiseScale", 0.0004, 2.0, 2000)
    dry_amount = mel.create_material_expression(
        mat, unreal.MaterialExpressionScalarParameter, -480, 2160)
    dry_amount.set_editor_property("parameter_name", "OWDryPatchAmount")
    dry_amount.set_editor_property("default_value", 0.35)
    dry_x2 = mel.create_material_expression(
        mat, unreal.MaterialExpressionMultiply, -340, 2160)
    two = mel.create_material_expression(
        mat, unreal.MaterialExpressionConstant, -480, 2280)
    two.set_editor_property("r", 2.0)
    mel.connect_material_expressions(dry_amount, "", dry_x2, "A")
    mel.connect_material_expressions(two, "", dry_x2, "B")
    dry_scaled = mel.create_material_expression(
        mat, unreal.MaterialExpressionMultiply, -220, 2000)
    mel.connect_material_expressions(dry_noise, "", dry_scaled, "A")
    mel.connect_material_expressions(dry_x2, "", dry_scaled, "B")
    dry_mask = mel.create_material_expression(
        mat, unreal.MaterialExpressionSaturate, -100, 2000)
    mel.connect_material_expressions(dry_scaled, "", dry_mask, "")
    green_mask = mel.create_material_expression(
        mat, unreal.MaterialExpressionOneMinus, -100, 2120)
    mel.connect_material_expressions(dry_mask, "", green_mask, "")

    # D1: live grass wired to painted weights (MF3: masked pins multiply
    # the painted weight by their noise chain first).
    grass_out = mel.create_material_expression(
        mat, unreal.MaterialExpressionLandscapeGrassOutput, -100, 900)
    entries = []
    for asset_name, pin, _d, _c, layer in GRASS_TYPES:
        lgt = unreal.load_asset(f"{ASSET_DIR}/{asset_name}")
        # Paid 2026-07-29 (vanished-carpet incident): a silent None here
        # leaves the pin wired to NULL and that grass type simply never
        # spawns again after a rebuild. Fail loudly instead.
        if lgt is None:
            raise RuntimeError(f"grass type failed to load: {asset_name}")
        gi = unreal.GrassInput()
        gi.set_editor_property("name", pin)
        gi.set_editor_property("grass_type", lgt)
        entries.append(gi)
    grass_out.set_editor_property("grass_types", entries)
    # Road kill-switch (PAID 2026-07-30, five failed suppression routes):
    # grass pins read RAW layer weights (LandscapeLayerSample), and only
    # the interactive paint brush normalizes sibling layers down - every
    # programmatic verge-paint route (commandlet SetAlphaData, even the
    # engine's own EditorApplySpline) writes verge=255 while OW_Meadow/
    # OW_ForestOak stay 255 underneath, so "paint the verge" silently
    # never suppressed anything. Multiply EVERY grass pin by
    # (1 - OW_RoadVerge) so verge weight kills grass DIRECTLY, no
    # normalization semantics involved.
    kill_mask = mel.create_material_expression(
        mat, unreal.MaterialExpressionOneMinus, -400, 660)
    conn(samples["OW_RoadVerge"], "", kill_mask, "")
    wiring["grass_kill_terms"] = ["OW_RoadVerge"]

    killed_pins = []
    PIN_MASKS = {pin: patch_mask for pin in PATCH_PINS}
    PIN_MASKS.update({pin: drift_mask for pin in DRIFT_PINS})
    PIN_MASKS["MeadowGrass"] = green_mask
    PIN_MASKS["MeadowDryPatches"] = dry_mask
    for i, (asset_name, pin, _d, _c, layer) in enumerate(GRASS_TYPES):
        mask = PIN_MASKS.get(pin)
        weight_expr = samples[layer]
        if mask is not None:
            pin_mul = mel.create_material_expression(
                mat, unreal.MaterialExpressionMultiply, -260, 900 + i * 120)
            mel.connect_material_expressions(weight_expr, "", pin_mul, "A")
            mel.connect_material_expressions(mask, "", pin_mul, "B")
            weight_expr = pin_mul
        kill_mul = mel.create_material_expression(
            mat, unreal.MaterialExpressionMultiply, -180, 900 + i * 120)
        mel.connect_material_expressions(weight_expr, "", kill_mul, "A")
        conn(kill_mask, "", kill_mul, "B")
        conn(kill_mul, "", grass_out, pin)
        killed_pins.append(pin)

    # --- report facts + assertions ----------------------------------------
    # Connections cannot be read back from python, so the gate is: every kill
    # connect returned True (conn() raises otherwise) AND the counts below.
    wiring["layer_samples"] = len(samples)
    wiring["grass_pins_killed"] = killed_pins
    if wiring["layer_samples"] != 13:
        raise RuntimeError(
            f"expected 13 LandscapeLayerSample nodes, got "
            f"{wiring['layer_samples']}: {sorted(samples)}")
    if len(killed_pins) != len(GRASS_TYPES):
        raise RuntimeError(
            f"{len(killed_pins)} grass pins wired through the kill mask, expected "
            f"{len(GRASS_TYPES)}")
    result["material"] = wiring

    mel.recompile_material(mat)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mat):
        raise RuntimeError("save failed for lab material")
    return (f"{mat_path} (RL0: display R+N from RVT sample, mip mode enum "
            f"'{mip_enum_used}', tangent_space_normal=False, RVT write +"
            f"VertexNormalWS; {wiring['layer_samples']} layer samples, "
            f"verge kill mask x {len(killed_pins)} pins)")


@step("lighting_rig")
def lighting_rig():
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in list(actors_sub.get_all_level_actors()):
        label = a.get_actor_label()
        # Purge ONLY this script's rig. The DRESSLAB_PCG_* biome actors are
        # ClaudeSetupBiomePCG.py's - the blanket PREFIX purge deleted them on
        # the D2.5 rerun (paid 2026-07-28; rerun ClaudeSetupBiomePCG.py to
        # respawn them).
        if label.startswith(PREFIX) and not label.startswith(PREFIX + "PCG_"):
            actors_sub.destroy_actor(a)

    def spawn(cls, label, loc=unreal.Vector(0, 0, 20000)):
        a = actors_sub.spawn_actor_from_class(cls, loc)
        a.set_actor_label(PREFIX + label)
        return a

    sun = spawn(unreal.DirectionalLight, "Sun")
    sun.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-42.0, yaw=35.0), False)
    sun_c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_c.set_editor_property("intensity", 3.0)
    sun_c.set_editor_property("atmosphere_sun_light", True)

    spawn(unreal.SkyAtmosphere, "Atmosphere")
    spawn(unreal.ExponentialHeightFog, "Fog", unreal.Vector(0, 0, 0))

    sky = spawn(unreal.SkyLight, "SkyLight")
    sky_c = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky_c.set_editor_property("real_time_capture", True)  # STATIONARY no-ops
    # 8.0 user-tuned live 2026-07-28: at 1.0 shadowed faces clipped to black
    # once trees cast shadows + solid canopies raised Lumen sky occlusion
    # (exposure is locked below, so there is no adaptation to hide it).
    sky_c.set_editor_property("intensity", 8.0)

    ppv = spawn(unreal.PostProcessVolume, "Exposure", unreal.Vector(0, 0, 0))
    ppv.set_editor_property("unbound", True)
    pps = ppv.get_editor_property("settings")
    for prop, val in (("override_auto_exposure_min_brightness", True),
                      ("override_auto_exposure_max_brightness", True),
                      ("auto_exposure_min_brightness", 1.0),
                      ("auto_exposure_max_brightness", 1.0)):
        pps.set_editor_property(prop, val)
    ppv.set_editor_property("settings", pps)

    # AM3 (Docs/MeadowPackIntegrationPlan.md): ANGRY MESH global settings
    # actor drives the pack's wind/global MPCs so pack grass/bushes animate
    # in the lab. Purged+respawned with the rest of the rig (label is
    # DRESSLAB_-prefixed, not DRESSLAB_PCG_). Deliberately NOT spawning
    # BP_AG_Lumen_Settings_01 - it would fight the DRESSLAB_Exposure rig
    # (recorded as available if lighting work ever wants it).
    ag_class = unreal.EditorAssetLibrary.load_blueprint_class(
        "/Game/ANGRY_MESH/StylizedPack_Common/Blueprints/BP_AG_Global_Settings_01")
    if ag_class is None:
        raise RuntimeError("BP_AG_Global_Settings_01 failed to load - is the "
                           "ANGRY MESH pack installed at /Game/ANGRY_MESH?")
    ag = actors_sub.spawn_actor_from_class(ag_class, unreal.Vector(0, 0, 0))
    ag.set_actor_label(PREFIX + "AGSettings")
    # Disable RVT Grass = TRUE (user-approved 2026-07-29, vanished-carpet
    # incident): with the lab ground DISPLAYING the RVT composite (RL0)
    # and pack grass TINTING from the same composite, RVT grass tint
    # renders blades in exactly the ground color = a fully camouflaged,
    # invisible carpet. The respawn used to reset this toggle to the BP
    # default (False) on every rerun - bake the approved value instead.
    ag.set_editor_property("Disable RVT Grass", True)
    if not ag.get_editor_property("Disable RVT Grass"):
        raise RuntimeError("Disable RVT Grass read-back still False")
    return ("sun/atmosphere/fog/skylight/exposure/AGSettings spawned "
            "(Disable RVT Grass baked TRUE)")


@step("landscape_hookup")
def landscape_hookup():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    landscapes = [a for a in actors if isinstance(a, unreal.LandscapeProxy)]
    if not landscapes:
        return ("NO LANDSCAPE YET - build one (GrandTour: "
                "OWToolkitSetupLibrary.BuildToolkitTestLandscape, or Landscape "
                "mode > Manage > Import from File). Then RERUN this script.")
    mat = unreal.load_asset(f"{ASSET_DIR}/M_OWDressingLab")
    # RV0: the landscape draws into the pack's RVTs (vendor assets,
    # referenced only). Volumes come from ClaudeSetupRVTVolumes.py.
    rvts = [unreal.load_asset(p) for p in (
        "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material",
        "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Height")]
    if any(r is None for r in rvts):
        raise RuntimeError("pack RVT assets failed to load")
    assigned = []
    for ls in landscapes:
        ls.modify()
        ls.set_editor_property("landscape_material", mat)
        ls.set_editor_property("runtime_virtual_textures", rvts)
        got = ls.get_editor_property("runtime_virtual_textures")
        if len(got) != 2:
            raise RuntimeError(f"runtime_virtual_textures read-back: {got}")
        assigned.append(f"{ls.get_actor_label()}: material + 2 RVTs assigned; "
                        "layer infos are Paint-panel work (see layer_infos_check NOTE)")
    return assigned


@step("save_all")
def save_all():
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return "saved"


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log("DRESSLAB setup pass complete - check the landscape_hookup step value")
