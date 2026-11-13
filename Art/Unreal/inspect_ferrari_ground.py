"""Inspect drawn wheel centres against ground contacts in real Benmore grass, including braking."""
import unreal as u,json,time,traceback,math
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/FerrariGroundContact');OUT.mkdir(exist_ok=True)
AFTER='-ferrarigroundafter' in u.SystemLibrary.get_command_line().lower();TAG='after' if AFTER else 'before'
HEADLESS='-nullrhi' in u.SystemLibrary.get_command_line().lower()
phase='load';started=time.monotonic();last=started;next_sample=0
report={'ok':False,'samples':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def save():(OUT/(TAG+'.json')).write_text(json.dumps(report,indent=2))
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    save();u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def enter_profile_check():
    provider=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTTerrainBuilder) if a.get_actor_label()=='Benmore_RL_CrossingProfiles')
    spec=provider.get_editor_property('spec_asset').get_editor_property('spec');route=spec.get_editor_property('route_m')
    section=next(s for s in spec.get_editor_property('sections') if s.get_editor_property('deform').get_editor_property('max_sinkage_m')>.05)
    distance=(section.get_editor_property('start_m')+section.get_editor_property('end_m'))/2
    dx=route[1].x-route[0].x;dy=route[1].y-route[0].y;length=math.hypot(dx,dy)
    p=u.Vector((route[0].x+dx*distance/length)*100,(route[0].y+dy*distance/length)*100,car.get_actor_location().z)
    p.z=ground(p)+12
    car.reset_driving_inputs();move.set_handbrake_input(True);mesh.set_physics_linear_velocity(u.Vector(),False);mesh.set_physics_angular_velocity_in_degrees(u.Vector(),False)
    car.set_actor_transform(u.Transform(p,u.Rotator(yaw=math.degrees(math.atan2(dy,dx))),u.Vector(1,1,1)),False,True);mesh.wake_all_rigid_bodies()
def ground(p):
    hit=u.SystemLibrary.line_trace_single(world,p+u.Vector(0,0,1000),p-u.Vector(0,0,2000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
    assert hit
    return [v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z
def sample(label):
    row={'phase':label,'kph':car.get_velocity().length()*.036,'pitch':car.get_actor_rotation().pitch,'pose_tick':str(mesh.get_editor_property('visibility_based_anim_tick_option')),'wheels':[]}
    for i,(w,s,traction) in enumerate(zip(move.get_editor_property('wheels'),move.get_editor_property('wheel_setups'),car.get_traction().get_editor_property('wheels'))):
        bone=str(s.get_editor_property('bone_name'));centre=mesh.get_socket_location(bone);g=ground(centre)
        status=u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i));pm=status[2]
        base=u.get_default_object(s.get_editor_property('wheel_class')).get_editor_property('wheel_radius')
        row['wheels'].append({'bone':bone,'centre':list(centre.to_tuple()),'ground_z':g,'drawn_clearance_cm':centre.z-base-g,'radius_cm':w.get_wheel_radius(),'base_radius_cm':base,'suspension_offset_cm':w.get_suspension_offset(),'contact':bool(status[0]),'contact_point':list(status[1].to_tuple()),'material':pm.get_path_name() if pm else None,'sinkage_cm':traction.sinkage*100,'visible_sinkage_cm':traction.visible_sinkage*100,'load':traction.load})
    report['samples'].append(row);save()
def view():
    p=car.get_actor_location();pos=p+car.get_actor_forward_vector()*380-car.get_actor_right_vector()*530+u.Vector(0,0,110)
    camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,p+u.Vector(0,0,55)),False)
def shot(name):
    if HEADLESS:return
    u.SystemLibrary.execute_console_command(world,'HighResShot 1280x800 filename="'+(OUT/(TAG+'_'+name+'.png')).as_posix()+'"',pc)
def tick(dt):
    global phase,last,world,pc,car,move,mesh,ignore,camera,next_sample
    now=time.monotonic()
    try:
        if now-started>600:raise RuntimeError('Ground inspection timeout')
        if phase=='load':
            phase='loading';assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview');phase='loaded';last=now
        elif phase=='loaded' and now-last>4:
            phase='starting';u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>15:
            world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0)
            car=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn) if a.get_actor_label()=='Benmore_Fleet_Ferrari288')
            move=car.get_chaos_movement();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
            if HEADLESS:mesh.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            ignore=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if not isinstance(a,u.LandscapeProxy)]
            pc.get_car().reset_driving_inputs();assert pc.exit_car();assert pc.enter_vehicle(car);car.disable_input(pc)
            camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'FerrariGroundCamera');ignore.append(camera);camera.camera_component.set_field_of_view(55);pc.set_view_target_with_blend(camera,0)
            p=car.get_actor_location()+car.get_actor_right_vector()*1400;p.z=ground(p)+12
            mesh.set_physics_linear_velocity(u.Vector(),False);mesh.set_physics_angular_velocity_in_degrees(u.Vector(),False)
            car.set_actor_transform(u.Transform(p,u.Rotator(yaw=car.get_actor_rotation().yaw),u.Vector(1,1,1)),False,True);mesh.wake_all_rigid_bodies()
            car.reset_driving_inputs();move.set_handbrake_input(True);phase='park';last=u.GameplayStatics.get_time_seconds(world);next_sample=2
        elif phase in ['park','drive','brake','stopped','profile']:
            view();elapsed=u.GameplayStatics.get_time_seconds(world)-last
            if elapsed>=next_sample:sample(phase);next_sample+=1
            if phase=='park' and elapsed>8:
                phase='park_shot';last=now;shot('parked')
            elif phase=='drive':
                move.set_throttle_input(.45);car.set_raw_steer(0)
                if elapsed>5:phase='drive_shot';last=now;shot('rolling')
            elif phase=='brake':
                move.set_throttle_input(0);move.set_brake_input(1)
                if elapsed>1.5:phase='brake_shot';last=now;shot('braking')
            elif phase=='stopped' and elapsed>3:
                if AFTER:
                    grass=[w for s in report['samples'] for w in s['wheels']]
                    assert all(w['visible_sinkage_cm']<.05 for w in grass)
                    assert min(w['drawn_clearance_cm'] for w in grass)>-2.5
                    report['grass_no_sinkage']=True
                    enter_profile_check();phase='profile';last=u.GameplayStatics.get_time_seconds(world);next_sample=2
                else:finish()
            elif phase=='profile' and elapsed>8:
                report['profile_sinkage_cm']=max(w['visible_sinkage_cm'] for s in report['samples'] if s['phase']=='profile' for w in s['wheels'])
                assert report['profile_sinkage_cm']>.5,'Authored mud profile did not apply'
                report['mud_profile_preserved']=True;finish()
        elif phase.endswith('_shot') and now-last>3:
            if phase=='park_shot':car.reset_driving_inputs();phase='drive'
            elif phase=='drive_shot':move.set_throttle_input(0);move.set_brake_input(1);phase='brake'
            else:car.reset_driving_inputs();move.set_handbrake_input(True);phase='stopped'
            last=u.GameplayStatics.get_time_seconds(world);next_sample=0
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
