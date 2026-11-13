"""Capture the saved road map after visual-only updates; does not mutate it."""
import unreal as u,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRoads'
data=json.loads((OUT/'road-manifest.json').read_text());les=u.get_editor_subsystem(u.LevelEditorSubsystem)
phase='load';last=time.monotonic();started=last;report={'ok':False,'images':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'capture-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def shot(name):
    path=OUT/(name+'.png');report['images'].append(str(path));u.SystemLibrary.execute_console_command(world,'HighResShot 1600x1000 filename="'+path.as_posix()+'"',pc)
def tick(dt):
    global phase,last,world,pc,car,camera
    now=time.monotonic()
    try:
        if now-started>300:raise RuntimeError('Capture timeout')
        if phase=='load':
            phase='loading';assert les.load_level(data['level']);phase='loaded';last=now
        elif phase=='loaded' and now-last>5:
            phase='begin';les.editor_request_begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>18:
            phase='setting_view';world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0);assert isinstance(car,u.GTCarPawn)
            car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
            for cmd in ['gt.Look.Post 0','gt.Look.Kuwahara 0','gt.Look.Weather Clear','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Benmore_RouteOverview')
            pc.set_view_target_with_blend(camera,0);phase='overview';last=now
        elif phase=='overview' and now-last>6:
            phase='capturing';shot('Unreal_Road_Overview');phase='start_view';last=now
        elif phase=='start_view' and now-last>4:
            phase='setting_start';pc.set_view_target_with_blend(car,0);car.set_chase_camera(True);phase='start_shot';last=now
        elif phase=='start_shot' and now-last>5:
            phase='capturing';shot('Start_Driver');phase='ground_view';last=now
        elif phase=='ground_view' and now-last>4:
            phase='setting_ground';p=data['routes'][0]['points'][55];target=data['routes'][0]['points'][75]
            camera.set_actor_location(u.Vector(p['x_m']*100,p['y_m']*100,p['z_m']*100+180),False,False)
            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(target['x_m']*100,target['y_m']*100,target['z_m']*100+160)),False)
            camera.camera_component.set_field_of_view(70);pc.set_view_target_with_blend(camera,0);phase='ground_shot';last=now
        elif phase=='ground_shot' and now-last>5:
            phase='capturing';shot('Roadside_ArtSample');phase='done';last=now
        elif phase=='done' and now-last>4:finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
