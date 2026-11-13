"""FoliageStat (LP3a): PIE frame-time and CSV-profiler samples at the four review sites. Read-only.
Loads L_LidarStudy, starts PIE like check_lidar_place.py, teleports the car to each installed site,
settles 8 s, then records 120 slate-tick frame deltas (t.MaxFPS 0) and a CSV-profiler capture over
the same frames (FrameTime, GameThreadTime, RenderThreadTime, RHIThreadTime, GPUTime, GPUMem/*,
MemoryFreeMB). Stats-system counters (stat unit, stat RHI) cannot be read from python; the CSV
profiler columns are their equivalent. Writes Place/foliagestat.json and a labelled copy:
foliagestat-<GT_STAT_LABEL>.json (default giant while the forest is a handful of components, cells once it is split)
so every variant keeps its own table."""
import unreal as u
from pathlib import Path
import json,time,traceback,gc,csv,gzip,statistics,os,re
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/Place';BASE='/Game/GrandTour/ArtTests/LidarStudy';CSV_DIR=ROOT/'Saved/Profiling/CSV'
sites=json.loads((OUT/'installed-sites.json').read_text())
FRAMES=120;SETTLE=8
COLUMNS=['FrameTime','GameThreadTime','RenderThreadTime','RHIThreadTime','GPUTime','GPUMem/LocalUsedMB','GPUMem/LocalBudgetMB','GPUMem/SystemUsedMB','MemoryFreeMB']
report=dict(ok=False,driving_tested=False,frames_per_site=FRAMES,settle_s=SETTLE,sites=[],caveat='Hidden editor PIE (-RenderOffScreen, 1440x900, t.MaxFPS 0) renders at a fraction of play speed; compare runs against each other, not against play.')
world=pc=car=None;busy=False;frame_samples=[];measure_frames=False

def save():
 (OUT/'foliagestat.json').write_text(json.dumps(report,indent=2,default=str))
 if report.get('label'):(OUT/('foliagestat-'+report['label']+'.json')).write_text(json.dumps(report,indent=2,default=str))
def inventory(refs):
 out={}
 for a in refs:
  if a.get_actor_label() in ['LidarStudy_Forest','LidarStudy_Understory']:
   meshes={};classes={};mobility={}
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if not c.static_mesh:continue
    n=c.static_mesh.get_name();meshes[n]=meshes.get(n,0)+c.get_instance_count();k=c.get_class().get_name();classes[k]=classes.get(k,0)+1;m=str(c.get_editor_property('mobility')).split('.')[-1].split(':')[0];mobility[m]=mobility.get(m,0)+1
   out[a.get_actor_label()]=dict(instances=meshes,components=classes,mobility=mobility)
 return out
def pct(v,q):
 v=sorted(v);f=(len(v)-1)*q/100;i=int(f);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(f-i)
def stats_ms(v):return dict(mean=round(1000*statistics.fmean(v),2),p95=round(1000*pct(v,95),2),max=round(1000*max(v),2),n=len(v))
def csv_files():return set(p.name for p in CSV_DIR.glob('Profile*.csv*')) if CSV_DIR.exists() else set()
def read_csv(path):
 opener=gzip.open if path.suffix=='.gz' else open
 with opener(path,'rt',newline='') as f:rows=list(csv.reader(f))
 header=rows[0];body=[]
 for r in rows[1:]:
  if not r or r[0].startswith('[') or r[0]=='EVENTS':break
  body.append(r)
 return header,body
def column(header,body,name):
 if name not in header:return None
 i=header.index(name);vals=[]
 for r in body:
  try:vals.append(float(r[i]))
  except (ValueError,IndexError):pass
 return dict(mean=round(statistics.fmean(vals),3),p95=round(pct(vals,95),3),max=round(max(vals),3),n=len(vals)) if vals else None
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world);deadline=time.monotonic()+180
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:
  assert time.monotonic()<deadline;yield .1
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)

def run():
 global world,pc,car,measure_frames
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 report['inventory']=inventory(refs);forest=report['inventory']['LidarStudy_Forest']['components']
 report['label']=os.environ.get('GT_STAT_LABEL') or ('cells' if sum(forest.values())>10 else 'giant');refs=None;save()
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 deadline=time.monotonic()+180
 while not world:
  world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<deadline;yield .5
 pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert isinstance(car,u.GTCarPawn);pc.possess(car)
 car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement();move.set_brake_input(0);move.set_throttle_input(0);move.set_handbrake_input(True)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:console(cmd)
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
 report['pie_started_s']=round(time.monotonic()-began,1)
 for site in sites:
  x,y=site['center'];z=site['center_height_cm'];car.set_actor_location_and_rotation(u.Vector(x,y,z+100),u.Rotator(yaw=site['yaw']),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(SETTLE)
  before=csv_files();console('csvprofile start');frame_samples.clear();measure_frames=True;until=time.monotonic()+300
  while len(frame_samples)<FRAMES:
   assert time.monotonic()<until,'frame capture timeout';yield .1
  measure_frames=False;console('csvprofile stop');samples=list(frame_samples)
  rep=grass.grass_report();cnt={k:int(v) for k,v in re.findall(r'(near|rank|distant)=(\d+)',rep)}   # GP4b: near is the sum over the pasture components (one per patch mesh), rank the rank band, distant the card layer
  row=dict(name=site['name'],slate_frame_ms=stats_ms(samples),grass=cnt.get('near',grass.grass.get_instance_count()),rank_grass=cnt.get('rank'),distant_grass=cnt.get('distant',grass.distant_grass.get_instance_count()),grass_report=rep,csv=None)
  # The profiler writes the file from its own thread after stop; wait for a new file that has gone quiet.
  until=time.monotonic()+60;path=None
  while time.monotonic()<until:
   new=sorted(csv_files()-before)
   if new:
    p=CSV_DIR/new[-1];size=p.stat().st_size;yield 2
    if size>0 and p.stat().st_size==size:path=p;break
   else:yield 1
  if path:
   header,body=read_csv(path);row['csv']=dict(file=str(path),frames=len(body),columns={n:column(header,body,n) for n in COLUMNS if n in header},missing=[n for n in COLUMNS if n not in header],header_hits=sorted(h for h in header if any(k in h for k in ['Thread','GPUTime','GPUMem','Mem','FrameTime']))[:200])
  else:row['csv_error']='no CSV profiler file appeared within 60 s'
  report['sites'].append(row);save()
 report['elapsed_s']=round(time.monotonic()-began,1);report['ok']=True;save()
 grass=mesh=move=None;gc.collect();yield from finish()

def finish():
 global world,pc,car
 if world:u.GameplayStatics.set_game_paused(world,False)
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=None;gc.collect()
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');world=None;yield 2
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if measure_frames and 0<dt<1:frame_samples.append(dt)
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1500,'FoliageStat timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
