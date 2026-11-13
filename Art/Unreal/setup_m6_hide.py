"""setup_m6_hide.py - The Hide (leg 3) gets real ground: a landscape material, a generated landscape, the leg on it.

Run with Art\\setup_m6_hide.bat (close the editor first; run setup_m1_track, setup_m3_weather, setup_m3_leg and
setup_m5_legs before it). M6, terrain first: shape before textures.
- M_GT_Landscape under /Game/GrandTour/Materials: a copy of M_GT_Environment (so it keeps the MF_Weather call, the
  CanPool puddles and the MF_TrackPaint ruts) whose BaseColor, Roughness and Porosity come from Landscape Layer
  Blend nodes over the four surface layers (Tarmac, Dirt, Mud, Snow) instead of one parameter each, and (mud plan
  stage B, redone in section 30, made one surface in section 31) an opacity-mask hole over each mud patch's whole box
  (MPC_TrackPaint's Patch0..Patch3, added by setup_m6_mud.py, run it first) shrunk by HoleInsetCm, so the mud mesh is
  the ground there. Since stage E3 the Mud and Bog rows also wear the CC0 "muddy_tracks" maps, sampled tri-planar at
  MudTileCm and tinted by the row colour over the map's mean, exactly as M_GT_Mud samples them (the mud mesh and the
  landscape meet at the patch box's border), and a layer-blended world-space normal feeds MP_NORMAL: MF_Weather has no
  normal input. Since stage J1 that shared block remaps the roughness map into MudRoughMin 0.70 - MudRoughMax 0.90 and
  the band is the Mud and Bog rows' roughness (the user: "mud is too shiny"), the same band the mud mesh takes.
  Run Art/setup_m6_textures.bat before this. Rebuilt from a fresh copy
  every run, so after any MF_Weather rebuild run setup_m3_weather.bat and then this again.
  Leg dressing LD2 (docs/LEG_DRESSING_PLAN.md): the eleven biome rows (BIOME_ROWS, graded samples of the Scrub / Dirt
  rows, no new texture sample), the OW LandscapeGrassOutput and an RVT output. GT_M6_STEP=material builds the material
  alone and touches no map (Art/dressing/ld2_landscape_material.bat); GT_M6_REPORT names a report JSON.
- /Game/GrandTour/Terrain/Layers/LI_Tarmac, LI_Dirt, LI_Mud, LI_Snow: landscape layer infos pointing at the
  surfaces' physical materials (what the wheels and the ruts read).
- L_Leg03: the flat floor and the old props go; UGTVehicleSetupLibrary.build_leg_landscape imports the ground
  generated from GTTerrain::HideSpec (the C++ is the one source of the route and the landforms: a valley start, a
  climb onto the plateau with the bear's dell beside the radiation pocket, a stream crossing, the last stretch under
  a hillside) as an 8 x 8 component landscape, 2 m quads, 2 km square; then the leg's actors are placed on it at the
  generated heights: checkpoints turned to the road, the zone, the leg start, the pocket and its cache, the bear in
  its dell ringed by boulders, cable bundles and a wreck beside the road, and boulders scattered off the road.
Safe to re-run.
"""
import json
import math
import os
import random
import re

import unreal

LEVEL_PATH = "/Game/GrandTour/Legs/L_Leg03"
HIDE_SPEC_NAME = "DA_Terrain_Hide"
LEG_FOLDER = "/Game/GrandTour/Legs"
HARVEST_FOLDER = "/Game/GrandTour/Harvest"
SURF_PATH = "/Game/GrandTour/Terrain/Surfaces"
TERRAIN_PATH = "/Game/GrandTour/Terrain"
LAYER_PATH = "/Game/GrandTour/Terrain/Layers"
MAT_PATH = "/Game/GrandTour/Materials"
MASTER = "M_GT_Environment"
HOLE_INSET_PARAM = "HoleInsetCm"   # the mud hole is a patch's box shrunk by this on every side: one mesh cell (AGTMudPatch::MeshCellCm)
HOLE_INSET_CM = 12.5
LANDSCAPE_MATERIAL = "M_GT_Landscape"
WATER_MATERIAL = "M_GT_Water"
PROP_PREFIXES = ("Lane_", "Marker_", "Road_", "Roof_", "Post_", "Node_", "Wreck_", "Zone_", "Front_", "Checkpoint_", "Extraction_", "LegStart_", "Subject_", "Hide_", "Rock_", "Water_", "Floor")   # the builder removes the landscape itself
# Per layer: base colour, roughness, porosity (the environment instances' values, setup_m1_track / setup_m1_masters).
LAYERS = [
    ("Tarmac", (0.16, 0.16, 0.17), 0.85, 0.3),
    ("Dirt", (0.52, 0.38, 0.22), 0.85, 0.9),    # the dirt road: warmer and lighter than the ground beside it
    ("Mud", (0.28, 0.20, 0.12), 0.55, 1.0),
    ("Snow", (0.90, 0.92, 0.96), 0.60, 0.6),
    ("Scrub", (0.30, 0.29, 0.19), 0.90, 0.85),  # the ground away from the road: dirt to the wheels, a duller face
    ("Bog", (0.18, 0.13, 0.08), 0.45, 1.0),     # deep mud down a bog's middle (stage 3): darker, wetter
]

# Mud plan stage D, one surface (setup_m6_mud.py adds the boxes to MPC_TrackPaint): inputs WorldPos, P0..P3 (a patch's
# box x0 y0 x1 y1 in cm, all zero = none) and HoleInsetCm. The landscape is masked out over the whole of a patch's box
# shrunk by HoleInsetCm on every side, so the mud mesh is the ground there and nothing meets at a lip; the inset leaves
# a one-cell ring of landscape under the mesh's edge. No texture sampling: until stage D the hole followed the mesh's
# own mask (the patches' field textures as MudField0..3) and the edge of the touched region was a visible seam.
# ---- stage E3: the same mud texture on the landscape's Mud and Bog rows ------------------------------------------
# The mud mesh (M_GT_Mud, setup_m6_mud.py) and the landscape meet at the mud patch's box border, so both must sample the
# same maps at the same world scale with the same tint. TRIPLANAR_HLSL below is a word-for-word copy of the block in
# setup_m6_mud.py and these five numbers are its numbers: keep them in step or the border draws itself.
MUD_TEX_PATH = "/Game/GrandTour/Textures/Mud"     # setup_m6_textures.bat imports the CC0 set here; run it first
MUD_TILE_CM = 150.0
TEXTURE_MEAN = (0.080993, 0.029794, 0.011753)     # the diffuse map's mean colour in linear space (setup_m6_textures.log)
MUD_NORMAL_SCALE = 1.0
MUD_ROUGH_VARY = 0.35                             # stage E2's swing of the row's roughness; unused since stage J's remap (kept as a parameter)
# Stage J1 (2026-09-16): the sourced roughness map reads wet (the user: "mud is too shiny"), so the shared block
# remaps its sample into this band and the band is the Mud and Bog rows' roughness. setup_m6_mud.py's two numbers.
MUD_ROUGH_MIN = 0.70
MUD_ROUGH_MAX = 0.90
# Stage H2 (2026-09-16): the same five noise numbers as setup_m6_mud.py, inside the same TRIPLANAR_HLSL block.
MUD_NOISE_FINE_CM = 60.0
MUD_NOISE_COARSE_CM = 250.0
MUD_NOISE_TINT = 0.08
MUD_NOISE_ROUGH = 0.1
MUD_NOISE_WARP = 0.15
# Stage I3 (2026-09-16): the tri-planar weights' exponent, inside TRIPLANAR_HLSL and so the same in both materials.
MUD_TRI_SHARP = 6.0
# The painterly ground rows (the user, 2026-09-20: "bring some painterly textures in"). Two CC0 sets from
# 3dtextures.me, imported by Art/setup_m6_textures.bat into /Game/GrandTour/Textures/Stylised: the Scrub row (the
# ground away from any road, the biggest thing on screen) wears "Stylized Grass 002", the Dirt row (every leg's road
# and the Proving Ground's tracks) "Stylized Dry Mud 001". Provenance: Art/Textures/Stylised/SOURCE.txt. The Mud and
# Bog rows are NOT touched - they keep the photoreal muddy_tracks set and the mud mesh's look (the user: "leave the
# mud alone"), so the two sit side by side and that is the thing to judge first.
# Sampled tri-planar like the mud, at these tiles, so nothing stretches on the verges, the ramp flanks or a hillside;
# albedo and roughness only (the sets' normals are imported but not sampled). GrassTint / DirtTint are colour knobs
# with a neutral default: the texture as its author made it.
STYLISED_TEX_PATH = "/Game/GrandTour/Textures/Stylised"
GRASS_TILE_CM = 350.0
DIRT_TILE_CM = 250.0
STYLISED_MAPS = (
    ("GrassDiff", "T_GT_Grass_D", "SAMPLERTYPE_COLOR"),
    ("GrassRough", "T_GT_Grass_R", "SAMPLERTYPE_LINEAR_COLOR"),
    ("DirtDiff", "T_GT_Dirt_D", "SAMPLERTYPE_COLOR"),
    ("DirtRough", "T_GT_Dirt_R", "SAMPLERTYPE_LINEAR_COLOR"),
)
STYLISED_ROWS = {"Scrub": "Grass", "Dirt": "Dirt"}

# ---- leg dressing LD2 (docs/LEG_DRESSING_PLAN.md, 2026-09-27): the biome rows ---------------------------------------
# A spec with biome rules (FGTTerrainSpec::Biomes, LD1) splits the Scrub weight into these layers (LI_<name>, each with
# the off-road physical material), so each gets a row here. No row samples a texture of its own: every one reuses the
# painterly ground node's sample of its parent row - Scrub's T_GT_Grass, or Dirt's T_GT_Dirt for Scree and Alpine - graded
# by the OW layer tint the way M_OWDressingLab grades its pack textures (Art/dressing/ported/ClaudeSetupDressingLab.py
# lab_material: texture x tint x GRADE_GAIN 10/3, so the meadow tint is about neutral and the forest floors darker).
# Roughness and porosity are the parent row's. A landscape with none of these layers (L_Proving, L_Leg03 until LD6)
# compiles them out per component, so its ground is unchanged.
BIOME_GRADE_GAIN = 10.0 / 3.0
# ClaudeSetupDressingLab.py:70 LAYER_TINTS (copied: that script runs its steps on import), and GrandTour's Thicket.
BIOME_TINTS = {
    "OW_Meadow": (0.13, 0.30, 0.10),
    "OW_MeadowLush": (0.10, 0.28, 0.08),
    "OW_MeadowDry": (0.30, 0.28, 0.12),
    "OW_Forest": (0.05, 0.15, 0.06),
    "OW_ForestBeech": (0.08, 0.16, 0.04),
    "OW_ForestBirch": (0.10, 0.19, 0.08),
    "OW_ForestFir": (0.03, 0.12, 0.07),
    "OW_ForestOak": (0.14, 0.18, 0.04),
    "OW_Scree": (0.32, 0.30, 0.28),
    "OW_Alpine": (0.26, 0.26, 0.18),
}
BIOME_TINTS["Thicket"] = tuple(0.8 * c for c in BIOME_TINTS["OW_MeadowLush"])   # the plan: MeadowLush's tint x 0.8
# (layer, parent row): the parent's painterly sample, roughness and porosity.
BIOME_ROWS = [
    ("OW_Meadow", "Scrub"), ("OW_MeadowLush", "Scrub"), ("OW_MeadowDry", "Scrub"),
    ("OW_Forest", "Scrub"), ("OW_ForestBeech", "Scrub"), ("OW_ForestBirch", "Scrub"),
    ("OW_ForestFir", "Scrub"), ("OW_ForestOak", "Scrub"),
    ("OW_Scree", "Dirt"), ("OW_Alpine", "Dirt"),
    ("Thicket", "Scrub"),
]
# The OW grass output (docs/landscape_migration/closure_summary.md:193, M_OWDressingLab's 12 pins) plus GrandTour's
# Thicket: (grass type, pin, layer, mask). The masks are lab_material()'s MF3 noise chains: "patch" clumps the forest
# floors, "drift" the flowers, "green" / "dry" split the meadow carpet into green and dry patches. The lab's verge kill
# (x (1 - OW_RoadVerge)) has no layer here: GrandTour's biome layers only ever hold off-road weight.
OW_GRASS_PATH = "/Game/OWGame/Dev/DressingLab"
# Leg dressing LD8b: the output wears GrandTour copies of the OW grass types (Art/dressing/gt_grass_copies.bat:
# LGT_OW<Name> -> /Game/GrandTour/Dressing/Grass/LGT_GT_<Name>, no dynamic shadow, contact shadow, no distance field
# lighting); the OW grass types stay untouched.
GT_GRASS_PATH = "/Game/GrandTour/Dressing/Grass"


def gt_grass_name(ow_name):
    return "LGT_GT_" + ow_name[len("LGT_OW"):]
BIOME_GRASS = [
    ("LGT_OWMeadowGrass", "MeadowGrass", "OW_Meadow", "green"),
    ("LGT_OWMeadowFlowers", "MeadowFlowers", "OW_Meadow", "drift"),
    ("LGT_OWMeadowDryGrass", "MeadowDryPatches", "OW_Meadow", "dry"),
    ("LGT_OWMeadowLushGrass", "MeadowLushGrass", "OW_MeadowLush", None),
    ("LGT_OWMeadowLushFlowers", "MeadowLushFlowers", "OW_MeadowLush", "drift"),
    ("LGT_OWMeadowDryGrass", "MeadowDryGrass", "OW_MeadowDry", None),
    ("LGT_OWForestFloor", "ForestFloor", "OW_Forest", "patch"),
    ("LGT_OWFloorDeciduous", "ForestFloorBeech", "OW_ForestBeech", "patch"),
    ("LGT_OWFloorDeciduous", "ForestFloorBirch", "OW_ForestBirch", "patch"),
    ("LGT_OWFloorFir", "ForestFloorFir", "OW_ForestFir", "patch"),
    ("LGT_OWFloorOak", "ForestFloorOak", "OW_ForestOak", "patch"),
    ("LGT_OWAlpineGrass", "AlpineGrass", "OW_Alpine", None),
    ("LGT_OWMeadowLushGrass", "ThicketGrass", "Thicket", None),
]
# The pack RVT M_OWDressingLab writes (BaseColor, Roughness, Normal: lab_material()). The output node names no RVT: the
# landscape's own RuntimeVirtualTextures list does (LD6).
BIOME_RVT = "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material"


def _biome_row(layer_name, parent):
    base = dict((n, (c, r, p)) for (n, c, r, p) in LAYERS)[parent]
    return (layer_name, BIOME_TINTS[layer_name], base[1], base[2])


# Every row of the landscape material's layer blends: the six surface layers (indices 0-5, as the generator's), then the biomes.
ROWS = LAYERS + [_biome_row(n, p) for (n, p) in BIOME_ROWS]

# What build_landscape_material found and made (the LD2 report, GT_M6_REPORT).
MATERIAL_FACTS = {}

GROUND_TEX_HLSL = """float3 gn = normalize(VertexNormal.xyz);
float3 bl = pow(abs(gn), max(TriSharp, 1.0));
bl /= max(bl.x + bl.y + bl.z, 1e-4);
float gt = max(GrassTileCm, 1.0);
float3 gtex = bl.z * Texture2DSample(GrassDiff, GrassDiffSampler, WorldPos.xy / gt).rgb
            + bl.y * Texture2DSample(GrassDiff, GrassDiffSampler, WorldPos.xz / gt).rgb
            + bl.x * Texture2DSample(GrassDiff, GrassDiffSampler, WorldPos.yz / gt).rgb;
float grough = bl.z * Texture2DSample(GrassRough, GrassRoughSampler, WorldPos.xy / gt).r
             + bl.y * Texture2DSample(GrassRough, GrassRoughSampler, WorldPos.xz / gt).r
             + bl.x * Texture2DSample(GrassRough, GrassRoughSampler, WorldPos.yz / gt).r;
float dt = max(DirtTileCm, 1.0);
float3 dtex = bl.z * Texture2DSample(DirtDiff, DirtDiffSampler, WorldPos.xy / dt).rgb
            + bl.y * Texture2DSample(DirtDiff, DirtDiffSampler, WorldPos.xz / dt).rgb
            + bl.x * Texture2DSample(DirtDiff, DirtDiffSampler, WorldPos.yz / dt).rgb;
float drough = bl.z * Texture2DSample(DirtRough, DirtRoughSampler, WorldPos.xy / dt).r
             + bl.y * Texture2DSample(DirtRough, DirtRoughSampler, WorldPos.xz / dt).r
             + bl.x * Texture2DSample(DirtRough, DirtRoughSampler, WorldPos.yz / dt).r;
float gr = clamp(grough, 0.05, 1.0);
float dr = clamp(drough, 0.05, 1.0);
GrassRoughOut = float3(gr, gr, gr);
DirtRoughOut = float3(dr, dr, dr);
DirtAlbedo = saturate(dtex * DirtTint.rgb);
return saturate(gtex * GrassTint.rgb);
"""

TEXTURED_ROWS = ("Mud", "Bog")                    # the rows that wear the texture; every other row stays constant
MUD_MAPS = (
    ("MudDiffuse", "T_GT_Mud_Diffuse", "SAMPLERTYPE_COLOR"),
    ("MudNormal", "T_GT_Mud_Normal", "SAMPLERTYPE_NORMAL"),
    ("MudRough", "T_GT_Mud_Rough", "SAMPLERTYPE_LINEAR_COLOR"),
)

TRIPLANAR_HLSL = """float2 nfp = WorldPos.xy / max(NoiseFineCm, 1.0);
float2 nfi = floor(nfp);
float2 nff = nfp - nfi;
nff = nff * nff * (3.0 - 2.0 * nff);
float4 nfh = frac(sin(float4(dot(nfi, float2(127.1, 311.7)), dot(nfi + float2(1.0, 0.0), float2(127.1, 311.7)),
                             dot(nfi + float2(0.0, 1.0), float2(127.1, 311.7)), dot(nfi + float2(1.0, 1.0), float2(127.1, 311.7)))) * 43758.5453);
float nFine = lerp(lerp(nfh.x, nfh.y, nff.x), lerp(nfh.z, nfh.w, nff.x), nff.y) * 2.0 - 1.0;
float2 ncp = WorldPos.xy / max(NoiseCoarseCm, 1.0);
float2 nci = floor(ncp);
float2 ncf = ncp - nci;
ncf = ncf * ncf * (3.0 - 2.0 * ncf);
float4 nch = frac(sin(float4(dot(nci, float2(269.5, 183.3)), dot(nci + float2(1.0, 0.0), float2(269.5, 183.3)),
                             dot(nci + float2(0.0, 1.0), float2(269.5, 183.3)), dot(nci + float2(1.0, 1.0), float2(269.5, 183.3)))) * 27183.1717);
float nCoarse = lerp(lerp(nch.x, nch.y, ncf.x), lerp(nch.z, nch.w, ncf.x), ncf.y) * 2.0 - 1.0;
float nMud = 0.6 * nFine + 0.4 * nCoarse;
float2 warp = float2(nFine, nCoarse) * NoiseWarp;
float3 bl = pow(abs(gn), max(TriSharp, 1.0));
bl /= max(bl.x + bl.y + bl.z, 1e-4);
float tile = max(TileCm, 1.0);
float2 tuz = WorldPos.xy / tile + warp;
float2 tuy = WorldPos.xz / tile + warp;
float2 tux = WorldPos.yz / tile + warp;
float3 tex = bl.z * Texture2DSample(DiffTex, DiffTexSampler, tuz).rgb
           + bl.y * Texture2DSample(DiffTex, DiffTexSampler, tuy).rgb
           + bl.x * Texture2DSample(DiffTex, DiffTexSampler, tux).rgb;
tex *= 1.0 + NoiseTint * nMud;
float texRough = bl.z * Texture2DSample(RoughTex, RoughTexSampler, tuz).r
               + bl.y * Texture2DSample(RoughTex, RoughTexSampler, tuy).r
               + bl.x * Texture2DSample(RoughTex, RoughTexSampler, tux).r;
// Stage J1: the sourced roughness map reads wet, so its range is remapped into RoughMin..RoughMax and texRough is the
// roughness itself from here on - the layer rows' own roughness and MudRoughVary's swing no longer reach the mud.
texRough = clamp(lerp(RoughMin, RoughMax, saturate(texRough)), 0.02, 1.0);
float2 pz = Texture2DSample(NormTex, NormTexSampler, tuz).rg * 2.0 - 1.0;
float2 py = Texture2DSample(NormTex, NormTexSampler, tuy).rg * 2.0 - 1.0;
float2 px = Texture2DSample(NormTex, NormTexSampler, tux).rg * 2.0 - 1.0;
float3 tz = float3(pz, sqrt(saturate(1.0 - dot(pz, pz))));
float3 ty = float3(py, sqrt(saturate(1.0 - dot(py, py))));
float3 tx = float3(px, sqrt(saturate(1.0 - dot(px, px))));
float3 dn = bl.z * float3(tz.x, tz.y, tz.z * sign(gn.z))
          + bl.y * float3(ty.x, ty.z * sign(gn.y), ty.y)
          + bl.x * float3(tx.z * sign(gn.x), tx.x, tx.y);
"""

# One node for both textured rows: the albedo tinted by each row's own colour (the row's colour divided by the map's mean,
# so the texture's average reads as the row and the ground keeps the tone it had), the row's roughness swung by the
# roughness map, and one world-space detail normal over the landscape's vertex normal.
MUD_TEX_HLSL = """float3 gn = normalize(VertexNormal.xyz);
""" + TRIPLANAR_HLSL + """float3 tint = 1.0 / max(MeanColor.rgb, 1e-4);
BogAlbedo = saturate(tex * (BogColor.rgb * tint));
// Stage J1: texRough is the map remapped into RoughMin..RoughMax by the shared block and it is the roughness itself,
// the same band the mud mesh takes, so the box border stays invisible. Until then it swung each row's own roughness
// (MudRough 0.55 / BogRough 0.45) by RoughVary, and both the rows and the map read wet. Those three are still wired.
float mr = clamp(texRough + NoiseRough * nMud, 0.02, 1.0);
float br = mr;
MudRoughOut = float3(mr, mr, mr);
BogRoughOut = float3(br, br, br);
Normal = normalize(float3(gn.xy + dn.xy * NormalScale, gn.z));
return saturate(tex * (MudColor.rgb * tint));
"""

# The layer blend sums its rows by weight, so a pixel with no weight at all would hand MP_NORMAL a zero vector.
NORMAL_SAFE_HLSL = """float3 n = N;
float l = length(n);
return (l > 0.001) ? (n / l) : normalize(VN);
"""

MUD_HOLE_HLSL = """float4 boxes[4] = { P0, P1, P2, P3 };
float mask = 1.0;
float inset = max(HoleInsetCm, 0.0);
[unroll]
for (int i = 0; i < 4; ++i)
{
    float4 b = boxes[i];
    if (b.z > b.x + 2.0 * inset && b.w > b.y + 2.0 * inset
        && WorldPos.x >= b.x + inset && WorldPos.x <= b.z - inset
        && WorldPos.y >= b.y + inset && WorldPos.y <= b.w - inset)
    {
        mask = 0.0;
    }
}
return mask;
"""

lib = unreal.GTVehicleSetupLibrary
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cube = unreal.load_asset("/Engine/BasicShapes/Cube")
sphere = unreal.load_asset("/Engine/BasicShapes/Sphere")


def log(msg):
    unreal.log("SETUP_M6_HIDE " + msg)


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    # unreal.Rotator's positional order is (roll, pitch, yaw); always use keywords.
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def load_or_none(path):
    return eal.load_asset(path) if eal.does_asset_exist(path) else None


def connect(src, out_name, dst, in_name):
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    for alt in names:
        if alt != in_name and mel.connect_material_expressions(src, out_name, dst, alt):
            return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


def connect_exact(src, out_name, dst, in_name):
    """connect() without its fallback: a custom node's pins are named by us, so a miss is a mistake, not a rename."""
    if mel.connect_material_expressions(src, out_name, dst, in_name):
        return
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


SAMPLE_CALL = re.compile(r"\bTexture(?:2D|2DArray|3D|Cube)Sample\w*\s*\(")


def texture_sample_count(material):
    """LD2: the texture samples a pixel of the material's own graph costs - every Texture*Sample call in its custom HLSL
    nodes (the mud node's 9, the painterly ground node's 12) plus every texture / virtual texture sample expression - the
    way the 21 was counted (VEHICLE_BUILD_SYSTEM 48). Material functions' insides are not counted (MF_Weather's own)."""
    count = 0
    for e in mel.get_material_expressions(material):
        if isinstance(e, unreal.MaterialExpressionCustom):
            count += len(SAMPLE_CALL.findall(str(e.get_editor_property("code"))))
        elif isinstance(e, unreal.MaterialExpressionTextureObjectParameter):
            continue   # a texture object (a TextureSample subclass) samples nothing: the custom node that reads it does
        elif isinstance(e, (unreal.MaterialExpressionTextureSample, unreal.MaterialExpressionRuntimeVirtualTextureSample)):
            count += 1
    return count


def asset_class_name(asset_data):
    """An AssetData's class name (the audit_toolkit.py way: asset_class_path's asset_name, else the old asset_class)."""
    for getter in (lambda: asset_data.get_editor_property("asset_class_path").get_editor_property("asset_name"),
                   lambda: asset_data.asset_class_path.asset_name,
                   lambda: asset_data.get_editor_property("asset_class")):
        try:
            name = str(getter())
            if name and name != "None":
                return name
        except Exception:
            pass
    return ""


def parameter_collections(material):
    """LD2: the parameter collections the material's shader reads: those its own graph's Collection Parameter nodes name,
    plus those its material functions reach (the functions' packages' hard dependencies, through nested functions; the
    asset registry holds them from disk). Not through grass types or meshes: those are other materials' shaders. The
    material's own package is not asked of the registry, so a just-rebuilt, just-saved material reads right too."""
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True,
                                                    include_searchable_names=False, include_soft_management_references=False,
                                                    include_hard_management_references=False)
    found, seen, todo = set(), set(), []
    for e in mel.get_material_expressions(material):
        if isinstance(e, unreal.MaterialExpressionCollectionParameter):
            collection = e.get_editor_property("collection")
            if collection is not None:
                found.add(collection.get_outermost().get_name())
        elif isinstance(e, unreal.MaterialExpressionMaterialFunctionCall):
            function = e.get_editor_property("material_function")
            if function is not None:
                todo.append(function.get_outermost().get_name())
    while todo:
        package = todo.pop()
        if package in seen:
            continue
        seen.add(package)
        for dep in ar.get_dependencies(unreal.Name(package), options) or []:
            dep = str(dep)
            classes = [asset_class_name(a) for a in (ar.get_assets_by_package_name(unreal.Name(dep), False) or [])]
            if "MaterialParameterCollection" in classes:
                found.add(dep)
            elif "MaterialFunction" in classes:
                todo.append(dep)
    return sorted(found), sorted(seen)


# ---- the landscape material -------------------------------------------------------------------
def build_landscape_material():
    master_full = MAT_PATH + "/" + MASTER
    target_full = MAT_PATH + "/" + LANDSCAPE_MATERIAL
    if not eal.does_asset_exist(master_full):
        raise SystemExit("missing " + master_full + " (run setup_m1_masters.bat first)")
    if eal.does_asset_exist(target_full):
        old = eal.load_asset(target_full)
        MATERIAL_FACTS["samples_before"] = texture_sample_count(old)
        MATERIAL_FACTS["expressions_before"] = mel.get_num_material_expressions(old)
        MATERIAL_FACTS["mpcs_before"], MATERIAL_FACTS["functions_before"] = parameter_collections(old)
        log("LD2 before: %s had %d texture samples in its own graph, %d expressions, parameter collections %s"
            % (LANDSCAPE_MATERIAL, MATERIAL_FACTS["samples_before"], MATERIAL_FACTS["expressions_before"], MATERIAL_FACTS["mpcs_before"]))
        old = None
        eal.delete_asset(target_full)
    if not eal.duplicate_asset(master_full, target_full):
        raise SystemExit("could not copy the environment master to " + target_full)
    m = eal.load_asset(target_full)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)   # the hole under the mud mesh (the block below)
    call = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
    if call is None or not isinstance(call, unreal.MaterialExpressionMaterialFunctionCall):
        raise SystemExit("the copied master does not end in an MF_Weather call (run setup_m1_masters.bat)")

    def blend(name, x, y, values, inputs=None):
        """A Landscape Layer Blend over ROWS (the six surface layers, then LD2's biome rows). A row in `inputs`
        ({index: (expression, output)}) takes that expression on its layer_input pin instead of its constant: stage E3
        feeds the Mud and Bog rows the tri-planar mud maps, LD2 the biome rows their parent's graded sample."""
        if len(values) != len(ROWS):
            raise SystemExit("the %s blend has %d values for %d rows" % (name, len(values), len(ROWS)))
        node = mel.create_material_expression(m, unreal.MaterialExpressionLandscapeLayerBlend, x, y)
        node.set_editor_property("desc", "Landscape:" + name)
        layers = []
        for index, (layer_name, _colour, _rough, _poro) in enumerate(ROWS):
            entry = unreal.LayerBlendInput()
            entry.set_editor_property("layer_name", layer_name)
            entry.set_editor_property("blend_type", unreal.LandscapeLayerBlendType.LB_WEIGHT_BLEND)
            v = values[index]
            entry.set_editor_property("const_layer_input", unreal.Vector(v[0], v[1], v[2]))
            entry.set_editor_property("preview_weight", 1.0 if index == 1 else 0.0)
            layers.append(entry)
        node.set_editor_property("layers", layers)
        if inputs:
            pins = [str(p) for p in mel.get_material_expression_input_names(node)]
            wired = []
            for index in sorted(inputs):
                src, out_name = inputs[index]
                layer_name = ROWS[index][0]
                # The pin whose name ends in the layer's own name ("Layer OW_Meadow"): a substring match would take
                # OW_MeadowLush's pin for OW_Meadow.
                pin = next((p for p in pins if p.lower().split()[-1:] == [layer_name.lower()]), None)
                if pin is None:
                    raise SystemExit("no pin for the %s row on the %s blend (pins %s)" % (layer_name, name, pins))
                connect_exact(src, out_name, node, pin)
                wired.append("%s <- %s.%s" % (pin, src.get_name(), out_name or "(main)"))
            log("layer blend %s: pins %s; wired %s" % (name, pins, wired))
        return node

    # ---- stage E3: the sourced mud maps on the Mud and Bog rows ---------------------------------
    tex_nodes = {}
    for offset, (param_name, asset_name, sampler) in enumerate(MUD_MAPS):
        asset_full = MUD_TEX_PATH + "/" + asset_name
        if not eal.does_asset_exist(asset_full):
            raise SystemExit("missing " + asset_full + " (run Art/setup_m6_textures.bat first: it imports the CC0 mud set)")
        node = mel.create_material_expression(m, unreal.MaterialExpressionTextureObjectParameter, -1400, -950 + 150 * offset)
        node.set_editor_property("parameter_name", param_name)
        node.set_editor_property("texture", eal.load_asset(asset_full))
        node.set_editor_property("sampler_type", getattr(unreal.MaterialSamplerType, sampler))
        node.set_editor_property("desc", "Landscape:" + param_name.lower())
        tex_nodes[param_name] = node
        log("%s <- %s (%s)" % (param_name, asset_full, sampler))

    def const3(name, value, x, y):
        e = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, x, y)
        e.set_editor_property("desc", "Landscape:" + name)
        e.set_editor_property("constant", unreal.LinearColor(value[0], value[1], value[2], 1.0))
        return e

    def param_scalar(name, value, x, y):
        e = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, x, y)
        e.set_editor_property("desc", "Landscape:" + name.lower())
        e.set_editor_property("parameter_name", name)
        e.set_editor_property("default_value", value)
        return e

    rows = dict((layer_name, (colour_value, rough_value)) for (layer_name, colour_value, rough_value, _p) in LAYERS)
    tex_wpos = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -1400, -1250)
    tex_wpos.set_editor_property("desc", "Landscape:texwpos")
    vnormal = mel.create_material_expression(m, unreal.MaterialExpressionVertexNormalWS, -1400, -1150)
    vnormal.set_editor_property("desc", "Landscape:vertexnormal")
    mean_colour = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -1400, -500)
    mean_colour.set_editor_property("desc", "Landscape:texmean")
    mean_colour.set_editor_property("parameter_name", "TextureMeanColor")
    mean_colour.set_editor_property("default_value", unreal.LinearColor(TEXTURE_MEAN[0], TEXTURE_MEAN[1], TEXTURE_MEAN[2], 1.0))
    mudtex = mel.create_material_expression(m, unreal.MaterialExpressionCustom, -1050, -700)
    mudtex.set_editor_property("desc", "Landscape:mudtex")
    mudtex.set_editor_property("description", "Mud maps (tri-planar)")
    mudtex.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    tex_inputs = []
    for name in ("WorldPos", "VertexNormal", "DiffTex", "NormTex", "RoughTex", "TileCm", "MeanColor",
                 "MudColor", "BogColor", "MudRough", "BogRough", "RoughVary", "RoughMin", "RoughMax", "NormalScale",
                 "NoiseFineCm", "NoiseCoarseCm", "NoiseTint", "NoiseRough", "NoiseWarp", "TriSharp"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        tex_inputs.append(ci)
    mudtex.set_editor_property("inputs", tex_inputs)
    tex_outputs = []
    for name in ("BogAlbedo", "Normal", "MudRoughOut", "BogRoughOut"):
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", name)
        co.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        tex_outputs.append(co)
    mudtex.set_editor_property("additional_outputs", tex_outputs)
    mudtex.set_editor_property("code", MUD_TEX_HLSL)
    for src, pin in ((tex_wpos, "WorldPos"), (vnormal, "VertexNormal"),
                     (tex_nodes["MudDiffuse"], "DiffTex"), (tex_nodes["MudNormal"], "NormTex"), (tex_nodes["MudRough"], "RoughTex"),
                     (param_scalar("MudTileCm", MUD_TILE_CM, -1400, -600), "TileCm"), (mean_colour, "MeanColor"),
                     (const3("mudcolour", rows["Mud"][0], -1400, -400), "MudColor"),
                     (const3("bogcolour", rows["Bog"][0], -1400, -300), "BogColor"),
                     (param_scalar("MudRoughVary", MUD_ROUGH_VARY, -1400, 0), "RoughVary"),
                     (param_scalar("MudRoughMin", MUD_ROUGH_MIN, -1400, 40), "RoughMin"),
                     (param_scalar("MudRoughMax", MUD_ROUGH_MAX, -1400, 70), "RoughMax"),
                     (param_scalar("MudNormalScale", MUD_NORMAL_SCALE, -1400, 100), "NormalScale"),
                     (param_scalar("MudNoiseFineCm", MUD_NOISE_FINE_CM, -1400, 200), "NoiseFineCm"),
                     (param_scalar("MudNoiseCoarseCm", MUD_NOISE_COARSE_CM, -1400, 300), "NoiseCoarseCm"),
                     (param_scalar("MudNoiseTint", MUD_NOISE_TINT, -1400, 400), "NoiseTint"),
                     (param_scalar("MudNoiseRough", MUD_NOISE_ROUGH, -1400, 500), "NoiseRough"),
                     (param_scalar("MudNoiseWarp", MUD_NOISE_WARP, -1400, 600), "NoiseWarp"),
                     (param_scalar("MudTriSharp", MUD_TRI_SHARP, -1400, 700), "TriSharp")):
        connect_exact(src, "", mudtex, pin)
    for value, pin, y in ((rows["Mud"][1], "MudRough", -200), (rows["Bog"][1], "BogRough", -100)):
        e = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -1400, y)
        e.set_editor_property("desc", "Landscape:" + pin.lower())
        e.set_editor_property("r", value)
        connect_exact(e, "", mudtex, pin)
    textured = [i for i, (layer_name, _c, _r, _p) in enumerate(LAYERS) if layer_name in TEXTURED_ROWS]
    log("mud texture: tri-planar %s / %s / %s at MudTileCm %.0f cm on the %s rows, tinted by the row colour / TextureMeanColor "
        "%.6f %.6f %.6f, detail normal at MudNormalScale %.2f, the roughness map remapped into MudRoughMin %.2f - "
        "MudRoughMax %.2f (stage J1; MudRoughVary %.2f no longer reads, and the rows' own %.2f / %.2f with it); "
        "M_GT_Mud carries the same block and the same band"
        % (MUD_MAPS[0][1], MUD_MAPS[1][1], MUD_MAPS[2][1], MUD_TILE_CM, list(TEXTURED_ROWS),
           TEXTURE_MEAN[0], TEXTURE_MEAN[1], TEXTURE_MEAN[2], MUD_NORMAL_SCALE, MUD_ROUGH_MIN, MUD_ROUGH_MAX,
           MUD_ROUGH_VARY, rows["Mud"][1], rows["Bog"][1]))
    log("stage I3: the tri-planar weights sharpened to pow(abs(n), %.0f) (MudTriSharp, 4 until stage I); M_GT_Mud carries "
        "the same number, and the slurry floor and the matte crests are the mesh's own (there are no tracks on the landscape)"
        % MUD_TRI_SHARP)
    log("stage H2 noise: two octaves of world-space value noise at MudNoiseFineCm %.0f and MudNoiseCoarseCm %.0f cm, the uv "
        "warped by MudNoiseWarp %.2f tiles per octave, the tint swung by MudNoiseTint %.2f and the %s rows' roughness by "
        "MudNoiseRough %.2f; M_GT_Mud carries the same block and the same five numbers"
        % (MUD_NOISE_FINE_CM, MUD_NOISE_COARSE_CM, MUD_NOISE_WARP, MUD_NOISE_TINT, list(TEXTURED_ROWS), MUD_NOISE_ROUGH))

    # ---- the painterly ground rows (2026-09-20): the same tri-planar treatment on Scrub and Dirt -------------
    ground_nodes = {}
    for offset, (param_name, asset_name, sampler) in enumerate(STYLISED_MAPS):
        asset_full = STYLISED_TEX_PATH + "/" + asset_name
        if not eal.does_asset_exist(asset_full):
            raise SystemExit("missing " + asset_full + " (run Art/setup_m6_textures.bat first: it imports the CC0 painterly ground sets)")
        node = mel.create_material_expression(m, unreal.MaterialExpressionTextureObjectParameter, -1750, -950 + 150 * offset)
        node.set_editor_property("parameter_name", param_name)
        node.set_editor_property("texture", eal.load_asset(asset_full))
        node.set_editor_property("sampler_type", getattr(unreal.MaterialSamplerType, sampler))
        node.set_editor_property("desc", "Landscape:" + param_name.lower())
        ground_nodes[param_name] = node
        log("%s <- %s (%s)" % (param_name, asset_full, sampler))

    def param_colour(name, x, y):
        e = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, x, y)
        e.set_editor_property("desc", "Landscape:" + name.lower())
        e.set_editor_property("parameter_name", name)
        e.set_editor_property("default_value", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
        return e

    groundtex = mel.create_material_expression(m, unreal.MaterialExpressionCustom, -1050, -1100)
    groundtex.set_editor_property("desc", "Landscape:groundtex")
    groundtex.set_editor_property("description", "Painterly ground (tri-planar)")
    groundtex.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    ground_inputs = []
    for name in ("WorldPos", "VertexNormal", "GrassDiff", "GrassRough", "DirtDiff", "DirtRough",
                 "GrassTileCm", "DirtTileCm", "GrassTint", "DirtTint", "TriSharp"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        ground_inputs.append(ci)
    groundtex.set_editor_property("inputs", ground_inputs)
    ground_outputs = []
    for name in ("DirtAlbedo", "GrassRoughOut", "DirtRoughOut"):
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", name)
        co.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        ground_outputs.append(co)
    groundtex.set_editor_property("additional_outputs", ground_outputs)
    groundtex.set_editor_property("code", GROUND_TEX_HLSL)
    for src, pin in ((tex_wpos, "WorldPos"), (vnormal, "VertexNormal"),
                     (ground_nodes["GrassDiff"], "GrassDiff"), (ground_nodes["GrassRough"], "GrassRough"),
                     (ground_nodes["DirtDiff"], "DirtDiff"), (ground_nodes["DirtRough"], "DirtRough"),
                     (param_scalar("GrassTileCm", GRASS_TILE_CM, -1750, -300), "GrassTileCm"),
                     (param_scalar("DirtTileCm", DIRT_TILE_CM, -1750, -250), "DirtTileCm"),
                     (param_colour("GrassTint", -1750, -200), "GrassTint"),
                     (param_colour("DirtTint", -1750, -120), "DirtTint"),
                     (param_scalar("GroundTriSharp", MUD_TRI_SHARP, -1750, -60), "TriSharp")):
        connect_exact(src, "", groundtex, pin)
    stylised = dict((layer_name, index) for index, (layer_name, _c, _r, _p) in enumerate(LAYERS) if layer_name in STYLISED_ROWS)
    log("painterly ground: %s tri-planar on the %s row at GrassTileCm %.0f cm and %s on the %s row at DirtTileCm %.0f cm "
        "(albedo and roughness only, the sets' normals imported and not sampled; GrassTint / DirtTint neutral). The Mud "
        "and Bog rows keep the photoreal muddy_tracks set."
        % (STYLISED_MAPS[0][1], "Scrub", GRASS_TILE_CM, STYLISED_MAPS[2][1], "Dirt", DIRT_TILE_CM))

    # ---- LD2: the biome rows - each the parent row's painterly output (no new sample) graded by its OW tint --------
    parent_albedo = {"Scrub": (groundtex, ""), "Dirt": (groundtex, "DirtAlbedo")}
    parent_rough = {"Scrub": (groundtex, "GrassRoughOut"), "Dirt": (groundtex, "DirtRoughOut")}
    biome_colour, biome_rough = {}, {}
    graded = []
    for offset, (layer_name, parent) in enumerate(BIOME_ROWS):
        index = len(LAYERS) + offset
        tint = BIOME_TINTS[layer_name]
        grade_value = tuple(c * BIOME_GRADE_GAIN for c in tint)
        grade = const3("grade_" + layer_name.lower(), grade_value, -1050, 1600 + 120 * offset)
        mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -880, 1600 + 120 * offset)
        mul.set_editor_property("desc", "Landscape:graded_" + layer_name.lower())
        src, out_name = parent_albedo[parent]
        connect_exact(src, out_name, mul, "A")
        connect_exact(grade, "", mul, "B")
        biome_colour[index] = (mul, "")
        biome_rough[index] = parent_rough[parent]
        graded.append("%s = %s x (%.3f %.3f %.3f)" % (layer_name, "T_GT_Grass" if parent == "Scrub" else "T_GT_Dirt",
                                                       grade_value[0], grade_value[1], grade_value[2]))
    log("LD2 biome rows (%d): %s; grade = OW tint x %.3f (lab_material's GRADE_GAIN), roughness and porosity the parent's"
        % (len(BIOME_ROWS), "; ".join(graded), BIOME_GRADE_GAIN))
    colour_inputs = {textured[0]: (mudtex, ""), textured[1]: (mudtex, "BogAlbedo"),
                     stylised["Scrub"]: (groundtex, ""), stylised["Dirt"]: (groundtex, "DirtAlbedo")}
    colour_inputs.update(biome_colour)
    rough_inputs = {textured[0]: (mudtex, "MudRoughOut"), textured[1]: (mudtex, "BogRoughOut"),
                    stylised["Scrub"]: (groundtex, "GrassRoughOut"), stylised["Dirt"]: (groundtex, "DirtRoughOut")}
    rough_inputs.update(biome_rough)
    colour = blend("colour", -700, -400, [c for (_n, c, _r, _p) in ROWS], inputs=colour_inputs)
    rough = blend("roughness", -700, -100, [(r, r, r) for (_n, _c, r, _p) in ROWS], inputs=rough_inputs)
    poro = blend("porosity", -700, 200, [(p, p, p) for (_n, _c, _r, p) in ROWS])
    connect(colour, "", call, "BaseColor")
    masks = {}
    for node, pin, tag in ((rough, "Roughness", "roughmask"), (poro, "Porosity", "poromask")):
        mask = mel.create_material_expression(m, unreal.MaterialExpressionComponentMask, -450, -100 if pin == "Roughness" else 200)
        mask.set_editor_property("desc", "Landscape:" + tag)
        mask.set_editor_property("r", True)
        mask.set_editor_property("g", False)
        mask.set_editor_property("b", False)
        mask.set_editor_property("a", False)
        connect(node, "", mask, "")
        connect(mask, "", call, pin)
        masks[pin] = mask
    # Stage E3, the normal. MF_Weather takes BaseColor, Roughness, Porosity, LocalWetness, LocalSnow and CanPool and no
    # normal at all (the call's pins are logged below), so the plan's fallback applies: a layer-blended normal goes
    # straight into MP_NORMAL. It is a world-space normal (tangent_space_normal off), exactly as the mud mesh's is, so
    # the two surfaces shade the same detail the same way where they meet. The Mud and Bog rows take the tri-planar
    # detail normal over the landscape's vertex normal; every other row takes the vertex normal itself, so nothing else
    # changes. The layer blend sums by weight, so a small custom node normalises it and falls back to the vertex normal
    # where no layer has any weight.
    m.set_editor_property("tangent_space_normal", False)
    normal_inputs = dict((index, (mudtex, "Normal") if layer_name in TEXTURED_ROWS else (vnormal, ""))
                         for index, (layer_name, _c, _r, _p) in enumerate(ROWS))
    normal_blend = blend("normal", -700, 1200, [(0.0, 0.0, 1.0)] * len(ROWS), inputs=normal_inputs)
    normal_safe = mel.create_material_expression(m, unreal.MaterialExpressionCustom, -350, 1200)
    normal_safe.set_editor_property("desc", "Landscape:normalsafe")
    normal_safe.set_editor_property("description", "Blended normal (world space)")
    normal_safe.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    safe_inputs = []
    for name in ("N", "VN"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        safe_inputs.append(ci)
    normal_safe.set_editor_property("inputs", safe_inputs)
    normal_safe.set_editor_property("code", NORMAL_SAFE_HLSL)
    connect_exact(normal_blend, "", normal_safe, "N")
    connect_exact(vnormal, "", normal_safe, "VN")
    if not mel.connect_material_property(normal_safe, "", unreal.MaterialProperty.MP_NORMAL):
        raise SystemExit("could not connect the layer-blended normal to Normal")
    log("normal: MF_Weather takes no normal input, so the layer-blended normal feeds MP_NORMAL directly, in world space "
        "(tangent_space_normal off) as M_GT_Mud's is; the %s rows take the mud maps' detail normal, every other row the "
        "landscape's vertex normal" % list(TEXTURED_ROWS))
    # Mud plan stage D, 2026-09-15 (section 31): the landscape is masked out over the whole of each mud patch's box,
    # shrunk by HoleInsetCm (12.5, one mesh cell), so the mud mesh is the ground there and there is no boundary between
    # touched and untouched mud. The boxes Patch0..3 come from MPC_TrackPaint (UGTMudSubsystem writes them at BeginPlay;
    # a material may reference two collections and this one has weather and track paint), and nothing else is needed:
    # the MudField0..3 texture object parameters and their per-patch binding are gone (section 30's hole followed the
    # mesh's own mask, and the edge of the touched region showed as a thin dark line from eye height). Before that the
    # Mud and Bog layers were pushed back 100 cm in depth inside the boxes instead, and the sheet floated in front of
    # the dirt. Outside play the boxes are zero, so there is no hole.
    mpc_mud = load_or_none(TERRAIN_PATH + "/MPC_TrackPaint")
    if mpc_mud is None or "Patch0" not in [str(n) for n in mpc_mud.get_vector_parameter_names()]:
        raise SystemExit("MPC_TrackPaint has no Patch0..Patch3 (run setup_m6_mud.bat first)")
    hole_wpos = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -700, 500)
    hole_wpos.set_editor_property("desc", "Landscape:holewpos")
    hole = mel.create_material_expression(m, unreal.MaterialExpressionCustom, -250, 650)
    hole.set_editor_property("desc", "Landscape:hole")
    hole.set_editor_property("description", "Mud hole (opacity mask)")
    hole.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    inputs = []
    for name in ("WorldPos", "P0", "P1", "P2", "P3", "HoleInsetCm"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        inputs.append(ci)
    hole.set_editor_property("inputs", inputs)
    hole.set_editor_property("code", MUD_HOLE_HLSL)
    connect(hole_wpos, "", hole, "WorldPos")
    for index in range(4):
        box = mel.create_material_expression(m, unreal.MaterialExpressionCollectionParameter, -700, 600 + 100 * index)
        box.set_editor_property("desc", "Landscape:patch%d" % index)
        box.set_editor_property("collection", mpc_mud)
        box.set_editor_property("parameter_name", "Patch%d" % index)
        connect(box, "", hole, "P%d" % index)
    inset = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -700, 1000)
    inset.set_editor_property("desc", "Landscape:holeinset")
    inset.set_editor_property("parameter_name", HOLE_INSET_PARAM)
    inset.set_editor_property("default_value", HOLE_INSET_CM)
    connect(inset, "", hole, "HoleInsetCm")
    if not mel.connect_material_property(hole, "", unreal.MaterialProperty.MP_OPACITY_MASK):
        raise SystemExit("could not connect the mud hole to Opacity Mask")
    log("mud hole: the patch boxes shrunk by %s %.1f cm (one mesh cell), no field textures, the material masked at clip %.3f"
        % (HOLE_INSET_PARAM, HOLE_INSET_CM, m.get_editor_property("opacity_mask_clip_value")))

    # ---- LD2: the OW grass output, keyed on the biome layers' weights -------------------------------------------
    # lab_material()'s pattern (Art/dressing/ported/ClaudeSetupDressingLab.py): a LandscapeLayerSample per layer, the
    # MF3 noise chains (same parameters and defaults) on the masked pins, every pin wired and the wiring gated.
    samples = {}
    for offset, layer_name in enumerate(dict.fromkeys(layer for (_a, _p, layer, _m) in BIOME_GRASS)):
        sample = mel.create_material_expression(m, unreal.MaterialExpressionLandscapeLayerSample, 600, 1600 + 120 * offset)
        sample.set_editor_property("desc", "Landscape:grass_" + layer_name.lower())
        sample.set_editor_property("parameter_name", layer_name)
        sample.set_editor_property("preview_weight", 0.0)
        samples[layer_name] = sample

    def noise_chain(param_name, default_scale, exponent, y):
        wpos = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, 600, y)
        scale = param_scalar(param_name, default_scale, 600, y + 140)
        pos_mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, 780, y)
        connect_exact(wpos, "", pos_mul, "A")
        connect_exact(scale, "", pos_mul, "B")
        noise = mel.create_material_expression(m, unreal.MaterialExpressionNoise, 940, y)
        noise.set_editor_property("scale", 1.0)
        noise.set_editor_property("output_min", 0.0)
        noise.set_editor_property("output_max", 1.0)
        noise.set_editor_property("levels", 2)
        noise.set_editor_property("turbulence", False)
        # UE 5.8 names the pin "World Position"; lab_material() connects "Position" without checking the result.
        connect_exact(pos_mul, "", noise, "World Position")
        power = mel.create_material_expression(m, unreal.MaterialExpressionPower, 1120, y)
        power.set_editor_property("const_exponent", exponent)
        connect_exact(noise, "", power, "Base")
        return power

    patch_mask = noise_chain("OWPatchNoiseScale", 0.0005, 2.0, 3200)
    drift_mask = noise_chain("OWDriftNoiseScale", 0.0003, 2.5, 3500)
    dry_noise = noise_chain("OWDryPatchNoiseScale", 0.0004, 2.0, 3800)
    dry_amount = param_scalar("OWDryPatchAmount", 0.35, 1120, 3960)
    two = mel.create_material_expression(m, unreal.MaterialExpressionConstant, 1120, 4080)
    two.set_editor_property("r", 2.0)
    dry_x2 = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, 1260, 3960)
    connect_exact(dry_amount, "", dry_x2, "A")
    connect_exact(two, "", dry_x2, "B")
    dry_scaled = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, 1380, 3800)
    connect_exact(dry_noise, "", dry_scaled, "A")
    connect_exact(dry_x2, "", dry_scaled, "B")
    dry_mask = mel.create_material_expression(m, unreal.MaterialExpressionSaturate, 1500, 3800)
    connect(dry_scaled, "", dry_mask, "")
    green_mask = mel.create_material_expression(m, unreal.MaterialExpressionOneMinus, 1500, 3920)
    connect(dry_mask, "", green_mask, "")
    pin_masks = {"patch": patch_mask, "drift": drift_mask, "dry": dry_mask, "green": green_mask}

    grass_out = mel.create_material_expression(m, unreal.MaterialExpressionLandscapeGrassOutput, 1700, 1600)
    grass_out.set_editor_property("desc", "Landscape:grass")
    entries = []
    for asset_name, pin, _layer, _mask in BIOME_GRASS:
        lgt = load_or_none(GT_GRASS_PATH + "/" + gt_grass_name(asset_name))
        if lgt is None:
            raise SystemExit("missing grass type " + GT_GRASS_PATH + "/" + gt_grass_name(asset_name)
                             + " (run Art/dressing/gt_grass_copies.bat first)")
        gi = unreal.GrassInput()
        gi.set_editor_property("name", pin)
        gi.set_editor_property("grass_type", lgt)
        entries.append(gi)
    grass_out.set_editor_property("grass_types", entries)
    grass_pins = [str(p) for p in mel.get_material_expression_input_names(grass_out)]
    grass_wired = []
    for index, (asset_name, pin, layer_name, mask_name) in enumerate(BIOME_GRASS):
        weight = samples[layer_name]
        if mask_name is not None:
            pin_mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, 1500, 1600 + 120 * index)
            connect_exact(weight, "", pin_mul, "A")
            connect_exact(pin_masks[mask_name], "", pin_mul, "B")
            weight = pin_mul
        connect_exact(weight, "", grass_out, pin)
        grass_wired.append("%s <- %s%s (%s)" % (pin, layer_name, " x " + mask_name if mask_name else "", gt_grass_name(asset_name)))
    if len(grass_wired) != len(BIOME_GRASS) or len(set(p for (_a, p, _l, _m) in BIOME_GRASS)) != len(BIOME_GRASS):
        raise SystemExit("grass output: %d of %d pins wired" % (len(grass_wired), len(BIOME_GRASS)))
    log("LD2 grass output: %d entries on %d layer samples, pins %s; %s" % (len(entries), len(samples), grass_pins, "; ".join(grass_wired)))

    # ---- LD2: the RVT output - the attributes M_OWDressingLab writes (BaseColor, Roughness, Normal) ------------------
    # The ground's own colour and roughness before the weather (the lab has no weather: its RVT carries the painted
    # ground, and the pack grass tints its blade bases from it), and the vertex normal, as the lab writes.
    rvt_out = mel.create_material_expression(m, unreal.MaterialExpressionRuntimeVirtualTextureOutput, 300, 900)
    rvt_out.set_editor_property("desc", "Landscape:rvt")
    rvt_attributes = []
    for src, out_name, pin in ((colour, "", "BaseColor"), (masks["Roughness"], "", "Roughness"), (vnormal, "", "Normal")):
        connect_exact(src, out_name, rvt_out, pin)
        rvt_attributes.append(pin)
    rvt_asset = load_or_none(BIOME_RVT)
    log("LD2 RVT output: %s (from the colour blend, the roughness blend's R, the vertex normal); the landscape's "
        "RuntimeVirtualTextures names the RVT (%s, %s), not the node"
        % (rvt_attributes, BIOME_RVT, "found" if rvt_asset is not None else "MISSING"))
    if rvt_asset is None:
        raise SystemExit("missing " + BIOME_RVT)
    MATERIAL_FACTS.update({
        "biome_rows": [n for (n, _p) in BIOME_ROWS],
        "rows": len(ROWS),
        "grades": graded,
        "grass_entries": len(entries),
        "grass_layer_samples": len(samples),
        "grass_wired": grass_wired,
        "rvt_attributes": rvt_attributes,
        "rvt": BIOME_RVT,
    })
    # What feeds the weather call now, pin by pin, so a mis-wired blend shows in the log.
    names = [str(n) for n in mel.get_material_expression_input_names(call)]
    feeds = list(mel.get_inputs_for_material_expression(m, call))
    log("weather call inputs %s fed by %s" % (names, [(e.get_name() + ":" + str(e.get_editor_property("desc"))) if e is not None else None for e in feeds]))
    for prop in (unreal.MaterialProperty.MP_BASE_COLOR, unreal.MaterialProperty.MP_ROUGHNESS, unreal.MaterialProperty.MP_NORMAL,
                 unreal.MaterialProperty.MP_OPACITY_MASK):
        node = mel.get_material_property_input_node(m, prop)
        log("%s <- %s.%s" % (prop, node.get_name() if node else None, mel.get_material_property_input_node_output_name(m, prop)))
    errors = [str(e) for e in mel.recompile_material(m)]
    eal.save_loaded_asset(m)
    if errors:
        for error in errors:
            unreal.log_error("SETUP_M6_HIDE " + error)
        raise SystemExit(LANDSCAPE_MATERIAL + " has compile errors")
    MATERIAL_FACTS["samples_after"] = texture_sample_count(m)
    MATERIAL_FACTS["expressions_after"] = mel.get_num_material_expressions(m)
    MATERIAL_FACTS["mpcs_after"], MATERIAL_FACTS["functions_after"] = parameter_collections(m)
    MATERIAL_FACTS["compile_errors"] = errors
    log("LD2 after: %d texture samples in its own graph (before %s), %d expressions, parameter collections %s (before %s) "
        "through the graph and the functions %s (before %s)"
        % (MATERIAL_FACTS["samples_after"], MATERIAL_FACTS.get("samples_before"), MATERIAL_FACTS["expressions_after"],
           MATERIAL_FACTS["mpcs_after"], MATERIAL_FACTS.get("mpcs_before"), MATERIAL_FACTS["functions_after"], MATERIAL_FACTS.get("functions_before")))
    if len(MATERIAL_FACTS["mpcs_after"]) != 2:
        raise SystemExit("%s reads %d parameter collections, not 2: %s" % (LANDSCAPE_MATERIAL, len(MATERIAL_FACTS["mpcs_after"]), MATERIAL_FACTS["mpcs_after"]))
    if MATERIAL_FACTS.get("samples_before") is not None and MATERIAL_FACTS["samples_after"] != MATERIAL_FACTS["samples_before"]:
        raise SystemExit("%s: %d texture samples, was %d (LD2 adds none)" % (LANDSCAPE_MATERIAL, MATERIAL_FACTS["samples_after"], MATERIAL_FACTS["samples_before"]))
    log("%s: a copy of %s with layer blends on BaseColor, Roughness, Porosity and (stage E3) Normal, the Mud and Bog rows "
        "wearing the tri-planar mud maps, masked by the mud hole, the LD2 biome rows, grass and RVT outputs (%d expressions)"
        % (LANDSCAPE_MATERIAL, MASTER, mel.get_num_material_expressions(m)))
    return m


# ---- the water material -------------------------------------------------------------------------
def build_water_material():
    """M_GT_Water: a translucent blue sheet for fords. Its own master: water does not get wet, so it stays outside MF_Weather.

    Water stage W1 (docs/WATER_PLAN.md): the builder moved to Art/Unreal/setup_m6_water.py, which rebuilds the asset
    every run and gives it the flow parameters (FlowDir, FlowSpeed) and the ripple tell. This loads what that script
    built; the create below stays as the fallback for a project where setup_m6_water.bat has never been run.
    """
    full = MAT_PATH + "/" + WATER_MATERIAL
    if eal.does_asset_exist(full):
        log("%s loaded (built by Art/setup_m6_water.bat since W1)" % WATER_MATERIAL)
        return eal.load_asset(full)
    log("%s missing: built here without the flow tell (run Art/setup_m6_water.bat for it)" % WATER_MATERIAL)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    m = tools.create_asset(WATER_MATERIAL, MAT_PATH, unreal.Material, unreal.MaterialFactoryNew())
    if m is None:
        raise SystemExit("could not create " + full)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("two_sided", True)
    colour = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -500, -200)
    colour.set_editor_property("parameter_name", "BaseColor")
    colour.set_editor_property("default_value", unreal.LinearColor(0.08, 0.18, 0.22, 1.0))
    rough = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -500, 0)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.05)
    opacity = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -500, 200)
    opacity.set_editor_property("parameter_name", "Opacity")
    opacity.set_editor_property("default_value", 0.65)
    mel.connect_material_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    errors = [str(e) for e in mel.recompile_material(m)]
    eal.save_loaded_asset(m)
    if errors:
        for error in errors:
            unreal.log_error("SETUP_M6_HIDE " + error)
        raise SystemExit(WATER_MATERIAL + " has compile errors")
    log("%s created (translucent, its own master)" % WATER_MATERIAL)
    return m


# ---- the level ---------------------------------------------------------------------------------------
def box(world, label, x, y, z, sx, sy, sz, material=None, mesh=None, yaw=0.0):
    transform = unreal.Transform(unreal.Vector(x, y, z), rot(yaw=yaw), unreal.Vector(sx, sy, sz))
    actor = lib.spawn_static_mesh_actor(world, mesh or cube, transform, label)
    if actor is None:
        raise SystemExit("could not spawn " + label)
    if material is not None:
        actor.get_editor_property("static_mesh_component").set_material(0, material)
    return actor


def spawn(world, cls, label, x, y, z, yaw=0.0):
    actor = lib.spawn_actor_of_class(world, cls, unreal.Transform(unreal.Vector(x, y, z), rot(yaw=yaw), unreal.Vector(1, 1, 1)), label)
    if actor is None:
        raise SystemExit("could not spawn " + label)
    return actor


def place_ford_sheet(world, spec, index, section, water_material):
    """An AGTWaterSheet over a Ford section: its level, its flow, no collision. Shared by The Hide and the Proving Ground."""
    start_m, end_m = section.get_editor_property("start_m"), section.get_editor_property("end_m")
    level = lib.terrain_ford_water_level_cm(spec, index)
    p, yaw = lib.terrain_route_point_cm(spec, (start_m + end_m) * 0.5)
    # An AGTWaterSheet (stage 3): the car reads its level; the weather lifts it. Scaled and coloured like the old slab.
    sheet = spawn(world, unreal.GTWaterSheet, "Water_%d" % index, p.x, p.y, level, yaw=yaw)
    sheet.set_actor_scale3d(unreal.Vector((end_m - start_m) + 24.0, 30.0, 0.1))
    sheet.set_editor_property("base_level_cm", level)
    # Water stage WS1 (docs/WATER_PLAN.md): the engine cube is hidden by AGTWaterSheet's own constructor and
    # the surface is a procedural grid at the cells of the sheet's shallow-water field, which loads
    # M_GT_Water by path at runtime. The cube's material is set anyway so a project whose C++ predates WS1
    # still shows water, and the check below is what says the material exists at all.
    sheet.get_editor_property("static_mesh_component").set_material(0, water_material)
    sheet.get_editor_property("static_mesh_component").set_visibility(False)
    # No collision at all: the car drives through the water, traces reach the bed.
    sheet.get_editor_property("static_mesh_component").set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sheet.get_editor_property("static_mesh_component").set_collision_profile_name("NoCollision")
    sheet.set_actor_enable_collision(False)
    # Water stage W1: the current. The flow's yaw is the section's mid-route heading plus FlowYawOffsetDeg;
    # Unreal's yaw turns clockwise seen from above, so heading + 90 is the car's right and the default 90 runs
    # the water across the crossing from the driver's left to his right.
    flow_speed_mps = section.get_editor_property("flow_speed_mps")
    flow_yaw = yaw + section.get_editor_property("flow_yaw_offset_deg")
    sheet.set_editor_property("flow_direction", unreal.Vector2D(math.cos(math.radians(flow_yaw)), math.sin(math.radians(flow_yaw))))
    sheet.set_editor_property("flow_speed_cm_per_s", flow_speed_mps * 100.0)
    log("ford %d: water at %.1f m over %.0f-%.0f m, flow %.2f m/s at yaw %.0f (route yaw %.0f + offset %.0f), fade %.0f m at each end; "
        "WS1 field %.1f cm cells with a head drop of %.1f cm, surface mesh built at BeginPlay (the cube is hidden)"
        % (index, level / 100.0, start_m, end_m, flow_speed_mps, flow_yaw, yaw,
           section.get_editor_property("flow_yaw_offset_deg"), sheet.get_editor_property("flow_fade_m"),
           sheet.get_editor_property("field_cell_cm"), sheet.get_editor_property("head_drop_cm")))
    return sheet


def upgrade_hide_spec(spec_asset, spec):
    """The Hide's asset upgrades (stage 2, J3): an old DA_Terrain_Hide is brought up to the C++ default where it still has an old number."""
    # Stage 2: the relief needs a 1 m landscape. An asset written when the default was 2 m quads (8 components a side)
    # is upgraded in place (same 2 km extent); every other field the user set is kept.
    if spec.get_editor_property("quad_size_cm") >= 199.0 and spec.get_editor_property("components_per_side") == 8:
        spec.set_editor_property("quad_size_cm", 100.0)
        spec.set_editor_property("components_per_side", 16)
        spec_asset.set_editor_property("spec", spec)
        eal.save_loaded_asset(spec_asset)
        spec = spec_asset.get_editor_property("spec")
        log("spec upgraded to 1 m quads (16 components a side)")
    # Stage 2's rest: the rally road narrowed (RallyWidthScale 1.3 -> 0.75 with verges) and the crests and compressions on
    # the rally sections, taken from the C++ default when the asset still has the old width or a rally section with no
    # bumps; every other field the user set is kept. The new track and rally fields arrive with their C++ defaults.
    default = lib.make_hide_terrain_spec()
    upgraded = []
    if abs(spec.get_editor_property("rally_width_scale") - 1.3) < 1e-3:
        spec.set_editor_property("rally_width_scale", default.get_editor_property("rally_width_scale"))
        upgraded.append("rally width scale %.2f" % default.get_editor_property("rally_width_scale"))
    sections = list(spec.get_editor_property("sections"))
    default_sections = list(default.get_editor_property("sections"))
    for section in sections:
        if section.get_editor_property("kind") != unreal.GTRouteSectionKind.RALLY or len(section.get_editor_property("bumps")) > 0:
            continue
        for candidate in default_sections:
            if candidate.get_editor_property("kind") == unreal.GTRouteSectionKind.RALLY and abs(candidate.get_editor_property("start_m") - section.get_editor_property("start_m")) < 50.0:
                section.set_editor_property("bumps", candidate.get_editor_property("bumps"))
                upgraded.append("%d crests/compressions on the rally section at %.0f m" % (len(candidate.get_editor_property("bumps")), section.get_editor_property("start_m")))
                break
    # Stage J3 (2026-09-16, the user: "the waterline needs to be lowered a bit, maybe by half"): the Mud sections'
    # water table went -20 -> -25 cm in C++ (FGTRouteSection::WaterTableCm). A spec asset saved before that may carry
    # the old number, so any Mud section still reading the old default is moved to the C++ one and every Mud section's
    # table is logged either way - the rebuilt level must have what the header says it has.
    old_water_table_cm = -20.0
    new_water_table_cm = None
    for candidate in default_sections:
        if candidate.get_editor_property("kind") == unreal.GTRouteSectionKind.MUD:
            new_water_table_cm = candidate.get_editor_property("water_table_cm")
            break
    water_tables = []
    for section in sections:
        if section.get_editor_property("kind") != unreal.GTRouteSectionKind.MUD:
            continue
        table = section.get_editor_property("water_table_cm")
        if new_water_table_cm is not None and abs(table - old_water_table_cm) < 1e-3 and abs(new_water_table_cm - old_water_table_cm) > 1e-3:
            section.set_editor_property("water_table_cm", new_water_table_cm)
            upgraded.append("water table %.1f -> %.1f cm on the mud section at %.0f m" % (table, new_water_table_cm, section.get_editor_property("start_m")))
            table = new_water_table_cm
        water_tables.append("%.0f m: %.1f cm" % (section.get_editor_property("start_m"), table))
    log("mud sections' water table (stage J3, the C++ default is %s): %s"
        % ("%.1f cm" % new_water_table_cm if new_water_table_cm is not None else "unknown", ", ".join(water_tables) or "no mud sections"))
    if upgraded:
        spec.set_editor_property("sections", sections)
        spec_asset.set_editor_property("spec", spec)
        eal.save_loaded_asset(spec_asset)
        spec = spec_asset.get_editor_property("spec")
        log("spec upgraded: " + ", ".join(upgraded))
    return spec


def place_hide(world, spec, builder):
    """The Hide's own actors on its ground: the start, the checkpoints, the zone, the bear, the fords' sheets, the posts, the boulders."""
    # A skirt under the landscape's lowest point out to the horizon, so height views end in ground, not the sky's sea.
    mi_dirt = load_or_none(MAT_PATH + "/MI_Env_Dirt")
    box(world, "Floor_Skirt", 70000.0, 0.0, -2200.0, 20000.0, 20000.0, 1.0, material=mi_dirt)   # 20 km square, 22 m down

    def ground(x, y):
        return lib.sample_terrain_height_cm(spec, x, y)

    def route(arc_m):
        point, yaw = lib.terrain_route_point_cm(spec, arc_m)
        return point, yaw

    mi = {name: load_or_none(MAT_PATH + "/MI_Env_" + name) for name in ("Greybox", "Marker")}

    # The car starts on the road, 20 m in.
    start, start_yaw = route(20.0)
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if isinstance(actor, unreal.PlayerStart):
            actor.set_actor_location(unreal.Vector(start.x, start.y, start.z + 150.0), False, False)
            actor.set_actor_rotation(rot(yaw=start_yaw), False)

    # Checkpoints across the road at (500, 0) and (1100, 40), turned to it; the zone at (1400, 0); the leg start.
    for index, (x, y) in enumerate(((500.0, 0.0), (1100.0, 40.0)), start=1):
        dist, arc = lib.terrain_route_distance_m(spec, x * 100.0, y * 100.0)
        _p, yaw = route(arc)
        cp = spawn(world, unreal.GTCheckpoint, "Checkpoint_%d" % index, x * 100.0, y * 100.0, ground(x * 100.0, y * 100.0) + 250.0, yaw=yaw)
        cp.set_editor_property("index", index)
        cp.set_editor_property("extent", unreal.Vector(150, 1500, 500))
    ex = spawn(world, unreal.GTExtractionZone, "Extraction_A", 140000.0, 0.0, ground(140000.0, 0.0) + 250.0)
    ex.set_editor_property("extent", unreal.Vector(1000, 1000, 500))
    ls = spawn(world, unreal.GTLegStart, "LegStart_A", start.x, start.y, start.z)
    ls.set_editor_property("leg_asset_path", LEG_FOLDER + "/DA_Leg_03")

    # The radiation pocket on the plateau with one cache; the bear in its dell beside it, ringed by boulders.
    zx, zy = 70000.0, 12000.0
    zone = spawn(world, unreal.GTRadiationZone, "Zone_Radiation_A", zx, zy, ground(zx, zy) + 600.0)
    zone.set_editor_property("extent", unreal.Vector(2500, 2500, 600))
    cache = spawn(world, unreal.GTHarvestNode, "Node_Cache_0", 69000.0, 12500.0, ground(69000.0, 12500.0) + 30.0)
    cache.set_editor_property("node_name", "alloy cache")
    cache.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_RadiationCache")
    cache.set_editor_property("uses", 2)
    cache.set_editor_property("colour", unreal.LinearColor(0.3, 0.9, 0.35, 1.0))
    bx, by = 73500.0, 15000.0
    bear = spawn(world, unreal.GTPhotoSubject, "Subject_A", bx, by, ground(bx, by) + 100.0, yaw=200.0)
    bear.set_editor_property("subject_name", "spectacled bear")
    rng = random.Random(7)
    for index in range(9):
        angle = math.radians(index * 40.0 + 20.0)
        if 100.0 < math.degrees(angle) < 150.0:
            continue   # the way in, from the road side
        r = 2000.0 + rng.uniform(-150.0, 250.0)
        x, y = bx + math.cos(angle) * r, by + math.sin(angle) * r
        size = rng.uniform(2.2, 4.0)
        box(world, "Hide_%d" % index, x, y, ground(x, y) + size * 35.0, size, size * rng.uniform(0.7, 1.1), size * 0.8, material=mi["Greybox"], mesh=sphere, yaw=rng.uniform(0, 360))

    # Cable bundles and a wreck beside the road; a steel post by the crossing.
    for index, (arc, side) in enumerate(((250.0, 14.0), (1250.0, -16.0))):
        p, yaw = route(arc)
        nx, ny = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        x, y = p.x + nx * side * 100.0, p.y + ny * side * 100.0
        node = spawn(world, unreal.GTHarvestNode, "Node_Cable_%d" % index, x, y, ground(x, y) + 30.0)
        node.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_CableBundle")
    p, yaw = route(880.0)
    nx, ny = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    wx, wy = p.x + nx * -1700.0, p.y + ny * -1700.0
    wreck = spawn(world, unreal.GTWreck, "Wreck_0", wx, wy, ground(wx, wy) + 55.0, yaw=yaw + 15.0)
    wreck.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_Wreck")
    # The route's sections: winch posts either side of a bog's far end (the answer to it), a water sheet over a ford.
    posts = 0
    water_material = build_water_material()
    for index, section in enumerate(spec.get_editor_property("sections")):
        kind = section.get_editor_property("kind")
        start_m, end_m = section.get_editor_property("start_m"), section.get_editor_property("end_m")
        if kind == unreal.GTRouteSectionKind.MUD:
            p, yaw = route(end_m)
            nx, ny = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
            for side in (-1, 1):
                px, py = p.x + nx * side * 1100.0, p.y + ny * side * 1100.0
                post = spawn(world, unreal.GTWinchAnchor, "Post_Bog_%d_%d" % (index, side), px, py, ground(px, py))
                post.get_anchor().set_editor_property("strength_n", 200000.0)
                post.get_anchor().set_editor_property("display_name", "steel post")
                posts += 1
        elif kind == unreal.GTRouteSectionKind.FORD:
            place_ford_sheet(world, spec, index, section, water_material)
    # And one post by the ford's exit for the stuck.
    p, yaw = route(1150.0)
    nx, ny = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    px, py = p.x + nx * 1200.0, p.y + ny * 1200.0
    post = spawn(world, unreal.GTWinchAnchor, "Post_Ford", px, py, ground(px, py))
    post.get_anchor().set_editor_property("strength_n", 200000.0)
    post.get_anchor().set_editor_property("display_name", "steel post")
    posts += 1

    # Boulders off the road and the detour, never on them, thicker where the ground is steep.
    placed = 0
    tries = 0
    while placed < 140 and tries < 3000:
        tries += 1
        x = rng.uniform(-20000.0, 160000.0)
        y = rng.uniform(-40000.0, 40000.0)
        dist, _arc = lib.terrain_route_distance_m(spec, x, y)
        if dist < 26.0 or math.hypot(x - bx, y - by) < 3500.0 or lib.terrain_layer_at(spec, x, y) != 4:
            continue
        slope = lib.terrain_slope_degrees(spec, x, y)
        if rng.random() > 0.12 + 0.88 * min(slope / 25.0, 1.0):
            continue
        size = rng.uniform(1.5, 5.0)
        box(world, "Rock_%d" % placed, x, y, ground(x, y) + size * 30.0, size, size * rng.uniform(0.6, 1.2), size * rng.uniform(0.5, 0.9), material=mi["Greybox"], mesh=sphere, yaw=rng.uniform(0, 360))
        placed += 1
    log("%d winch posts, %d boulders (%d tries)" % (posts, placed, tries))
    return {"witness": bear, "witness_name": "bear", "min_regrounded": 70,
            "summary": "landscape, the leg's actors on it, %d boulders; start at (%.0f, %.0f, %.0f) yaw %.0f; bear at %.0f m above sea level" % (
                placed, start.x, start.y, start.z, start_yaw, ground(bx, by) / 100.0)}


def build_level(material, level_path=LEVEL_PATH, spec_name=HIDE_SPEC_NAME, write_spec=None, place=None, builder_xyz=(0.0, -3000.0, 500.0)):
    """One path for every generated map: load it, clear the props, write (or keep) the spec asset, build the landscape through the
    builder, place the map's actors (place(world, spec, builder), The Hide's by default), rebuild once more as the button does
    and check the witness came back to its height, save. The Hide passes nothing; setup_m6_proving.py passes its own."""
    if not eal.does_asset_exist(level_path):
        raise SystemExit("missing " + level_path + " (run setup_m5_legs.bat first)")
    if not les.load_level(level_path):
        raise SystemExit("could not load " + level_path)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    removed = sum(lib.destroy_actors_with_label_prefix(world, prefix) for prefix in PROP_PREFIXES)
    log("removed %d old props (the flat floor among them)" % removed)

    # The spec is an asset the user edits (kept across re-runs); the builder actor in the map rebuilds from it with a
    # button, and this script drives the same function so the headless build and the button share one path.
    reset = os.environ.get("GT_RESET_SPEC", "0") == "1"
    write_spec = write_spec or (lambda r: lib.create_terrain_spec_assets(TERRAIN_PATH, r))
    if write_spec(reset) < 1:
        raise SystemExit("could not write " + spec_name)
    log("spec asset %s" % ("reset to the C++ default" if reset else "kept if it existed"))
    spec_asset = eal.load_asset(TERRAIN_PATH + "/" + spec_name)
    builder = None
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if isinstance(actor, unreal.GTTerrainBuilder):
            builder = actor
            break
    if builder is None:
        builder = spawn(world, unreal.GTTerrainBuilder, "TerrainBuilder", builder_xyz[0], builder_xyz[1], builder_xyz[2])
    builder.set_editor_property("spec_asset", spec_asset)
    builder.set_editor_property("landscape_material_path", MAT_PATH + "/" + LANDSCAPE_MATERIAL)
    landscape = builder.rebuild_landscape()
    if landscape is None:
        raise SystemExit("the landscape did not build: " + str(builder.get_editor_property("last_message")))
    log("builder: %s | %s" % (builder.get_editor_property("last_message"), spec_asset.describe()))
    spec = spec_asset.get_editor_property("spec")
    if place is None:
        spec = upgrade_hide_spec(spec_asset, spec)
        result = place_hide(world, spec, builder)
    else:
        result = place(world, spec, builder)

    # The button's path once more with everything placed: the landscape is thrown away and rebuilt, and every actor
    # must come back at the height it had (the witness: The Hide's bear, a winch post on the Proving Ground).
    witness = result["witness"]
    witness_before = witness.get_actor_location()
    if builder.rebuild_landscape() is None:
        raise SystemExit("the second rebuild failed: " + str(builder.get_editor_property("last_message")))
    witness_after = witness.get_actor_location()
    regrounded = builder.get_editor_property("last_regrounded")
    log("second rebuild: %s; %s z %.1f -> %.1f" % (builder.get_editor_property("last_message"), result["witness_name"], witness_before.z, witness_after.z))
    dressing = builder.get_editor_property("dressing")
    log("dressing: %s" % (dressing.get_editor_property("last_message") if dressing is not None else "none"))
    # A trace against the old landscape's collision differs from the generated height by a centimetre or two.
    if regrounded < result["min_regrounded"] or abs(witness_after.z - witness_before.z) > 5.0:
        raise SystemExit("the rebuild did not put the actors back where they were")

    if not les.save_current_level():
        raise SystemExit("could not save " + level_path)
    log("saved %s: %s" % (level_path, result["summary"]))


# setup_m6_proving.py imports this file with GT_M6_AS_MODULE=1 and drives build_level itself.
# GT_M6_STEP (LD2, 2026-09-27; Art/dressing/ld2_landscape_material.bat): "all" (the default) builds the material and
# The Hide; "material" builds M_GT_Landscape alone and touches no map. GT_M6_REPORT names a report JSON (per-step ok).
def write_report(steps):
    path = os.environ.get("GT_M6_REPORT", "")
    if path:
        with open(path, "w") as f:
            json.dump({"ok": all(s.get("ok") for s in steps.values()), "steps": steps}, f, indent=2, default=str)


if os.environ.get("GT_M6_AS_MODULE", "0") != "1":
    run_step = (os.environ.get("GT_M6_STEP", "") or "all").strip().lower()
    report = {}
    try:
        if run_step not in ("all", "material"):
            raise SystemExit("GT_M6_STEP must be all or material, not %r" % run_step)
        report["material"] = {"ok": False}
        material = build_landscape_material()
        report["material"] = dict(MATERIAL_FACTS, ok=True)
        if run_step == "all":
            report["level"] = {"ok": False}
            build_level(material)
            report["level"] = {"ok": True}
        write_report(report)
        log("DONE (GT_M6_STEP=%s)" % run_step)
    except BaseException as error:
        failed = next((k for k, v in report.items() if not v.get("ok")), "setup")
        report[failed] = dict(MATERIAL_FACTS, ok=False, error=str(error)) if failed == "material" else {"ok": False, "error": str(error)}
        write_report(report)
        raise
