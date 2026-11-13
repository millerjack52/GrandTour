"""Matched real-map runtime views; no saved camera, soil, light or road changes."""
import unreal as u,sys,os
from pathlib import Path
ROOT=Path('C:/GrandTour');sys.path.insert(0,str(ROOT/'Art/Unreal'))
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-runtime-helpers>','exec'))
import lidar_logging_trial as trial
from lidar_grounding import GroundSampler
OUT=ROOT/'Art/Export/LidarStudy/FloraIntegration'
PHASE=os.environ.get('GT_FLORA_LIDAR_PHASE','before')
RD1_THROTTLE=.8
report=dict(ok=False,phase=PHASE,images=[],timings={},views=[])
def save():(OUT/(PHASE+'-report.json')).write_text(json.dumps(report,indent=2))

def long_capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'LidarLongRangeReview')
 camera.camera_component.set_field_of_view(68);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
 pc.set_view_target_with_blend(camera,0);yield from settle(5)
 path=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1920x1080 filename="'+path.as_posix()+'"',pc)
 until=time.monotonic()+45
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
 u.GameplayStatics.set_game_paused(world,False);report['images'].append(str(path));save()

def coverage_state(rows):
 expected=json.loads((OUT/'coverage-report.json').read_text());assert expected['ok']
 path=ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
 assert hashlib.sha256(path.read_bytes()).hexdigest()==expected['map_sha256']
 owner=next(a for a in rows if a.get_actor_label()=='LidarStudy_Understory');counts={}
 for name,prior in expected['counts_before'].items():
  c=next(c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name()==name)
  assert c.get_instance_count()==prior+expected['restored_by_mesh'][c.static_mesh.get_name()]
  counts[name]=c.get_instance_count()
 return dict(saved_fern_counts_verified=True,counts=counts,restored_ferns=expected['restored_ferns'],map_sha256=expected['map_sha256'])

def rd1_project(pts,cum,x,y,lo=0.,hi=None):
 # Authoring stations use 3D segment length, including climbs. Projection is
 # in XY but must interpolate that same station interval for the steering target.
 hi=cum[-1] if hi is None else hi;best=(None,1e18)
 for k,(a,b) in enumerate(zip(pts,pts[1:]),1):
  if cum[k]<lo or cum[k-1]>hi:continue
  dx,dy=b[0]-a[0],b[1]-a[1];t=max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/max(1e-9,dx*dx+dy*dy)))
  d=math.hypot(x-a[0]-dx*t,y-a[1]-dy*t)
  if d<best[1]:best=(cum[k-1]+t*(cum[k]-cum[k-1]),d)
 return best

def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 rows=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 if PHASE in ['coverageview','longrange']:report['coverage_validation']=coverage_state(rows)
 author=next(a for a in rows if isinstance(a,u.GTProceduralGround));g=GroundSampler(author)
 route=trial.route(json.loads((ROOT/'Art/Export/LidarStudy/Place/roads.json').read_text()))
 views=[]
 for name,s,off,height,look in [('approach',185.,-.8,170.,200.),('mud',211.,-.7,125.,221.),('bank',229.,-2.,180.,239.)]:
  x,y,yaw=trial.at(route,s,off);tx,ty,_=trial.at(route,look,5. if name=='bank' else 0)
  views.append(dict(name=name,station=s,position=[x,y,g.height(x,y)+height],target=[tx,ty,g.height(tx,ty)+100]))
 x,y,_=trial.at(route,210,-65);tx,ty,_=trial.at(route,220)
 views.append(dict(name='context',station=210.,position=[x,y,g.height(x,y)+5500],target=[tx,ty,g.height(tx,ty)+600]))
 if PHASE=='longrange':
  x,y,_=trial.at(route,215);views=[dict(name='integrated_hillside',station=210.,position=[-64000,-32500,g.height(-64000,-32500)+14000],target=[x,y,g.height(x,y)+1200],description='New logging-road canopy and its transition into the existing forest, about 250m away')]
  known=json.loads((ROOT/'Saved/LidarAuthoringQA/ValleyGround/cameras.json').read_text())
  for key,name in [('V02','river_valley'),('V03','long_valley')]:
   v=next(v for v in known if v['view']==key);views.append(dict(name=name,station=210.,position=v['position'],target=v['target'],description=v['description']))
  report['scope']='Actual current saved map; new assets remain in the bounded logging-road section. No art, lighting or fog changes.'
 report['views']=views;report['ground_digest']=str(author.output_digest);save()
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1920 if PHASE=='longrange' else 1440,1080 if PHASE=='longrange' else 900)
 until=time.monotonic()+180
 while not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:
   pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();mv=car.get_chaos_movement();mv.set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','gt.Perf.LogSpikes 1','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 for v in views:
  x,y,yaw=trial.at(route,v['station']-7);car.set_actor_location_and_rotation(u.Vector(x,y,g.height(x,y)+80),u.Rotator(yaw=yaw),False,True)
  mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(7)
  yield from (long_capture if PHASE=='longrange' else capture)(PHASE+'_'+v['name'],v['position'],v['target'])
  u.SystemLibrary.execute_console_command(world,'gt.Perf.Reset',pc);report['timings'][v['name']]=yield from frame_window(4)
  u.SystemLibrary.execute_console_command(world,'gt.Perf.Dump FLORA_LIDAR_'+PHASE+'_'+v['name'],pc);save()
 if PHASE=='check':
  import lidar_flora_drivecheck
  yield from lidar_flora_drivecheck.run(globals(),route,g)
 rows=author=g=mesh=mv=None;gc.collect()
 report['ok']=True;report['timing_scope']='Hidden editor tick intervals; not standalone GPU benchmark';save()
 yield from finish()

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if measure_frames and dt>0:frame_samples.append(dt)
 if drive_on and car:drive_ctrl()
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1200,'LiDAR visual check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
