"""LM2b + LM2c (docs/LIVING_MUD_PLAN.md): import the clods Art/Blender/build_mud_clods.py exported (LM2c: ten in four families).

Run with & Art/import_mud_clods.ps1 (it refuses with a game or the editor open). Imports every clod in
Art/Export/MudClods/manifest.json (SM_GT_Clod_0..9.fbx) as /Game/GrandTour/Mud/Clods/SM_GT_Clod_0..9: no collision, Nanite off, no
lightmap UVs, the FBX's normals; M_GT_Clod on slot 0 when Art/Unreal/live_mud_style.py has built it (the live setup
assigns it again either way). AGTMudPatch loads the meshes by path at runtime; without them it draws no clods.
Writes Art/Export/MudClods/import-report.json.
"""
import unreal as u, json, traceback
from pathlib import Path
ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/MudClods'
DEST = '/Game/GrandTour/Mud/Clods'
MATERIAL = '/Game/GrandTour/Materials/M_GT_Clod'
eal = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
report = {'ok': False, 'meshes': []}
try:
    data = json.loads((OUT / 'manifest.json').read_text())
    sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    material = eal.load_asset(MATERIAL) if eal.does_asset_exist(MATERIAL) else None
    for row in data['clods']:
        name = row['name']
        task = u.AssetImportTask()
        task.filename = str(OUT / (name + '.fbx'))
        task.destination_path = DEST
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = True
        opt = u.FbxImportUI()
        opt.import_mesh = True
        opt.import_as_skeletal = False
        opt.import_materials = False
        opt.import_textures = False
        opt.import_animations = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        opt.static_mesh_import_data.combine_meshes = True
        opt.static_mesh_import_data.auto_generate_collision = False
        opt.static_mesh_import_data.generate_lightmap_u_vs = False
        opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options = opt
        assets.import_asset_tasks([task])
        mesh = eal.load_asset(DEST + '/' + name)
        assert mesh, name
        # No collision (the patch's HISM has none either) and Nanite off.
        try:
            sm.remove_collisions(mesh)
        except Exception:
            report.setdefault('collision_notes', []).append(name + ': ' + traceback.format_exc().splitlines()[-1])
        ns = mesh.get_editor_property('nanite_settings')
        ns.enabled = False
        sm.set_nanite_settings(mesh, ns, True)
        if material:
            mesh.set_material(0, material)
        eal.save_loaded_asset(mesh)
        bounds = mesh.get_bounds()
        size = [round(bounds.box_extent.x * 2, 2), round(bounds.box_extent.y * 2, 2), round(bounds.box_extent.z * 2, 2)]
        assert 8.0 < max(size[0], size[1]) < 12.0, (name, size)   # 10 cm across: the FBX came in in centimetres
        tris = None
        for reader in (lambda: mesh.get_num_triangles(0), lambda: sm.get_number_triangles(mesh, 0)):
            try:
                tris = int(reader())
                break
            except Exception:
                pass
        report['meshes'].append(dict(asset=mesh.get_path_name(), family=row.get('family'), source_triangles=row['triangles'], triangles=tris, size_cm=size,
                                     nanite=False, simple_collision=sm.get_simple_collision_count(mesh), material=material.get_path_name() if material else None))
    report['ok'] = len(report['meshes']) == len(data['clods'])
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'import-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
