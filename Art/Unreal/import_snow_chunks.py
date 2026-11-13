"""LM4 item 4 (docs/LIVING_MUD_PLAN.md LM4): import the snow shards Art/Blender/build_snow_chunks.py exported (eight).
LM4b item 3: the same names now carry LM4b's rounded, lumpy snow clumps (5-18 cm, smooth shaded); the import is unchanged.

Run with & Art/import_snow_chunks.ps1 (it refuses with a game or the editor open). Imports every shard in
Art/Export/SnowChunks/manifest.json (SM_GT_SnowChunk_0..7.fbx) as /Game/GrandTour/Mud/SnowChunks/SM_GT_SnowChunk_0..7 on the
clods' import (Art/Unreal/import_mud_clods.py): no collision, Nanite off, no lightmap UVs, the FBX's normals (flat shaded:
every face sharp); M_GT_Clod_Snow on slot 0 when Art/Unreal/live_snow_style.py has built it. AGTMudPatch loads them by
path at runtime and a snow patch draws them in place of the clods. Writes Art/Export/SnowChunks/import-report.json.
"""
import unreal as u, json, traceback
from pathlib import Path
ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/SnowChunks'
DEST = '/Game/GrandTour/Mud/SnowChunks'
MATERIAL = '/Game/GrandTour/Materials/M_GT_Clod_Snow'
eal = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
report = {'ok': False, 'meshes': []}
try:
    data = json.loads((OUT / 'manifest.json').read_text())
    sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    material = eal.load_asset(MATERIAL) if eal.does_asset_exist(MATERIAL) else None
    for row in data['chunks']:
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
        # The FBX came in in centimetres: its across within a centimetre of the manifest's.
        assert abs(max(size[0], size[1]) - row['across_cm']) < 1.5, (name, size, row['across_cm'])
        tris = None
        for reader in (lambda: mesh.get_num_triangles(0), lambda: sm.get_number_triangles(mesh, 0)):
            try:
                tris = int(reader())
                break
            except Exception:
                pass
        report['meshes'].append(dict(asset=mesh.get_path_name(), source_triangles=row['triangles'], triangles=tris, size_cm=size, across_cm=row['across_cm'],
                                     thickness_cm=row['thickness_cm'], nanite=False, simple_collision=sm.get_simple_collision_count(mesh),
                                     material=material.get_path_name() if material else None))
    report['ok'] = len(report['meshes']) == len(data['chunks'])
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'import-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
