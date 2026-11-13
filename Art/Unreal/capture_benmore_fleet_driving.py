"""Render the six converted cars in the real saved map after suspension settles."""
import unreal as u,json,time,traceback
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/Driving')
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
phase='load';started=time.monotonic();last=started;index=0
report={'ok':False,'images':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'visual-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle)
    u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,pc,camera,cars,views,index
    now=time.monotonic()
    try:
        if now-started>600:raise RuntimeError('Fleet visual review timeout')
        if phase=='load':
            phase='loading';assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP);phase='loaded';last=now
        elif phase=='loaded' and now-last>4:
            phase='starting';u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>20:
            world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0)
            cars={a.get_actor_label().removeprefix('Benmore_Fleet_'):a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn) if a.get_actor_label().startswith('Benmore_Fleet_')};assert len(cars)==12
            overview=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Benmore_Fleet_Overview')
            camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'FleetDrivingCapture')
            views=[('DrivingFleet',overview.get_actor_location(),overview.get_actor_rotation(),65)]
            for name in ['CraftedUtility','Panda1990','Pathfinder2002','Prado','Impreza2003','LandCruiser80']:
                a=cars[name];p=a.get_actor_location();pos=p+a.get_actor_forward_vector()*680-a.get_actor_right_vector()*580+u.Vector(0,0,350)
                views.append((name,pos,u.MathLibrary.find_look_at_rotation(pos,p+u.Vector(0,0,105)),55))
                eye=a.get_editor_property('driver_eye_offset')
                eye_pos=p+a.get_actor_forward_vector()*eye.x+a.get_actor_right_vector()*eye.y+a.get_actor_up_vector()*eye.z
                views.append((name+'_Cockpit',eye_pos,a.get_actor_rotation(),95))
            phase='view'
        elif phase=='view':
            name,pos,rot,fov=views[index]
            if name.endswith('_Cockpit'):
                # Exercise the real pawn camera; a precomputed world point can become stale as parked suspension settles.
                pc.exit_car()
                target=cars[name.removesuffix('_Cockpit')]
                assert pc.enter_vehicle(target),name
                target.set_chase_camera(False)
                pc.set_view_target_with_blend(target,0)
            else:
                camera.set_actor_location(pos,False,False);camera.set_actor_rotation(rot,False);camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0)
            phase='wait';last=now
        elif phase=='wait' and now-last>7:
            phase='shot';last=now
            path=OUT/(views[index][0]+'.png');u.SystemLibrary.execute_console_command(world,'HighResShot 1280x800 filename="'+path.as_posix()+'"',pc)
        elif phase=='shot' and now-last>3:
            path=OUT/(views[index][0]+'.png')
            if not path.exists():
                if now-last<35:return
                raise RuntimeError('No capture '+str(path))
            report['images'].append(str(path));index+=1
            if index==len(views):finish()
            else:phase='view'
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
