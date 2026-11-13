"""setup_m6_textures.py - imports the CC0 mud texture set (docs/MUD_ONE_SURFACE_PLAN.md, stage E1) and the CC0
water ripple normal (docs/WATER_PLAN.md, stage W4).

The water half (stage W4): "Rain Ripples on Puddle" (others_0028) by TextureCan.com, licence CC0 1.0 Universal,
2K, downloaded with curl into Art/Textures/Water/rain_ripples/ - the whole provenance is in
Art/Textures/Water/SOURCE.txt, which also records why ambientCG, Poly Haven, 3dtextures.me and OpenGameArt are not
the source. The set ships the DirectX-convention normal (green down), which is what Unreal wants, so it is imported
as T_GT_Water_N with TC_Normalmap, sRGB off and NO green flip, into /Game/GrandTour/Textures/Water.
M_GT_Water (Art/Unreal/setup_m6_water.py) reads only its RG as a slope, and refuses to build without it.

Run with Art\\setup_m6_textures.bat (close the editor first; run it before setup_m6_mud.py, which is what will
sample these textures in stage E2). No painting, no generation: the maps are sourced from Poly Haven.
- The set: "Muddy Tracks" (muddy_tracks) by Amal Kumar, Poly Haven, licence CC0 (public domain, no attribution
  required). 2K, downloaded with curl into Art/Textures/Mud/muddy_tracks/ (the thumbnails of the candidates that
  were compared are in Art/Textures/Mud/). Picked as the thumbnail nearest a churned wet dirt track: dark wet
  brown with directional smeared ruts, no leaves, no grass, no cracked dry clay.
- Imported with unreal.AssetImportTask into /Game/GrandTour/Textures/Mud as T_GT_Mud_Diffuse (TC_Default, sRGB on),
  T_GT_Mud_Normal (the _nor_dx file, DirectX convention, so TC_Normalmap with sRGB off and the green channel NOT
  flipped), T_GT_Mud_Rough and T_GT_Mud_Disp (TC_Masks, sRGB off). Each texture's source size on disk, its
  resolution and its settings are logged with the SETUP_M6_TEXTURES prefix.
- The diffuse map's mean colour in LINEAR space is logged as "mean colour r g b". It is the divisor of stage E2's
  tint (lerp(GroundColor, BogColor, bog) / TextureMeanColor), so the textured mud keeps the landscape's tone.
  Unreal's Python has no PIL and the diffuse is a JPG, which plain Python cannot decode, so the .bat measures it
  first with a PowerShell System.Drawing pass (a 256 x 256 grid of original pixels, each linearised through the
  sRGB EOTF, then averaged) and writes muddy_tracks_mean.json beside the sources; this script reads that file.
Safe to re-run: every texture is re-imported over the existing asset and saved.
"""
import json
import os

import unreal

PROJECT_DIR = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())

DEST = "/Game/GrandTour/Textures/Mud"
SET_NAME = "muddy_tracks"
SOURCE_DIR = os.path.join(PROJECT_DIR, "Art", "Textures", "Mud", SET_NAME)
MEAN_JSON = os.path.join(SOURCE_DIR, SET_NAME + "_mean.json")
LICENCE = "muddy_tracks (Muddy Tracks) by Amal Kumar, Poly Haven, CC0"

# Water stage W4: the ripple normal the ford's surface wears.
WATER_DEST = "/Game/GrandTour/Textures/Water"
WATER_SET = "rain_ripples"
WATER_SOURCE_DIR = os.path.join(PROJECT_DIR, "Art", "Textures", "Water", WATER_SET)
WATER_LICENCE = ("others_0028 (Rain Ripples on Puddle) by TextureCan.com, CC0 1.0 Universal "
                 "(https://www.texturecan.com/details/531/); see Art/Textures/Water/SOURCE.txt")

TC = unreal.TextureCompressionSettings

# file in SOURCE_DIR, asset name, compression, sRGB, what it is
MAPS = [
    ("muddy_tracks_diff_2k.jpg", "T_GT_Mud_Diffuse", TC.TC_DEFAULT, True, "diffuse / albedo"),
    ("muddy_tracks_nor_dx_2k.png", "T_GT_Mud_Normal", TC.TC_NORMALMAP, False, "normal, DirectX (_nor_dx)"),
    ("muddy_tracks_rough_2k.png", "T_GT_Mud_Rough", TC.TC_MASKS, False, "roughness"),
    ("muddy_tracks_disp_2k.png", "T_GT_Mud_Disp", TC.TC_MASKS, False, "displacement / height"),
]

# The painterly ground sets (the user, 2026-09-20: "bring some painterly textures in"), both CC0 from
# 3dtextures.me; the whole provenance, including why these two of the site's five stylised ground sets, is in
# Art/Textures/Stylised/SOURCE.txt. The Scrub row (the ground away from any road) wears the grass, the Dirt row
# (every leg's road) the dry mud; the Mud and Bog rows keep the photoreal muddy_tracks set. The normals are
# imported but nothing samples them yet - Art/Unreal/setup_m6_hide.py takes the albedo and the roughness only.
STYLISED_DEST = "/Game/GrandTour/Textures/Stylised"
STYLISED_DIR = os.path.join(PROJECT_DIR, "Art", "Textures", "Stylised")
STYLISED_LICENCE = ("Stylized Grass 002 and Stylized Dry Mud 001 by Katsukagi, 3dtextures.me, CC0 "
                    "(\"All textures on this site are licensed as CC0\", https://3dtextures.me/about/); "
                    "see Art/Textures/Stylised/SOURCE.txt")

# The same, for the water set. Only the normal is wanted: the ford's colour and opacity come from the field's own
# depth (stage W4's whole point), not from a photograph of a puddle.
WATER_MAPS = [
    ("others_0028_normal_directx_2k.png", "T_GT_Water_N", TC.TC_NORMALMAP, False,
     "water ripple normal, DirectX convention (no green flip)"),
]


STYLISED_MAPS = [
    ("stylized_grass_002", "Stylized_Grass_002_basecolor.jpg", "T_GT_Grass_D", TC.TC_DEFAULT, True, "painterly grass, albedo (the Scrub row)"),
    ("stylized_grass_002", "Stylized_Grass_002_roughness.jpg", "T_GT_Grass_R", TC.TC_MASKS, False, "painterly grass, roughness"),
    ("stylized_grass_002", "Stylized_Grass_002_normal.jpg", "T_GT_Grass_N", TC.TC_NORMALMAP, False, "painterly grass, normal (imported, not sampled yet)"),
    ("stylized_dry_mud_001", "Stylized_Dry_Mud_001_basecolor.jpg", "T_GT_Dirt_D", TC.TC_DEFAULT, True, "painterly dry mud, albedo (the Dirt row)"),
    ("stylized_dry_mud_001", "Stylized_Dry_Mud_001_roughness.jpg", "T_GT_Dirt_R", TC.TC_MASKS, False, "painterly dry mud, roughness"),
    ("stylized_dry_mud_001", "Stylized_Dry_Mud_001_normal.jpg", "T_GT_Dirt_N", TC.TC_NORMALMAP, False, "painterly dry mud, normal (imported, not sampled yet)"),
]


def log(msg):
    unreal.log("SETUP_M6_TEXTURES " + msg)


def log_error(msg):
    unreal.log_error("SETUP_M6_TEXTURES " + msg)


def enum_name(value):
    """TextureCompressionSettings.TC_MASKS -> 'TC_Masks'-ish; never raises."""
    try:
        return str(value.name)
    except Exception:
        return str(value)


def texture_size(tex):
    """(x, y) of the imported texture, by whichever accessor this build exposes."""
    try:
        return int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())
    except Exception:
        pass
    try:
        p = tex.get_editor_property("imported_size")
        return int(p.x), int(p.y)
    except Exception:
        pass
    return 0, 0


def import_one(file_name, asset_name, compression, srgb, what, source_dir=None, dest=None):
    source_dir = source_dir or SOURCE_DIR
    dest = dest or DEST
    path = os.path.join(source_dir, file_name)
    if not os.path.isfile(path):
        log_error("missing source " + path + " (download it with curl from the source in that folder's SOURCE.txt, 2K)")
        return None
    mb = os.path.getsize(path) / (1024.0 * 1024.0)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", asset_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)  # saved below, after the settings are on
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    asset_path = dest + "/" + asset_name
    tex = unreal.EditorAssetLibrary.load_asset(asset_path)
    if tex is None:
        log_error("import produced no asset at " + asset_path + " from " + file_name)
        return None

    tex.set_editor_property("compression_settings", compression)
    tex.set_editor_property("srgb", srgb)
    if compression == TC.TC_NORMALMAP:
        # Poly Haven's _nor_dx file and TextureCan's _directx one are already DirectX convention (green down),
        # which is what Unreal wants. 3dtextures.me states no convention and Substance Designer exports OpenGL by
        # default, so the stylised sets are flipped - unchecked, and nothing samples them yet (SOURCE.txt says so).
        flip = dest == STYLISED_DEST
        try:
            tex.set_editor_property("flip_green_channel", flip)
        except Exception:
            log("note: flip_green_channel not settable on this build; wanted flip=%s for %s" % (flip, asset_name))
    try:
        tex.post_edit_change()   # set_editor_property already fires PostEditChangeProperty; this rebuilds the platform data
    except Exception as error:
        log("note: post_edit_change unavailable on this build (%s); the settings were applied by set_editor_property" % error)
    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)

    x, y = texture_size(tex)
    log("%s <- %s: %d x %d, source %.2f MB, %s, sRGB %s (%s)"
        % (asset_path, file_name, x, y, mb, enum_name(compression), srgb, what))
    return tex


def mean_colour():
    """The diffuse map's mean colour in linear space, measured by the .bat's PowerShell pass."""
    if not os.path.isfile(MEAN_JSON):
        log_error("no " + MEAN_JSON + ": run Art\\setup_m6_textures.bat, which measures it before this script. "
                  "Stage E2's TextureMeanColor has no value to take.")
        return None
    try:
        with open(MEAN_JSON, "r") as handle:
            data = json.load(handle)
    except Exception as error:
        log_error("could not read " + MEAN_JSON + ": " + str(error))
        return None
    rgb = data.get("mean_linear")
    if not rgb or len(rgb) != 3:
        log_error("no mean_linear in " + MEAN_JSON)
        return None
    log("mean colour %.6f %.6f %.6f" % (float(rgb[0]), float(rgb[1]), float(rgb[2])))
    log("mean colour measured over %s samples of %s (sRGB 0-255 mean %s); it is stage E2's TextureMeanColor"
        % (data.get("samples"), os.path.basename(str(data.get("source", ""))), data.get("mean_srgb_255")))
    return rgb


def run():
    log("licence: " + LICENCE)
    log("sources in " + SOURCE_DIR + ", importing into " + DEST)
    if not unreal.EditorAssetLibrary.does_directory_exist(DEST):
        unreal.EditorAssetLibrary.make_directory(DEST)
    done = 0
    for file_name, asset_name, compression, srgb, what in MAPS:
        if import_one(file_name, asset_name, compression, srgb, what) is not None:
            done += 1
    mean_colour()
    log("imported %d of %d mud maps" % (done, len(MAPS)))
    if done != len(MAPS):
        log_error("not every mud map imported; see the lines above")

    # ---- the painterly ground sets (2026-09-20) ----
    log("stylised licence: " + STYLISED_LICENCE)
    log("stylised sources in " + STYLISED_DIR + ", importing into " + STYLISED_DEST)
    if not unreal.EditorAssetLibrary.does_directory_exist(STYLISED_DEST):
        unreal.EditorAssetLibrary.make_directory(STYLISED_DEST)
    stylised_done = 0
    for set_name, file_name, asset_name, compression, srgb, what in STYLISED_MAPS:
        if import_one(file_name, asset_name, compression, srgb, what,
                      source_dir=os.path.join(STYLISED_DIR, set_name), dest=STYLISED_DEST) is not None:
            stylised_done += 1
    log("imported %d of %d stylised ground maps" % (stylised_done, len(STYLISED_MAPS)))
    if stylised_done != len(STYLISED_MAPS):
        log_error("not every stylised map imported; M_GT_Landscape will refuse to build without "
                  + STYLISED_DEST + "/T_GT_Grass_D")

    # ---- water stage W4: the ripple normal ----
    log("water licence: " + WATER_LICENCE)
    log("water sources in " + WATER_SOURCE_DIR + ", importing into " + WATER_DEST)
    if not unreal.EditorAssetLibrary.does_directory_exist(WATER_DEST):
        unreal.EditorAssetLibrary.make_directory(WATER_DEST)
    water_done = 0
    for file_name, asset_name, compression, srgb, what in WATER_MAPS:
        if import_one(file_name, asset_name, compression, srgb, what,
                      source_dir=WATER_SOURCE_DIR, dest=WATER_DEST) is not None:
            water_done += 1
    log("imported %d of %d water maps" % (water_done, len(WATER_MAPS)))
    if water_done != len(WATER_MAPS):
        log_error("not every water map imported; M_GT_Water will refuse to build without "
                  + WATER_DEST + "/T_GT_Water_N")


run()
