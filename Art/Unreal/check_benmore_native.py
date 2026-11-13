"""Saved-level, fixed-camera and synthetic-contact checks. No throttle or driving."""
import unreal as u
from pathlib import Path
import json,time,traceback,math,array,hashlib,re
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreNative'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
data=json.loads((OUT/'authoring.json').read_text());report={'ok':False,'images':[],'driving_tested':False,'deformation':{}}
world=pc=car=camera=None;busy=False
def save():(OUT/'check.json').write_text(json.dumps(report,indent=2))
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:yield 0
def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'NativeReview')
 camera.get_component_by_class(u.CameraComponent).set_field_of_view(65)
 pc.set_view_target_with_blend(camera,0);yield from settle(2)
 f=OUT/(name+'.png');stamp=time.time()
 u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+f.as_posix()+'"',pc)
 deadline=time.monotonic()+45
 while not f.exists() or f.stat().st_mtime<stamp:assert time.monotonic()<deadline;yield .3
 report['images'].append(str(f));u.GameplayStatics.set_game_paused(world,False);save()
def run():
 global world,pc,car
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(LEVEL)
 mapfile=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'
 # Reuse a successful export only while its map file is older than that export.
 # Subsequent map installation invalidates the proof automatically.
 checked=OUT/'checked-height.r16'
 cached=checked.exists() and checked.stat().st_mtime>mapfile.stat().st_mtime and hashlib.sha256(checked.read_bytes()).hexdigest()==data['terrain_sha256']
 if cached:
  report['terrain_sha256']=data['terrain_sha256'];report['height_proof_reused']=True
 else:
  editor=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  land=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.Landscape))
  rt=u.RenderingLibrary.create_render_target2d(editor,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);yield 12
  assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 10
  assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 5
  pixels=u.RenderingLibrary.read_render_target(editor,rt,False);heights=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
  checked.write_bytes(heights.tobytes())
  report['terrain_sha256']=hashlib.sha256(heights.tobytes()).hexdigest();report['height_range']=[min(heights),max(heights)];assert report['terrain_sha256']==data['terrain_sha256']
  rt=editor=land=None
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 18
 world=u.EditorLevelLibrary.get_game_world();assert world;pc=u.GameplayStatics.get_player_controller(world,0)
 pawn=u.GameplayStatics.get_player_pawn(world,0);cars=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn)
 car=pawn if isinstance(pawn,u.GTCarPawn) else cars[0];pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement();move.set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 surfaces=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface);visuals=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)
 assert len(surfaces)==3 and len(visuals)==3
 assert not u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch),'Legacy crossing overlays must be retired'
 sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
 land=u.GameplayStatics.get_all_actors_of_class(world,u.Landscape)[0];assert not land.get_editor_property('hidden')
 report['visuals']=[v.get_research_report() for v in visuals];report['water_queries']={}
 for x,y in [(-68000,22000),(-40375,43750),(-166800,-2700)]:
  report['water_queries'][str((x,y))]=dict(covers=sheet.covers(u.Vector2D(x,y)),surface_cm=sheet.surface_cm_at(u.Vector2D(x,y)))
 for x,y in [(-68000,22000),(-166800,-2700)]:
  level=sheet.surface_cm_at(u.Vector2D(x,y))
  wet=u.GTLandscapeSurface.query_wheel_surface(car,u.Vector(x,y,level-20),u.Vector2D(1,0),25)
  above=u.GTLandscapeSurface.query_wheel_surface(car,u.Vector(x,y,level+300),u.Vector2D(1,0),25)
  assert wet.native_water_response and not above.native_water_response,(x,y)
 report['water_contact_height_gate']=True
 # Teleport solely to load each bounded contact field; parked throughout.
 for site in data['sites']:
  name=site['name'];x,y=site['center'];z=site['center_height_cm']
  body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector())
  car.set_actor_transform(u.Transform(location=u.Vector(x,y,z+80),rotation=u.Rotator(yaw=0),scale=car.get_actor_scale3d()),False,True)
  move.reset_vehicle();car.reset_driving_inputs();move.set_handbrake_input(True)
  parked=[]
  for _ in range(10):
   yield from settle(.5)
   p=car.get_actor_location();r=car.get_actor_rotation();vel=car.get_velocity()
   parked.append(dict(x=p.x,y=p.y,z=p.z,pitch=r.pitch,roll=r.roll,speed_cm_s=vel.length(),wheel_contacts=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(len(move.get_editor_property('wheels')))]))
  report.setdefault('parked_samples',{})[name]=parked
  # ResetVehicle invalidates Chaos's cached suspension state after a teleport.
  # Require sustained support and a settled pose; synthetic rut checks alone
  # would miss an airborne or overturned review vehicle.
  tail=parked[-4:]
  assert all(sum(p['wheel_contacts'])>=3 and abs(p['roll'])<15 and abs(p['pitch'])<15 and p['speed_cm_s']<30 for p in tail),(name,tail)
  assert max(p['z'] for p in tail)-min(p['z'] for p in tail)<3,(name,tail)
  s=next(s for s in surfaces if name+'_Surface' in s.get_actor_label());v=next(v for v in visuals if v.surface==s)
  # Off-car synthetic stroke verifies finite layers, permanent deformation and tread rendering.
  tx,ty=(x+180,y-270) if name=='Road' else (x+650,y) if name=='Bog' else (x-650,y+200)
  before=s.sample_surface(u.Vector2D(tx,ty));depth=7 if name!='Bog' else 65
  for _ in range(12):s.apply_review_soil_stroke(u.Vector2D(tx-200,ty),u.Vector2D(tx+200,ty),30,depth,.35);yield from settle(.04)
  after=s.sample_surface(u.Vector2D(tx,ty));assert after.authored and after.sinkage_cap_cm>0
  if name=='Ford':assert after.granular_response and after.grass_cover==0
  assert after.surface_delta_cm<before.surface_delta_cm-.3,(name,before.surface_delta_cm,after.surface_delta_cm)
  report['deformation'][name]=dict(layer_cm=after.sinkage_cap_cm,before_cm=before.surface_delta_cm,after_cm=after.surface_delta_cm,granular=after.granular_response,grass=after.grass_cover)
  v.add_review_tread(u.Vector(tx-200,ty,0),u.Vector(tx+200,ty,0),30,.35,0)
  if name=='Ford':
   grass=u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails)[0]
   grass.apply_review_grass_contact(u.Vector2D(x-1100,y+1400),True);report['grass']=grass.grass_report();assert re.search(r'bent=[1-9]',report['grass'])
   gx,gy=x-1100,y+1400;gb=s.sample_surface(u.Vector2D(gx,gy));assert gb.grass_cover>.9
   for _ in range(8):s.apply_review_soil_stroke(u.Vector2D(gx-100,gy),u.Vector2D(gx+100,gy),30,4,.35)
   ga=s.sample_surface(u.Vector2D(gx,gy));assert ga.surface_delta_cm<gb.surface_delta_cm-.3
   report['deformation']['Grass']=dict(before_cm=gb.surface_delta_cm,after_cm=ga.surface_delta_cm,grass=ga.grass_cover)
   sheet.review_water_contact(u.Vector2D(x,y),18)
  yield from settle(2)
  report.setdefault('surface_reports',{})[name]=s.get_surface_report()
  yield from capture(name+'_surface',(x+900,y-1300,z+850),(x,y,z))
  if name=='Bog':yield from capture('Bog_tread',(tx+300,ty-350,z+380),(tx,ty,z-25))
 # Domain and static meshes must all receive the same live wave texture/clock.
 mats=[sheet.get_component_by_class(u.ProceduralMeshComponent).get_material(0)]+[a.static_mesh_component.get_material(0) for a in sheet.get_editor_property('domain_surfaces')]
 assert all(isinstance(m,u.MaterialInstanceDynamic) for m in mats)
 assert all(m.get_scalar_parameter_value('AmbientReady')==1 for m in mats)
 tex=mats[0].get_texture_parameter_value('AmbientTex');assert all(m.get_texture_parameter_value('AmbientTex')==tex for m in mats)
 a=u.RenderingLibrary.read_render_target_raw_pixel(world,tex,100,150,False);clock0=mats[0].get_scalar_parameter_value('AmbientClock');yield from settle(.7)
 b=u.RenderingLibrary.read_render_target_raw_pixel(world,tex,100,150,False);delta=max(abs(v-w) for v,w in zip([a.r,a.g,a.b],[b.r,b.g,b.b]))
 assert delta>1e-4 and mats[0].get_scalar_parameter_value('AmbientClock')>clock0;report['wave_animation_delta']=delta
 for name,pos,target in [('River',(-67100,20800,2200),(-68000,22000,1600)),('Lake',(-166100,-3500,550),(-166800,-2700,48))]:
  yield from capture(name+'_waves',pos,target)
  if name=='Lake':
   comp=next(a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces') if 'Lake' in a.get_actor_label());native=comp.get_material(0)
   comp.set_material(0,u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterSurface/M_GC_DomainLake'))
   yield from capture('Lake_original_material_reference',pos,target);comp.set_material(0,native)
 fx=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerWheelEffects);assert len(fx)==1
 fx[0].review_wheel(u.Vector(-67900,21850,1640),3,12,.12,.22,.4);yield from settle(.2);report['effects']=fx[0].effect_report();fx[0].clear_review()
 fx[0].review_wheel(u.Vector(-59550,-59475,2150),3,20,.3,0,.4);yield from settle(.2);report['mud_effects']=fx[0].effect_report();fx[0].clear_review();assert re.search(r'mud_small=[1-9]',report['mud_effects'])
 report['native_response']=move.native_substance_report()
 report['ok']=True;save();yield from finish()
def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=camera=None;u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 3
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_set_viewport_realtime(True)
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global steps,deadline,busy,failed
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<540,'Deadline'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;import gc;gc.collect();u.SystemLibrary.collect_garbage();u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
