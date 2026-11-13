"""Ground relief GR2 phase B item 1 (docs/GROUND_RELIEF_PLAN.md GR2): the phase A/A2 ground detail into Unreal. Repeatable.
- The bakes (Art/Export/GroundDetailGR2/T_GD_<Set><Channel>.png, Art/Blender/bake_ground_detail_gr2.py) into
  /Game/GrandTour/ArtTests/GroundDetail/TA_GD_{Color,Normal,ORH}: slice 0 ScrubSoil, slice 1 SoilUnderGrass; Color sRGB (BC1), Normal
  linear BC5 (DirectX green, as baked), ORH linear BC7 (R horizon AO, G roughness 0.6-0.95, B the parallax height with soft rims);
  wrapped, the World group, at most 2048 - the mud's array builder (import_gravel_dg1.py's route: Texture2DArrayFactory, then
  UGTMudArtLibrary::BuildTextureArray).
- The scatter meshes SM_GD_Clod0-5, Pebble0-3, Litter0-3, Twig0-2, TussockBase0-2 from their FBX: vertex colour (replaced from the FBX),
  imported normals, no collision, no Nanite; each wears its family's instance of M_GT_GroundScatter (ground_detail.build_scatter_material).
- MPC_TrackPaint's GroundDetail scalar (gt.Ground.Detail, UGTTrackPaintSubsystem writes it), default 1.
Writes Art/Export/GroundDetailGR2/import-report.json. Run with & Art/ground_detail_gr2.ps1 -Step import.
"""
import json
import sys
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
import ground_detail as gd   # noqa: E402

SRC = ROOT / 'Art/Export/GroundDetailGR2'
OUT = SRC
SLICES = gd.DEST + '/Bakes'
SETS = ['ScrubSoil', 'SoilUnderGrass']   # slice 0, slice 1
TC = u.TextureCompressionSettings
CHANNELS = {'Color': dict(srgb=True, compression=TC.TC_DEFAULT), 'Normal': dict(srgb=False, compression=TC.TC_NORMALMAP),
            'ORH': dict(srgb=False, compression=TC.TC_BC7)}
eal = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
report = {'ok': False, 'slices': [], 'arrays': [], 'meshes': []}


def settings(tex, channel):
    c = CHANNELS[channel]
    tex.set_editor_property('srgb', c['srgb'])
    tex.set_editor_property('compression_settings', c['compression'])
    if channel == 'Normal':
        tex.set_editor_property('flip_green_channel', False)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WORLD)
    tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    tex.set_editor_property('max_texture_size', 2048)


def import_textures():
    u.SystemLibrary.execute_console_command(None, 'r.AllowTexture2DArrayCreation 1')
    tasks = []
    for channel in CHANNELS:
        for name in SETS:
            asset = 'T_GD_%s%s' % (name, channel)
            path = SRC / (asset + '.png')
            assert path.exists(), 'no %s (Art/Blender/bake_ground_detail_gr2.py bakes it)' % path
            task = u.AssetImportTask()
            task.filename = str(path)
            task.destination_path = SLICES
            task.destination_name = asset
            task.automated = True
            task.replace_existing = True
            task.save = False
            tasks.append(task)
    assets.import_asset_tasks(tasks)
    slices = {}
    for channel in CHANNELS:
        for name in SETS:
            asset = 'T_GD_%s%s' % (name, channel)
            tex = eal.load_asset(SLICES + '/' + asset)
            assert tex, 'the import made no ' + asset
            settings(tex, channel)
            for axis in ('address_x', 'address_y'):
                tex.set_editor_property(axis, u.TextureAddress.TA_WRAP)
            eal.save_loaded_asset(tex)
            slices.setdefault(channel, []).append(tex)
            report['slices'].append(dict(asset=tex.get_path_name(), size=[tex.blueprint_get_size_x(), tex.blueprint_get_size_y()],
                                         srgb=bool(tex.get_editor_property('srgb')), compression=str(tex.get_editor_property('compression_settings'))))
    for channel, textures in slices.items():
        name = 'TA_GD_' + channel
        path = gd.DEST + '/' + name
        created = False
        arr = eal.load_asset(path) if eal.does_asset_exist(path) else None
        if arr is None:
            arr = assets.create_asset(name, gd.DEST, u.Texture2DArray, u.Texture2DArrayFactory())
            created = True
        assert arr, 'Texture2DArrayFactory made no %s (r.AllowTexture2DArrayCreation?)' % path
        settings(arr, channel)
        for axis in ('address_x', 'address_y', 'address_z'):
            try:
                arr.set_editor_property(axis, u.TextureAddress.TA_WRAP if axis != 'address_z' else u.TextureAddress.TA_CLAMP)
            except Exception as error:
                report.setdefault('address_errors', []).append('%s %s: %s' % (name, axis, error))
        try:
            arr.set_editor_property('source_textures', [])
            arr.set_editor_property('source_textures', textures)
        except Exception as error:
            report.setdefault('python_route_errors', []).append('%s: %s' % (name, error))
        built, message = u.GTMudArtLibrary.build_texture_array(arr, textures)
        assert built == len(SETS), '%s: BuildTextureArray %s (%s)' % (name, built, message)
        settings(arr, channel)
        assert eal.save_loaded_asset(arr), 'could not save ' + path
        n, sx, sy = u.GTMudArtLibrary.texture_array_source_slices(arr)
        assert (n, sx, sy) == (len(SETS), 2048, 2048), '%s: %d slices of %d x %d' % (name, n, sx, sy)
        report['arrays'].append(dict(asset=arr.get_path_name(), created=created, slices=[t.get_name() for t in textures], rebuilt=message,
                                     source_slices=n, size=[sx, sy], srgb=bool(arr.get_editor_property('srgb')),
                                     compression=str(arr.get_editor_property('compression_settings'))))


def import_meshes(materials):
    manifest = json.loads((SRC / 'manifest.json').read_text())
    sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for row in manifest['scatter']:
        name = row['name']
        task = u.AssetImportTask()
        task.filename = str(ROOT / row['fbx'])
        task.destination_path = gd.DEST
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        opt = u.FbxImportUI()
        opt.import_mesh = True
        opt.import_as_skeletal = False
        opt.import_materials = False
        opt.import_textures = False
        opt.import_animations = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        data = opt.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.generate_lightmap_u_vs = False
        data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options = opt
        assets.import_asset_tasks([task])
        mesh = eal.load_asset(gd.DEST + '/' + name)
        assert mesh, 'the import made no ' + name
        family = gd.family_of(name)
        mesh.set_material(0, materials[family])
        ns = mesh.get_editor_property('nanite_settings')
        ns.enabled = False
        sm.set_nanite_settings(mesh, ns, True)
        body = mesh.get_editor_property('body_setup')
        if body is not None:
            body.set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
            try:
                sm.remove_collisions(mesh)
            except Exception:
                pass
        eal.save_loaded_asset(mesh)
        box = mesh.get_bounding_box()
        size_cm = [round(box.max.x - box.min.x, 2), round(box.max.y - box.min.y, 2), round(box.max.z - box.min.z, 2)]
        want = [round(100 * v, 2) for v in row['size_m']]
        assert all(abs(a - b) <= max(0.5, 0.05 * b) for a, b in zip(size_cm, want)), '%s: units? %s cm against the manifest %s cm' % (name, size_cm, want)
        report['meshes'].append(dict(name=name, family=family, triangles=row['triangles'], size_cm=size_cm, min_z_cm=round(box.min.z, 2),
                                     material=materials[family].get_name(), vertex_colour='replaced from the FBX', collision='none', nanite=False))


try:
    report['mpc'] = gd.ensure_mpc()
    import_textures()
    report['scatter_material'] = gd.build_scatter_material()
    materials = {fam: eal.load_asset(gd.DEST + '/' + mi) for fam, mi in gd.SCATTER_MI.items()}
    import_meshes(materials)
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'import-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
