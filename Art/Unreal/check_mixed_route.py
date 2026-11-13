"""Stationary drops, synthetic terrain/grass contacts and fixed cameras. No driving."""
import unreal as u
from pathlib import Path
import json,time,math,traceback,sys,re
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudRoad/MixedSurfaces'
VISUAL_ONLY='-GTMixedVisualOnly' in u.SystemLibrary.get_command_line()
sys.path.insert(0,str(ROOT/'Art/tools'));from make_mixed_route import ground,route_y
from make_mud_road import centre,heading
report=dict(ok=False,images=[],cases=[]);world=pc=car=surface=details=camera=None
def save():(OUT/('visual-check-report.json' if VISUAL_ONLY else 'playtest-report.json')).write_text(json.dumps(report,indent=2))
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:yield 0
def bind():
 global world,pc,car,surface,details
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
 surface=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface) if a.get_actor_label()=='MixedRoute_Surface')
 details=u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails)[0]
 car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'MixedReviewCamera')
 camera.get_component_by_class(u.CameraComponent).set_field_of_view(65)
 camera.get_component_by_class(u.CameraComponent).set_editor_property('constrain_aspect_ratio',False)
 pc.set_view_target_with_blend(camera,0);yield 3
 u.GameplayStatics.set_game_paused(world,True);yield .5
 f=OUT/(name+'.png');stamp=time.time();u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+f.as_posix()+'"',pc)
 deadline=time.monotonic()+30
 while not f.exists() or f.stat().st_mtime<stamp:
  assert time.monotonic()<deadline;yield .2
 report['images'].append(str(f));u.GameplayStatics.set_game_paused(world,False);save()
def run():
 global world,pc,car,surface,details,camera
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/MudRoad/L_MudRoad')
 if not VISUAL_ONLY:
  ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  u.SystemLibrary.execute_console_command(ew,'Automation RunTests GrandTour.MudRunner+GrandTour.LandscapeMud.GranularSand+GrandTour.DustLab.Emission');ew=None;yield 14
  while u.AutomationLibrary.are_automated_tests_running():yield .25
 u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 12;bind()
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 yield from capture('00_initial_overview',(3800,-4100,3500),(6300,100,0))
 pc.set_view_target_with_blend(car,0)
 original=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface) if a!=surface)
 assert original.use_native_substance_response and original.use_native_mud_shader_updates
 report['original_surface']=original.get_surface_report();original=None
 report['grass_initial']=details.grass_report();assert 'bent=0 removed=0' in report['grass_initial']
 data=json.loads((OUT/'authoring.json').read_text())
 dust=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTDustLab) if a.get_actor_label()=='MixedRoute_SandDust')
 assert dust.granular_only and dust.dust_system;report['sand_dust_bound']=True;dust=None
 for name,lane in ([] if VISUAL_ONLY else [('sand',4),('grass',5),('river',6),('old_dip',3)]):
  pc.select_lane(lane)
  if name=='old_dip':car.set_actor_location_and_rotation(u.Vector(650,centre(650),100),u.Rotator(yaw=heading(650)),False,True)
  car.get_chaos_movement().set_handbrake_input(True);yield from settle(10)
  case=dict(name=name,position=car.get_actor_location().to_tuple(),speed_cm_s=car.get_velocity().length(),frames=[]);report['cases'].append(case)
  start=u.GameplayStatics.get_time_seconds(world)
  while u.GameplayStatics.get_time_seconds(world)-start<4:
   case['frames'].append([dict(contact=not w.is_in_air(),offset=w.get_suspension_offset()) for w in car.get_chaos_movement().wheels]);yield 0
  frames=case.pop('frames')
  case['contact_changes']=[sum(a[i]['contact']!=b[i]['contact'] for a,b in zip(frames,frames[1:])) for i in range(4)]
  case['offset_range_cm']=[max(f[i]['offset'] for f in frames)-min(f[i]['offset'] for f in frames) for i in range(4)]
  case['contacts']=[frames[-1][i]['contact'] for i in range(4)]
  case['water_cm']=[w.water_depth_m*100 for w in car.get_traction().wheels]
  assert all(math.isfinite(v) for v in case['position']) and case['speed_cm_s']<200,case
  assert max(case['contact_changes'])<5,case
  assert all(case['contacts']),case
  if name in ['river','old_dip']:assert max(case['water_cm'])>5,case
  save()
 # Keep the player close so the active soil window and pond budget cover the fixtures.
 pc.select_lane(5);car.get_chaos_movement().set_handbrake_input(True);yield 2
 report['strokes']={}
 for name in ['sand','grass']:
  x,y=data['probes'][name];y-=350
  a=u.Vector2D(x-130,y);b=u.Vector2D(x+130,y);probe=u.Vector2D(x,y)
  before=surface.sample_surface(probe)
  for _ in range(8):surface.apply_review_soil_stroke(a,b,30.,5.,.4)
  after=surface.sample_surface(probe)
  report['strokes'][name]=dict(before=before.surface_delta_cm,after=after.surface_delta_cm,compression=after.compression_cm,tag=str(after.surface_tag),granular=after.granular_response,grass=after.grass_cover)
  assert after.surface_delta_cm<before.surface_delta_cm-.5,report['strokes'][name]
  assert after.granular_response==(name=='sand')
  if name=='grass':
   for dx in range(-130,131,30):details.apply_review_grass_contact(u.Vector2D(x+dx,y),False)
   details.apply_review_grass_contact(u.Vector2D(x,y),True)
  visual=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual) if a.surface==surface)
  visual.add_review_tread(u.Vector(x-130,y,ground(x-130,y)),u.Vector(x+130,y,ground(x+130,y)),30,.4);visual=None
 before=after=None;yield 2
 report['grass_after']=details.grass_report();assert re.search(r'bent=[1-9]',report['grass_after']) and re.search(r'removed=[1-9]',report['grass_after'])
 report['pond']=surface.simulated_water.mud_water_diagnostics()
 pondprobe=surface.sample_surface(u.Vector2D(5550,1550));report['pond_depth_cm']=pondprobe.water_depth_cm;assert pondprobe.water_depth_cm>50;pondprobe=None
 river=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if a.get_actor_label()=='MixedRoute_River');report['river']=river.water_diagnostics();river=None
 yield from capture('01_mixed_overview',(3800,-4100,3500),(6300,100,0))
 pc.select_lane(4);car.get_chaos_movement().set_handbrake_input(True);yield from settle(3)
 x,y=data['probes']['sand'];yield from capture('02_sand',(x-600,y-700,ground(x,y)+520),(x,y-250,ground(x,y)))
 pc.select_lane(5);car.get_chaos_movement().set_handbrake_input(True);yield from settle(3)
 x,y=data['probes']['grass'];yield from capture('03_grass_deformation',(x-100,y-750,ground(x,y)+270),(x,y-350,ground(x,y)))
 yield from capture('04_river_crossing',(6900,-900,480),(7450,-400,0))
 yield from capture('05_pond',(5550,450,750),(5550,1550,-5))
 camera.destroy_actor();camera=None
 pc.reset_lab();world=pc=car=surface=details=None;yield 12;bind()
 report['grass_reset']=details.grass_report();assert 'bent=0 removed=0' in report['grass_reset']
 pc.select_lane(5);car.get_chaos_movement().set_handbrake_input(True);yield from settle(2)
 x,y=data['probes']['grass'];reset=surface.sample_surface(u.Vector2D(x,y-350));report['reset_compression_cm']=reset.compression_cm;report['reset_height_cm']=reset.surface_delta_cm
 assert abs(reset.surface_delta_cm-report['strokes']['grass']['before'])<.01;reset=None
 report['ok']=True;save();yield from finish()
def finish():
 global world,pc,car,surface,details,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=surface=details=camera=None
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 3
steps=run();deadline=0;busy=False;began=time.monotonic()
def tick(dt):
 global deadline,busy,steps
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<420,'Check deadline'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;import gc;gc.collect();u.SystemLibrary.collect_garbage();u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error']);steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
