"""Saved-map and stationary runtime checks. No test driving."""
import unreal as u
from pathlib import Path
import json,time,traceback,math,hashlib,re,gc
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/NativeRoad';BASE='/Game/GrandTour/ArtTests/NativeRoad'
data=json.loads((OUT/'authoring.json').read_text());report=dict(ok=False,driving_tested=False,sites=[],images=[])
WATER_ONLY='-GTWaterOnly' in u.SystemLibrary.get_command_line()
ENRICH='-GTEnrichCheck' in u.SystemLibrary.get_command_line()
if WATER_ONLY:
 report=json.loads((OUT/'check.json').read_text());report.update(ok=False,water_mesh_rechecked=True)
 report.pop('validation_correction',None);report.pop('water_stepping_frames',None)
world=pc=car=camera=None;busy=False
def save():(OUT/('enrichcheck.json' if ENRICH else 'watercheck.json' if WATER_ONLY else 'check.json')).write_text(json.dumps(report,indent=2))
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:yield 0
def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target);camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'NativeRoadReview')
 camera.get_component_by_class(u.CameraComponent).set_field_of_view(65);camera.get_component_by_class(u.CameraComponent).set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);yield from settle(3)
 if name=='Native_pool':
  sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
  report['water_capture_diagnostics']=sheet.water_diagnostics()
  report['water_capture_steady']=('clamps 0, deficit 0.000 s' in report['water_capture_diagnostics'])
 path=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 until=time.monotonic()+45
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
 u.GameplayStatics.set_game_paused(world,False);report['images'].append(str(path));save()
def run():
 global world,pc,car
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_NativeRoad')
 install=json.loads((OUT/'install.json').read_text());assert install['ok'] and install['height_verified']
 material_audit={}
 for name in ['Terrain','Detail','Tread']:
  m=u.load_asset(BASE+'/M_'+name);codes=[str(e.get_editor_property('code')) for e in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCustom)]
  assert not any('125000' in c or '250000' in c for c in codes),'Old atlas mapping in '+name
  material_audit[name]=len(codes)
 report['material_atlas_audit']=material_audit
 if ENRICH:
  enrichment=json.loads((OUT/'enrich.json').read_text());assert enrichment['ok'] and enrichment['height_sha256']==data['terrain_sha256']
 for path,digest in install['protected_before'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 24
 world=u.EditorLevelLibrary.get_game_world();assert world;pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0);assert isinstance(car,u.GTCarPawn)
 car.disable_input(pc);move=car.get_chaos_movement();move.set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 surfaces=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface);assert len(surfaces)==1;s=surfaces[0]
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails))
 effects=u.GameplayStatics.get_all_actors_of_class(world,u.GTVehicleSurfaceEffects);assert effects and all(a.dust_intensity==0 for a in effects)
 for i,site in enumerate([] if WATER_ONLY else data['sites'],1):
  x,y=site['center'];z=site['center_height_cm'];pc.select_lane(i);car.disable_input(pc);move.set_handbrake_input(True);yield from settle(5)
  poses=[]
  for _ in range(6):
   yield from settle(.5);p=car.get_actor_location();r=car.get_actor_rotation();poses.append(dict(z=p.z,pitch=r.pitch,roll=r.roll,speed=car.get_velocity().length(),contacts=sum(bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(k))[0]) for k in range(4))))
  assert all(p['contacts']>=3 and abs(p['roll'])<25 and abs(p['pitch'])<30 for p in poses[-3:]),(site['name'],poses)
  assert max(p['z'] for p in poses[-3:])-min(p['z'] for p in poses[-3:])<8,(site['name'],poses)
  sample=s.sample_surface(u.Vector2D(x,y));assert sample.sinkage_cap_cm>0
  row=dict(name=site['name'],poses=poses,mud_depth_cm=sample.sinkage_cap_cm,grass=grass.grass.get_instance_count(),distance_grass=grass.distant_grass.get_instance_count());report['sites'].append(row)
  assert row['grass']==data['native_grass_instances'],row
  yaw=math.radians(site['yaw']);fx,fy=math.cos(yaw),math.sin(yaw)
  yield from capture(site['name'],(x-fx*600-fy*120,y-fy*600+fx*120,z+350),(x+fx*300,y+fy*300,z+80))
  if i==1:
   candidates=[]
   for dx in range(-1200,1201,200):
    for dy in range(-1200,1201,200):
     if math.hypot(dx,dy)<400:continue
     q=s.sample_surface(u.Vector2D(x+dx,y+dy))
     if q.sinkage_cap_cm>6:candidates.append((q.sinkage_cap_cm,x+dx,y+dy))
   assert candidates;_,tx,ty=max(candidates);before=s.sample_surface(u.Vector2D(tx,ty)).surface_delta_cm
   for _ in range(12):s.apply_review_soil_stroke(u.Vector2D(tx-100,ty),u.Vector2D(tx+100,ty),30,7,.35);yield from settle(.05)
   after=s.sample_surface(u.Vector2D(tx,ty)).surface_delta_cm;assert after<before-.3
   report['synthetic_deformation_cm']=after-before
 # A wide stationary view makes the route's landform and lake placement reviewable.
 site=data['sites'][-1];x,y=site['center'];z=site['center_height_cm']
 yield from capture('Native_section_overview',(x+7000,y-6000,z+6500),(0,0,2000))
 sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
 probe=json.loads((OUT/'water-probe.json').read_text());wx,wy=probe['point'];wz=probe['surface_cm']
 assert sheet.covers(u.Vector2D(wx,wy)),'Shore probe is dry'
 assert abs(sheet.surface_cm_at(u.Vector2D(wx,wy))-wz)<1
 # Stationary placement in shallow water exercises the active field without
 # throttle or steering. The user drives the route.
 car.set_actor_location(u.Vector(wx,wy,wz+100),False,True);yield from settle(6)
 report['water_arrival_diagnostics']=sheet.water_diagnostics(True)
 report['water_probe']=probe
 yield from capture('Native_pool',(wx+1200,wy+800,wz+650),(wx-200,wy-500,wz))
 mats=[a.static_mesh_component.get_material(0) for a in sheet.get_editor_property('domain_surfaces')]
 assert mats and all(isinstance(m,u.MaterialInstanceDynamic) and m.get_scalar_parameter_value('AmbientReady')==1 for m in mats)
 tex=mats[0].get_texture_parameter_value('AmbientTex');a=u.RenderingLibrary.read_render_target_raw_pixel(world,tex,100,150,False);yield from settle(.7);b=u.RenderingLibrary.read_render_target_raw_pixel(world,tex,100,150,False)
 report['wave_delta']=max(abs(a.r-b.r),abs(a.g-b.g),abs(a.b-b.b));assert report['wave_delta']>.0001
 report['water_diagnostics']=sheet.water_diagnostics();assert 'over 0 stepping frames' not in report['water_diagnostics']
 report['water_stepping_frames']=int(re.search(r'over (\d+) stepping frames',report['water_diagnostics'])[1])
 report['surface_report']=s.get_surface_report()
 owner=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='NativeRoad_NativeDebris')
 report['grass_contacts']=grass.grass_report()
 report['native_debris_instances']=sum(c.get_instance_count() for c in owner.get_components_by_class(u.InstancedStaticMeshComponent));assert report['native_debris_instances']==data['debris']
 clods=[c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name().startswith('SM_plants_mud_chunk')]
 assert len(clods)==2 and all(c.get_collision_enabled()==u.CollisionEnabled.QUERY_AND_PHYSICS for c in clods)
 ignore=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a!=owner];report['clod_collision_traces']=0
 for c in clods:
  for index in [0,c.get_instance_count()//2,c.get_instance_count()-1]:
   t=c.get_instance_transform(index,True);point=u.MathLibrary.transform_location(t,c.static_mesh.get_bounds().origin)
   hit=u.SystemLibrary.line_trace_single(world,point+u.Vector(0,0,100),point-u.Vector(0,0,100),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,u.DrawDebugTrace.NONE,True)
   assert hit is not None,(c.static_mesh.get_name(),index)
   parts=hit.to_tuple();hit_actor=next((v for v in parts if isinstance(v,u.Actor)),None)
   assert parts[0] and hit_actor==owner,(c.static_mesh.get_name(),index,str(parts))
   report['clod_collision_traces']+=1
 p=grass.grass.get_instance_transform(0,True).translation
 grass.apply_review_grass_contact(u.Vector2D(p.x,p.y),True);yield from settle(.25)
 report['synthetic_grass_contact']=grass.grass_report();assert int(re.search(r'removed=(\d+)',report['synthetic_grass_contact'])[1])>0
 frames=[]
 for _ in range(120):
  frames.append(u.GameplayStatics.get_world_delta_seconds(world));yield 0
 frames.sort();report['stationary_frame_ms']={'median':frames[len(frames)//2]*1000,'p95':frames[int(len(frames)*.95)]*1000,'samples':len(frames),'cap_fps':60}
 report['ok']=True;save()
 yield from finish()
def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 if camera:camera.destroy_actor()
 camera=pc=car=None
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=None
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');yield 4
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<800,'Check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle)
  # Release the completed generator and its PIE UObject wrappers before Python
  # and the object subsystem are torn down by editor shutdown.
  steps=None;gc.collect();u.SystemLibrary.collect_garbage();u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
