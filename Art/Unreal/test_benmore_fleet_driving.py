"""Exercise saved fleet entry via real look/hold interaction, then Chaos driving.
Repositions cars only in PIE to a shared clear road start; never saves the map.
"""
import unreal as u,json,time,traceback,math
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/Driving')
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
report={'ok':False,'cars':[],'scope':'Actual PIE interaction, possession, driving, braking, steering, exit and re-entry. Runtime-only test placements.'}
phase='load';started=time.monotonic();last=started;index=-1;row=None
u.EditorPythonScripting.set_keep_python_script_alive(True)
def save():(OUT/'runtime-report.json').write_text(json.dumps(report,indent=2))
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    save();u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def ground(x,y):
    hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,100000),u.Vector(x,y,-100000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
    assert hit
    return [v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z
def reset(a,transform):
    c=a.get_component_by_class(u.SkeletalMeshComponent);c.set_physics_linear_velocity(u.Vector(),False);c.set_physics_angular_velocity_in_degrees(u.Vector(),False)
    a.reset_driving_inputs();a.get_chaos_movement().set_handbrake_input(True)
    a.set_actor_transform(transform,False,True)
def aim():
    target=car.get_actor_location()+car.get_actor_up_vector()*85
    pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(character.get_camera().get_world_location(),target))
def tick(dt):
    global phase,last,world,pc,cars,car,character,interaction,move,mesh,ignore,start,poses,row,index,origin,peak,brake_start,steer_yaw,previous_car,hold_started
    now=time.monotonic()
    try:
        if now-started>900:raise RuntimeError('Fleet runtime timeout')
        if phase=='load':
            phase='loading'
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP)
            phase='loaded';last=now
        elif phase=='loaded' and now-last>5:
            phase='starting'
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>10:
            world=u.EditorLevelLibrary.get_game_world();assert world
            u.SystemLibrary.execute_console_command(world,'t.MaxFPS 60')
            pc=u.GameplayStatics.get_player_controller(world,0);assert isinstance(pc,u.GTPlayerController)
            cars=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn) if a.get_actor_label().startswith('Benmore_Fleet_')]
            cars.sort(key=lambda a:a.get_actor_label());assert len(cars)==12,len(cars)
            poses={a.get_actor_label():a.get_actor_transform() for a in cars}
            starts=u.GameplayStatics.get_all_actors_of_class(world,u.PlayerStart);assert len(starts)==1;start=starts[0]
            allactors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
            ignore=[a for a in allactors if not isinstance(a,u.LandscapeProxy)]
            initial=pc.get_car();initial.reset_driving_inputs();initial.get_chaos_movement().set_handbrake_input(True)
            assert not pc.enter_vehicle(None)
            assert not pc.enter_vehicle(cars[0]),'Cannot switch directly while already driving'
            assert u.GameplayStatics.get_player_pawn(world,0)==initial
            assert pc.exit_car();character=pc.get_player_character();character.disable_input(pc)
            initial.set_actor_location(initial.get_actor_location()+u.Vector(0,2000,0),False,True)
            interaction=character.get_interaction();phase='next'
            assert not pc.enter_vehicle(None) and u.GameplayStatics.get_player_pawn(world,0)==character
            report['invalid_entry_preserves_possession']=True
        elif phase=='next':
            index+=1
            if index==len(cars):finish();return
            car=cars[index];previous_car=pc.get_car();move=car.get_chaos_movement();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
            car.reset_driving_inputs();move.set_handbrake_input(True)
            p=car.get_actor_location()-car.get_actor_right_vector()*245
            z=ground(p.x,p.y);capsule=character.get_component_by_class(u.CapsuleComponent)
            character.set_actor_location(u.Vector(p.x,p.y,z+capsule.get_scaled_capsule_half_height()+3),False,True)
            character.get_component_by_class(u.CharacterMovementComponent).stop_movement_immediately()
            interaction.set_hold_input(False);aim()
            row={'label':car.get_actor_label(),'class':car.get_class().get_path_name(),'previous_car':previous_car.get_actor_label(),'prompts':[]}
            report['cars'].append(row);phase='offer';last=now;save()
        elif phase=='offer':
            aim()
            if now-last>15:raise RuntimeError('No entry offer: '+interaction.describe())
            if interaction.get_current_target()==car and interaction.is_offer_available():
                prompt=interaction.get_prompt()
                if prompt not in row['prompts']:row['prompts'].append(prompt)
                if prompt=='Get in' or prompt.startswith('Open '):
                    interaction.set_hold_input(True);phase='hold';hold_started=now
        elif phase=='hold':
            aim()
            if u.GameplayStatics.get_player_pawn(world,0)==car:
                interaction.set_hold_input(False)
                assert pc.get_car()==car and car!=previous_car
                assert character.is_in_car() and character.get_editor_property('hidden')
                assert not move.get_handbrake_input(),'Entry did not release parking brake'
                row['actual_interaction_entry']='PASS';row['new_target_possessed']=True
                car.disable_input(pc)
                p=start.get_actor_location();z=ground(p.x,p.y)
                setups=move.get_editor_property('wheel_setups')
                bottom=min(mesh.get_socket_transform(str(s.get_editor_property('bone_name')),u.RelativeTransformSpace.RTS_ACTOR).translation.z-u.get_default_object(s.get_editor_property('wheel_class')).get_editor_property('wheel_radius') for s in setups)
                reset(car,u.Transform(u.Vector(p.x,p.y,z-bottom+8),u.Rotator(yaw=start.get_actor_rotation().yaw),u.Vector(1,1,1)))
                phase='settle';last=now
            elif now-hold_started>.8:
                interaction.set_hold_input(False);phase='door_wait';hold_started=now
        elif phase=='door_wait' and now-hold_started>1.2:
            phase='offer'
        elif phase=='settle' and now-last>2:
            assert len(move.get_editor_property('wheels'))==4
            row['ground_contacts']=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4)]
            assert all(row['ground_contacts']),row
            origin=car.get_actor_location();peak=0;car.reset_driving_inputs();phase='drive';last=now
        elif phase=='drive':
            move.set_throttle_input(.55);car.set_raw_steer(0);peak=max(peak,car.get_velocity().length())
            if now-last>4:
                row['distance_cm']=(car.get_actor_location()-origin).length();row['peak_speed_cm_s']=peak
                assert row['distance_cm']>150 and peak>100,row
                row['wheel_roll_degrees']=[w.get_rotation_angle() for w in move.get_editor_property('wheels')]
                assert all(abs(v)>1 for v in row['wheel_roll_degrees'])
                brake_start=car.get_velocity().length();move.set_throttle_input(0);move.set_brake_input(1);phase='brake';last=now;save()
        elif phase=='brake':
            move.set_throttle_input(0);move.set_brake_input(1)
            if now-last>2:
                row['brake_start_cm_s']=brake_start;row['brake_end_cm_s']=car.get_velocity().length()
                assert row['brake_end_cm_s']<max(50,brake_start*.55),row
                car.reset_driving_inputs();steer_yaw=car.get_actor_rotation().yaw;phase='steer';last=now
        elif phase=='steer':
            move.set_throttle_input(.4);car.set_raw_steer(.65)
            if now-last>2.5:
                row['steer_yaw_change_deg']=abs((car.get_actor_rotation().yaw-steer_yaw+180)%360-180)
                assert row['steer_yaw_change_deg']>2,row
                row['roll_deg']=car.get_actor_rotation().roll;assert abs(row['roll_deg'])<35
                car.reset_driving_inputs();move.set_brake_input(1);move.set_handbrake_input(True);phase='stop';last=now
        elif phase=='stop':
            if now-last>12:raise RuntimeError('Failed to stop '+str(row))
            if car.get_velocity().length()<60 and now-last>1:
                assert pc.exit_car();assert u.GameplayStatics.get_player_pawn(world,0)==character
                assert pc.enter_car();assert u.GameplayStatics.get_player_pawn(world,0)==car
                assert pc.exit_car();assert u.GameplayStatics.get_player_pawn(world,0)==character
                row['exit_and_reenter']='PASS';row['ok']=True
                reset(car,poses[car.get_actor_label()]);save();u.log('FLEET_DRIVE_PASS '+car.get_actor_label());phase='next'
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
save()



