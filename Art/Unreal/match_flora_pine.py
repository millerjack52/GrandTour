"""Pine-only source matching. Isolated native 768-square capture, no scene grading."""
import unreal as u,json,sys,time,traceback,os,gc,hashlib
from pathlib import Path
R=Path('C:/GrandTour');sys.path[:0]=[str(R/'Art/Unreal'),str(R/'Art')]
from benmore_river_life_materials import props,Graph
from flora_pine_match_baseline import verify
P='/Game/GrandTour/ArtTests/FloraTrail/PineTrial';D=P+'/SourceMatch';O=R/'Art/Export/FloraTrail/PineMatch'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem)
stage=os.environ.get('GT_PINE_MATCH_STAGE','probe');report={'ok':False,'stage':stage,'images':[]};state={'busy':False,'due':0}
def save():(O/(stage+'-report.json')).write_text(json.dumps(report,indent=2))
def vec(v):return u.Vector(v[0]*100,-v[1]*100,v[2]*100)
def spawn(cls,name,pos=None):
 a=A.spawn_actor_from_class(cls,pos or u.Vector());a.set_actor_label(name);return a
def clone(source,name):
 path=D+'/'+name
 return u.load_asset(path) or E.duplicate_asset(source.get_path_name().split('.')[0],path)
def finish(m):assert not M.recompile_material(m);assert E.save_loaded_asset(m,False);return m
def pigment(source,white=False):
 m=clone(source,stage+('_M_Opacity_' if white else '_M_Pigment_')+source.get_name());props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=Graph(m)
 tex=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name')) in ('SourcePigment','SourceBarkColour'))
 g.output(g.scalar(1) if white else tex,u.MaterialProperty.MP_EMISSIVE_COLOR,'' if white else 'RGB');return finish(m)
def gain_material(source,gain):
 m=clone(source,'M_Coverage_'+str(int(gain*100)))
 node=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'float b=clamp(Soft' in str(n.get_editor_property('code')))
 code=str(node.get_editor_property('code')).replace('saturate(A*','saturate('+str(gain)+'*A*')
 node.set_editor_property('code',code);return finish(m)
def sampling_material(source,kind):
 m=clone(source,'M_Sampling_'+kind)
 if kind=='mip0':
  n=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourceCoverage')
  props(n,mip_value_mode=u.TextureMipValueMode.TMVM_MIP_LEVEL,const_mip_value=0)
 else:
  old=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'uint2 p=uint2(Parameters.SvPosition.xy)' in str(n.get_editor_property('code')))
  code=str(old.get_editor_property('code')).replace('View.StateFrameIndex & 7u','View.StateFrameIndex & 127u').replace('uint rank=((t&1u)<<2)|(t&2u)|((t&4u)>>2);','uint rank=reversebits(t)>>25;').replace('float(rank)*.125','float(rank)/128.')
  if kind=='depth128':
   code=code.replace('h^=h>>16;h*=0x7feb352du;', '#if !SHADOW_DEPTH_SHADER\nuint3 cell=uint3(int3(floor(P*4.)));h^=cell.x*73856093u+cell.y*19349663u+cell.z*83492791u;\n#endif\nh^=h>>16;h*=0x7feb352du;')
   g=Graph(m,'PineCoverageSampling');hashed=g.custom(['Coverage','Seed','ShadowCoverage','P'],code,u.CustomMaterialOutputType.CMOT_FLOAT1)
   nodes=M.get_material_expressions(m)
   coverage=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float b=clamp(Soft' in str(n.get_editor_property('code')))
   seed=next(n for n in nodes if isinstance(n,u.MaterialExpressionVertexColor));shadow=next(n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='SourceShadowCoverage')
   g.wire(coverage,hashed,'Coverage');g.wire(seed,hashed,'Seed','A');g.wire(shadow,hashed,'ShadowCoverage');g.wire(g.node(u.MaterialExpressionWorldPosition),hashed,'P');g.output(hashed,u.MaterialProperty.MP_OPACITY_MASK)
   M.delete_material_expression(m,old)
  else:old.set_editor_property('code',code)
 return finish(m)
def source_mask():
 data=json.loads((O/'mask-report.json').read_text());assert data['ok'] and data['source_unchanged']
 path=D+'/T_SourceMask4K';tex=u.load_asset(path)
 if not tex:
  task=props(u.AssetImportTask(),filename=data['masks']['Leaf_0.002'],destination_path=D,destination_name='T_SourceMask4K',automated=True,save=True)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(path)
 props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE,max_texture_size=4096,lod_bias=0);assert E.save_loaded_asset(tex,False)
 return tex
def matched_material(source,name,tex,gain=1.,surface_only=False):
 m=clone(source,'M_'+name)
 for n in M.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourceCoverage':n.set_editor_property('texture',tex)
  if isinstance(n,u.MaterialExpressionCustom):
   code=str(n.get_editor_property('code'))
   if gain!=1 and not surface_only and 'float b=clamp(Soft' in code:n.set_editor_property('code',code.replace('saturate(A*','saturate('+str(gain)+'*A*'))
   if gain!=1 and surface_only and 'uint2 p=uint2(Parameters.SvPosition.xy)' in code:n.set_editor_property('code',code.replace('Coverage*=ShadowCoverage;\n#endif','Coverage*=ShadowCoverage;\n#else\nCoverage*= '+str(gain)+';\n#endif'))
 return finish(m)
def run():
 global world,cc,target
 baseline=verify(True);recipe=json.loads((O/'recipe.json').read_text())
 existing={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in baseline['hashes']}
 assert L.load_level('/Engine/Maps/Entry');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for c in ['r.AmbientOcclusionLevels 0','r.ScreenPercentage 100','r.MotionBlurQuality 0','r.EyeAdaptationQuality 0','r.AntiAliasingMethod 4','r.Shadow.Virtual.Enable 1','r.Shadow.Virtual.Cache 1','r.Lumen.DiffuseIndirect.Allow 0','r.Lumen.Reflections.Allow 0','r.DistanceFieldAO 0','gt.Look.Post 0','r.LUT.TonemappingMethod 0','r.LUT.TonemappingSDRInvEOTF 0','r.Streaming.FullyLoadUsedTextures 1']:
  u.SystemLibrary.execute_console_command(world,c)
 mesh=u.load_asset(P+'/Assets/SM_Exact_pine_f002');assert mesh
 bark=u.load_asset(P+'/Assets/T_SourceBark_pine_f002');deadline=time.monotonic()+120
 while bark.blueprint_get_size_x()!=4096:
  assert time.monotonic()<deadline;yield .25
 report['bounds']={'origin':list(mesh.get_bounds().origin.to_tuple()),'extent':list(mesh.get_bounds().box_extent.to_tuple())}
 tree=spawn(u.StaticMeshActor,'PineMatchTree');tree.static_mesh_component.set_static_mesh(mesh);tree.static_mesh_component.set_forced_lod_model(1);comp=tree.static_mesh_component
 originals=list(comp.get_materials());leafslot=next(i for i,m in enumerate(originals) if m.blend_mode==u.BlendMode.BLEND_MASKED);leaf=originals[leafslot]
 if stage not in ('install','recheck'):
  leaf=u.load_asset(D+'/M_PreMatch') or leaf
 report['leaf_nodes']=[{'name':n.get_name(),'code':str(n.get_editor_property('code'))} for n in M.get_material_expressions(leaf) if isinstance(n,u.MaterialExpressionCustom)]
 report['leaf_parameters']={str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value') for n in M.get_material_expressions(leaf) if isinstance(n,u.MaterialExpressionScalarParameter)}
 variants={'baseline':leaf}
 if stage in ('install','recheck'):
  before=clone(leaf,'M_PreMatch') if stage=='install' else u.load_asset(D+'/M_PreMatch')
  assert before
  if stage=='install':assert E.save_loaded_asset(before,False)
  if stage=='install':
   from flora_pine_match_materials import apply
   report['installed_settings']=apply(leaf)
  else:report['installed_settings']=json.loads((R/'Art/flora_pine_match_settings.json').read_text())
  variants={'baseline':before,'candidate':leaf}
  tex=u.load_asset(D+'/T_SourceMask4K');assert tex
  deadline=time.monotonic()+120
  while tex.blueprint_get_size_x()!=4096:
   assert time.monotonic()<deadline;yield .25
  report['saved_coverage_size']=[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()]
 elif stage=='temporal':
  tex=source_mask()
  for name,texture in [('static2k',None),('static4k',tex)]:
   mat=clone(leaf,'M_'+name) if texture is None else matched_material(leaf,name,texture)
   props(mat,has_pixel_animation=False);variants[name]=finish(mat)
 elif stage=='candidate':
  tex=source_mask()
  for name,gain,surface in [('mask4k',1.,False),('surface150',1.5,True),('all150',1.5,False)]:variants[name]=matched_material(leaf,name,tex,gain,surface)
  deadline=time.monotonic()+120
  while tex.blueprint_get_size_x()!=4096:
   assert time.monotonic()<deadline;yield .25
 elif stage=='sampling':
  for kind in ('screen128','depth128','mip0'):variants[kind]=sampling_material(leaf,kind)
 else:
  for gain in (1.25,1.5):variants['coverage'+str(int(gain*100))]=gain_material(leaf,gain)
  up=clone(leaf,'M_UpNormal');Graph(up).output(Graph(up).vector((0,0,1)),u.MaterialProperty.MP_NORMAL);variants['up_normal']=finish(up)
 bg=spawn(u.StaticMeshActor,'PineMatchBackdrop');bg.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));bg.set_actor_scale3d(u.Vector(200,200,200));bg.static_mesh_component.set_material(0,u.load_asset(P+'/Assets/M_SourceBackdrop'));props(bg.static_mesh_component,cast_shadow=False,affect_distance_field_lighting=False,visible_in_ray_tracing=False)
 sky=spawn(u.SkyLight,'PineMatchSky');sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
 props(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=u.load_asset('/Game/GrandTour/ArtTests/FloraParity/AssetMatch/T_ParityWhite'),intensity=.784,lower_hemisphere_is_black=False,cast_shadows=False)
 sky.light_component.set_light_color(u.LinearColor(.58,.74,1,1));sky.light_component.recapture_sky()
 sun=spawn(u.DirectionalLight,'PineMatchSun');sun.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sun.light_component,intensity=15.68,light_source_angle=.5,use_temperature=False);sun.light_component.set_light_color(u.LinearColor(1,.814,.539,1))
 cap=spawn(u.SceneCapture2D,'PineMatchCapture');cc=cap.capture_component2d
 target=u.RenderingLibrary.create_render_target2d(world,768,768,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
 props(cc,capture_every_frame=False,capture_on_movement=False,always_persist_rendering_state=True,fov_angle=recipe['camera']['horizontal_fov'],post_process_blend_weight=1,capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR,texture_target=target)
 s=cc.post_process_settings
 for k,v in dict(auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,auto_exposure_apply_physical_camera_exposure=False,auto_exposure_bias=0.,bloom_intensity=0.,vignette_intensity=0.,film_grain_intensity=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.,tone_curve_amount=0.,expand_gamut=0.,blue_correction=0.).items():props(s,**{'override_'+k:True,k:v})
 s.weighted_blendables=props(u.WeightedBlendables(),array=[props(u.WeightedBlendable(),weight=1.,object=u.load_asset('/Game/GrandTour/ArtTests/FloraTreeLighting/M_StandardCapture'))]);cc.post_process_settings=s
 cc.show_flag_settings=[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=False) for n in ['Fog','Atmosphere','MotionBlur','Bloom','LocalExposure']]+[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=True) for n in ['TemporalAA','AntiAliasing']]
 pos=vec(recipe['camera']['position']);cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,vec(recipe['camera']['target'])),False,True)
 yield 8
 def capture(name):
  for _ in range(128):cc.capture_scene();yield .025
  u.RenderingLibrary.export_render_target(world,target,str(O),name+'.png');assert (O/(name+'.png')).exists();report['images'].append(name);save()
 for case in recipe['cases']:
  sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),vec(case['ray'])),False)
  if stage in ('sampling','temporal') and case['name']!='warm':continue
  for name,mat in variants.items():
   if stage not in ('candidate','install','recheck') and name!='baseline' and case['name']!='warm':continue
   comp.set_material(leafslot,mat);yield from capture('ue_'+name+'_'+case['name'])
 comp.set_material(leafslot,leaf)
 bg.set_actor_hidden_in_game(True);bg.static_mesh_component.set_visibility(False);sun.light_component.set_intensity(0);sky.light_component.set_intensity(0)
 for name,variant in variants.items():
  for white in (False,True):
   if name not in ('baseline','candidate') and not white:continue
   for i,m in enumerate(originals):comp.set_material(i,pigment(variant if i==leafslot else m,white))
   yield from capture('ue_'+name+('_opacity' if white else '_pigment'))
 verify(True)
 if stage!='install':
  for p,digest in existing.items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==digest,p
 report.update(ok=True,native_size=[768,768],scene_unchanged=True);save()
 cc.texture_target=None;A.destroy_actor(cap);u.RenderingLibrary.release_render_target2d(target);target=cc=None
 L.load_level('/Engine/Maps/Entry');yield 3
def close():
 for key,value in list(globals().items()):
  if not key.startswith('__') and key not in ('u','time'):globals()[key]=None
 value=None
 import gc
 gc.collect();u.SystemLibrary.collect_garbage();globals()['quit_at']=time.monotonic()+3
 def shutdown(dt):
  if time.monotonic()>quit_at:
   u.unregister_slate_post_tick_callback(quit_handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 globals()['quit_handle']=u.register_slate_post_tick_callback(shutdown)
steps=run()
def tick(dt):
 global steps
 if state['busy'] or time.monotonic()<state['due']:return
 state['busy']=True
 try:state['due']=time.monotonic()+next(steps)
 except StopIteration:steps=None;u.unregister_slate_post_tick_callback(handle);close()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);close()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
