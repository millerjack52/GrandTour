"""Saved-map reference tree validation including reversible style and directional-light probes."""
import unreal as u,json,sys,time,traceback,math,shutil,gc
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Source34';O.mkdir(parents=True,exist_ok=True);D='/Game/GrandTour/ArtTests/FloraTrail'
sys.path.insert(0,str(R/'Art/Unreal'))
from flora_trail_asset_audit import verify
from flora_trail_evidence import audited_fingerprint
from flora_trail_source34 import candidate,configure,settings
from benmore_river_life_materials import Graph,props
SAVED='-GTSource34Saved=1' in u.SystemLibrary.get_command_line()
STAGE='verify' if SAVED else 'preview'
report={'ok':False,'images':[],'timings':[],'package_fingerprint':audited_fingerprint()};world=pc=car=camera=None
state={'busy':False,'due':0,'frame':0}
def save():(O/(STAGE+'-report.json')).write_text(json.dumps(report,indent=2))
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
 mats={k:(u.load_asset(D+'/Materials/Source34/M_Source34_'+k) if SAVED else candidate(k)) for k in ['tree','pine']}
 yield 8
 report['assets_before']=verify(world)
 grey=u.load_asset('/Game/GrandTour/ArtTests/FloraTrailReview/M_DisplayCheck')
 if not grey:
  grey=u.AssetToolsHelpers.get_asset_tools().create_asset('M_DisplayCheck','/Game/GrandTour/ArtTests/FloraTrailReview',u.Material,u.MaterialFactoryNew());props(grey,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=Graph(grey);g.output(g.scalar(.18),u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not u.MaterialEditingLibrary.recompile_material(grey);u.EditorAssetLibrary.save_loaded_asset(grey,False)
 u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
 car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
 for c in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.ScreenPercentage 100','t.MaxFPS 0','r.VSync 0','r.DynamicRes.OperationMode 0']:cmd(c)
 while u.GameplayStatics.get_time_seconds(world)<8:yield .1
 slots=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.get_instance_count() and c.static_mesh and c.static_mesh.get_path_name().startswith(D+'/Meshes/') and c.static_mesh.get_name() in ['SM_Exact_tree','SM_Exact_pine']:
    key=c.static_mesh.get_name().removeprefix('SM_Exact_')
    for i,m in enumerate(c.get_materials()):
     if m.blend_mode==u.BlendMode.BLEND_MASKED:slots.append((c,i,m,key))
 assert len(slots)==4
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector()),'FloraTrail_Source34Review')
 camera.camera_component.set_field_of_view(65.);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
 pc.set_view_target_with_blend(camera,0);cmd('ShowHUD')
 views=[('road',(-2350,-470,210),(900,150,640)),('canopy',(-1200,-900,130),(500,1300,1550)),('mixed',(-900,150,150),(500,900,400)),('pond',(1600,200,250),(650,1400,900))]
 for mode in (['saved'] if SAVED else ['before','candidate']):
  if mode=='candidate':
   for c,i,m,key in slots:c.set_material(i,mats[key])
   report['lighting']=configure(world,settings())
  if mode=='saved':
   for c,i,m,key in slots:assert m.get_path_name()==mats[key].get_path_name()
   actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
   sun=next(a for a in actors if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='FloraTrail_Sun');sky=next(a for a in actors if isinstance(a,u.SkyLight) and a.get_actor_label()=='FloraTrail_Sky')
   cfg=settings();assert abs(sun.light_component.intensity-cfg['sun_energy']*cfg['sun_unit_gain'])<1e-5
   assert abs(sky.light_component.intensity-cfg['sky_strength']*cfg['sky_unit_gain'])<1e-5
   collection=u.load_asset(D+'/Controls/MPC_SourceLighting');v=u.MaterialLibrary.get_vector_parameter_value(world,collection,'SunDirection');ray=sun.get_actor_forward_vector();assert max(abs(v.r+ray.x),abs(v.g+ray.y),abs(v.b+ray.z))<1e-5
   report['lighting']={'sun':sun.light_component.intensity,'sky':sky.light_component.intensity,'collection_direction':[v.r,v.g,v.b]}
  for label,pos,target in views:
   if mode=='before' and label in ['mixed','pond']:continue
   camera.set_actor_location(u.Vector(*pos),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
   yield from shot('game_'+mode+'_'+label)
 report['rendered_tree_materials']=[c.get_material(i).get_path_name() for c,i,m,key in slots]
 # A temporary neutral emissive card checks the actual game's display transfer.
 camera.set_actor_location(u.Vector(-2350,-470,210),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(-2350,-470,210),u.Vector(900,150,640)),False)
 cube=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=camera.get_actor_location()+camera.get_actor_forward_vector()*300),'Source34_DisplayCheck');cube.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE);assert cube.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));cube.set_actor_scale3d(u.Vector(.5,.5,.5));cube.static_mesh_component.set_material(0,grey)
 yield from shot('game_'+STAGE+'_display_check');cube.destroy_actor()
 pc.set_view_target_with_blend(car,0);cmd('ShowHUD');yield 2;yield from shot('game_'+STAGE+'_driving')
 assert audited_fingerprint()==report['package_fingerprint']
 report.update(ok=True,performance_verified=False,scene_saved=SAVED,existing_packages_unchanged=True);save()
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
