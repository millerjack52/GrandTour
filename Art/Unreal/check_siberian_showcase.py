"""Stationary contact checks, synthetic terrain stamps and fixed-camera captures. No driving."""
import unreal as u
from pathlib import Path
import json,time,math,traceback,sys,re
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/SiberianShowcase'
sys.path.insert(0,str(ROOT/'Art/tools'));from make_siberian_showcase import ground,river_y
report=dict(ok=False,images=[],cases=[]);world=pc=car=camera=None
REPORT_NAME='treads-report.json' if '-GTTreadReview' in u.SystemLibrary.get_command_line() else 'check-report.json'
if '-GTWaveReview' in u.SystemLibrary.get_command_line():REPORT_NAME='wavecheck-report.json'
data=json.loads((OUT/'authoring.json').read_text())
def save():(OUT/REPORT_NAME).write_text(json.dumps(report,indent=2))
def settle(t):
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<t:yield 0

def render_cost(label):
 start=time.monotonic();frames=0
 while time.monotonic()-start<4:frames+=1;yield 0
 # Slate callbacks are a smoke measurement, not a game-frame benchmark.
 report.setdefault('slate_callbacks_per_second',{})[label]=frames/(time.monotonic()-start);save()
def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target);camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'TaigaReview')
 c=camera.get_component_by_class(u.CameraComponent);c.set_field_of_view(65);c.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);yield from settle(2)
 u.GameplayStatics.set_game_paused(world,True);yield .3
 f=OUT/(name+'.png');stamp=time.time();u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+f.as_posix()+'"',pc);end=time.monotonic()+30
 while not f.exists() or f.stat().st_mtime<stamp:assert time.monotonic()<end;yield .2
 report['images'].append(str(f));u.GameplayStatics.set_game_paused(world,False);save()
def run():
 global world,pc,car,camera
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/SiberianShowcase/L_SiberianShowcase')
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_set_viewport_realtime(False)
 u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 14
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car;car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 surfaces=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface);assert len(surfaces)==4
 report['surfaces']=[s.get_surface_report() for s in surfaces];assert all(s.use_native_water_response for s in surfaces)
 assert sum(s.use_native_substance_response for s in surfaces)==2
 assert len(u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual))==4
 assert len(u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerWheelEffects))==1
 if '-GTWaveReview' in u.SystemLibrary.get_command_line():
  sys.path.insert(0,str(ROOT/'Art/Unreal'))
  from check_siberian_waves import review
  yield from review(world,pc,report,capture,settle)
  surfaces=[];report['ok']=True;save();yield from finish();return
 if '-GTTreadReview' in u.SystemLibrary.get_command_line():
  pc.select_lane(3);car.get_chaos_movement().set_handbrake_input(True);yield from settle(3)
  s=next(s for s in surfaces if s.sample_surface(u.Vector2D(2300,-2070)).authored)
  visual=next(v for v in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual) if v.surface==s)
  for k in range(40):
   a=k*math.pi/30;b=(k+1)*math.pi/30
   for radius in [230,380]:
    p=u.Vector2D(2600+radius*math.cos(a),-2400+radius*math.sin(a));q=u.Vector2D(2600+radius*math.cos(b),-2400+radius*math.sin(b))
    s.apply_review_soil_stroke(p,q,29,10,.15);visual.add_review_tread(u.Vector(p.x,p.y,0),u.Vector(q.x,q.y,0),29,.15,k*2*radius*math.sin(math.pi/60)/29)
   yield 0
  # Diagnostic only: reveal the submerged tread geometry; this never saves a map.
  for sheet in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet):sheet.set_actor_hidden_in_game(True)
  sheet=s=visual=None;surfaces=[]
  yield from capture('13_treads_without_water',(2600,-2400,1200),(2600,-2400,30))
  yield from capture('14_tread_detail',(2860,-2190,450),(2760,-2090,30))
  report['ok']=True;save();yield from finish();return
 clods=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerClod);assert len(clods)>25
 report['clods']=dict(count=len(clods),released=sum(int(a.released) for a in clods),masses=sorted(set(round(a.body.get_mass(),2) for a in clods)))
 assert report['clods']['released']==0 and report['clods']['masses']==[10.,20.],report['clods']
 assert car.get_chaos_movement().review_suspension_obstacle(clods[0]);clods=[]
 yield from capture('01_overview',(-9600,-11000,8500),(0,400,0))
 yield from render_cost('overview')
 # Isolate the shore material from the water sheet at the reported pale bank.
 yield from capture('11_upper_shore',(3200,3200,650),(3900,4400,150))
 upper=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if 'NE' in a.get_actor_label())
 upper.set_actor_hidden_in_game(True)
 yield from capture('12_upper_bed',(3200,3200,650),(3900,4400,150))
 upper.set_actor_hidden_in_game(False);upper=None
 for lane,p in enumerate(data['checkpoints'],1):
  pc.select_lane(lane);car.get_chaos_movement().set_handbrake_input(True);yield from settle(7)
  case=dict(name=p['name'],position=car.get_actor_location().to_tuple(),speed_cm_s=car.get_velocity().length());frames=[]
  start=u.GameplayStatics.get_time_seconds(world)
  while u.GameplayStatics.get_time_seconds(world)-start<2:
   frames.append([(not w.is_in_air(),w.get_suspension_offset()) for w in car.get_chaos_movement().wheels]);yield 0
  case['contact_changes']=[sum(a[i][0]!=b[i][0] for a,b in zip(frames,frames[1:])) for i in range(4)]
  case['offset_range_cm']=[max(f[i][1] for f in frames)-min(f[i][1] for f in frames) for i in range(4)]
  case['contacts']=[f[0] for f in frames[-1]];case['water_cm']=[w.water_depth_m*100 for w in car.get_traction().wheels]
  report['cases'].append(case);save()
  assert all(math.isfinite(v) for v in case['position']) and case['speed_cm_s']<200,case
  assert all(case['contacts']) and max(case['contact_changes'])<5,case
  if 'ford' in p['name']:assert max(case['water_cm'])>10,case
 report['native_response']=car.get_chaos_movement().native_substance_report();assert re.search(r'water_steps=[1-9]',report['native_response'])
 # Continuous collision at the four tile joins, including both river banks.
 report['seam_traces']=[]
 for x,y in [(0,-4000),(0,-2050),(0,4100),(-4400,0),(4400,0),(0,float(river_y(0)))]:
  hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,1500),u.Vector(x,y,-1500),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[car],u.DrawDebugTrace.NONE,False)
  assert hit,(x,y);report['seam_traces'].append([x,y,bool(hit.to_tuple()[0])]);assert hit.to_tuple()[0]
 hit=None
 report['surroundings_height_checks']=[]
 for x,y in [(-6600,-3000),(6600,4000),(3000,6600)]:
  hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,2000),u.Vector(x,y,-2000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[car],u.DrawDebugTrace.NONE,False)
  assert hit and hit.to_tuple()[0]
  actual=hit.to_tuple()[4].z;expected=float(ground(x,y));report['surroundings_height_checks'].append(dict(x=x,y=y,expected=expected,actual=actual,error_cm=abs(actual-expected)));assert abs(actual-expected)<2
 hit=None
 pc.select_lane(5);car.get_chaos_movement().set_handbrake_input(True);yield from settle(2)
 report['deformation']={}
 for name,x,y in [('grass',-900,3000),('sand',-3600,float(river_y(-3600))+650)]:
  s=next(s for s in surfaces if s.sample_surface(u.Vector2D(x,y)).authored);before=s.sample_surface(u.Vector2D(x,y)).surface_delta_cm
  for _ in range(8):s.apply_review_soil_stroke(u.Vector2D(x-130,y),u.Vector2D(x+130,y),30,5,.4)
  sample=s.sample_surface(u.Vector2D(x,y));report['deformation'][name]=dict(before=before,after=sample.surface_delta_cm,granular=sample.granular_response)
  assert sample.surface_delta_cm<before-.5
  if name=='grass':
   detail=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.surface==s)
   for xx in range(-130,131,30):detail.apply_review_grass_contact(u.Vector2D(x+xx,y),False)
   detail.apply_review_grass_contact(u.Vector2D(x,y),True);report['grass']=detail.grass_report();assert re.search(r'bent=[1-9]',report['grass'])
 # Controlled curved impressions, not a driven vehicle path.
 s=next(s for s in surfaces if s.sample_surface(u.Vector2D(2300,-2070)).authored)
 report['deep_layer_cm']=s.sample_surface(u.Vector2D(2300,-2070)).sinkage_cap_cm
 assert report['deep_layer_cm']>80
 pc.select_lane(3);car.get_chaos_movement().set_handbrake_input(True);yield from settle(2)
 visual=next(v for v in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual) if v.surface==s)
 for k in range(40):
  a=k*math.pi/30;b=(k+1)*math.pi/30
  for radius in [230,380]:
   p=u.Vector2D(2600+radius*math.cos(a),-2400+radius*math.sin(a));q=u.Vector2D(2600+radius*math.cos(b),-2400+radius*math.sin(b))
   s.apply_review_soil_stroke(p,q,29,10,.15);visual.add_review_tread(u.Vector(p.x,p.y,0),u.Vector(q.x,q.y,0),29,.15,k*2*radius*math.sin(math.pi/60)/29)
  yield 0
 yield from settle(2)
 yield from capture('07_curved_treads',(2600,-2400,1200),(2600,-2400,30))
 # A repeated pressure fixture proves the native geometry can pass the former cap.
 for k in range(110):
  s.apply_review_soil_stroke(u.Vector2D(2450,-2070),u.Vector2D(2650,-2070),32,85,.8)
  yield 0
 report['deep_stroke_cm']=-s.sample_surface(u.Vector2D(2550,-2070)).surface_delta_cm
 assert report['deep_stroke_cm']>50,report['deep_stroke_cm']
 s=sample=detail=visual=None;surfaces=[]
 water=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet);report['water']={a.get_actor_label():a.mud_water_diagnostics() if a.mud_surface else a.water_diagnostics() for a in water};assert len(water)==4
 for p in data['ponds']:
  sheet=next(a for a in water if ('SW' if p['name']=='Forest pond' else 'NE') in a.get_actor_label());depth=sheet.mud_surface.sample_surface(u.Vector2D(p['x'],p['y'])).water_depth_cm;report[p['name']+'_depth_cm']=depth;assert 10<depth<50
  depths=[sheet.review_water_column(u.Vector2D(p['x']+dx,p['y']+dy)).g for dx in range(-1200,1201,100) for dy in range(-900,901,100)]
  depths=sorted(d for d in depths if d>1)
  report.setdefault('pond_depth_profiles',{})[p['name']]=dict(wet_probes=len(depths),median_cm=depths[len(depths)//2],maximum_cm=max(depths),shallow_fraction=sum(d<25 for d in depths)/len(depths))
  assert max(depths)<55 and sum(d<25 for d in depths)/len(depths)>.35,(p['name'],report['pond_depth_profiles'][p['name']])
 river=next(a for a in water if not a.mud_surface)
 report['river_coverage']=[]
 for x in range(-6000,6001,300):
  # Avoid the authored gravel bar with a second channel probe.
  cols=[river.review_water_column(u.Vector2D(x,float(river_y(x))+dy)) for dy in [-220,0,220]]
  best=max(c.g for c in cols);report['river_coverage'].append([x,best]);assert 5<best<60,(x,best)
 # Stationary body occupancy followed by decay, at the forest pond.
 pc.select_lane(2);car.get_chaos_movement().set_handbrake_input(True);yield from settle(2)
 sheet=next(a for a in water if 'SW' in a.get_actor_label());centre=u.Vector2D(-2500,-900)
 report['water_contact_samples']=[]
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<3:
  sheet.review_water_contact(centre,30)
  c=sheet.review_water_column(centre);report['water_contact_samples'].append([c.r,c.g,c.b,c.a]);yield 0
 assert all(all(math.isfinite(v) for v in c) and abs(c[0]-c[2])<.01 and c[1]>0 for c in report['water_contact_samples'])
 yield from capture('08_water_contact',(-3200,-1700,650),(-2500,-900,30))
 yield from settle(8)
 yield from capture('09_water_recovery',(-3200,-1700,650),(-2500,-900,30))
 report['water_after_contact']=sheet.mud_water_diagnostics()
 for v in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual):
  rt=v.get_research_water_state()
  if rt:
   colours=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for x,y in [(10,10),(30,30),(50,50)]]
   assert all(math.isfinite(k) and -.001<=k<=1.001 for c in colours for k in [c.r,c.g,c.b])
 v=rt=colours=cols=river=None;water=[];sheet=None
 yield from capture('02_river',(-5500,-500,1900),(-1000,1500,-20))
 yield from capture('03_forest_pond',(-3400,-1300,950),(-2500,-900,30))
 pc.select_lane(3);car.get_chaos_movement().set_handbrake_input(True);yield from settle(2)
 yield from capture('04_bog',(1700,-2800,650),(2300,-2070,30))
 yield from capture('05_upper_pond',(2300,2800,1800),(3900,4500,160))
 pc.select_lane(4);car.get_chaos_movement().set_handbrake_input(True);yield from settle(2)
 p=data['checkpoints'][3];yield from capture('06_ford',(p['x']-950,p['y']-1200,600),(p['x'],p['y'],0))
 yield from capture('10_grass',(-1200,3000,190),(-500,3400,80))
 sys.path.insert(0,str(ROOT/'Art/Unreal'))
 from check_siberian_waves import review
 yield from review(world,pc,report,capture,settle)
 report['ok']=True;save();yield from finish()
def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=camera=None;u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 3
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_set_viewport_realtime(True)
steps=run();deadline=0;busy=False;began=time.monotonic()
def tick(dt):
 global steps,deadline,busy
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<540,'Deadline'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;import gc;gc.collect();u.SystemLibrary.collect_garbage();u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error']);steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
