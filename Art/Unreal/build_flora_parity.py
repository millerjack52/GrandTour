"""Paired diagnostic render targets, current shipped materials, isolated level."""
import unreal as u,json,sys,time,traceback,array,math,gc,os
from pathlib import Path
R=Path('C:/GrandTour');sys.path.insert(0,str(R/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
O=R/'Art/Export/LidarStudy/FloraParity';D='/Game/GrandTour/ArtTests/FloraParity'
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
CANDIDATE=os.environ.get('GT_FLORA_PARITY_CANDIDATE')=='1'
TEMPORAL=os.environ.get('GT_FLORA_PARITY_TEMPORAL')=='1'
MODE=('temporal_candidate' if CANDIDATE else 'temporal_baseline') if TEMPORAL else ('candidate' if CANDIDATE else 'build')
IMAGE_DIR=MODE if TEMPORAL else ('unreal_candidate' if CANDIDATE else 'unreal')
recipe=json.loads((O/'recipe.json').read_text());report={'ok':False,'mode':MODE,'images':[],'assets':[],'materials':{},'candidates':[]}
def save():(O/(MODE+'-report.json')).write_text(json.dumps(report,indent=2))
def vec(p):return u.Vector(p[0]*100,-p[1]*100,p[2]*100)
def spawn(cls,label,pos=None):
 a=A.spawn_actor_from_class(cls,pos or u.Vector());a.set_actor_label('Parity_'+label);return a
def capture(name):
 cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_HDR if TEMPORAL else u.SceneCaptureSource.SCS_SCENE_COLOR_HDR;cc.texture_target=hdr
 # SceneCapture visibility/history can lag the actor swap. Warm the SAME target
 # across several editor frames before reading it, not just a wall-clock delay.
 for _ in range(32 if TEMPORAL else 4):cc.capture_scene();yield .03 if TEMPORAL else .15
 colours=u.RenderingLibrary.read_render_target_raw_pixel_area(world,hdr,0,0,512,512,False)
 assert len(colours)==512*512
 raw=array.array('f');raw.extend(v for c in colours for v in (c.r,c.g,c.b,c.a))
 with (O/IMAGE_DIR/(name+'.f32')).open('wb') as f:raw.tofile(f)
 cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR;cc.texture_target=ldr;cc.capture_scene();yield 1
 u.RenderingLibrary.export_render_target(world,ldr,str(O/IMAGE_DIR),name+'.png')
 assert (O/IMAGE_DIR/(name+'.png')).is_file();report['images'].append(name);save()
def run():
 global world,cc,hdr,ldr
 (O/IMAGE_DIR).mkdir(parents=True,exist_ok=True);E.make_directory(D)
 if E.does_asset_exist(D+'/L_FloraParity'):
  assert L.load_level(D+'/L_FloraParity')
  for old in A.get_all_level_actors():
   if old.get_actor_label().startswith('Parity_'):A.destroy_actor(old)
 else:assert L.new_level(D+'/L_FloraParity')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for cmd in ['r.ScreenPercentage 100','r.MotionBlurQuality 0','r.EyeAdaptationQuality 0','r.ForceLOD 0','r.AntiAliasingMethod 0','r.AllowOcclusionQueries 0','r.HZBOcclusion 0','r.Shadow.Virtual.Enable 1','r.Lumen.DiffuseIndirect.Allow 0','r.Lumen.Reflections.Allow 0']:u.SystemLibrary.execute_console_command(world,cmd)
 if TEMPORAL:u.SystemLibrary.execute_console_command(world,'r.AntiAliasingMethod 2')
 material=u.load_asset(D+'/M_ParityGrey') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_ParityGrey',D,u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(material);g=Graph(material,'ParityGrey');g.output(g.vector((.18,.18,.18)),u.MaterialProperty.MP_BASE_COLOR);g.output(g.scalar(1),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(0),u.MaterialProperty.MP_SPECULAR);assert not M.recompile_material(material);E.save_loaded_asset(material,False)
 floor=spawn(u.StaticMeshActor,'Receiver');floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));floor.set_actor_scale3d(u.Vector(20,20,20));floor.static_mesh_component.set_material(0,material)
 chart=spawn(u.StaticMeshActor,'Chart',u.Vector(0,0,75));chart.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));chart.set_actor_scale3d(u.Vector(1.3,1.3,1.3));chart.static_mesh_component.set_material(0,material);chart.set_actor_hidden_in_game(True);chart.static_mesh_component.set_visibility(False)
 models={}
 for asset in recipe['assets']:
  mesh=u.load_asset('/Game/GrandTour/ArtTests/FloraPath/'+asset['mesh']);assert mesh
  a=spawn(u.StaticMeshActor,asset['key'],vec(asset['location']));c=a.static_mesh_component;c.set_static_mesh(mesh);a.set_actor_scale3d(u.Vector(asset['scale'],asset['scale'],asset['scale']));c.set_forced_lod_model(1)
  bindings=[]
  for i,src in enumerate(c.get_materials()):
   source_mat=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/FloraWorld/Foliage/'+src.get_name()) or src
   # Freeze wind only in bench-local instances; production instances stay intact.
   path=D+'/Baseline/'+source_mat.get_name()
   mat=u.load_asset(path) or E.duplicate_asset(source_mat.get_path_name().split('.')[0],path)
   if isinstance(mat,u.MaterialInstanceConstant):M.set_material_instance_scalar_parameter_value(mat,'BreezeCm',0.);E.save_loaded_asset(mat,False)
   if CANDIDATE:
    from flora_parity_coverage import make_candidate
    mat,detail=make_candidate(mat)
    if detail:report['candidates'].append(detail)
   c.set_material(i,mat);bindings.append(dict(source=source_mat.get_path_name(),bench=mat.get_path_name(),overrides={'BreezeCm':0}))
   root=mat
   while isinstance(root,u.MaterialInstanceConstant):root=root.get_editor_property('parent')
   if isinstance(root,u.Material) and root.get_path_name() not in report['materials']:
    report['materials'][root.get_path_name()]={'tangent_space_normal':root.get_editor_property('tangent_space_normal'),'blend':str(root.blend_mode),'shading_model':str(root.get_editor_property('shading_model')),'parameters':{str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value') for n in M.get_material_expressions(root) if isinstance(n,u.MaterialExpressionScalarParameter)},'custom_nodes':[dict(tag=str(n.get_editor_property('desc')),code=str(n.get_editor_property('code'))) for n in M.get_material_expressions(root) if isinstance(n,u.MaterialExpressionCustom)]}
  b=mesh.get_bounds();report['assets'].append(dict(key=asset['key'],materials=bindings,bounds=dict(origin=list(b.origin.to_tuple()),extent=list(b.box_extent.to_tuple())),forced_lod=1))
  a.set_actor_hidden_in_game(True);c.set_visibility(False);models[asset['key']]=a
 # Constant white environment. Actual intensity follows the shared recipe.
 hp=O/'T_ParityWhite.hdr';hp.write_bytes(b'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 8 +X 16\n'+bytes([128,128,128,129])*128)
 tex=u.load_asset(D+'/T_ParityWhite')
 if not tex:
  task=props(u.AssetImportTask(),filename=str(hp),destination_path=D,destination_name='T_ParityWhite',automated=True,save=True);u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(D+'/T_ParityWhite')
 assert isinstance(tex,u.TextureCube),str(tex)
 sky=spawn(u.SkyLight,'Sky');sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=tex,intensity=0,lower_hemisphere_is_black=False)
 sun=spawn(u.DirectionalLight,'Sun');sun.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sun.light_component,intensity=1,light_source_angle=.5,use_temperature=False)
 cap=spawn(u.SceneCapture2D,'Capture');cc=cap.capture_component2d
 hdr=u.RenderingLibrary.create_render_target2d(world,512,512,u.TextureRenderTargetFormat.RTF_RGBA32F)
 ldr=u.RenderingLibrary.create_render_target2d(world,512,512,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
 props(cc,capture_every_frame=False,capture_on_movement=False,always_persist_rendering_state=True,fov_angle=50,post_process_blend_weight=1)
 settings=cc.post_process_settings
 for k,v in dict(auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,auto_exposure_apply_physical_camera_exposure=False,auto_exposure_bias=0.,bloom_intensity=0.,vignette_intensity=0.,film_grain_intensity=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.).items():
  settings.set_editor_property('override_'+k,True);settings.set_editor_property(k,v)
 cc.post_process_settings=settings
 cc.show_flag_settings=[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=False) for n in ['Fog','Atmosphere','MotionBlur','Bloom','LocalExposure']+([] if TEMPORAL else ['TemporalAA'])]
 if TEMPORAL:cc.show_flag_settings=list(cc.show_flag_settings)+[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=True) for n in ['TemporalAA','AntiAliasing']]
 assert L.save_current_level();yield 8
 report['runtime']={k:u.SystemLibrary.get_console_variable_float_value(k) for k in ['r.Substrate','r.Substrate.ProjectGBufferFormat','r.ScreenPercentage','r.ForceLOD','r.AntiAliasingMethod']}
 for case in recipe['cases']:
  if TEMPORAL and case['name'] not in ['fern_front_face','shrub_side_face','tree_back_face','fern_shade_face']:continue
  pos=vec(case['camera']);target=vec(case['target']);cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,target),False,True)
  ray=vec(case['sun_ray']);sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),ray),False);sun.light_component.set_intensity(case['sun_energy']);sky.light_component.set_intensity(case['sky_strength'])
  a=models[case['asset']];a.set_actor_hidden_in_game(False);a.static_mesh_component.set_visibility(True);yield 1
  yield from capture(case['name'])
  a.set_actor_hidden_in_game(True);a.static_mesh_component.set_visibility(False)
  if (case['asset']=='tree' and case['angle']=='face') or (TEMPORAL and case['name']=='fern_front_face'):
   chart.set_actor_hidden_in_game(False);chart.static_mesh_component.set_visibility(True);yield 1;yield from capture('chart_'+case['light']);chart.set_actor_hidden_in_game(True);chart.static_mesh_component.set_visibility(False)
 report.update(ok=True,capture='512 square SceneCapture2D diagnostics; scene-linear float32 RGBA and native UE final colour PNG; not gameplay screenshots',limitations=['No temporal AA in initial diagnostic capture','Light-unit equivalence awaits grey-chart calibration','Current map materials copied locally with wind disabled; source Blender geometry reused'])
 if TEMPORAL:report.update(capture='32 settled frames of TAA; Final Color HDR in Linear Working Color Space; static coverage diagnostic, not motion validation',limitations=['Tone/exposure path differs from raw pre-postprocess baseline; do not use as a numerical shader parity score','Lighting calibration pending','Static TAA only; motion and TSR validation pending'])
 save();yield 2
 cc.texture_target=None;A.destroy_actor(cap);cc=None
 yield 2
 u.RenderingLibrary.release_render_target2d(hdr);u.RenderingLibrary.release_render_target2d(ldr);hdr=ldr=None
 yield 2
 models.clear();a=c=mat=root=source_mat=mesh=tex=sky=sun=cap=chart=floor=material=g=None
 world=None;gc.collect();u.SystemLibrary.collect_garbage();yield 2
steps=run();state={'busy':False,'deadline':0}
def tick(dt):
 global steps
 if state['busy'] or time.monotonic()<state['deadline']:return
 state['busy']=True
 try:state['deadline']=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(state['handle']);steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(state['handle']);u.SystemLibrary.quit_editor()
 finally:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);state['handle']=u.register_slate_post_tick_callback(tick)

