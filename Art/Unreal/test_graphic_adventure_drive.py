"""Real PIE checks of the persisted Graphic Adventure pawn and test level."""
import unreal as u,json,time,traceback,math
from pathlib import Path
OUT=Path(u.Paths.project_dir()).resolve()/'Art/Export/VehicleTools/graphic-adventure-unreal-v01'
FINISH='-gainterior' in u.SystemLibrary.get_command_line().lower()
CAPTURE_ONLY='-gacaptureonly' in u.SystemLibrary.get_command_line().lower()
if FINISH:OUT=OUT.parent/'graphic-adventure-unreal-v02'
MAP='/Game/GrandTour/Test/GraphicAdventure/L_GraphicAdventure_Test'
RENDER='-nullrhi' not in u.SystemLibrary.get_command_line().lower()
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase='load';last=time.monotonic();started=last;samples=0;report={'ok':False,'level':MAP,'status':'STARTED'}
def save():(OUT/('render-check.json' if CAPTURE_ONLY else 'runtime-check.json')).write_text(json.dumps(report,indent=2))
save()
def finish(error=None):
 global phase
 phase='done';report['ok']=error is None;report['status']='PASS' if error is None else 'FAILED'
 if error:report['error']=error
 save();u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def shot(name):
 if not RENDER:return
 path=OUT/(name+'.png');u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 report.setdefault('images',[]).append(str(path))
def camera_view(offset):
 p=car.get_actor_location();camera.set_actor_location(p+u.Vector(*offset),False,False)
 camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(p+u.Vector(*offset),p+u.Vector(0,0,120)),False)
 pc.set_view_target_with_blend(camera,0.)
def tick(dt):
 global phase,last,world,pc,car,move,camera,origin,peak,brake_start,steer_start,samples
 now=time.monotonic()
 try:
  if now-started>480:finish('Runtime check timed out');return
  if phase=='load':
   assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP);phase='loaded';last=now
  elif phase=='loaded' and now-last>5:
   u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();phase='warm';last=now
  elif phase=='warm' and now-last>16:
   world=u.EditorLevelLibrary.get_game_world();assert world
   pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0)
   assert isinstance(car,u.GTCarPawn) and car.get_class().get_name()=='BP_GraphicAdventure_C'
   car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement()
   assert len(move.get_editor_property('wheels'))==4
   assert car.get_body().get_panel_count()==0
   assert not [c.get_name() for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith(('Panel_','Dash_'))]
   mesh=car.get_component_by_class(u.SkeletalMeshComponent);assert mesh.get_editor_property('skeletal_mesh_asset').get_name()=='SK_GraphicAdventure'
   if FINISH:
    sk=mesh.get_editor_property('skeletal_mesh_asset');assert '/Finished/' in sk.get_path_name()
    assert u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(sk)==3
    assert len(sk.get_editor_property('materials'))==2
    report['lod_count']=3;report['material_slots']=2
    report['eye_cm']=str(car.get_editor_property('driver_eye_offset'))
   report['mass_kg']=mesh.get_mass();report['pawn_class']=car.get_class().get_name()
   report['ground_contacts']=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4)]
   assert all(report['ground_contacts']),report['ground_contacts']
   report['wheel_radii_cm']=[w.get_editor_property('wheel_radius') for w in move.get_editor_property('wheels')]
   assert all(abs(r-44.5)<.01 for r in report['wheel_radii_cm'])
   camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'GA_RuntimeCamera');camera.camera_component.set_field_of_view(45)
   camera_view((650,-640,350));move.set_handbrake_input(True);phase='front';last=now;save()
  elif phase=='front' and now-last>3:
   shot('UE_Front');phase='rear_wait';last=now
  elif phase=='rear_wait' and now-last>3:
   camera_view((-690,590,325));phase='rear';last=now
  elif phase=='rear' and now-last>3:
   shot('UE_Rear');phase='drive_start';last=now
  elif phase=='drive_start' and now-last>3:
   if CAPTURE_ONLY:
    car.set_chase_camera(False);pc.set_view_target_with_blend(car,0.);phase='cockpit';last=now;return
   car.set_chase_camera(True);pc.set_view_target_with_blend(car,0.)
   origin=car.get_actor_location();peak=0.;report['peak_drive_torque_nm']=[0.]*4
   car.reset_driving_inputs();move.set_handbrake_input(False);phase='drive';last=now;samples=0
  elif phase=='cockpit' and now-last>5:
   shot('UE_Cockpit');phase='capture_wait';last=now
  elif phase=='capture_wait' and now-last>3:
   camera_view((650,-640,350));car.get_component_by_class(u.SkeletalMeshComponent).set_forced_lod(2);phase='lod1';last=now
  elif phase=='lod1' and now-last>3:
   shot('UE_LOD1');phase='lod2_start';last=now
  elif phase=='lod2_start' and now-last>3:
   car.get_component_by_class(u.SkeletalMeshComponent).set_forced_lod(3);phase='lod2';last=now
  elif phase=='lod2' and now-last>3:
   shot('UE_LOD2');phase='finish_capture';last=now
  elif phase=='finish_capture' and now-last>3:
   report['renderer_enabled']=RENDER
   assert all(Path(p).exists() and Path(p).stat().st_size>10000 for p in report.get('images',[]))
   finish()
  elif phase=='drive':
   samples+=1
   move.set_throttle_input(.65);car.set_raw_steer(0.);peak=max(peak,car.get_velocity().length())
   for i,w in enumerate(car.get_drivetrain().wheels):report['peak_drive_torque_nm'][i]=max(report['peak_drive_torque_nm'][i],abs(w.get_editor_property('drive_torque_nm')))
   if now-last>6 and samples>=180:
    report['drive_frames']=samples;report['drive_wall_seconds']=now-last
    report['forward_distance_cm']=(car.get_actor_location()-origin).length();report['peak_speed_cm_s']=peak
    assert report['forward_distance_cm']>150 and peak>100,report
    report['wheel_rotation_deg']=[w.get_rotation_angle() for w in move.get_editor_property('wheels')]
    assert any(abs(v)>1 for v in report['wheel_rotation_deg'])
    assert min(report['peak_drive_torque_nm'])>1,report['peak_drive_torque_nm']
    shot('UE_Driving');brake_start=car.get_velocity().length();move.set_throttle_input(0);move.set_brake_input(1);phase='brake';last=now;samples=0;save()
  elif phase=='brake':
   samples+=1
   move.set_throttle_input(0);move.set_brake_input(1)
   if samples>=60:
    report['brake_start_cm_s']=brake_start;report['brake_end_cm_s']=car.get_velocity().length()
    assert report['brake_end_cm_s']<brake_start*.55,report
    car.reset_driving_inputs();steer_start=car.get_actor_rotation().yaw;phase='steer';last=now;samples=0
  elif phase=='steer':
   samples+=1
   move.set_throttle_input(.45);car.set_raw_steer(.7)
   if samples>=120:
    report['steer_yaw_change_deg']=abs((car.get_actor_rotation().yaw-steer_start+180)%360-180)
    assert report['steer_yaw_change_deg']>2,report
    report['final_roll_deg']=car.get_actor_rotation().roll;assert abs(report['final_roll_deg'])<35
    car.reset_driving_inputs();move.set_handbrake_input(True);phase='park';last=now;save()
  elif phase=='park' and now-last>3:
   assert pc.exit_car();assert isinstance(u.GameplayStatics.get_player_pawn(world,0),u.GTPlayerCharacter);phase='onfoot';last=now
  elif phase=='onfoot' and now-last>1:
   assert pc.enter_car();assert u.GameplayStatics.get_player_pawn(world,0)==car;report['exit_reenter']='PASS'
   report['renderer_enabled']=RENDER
   assert all(Path(p).exists() and Path(p).stat().st_size>10000 for p in report.get('images',[]))
   finish()
 except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
