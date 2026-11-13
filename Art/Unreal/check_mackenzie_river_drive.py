"""One actual Range Rover crossing. Normal inputs; no force or handling tuning.

This measures connection to existing water interactions, not driving quality.
Uses the PIE car (or spawns one). Checks/repairs study mesh collision first;
no level or driving-physics assets are saved. Fixed simulation timestep.
"""
import json,sys,time,traceback,math
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from mackenzie_river_study_shape import height
from check_render import Gate
from mackenzie_river_study_bridge import survey_collision,repair_bed_collision
OUT=ROOT/'Art/Export/MackenzieRiverStudy';GATE=Gate(warm=25)
report=dict(ok=False,actual_vehicle=True,scope='Functional water hookup only. Untagged static bed; no deformable mud or loose-stone collision.',samples=[],images=[])
phase='load';started=last=time.monotonic();busy=False;world=pc=car=camera=pace_rt=None;capture_key=None

def finish(error=None):
    global phase,last,world,pc,car,camera,pace_rt
    report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    if world:u.GameplayStatics.set_game_paused(world,False)
    report['fixed_dt']=GATE.report()['fixed_dt']
    (OUT/'drive-report.json').write_text(json.dumps(report,indent=2))
    if pace_rt:u.RenderingLibrary.release_render_target2d(pace_rt)
    pace_rt=None
    world=pc=car=camera=None;u.EditorLevelLibrary.editor_end_play();phase='ending';last=time.monotonic()

def tag_name(tag):
    try:return str(tag.get_editor_property('TagName'))
    except Exception:return 'unavailable'

def sample():
    wheels=car.get_traction().get_editor_property('wheels');spray=car.get_spray();hull=car.get_hull()
    return dict(t=u.GameplayStatics.get_time_seconds(world)-drive_start,position_cm=car.get_actor_location().to_tuple(),speed_mps=car.get_velocity().length()*.01,
        contacts=[w.get_editor_property('bInContact') for w in wheels],
        depth_m=[w.get_editor_property('water_depth_m') for w in wheels],
        surface=[tag_name(w.get_editor_property('surface_tag')) for w in wheels],
        contact_cm=[w.get_editor_property('contact_point').to_tuple() for w in wheels],
        water_forces_n=[w.get_editor_property('water_force_n').to_tuple() for w in wheels],
        splash_rate=spray.get_splash_rate_now(),bow_rate=spray.get_bow_rate_now(),
        hull_force_n=hull.get_editor_property('last_water_force').to_tuple())

def body():
    global phase,last,world,pc,car,move,camera,drive_start,settle_start,next_sample,capture_key,shot_time,pace_rt
    now=time.monotonic()
    if phase=='ending':
        if now-last>5 and u.EditorLevelLibrary.get_game_world() is None:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        return
    if now-started>600:raise RuntimeError('Crossing review timed out')
    if phase=='load':
        assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/MackenzieRiverStudy/L_MackenzieRiverStudy')
        phase='play';last=now
        (OUT/'drive-report.json').write_text(json.dumps(report,indent=2))
    elif phase=='repair' and now-last>5 and u.EditorLevelLibrary.get_game_world() is None:
        report['collision_backup']=repair_bed_collision();phase='play';last=time.monotonic()
    elif phase=='play' and now-last>8:
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1280,800);phase='warm';last=now
    elif phase=='warm' and now-last>12:
        world=u.EditorLevelLibrary.get_game_world()
        if world is None:return
        collision=survey_collision(world)
        report['collision_after' if 'collision_backup' in report else 'collision_before']=collision
        (OUT/'collision-review.json').write_text(json.dumps({k:v for k,v in report.items() if k.startswith('collision')},indent=2))
        if max(abs(r['error_cm']) for r in collision)>2:
            assert 'collision_backup' not in report,'Rebuilt collision still differs from the visible bed'
            world=None;u.EditorLevelLibrary.editor_end_play();phase='repair';last=now;return
        pc=u.GameplayStatics.get_player_controller(world,0)
        old=u.GameplayStatics.get_player_pawn(world,0)
        if old:old.set_actor_hidden_in_game(True)
        at=u.Vector(-1100,-1100,height(-1100,-1100)+300)
        car=pc.get_car()
        if car is None:car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.GTCarPawn,u.Transform(at,u.Rotator(yaw=90),u.Vector(1,1,1)),'RiverStudy_DriveProbe')
        assert car
        car.set_actor_hidden_in_game(False);car.set_actor_location_and_rotation(at,u.Rotator(yaw=90),False,True)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
        pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement();move.set_handbrake_input(True)
        car.get_drivetrain().set_low_range(True)
        camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='RiverStudy_Camera_shore_transition')
        for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0']:u.SystemLibrary.execute_console_command(world,cmd,pc)
        GATE.start_dt();GATE.set(world,pc,False);settle_start=u.GameplayStatics.get_time_seconds(world);phase='settle'
        pace_rt=u.RenderingLibrary.create_render_target2d(world,1,1,u.TextureRenderTargetFormat.RTF_RGBA8)
        report['car']=car.get_class().get_path_name();report['initial_position_cm']=at.to_tuple()
    if not world:return
    GATE.tick(world)
    # Scene captures (including the rain emitter) still render with the main
    # viewport off. Drain the GPU queue during the fixed-step review as well.
    if pace_rt:u.RenderingLibrary.read_render_target_pixel(world,pace_rt,0,0)
    if phase=='settle' and u.GameplayStatics.get_time_seconds(world)-settle_start>3:
        drive_start=u.GameplayStatics.get_time_seconds(world);next_sample=0;move.set_handbrake_input(False);phase='drive'
    if phase=='drive':
        t=u.GameplayStatics.get_time_seconds(world)-drive_start;pos=car.get_actor_location();speed=car.get_velocity().length()*.01
        move.set_throttle_input(.5 if speed<3 else 0);move.set_brake_input(.15 if speed>3.7 else 0)
        error=(90-car.get_actor_rotation().yaw+180)%360-180;car.set_raw_steer(max(-.25,min(.25,error*.025)))
        if t>=next_sample:
            row=sample();report['samples'].append(row);next_sample=t+.15
            if len(report['samples'])%7==0:(OUT/'drive-report.json').write_text(json.dumps(report,indent=2))
            if max(row['depth_m'])>.18 and 'wet' not in report:
                report['wet']=row;capture_key='vehicle_water';phase='pre_capture'
            if pos.y>950:
                report['exit']=row
                assert 'wet' in report,'Vehicle never reached water'
                assert max(r['splash_rate'] for r in report['samples'])>0,'No existing water spray was activated'
                assert any(max(r['depth_m'])==0 and r['splash_rate']==0 for r in report['samples'][:8]),'No dry baseline'
                assert max(row['depth_m'])==0,'Exit still submerged'
                finish();return
        if t>35:raise RuntimeError('Vehicle did not complete crossing within 35 simulation seconds')
    if phase=='pre_capture':
        at=car.get_actor_location();p=at+u.Vector(620,-430,300);camera.set_actor_location(p,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(p,at+u.Vector(0,0,30)),False);pc.set_view_target_with_blend(camera,0)
        GATE.set(world,pc,True);phase='pause_capture';return
    elif phase=='pause_capture':
        u.GameplayStatics.set_game_paused(world,True);phase='capture'
    if phase=='capture':
        if GATE.ready(world,pc):
            path=OUT/(capture_key+'.png');shot_time=time.time();u.SystemLibrary.execute_console_command(world,'HighResShot 1280x800 filename="'+path.as_posix()+'"',pc);phase='wait_capture'
    elif phase=='wait_capture':
        path=OUT/(capture_key+'.png')
        if path.exists() and path.stat().st_mtime>=shot_time:
            report['images'].append(str(path));u.GameplayStatics.set_game_paused(world,False);GATE.set(world,pc,False);phase='drive'

def tick(dt):
    global busy
    if busy:return
    busy=True
    try:body()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
