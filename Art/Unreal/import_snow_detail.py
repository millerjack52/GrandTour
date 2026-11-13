"""LM4b item 4 (docs/LIVING_MUD_PLAN.md LM4b): import the snow-clump detail height map Art/tools/bake_snow_detail.py baked.

Run with & Art/import_snow_detail.ps1 (it refuses with a game or the editor open). Imports Art/Textures/Snow/T_GT_SnowDetail.png
(1024 x 1024, 16 bits a channel: R crumbs, G clods, B the two together) as /Game/GrandTour/Textures/Snow/T_GT_SnowDetail, a
linear texture: sRGB off, BC7 (TC_BC7: all three channels at a byte's precision or better, a quarter of the uncompressed
8-bit size), wrapped, the World texture group's filtering, mips from the source. M_GT_Snow (Art/Unreal/live_snow_style.py)
and the strip landscape's snow apron sample it tri-planar in world space. Writes Art/Export/LiveSnowDrive/detail-import-report.json.
"""
import unreal as u, json, traceback
from pathlib import Path
ROOT = Path(u.Paths.project_dir()).resolve()
SRC = ROOT / 'Art/Textures/Snow/T_GT_SnowDetail.png'
DEST = '/Game/GrandTour/Textures/Snow'
NAME = 'T_GT_SnowDetail'
OUT = ROOT / 'Art/Export/LiveSnowDrive'
OUT.mkdir(parents=True, exist_ok=True)
eal = u.EditorAssetLibrary
report = {'ok': False}
try:
    assert SRC.exists(), 'no %s (python Art/tools/bake_snow_detail.py makes it)' % SRC
    task = u.AssetImportTask()
    task.filename = str(SRC)
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = eal.load_asset(DEST + '/' + NAME)
    assert tex, 'the import made no texture'
    tex.set_editor_property('srgb', False)
    settings = u.TextureCompressionSettings
    compression = getattr(settings, 'TC_BC7', None) or settings.TC_MASKS
    tex.set_editor_property('compression_settings', compression)
    tex.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
    tex.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WORLD)
    tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    eal.save_loaded_asset(tex)
    fmt = None
    try:
        fmt = str(tex.source.get_format())
    except Exception:
        pass
    report.update(ok=True, asset=tex.get_path_name(), source=str(SRC.relative_to(ROOT)).replace('\\', '/'), source_bytes=SRC.stat().st_size,
                  size=[tex.blueprint_get_size_x(), tex.blueprint_get_size_y()], srgb=bool(tex.get_editor_property('srgb')),
                  compression=str(tex.get_editor_property('compression_settings')), source_format=fmt,
                  address=[str(tex.get_editor_property('address_x')), str(tex.get_editor_property('address_y'))])
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'detail-import-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
