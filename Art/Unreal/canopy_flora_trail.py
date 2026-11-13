"""Controlled tree tests, all from identical cameras and unchanged scene lights."""
import unreal as u,json,sys,time,traceback,gc,hashlib
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Canopy';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'Art/Unreal'))
from benmore_river_life_materials import props
from flora_trail_canopy_materials import candidate
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'images':[],'tree_materials':[]};cfg=json.loads((R/'Art/flora_trail_canopy_settings.json').read_text())
def save():(O/'canopy-report.json').write_text(json.dumps(report,indent=2))
def cmd(s):u.SystemLibrary.execute_console_command(world,s)
def run():
 global world
 level='/Game/GrandTour/ArtTests/FloraTrail/L_FloraTrail'
 before=hashlib.sha256((R/'Content/GrandTour/ArtTests/FloraTrail/L_FloraTrail.umap').read_bytes()).hexdigest()
 assert L.load_level(level);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for c in json.loads((R/'Art/flora_trail_settings.json').read_text())['console']:cmd(c)
 actors=A.get_all_level_actors();trees=[];slots=[]
 for a in actors:
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.get_instance_count() and c.static_mesh and c.static_mesh.get_path_name().startswith('/Game/GrandTour/ArtTests/FloraTrail/Meshes/') and c.static_mesh.get_name() in ['SM_Exact_tree','SM_Exact_pine']:
    trees.append(c)
    for i,m in enumerate(c.get_materials()):
     if m.blend_mode==u.BlendMode.BLEND_MASKED:slots.append((c,i,m))
 assert len(trees)==4 and len(slots)==4
 variants={}
 for c,i,m in slots:
  if m.get_path_name() in variants:continue
  variants[m.get_path_name()]={(a,b):candidate(m,a,b,cfg) for a,b in [(True,False),(False,True),(True,True)]}
  report['tree_materials'].append(m.get_path_name())
 pp=next(a for a in actors if a.get_actor_label()=='FloraTrail_Display')
 ps=pp.settings;ps.weighted_blendables=props(u.WeightedBlendables(),array=[props(u.WeightedBlendable(),weight=1.,object=u.load_asset('/Game/GrandTour/ArtTests/FloraParity/AssetMatch/M_SourceStandardDisplay_02'))]);pp.settings=ps
 capture=A.spawn_actor_from_class(u.SceneCapture2D,u.Vector());cc=capture.capture_component2d
 rt=u.RenderingLibrary.create_render_target2d(world,1200,675,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
 props(cc,capture_every_frame=False,capture_on_movement=False,always_persist_rendering_state=True,fov_angle=65.,capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR,texture_target=rt,post_process_blend_weight=1.);cc.post_process_settings=ps
 cc.show_flag_settings=[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=True) for n in ['TemporalAA','AntiAliasing','Fog','Atmosphere']]
 views=[('canopy',(-1200,-900,130),(500,1300,1550)),('road',(-2350,-470,210),(900,150,640))]
 sun=next(a for a in actors if a.get_actor_label()=='FloraTrail_Sun');sun_intensity=sun.light_component.intensity
 for case,a,b,lod,light in [('00_before',False,False,0,True),('01_lod0_only',False,False,1,True),('02_coverage_only',True,False,0,True),('03_lighting_only',False,True,0,True),('04_combined',True,True,0,True),('05_combined_sun_off',True,True,0,False)]:
  for c in trees:c.set_forced_lod_model(lod)
  for c,i,m in slots:c.set_material(i,variants[m.get_path_name()][a,b] if a or b else m)
  sun.light_component.set_intensity(sun_intensity if light else 0);yield 3
  for label,pos,target in views:
   capture.set_actor_location(u.Vector(*pos),False,True);capture.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
   for frame in range(64):cc.capture_scene();yield .02
   name=case+'_'+label;u.RenderingLibrary.export_render_target(world,rt,str(O),name+'.png');assert (O/(name+'.png')).exists();report['images'].append(name);save()
 sun.light_component.set_intensity(sun_intensity)
 cc.texture_target=None;A.destroy_actor(capture);u.RenderingLibrary.release_render_target2d(rt)
 assert hashlib.sha256((R/'Content/GrandTour/ArtTests/FloraTrail/L_FloraTrail.umap').read_bytes()).hexdigest()==before
 report.update(ok=True,map_unchanged=True,settings=cfg,cameras=views,source_textures_preserved=True);save()
 cmd('r.RHIThread.Enable 0');yield 2;assert L.load_level('/Engine/Maps/Entry');yield 3
 world=None;variants.clear();slots.clear();trees.clear();gc.collect();u.SystemLibrary.collect_garbage();yield 2
steps=run();state={'busy':False,'due':0}
def tick(dt):
 global steps
 if state['busy'] or time.monotonic()<state['due']:return
 state['busy']=True
 try:state['due']=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;u.unregister_slate_post_tick_callback(handle)
  for key,value in list(globals().items()):
   if not key.startswith('__') and key not in ('u','time'):globals()[key]=None
  value=None
  import gc
  gc.collect();u.SystemLibrary.collect_garbage();globals()['quit_at']=time.monotonic()+3
  def close(dt):
   if time.monotonic()>quit_at:u.unregister_slate_post_tick_callback(quit_handle);u.SystemLibrary.quit_editor()
  globals()['quit_handle']=u.register_slate_post_tick_callback(close)
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);steps=None;u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
