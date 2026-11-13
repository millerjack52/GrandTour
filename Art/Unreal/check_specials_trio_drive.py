"""PIE driving checks and real renderer previews of the three saved test variants."""
import unreal as u
import json,time,traceback,math
from pathlib import Path
OUT=Path(u.Paths.project_dir()).resolve()/'Art/Export/SpecialsTrio/UnrealReview'
OUT.mkdir(exist_ok=True)
u.EditorPythonScripting.set_keep_python_script_alive(True)
queue=[(car,suffix) for suffix in ['Test','Mud'] for car in ['KadettA','E39Touring','SJ413']]
report={'ok':False,'runs':[]}; index=0; phase='load'; last=time.monotonic(); started=last

def save(): (OUT/'runtime_check.json').write_text(json.dumps(report,indent=2))
def finish(error=None):
    global phase
    phase='done'
    if error: report['error']=error
    else: report['ok']=True
    save(); u.unregister_slate_post_tick_callback(handle)
    u.EditorLevelLibrary.editor_end_play(); u.SystemLibrary.quit_editor()

def shot(name):
    path=OUT/(name+'.png')
    u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
    row.setdefault('images',[]).append(str(path))

def tick(dt):
    global phase,last,index,world,car,pc,move,row,camera,origin,initial_yaw,peak_speed,brake_start,steer_start
    now=time.monotonic()
    try:
        if now-started>720: finish('Timeout'); return
        if phase=='load':
            ident,suffix=queue[index]
            level='/Game/GrandTour/Test/SpecialsTrio/L_'+ident+'_'+suffix
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(level)
            row={'car':ident,'map':level,'status':'STARTED'}; report['runs'].append(row); save()
            phase='loaded';last=now
        elif phase=='loaded' and now-last>3:
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play(); phase='warm';last=now
        elif phase=='warm' and now-last>12:
            world=u.EditorLevelLibrary.get_game_world(); assert world
            pc=u.GameplayStatics.get_player_controller(world,0); car=u.GameplayStatics.get_player_pawn(world,0)
            assert isinstance(car,u.GTCarPawn),'Wrong possessed pawn'
            assert car.get_class().get_name()=='BP_'+row['car']+'_C',car.get_class().get_name()
            car.disable_input(pc); car.reset_driving_inputs(); move=car.get_chaos_movement()
            assert len(move.get_editor_property('wheels'))==4
            assert car.get_body().get_panel_count()==0,'Legacy panels attached'
            extra=[c.get_name() for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith(('Panel_','Dash_'))]
            assert not extra,extra
            assert not [c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_editor_property('static_mesh') and c.get_editor_property('static_mesh').get_path_name()=='/Engine/BasicShapes/Cube.Cube'],'Placeholder cubes on car'
            mesh=car.get_component_by_class(u.SkeletalMeshComponent)
            assert mesh.get_editor_property('skeletal_mesh_asset').get_name()=='SK_'+row['car']
            row['spawn_cm']=str(car.get_actor_location()); row['mass_kg']=mesh.get_mass()
            row['wheel_radii_cm']=[w.get_editor_property('wheel_radius') for w in move.get_editor_property('wheels')]
            row['wheel_ground_contacts']=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4)]
            assert all(row['wheel_ground_contacts']),row['wheel_ground_contacts']
            camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'SpecialsReviewCamera')
            p=car.get_actor_location(); yaw=car.get_actor_rotation().yaw
            angle=math.radians(yaw); offset=u.Vector(580*math.cos(angle)+520*math.sin(angle),580*math.sin(angle)-520*math.cos(angle),290)
            camera.set_actor_location(p+offset,False,False); camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(p+offset,p+u.Vector(0,0,75)),False)
            camera.camera_component.set_field_of_view(45); pc.set_view_target_with_blend(camera,0.)
            move.set_handbrake_input(True); phase='front';last=now
        elif phase=='front' and now-last>2:
            shot(row['car']+'_'+queue[index][1]+'_Front');phase='cockpit_wait';last=now
        elif phase=='cockpit_wait' and now-last>1:
            pc.set_view_target_with_blend(car,0.);car.set_chase_camera(False);phase='cockpit';last=now
        elif phase=='cockpit' and now-last>2:
            shot(row['car']+'_'+queue[index][1]+'_Cockpit');phase='drive_start';last=now
        elif phase=='drive_start' and now-last>1:
            origin=car.get_actor_location(); initial_yaw=car.get_actor_rotation().yaw; peak_speed=0.
            row['peak_drive_torque_nm']=[0.,0.,0.,0.]
            car.reset_driving_inputs();move.set_handbrake_input(False); phase='drive';last=now
        elif phase=='drive':
            move.set_throttle_input(.65);car.set_raw_steer(0.)
            peak_speed=max(peak_speed,car.get_velocity().length())
            for i,w in enumerate(car.get_drivetrain().wheels):
                row['peak_drive_torque_nm'][i]=max(row['peak_drive_torque_nm'][i],abs(w.get_editor_property('drive_torque_nm')))
            if now-last>5:
                row['forward_distance_cm']=(car.get_actor_location()-origin).length(); row['peak_speed_cm_s']=peak_speed
                assert row['forward_distance_cm']>150 and peak_speed>100,('Did not drive',row)
                row['wheel_rotation_deg']=[w.get_rotation_angle() for w in move.get_editor_property('wheels')]
                assert any(abs(v)>1 for v in row['wheel_rotation_deg'])
                if row['car']!='SJ413':
                    assert max(row['peak_drive_torque_nm'][:2])<.01,'RWD front axle received drive torque'
                assert max(row['peak_drive_torque_nm'][2:])>1,'Rear wheels received no drive torque'
                brake_start=car.get_velocity().length(); move.set_throttle_input(0);move.set_brake_input(1);phase='brake';last=now
        elif phase=='brake':
            move.set_throttle_input(0);move.set_brake_input(1)
            if now-last>1.5:
                row['brake_start_cm_s']=brake_start;row['brake_end_cm_s']=car.get_velocity().length()
                assert row['brake_end_cm_s']<brake_start*.55,('Brake failed',row)
                car.reset_driving_inputs(); steer_start=car.get_actor_rotation().yaw;phase='steer';last=now
        elif phase=='steer':
            move.set_throttle_input(.45);car.set_raw_steer(.7)
            if now-last>3:
                yaw=car.get_actor_rotation().yaw; row['steer_yaw_change_deg']=abs((yaw-steer_start+180)%360-180)
                assert row['steer_yaw_change_deg']>2,('No steering',row)
                car.reset_driving_inputs();move.set_handbrake_input(True)
                phase='park';last=now
        elif phase=='park' and now-last>3:
            assert pc.exit_car(),'Exit failed'
            assert isinstance(u.GameplayStatics.get_player_pawn(world,0),u.GTPlayerCharacter)
            phase='onfoot';last=now
        elif phase=='onfoot' and now-last>1:
            assert pc.enter_car(),'Re-entry failed'
            assert u.GameplayStatics.get_player_pawn(world,0)==car
            row['exit_reenter']='PASS'
            row['status']='PASS';save();u.EditorLevelLibrary.editor_end_play();phase='ended';last=now
        elif phase=='ended' and now-last>3:
            index+=1
            if index>=len(queue): finish()
            else:phase='load'
    except Exception: finish(traceback.format_exc())

handle=u.register_slate_post_tick_callback(tick)
