"""Saved-map audit and before/after tree GPU comparisons in actual PIE views."""
import unreal as u,json,sys,time,traceback,math,shutil,gc
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Canopy';D='/Game/GrandTour/ArtTests/FloraTrail'
sys.path.insert(0,str(R/'Art/Unreal'))
from flora_trail_asset_audit import verify
from flora_trail_evidence import audited_fingerprint
from benmore_profile_metrics import analyse
report={'ok':False,'images':[],'timings':[],'package_fingerprint':audited_fingerprint()};world=pc=car=camera=None
state={'busy':False,'due':0,'frame':0}
def save():(O/'verify-report.json').write_text(json.dumps(report,indent=2))
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def frames(n):
 target=state['frame']+n
 while state['frame']<target:yield 0

def shot(name):
 yield from frames(80)
 stamp=time.time();p=O/(name+'.png');cmd('Shot filename="'+p.as_posix()+'" -nosuffix')
 end=time.monotonic()+40
 while not p.exists() or p.stat().st_mtime<stamp:
  assert time.monotonic()<end;yield .2
 report['images'].append(name);save()

def run():
 global world,pc,car,camera
 L=u.get_editor_subsystem(u.LevelEditorSubsystem);assert L.load_level(D+'/L_FloraTrail')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for c in json.loads((R/'Art/flora_trail_settings.json').read_text())['console']:cmd(c)
 yield 10;report['assets']=verify(world)
 # Both alternatives are compiled before the play world starts.
 original={k:u.load_asset(D+'/Materials/M_Exact_'+k+'_Leaf_0_26834fc') for k in ['tree','pine']};assert all(original.values())
 u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
 car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
 for c in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.ScreenPercentage 100','t.MaxFPS 0','r.VSync 0','r.DynamicRes.OperationMode 0']:cmd(c)
 while u.GameplayStatics.get_time_seconds(world)<8:yield .1
 slots=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.get_instance_count() and c.static_mesh and c.static_mesh.get_path_name().startswith(D+'/Meshes/') and c.static_mesh.get_name() in ['SM_Exact_tree','SM_Exact_pine']:
    key='pine' if c.static_mesh.get_name()=='SM_Exact_pine' else 'tree'
    for i,m in enumerate(c.get_materials()):
     if m.blend_mode==u.BlendMode.BLEND_MASKED:slots.append((c,i,m,original[key]))
 assert len(slots)==4
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector()),'FloraTrail_CanopyReview')
 camera.camera_component.set_field_of_view(65.);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
 pc.set_view_target_with_blend(camera,0);cmd('ShowHUD')
 csv_dir=R/'Saved/Profiling/CSV'
 for mode in ['before','after']:
  for c,i,new,old in slots:c.set_material(i,new if mode=='after' else old)
  for label,pos,target in [('canopy',(-1200,-900,130),(500,1300,1550)),('road',(-2350,-470,210),(900,150,640))]:
   camera.set_actor_location(u.Vector(*pos),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
   yield from shot('game_'+mode+'_'+label)
   if not json.loads((R/'Art/flora_trail_canopy_settings.json').read_text()).get('measure_gpu',False):continue
   yield from frames(90);existing=set(csv_dir.glob('*.csv'));cmd('CsvProfile START');yield from frames(300);cmd('CsvProfile STOP')
   end=time.monotonic()+30;files=[]
   while not files:
    yield 1;files=[p for p in csv_dir.glob('*.csv') if p not in existing];assert time.monotonic()<end
   yield 2;p=O/(mode+'_'+label+'.csv');shutil.copy2(max(files,key=lambda x:x.stat().st_mtime),p)
   metrics=analyse(p)['metrics'];report['timings'].append({'mode':mode,'view':label,'resolution':list(pc.get_viewport_size()),'metrics':{k:metrics[k] for k in ['FrameTime','GPUTime','GameThreadTime'] if k in metrics}});save()
 pc.set_view_target_with_blend(car,0);cmd('ShowHUD');yield 2;yield from shot('game_after_driving')
 report.update(ok=True,performance_verified=False,performance_scope='Timings skipped by default; optional 300-frame PIE spot checks are not a sustained-driving or 1080p certification',geometry_lods_lights_exposure_unchanged=True);save()
 cmd('r.RHIThread.Enable 0');yield 2;u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=camera=None;slots.clear();original.clear();L.load_level('/Engine/Maps/Entry');yield 3
steps=run()
def tick(dt):
 global steps
 if state['busy']:return
 state['busy']=True;state['frame']+=1
 try:
  if time.monotonic()>=state['due']:state['due']=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;u.unregister_slate_post_tick_callback(handle)
  for key,value in list(globals().items()):
   if not key.startswith('__') and key not in ('u','time'):globals()[key]=None
  value=None
  import gc
  gc.collect();u.SystemLibrary.collect_garbage();globals()['quit_at']=time.monotonic()+3
  def close(dt):
   if time.monotonic()>quit_at:u.unregister_slate_post_tick_callback(quit_handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
  globals()['quit_handle']=u.register_slate_post_tick_callback(close)
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
