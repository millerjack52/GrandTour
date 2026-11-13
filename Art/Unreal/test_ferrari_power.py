"""Repeatable full-throttle telemetry on an isolated flat lane in the actual Benmore PIE world."""
import unreal as u,json,time,traceback
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/FerrariPower');OUT.mkdir(exist_ok=True)
AFTER='-ferraripowerafter' in u.SystemLibrary.get_command_line().lower()
REPORT=OUT/('after.json' if AFTER else 'before.json')
phase='load';started=time.monotonic();last=started
report={'ok':False,'fixture':'Saved Benmore Ferrari on a temporary flat collision lane, full throttle, game-time measurements','samples':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def save():REPORT.write_text(json.dumps(report,indent=2))
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    save();u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def settings(a):
    m=a.get_chaos_movement();d=a.get_drivetrain();e=m.get_editor_property('engine_setup');t=m.get_editor_property('transmission_setup')
    return {'mass':m.get_editor_property('mass'),'engine':{k:e.get_editor_property(k) for k in ['max_torque','max_rpm','engine_idle_rpm','engine_brake_effect']},'transmission':{k:(list(t.get_editor_property(k)) if k.endswith('ratios') else t.get_editor_property(k)) for k in ['final_ratio','forward_gear_ratios','change_up_rpm','change_down_rpm','gear_change_time']},'split_front':d.get_editor_property('centre_split_front'),'driver_eye':list(a.get_editor_property('driver_eye_offset').to_tuple()),'wheels':[str(s) for s in m.get_editor_property('wheel_setups')]}
def sample(elapsed):
    tune=car.get_component_by_class(u.GTVehicleTuningComponent).get_current()
    return {'t':round(elapsed,3),'kph':round(move.get_forward_speed()*.036,3),'rpm':drive.get_engine_rpm(),'gear':drive.get_gear(),'engine_nm':drive.get_engine_torque_nm(),'torque_scale':tune.torque_scale,'throttle':move.get_throttle_input(),'brake':move.get_brake_input(),'handbrake':bool(move.get_handbrake_input()),'contacts':[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4)],'drive':drive.describe(),'traction':[{'surface':str(w.surface_tag),'sinkage':w.sinkage,'friction':w.friction_scale,'load':w.load} for w in car.get_traction().get_editor_property('wheels')],'health':car.get_condition().get_part_health(u.GTCarPart.ENGINE),'roll':car.get_actor_rotation().roll}
def tick(dt):
    global phase,last,world,pc,car,move,drive,mesh,origin,drive_start,next_sample,brake_start,reverse_start
    now=time.monotonic()
    try:
        if now-started>600:raise RuntimeError('Ferrari telemetry timeout')
        if phase=='load':
            phase='loading';assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
            actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();a=next(a for a in actors if a.get_actor_label()=='Benmore_Fleet_Ferrari288')
            report['saved_instance']=settings(a);report['blueprint_defaults']=settings(u.get_default_object(a.get_class()));save();phase='loaded';last=now
        elif phase=='loaded' and now-last>3:
            phase='starting';u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>8:
            world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0)
            car=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn) if a.get_actor_label()=='Benmore_Fleet_Ferrari288')
            pc.get_car().reset_driving_inputs();assert pc.exit_car();assert pc.enter_vehicle(car);car.disable_input(pc)
            move=car.get_chaos_movement();drive=car.get_drivetrain();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
            report['runtime']=settings(car)
            lane=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(u.Vector(-80000,-20000,20000),u.Rotator(),u.Vector(2000,300,1)),'FerrariPowerTemporaryLane')
            lane.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
            assert lane.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
            assert lane.static_mesh_component.get_editor_property('static_mesh')
            lane.static_mesh_component.set_collision_profile_name('BlockAll');lane.static_mesh_component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
            mesh.set_physics_linear_velocity(u.Vector(),False);mesh.set_physics_angular_velocity_in_degrees(u.Vector(),False)
            car.set_actor_transform(u.Transform(u.Vector(-150000,-20000,20058),u.Rotator(),u.Vector(1,1,1)),False,True)
            mesh.wake_all_rigid_bodies()
            car.reset_driving_inputs();move.set_handbrake_input(True);phase='settle';last=u.GameplayStatics.get_time_seconds(world)
        elif phase=='settle' and u.GameplayStatics.get_time_seconds(world)-last>3:
            report['settled']=sample(0);assert all(report['settled']['contacts']),report['settled']
            report['physical_mass_kg']=mesh.get_mass();origin=car.get_actor_location();car.reset_driving_inputs();drive_start=u.GameplayStatics.get_time_seconds(world);next_sample=0;phase='drive'
        elif phase=='drive':
            move.set_throttle_input(1);move.set_brake_input(0);move.set_handbrake_input(False);car.set_raw_steer(0)
            elapsed=u.GameplayStatics.get_time_seconds(world)-drive_start;speed=move.get_forward_speed()*.036
            for kph in [30,60,100]:
                key='zero_to_'+str(kph)+'_seconds'
                if key not in report and speed>=kph:report[key]=elapsed
            if elapsed>=next_sample:
                row=sample(elapsed);row['lateral_displacement_m']=(car.get_actor_location().y-origin.y)/100;row['yaw_deg']=car.get_actor_rotation().yaw
                report['samples'].append(row);next_sample+=1;save()
            if elapsed>=20:
                report['distance_m']=(car.get_actor_location()-origin).length()/100;report['speed_20s_kph']=speed
                brake_start=u.GameplayStatics.get_time_seconds(world);report['brake_start_kph']=speed;car.reset_driving_inputs();move.set_brake_input(1);phase='brake'
        elif phase=='brake':
            move.set_throttle_input(0);move.set_brake_input(1)
            if abs(move.get_forward_speed())<40:
                report['braking_seconds']=u.GameplayStatics.get_time_seconds(world)-brake_start
                reverse_start=u.GameplayStatics.get_time_seconds(world);phase='reverse'
            elif u.GameplayStatics.get_time_seconds(world)-brake_start>15:raise RuntimeError('Brake stop timeout')
        elif phase=='reverse':
            move.set_brake_input(.5)
            if u.GameplayStatics.get_time_seconds(world)-reverse_start>2:
                report['reverse_kph']=move.get_forward_speed()*.036
                assert report['reverse_kph']<-1
                assert report['speed_20s_kph']>40
                if AFTER:
                    before=json.loads((OUT/'before.json').read_text())
                    assert report['saved_instance']['split_front']==0 and report['runtime']['split_front']==0
                    assert report['saved_instance']['engine']['max_torque']==450 and report['runtime']['engine']['max_rpm']==7500
                    assert len(report['saved_instance']['transmission']['forward_gear_ratios'])==5
                    assert report['zero_to_100_seconds']<before['zero_to_100_seconds']*.8
                    assert all(s['health']>.95 and s['torque_scale']>.95 and not s['handbrake'] and abs(s['roll'])<5 for s in report['samples'])
                    report['acceleration_improvement_percent']=(1-report['zero_to_100_seconds']/before['zero_to_100_seconds'])*100
                finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
