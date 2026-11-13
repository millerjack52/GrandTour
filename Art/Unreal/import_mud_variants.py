"""Living mud LM5b (docs/LIVING_MUD_PLAN.md LM5b phase B item 2, docs/MUD_VARIANTS.md): the four bog bake sets into four
Texture2DArrays, one per channel, slice = EGTMudVariant (0 Standard, 1 Firm, 2 Deep, 3 Stony).

Run with & Art/import_mud_variants.ps1 (it refuses with a game or the editor open). Repeatable: re-running it re-imports the
sixteen PNGs over the same assets and rebuilds the four arrays from them, so revised bakes replace the old cleanly.
- The slices: Art/Export/MudStyleUE/T_MS_Bog<Variant><Channel>.png (2048, a 3 m tile; Art/Blender/export_mud_wet.py) as
  /Game/GrandTour/ArtTests/MudStyle/Variants/T_MS_Bog<Variant><Channel> (Texture2D: the arrays' sources only).
- The arrays: /Game/GrandTour/ArtTests/MudStyle/TA_MS_Bog<Channel> - Color sRGB (BC1), Normal linear (BC5, DirectX green
  as the clay's), Rough and Height linear (TC_Masks: BC1), wrapped, the World group, mips from the source, at most 2048.
- MudRunner MRP (docs/MUDRUNNER_LESSONS_PLAN.md MRP item 2): and TA_MS_BogORH from T_MS_Bog<Variant>ORH.png (python
  Art/bake_mud_orh.py first: R horizon AO, G the remapped roughness, B the height), linear BC7. The mud materials sample Color,
  Normal and ORH since MRP; Rough and Height stay imported (M_GT_Snow's copy of the older mud graph still names them).
  The array asset is made by Python (Texture2DArrayFactory); its Source Textures are set by Python (set_editor_property,
  whose edit notification should rebuild the source) and the slice count that gives is recorded (python_route); then
  UGTMudArtLibrary::BuildTextureArray rebuilds the source from the slices explicitly (so a re-import is never stale), and
  the final slice count and size are checked (4 x 2048 x 2048).
Writes Art/Export/MudVariants/import-report.json. Run & Art/setup_live_mud_drive.ps1 (or & Art/setup_mud_variants.ps1)
after the first import: the materials take the arrays by asset, so a later re-import needs no material rebuild.
"""
import unreal as u, json, traceback
from pathlib import Path
ROOT = Path(u.Paths.project_dir()).resolve()
SRC = ROOT / 'Art/Export/MudStyleUE'
OUT = ROOT / 'Art/Export/MudVariants'
OUT.mkdir(parents=True, exist_ok=True)
DEST = '/Game/GrandTour/ArtTests/MudStyle'
SLICES = DEST + '/Variants'
VARIANTS = ['Standard', 'Firm', 'Deep', 'Stony']   # EGTMudVariant's order: never reorder, append
TC = u.TextureCompressionSettings
CHANNELS = {
    'Color': dict(srgb=True, compression=TC.TC_DEFAULT),
    'Normal': dict(srgb=False, compression=TC.TC_NORMALMAP),
    'Rough': dict(srgb=False, compression=TC.TC_MASKS),
    'Height': dict(srgb=False, compression=TC.TC_MASKS),
    # MudRunner MRP item 2: R ambient occlusion, G roughness (remapped into the PBR bands), B height, packed by Art/bake_mud_orh.py;
    # linear BC7 (three uncorrelated channels: BC1's 5:6:5 endpoints would step the parallax's height). MRP follow-up 3: B is the
    # soft-rimmed parallax height; follow-up 2's OR (BC5) and HeightPOM / HeightPOM8 (BC4 / G8) arrays are no longer built (their
    # assets stay on disk, unreferenced: TA_MS_BogOR, TA_MS_BogHeightPOM, TA_MS_BogHeightPOM8 and their Variants/ slices).
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
            name = 'T_MS_Bog%s%s' % (variant, channel)
            path = SRC / (name + '.png')
            assert path.exists(), 'no %s (Art/Blender/export_mud_wet.py bakes it; the ORH maps: python Art/bake_mud_orh.py)' % path
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
            name = 'T_MS_Bog%s%s' % (variant, channel)
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
        name = 'TA_MS_Bog' + channel
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
    (OUT / 'import-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
