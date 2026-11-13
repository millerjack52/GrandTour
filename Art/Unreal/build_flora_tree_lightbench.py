"""Isolated source-version lighting bench. Production packages are read-only."""
import unreal as u,json,sys,time,traceback,array,hashlib,gc
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTreeLightBench';OUT=O/'unreal';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
D='/Game/GrandTour/ArtTests/FloraTreeLighting';E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);T=u.AssetToolsHelpers.get_asset_tools()
recipe=json.loads((O/'recipe.json').read_text());report={'ok':False,'images':[],'materials':{},'size':recipe['size']};SIZE=recipe['size']
controls=json.loads((R/'Art/flora_tree_lightbench_settings.json').read_text());SUN_GAIN=controls['sun_unit_gain'];SKY_GAIN=controls['sky_unit_gain']
def save():(OUT/'report.json').write_text(json.dumps(report,indent=2))
def vec(p):return u.Vector(p[0]*100,-p[1]*100,p[2]*100)
def spawn(cls,name,pos=None):
 a=A.spawn_actor_from_class(cls,pos or u.Vector());a.set_actor_label('TreeBench_'+name);return a
def mat(name):
 m=u.load_asset(D+'/'+name) or T.create_asset(name,D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(m);return m
def finish(m):
 assert not M.recompile_material(m);assert E.save_loaded_asset(m,False);return m
def copied(source,name):
 m=u.load_asset(D+'/'+name) or E.duplicate_asset(source.get_path_name().split('.')[0],D+'/'+name);assert m;return m
def checked_hashes():
 hashes=json.loads((O/'protected-before.json').read_text())
 for p,h in hashes.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 return len(hashes)
def capture(name):
 settings=cc.post_process_settings;settings.weighted_blendables=props(u.WeightedBlendables(),array=[]);cc.post_process_settings=settings;cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_HDR;cc.texture_target=hdr
 for _ in range(40):cc.capture_scene();yield .025
 pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(world,hdr,0,0,SIZE,SIZE,False);assert len(pixels)==SIZE*SIZE
 data=array.array('f');data.extend(v for c in pixels for v in (c.r,c.g,c.b,c.a))
 with (OUT/(name+'.f32')).open('wb') as f:data.tofile(f)
 settings=cc.post_process_settings;settings.weighted_blendables=props(u.WeightedBlendables(),array=[props(u.WeightedBlendable(),weight=1.,object=display)]);cc.post_process_settings=settings;cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR;cc.texture_target=ldr
 for _ in range(40):cc.capture_scene();yield .025
 u.RenderingLibrary.export_render_target(world,ldr,str(OUT),name+'.png');assert (OUT/(name+'.png')).exists()
 report['images'].append(name);save()
def show(a,on):a.set_actor_hidden_in_game(not on);a.static_mesh_component.set_visibility(on)
def run():
 global world,cc,hdr,ldr,display
 report['protected_before']=checked_hashes();E.make_directory(D)
 if E.does_asset_exist(D+'/L_TreeLightBench'):
  assert L.load_level(D+'/L_TreeLightBench')
  for a in A.get_all_level_actors():
   if a.get_actor_label().startswith('TreeBench_'):A.destroy_actor(a)
 else:assert L.new_level(D+'/L_TreeLightBench')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for cmd in ['r.AmbientOcclusionLevels 0','r.ScreenPercentage 100','r.MotionBlurQuality 0','r.EyeAdaptationQuality 0','r.ForceLOD 0','r.AntiAliasingMethod 4','r.AllowOcclusionQueries 0','r.HZBOcclusion 0','r.Shadow.Virtual.Enable 1','r.Shadow.Virtual.Cache 1','r.Lumen.DiffuseIndirect.Allow 0','r.Lumen.Reflections.Allow 0','r.DistanceFieldAO 0','gt.Look.Post 0','r.LUT.TonemappingMethod 0','r.LUT.TonemappingSDRInvEOTF 0']:u.SystemLibrary.execute_console_command(world,cmd)
 display=mat('M_StandardCapture');props(display,material_domain=u.MaterialDomain.MD_POST_PROCESS,blendable_location=u.BlendableLocation.BL_REPLACING_TONEMAPPER);g=Graph(display);sc=g.node(u.MaterialExpressionSceneTexture,scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0);f=g.custom(['C'],'return max(0.,C*View.OneOverPreExposure);');g.wire(sc,f,'C','Color');g.output(f,u.MaterialProperty.MP_EMISSIVE_COLOR);finish(display)
 grey=mat('M_Grey');g=Graph(grey);g.output(g.vector((.18,.18,.18)),u.MaterialProperty.MP_BASE_COLOR);g.output(g.scalar(0),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(0),u.MaterialProperty.MP_SPECULAR);finish(grey)
 floor=spawn(u.StaticMeshActor,'Floor');floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));floor.set_actor_scale3d(u.Vector(20,20,20));floor.static_mesh_component.set_material(0,grey)
 chart=spawn(u.StaticMeshActor,'Chart',u.Vector(0,0,75));chart.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));chart.set_actor_scale3d(u.Vector(1.3,1.3,1.3));chart.static_mesh_component.set_material(0,grey);show(chart,False)
 mesh=u.load_asset('/Game/GrandTour/ArtTests/FloraGroup/Assets/SM_Exact_tree');assert mesh
 scene_mesh=u.load_asset('/Game/GrandTour/ArtTests/FloraTrail/Meshes/SM_Exact_tree');assert scene_mesh
 assert mesh.get_static_mesh_description(0).get_triangle_count()==scene_mesh.get_static_mesh_description(0).get_triangle_count()
 assert (mesh.get_bounds().origin-scene_mesh.get_bounds().origin).length()<.01 and (mesh.get_bounds().box_extent-scene_mesh.get_bounds().box_extent).length()<.01
 tree=spawn(u.StaticMeshActor,'Tree',vec(recipe['location']));c=tree.static_mesh_component;c.set_static_mesh(mesh);c.set_forced_lod_model(1);tree.set_actor_scale3d(u.Vector(*([recipe['scale']]*3)))
 digest=hashlib.sha256(Path(recipe['fbx']).read_bytes()).hexdigest();stored=E.get_metadata_tag(mesh,'FloraBarkSHA256')
 assert stored==digest,{'mesh':mesh.get_path_name(),'stored_fbx_sha256':stored,'actual_fbx_sha256':digest}
 report['source_fbx_sha256']=digest;report['scene_lod0_triangles_and_bounds_match']=True
 bark=u.load_asset('/Game/GrandTour/ArtTests/FloraGroup/Assets/M_SourceBark_tree');assert bark
 for i,m in enumerate(c.get_materials()):
  if m.blend_mode!=u.BlendMode.BLEND_MASKED:c.set_material(i,bark)
 source=u.load_asset('/Game/GrandTour/ArtTests/FloraGroup/Assets/M_Exact_tree_Leaf_0_26834fc');assert source
 leafslot=next(i for i,m in enumerate(c.get_materials()) if m.blend_mode==u.BlendMode.BLEND_MASKED)
 # Snapshot the actual scene response without editing its parent material.
 current=u.load_asset('/Game/GrandTour/ArtTests/FloraTrail/Materials/Canopy/M_Exact_tree_Leaf_0_26834fc_coverage_lighting');assert current
 baseline=copied(current,'M_CurrentTree')
 # Private collection: all lighting experiments stay inside this bench.
 mpc=u.load_asset(D+'/MPC_Bench') or T.create_asset('MPC_Bench',D,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
 if len(mpc.get_editor_property('vector_parameters'))!=3:
  props(mpc,vector_parameters=[props(u.CollectionVectorParameter(),parameter_name='SunDirection',default_value=u.LinearColor(0,0,1,0)),props(u.CollectionVectorParameter(),parameter_name='SkyRadiance',default_value=u.LinearColor(1,1,1,0)),props(u.CollectionVectorParameter(),parameter_name='TreeSunDirection',default_value=u.LinearColor(0,0,1,0))]);E.save_loaded_asset(mpc,False)
 for n in M.get_material_expressions(baseline):
  if isinstance(n,u.MaterialExpressionCollectionParameter):
   n.set_editor_property('collection',mpc)
 finish(baseline)
 candidate=copied(source,'M_Source34Tree');props(candidate,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,two_sided=True,tangent_space_normal=False)
 for n in list(M.get_material_expressions(candidate)):
  if str(n.get_editor_property('desc'))=='Source34Light' and not isinstance(n,u.MaterialExpressionScalarParameter):M.delete_material_expression(candidate,n)
 g=Graph(candidate,'Source34Light');nodes=M.get_material_expressions(candidate);pigment=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourcePigment')
 old_hash=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'uint2 p=uint2(Parameters.SvPosition.xy)' in str(n.get_editor_property('code')))
 shadow_coverage=next((n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='SourceShadowCoverage'),None)
 if not shadow_coverage:shadow_coverage=g.node(u.MaterialExpressionScalarParameter,parameter_name='SourceShadowCoverage',default_value=1.)
 shadow_coverage.set_editor_property('default_value',controls.get('shadow_coverage',1.))
 # Build and wire the replacement before switching the active opacity output.
 # Mutating a connected custom node's input array triggers transient failures.
 code=str(old_hash.get_editor_property('code')).replace('Coverage*=ShadowCoverage;','').replace('t=0u;','t=0u;Coverage*=ShadowCoverage;')
 h=Graph(candidate,'Source34Coverage');hashed=h.custom(['Coverage','Seed','ShadowCoverage'],code,u.CustomMaterialOutputType.CMOT_FLOAT1)
 coverage=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float b=clamp(Soft' in str(n.get_editor_property('code')));seed=next(n for n in nodes if isinstance(n,u.MaterialExpressionVertexColor))
 h.wire(coverage,hashed,'Coverage');h.wire(seed,hashed,'Seed','A');h.wire(shadow_coverage,hashed,'ShadowCoverage');h.output(hashed,u.MaterialProperty.MP_OPACITY_MASK);M.delete_material_expression(candidate,old_hash)
 # This source leaf material is 100% Translucent BSDF with authored normal -Z.
 # Eevee 3.4 evaluates the opposite hemisphere (+Z); native UE diffuse +Z
 # supplies the same directional and uniform-sky response with actual shadows.
 g.output(pigment,u.MaterialProperty.MP_BASE_COLOR,'RGB');g.output(g.vector((0,0,1)),u.MaterialProperty.MP_NORMAL);g.output(g.scalar(0),u.MaterialProperty.MP_EMISSIVE_COLOR);g.output(g.scalar(0),u.MaterialProperty.MP_SPECULAR);g.output(g.scalar(0),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(1),u.MaterialProperty.MP_AMBIENT_OCCLUSION);finish(candidate)
 report['candidate']='Original source pigment and facing coverage; native +Z diffuse lobe matching source -Z translucent normal, no emission or colour tint.'
 report['mesh']={'path':mesh.get_path_name(),'forced_lod':1,'location':recipe['location'],'scale':recipe['scale'],'bounds_origin':list(mesh.get_bounds().origin.to_tuple()),'bounds_extent':list(mesh.get_bounds().box_extent.to_tuple())}
 for name,m in [('current',baseline),('matched',candidate)]:
  stat=M.get_statistics(m);report['materials'][name]={'path':m.get_path_name(),'statistics':{k:stat.get_editor_property(k) for k in ['num_pixel_shader_instructions','num_vertex_shader_instructions','num_samplers','num_pixel_texture_samples']},'textures':[{'parameter':str(n.get_editor_property('parameter_name')),'path':n.get_editor_property('texture').get_path_name(),'srgb':n.get_editor_property('texture').get_editor_property('srgb')} for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D)]}
 bgmat=mat('M_Background');props(bgmat,two_sided=True,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=Graph(bgmat);colour=g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name='SkyRadiance');g.output(colour,u.MaterialProperty.MP_EMISSIVE_COLOR);finish(bgmat)
 bg=spawn(u.StaticMeshActor,'Background');bg.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));bg.set_actor_scale3d(u.Vector(200,200,200));bg.static_mesh_component.set_material(0,bgmat);props(bg.static_mesh_component,cast_shadow=False,affect_distance_field_lighting=False,visible_in_ray_tracing=False)
 cube=u.load_asset('/Game/GrandTour/ArtTests/FloraParity/AssetMatch/T_ParityWhite');assert cube
 sky=spawn(u.SkyLight,'Sky');sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=cube,intensity=0,lower_hemisphere_is_black=False,cast_shadows=False)
 sun=spawn(u.DirectionalLight,'Sun');sun.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sun.light_component,intensity=1,light_source_angle=.5,use_temperature=False)
 cap=spawn(u.SceneCapture2D,'Capture');cc=cap.capture_component2d;hdr=u.RenderingLibrary.create_render_target2d(world,SIZE,SIZE,u.TextureRenderTargetFormat.RTF_RGBA16F);ldr=u.RenderingLibrary.create_render_target2d(world,SIZE,SIZE,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
 props(cc,capture_every_frame=False,capture_on_movement=False,always_persist_rendering_state=True,fov_angle=recipe['fov'],post_process_blend_weight=1)
 settings=cc.post_process_settings
 for k,v in dict(auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,auto_exposure_apply_physical_camera_exposure=False,auto_exposure_bias=0.,bloom_intensity=0.,vignette_intensity=0.,film_grain_intensity=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.,tone_curve_amount=0.,expand_gamut=0.,blue_correction=0.).items():settings.set_editor_property('override_'+k,True);settings.set_editor_property(k,v)
 cc.post_process_settings=settings;cc.show_flag_settings=[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=False) for n in ['Fog','Atmosphere','MotionBlur','Bloom','LocalExposure']]+[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=True) for n in ['TemporalAA','AntiAliasing']]
 yield 6
 for case in recipe['cases']:
  pos=vec(case['camera']);cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,vec(case['target'])),False,True)
  sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),vec(case['sun_ray'])),False);sun.light_component.set_intensity(case['sun_energy']*SUN_GAIN);sun.light_component.set_light_color(u.LinearColor(*case['sun_colour'],1))
  sky.light_component.set_intensity(case['sky_strength']*SKY_GAIN);sky.light_component.set_light_color(u.LinearColor(*case['sky_colour'],1))
  ray=case['sun_ray'];u.MaterialLibrary.set_vector_parameter_value(world,mpc,'SunDirection',u.LinearColor(-ray[0],ray[1],-ray[2],0));u.MaterialLibrary.set_vector_parameter_value(world,mpc,'SkyRadiance',u.LinearColor(*(v*case['sky_strength'] for v in case['sky_colour']),0))
  u.MaterialLibrary.set_vector_parameter_value(world,mpc,'TreeSunDirection',u.LinearColor(-ray[0],ray[1],-ray[2],0))
  for name,m in [('current',baseline),('matched',candidate)]:c.set_material(leafslot,m);show(tree,True);show(chart,False);yield from capture(name+'_'+case['name'])
  show(tree,False);show(chart,True);yield from capture('chart_'+case['name']);show(chart,False)
 # Separate the source light lobe from shadow-receiver implementation.
 show(tree,True);show(chart,False);c.set_material(leafslot,candidate);sun.light_component.set_editor_property('cast_shadows',False);yield from capture('matched_sun_unshadowed');sun.light_component.set_editor_property('cast_shadows',True)
 u.SystemLibrary.execute_console_command(world,'r.Shadow.Virtual.Enable 0');yield 2;yield from capture('matched_sun_cascade');u.SystemLibrary.execute_console_command(world,'r.Shadow.Virtual.Enable 1');yield 2
 u.SystemLibrary.execute_console_command(world,'r.Shadow.Virtual.Cache 0')
 for factor in [.65,.35,.15]:
  mid=c.create_dynamic_material_instance(leafslot,candidate);mid.set_scalar_parameter_value('SourceShadowCoverage',factor);yield from capture('shadow_coverage_'+str(int(factor*100)))
 c.set_material(leafslot,candidate);u.SystemLibrary.execute_console_command(world,'r.Shadow.Virtual.Cache 1')
 for bias in [1.5,4.,8.]:
  u.SystemLibrary.execute_console_command(world,'r.Shadow.Virtual.NormalBias '+str(bias));yield from capture('shadow_bias_'+str(bias).replace('.','_'))
 u.SystemLibrary.execute_console_command(world,'r.Shadow.Virtual.NormalBias 0.5')
 # Independent opacity and pigment masks for foliage-only measurements.
 show(bg,False);show(floor,False);show(tree,True);sun.light_component.set_intensity(0);sky.light_component.set_intensity(0)
 original=list(c.get_materials())
 for white in [False,True]:
  for i,m in enumerate(original):
   diagnostic=copied(m,('M_Opacity_' if white else 'M_Pigment_')+str(i));props(diagnostic,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=Graph(diagnostic)
   tex=next(n for n in M.get_material_expressions(diagnostic) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name')) in ['SourcePigment','SourceBarkColour'])
   g.output(g.scalar(1) if white else tex,u.MaterialProperty.MP_EMISSIVE_COLOR,'' if white else 'RGB');finish(diagnostic);c.set_material(i,diagnostic)
  yield from capture('tree_opacity_face' if white else 'tree_pigment_face')
  for i,m in enumerate(original):c.set_material(i,m)
 show(bg,True);show(floor,True);c.set_material(leafslot,candidate)
 case=recipe['cases'][0];sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),vec(case['sun_ray'])),False);sun.light_component.set_intensity(case['sun_energy']*SUN_GAIN);sun.light_component.set_light_color(u.LinearColor(*case['sun_colour'],1));sky.light_component.set_intensity(case['sky_strength']*SKY_GAIN);sky.light_component.set_light_color(u.LinearColor(*case['sky_colour'],1))
 u.MaterialLibrary.set_vector_parameter_value(world,mpc,'SkyRadiance',u.LinearColor(*(v*case['sky_strength'] for v in case['sky_colour']),0))
 pos=vec(case['camera']);rotation=u.MathLibrary.find_look_at_rotation(pos,vec(case['target']));u.EditorLevelLibrary.set_level_viewport_camera_info(pos,rotation)
 assert L.save_current_level();report.update(ok=True,protected_after=checked_hashes(),sun_gain=SUN_GAIN,sky_gain=SKY_GAIN,display='Standard linear to native sRGB target; no external image recolouring',performance_verified=False,scene_modified=False);save()
 yield 2;cc.texture_target=None;A.destroy_actor(cap);cc=None;yield 2;u.RenderingLibrary.release_render_target2d(hdr);u.RenderingLibrary.release_render_target2d(ldr);hdr=ldr=None
 L.load_level('/Engine/Maps/Entry');yield 3
steps=run();state={'busy':False,'due':0}
def tick(dt):
 global steps
 if state['busy'] or time.monotonic()<state['due']:return
 state['busy']=True
 try:state['due']=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;u.unregister_slate_post_tick_callback(handle)
  for k,v in list(globals().items()):
   if not k.startswith('__') and k not in ('u','time'):globals()[k]=None
  v=None;import gc;gc.collect();u.SystemLibrary.collect_garbage();globals()['quit_at']=time.monotonic()+3
  def close(dt):
   if time.monotonic()>quit_at:u.unregister_slate_post_tick_callback(quit_handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
  globals()['quit_handle']=u.register_slate_post_tick_callback(close)
 except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
