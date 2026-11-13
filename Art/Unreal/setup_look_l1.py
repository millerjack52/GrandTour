"""setup_look_l1.py - the Unreal half of Look stage L1 (docs/LOOK_PLAN.md L1, docs/VEHICLE_BUILD_SYSTEM.md section 55).

Run with Art\\setup_look_l1.bat (close the editor first; it writes .uasset files). For every folder Art/Export/<Asset>/
holding the GT Paint addon's three outputs - SM_<Asset>.fbx, T_GT_<Asset>_D.png and T_GT_<Asset>_M.png - it:
- imports the FBX as a static mesh into /Game/GrandTour/Props/Painted with import_rangerover.py's make_task settings
  (no materials, no textures, scene and unit conversion, combined meshes, auto collision), generalised to any asset;
- imports the bake into /Game/GrandTour/Textures/Painted on setup_m6_textures.py's conventions (AssetImportTask,
  replace, then the settings, post_edit_change, save): _D as TC_Default with sRGB on (its alpha only marks the painted
  texels, so compression_no_alpha), _M as TC_Masks with sRGB off (R wear, G grime, B roughness, linear);
- builds M_GT_Painted once (/Game/GrandTour/Materials): BaseColor = lerp(Albedo, white, Masks.R x WearLighten) x
  (1 - Masks.G x GrimeDarken), Roughness = Masks.B, and (follow-up 2) Normal = the painted-dab _N - no specular or
  emissive tricks: the lighting is L2's post layer's. WearLighten and GrimeDarken default to 0 because the bake already carries its wear and
  grime as paint; they add on top and are the owner's to name. Plus M_GT_PaintedGrey, the plain grey "before"
  material for the pictures (BaseColor 0.214 linear = sRGB 128, Roughness 0.85);
- makes MI_GT_Painted_<Asset> (/Game/GrandTour/Materials/Painted) with the asset's textures and puts it on every
  material slot of the imported mesh.
Follow-up 2 (2026-09-24): T_GT_<Asset>_N.png, the painted-dab normal GT Paint gets from the owner's OW Painterly
Normal Baker (its DirectX file), comes in as TC_Normalmap, sRGB off, NO green flip (the project's convention,
setup_m6_textures.py); M_GT_Painted takes it on the Normal pin: normalize(lerp((0,0,1), Normal, NormalStrength)),
NormalStrength 1 (proposed, unmeasured), no specular tricks. An asset without an _N gets the engine's flat normal
(logged). A folder with bakes but no SM_<Asset>.fbx (the owner's own bakes of single parts) is skipped by this first
pass with one line.
Follow-up 3 (2026-09-24), the second pass: the owner's panel bakes on the driven car. For every Art/Export/<Asset>/ with
T_GT_<Asset>_D.png and NO SM_<Asset>.fbx whose name is a panel in /Game/GrandTour/Vehicles/Bodies/RangeRover/Panels
(SM_RR_<Asset>_L/_R or SM_RR_<Asset>; a bake of one Blender object keeps that object's UV, and export_rangerover.py
splits a mirrored object into its _L/_R halves), _D (sRGB), _M (TC_Masks, linear) and _N (TC_Normalmap, if present)
come into /Game/GrandTour/Vehicles/Bodies/RangeRover/Paint as T_GT_<Asset>_D/_M/_N, over the earlier import (a stale
_N is deleted when the new bake has none). No mesh import. One line per panel: painted / no bake / no such panel / no
UV. The UV gate: a panel mesh whose UV0 has no area (it came in without a UV map: every vertex at 0,0, as the 2026-09-11
car export did) cannot carry any bake, so nothing is imported for it and an earlier import is removed - the car keeps
UsePaint 0 there until the Blender object has a UV map, the car is re-exported and re-imported, and it is baked again. The
car keeps M_GT_Vehicle (runtime dirt, wetness, dents, clear coat; setup_m1_body.py's painted path behind UsePaint):
UGTBodyComponent sets the textures on each panel's instance and UsePaint 1. The Range Rover's meshes (Art/Export/
SK_RangeRover.fbx + Static/) are never touched here.
Safe to re-run: every asset is re-imported over the existing one. Log prefix SETUP_LOOK_L1.
"""
import os

import unreal

PROJECT_DIR = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
EXPORT_DIR = os.path.join(PROJECT_DIR, "Art", "Export")
MESH_DEST = "/Game/GrandTour/Props/Painted"
TEX_DEST = "/Game/GrandTour/Textures/Painted"
MAT = "/Game/GrandTour/Materials"
MI_DEST = MAT + "/Painted"
MASTER = "M_GT_Painted"
GREY = "M_GT_PaintedGrey"
GREY_LINEAR = 0.214      # sRGB 128
GREY_ROUGHNESS = 0.85
NORMAL_STRENGTH = 0.5    # follow-up 2: 1 = the painted normal as baked; 0.5 mirrors the preset's normal_strength by hand (2026-09-24); proposed, unmeasured
FLAT_NORMAL = "/Engine/EngineMaterials/FlatNormal"
# Follow-up 3: the driven car's panel bakes.
PANEL_DIR = "/Game/GrandTour/Vehicles/Bodies/RangeRover/Panels"
PANEL_PREFIX = "SM_RR_"
PANEL_SKIP = ("Wheel",)   # UGTBodyComponent's SkipPanels: the wheels are bones, not panels
PAINT_DEST = "/Game/GrandTour/Vehicles/Bodies/RangeRover/Paint"

TC = unreal.TextureCompressionSettings
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log("SETUP_LOOK_L1 " + msg)


def log_error(msg):
    unreal.log_error("SETUP_LOOK_L1 " + msg)


def find_assets():
    """[(asset, folder)] for every Art/Export/<Asset>/ with the mesh and both bakes; the rest are reported and skipped
    (a folder with no SM_<Asset>.fbx - a bake the owner has not exported - with one skip line, not an error)."""
    found = []
    if not os.path.isdir(EXPORT_DIR):
        log_error("no " + EXPORT_DIR)
        return found
    for name in sorted(os.listdir(EXPORT_DIR)):
        folder = os.path.join(EXPORT_DIR, name)
        if not os.path.isdir(folder):
            continue
        files = ["SM_%s.fbx" % name, "T_GT_%s_D.png" % name, "T_GT_%s_M.png" % name]
        present = [f for f in files if os.path.isfile(os.path.join(folder, f))]
        if not present:
            log("skipped Art/Export/%s/: not a GT Paint export (no %s)" % (name, " / ".join(files)))
            continue
        if files[0] not in present:
            log("skip Art/Export/%s/: no %s (bakes without an export: %s), no prop imported (the panel pass below "
                "takes it if it names a car panel)" % (name, files[0], ", ".join(present)))
            continue
        if len(present) != len(files):
            log_error("Art/Export/%s/ is missing %s: bake and export it again from the GT Paint panel"
                      % (name, ", ".join(f for f in files if f not in present)))
            continue
        found.append((name, folder))
    return found


def mesh_task(path, dest, name):
    """import_rangerover.py's make_task for a static mesh, with the asset's own name."""
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path)
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("create_physics_asset", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    d = ui.get_editor_property("static_mesh_import_data")
    d.set_editor_property("import_uniform_scale", 1.0)
    d.set_editor_property("convert_scene", True)
    d.set_editor_property("force_front_x_axis", False)
    d.set_editor_property("convert_scene_unit", True)
    d.set_editor_property("combine_meshes", True)
    d.set_editor_property("auto_generate_collision", True)
    d.set_editor_property("generate_lightmap_u_vs", False)
    t.set_editor_property("options", ui)
    return t


def texture_size(tex):
    try:
        return int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())
    except Exception:
        return 0, 0


def import_texture(path, asset_name, compression, srgb, no_alpha, what, flip_green=None, dest=TEX_DEST):
    mb = os.path.getsize(path) / (1024.0 * 1024.0)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", asset_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)   # saved below, after the settings are on
    tools.import_asset_tasks([task])
    full = dest + "/" + asset_name
    tex = eal.load_asset(full)
    if tex is None:
        log_error("import produced no texture at " + full)
        return None
    tex.set_editor_property("compression_settings", compression)
    tex.set_editor_property("srgb", srgb)
    if flip_green is not None:
        tex.set_editor_property("flip_green_channel", flip_green)
    try:
        tex.set_editor_property("compression_no_alpha", no_alpha)
    except Exception:
        log("note: compression_no_alpha not settable on this build (%s)" % asset_name)
    try:
        tex.post_edit_change()
    except Exception as error:
        log("note: post_edit_change unavailable on this build (%s); the settings were applied by set_editor_property" % error)
    eal.save_asset(full, only_if_is_dirty=False)
    x, y = texture_size(tex)
    log("%s <- %s: %d x %d, source %.2f MB, %s, sRGB %s, no alpha %s%s (%s)"
        % (full, os.path.basename(path), x, y, mb, compression.name, srgb, no_alpha,
           "" if flip_green is None else ", flip green %s" % tex.get_editor_property("flip_green_channel"), what))
    return tex


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
    names = [str(n) for n in mel.get_material_expression_input_names(dst)]
    for alt in names:
        if alt != in_name and mel.connect_material_expressions(src, out_name, dst, alt):
            return
    raise SystemExit("could not connect %s.%r -> %s.%r (inputs: %s)" % (src.get_name(), out_name, dst.get_name(), in_name, names))


def compile_or_die(material):
    errors = [str(e) for e in mel.recompile_material(material)]
    eal.save_loaded_asset(material)
    if errors:
        for error in errors:
            log_error("compile error in %s: %s" % (material.get_name(), error))
        raise SystemExit(material.get_name() + " failed to compile")
    log("%s compiled" % material.get_name())


def expr(material, cls, x, y):
    return mel.create_material_expression(material, cls, x, y)


def scalar(material, name, value, x, y):
    e = expr(material, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", value)
    return e


def texture_param(material, name, texture, sampler, x, y):
    e = expr(material, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("texture", texture)
    e.set_editor_property("sampler_type", sampler)
    return e


def build_grey():
    m = fresh_material(GREY)
    colour = expr(m, unreal.MaterialExpressionConstant3Vector, -400, 0)
    colour.set_editor_property("constant", unreal.LinearColor(GREY_LINEAR, GREY_LINEAR, GREY_LINEAR, 1.0))
    rough = expr(m, unreal.MaterialExpressionConstant, -400, 150)
    rough.set_editor_property("r", GREY_ROUGHNESS)
    mel.connect_material_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    compile_or_die(m)
    return m


def build_master(default_d, default_m, default_n):
    m = fresh_material(MASTER)
    albedo = texture_param(m, "Albedo", default_d, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -1100, -200)
    masks = texture_param(m, "Masks", default_m, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, -1100, 150)
    # Follow-up 2: the painted-dab normal. normalize(lerp((0,0,1), sampled, NormalStrength)): 0 = flat, 1 = as baked.
    normal = texture_param(m, "Normal", default_n, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -1100, 600)
    strength = scalar(m, "NormalStrength", NORMAL_STRENGTH, -800, 750)
    flat = expr(m, unreal.MaterialExpressionConstant3Vector, -800, 550)
    flat.set_editor_property("constant", unreal.LinearColor(0.0, 0.0, 1.0, 1.0))
    towards = expr(m, unreal.MaterialExpressionLinearInterpolate, -550, 600)
    connect(flat, "", towards, "A")
    connect(normal, "RGB", towards, "B")
    connect(strength, "", towards, "Alpha")
    unit = expr(m, unreal.MaterialExpressionNormalize, -350, 600)
    connect(towards, "", unit, "VectorInput")
    mel.connect_material_property(unit, "", unreal.MaterialProperty.MP_NORMAL)
    wear_lighten = scalar(m, "WearLighten", 0.0, -800, 350)
    grime_darken = scalar(m, "GrimeDarken", 0.0, -800, 450)
    white = expr(m, unreal.MaterialExpressionConstant3Vector, -700, -100)
    white.set_editor_property("constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    wear_amount = expr(m, unreal.MaterialExpressionMultiply, -600, 250)
    connect(masks, "R", wear_amount, "A")
    connect(wear_lighten, "", wear_amount, "B")
    lit = expr(m, unreal.MaterialExpressionLinearInterpolate, -400, -150)
    connect(albedo, "RGB", lit, "A")
    connect(white, "", lit, "B")
    connect(wear_amount, "", lit, "Alpha")
    grime_amount = expr(m, unreal.MaterialExpressionMultiply, -600, 400)
    connect(masks, "G", grime_amount, "A")
    connect(grime_darken, "", grime_amount, "B")
    keep = expr(m, unreal.MaterialExpressionOneMinus, -400, 400)
    connect(grime_amount, "", keep, "Input")
    base = expr(m, unreal.MaterialExpressionMultiply, -200, 0)
    connect(lit, "", base, "A")
    connect(keep, "", base, "B")
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(masks, "B", unreal.MaterialProperty.MP_ROUGHNESS)
    compile_or_die(m)
    return m


def make_instance(asset, master, tex_d, tex_m, tex_n):
    name = "MI_GT_Painted_" + asset
    full = MI_DEST + "/" + name
    inst = eal.load_asset(full) if eal.does_asset_exist(full) else None
    if inst is None:
        inst = tools.create_asset(name, MI_DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        if inst is None:
            raise SystemExit("could not create " + full)
    mel.set_material_instance_parent(inst, master)
    mel.set_material_instance_texture_parameter_value(inst, "Albedo", tex_d)
    mel.set_material_instance_texture_parameter_value(inst, "Masks", tex_m)
    mel.set_material_instance_texture_parameter_value(inst, "Normal", tex_n)
    mel.update_material_instance(inst)
    eal.save_loaded_asset(inst)
    log("%s: parent %s, Albedo %s, Masks %s, Normal %s" % (full, master.get_name(), tex_d.get_name(), tex_m.get_name(),
                                                           tex_n.get_name()))
    return inst


def import_props():
    assets = find_assets()
    log("%d GT Paint export(s) in %s: %s" % (len(assets), EXPORT_DIR, ", ".join(a for a, _ in assets) or "none"))
    if not assets:
        log("no prop to import: bake and export an asset from the GT Paint panel first (or bash Art/blender_test.sh)")
        return
    for path in (MESH_DEST, TEX_DEST, MI_DEST):
        if not eal.does_directory_exist(path):
            eal.make_directory(path)

    textures = {}
    for asset, folder in assets:
        tex_d = import_texture(os.path.join(folder, "T_GT_%s_D.png" % asset), "T_GT_%s_D" % asset, TC.TC_DEFAULT, True, True,
                               "painted albedo, unlit")
        tex_m = import_texture(os.path.join(folder, "T_GT_%s_M.png" % asset), "T_GT_%s_M" % asset, TC.TC_MASKS, False, False,
                               "mask: R wear, G grime, B roughness")
        if tex_d is None or tex_m is None:
            continue
        n_path = os.path.join(folder, "T_GT_%s_N.png" % asset)
        if os.path.isfile(n_path):
            tex_n = import_texture(n_path, "T_GT_%s_N" % asset, TC.TC_NORMALMAP, False, False,
                                   "painted-dab normal, DirectX (the OW Painterly Normal Baker's _DX file)", flip_green=False)
        else:
            tex_n = None
            log("%s: no T_GT_%s_N.png (a bake with normal_enable false): the engine's flat normal" % (asset, asset))
        if tex_n is None:
            tex_n = eal.load_asset(FLAT_NORMAL)
            if tex_n is None:
                log_error("%s: no _N and no %s" % (asset, FLAT_NORMAL))
                continue
        textures[asset] = (tex_d, tex_m, tex_n)

    tasks = [(asset, mesh_task(os.path.join(folder, "SM_%s.fbx" % asset), MESH_DEST, "SM_" + asset))
             for asset, folder in assets if asset in textures]
    tools.import_asset_tasks([t for _, t in tasks])

    grey = build_grey()
    first = next(iter(textures.values()))
    master = build_master(first[0], first[1], first[2])
    done = 0
    for asset, task in tasks:
        full = MESH_DEST + "/SM_" + asset
        mesh = eal.load_asset(full)
        if mesh is None:
            log_error("the FBX import produced no static mesh at " + full + " (imported: %s)"
                      % [str(p) for p in task.get_editor_property("imported_object_paths")])
            continue
        inst = make_instance(asset, master, *textures[asset])
        slots = len(mesh.get_editor_property("static_materials"))
        for i in range(slots):
            mesh.set_material(i, inst)
        eal.save_loaded_asset(mesh)
        b = mesh.get_bounds()
        try:
            tris = int(mesh.get_num_triangles(0))
        except Exception:
            tris = -1
        log("%s: %d material slot(s) -> %s, bounds %.0f x %.0f x %.0f cm, lowest point z %.0f cm, %d LOD0 triangles"
            % (full, slots, inst.get_name(), b.box_extent.x * 2, b.box_extent.y * 2, b.box_extent.z * 2,
               b.origin.z - b.box_extent.z, tris))
        done += 1
    log("grey 'before' material %s/%s; master %s/%s" % (MAT, grey.get_name(), MAT, master.get_name()))
    log("done: %d of %d asset(s) imported, textured and given their instance" % (done, len(assets)))
    if done != len(assets):
        log_error("not every asset made it; see the lines above")


def car_panels():
    """{asset: [panel mesh names]} for the driven car: SM_RR_<Asset>_L/_R and SM_RR_<Asset> under PANEL_DIR, keyed the
    way UGTBodyComponent looks a bake up (the name after the prefix, a trailing _L/_R stripped)."""
    panels = {}
    for path in eal.list_assets(PANEL_DIR, recursive=False, include_folder=False):
        name = path.rsplit("/", 1)[-1].split(".")[0]
        if not name.startswith(PANEL_PREFIX):
            continue
        rest = name[len(PANEL_PREFIX):]
        if rest.startswith(PANEL_SKIP):
            continue
        asset = rest[:-2] if rest.endswith(("_L", "_R")) else rest
        panels.setdefault(asset, []).append(name)
    return panels


def panel_uv(mesh_name):
    """(UV0 area, distinct UV0 values) over a car panel's LOD0 triangles: (0, 1) when the mesh came in without a UV."""
    sm = eal.load_asset(PANEL_DIR + "/" + mesh_name)
    if sm is None:
        return 0.0, 0
    desc = sm.get_static_mesh_description(0)
    seen = set()
    area = 0.0
    for t in range(desc.get_triangle_count()):
        p = [desc.get_vertex_instance_uv(v, 0) for v in desc.get_triangle_vertex_instances(unreal.TriangleID(t))]
        seen.update((round(q.x, 4), round(q.y, 4)) for q in p)
        area += abs((p[1].x - p[0].x) * (p[2].y - p[0].y) - (p[2].x - p[0].x) * (p[1].y - p[0].y)) / 2.0
    return area, len(seen)


def remove_panel_textures(asset, suffixes=("D", "M", "N")):
    """Deletes this pass's own earlier T_GT_<asset>_D/_M/_N imports from PAINT_DEST; returns their names. In the
    commandlet delete_asset logs "Force Deleting" but leaves the .uasset on disk (2026-09-24), so the file goes too."""
    removed = []
    folder = os.path.join(PROJECT_DIR, "Content", *PAINT_DEST.split("/")[2:])
    for suffix in suffixes:
        name = "T_GT_%s_%s" % (asset, suffix)
        full = PAINT_DEST + "/" + name
        path = os.path.join(folder, name + ".uasset")
        if not eal.does_asset_exist(full) and not os.path.isfile(path):
            continue
        if eal.does_asset_exist(full):
            eal.delete_asset(full)
        if os.path.isfile(path):
            unreal.SystemLibrary.collect_garbage()
            try:
                os.remove(path)
            except OSError as error:
                log_error("could not delete %s (%s): delete it by hand, or the car keeps wearing it" % (path, error))
                continue
        removed.append(name)
    return removed


def import_panel_bakes():
    """Follow-up 3: Art/Export/<Asset>/ with T_GT_<Asset>_D.png, no SM_<Asset>.fbx and a car panel of that name -> the
    textures in PAINT_DEST. One line per panel (painted / no bake) and per unmatched bake folder (no such panel)."""
    panels = car_panels()
    bakes = {}
    for name in (sorted(os.listdir(EXPORT_DIR)) if os.path.isdir(EXPORT_DIR) else []):
        folder = os.path.join(EXPORT_DIR, name)
        if not os.path.isdir(folder) or os.path.isfile(os.path.join(folder, "SM_%s.fbx" % name)):
            continue
        if os.path.isfile(os.path.join(folder, "T_GT_%s_D.png" % name)):
            bakes[name] = folder
    log("panel pass: %d car panel name(s) in %s, %d panel bake folder(s) (a _D and no FBX): %s"
        % (len(panels), PANEL_DIR, len(bakes), ", ".join(sorted(bakes)) or "none"))
    if bakes and not eal.does_directory_exist(PAINT_DEST):
        eal.make_directory(PAINT_DEST)
    painted = []
    for asset in sorted(set(panels) | set(bakes)):
        meshes = ", ".join(panels.get(asset, []))
        if asset not in bakes:
            stale = eal.does_asset_exist(PAINT_DEST + "/T_GT_%s_D" % asset)
            log("panel %s (%s): no bake%s" % (asset, meshes, " (an earlier import's T_GT_%s_D in %s still paints it)"
                                                               % (asset, PAINT_DEST) if stale else ""))
            continue
        if asset not in panels:
            log("panel bake Art/Export/%s/: no such panel (no %s%s_L/_R or %s%s in %s), nothing imported"
                % (asset, PANEL_PREFIX, asset, PANEL_PREFIX, asset, PANEL_DIR))
            continue
        no_uv = [(mesh,) + panel_uv(mesh) for mesh in panels[asset]]
        no_uv = [f for f in no_uv if f[1] < 1e-6]
        if no_uv:
            removed = remove_panel_textures(asset)
            log("panel %s (%s): no UV - %s: the bake (on its own UV) cannot lie on it, nothing imported%s. Give the Blender "
                "object a UV map, re-export and re-import the car (Art/export_rangerover.bat, Art/import_rangerover.bat), bake "
                "it again (GT Paint keeps a single object's UV) and rerun Art/setup_look_l1.bat"
                % (asset, meshes, ", ".join("%s UV0 area %.4f, %d distinct UV(s)" % f for f in no_uv),
                   "; the earlier import's %s removed (UsePaint stays 0)" % ", ".join(removed) if removed else ""))
            continue
        folder = bakes[asset]
        m_path = os.path.join(folder, "T_GT_%s_M.png" % asset)
        if not os.path.isfile(m_path):
            log_error("panel %s (%s): T_GT_%s_D.png but no T_GT_%s_M.png: bake and export it again, nothing imported"
                      % (asset, meshes, asset, asset))
            continue
        tex_d = import_texture(os.path.join(folder, "T_GT_%s_D.png" % asset), "T_GT_%s_D" % asset, TC.TC_DEFAULT, True,
                               True, "panel albedo", dest=PAINT_DEST)
        tex_m = import_texture(m_path, "T_GT_%s_M" % asset, TC.TC_MASKS, False, False,
                               "panel mask: R wear, G grime, B roughness", dest=PAINT_DEST)
        if tex_d is None or tex_m is None:
            continue
        n_path = os.path.join(folder, "T_GT_%s_N.png" % asset)
        if os.path.isfile(n_path):
            tex_n = import_texture(n_path, "T_GT_%s_N" % asset, TC.TC_NORMALMAP, False, False,
                                   "panel painted-dab normal, DirectX", flip_green=False, dest=PAINT_DEST)
            normal = tex_n.get_name() if tex_n else "the _N import FAILED"
        else:
            normal = "no _N (M_GT_Vehicle's flat default)"
            stale = remove_panel_textures(asset, ("N",))
            if stale:
                normal += "; the earlier import's %s deleted" % stale[0]
        painted.append(asset)
        log("panel %s (%s): painted - %s, %s, %s" % (asset, meshes, tex_d.get_name(), tex_m.get_name(), normal))
    log("panel pass done: %d painted (%s)" % (len(painted), ", ".join(painted) or "none"))


def run():
    import_props()
    import_panel_bakes()


run()
