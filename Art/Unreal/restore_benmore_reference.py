"""Restore the terrain-only review after the first road-map SaveMap copy issue."""
import unreal as u
import json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MackenzieRealTerrain/BenmoreFullSite'
DEST='/Game/GrandTour/Demo/BenmoreFullSite';LEVEL=DEST+'/L_Benmore_TerrainReview'
meta=json.loads((OUT/'terrain-manifest.json').read_text())
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
phase='load';last=time.monotonic();started=last
report={'ok':False,'purpose':'Restore original terrain-only reference and verify its saved heights'}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'reference-restore-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,land,rt,material
    now=time.monotonic()
    try:
        if now-started>400:raise RuntimeError('Restore timed out')
        if phase=='load':
            phase='loading';assert les.load_level(LEVEL)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
            for a in act.get_all_level_actors():
                if isinstance(a,(u.PlayerStart,u.CameraActor)) or a.get_actor_label()=='Benmore_Roadside_ArtSample':act.destroy_actor(a)
            land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
            land.set_actor_label('Benmore_FullSite_LINZ_2500m');land.set_editor_property('landscape_material',u.load_asset(DEST+'/M_Benmore_TerrainReview'));land.set_editor_property('default_phys_material',None)
            start=act.spawn_actor_from_class(u.PlayerStart,u.Vector(-95000,-95000,55000),u.Rotator(pitch=-20,yaw=40));start.set_actor_label('ReviewFlyStart')
            camera=act.spawn_actor_from_class(u.CameraActor,u.Vector(-260000,-340000,300000));camera.set_actor_label('ReviewCamera')
            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(0,0,10000)),False)
            camera.camera_component.set_field_of_view(56);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
            u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
            material=u.load_asset(DEST+'/M_Benmore_HeightTransfer');assert material
            rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8)
            phase='warm';last=now
        elif phase=='warm' and now-last>15:
            phase='drawing';u.RenderingLibrary.draw_material_to_render_target(world,rt,material);phase='import';last=now
        elif phase=='import' and now-last>8:
            phase='importing';u.RenderingLibrary.draw_material_to_render_target(world,rt,material)
            assert land.landscape_import_heightmap_from_render_target(rt,True,0);phase='settle';last=now
        elif phase=='settle' and now-last>25:
            phase='exporting';assert land.landscape_export_heightmap_to_render_target(rt,True,True);phase='verify';last=now
        elif phase=='verify' and now-last>10:
            phase='verifying';assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            errors=[]
            for a in meta['unreal_validation_anchors']:
                c=u.RenderingLibrary.read_render_target_pixel(world,rt,*a['pixel']);z=(((int(c.r)<<8)|int(c.g))-32768)/64*100;errors.append(abs(z-a['local_xyz_cm'][2]))
            report['height_max_error_cm']=max(errors);assert max(errors)<.01
            assert world.get_path_name().startswith(LEVEL+'.');assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
