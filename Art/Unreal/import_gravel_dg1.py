"""Deformable gravel DG1 item 1 (docs/DEFORMABLE_GRAVEL_PLAN.md DG1): the gravel bakes into Texture2DArrays, the mud's array
builder (Art/Unreal/import_mud_variants.py) for the two gravel sets. Slice 0 Loose, slice 1 Packed.
- The slices: /Game/GrandTour/ArtTests/DeformableGravel/Bakes/T_GV_<Set><Channel> from Art/Export/GravelDG1 (Art/Blender/bake_gravel_dg1.py:
  the revision-04 study shader baked tileable on a 2 m tile at 2048; ORH packed by Art/bake_gravel_orh.py).
- The arrays: /Game/GrandTour/ArtTests/DeformableGravel/TA_GV_{Color,Normal,ORH} - Color sRGB (BC1), Normal linear (BC5, DirectX
  green, as the bake), ORH linear BC7 (R horizon AO, G roughness 0.55-0.9, B the parallax height); wrapped, the World group, at
  most 2048. Made by Python (Texture2DArrayFactory), the source rebuilt by UGTMudArtLibrary::BuildTextureArray.
Writes Art/Export/DeformableGravel/dg1-import-report.json. Run with & Art/import_gravel_dg1.ps1. Repeatable.
"""
import unreal as u, json, traceback
from pathlib import Path
ROOT = Path(u.Paths.project_dir()).resolve()
SRC = ROOT / 'Art/Export/GravelDG1'
OUT = ROOT / 'Art/Export/DeformableGravel'
OUT.mkdir(parents=True, exist_ok=True)
DEST = '/Game/GrandTour/ArtTests/DeformableGravel'
SLICES = DEST + '/Bakes'
VARIANTS = ['Loose', 'Packed']   # slice 0 Loose, slice 1 Packed (M_GT_Gravel's order)
TC = u.TextureCompressionSettings
CHANNELS = {
    'Color': dict(srgb=True, compression=TC.TC_DEFAULT),
    'Normal': dict(srgb=False, compression=TC.TC_NORMALMAP),
    # linear BC7, as the mud's ORH (three uncorrelated channels; B the parallax height).
    'ORH': dict(srgb=False, compression=TC.TC_BC7),
}
eal = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
report = {'ok': False, 'slices': [], 'arrays': []}


def settings(tex, channel):
    c = CHANNELS[channel]
    tex.set_editor_property('srgb', c['srgb'])
    tex.set_editor_property('compression_settings', c['compression'])
    if channel == 'Normal':
        tex.set_editor_property('flip_green_channel', False)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WORLD)
    tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    tex.set_editor_property('max_texture_size', 2048)


try:
    u.SystemLibrary.execute_console_command(None, 'r.AllowTexture2DArrayCreation 1')
    tasks = []
    for channel in CHANNELS:
        for variant in VARIANTS:
            name = 'T_GV_%s%s' % (variant, channel)
            path = SRC / (name + '.png')
            assert path.exists(), 'no %s (Art/Blender/bake_gravel_dg1.py bakes it)' % path
            task = u.AssetImportTask()
            task.filename = str(path)
            task.destination_path = SLICES
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = False
            tasks.append(task)
    assets.import_asset_tasks(tasks)
    slices = {}
    for channel in CHANNELS:
        for variant in VARIANTS:
            name = 'T_GV_%s%s' % (variant, channel)
            tex = eal.load_asset(SLICES + '/' + name)
            assert tex, 'the import made no ' + name
            settings(tex, channel)
            for axis in ('address_x', 'address_y'):
                tex.set_editor_property(axis, u.TextureAddress.TA_WRAP)
            eal.save_loaded_asset(tex)
            fmt = None
            try:
                fmt = str(tex.source.get_format())
            except Exception:
                pass
            src = SRC / (name + '.png')
            slices.setdefault(channel, []).append(tex)
            report['slices'].append(dict(asset=tex.get_path_name(), source=str(src.relative_to(ROOT)).replace('\\', '/'), source_bytes=src.stat().st_size,
                                         size=[tex.blueprint_get_size_x(), tex.blueprint_get_size_y()], source_format=fmt,
                                         srgb=bool(tex.get_editor_property('srgb')), compression=str(tex.get_editor_property('compression_settings'))))
    for channel, textures in slices.items():
        name = 'TA_GV_' + channel
        path = DEST + '/' + name
        created = False
        arr = eal.load_asset(path) if eal.does_asset_exist(path) else None
        if arr is None:
            arr = assets.create_asset(name, DEST, u.Texture2DArray, u.Texture2DArrayFactory())
            created = True
        assert arr, 'Texture2DArrayFactory made no %s (r.AllowTexture2DArrayCreation?)' % path
        settings(arr, channel)
        for axis in ('address_x', 'address_y', 'address_z'):
            try:
                arr.set_editor_property(axis, u.TextureAddress.TA_WRAP if axis != 'address_z' else u.TextureAddress.TA_CLAMP)
            except Exception as error:
                report.setdefault('address_errors', []).append('%s %s: %s' % (name, axis, error))
        # Route 1, Python alone: the Source Textures through the property (its edit notification rebuilds the array's source).
        python_error = None
        try:
            arr.set_editor_property('source_textures', [])
            arr.set_editor_property('source_textures', textures)
        except Exception as error:
            python_error = '%s: %s' % (type(error).__name__, error)
        py_slices, py_x, py_y = u.GTMudArtLibrary.texture_array_source_slices(arr)
        # Then the explicit rebuild from the slices as they are now (a re-import's new pixels), and the check.
        built, message = u.GTMudArtLibrary.build_texture_array(arr, textures)
        assert built == len(VARIANTS), '%s: BuildTextureArray %s (%s)' % (name, built, message)
        settings(arr, channel)
        assert eal.save_loaded_asset(arr), 'could not save ' + path
        n, sx, sy = u.GTMudArtLibrary.texture_array_source_slices(arr)
        assert (n, sx, sy) == (len(VARIANTS), 2048, 2048), '%s: %d slices of %d x %d' % (name, n, sx, sy)
        package = ROOT / 'Content' / (path[len('/Game/'):] + '.uasset')
        report['arrays'].append(dict(asset=arr.get_path_name(), created=created, slices=[t.get_name() for t in textures],
                                     python_route=dict(slices=py_slices, size=[py_x, py_y], error=python_error),
                                     rebuilt=message, source_slices=n, size=[sx, sy], srgb=bool(arr.get_editor_property('srgb')),
                                     compression=str(arr.get_editor_property('compression_settings')),
                                     package_bytes=package.stat().st_size if package.exists() else None))
    report['route'] = ('Texture2DArray: made by Python (Texture2DArrayFactory), Source Textures set by Python (%s), the source rebuilt by '
                       'UGTMudArtLibrary::BuildTextureArray' % ('gave %s slices' % ','.join(str(a['python_route']['slices']) for a in report['arrays'])))
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'dg1-import-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
