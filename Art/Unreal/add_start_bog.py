"""Maximum-softness bog behind the existing spawn; owned authoring assets only."""
import unreal as u
import json, math, time, traceback, hashlib, shutil, re, gc
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ProceduralGround'
LEVEL='/Game/GrandTour/ArtTests/ProceduralGround/L_BigMountain_Authoring'
headless='-GTDensityNoVisual' in u.SystemLibrary.get_command_line()
REPORT=OUT/('startbog-functional.json' if headless else 'startbog.json')
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
def setup():
 assert les.load_level(LEVEL)
 refs=list(actors.get_all_level_actors());author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
 start=next(a for a in refs if isinstance(a,u.PlayerStart));origin=start.get_actor_location();yaw=start.get_actor_rotation().yaw
 forward=u.Vector2D(math.cos(math.radians(yaw)),math.sin(math.radians(yaw)));side=u.Vector2D(-forward.y,forward.x)
 bog=next((a for a in refs if isinstance(a,u.GTProceduralRoad) and a.get_actor_label().startswith('Bog behind start')),None)
 # Back up the entire owned package set before any saved mutations.
 backup=OUT/'BeforeStartBog'/str(time.time_ns());shutil.copytree(ROOT/'Content/GrandTour/ArtTests/ProceduralGround',backup)
 report['backup']=str(backup);report['start']=[origin.x,origin.y,origin.z];report['start_yaw']=yaw;save()
 if not bog:bog=actors.spawn_actor_from_class(u.GTProceduralRoad,origin)
 bog.set_actor_label('Bog behind start - maximum soft soil');bog.author=author
 props(bog,width_cm=1300.,bed_depth_cm=24.,mud_depth_cm=50.,wetness=1.,centre_grass_cover=.08,verge_grass_cover=.55,maximum_cut_fill_cm=100.,detail_seed=1062,relief_strength=.75)
 existing=next(a for a in refs if isinstance(a,u.GTProceduralRoad) and a.get_actor_label().startswith('Road 01'))
 bog.relief_texture=existing.relief_texture
 bog.control_points.clear_spline_points(False);positions=[]
 for i,(back,lateral,width) in enumerate([(1000,0,.65),(2300,80,1.05),(3900,-130,1.35),(5600,180,1.2),(7200,260,.8)]):
  p=u.Vector2D(origin.x,origin.y)-forward*back+side*lateral;z=author.base_height_at(p)
  bog.control_points.add_spline_point(u.Vector(p.x,p.y,z),u.SplineCoordinateSpace.WORLD,False)
  bog.control_points.set_scale_at_spline_point(i,u.Vector(1,width,1),False);positions.append([p.x,p.y,z])
 bog.control_points.update_spline()
 length=sum(math.dist(a[:2],b[:2]) for a,b in zip(positions,positions[1:]))/100
 condition=props(u.GTRoadCondition(),name='Super bog - 100cm / zero firmness',start_metres=0.,end_metres=length,blend_metres=9.,mud_depth_cm=100.,rut_depth_cm=32.,firmness=0.,wetness=1.,grass_cover=.1,water_fill_cm=18.,track_spread_cm=230.,churn=1.,crossing_tracks=.8,breakup_cm=16.)
 bog.conditions=[condition]
 report.update(points=positions,length_m=length,entry_behind_start_m=10,soil_layer_limit_cm=100,firmness=0,water_fill_limit_cm=18)
 # Existing authoring bounds must encompass this addition; do not silently clip it.
 centre=author.generation_bounds.get_world_location();extent=author.generation_bounds.get_scaled_box_extent()
 assert all(abs(p[0]-centre.x)<extent.x-1500 and abs(p[1]-centre.y)<extent.y-1500 for p in positions)
 assert author.rebuild(),author.last_message
 report['digest']=author.output_digest;report['tiles']=len(author.relief_tiles);report['triangles']=author.relief_triangles
 assert author.surface.maximum_layer_depth_cm>=100,author.surface.maximum_layer_depth_cm
 yield 2
 verify(author,origin,forward)
 assert author.rebuild(),author.last_message
 assert author.output_digest==report['digest'] and author.changed_relief_tiles==0
 report['repeat_rebuild_verified']=True
 for tex in [author.paint_texture,author.style_texture,author.macro_texture]:assert u.EditorAssetLibrary.save_loaded_asset(tex)
 assert les.save_current_level();yield 2
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
 assert author.output_digest==report['digest'];verify(author,origin,forward)
 protected();report.update(ok=True,saved_and_reloaded=True);save();les.load_level('/Engine/Maps/Entry');yield 2
def verify(author,origin,forward):
 tiles=list(author.relief_tiles.values());samples=[]
 pairs={(round(t.get_actor_location().x,2),round(t.get_actor_location().y,2)):t for t in tiles};seam=0.;count=0
 for t in tiles:
  o=t.get_actor_location();span=t.span_cm
  for dx,dy in [(1,0),(0,1)]:
   neighbour=pairs.get((round(o.x+dx*span,2),round(o.y+dy*span,2)))
   if not neighbour:continue
   for j in range(9):
    p=u.Vector2D(o.x+span*(1 if dx else j/8),o.y+span*(1 if dy else j/8));seam=max(seam,abs(t.height_at(p)-neighbour.height_at(p)));count+=1
 assert count>100 and seam<.05;report.update(seam_samples=count,seam_error_cm=seam)
 for tile in tiles:
  o=tile.get_actor_location();n=round(math.sqrt(len(tile.soil)))-1
  for y in range(2,n-1,2):
   for x in range(2,n-1,2):
    p=u.Vector2D(o.x+x*tile.span_cm/n,o.y+y*tile.span_cm/n);d=p-u.Vector2D(origin.x,origin.y)
    behind=-(d.x*forward.x+d.y*forward.y);across=abs(d.x*(-forward.y)+d.y*forward.x)
    c=tile.soil[y*(n+1)+x]
    if 2300<behind<5900 and across<700 and c.r>0:samples.append(dict(x=p.x,y=p.y,z=tile.height_at(p),depth=c.r,firm=c.b,soft=c.a,behind_m=behind/100))
 assert samples and max(p['depth'] for p in samples)>80
 core=[p for p in samples if p['depth']>65 and p['soft']>.99 and p['firm']<.01]
 assert len(core)>100,len(core)
 report['core_samples']=len(core);report['depth_range_cm']=[min(p['depth'] for p in core),max(p['depth'] for p in core)]
 # Pick a soft, locally gentle spot for a stationary integration check.
 def bed(x,y):
  for t in tiles:
   o=t.get_actor_location()
   if o.x<=x<o.x+t.span_cm and o.y<=y<o.y+t.span_cm:return t.height_at(u.Vector2D(x,y))
  raise AssertionError('Missing bog collision tile')
 def score(p):return p['depth']-40*math.hypot((bed(p['x']+100,p['y'])-bed(p['x']-100,p['y']))/200,(bed(p['x'],p['y']+100)-bed(p['x'],p['y']-100))/200)
 report['probe']=max(core,key=score)
 edworld=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();ignored=[a for a in actors.get_all_level_actors() if a!=author.landscape and not isinstance(a,u.GTRoadReliefTile)]
 errors=[]
 for p in core[::max(1,len(core)//24)]:
  hit=u.SystemLibrary.line_trace_single(edworld,u.Vector(p['x'],p['y'],p['z']+1000),u.Vector(p['x'],p['y'],p['z']-1000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignored,u.DrawDebugTrace.NONE,True).to_tuple()
  assert hit[0] and any(isinstance(v,u.GTRoadReliefTile) for v in hit),(p,[str(v) for v in hit]);errors.append(abs(hit[4].z-p['z']))
 assert max(errors)<.1;report['collision_samples']=len(errors);report['collision_error_cm']=max(errors)
 wet=[]
 for patch in author.generated_water_domain.road_patches:
  o=patch.origin_cm;v=patch.samples
  for i in range(len(v)//4):
   if v[i*4+1]<=.005:continue
   x=o.x+(i%patch.size_x+.5)*patch.cell_cm;y=o.y+(i//patch.size_x+.5)*patch.cell_cm
   d=u.Vector2D(x-origin.x,y-origin.y);back=-(d.x*forward.x+d.y*forward.y)
   if 1000<back<7300 and abs(d.x*(-forward.y)+d.y*forward.x)<1300:wet.append(v[i*4+1]*100)
 report['bog_water_samples']=len(wet);report['bog_water_depth_cm']=[min(wet),max(wet)] if wet else []
 assert wet and max(wet)<=18.1,'No shallow bog pools generated'
def review():
 global world
 functional=json.loads((OUT/'startbog-functional.json').read_text());assert functional['ok'];p=functional['probe']
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
 report['native']=nums(move.native_substance_report());report['soil']=nums(surface.get_surface_report());report['probe']=p
 report['drive_input']=car.get_drivetrain().get_drive_input();assert abs(report['drive_input'])<.0001
 assert report['native']['soil_contacts']>=3 and report['native']['native_mud_contacts']>=3,report['native']
 assert report['soil']['push_cells']>0,report['soil']
 report['wheel_samples']=[]
 report['car_position']=list(car.get_actor_location().to_tuple());report['car_velocity']=list(car.get_velocity().to_tuple())
 for i,w in enumerate(car.get_traction().wheels):
  s=surface.sample_surface(u.Vector2D(w.contact_point.x,w.contact_point.y))
  ws=u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))
  report['wheel_samples'].append(dict(depth=s.sinkage_cap_cm,softness=s.softness,q=s.native_extrude_cm,delta=s.surface_delta_cm,tread_cm_s=w.tread_cm_per_s,contact=w.get_editor_property('bInContact'),spring_force=ws[4],drive_torque=ws[11],brake_torque=ws[12]))
 path=OUT/'StartBog_parked.png';stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 until=time.monotonic()+45
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
 report['image']=str(path);save()
 assert max(abs(w['tread_cm_s']) for w in report['wheel_samples'])<20,report['wheel_samples']
 report.update(ok=True,stationary_contact_verified=True);save()
 u.GameplayStatics.set_game_paused(world,False);camera.destroy_actor();u.EditorLevelLibrary.editor_end_play();yield 3
 world=pc=car=move=mesh=surface=camera=None
 until=time.monotonic()+60
 while u.EditorLevelLibrary.get_game_world():assert time.monotonic()<until;yield .5
 les.load_level('/Engine/Maps/Entry');yield 3
steps=setup() if headless else review()
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
