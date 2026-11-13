"""Paired diagnostic render targets, current shipped materials, isolated level."""
import unreal as u,json,sys,time,traceback,array,math,gc,os
from pathlib import Path
R=Path('C:/GrandTour');sys.path.insert(0,str(R/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
O=R/'Art/Export/LidarStudy/FloraParity/AssetMatch';D='/Game/GrandTour/ArtTests/FloraParity/AssetMatch'
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
MOTION='-GTFloraMotion=1' in u.SystemLibrary.get_command_line()
QUICK='-GTFloraCoverage=1' in u.SystemLibrary.get_command_line()
CANDIDATE=False;TEMPORAL=True;MODE='motion' if MOTION else ('coverage' if QUICK else 'build');IMAGE_DIR='unreal-'+MODE if MODE!='build' else 'unreal'
from flora_exact_materials import import_asset,lighting_controls
recipe=json.loads((O/'recipe.json').read_text());report={'ok':False,'mode':MODE,'images':[],'assets':[],'materials':{},'candidates':[]}
SUN_GAIN=.96457146
SKY_GAIN=.89832447
def save():(O/(MODE+'-report.json')).write_text(json.dumps(report,indent=2))
def vec(p):return u.Vector(p[0]*100,-p[1]*100,p[2]*100)

def update_source_light(case):
 mpc=lighting_controls();ray=case['sun_ray'];s=case['sky_strength']*.92909;colour=case.get('sky_colour',[1,1,1])
 u.MaterialLibrary.set_vector_parameter_value(world,mpc,'SunDirection',u.LinearColor(-ray[0],ray[1],-ray[2],0))
 u.MaterialLibrary.set_vector_parameter_value(world,mpc,'SkyRadiance',u.LinearColor(*(v*s for v in colour),0))
def spawn(cls,label,pos=None):
 a=A.spawn_actor_from_class(cls,pos or u.Vector());a.set_actor_label('Parity_'+label);return a
def capture(name,settle=32,ldr_export=True):
 settings=cc.post_process_settings;settings.weighted_blendables=props(u.WeightedBlendables(),array=[]);cc.post_process_settings=settings
 cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_HDR if TEMPORAL else u.SceneCaptureSource.SCS_SCENE_COLOR_HDR;cc.texture_target=hdr
 # SceneCapture visibility/history can lag the actor swap. Warm the SAME target
 # across several editor frames before reading it, not just a wall-clock delay.
 for _ in range(settle if TEMPORAL else 4):cc.capture_scene();yield .03 if TEMPORAL else .15
 colours=u.RenderingLibrary.read_render_target_raw_pixel_area(world,hdr,0,0,512,512,False)
 assert len(colours)==512*512
 raw=array.array('f');raw.extend(v for c in colours for v in (c.r,c.g,c.b,c.a))
 with (O/IMAGE_DIR/(name+'.f32')).open('wb') as f:raw.tofile(f)
 if ldr_export:
  settings=cc.post_process_settings;settings.weighted_blendables=props(u.WeightedBlendables(),array=[props(u.WeightedBlendable(),weight=1.,object=display_material)]);cc.post_process_settings=settings
  cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR;cc.texture_target=ldr
  for _ in range(32):cc.capture_scene();yield .03
  u.RenderingLibrary.export_render_target(world,ldr,str(O/IMAGE_DIR),name+'.png')
  assert (O/IMAGE_DIR/(name+'.png')).is_file()
 report['images'].append(name);save()
def run():
 global world,cc,hdr,ldr,display_material
 (O/IMAGE_DIR).mkdir(parents=True,exist_ok=True);E.make_directory(D)
 if E.does_asset_exist(D+'/L_FloraAssetMatch'):
  assert L.load_level(D+'/L_FloraAssetMatch')
  for old in A.get_all_level_actors():
   if old.get_actor_label().startswith('Parity_'):A.destroy_actor(old)
 else:assert L.new_level(D+'/L_FloraAssetMatch')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 display_material=u.load_asset(D+'/M_SourceStandardDisplay_02')
 if not display_material:
  display_material=u.AssetToolsHelpers.get_asset_tools().create_asset('M_SourceStandardDisplay_02',D,u.Material,u.MaterialFactoryNew())
  props(display_material,material_domain=u.MaterialDomain.MD_POST_PROCESS,blendable_location=u.BlendableLocation.BL_REPLACING_TONEMAPPER)
  dg=Graph(display_material);scene=dg.node(u.MaterialExpressionSceneTexture,scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
  # The sRGB render target performs the display encoding. Doing it here too
  # double-encodes both the neutral receiver and the leaves.
  standard=dg.custom(['C'],'return max(0.,C*View.OneOverPreExposure);')
  dg.wire(scene,standard,'C','Color');dg.output(standard,u.MaterialProperty.MP_EMISSIVE_COLOR);assert not M.recompile_material(display_material);E.save_loaded_asset(display_material,False)
 for cmd in ['Interchange.FeatureFlags.Import.FBX 0','r.AmbientOcclusionLevels 0','r.ScreenPercentage 100','r.MotionBlurQuality 0','r.EyeAdaptationQuality 0','r.ForceLOD 0','r.AntiAliasingMethod 0','r.AllowOcclusionQueries 0','r.HZBOcclusion 0','r.Shadow.Virtual.Enable 1','r.Shadow.Virtual.Cache 1','r.Lumen.DiffuseIndirect.Allow 0','r.Lumen.Reflections.Allow 0']:u.SystemLibrary.execute_console_command(world,cmd)
 if TEMPORAL:u.SystemLibrary.execute_console_command(world,'r.AntiAliasingMethod 4')
 u.SystemLibrary.execute_console_command(world,'r.DistanceFieldAO 0')
 # UE 5.8 Standard ACES ignores Film settings. Select Filmic explicitly,
 # then disable its curve/gamut edits to obtain the source Standard display.
 u.SystemLibrary.execute_console_command(world,'r.LUT.TonemappingMethod 0')
 u.SystemLibrary.execute_console_command(world,'r.LUT.TonemappingSDRInvEOTF 0')
 u.SystemLibrary.execute_console_command(world,'gt.Look.Post 0')
 material=u.load_asset(D+'/M_ParityGrey') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_ParityGrey',D,u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(material);g=Graph(material,'ParityGrey');g.output(g.vector((.18,.18,.18)),u.MaterialProperty.MP_BASE_COLOR);g.output(g.scalar(0),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(0),u.MaterialProperty.MP_SPECULAR);assert not M.recompile_material(material);E.save_loaded_asset(material,False)
 floor=spawn(u.StaticMeshActor,'Receiver');floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));floor.set_actor_scale3d(u.Vector(20,20,20));floor.static_mesh_component.set_material(0,material)
 # Match the source World background as well as its illumination.
 bgmat=u.load_asset(D+'/M_ExactBackground2')
 if not bgmat:
  bgmat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_ExactBackground2',D,u.Material,u.MaterialFactoryNew());props(bgmat,two_sided=True,shading_model=u.MaterialShadingModel.MSM_UNLIT);bggraph=Graph(bgmat)
  bgs=bggraph.node(u.MaterialExpressionCollectionParameter,collection=lighting_controls(),parameter_name='SkyRadiance');bgr=bggraph.custom(['Sky'],'return Sky/.92909;');bggraph.wire(bgs,bgr,'Sky');bggraph.output(bgr,u.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(bgmat);E.save_loaded_asset(bgmat,False)
 background=spawn(u.StaticMeshActor,'WorldBackground');background.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));background.set_actor_scale3d(u.Vector(200,200,200));background.static_mesh_component.set_material(0,bgmat);props(background.static_mesh_component,cast_shadow=False,affect_distance_field_lighting=False,visible_in_ray_tracing=False)
 chart=spawn(u.StaticMeshActor,'Chart',u.Vector(0,0,75));chart.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));chart.set_actor_scale3d(u.Vector(1.3,1.3,1.3));chart.static_mesh_component.set_material(0,material);chart.set_actor_hidden_in_game(True);chart.static_mesh_component.set_visibility(False)
 models={}
 for asset in recipe['assets']:
  mesh=import_asset(asset);assert mesh
  a=spawn(u.StaticMeshActor,asset['key'],vec(asset['location']));c=a.static_mesh_component;c.set_static_mesh(mesh);a.set_actor_scale3d(u.Vector(asset['scale'],asset['scale'],asset['scale']));c.set_forced_lod_model(1)
  bindings=[]
  for i,src in enumerate(c.get_materials()):
   source_mat=src;mat=src;c.set_material(i,mat);bindings.append(dict(source=mat.get_path_name(),bench=mat.get_path_name(),overrides={}))
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
 sky=spawn(u.SkyLight,'Sky');sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=tex,intensity=0,lower_hemisphere_is_black=False,cast_shadows=False)
 sun=spawn(u.DirectionalLight,'Sun');sun.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sun.light_component,intensity=1,light_source_angle=.5,use_temperature=False)
 cap=spawn(u.SceneCapture2D,'Capture');cc=cap.capture_component2d
 hdr=u.RenderingLibrary.create_render_target2d(world,512,512,u.TextureRenderTargetFormat.RTF_RGBA32F)
 ldr=u.RenderingLibrary.create_render_target2d(world,512,512,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
 props(cc,capture_every_frame=False,capture_on_movement=False,always_persist_rendering_state=True,fov_angle=50,post_process_blend_weight=1)
 settings=cc.post_process_settings
 for k,v in dict(auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,auto_exposure_apply_physical_camera_exposure=False,auto_exposure_bias=0.,bloom_intensity=0.,vignette_intensity=0.,film_grain_intensity=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.,tone_curve_amount=0.,expand_gamut=0.,blue_correction=0.).items():
  settings.set_editor_property('override_'+k,True);settings.set_editor_property(k,v)
 cc.post_process_settings=settings
 report['actual_post_settings']={k:cc.post_process_settings.get_editor_property(k) for k in ['tone_curve_amount','expand_gamut','blue_correction','auto_exposure_bias','override_tone_curve_amount']}
 report['postprocess_volumes']=[a.get_actor_label() for a in A.get_all_level_actors() if isinstance(a,u.PostProcessVolume)]
 cc.show_flag_settings=[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=False) for n in ['Fog','Atmosphere','MotionBlur','Bloom','LocalExposure']+([] if TEMPORAL else ['TemporalAA'])]
 if TEMPORAL:cc.show_flag_settings=list(cc.show_flag_settings)+[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=True) for n in ['TemporalAA','AntiAliasing']]
 assert L.save_current_level();yield 8
 report['runtime']={k:u.SystemLibrary.get_console_variable_float_value(k) for k in ['r.Substrate','r.Substrate.ProjectGBufferFormat','r.ScreenPercentage','r.ForceLOD','r.AntiAliasingMethod']}
 for case in ([] if MOTION else recipe['cases']):
  if QUICK and not (case['light']=='front' and case['angle']=='face'):continue
  pos=vec(case['camera']);target=vec(case['target']);cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,target),False,True)
  ray=vec(case['sun_ray']);sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),ray),False);sun.light_component.set_intensity(case['sun_energy']*SUN_GAIN);sky.light_component.set_intensity(case['sky_strength']*SKY_GAIN)
  update_source_light(case)
  sun.light_component.set_light_color(u.LinearColor(*case.get('sun_colour',[1,1,1]),1));sky.light_component.set_light_color(u.LinearColor(*case.get('sky_colour',[1,1,1]),1))
  a=models[case['asset']];a.set_actor_hidden_in_game(False);a.static_mesh_component.set_visibility(True);yield 1
  yield from capture(case['name'])
  a.set_actor_hidden_in_game(True);a.static_mesh_component.set_visibility(False)
  if (case['asset']=='tree' and case['angle']=='face') or (TEMPORAL and case['name']=='fern_front_face'):
   chart.set_actor_hidden_in_game(False);chart.static_mesh_component.set_visibility(True);yield 1;yield from capture('chart_'+case['light']);chart.set_actor_hidden_in_game(True);chart.static_mesh_component.set_visibility(False)
 case=recipe['cases'][0];pos=vec(case['camera']);cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,vec(case['target'])),False,True)
 sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),vec(case['sun_ray'])),False);sun.light_component.set_intensity(3*SUN_GAIN);sun.light_component.set_editor_property('cast_shadows',False);sky.light_component.set_intensity(0)
 sun.light_component.set_light_color(u.LinearColor(1,1,1,1));sky.light_component.set_light_color(u.LinearColor(1,1,1,1))
 update_source_light(dict(case,sky_strength=0))
 background.set_actor_hidden_in_game(True);background.static_mesh_component.set_visibility(False)
 for key,a in ([] if MOTION or QUICK else models.items()):
  a.set_actor_hidden_in_game(False);a.static_mesh_component.set_visibility(True);yield 1;yield from capture(key+'_noshadow_face');a.set_actor_hidden_in_game(True);a.static_mesh_component.set_visibility(False)
 from flora_exact_materials import pigment_material
 background.set_actor_hidden_in_game(True);background.static_mesh_component.set_visibility(False)
 floor.set_actor_hidden_in_game(True);floor.static_mesh_component.set_visibility(False);sun.light_component.set_intensity(0);sky.light_component.set_intensity(0)
 case=recipe['cases'][0];pos=vec(case['camera']);cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,vec(case['target'])),False,True)
 for white in ([] if MOTION else ([True] if QUICK else [False,True])):
  for key,a in models.items():
   c=a.static_mesh_component;original=list(c.get_materials())
   for index,mat in enumerate(original):c.set_material(index,pigment_material(mat,white))
   a.set_actor_hidden_in_game(False);c.set_visibility(True);yield 1;yield from capture(key+('_opacity_face' if white else '_pigment_face'));a.set_actor_hidden_in_game(True);c.set_visibility(False)
   for index,mat in enumerate(original):c.set_material(index,mat)
 if MOTION:
  report['motion_cases']=[]
  sun.light_component.set_editor_property('cast_shadows',True)
  background.set_actor_hidden_in_game(False);background.static_mesh_component.set_visibility(True)
  floor.set_actor_hidden_in_game(False);floor.static_mesh_component.set_visibility(True)
  a=models['shrub'];a.set_actor_hidden_in_game(False);a.static_mesh_component.set_visibility(True)
  case=dict(recipe['cases'][0]);case['asset']='shrub'
  sky.light_component.set_intensity(.8*SKY_GAIN);sun.light_component.set_intensity(3*SUN_GAIN);update_source_light(case)
  yield from capture('warmup')
  for frame in range(48):
   phase=2*math.pi*frame/48;theta=.20*math.sin(phase)
   pos=u.Vector(math.sin(theta)*360,math.cos(theta)*360,165);target=u.Vector(0,0,100)
   cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,target),False,True)
   direction=[-.3+.5*math.sin(phase),-.8,1];length=math.sqrt(sum(v*v for v in direction))
   case['sun_ray']=[-v/length for v in direction];update_source_light(case)
   sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),vec(case['sun_ray'])),False)
   name='motion_%03d'%frame;report['motion_cases'].append(dict(name=name,camera=list(pos.to_tuple()),sun_ray=case['sun_ray']))
   yield from capture(name,settle=1,ldr_export=False)
  # Compare motion frames against the identical camera/light after settling.
  # These controls are captured after the sequence so they cannot hide trails
  # by resetting temporal history during the actual movement.
  for index in [6,30]:
   control=report['motion_cases'][index];pos=u.Vector(*control['camera'])
   cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,u.Vector(0,0,100)),False,True)
   case['sun_ray']=control['sun_ray'];update_source_light(case)
   sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),vec(case['sun_ray'])),False)
   yield from capture('settled_%03d'%index,settle=48,ldr_export=False)
  a.set_actor_hidden_in_game(True);a.static_mesh_component.set_visibility(False)
 report.update(ok=True,sky_unit_calibration=SKY_GAIN,sun_unit_calibration=SUN_GAIN,display_overrides=dict(tone_curve_amount=0,expand_gamut=0,blue_correction=0,replacing_tonemapper=D+'/M_SourceStandardDisplay_02',output='Linear source colour to sRGB render target; no external image colour correction'),capture='512 square; TSR, 32 settled frames for HDR and native PNG stills, one evolving HDR frame per motion sample',method='Baked source pigment and processed alpha; per-card hashed coverage; source thick-transmission sun + uniform-sky transfer; native directional shadows',performance_verified=False,limitations=['Sun and uniform-sky source response only; arbitrary local lights and directional sky not implemented','Source thickness transmission uses native surface shadows; source displaced transmission shadow path is not reproduced','VSM caching enabled with stable shadow-pass coverage; dense moving forest performance not measured','Source bark pigment restored; full procedural bark normal transfer remains open','Source display pass is validated for this sRGB capture path; game viewport/output configuration needs its own check; production postprocess unchanged'])
 save();yield 2
 if MOTION:
  cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR;cc.texture_target=ldr;cc.capture_scene();yield 2
 u.SystemLibrary.execute_console_command(world,'r.RHIThread.Enable 0');yield 2
 cc.texture_target=None;A.destroy_actor(cap);cc=None
 display_material=None
 yield 2
 u.RenderingLibrary.release_render_target2d(hdr);u.RenderingLibrary.release_render_target2d(ldr);hdr=ldr=None
 yield 2
 models.clear();a=c=mat=root=source_mat=mesh=tex=sky=sun=cap=chart=floor=material=g=background=bgmat=None
 original=None
 import flora_exact_materials
 flora_exact_materials.T=None;flora_exact_materials.S=None
 assert L.load_level('/Engine/Maps/Entry');yield 2
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

