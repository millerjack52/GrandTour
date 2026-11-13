"""Reload the saved terrain, verify persistence, and frame the entire site."""
import unreal as u,json,time,traceback
from pathlib import Path
OUT=Path(u.Paths.project_dir()).resolve()/'Art/Export/MackenzieRealTerrain/BenmoreFullSite'
meta=json.loads((OUT/'terrain-manifest.json').read_text());report=json.loads((OUT/'unreal-review-report.json').read_text());assert report['ok']
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase='load';last=time.monotonic();started=last
def finish(error=None):
    report['saved_map_verified']=not error
    if error:report['capture_error']=error
    (OUT/'unreal-review-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,land,rt
    now=time.monotonic()
    try:
        if now-started>240:raise RuntimeError('Capture timed out')
        if phase=='load':
            phase='loading'
            assert les.load_level(report['level'])
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
            land=next(a for a in actors if isinstance(a,u.Landscape))
            camera=next(a for a in actors if isinstance(a,u.CameraActor))
            camera.set_actor_location(u.Vector(-260000,-340000,300000),False,False)
            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(0,0,10000)),False)
            camera.camera_component.set_field_of_view(56)
            camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
            u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
            assert les.save_current_level()
            rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8)
            phase='warm';last=now
        elif phase=='warm' and now-last>12:
            phase='exporting';assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            phase='check';last=now
        elif phase=='check' and now-last>10:
            phase='checking';assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            errors=[]
            for a in meta['unreal_validation_anchors']:
                x,y=a['pixel'];c=u.RenderingLibrary.read_render_target_pixel(world,rt,x,y)
                errors.append(abs((((int(c.r)<<8)|int(c.g))-32768)/64*100-a['local_xyz_cm'][2]))
            report['saved_map_height_max_error_cm']=max(errors);assert max(errors)<.01
            les.editor_request_begin_play();phase='pie';last=now
        elif phase=='pie' and now-last>12:
            phase='view'
            game=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(game,0)
            camera=u.GameplayStatics.get_all_actors_of_class(game,u.CameraActor)[0]
            pc.set_view_target_with_blend(camera,0)
            for cmd in ['gt.Look.Post 0','gt.Look.Kuwahara 0']:
                u.SystemLibrary.execute_console_command(game,cmd,pc)
            phase='shot';last=now
        elif phase=='shot' and now-last>4:
            phase='capturing'
            game=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(game,0)
            u.SystemLibrary.execute_console_command(game,'HighResShot 1600x1100 filename="'+(OUT/'Unreal_Terrain_Review.png').as_posix()+'"',pc)
            phase='done';last=now
        elif phase=='done' and now-last>4:
            phase='finishing';u.EditorLevelLibrary.editor_end_play();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
