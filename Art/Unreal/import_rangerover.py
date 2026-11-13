"""import_rangerover.py - import Art/Export into the GrandTour project, headless.

Run via Art\\import_rangerover.bat (close the Unreal editor first, it writes .uasset files):
    UnrealEditor-Cmd.exe GrandTour.uproject -run=pythonscript -script=Art/Unreal/import_rangerover.py
        -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI

Imports SK_RangeRover.fbx as a skeletal mesh (+ skeleton) into DEST and every Static/*.fbx
as a static mesh into DEST/Panels, replacing existing assets of the same name. Afterwards it
lists assets in DEST/Panels that the current export did not produce (stale names after a
rename in Blender) so you can delete them in the editor.
"""
import glob
import os

import unreal

PROJECT = unreal.Paths.project_dir()
SRC = os.path.join(PROJECT, "Art", "Export")
DEST = "/Game/GrandTour/Vehicles/Bodies/RangeRover"
PANELS = DEST + "/Panels"


def make_task(path, dest, skeletal):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path)
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", skeletal)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("create_physics_asset", skeletal)
    ui.set_editor_property("mesh_type_to_import",
                           unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeletal
                           else unreal.FBXImportType.FBXIT_STATIC_MESH)
    d = ui.get_editor_property("skeletal_mesh_import_data" if skeletal else "static_mesh_import_data")
    d.set_editor_property("import_uniform_scale", 1.0)
    d.set_editor_property("convert_scene", True)
    d.set_editor_property("force_front_x_axis", False)
    d.set_editor_property("convert_scene_unit", True)
    if skeletal:
        d.set_editor_property("import_morph_targets", False)
    else:
        d.set_editor_property("combine_meshes", True)
        d.set_editor_property("auto_generate_collision", True)
        d.set_editor_property("generate_lightmap_u_vs", False)
    t.set_editor_property("options", ui)
    return t


sk_file = os.path.join(SRC, "SK_RangeRover.fbx")
static_files = sorted(glob.glob(os.path.join(SRC, "Static", "*.fbx")))
if not os.path.isfile(sk_file):
    raise SystemExit("missing " + sk_file + " (run Art/export_rangerover.bat first)")

tasks = [make_task(sk_file, DEST, True)] + [make_task(f, PANELS, False) for f in static_files]
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

imported = []
for t in tasks:
    for p in t.get_editor_property("imported_object_paths"):
        imported.append(str(p))
        unreal.log("imported " + str(p))

expected = {os.path.splitext(os.path.basename(f))[0] for f in static_files}
reg = unreal.AssetRegistryHelpers.get_asset_registry()
stale = [str(a.asset_name) for a in reg.get_assets_by_path(PANELS, recursive=False)
         if str(a.asset_name) not in expected]
sk = unreal.load_asset(DEST + "/SK_RangeRover")
if sk:
    b = sk.get_bounds()
    unreal.log("SK_RangeRover bounds extent (cm): %.0f x %.0f x %.0f" %
               (b.box_extent.x * 2, b.box_extent.y * 2, b.box_extent.z * 2))
unreal.log("IMPORT_DONE: %d assets" % len(imported))
if stale:
    unreal.log_warning("STALE assets in %s not produced by this export: %s" % (PANELS, ", ".join(stale)))
