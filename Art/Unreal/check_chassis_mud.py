"""Maximum-softness bog behind the existing spawn; owned authoring assets only."""
import unreal as u
import json, math, time, traceback, hashlib, shutil, re, gc
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ChassisMud';OUT.mkdir(parents=True,exist_ok=True)
LEVEL='/Game/GrandTour/ArtTests/ProceduralGround/L_BigMountain_Authoring'
headless='-GTDensityNoVisual' in u.SystemLibrary.get_command_line()
REPORT=OUT/'check.json'
report=dict(ok=False,driving_tested=False);busy=False;deadline=0;world=None
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
def save():REPORT.write_text(json.dumps(report,indent=2))
def props(a,**values):
 for k,v in values.items():a.set_editor_property(k,v)
 return a
def nums(s):return {k:float(v) for k,v in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',s)}
def protected():
 p=json.loads((OUT/'install.json').read_text())['protected']
 for name,h in p.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 report['protected_unchanged']=len(p)
def review():
 global world
 functional=json.loads((ROOT/'Art/Export/ProceduralGround/startbog-functional.json').read_text());assert functional['ok'];p=functional['probe']
 assert les.load_level(LEVEL);les.editor_set_viewport_realtime(False)
 assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 until=time.monotonic()+180;car=None
 while car is None:
  yield .5;world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car()
  assert time.monotonic()<until
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement()
 move.set_editor_property('reverse_as_brake',False);move.set_use_automatic_gears(False);move.set_target_gear(0,True);move.set_brake_input(0);move.set_throttle_input(0);move.set_handbrake_input(True)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent);surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 tiles=u.GameplayStatics.get_all_actors_of_class(world,u.GTRoadReliefTile)
 assert tiles and all(t.mesh.get_collision_enabled()==u.CollisionEnabled.QUERY_ONLY and t.mineral_base.get_collision_enabled()==u.CollisionEnabled.PHYSICS_ONLY for t in tiles)
 report['split_collision_tiles']=len(tiles)
 # Work a broad footprint to the deep state without driving. Chassis support
 # must cross the old upper surface; the previous collision would prevent it.
 for repeat in range(70):
  for dx in range(-300,301,50):
   for dy in range(-300,301,50):surface.apply_review_native_contact(u.Vector2D(p['x']+dx,p['y']+dy),2.)
 tile=next(t for t in tiles if t.get_actor_location().x<=p['x']<t.get_actor_location().x+t.span_cm and t.get_actor_location().y<=p['y']<t.get_actor_location().y+t.span_cm)
 report['mineral_z']=tile.mineral_height_at(u.Vector2D(p['x'],p['y']))
 report['upper_z']=tile.height_at(u.Vector2D(p['x'],p['y']))
 car.set_actor_location_and_rotation(u.Vector(p['x'],p['y'],p['z']+110),u.Rotator(yaw=functional['start_yaw']+180),False,True)
 mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'StartBogReview')
 target=u.Vector(p['x'],p['y'],p['z']);eye=target+u.Vector(950,-1300,950)
 camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,target),False,True);camera.camera_component.set_field_of_view(70)
 for cmd in ['DisableAllScreenMessages','showhud','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 pc.set_view_target_with_blend(camera,0)
 end=u.GameplayStatics.get_time_seconds(world)+14;timeout=time.monotonic()+240
 while u.GameplayStatics.get_time_seconds(world)<end or not nums(surface.get_surface_report()).get('textures_ready',0):
  assert time.monotonic()<timeout;yield .2
 pc.set_view_target_with_blend(camera,0);yield 2
 report['body']=nums(move.body_soil_report());report['native']=nums(move.native_substance_report());report['soil']=nums(surface.get_surface_report());report['probe']=p
 report['drive_input']=car.get_drivetrain().get_drive_input();assert abs(report['drive_input'])<.0001
 assert report['native']['soil_contacts']>=3 and report['native']['native_mud_contacts']>=3,report['native']
 assert report['soil']['push_cells']>0,report['soil']
 report['wheel_samples']=[]
 report['car_position']=list(car.get_actor_location().to_tuple());report['car_velocity']=list(car.get_velocity().to_tuple())
 for i,w in enumerate(car.get_traction().wheels):
  s=surface.sample_surface(u.Vector2D(w.contact_point.x,w.contact_point.y))
  ws=u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))
  report['wheel_samples'].append(dict(depth=s.sinkage_cap_cm,softness=s.softness,q=s.native_extrude_cm,delta=s.surface_delta_cm,tread_cm_s=w.tread_cm_per_s,contact=w.get_editor_property('bInContact'),spring_force=ws[4],drive_torque=ws[11],brake_torque=ws[12]))
 path=OUT/'Chassis_sunk.png';stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 until=time.monotonic()+45
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
 report['image']=str(path);save()
 assert report['body']['peak_immersion_cm']>10,report['body']
 assert report['body']['base_gap_cm']>-5,report['body']
 assert report['body']['body_steps']>0,report['body']
 assert car.get_velocity().length()<10,report['car_velocity']
 # Independent rigid-body drops verify that the solid base still catches
 # bodies and that firm road collision was not disabled with the upper mesh.
 # Move the parked vehicle clear after recording its result so the deep
 # bog itself is available for an independent collision probe.
 car.set_actor_location(u.Vector(p['x']+3000,p['y']+3000,p['z']+1000),False,True)
 mesh.set_simulate_physics(False)
 candidates={'firm':[],'deep':[]}
 for t in tiles:
  o=t.get_actor_location()
  for fx in [.1,.2,.3,.4,.5,.6,.7,.8,.9]:
   for fy in [.1,.2,.3,.4,.5,.6,.7,.8,.9]:
    xy=u.Vector2D(o.x+t.span_cm*fx,o.y+t.span_cm*fy);top=t.height_at(xy);base=t.mineral_height_at(xy);depth=top-base
    slope=math.hypot(t.mineral_height_at(xy+u.Vector2D(25,0))-t.mineral_height_at(xy-u.Vector2D(25,0)),t.mineral_height_at(xy+u.Vector2D(0,25))-t.mineral_height_at(xy-u.Vector2D(0,25)))/50
    kind='firm' if depth<.01 else 'deep' if depth>60 else None
    if kind and slope<.3:candidates[kind].append((slope,t,xy,top,base))
 probes={}
 for kind,choices in candidates.items():
  for slope,t,xy,top,base in sorted(choices,key=lambda c:c[0]):
   hit=u.SystemLibrary.line_trace_single(world,u.Vector(xy.x,xy.y,top+150),u.Vector(xy.x,xy.y,top-150),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[car,camera],u.DrawDebugTrace.NONE,True).to_tuple()
   if not any(v==t for v in hit):continue
   actor=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=u.Vector(xy.x,xy.y,top+80),scale=u.Vector(.2,.2,.2)),'CollisionDrop_'+kind)
   comp=actor.static_mesh_component;comp.set_mobility(u.ComponentMobility.MOVABLE);comp.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));comp.set_collision_profile_name('PhysicsActor');comp.set_simulate_physics(True)
   probes[kind]=(actor,top,base,slope);break
 assert set(probes)=={'firm','deep'}, {k:len(v) for k,v in candidates.items()}
 end=u.GameplayStatics.get_time_seconds(world)+6
 u.GameplayStatics.set_game_paused(world,False)
 while u.GameplayStatics.get_time_seconds(world)<end:yield .1
 report['rigid_drops']={}
 for kind,(actor,start_top,start_base,slope) in probes.items():
  pos=actor.get_actor_location();xy=u.Vector2D(pos.x,pos.y)
  t=next(t for t in tiles if t.get_actor_location().x<=pos.x<t.get_actor_location().x+t.span_cm and t.get_actor_location().y<=pos.y<t.get_actor_location().y+t.span_cm)
  top=t.height_at(xy);base=t.mineral_height_at(xy);bottom=pos.z-10
  row=dict(top=top,base=base,bottom=bottom,base_error_cm=bottom-base,speed=actor.get_velocity().length(),initial_slope=slope,initial_top=start_top,initial_base=start_base);report['rigid_drops'][kind]=row
  save()
  assert -5<row['base_error_cm']<8,row
  if kind=='deep':assert top-bottom>50,row
  actor.destroy_actor()
 report.update(ok=True,stationary_contact_verified=True);save()
 u.GameplayStatics.set_game_paused(world,False);camera.destroy_actor();u.EditorLevelLibrary.editor_end_play();yield 3
 world=pc=car=move=mesh=surface=camera=tile=tiles=t=actor=comp=candidates=probes=choices=hit=None
 gc.collect()
 until=time.monotonic()+60
 while u.EditorLevelLibrary.get_game_world():assert time.monotonic()<until;yield .5
 les.load_level('/Engine/Maps/Entry');yield 3
steps=review()
def tick(dt):
 global busy,deadline,steps
 if busy:return
 busy=True
 try:
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle)
  if world:u.GameplayStatics.set_game_paused(world,False);u.EditorLevelLibrary.editor_end_play()
  u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
