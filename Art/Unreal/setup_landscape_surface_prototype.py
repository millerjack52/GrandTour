"""Create a new isolated 31.5 m map. No Benmore load/save, no tests or profiling.
Run using Art/setup_landscape_surface_prototype.ps1 once the editor build succeeds.
"""
import json
import struct
import sys
import traceback
import zlib
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from landscape_surface_material import build, DEST


def write_paint(path):
    # A deliberately small authored mask: mud at x<3 m, gravel beyond, and firm perimeter.
    # The RGBA import path also accepts future Gaea/hand-painted masks with this channel contract.
    n=256
    def smooth(a,b,x):
        t=max(0.,min(1.,(x-a)/(b-a)))
        return t*t*(3-2*t)
    data=bytearray()
    for y in range(n):
        data.append(0)
        for x in range(n):
            wx=(x+.5)/n*3150-1575; wy=(y+.5)/n*3150-1575
            rim=(1-smooth(1250,1500,abs(wx)))*(1-smooth(650,1000,abs(wy)))
            mud=rim*(1-smooth(100,400,wx))
            gravel=rim*smooth(100,400,wx)
            data.extend((round(255*.6*mud),round(255*.16),round(255*gravel),round(255*.7*mud)))
    def chunk(kind,payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(data)))+chunk(b'IEND',b''))


def main():
    assets=u.EditorAssetLibrary
    level=DEST+'/L_LandscapeSurfacePrototype'
    if assets.does_asset_exist(level) or assets.does_asset_exist(DEST+'/M_LandscapeSurface'):
        raise RuntimeError('Prototype assets exist; refusing to overwrite review work.')
    out=ROOT/'Art/Export/LandscapeSurface';out.mkdir(parents=True,exist_ok=True)
    paint_file=out/'prototype-paint.png';write_paint(paint_file)
    task=u.AssetImportTask()
    for k,v in dict(filename=str(paint_file),destination_path=DEST,destination_name='T_SurfacePaint',automated=True,save=True,replace_existing=False).items():task.set_editor_property(k,v)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=assets.load_asset(DEST+'/T_SurfacePaint');assert texture
    texture.set_editor_property('srgb',False)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
    texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    assets.save_loaded_asset(texture)
    material=build(texture)
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert les.new_level(level)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    for cmd in ['landscape.Nanite.LiveRebuildOnModification 0','r.Nanite.Tessellation 1','r.Nanite.ProgrammableRaster 1','r.Nanite.ComputeRasterization 1']:
        u.SystemLibrary.execute_console_command(world,cmd)
    landscape=u.GTLandscapeSurfaceSetupLibrary.create_prototype_landscape(world,material);assert landscape
    landscape.set_editor_property('enable_nanite',True)
    landscape.set_editor_property('nanite_skirt_enabled',True)
    landscape.set_editor_property('nanite_skirt_depth',100.)
    surface=u.EditorLevelLibrary.spawn_actor_from_class(u.GTLandscapeSurface,u.Vector(0,0,0))
    surface.set_actor_label('LandscapeSurface_Prototype')
    surface.set_editor_property('landscape',landscape)
    surface.set_editor_property('paint_origin_cm',u.Vector2D(-1575,-1575))
    surface.set_editor_property('paint_size_cm',3150)
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(surface,texture)
    u.EditorLevelLibrary.spawn_actor_from_class(u.SkyAtmosphere,u.Vector(0,0,0))
    sun=u.EditorLevelLibrary.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1000),u.Rotator(-18,-25,0))
    sun.light_component.set_editor_property('intensity',5.)
    sun.light_component.set_editor_property('atmosphere_sun_light',True)
    sky=u.EditorLevelLibrary.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,1000))
    sky.light_component.set_editor_property('real_time_capture',True)
    u.EditorLevelLibrary.spawn_actor_from_class(u.PlayerStart,u.Vector(-1100,0,150))
    # Save only the new map; never SaveAllDirtyPackages in the shared checkout.
    assets.save_loaded_asset(texture)
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(-950,-350,160),u.Rotator(-12,15,0))
    assert les.save_current_level()
    (out/'setup-report.json').write_text(json.dumps(dict(level=level,material=material.get_path_name(),landscape=landscape.get_name(),
        status='created; shader/runtime/visual review and owner performance measurement pending',tests_run=False),indent=2))


try:
    main()
except Exception:
    u.log_error(traceback.format_exc())
    raise
finally:
    u.SystemLibrary.quit_editor()
