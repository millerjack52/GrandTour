"""Saved-route water/collision readbacks and high/low-range driving smoke tests."""
from pathlib import Path
import os
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
import lidar_logging_trial as trial
report=dict(ok=False,owner_drive_pending=True,runs=[],images=[])
RD1_LOOK_CM=300.;RD1_THROTTLE=.65
CONTACT_ONLY=os.environ.get('GT_LOGGING_CONTACT_ONLY')=='1'
report['contact_only']=CONTACT_ONLY

def save():(OUT/'loggingcheck.json').write_text(json.dumps(report,indent=2))

def run():
 global world,pc,car,drive_on,drive_cmd
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround));sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
 tiles=list(author.relief_tiles.values())
 def ground(x,y,mineral=False):
  for t in tiles:
   o=t.get_actor_location()
   if o.x<=x<o.x+t.span_cm and o.y<=y<o.y+t.span_cm:return t.mineral_height_at(u.Vector2D(x,y)) if mineral else t.height_at(u.Vector2D(x,y))
  return author.base_height_at(u.Vector2D(x,y))
 path=trial.route(json.loads((OUT/'roads.json').read_text()));assert path
 trial_spec=trial.specification()
 built=next(a for a in refs if isinstance(a,u.GTProceduralRoad) and a.actor_has_tag('LidarMudTrack'))
 widths=[built.width_cm*built.control_points.get_scale_at_spline_point(k).y/100 for k in range(built.control_points.get_number_of_spline_points())]
 report['width_range_m']=[min(widths),max(widths)];assert min(widths)<2.4 and max(widths)>4.1,report['width_range_m']
 report['pools']=trial.verify_pools(author,sheet,path,ground)
 report['river_pond_probes']=[]
 for spec in data['water']:
  x,y,z=spec['probe'];xy=u.Vector2D(x,y);assert sheet.covers(xy) and abs(sheet.surface_cm_at(xy)-z)<2
  report['river_pond_probes'].append(dict(name=spec['name'],surface_cm=sheet.surface_cm_at(xy)))
 # Physical pool depths come from the final bed, and remain queryable after reload.
 for bog in report['pools']['bogs']:
  p=bog['probe'];xy=u.Vector2D(p['x'],p['y']);assert sheet.covers(xy) and abs(sheet.surface_cm_at(xy)-p['z'])<2
 save()
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 until=time.monotonic()+180
 while not world:
  world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<until;yield .5
 pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();pc.possess(car);car.disable_input(pc)
 mv=car.get_chaos_movement();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 for command in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:u.SystemLibrary.execute_console_command(world,command,pc)
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 report['soil_probes']=[]
 for label,station in [('dirt',40.),('solid_mud',170.),('first_hollow',214.),('rutted_saddle',290.),('dry_crest',430.),('wet_shelf',552.),('deep_gully',667.)]:
  x,y,_=trial.at(path,station,.85);q=surface.sample_surface(u.Vector2D(x,y))
  report['soil_probes'].append(dict(name=label,station_m=station,sinkage_cap_cm=q.sinkage_cap_cm,softness=q.softness,wetness=q.wetness,water_depth_cm=q.water_depth_cm,native_extrude_cm=q.native_extrude_cm,bearing_strength=q.bearing_strength,surface_tag=str(q.surface_tag)))
 assert report['soil_probes'][-1]['sinkage_cap_cm']>3*report['soil_probes'][0]['sinkage_cap_cm'],report['soil_probes']
 assert report['soil_probes'][-1]['softness']>report['soil_probes'][0]['softness'],report['soil_probes']
 save()
 movable=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.actor_has_tag('LidarLoggingMovable')]
 assert len(movable)==len(trial_spec['obstacles']),('Missing movable obstacles',len(movable))
 mv.set_handbrake_input(True);yield from settle(8)
 report['movable_obstacles']=[]
 for a in movable:
  c=a.static_mesh_component;assert c.is_simulating_physics(),a.get_actor_label()
  assert c.get_collision_enabled()==u.CollisionEnabled.QUERY_AND_PHYSICS
  center,extent=a.get_actor_bounds(False);top=center.z+extent.z-ground(center.x,center.y)
  mineral_top=center.z+extent.z-ground(center.x,center.y,True)
  report['movable_obstacles'].append(dict(actor=a.get_actor_label(),kind='clump' if a.actor_has_tag('LoggingMudClump') else 'log',mass_kg=c.get_mass(),simulating=True,top_above_ground_cm=top,top_above_mineral_cm=mineral_top))
 save()
 # Rigid clods may sink into yielding mud; the mineral bed is the physical floor.
 assert all(b['top_above_mineral_cm']>2 for b in report['movable_obstacles']),('Objects fell through mineral bed',[b for b in report['movable_obstacles'] if b['top_above_mineral_cm']<=2])
 clumps=[b for b in report['movable_obstacles'] if b['kind']=='clump']
 assert sum(b['top_above_ground_cm']>2 for b in clumps)>=math.ceil(.9*len(clumps)),('Too many clumps hidden under mud',clumps)
 assert all(b['top_above_ground_cm']>2 for b in report['movable_obstacles'] if b['kind']=='log'),'A fallen log disappeared below the surface'
 pts=[p[:2] for p in path['points_cm']];cum=[0.]
 for a,b in zip(pts,pts[1:]):cum.append(cum[-1]+math.dist(a,b))
 # Same uphill entry in both ranges; bog resistance is allowed to stop the car.
 for low in ([] if CONTACT_ONLY else [False,True]):
  x,y,yaw=trial.at(path,159.)
  car.set_actor_location_and_rotation(u.Vector(x,y,ground(x,y)+100),u.Rotator(yaw=yaw),False,True)
  mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
  car.reset_driving_inputs();mv.set_throttle_input(0);mv.set_brake_input(0);mv.set_handbrake_input(True)
  car.get_drivetrain().set_low_range(low);car.get_drivetrain().set_diff_lock(True);yield from settle(8)
  tuning=car.get_component_by_class(u.GTVehicleTuningComponent).get_current()
  assert abs(tuning.max_engine_torque-480)<.1,('Power tune not active',tuning.max_engine_torque)
  p=car.get_actor_location();s0,_=rd1_project(pts,cum,p.x,p.y);now=u.GameplayStatics.get_time_seconds(world)
  drive_cmd=dict(pts=pts,cum=cum,s=s0,max_off=0.,t0=now,t_last=-1.,trace=[])
  mv.set_handbrake_input(False);drive_on=True
  max_torque=0.;deadline=time.monotonic()+180
  while u.GameplayStatics.get_time_seconds(world)-now<24 and drive_cmd['s']-s0<3000:
   assert time.monotonic()<deadline
   max_torque=max(max_torque,car.get_drivetrain().get_engine_torque_nm());yield .1
  drive_on=False;mv.set_throttle_input(0);mv.set_handbrake_input(True);car.set_raw_steer(0)
  progress=(drive_cmd['s']-s0)/100
  row=dict(low_range=low,progress_m=progress,max_engine_torque_nm=max_torque,max_offset_m=drive_cmd['max_off']/100,trace=drive_cmd['trace'],drivetrain=car.get_drivetrain().describe())
  report['runs'].append(row);save()
  assert max_torque>150 and progress>3,('Car cannot pull up entry',row)
  yield from settle(2)
 report['bog_drives']=[]
 for condition in ([] if CONTACT_ONLY else [c for c in path['conditions'] if c.get('water_fill_cm',0)>0]):
  x,y,yaw=trial.at(path,condition['start_metres']-4)
  car.set_actor_location_and_rotation(u.Vector(x,y,ground(x,y)+100),u.Rotator(yaw=yaw),False,True)
  mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
  car.reset_driving_inputs();mv.set_throttle_input(0);mv.set_brake_input(0);mv.set_handbrake_input(True)
  car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True);yield from settle(5)
  p=car.get_actor_location();s0,_=rd1_project(pts,cum,p.x,p.y);now=u.GameplayStatics.get_time_seconds(world)
  target=(condition['end_metres']-condition['start_metres']+8)*100
  drive_cmd=dict(pts=pts,cum=cum,s=s0,max_off=0.,t0=now,t_last=-1.,trace=[])
  mv.set_handbrake_input(False);drive_on=True;deadline=time.monotonic()+240
  while u.GameplayStatics.get_time_seconds(world)-now<45 and drive_cmd['s']-s0<target:
   assert time.monotonic()<deadline;yield .1
  drive_on=False;mv.set_throttle_input(0);mv.set_handbrake_input(True);car.set_raw_steer(0)
  progress=drive_cmd['s']-s0
  row=dict(name=condition['name'],progress_m=progress/100,target_m=target/100,cleared=progress>=target,max_offset_m=drive_cmd['max_off']/100,trace=drive_cmd['trace'])
  report['bog_drives'].append(row);save()
  assert progress>400,('Cannot enter bog in low range',row)
 # Isolate obstacle contact from bog traversal. Settle the log first, then give
 # the car a measured rolling approach so stationary sinkage cannot prevent impact.
 log=next(a for a in movable if a.get_actor_label()=='LidarStudy_LoggingDetail_movable_1')
 x,y,yaw=trial.at(path,325.);car.set_actor_location_and_rotation(u.Vector(x,y,ground(x,y)+100),u.Rotator(yaw=yaw),False,True)
 mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
 mv.set_handbrake_input(True);car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True);yield from settle(8)
 baseline=log.get_actor_location();yield from settle(2);rest=log.get_actor_location()
 drift=(rest-baseline).length();assert drift<10,('Log has not settled before contact test',drift)
 x,y,yaw=trial.at(path,332.)
 car.set_actor_location_and_rotation(u.Vector(x,y,ground(x,y)+70),u.Rotator(yaw=yaw),False,True)
 mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(1)
 mesh.set_physics_linear_velocity(u.Vector(math.cos(math.radians(yaw))*250,math.sin(math.radians(yaw))*250,0))
 p=car.get_actor_location();s0,_=rd1_project(pts,cum,p.x,p.y);now=u.GameplayStatics.get_time_seconds(world)
 drive_cmd=dict(pts=pts,cum=cum,s=s0,max_off=0.,t0=now,t_last=-1.,trace=[])
 mv.set_handbrake_input(False);drive_on=True;displacement=0.;nearest=1.e9;deadline=time.monotonic()+180
 while u.GameplayStatics.get_time_seconds(world)-now<16 and drive_cmd['s']-s0<800:
  assert time.monotonic()<deadline
  displacement=max(displacement,(log.get_actor_location()-rest).length())
  nearest=min(nearest,(log.get_actor_location()-car.get_actor_location()).length());yield .1
 drive_on=False;mv.set_throttle_input(0);mv.set_handbrake_input(True);car.set_raw_steer(0)
 report['log_push']=dict(displacement_cm=displacement,settled_drift_cm=drift,closest_car_cm=nearest,progress_m=(drive_cmd['s']-s0)/100,rolling_start_cm_s=250)
 p=car.get_actor_location();report['log_push']['car_position_cm']=[p.x,p.y,p.z]
 cx,cy,_=trial.at(path,322.);tx,ty,_=trial.at(path,338.)
 yield from capture('Logging_contact',(cx,cy,ground(cx,cy)+350),(tx,ty,ground(tx,ty)+60))
 save();assert displacement>10 and nearest<300,('Car did not move the settled log',report['log_push'])
 # A representative loose mud clump must also have a working rigid body.
 chunk=next(a for a in movable if a.actor_has_tag('LoggingMudClump'));c=chunk.static_mesh_component
 before=chunk.get_actor_location();c.add_impulse(u.Vector(120,0,70),'',True);yield from settle(1)
 report['clump_impulse_displacement_cm']=(chunk.get_actor_location()-before).length()
 assert report['clump_impulse_displacement_cm']>5
 # Captures put the car near each subject to stream the same ground/foliage as a drive.
 for name,station in ([] if CONTACT_ONLY else trial_spec['captures']):
  x,y,yaw=trial.at(path,station);z=ground(x,y)
  car.set_actor_location_and_rotation(u.Vector(x,y,z+100),u.Rotator(yaw=yaw),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());mv.set_handbrake_input(True);yield from settle(8)
  # Keep the camera inside the cleared route, rather than behind roadside foliage.
  cx,cy,_=trial.at(path,max(0,station-8));tx,ty,_=trial.at(path,station+8)
  yield from capture(name,(cx,cy,ground(cx,cy)+300),(tx,ty,ground(tx,ty)+60))
 report['ok']=True;save()
 refs=author=sheet=tiles=surface=mesh=mv=ground=movable=built=log=chunk=c=None;gc.collect()
 yield from finish()

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed,drive_on
 if busy:return
 busy=True
 try:
  if drive_on and car:drive_ctrl()
  assert time.monotonic()-began<1200,'Logging trial timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  drive_on=False;report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
