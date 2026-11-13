"""Tree colour response trials in PIE; source masks, normals, scene and lighting unchanged."""
import unreal as u,json,sys,time,traceback,math,shutil,gc
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/TreeColour';O.mkdir(parents=True,exist_ok=True);D='/Game/GrandTour/ArtTests/FloraTrail'
sys.path.insert(0,str(R/'Art/Unreal'))
from flora_trail_asset_audit import verify
from flora_trail_evidence import audited_fingerprint
report={'ok':False,'images':[],'timings':[],'package_fingerprint':audited_fingerprint()};world=pc=car=camera=None
state={'busy':False,'due':0,'frame':0}
def save():(O/'verify_colour-report.json').write_text(json.dumps(report,indent=2))
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
 u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
 car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
 for c in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.ScreenPercentage 100','t.MaxFPS 0','r.VSync 0','r.DynamicRes.OperationMode 0']:cmd(c)
 while u.GameplayStatics.get_time_seconds(world)<8:yield .1
 actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor);slots=[]
 for a in actors:
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.get_instance_count() and c.static_mesh and c.static_mesh.get_path_name().startswith(D+'/Meshes/') and c.static_mesh.get_name() in ['SM_Exact_tree','SM_Exact_pine']:
    for i,m in enumerate(c.get_materials()):
     if m.blend_mode==u.BlendMode.BLEND_MASKED:slots.append((c,i,m))
 assert len(slots)==4
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector()),'FloraTrail_CanopyReview')
 camera.camera_component.set_field_of_view(65.);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
 pc.set_view_target_with_blend(camera,0);cmd('ShowHUD')
 cfg=json.loads((R/'Art/flora_trail_canopy_settings.json').read_text())
 for c,i,m in slots:
  scalars={str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value') for n in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,u.MaterialExpressionScalarParameter)}
  assert abs(scalars['CanopyReflectance']-cfg['reflectance'])<1e-5
  assert abs(scalars['CanopyTransmission']-cfg['transmission'])<1e-5
 report['saved_settings_match']=True;report['settings']=cfg
 for mode in ['saved']:
  for label,pos,target in [('canopy',(-1200,-900,130),(500,1300,1550)),('road',(-2350,-470,210),(900,150,640)),('sunlit',(1600,2600,240),(-900,400,1300))]:
   camera.set_actor_location(u.Vector(*pos),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
   yield from shot('game_'+mode+'_'+label)
 pc.set_view_target_with_blend(car,0);cmd('ShowHUD');yield 2;yield from shot('game_saved_driving')
 assert audited_fingerprint()==report['package_fingerprint']
 report.update(ok=True,performance_verified=False,performance_scope='Not benchmarked; existing shared-GPU limitation. Volumetric grid dimensions and geometry unchanged.',saved_map_unchanged=True,scene_lighting_exposure_unchanged=True);save()
 yield 2;u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=camera=None;L.load_level('/Engine/Maps/Entry');yield 3
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
