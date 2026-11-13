"""MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block item 1): import the mud chunks Art/Blender/build_mud_chunks.py
exported (six, each with its UCX_ hull).

Run with & Art/import_mud_chunks.ps1 (it refuses with the editor open; -AllowGame runs it with a game open). The clods' import
(Art/Unreal/import_mud_clods.py) with these differences: every chunk in Art/Export/MudChunks/manifest.json
(SM_GT_MudChunk_0..5.fbx) comes in as /Game/GrandTour/Mud/Chunks/SM_GT_MudChunk_0..5 with its one convex hull kept as the simple
collision (the chunks simulate); a UGTMudChunkData on each carries the manifest's numbers (family, the closed-mesh volume, the
hull's volume, the embed height, the across), which AGTMudPatch reads for a break's deposit and the mass. Nanite off, no lightmap
UVs, the FBX's normals; M_GT_MudChunk on slot 0 when Art/Unreal/live_mud_style.py has built it (the live setup assigns it again
either way). Writes Art/Export/MudChunks/import-report.json.
"""
import unreal as u, json, traceback
from pathlib import Path
ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/MudChunks'
DEST = '/Game/GrandTour/Mud/Chunks'
MATERIAL = '/Game/GrandTour/Materials/M_GT_MudChunk'
eal = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
report = {'ok': False, 'meshes': []}


def put_chunk_data(mesh, row):
    """The manifest's numbers as a UGTMudChunkData on the mesh (replacing any earlier one)."""
    data = u.new_object(u.GTMudChunkData, mesh)
    data.set_editor_property('family', row['family'])
    data.set_editor_property('volume_cm3', float(row['volume_cm3']))
    data.set_editor_property('hull_volume_cm3', float(row['hull_volume_cm3']))
    data.set_editor_property('embed_cm', float(row['embed_cm']))
    data.set_editor_property('across_cm', float(row['across_cm']))
    try:
        kept = [d for d in (mesh.get_editor_property('asset_user_data') or []) if d and not isinstance(d, u.GTMudChunkData)]
        mesh.set_editor_property('asset_user_data', kept + [data])
        how = 'asset_user_data'
    except Exception:
        # Fallback: the interface's own call, then its object's numbers.
        mesh.add_asset_user_data_of_class(u.GTMudChunkData)
        data = mesh.get_asset_user_data_of_class(u.GTMudChunkData)
        for key in ('family', 'volume_cm3', 'hull_volume_cm3', 'embed_cm', 'across_cm'):
            data.set_editor_property(key, row[key] if key == 'family' else float(row[key]))
        how = 'add_asset_user_data_of_class'
    back = mesh.get_asset_user_data_of_class(u.GTMudChunkData)
    assert back and abs(back.get_editor_property('volume_cm3') - float(row['volume_cm3'])) < 0.01, (row['name'], how)
    return how


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
        # True: the import takes collision at all - under Interchange (5.8's FBX path) False drops the UCX_ hull too; with a UCX_ in
        # the file it is used as the simple collision (by its name), nothing generated.
        opt.static_mesh_import_data.auto_generate_collision = True
        opt.static_mesh_import_data.one_convex_hull_per_ucx = True
        opt.static_mesh_import_data.generate_lightmap_u_vs = False
        opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options = opt
        assets.import_asset_tasks([task])
        mesh = eal.load_asset(DEST + '/' + name)
        assert mesh, name
        ns = mesh.get_editor_property('nanite_settings')
        ns.enabled = False
        sm.set_nanite_settings(mesh, ns, True)
        if material:
            mesh.set_material(0, material)
        how = put_chunk_data(mesh, row)
        eal.save_loaded_asset(mesh)
        bounds = mesh.get_bounds()
        size = [round(bounds.box_extent.x * 2, 2), round(bounds.box_extent.y * 2, 2), round(bounds.box_extent.z * 2, 2)]
        bottom = round(bounds.origin.z - bounds.box_extent.z, 2)
        assert abs(max(size[0], size[1]) - row['across_cm']) < 1.5, (name, size, row['across_cm'])   # the FBX came in in centimetres
        convex = sm.get_convex_collision_count(mesh)
        assert convex == 1, (name, 'convex hulls', convex)   # its UCX_ hull, one
        tris = None
        for reader in (lambda: mesh.get_num_triangles(0), lambda: sm.get_number_triangles(mesh, 0)):
            try:
                tris = int(reader())
                break
            except Exception:
                pass
        report['meshes'].append(dict(asset=mesh.get_path_name(), family=row.get('family'), source_triangles=row['triangles'], triangles=tris, size_cm=size,
                                     bottom_cm=bottom, embed_cm=row['embed_cm'], volume_cm3=row['volume_cm3'], hull_volume_cm3=row['hull_volume_cm3'],
                                     hull_vertices=row['hull_vertices'], nanite=False, simple_collision=sm.get_simple_collision_count(mesh), convex=convex,
                                     chunk_data=how, material=material.get_path_name() if material else None))
    report['ok'] = len(report['meshes']) == len(data['chunks'])
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'import-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
