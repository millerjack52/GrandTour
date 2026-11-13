"""Stationary runtime and full-coverage checks. No driving inputs."""
import unreal as u
from pathlib import Path
import json,time,traceback,math,hashlib,re,gc
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy';BASE='/Game/GrandTour/ArtTests/LidarStudy'
data=json.loads((OUT/'authoring.json').read_text());sites=json.loads((OUT/'installed-sites.json').read_text());report=dict(ok=False,driving_tested=False,sites=[],images=[])
world=pc=car=camera=None;busy=False;frame_samples=[];measure_frames=False

def save():(OUT/'check.json').write_text(json.dumps(report,indent=2))
def nums(s):return {k:float(v) for k,v in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',s)}
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world);deadline=time.monotonic()+180
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:
  assert time.monotonic()<deadline;yield .1

def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target);camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'LiDARReview')
 camera.camera_component.set_field_of_view(68);camera.camera_component.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);yield from settle(3)
 path=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 until=time.monotonic()+45
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
 u.GameplayStatics.set_game_paused(world,False);report['images'].append(str(path));save()

def run():
 global world,pc,car,measure_frames
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 install=json.loads((OUT/'install.json').read_text());assert install['ok'] and install['height_verified']
 for path,digest in install['protected_before'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
 actors=u.get_editor_subsystem(u.EditorActorSubsystem);refs=actors.get_all_level_actors();author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
 assert author.relief_tiles and author.road_pool_wet_samples>0,author.road_pool_wet_samples
 counts={}
 for a in refs:
  if a.get_actor_label() in ['LidarStudy_Forest','LidarStudy_Understory']:
   counts[a.get_actor_label()]={c.static_mesh.get_name():c.get_instance_count() for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh}
 report['instances']=counts;report['relief_triangles']=author.relief_triangles;report['road_pool_wet_samples']=author.road_pool_wet_samples
 assert sum(n for k,n in counts['LidarStudy_Forest'].items() if k.startswith('SM_Fir'))==data['trees']
 assert sum(counts['LidarStudy_Understory'].values())==data['understory']
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 deadline=time.monotonic()+180
 while not world:
  world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<deadline;yield .5
 pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert isinstance(car,u.GTCarPawn);pc.possess(car)
 car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement();move.set_brake_input(0);move.set_throttle_input(0);move.set_handbrake_input(True)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
 import sys
 sys.path.insert(0,str(ROOT/'Art/Unreal'))
 import lidar_gravel_dust
 lidar_gravel_dust.validate(world)
 for site in sites:
  x,y=site['center'];z=site['center_height_cm'];car.set_actor_location_and_rotation(u.Vector(x,y,z+100),u.Rotator(yaw=site['yaw']),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(12)
  frame_samples.clear();measure_frames=True
  poses=[]
  for _ in range(5):
   yield from settle(.4);p=car.get_actor_location();r=car.get_actor_rotation();poses.append(dict(z=p.z,pitch=r.pitch,roll=r.roll,speed=car.get_velocity().length(),contacts=sum(bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(k))[0]) for k in range(4))))
  measure_frames=False
  native=nums(move.native_substance_report());sample=surface.sample_surface(u.Vector2D(x,y));row=dict(name=site['name'],poses=poses,native=native,mud_depth_cm=sample.sinkage_cap_cm,grass=grass.grass.get_instance_count(),distant_grass=grass.distant_grass.get_instance_count(),body=nums(move.body_soil_report()));row['editor_frame_ms_mean']=1000*sum(frame_samples)/max(1,len(frame_samples));row['frame_samples']=len(frame_samples);report['sites'].append(row);save()
  yaw=math.radians(site['yaw']);fx,fy=math.cos(yaw),math.sin(yaw)
  yield from capture(site['name'].replace(' ','_'),(x-fx*800-fy*220,y-fy*800+fx*220,z+450),(x+fx*900,y+fy*900,z+100))
  assert all(q['contacts']>=3 and abs(q['roll'])<25 and abs(q['pitch'])<30 for q in poses[-3:]),row
  assert row['grass']>100 and row['distant_grass']>500,row
  assert abs(car.get_drivetrain().get_drive_input())<.001
 # Overview from the central area; grass remains budgeted around the player.
 site=sites[0];x,y=site['center'];z=site['center_height_cm']
 yield from capture('Woodland_overview',(x-17000,y+18000,z+18000),(x+10000,y-12000,z+1000))
 report['surface']=surface.get_surface_report();report['protected_unchanged']=len(install['protected_before']);report['ok']=True;save();yield from finish()

def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=camera=None;gc.collect()
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');world=None;yield 2
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if measure_frames and 0<dt<1:frame_samples.append(dt)
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<800,'Check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
