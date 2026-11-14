"""A separate drivable FloraTrail map: change pine species, hold lighting fixed."""
import unreal as u,json,sys,os,time,traceback,hashlib,math
from pathlib import Path
R=Path('C:/GrandTour');sys.path[:0]=[str(R/'Art/Unreal'),str(R/'Art')]
from benmore_river_life_materials import props,Graph
from flora_trail_palette_baseline import verify as protected
from flora_trail_asset_audit import verify as audit_baseline,await_bark_textures
from flora_trail_source34 import configure,settings
import flora_exact_materials as fm
D='/Game/GrandTour/ArtTests/FloraTrail';P=D+'/PineTrial';LEVEL=P+'/L_FloraTrail_Pine'
SOURCE=R/'Art/Export/FloraTrail/PineTrial';O=Path(os.environ.get('GT_PINE_OUTPUT',str(SOURCE)));O.mkdir(parents=True,exist_ok=True);stage=os.environ.get('GT_PINE_STAGE','verify')
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;L=u.get_editor_subsystem(u.LevelEditorSubsystem);A=u.get_editor_subsystem(u.EditorActorSubsystem)
report={'ok':False,'stage':stage,'level':LEVEL,'images':[],'performance_verified':False,'gates':{},'motion_checked':False}
state={'busy':False,'due':0,'frame':0};world=pc=car=camera=None
cfg=json.loads((R/'Art/flora_trail_palette_probe_settings.json').read_text())
def save():(O/(stage+'-report.json')).write_text(json.dumps(report,indent=2))
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def frames(n):
 end=state['frame']+n
 while state['frame']<end:yield 0
def shot(name,settle=120):
 yield from frames(settle)
 path=O/(name+'.png');stamp=time.time();cmd('Shot filename="'+path.as_posix()+'" -nosuffix');deadline=time.monotonic()+45
 while not path.exists() or path.stat().st_mtime<stamp:
  assert time.monotonic()<deadline,name
  yield .2
 h=path.read_bytes()[:24];report['images'].append({'name':name,'size':[int.from_bytes(h[16:20],'big'),int.from_bytes(h[20:24],'big')]});save()
def import_tree(data):
 fm.D=P+'/Assets';fm.O=O
 asset=data['recipe']['assets'][0];slot=next(s for s in asset['exact_slots'] if s['foliage'])
 assert 0<=slot['diffuse_weight']<.05 and slot['emission_strength']==0,slot
 pigment=fm.texture(asset['textures']['Colour'],False);coverage=fm.texture(slot['shared_mask'],True)
 bark=fm.texture(data['bark'],False);props(bark,max_texture_size=4096,lod_bias=0);E.save_loaded_asset(bark,False)
 leafpath=P+'/Assets/M_Source34_pine_f002';leaf=u.load_asset(leafpath) or E.duplicate_asset('/Game/GrandTour/ArtTests/FloraTreeLighting/M_Source34Tree',leafpath)
 for n in M.get_material_expressions(leaf):
  if isinstance(n,u.MaterialExpressionTextureSampleParameter2D):
   key=str(n.get_editor_property('parameter_name'));assert key in ('SourcePigment','SourceCoverage');n.set_editor_property('texture',pigment if key=='SourcePigment' else coverage)
  if isinstance(n,u.MaterialExpressionScalarParameter):
   if str(n.get_editor_property('parameter_name'))=='SourceFacingSoftness':n.set_editor_property('default_value',slot['soft'])
   if str(n.get_editor_property('parameter_name'))=='SourceShadowCoverage':n.set_editor_property('default_value',1.)
 # This source variant mixes a small geometry-normal diffuse lobe with the
 # calibrated upward transmission response. Preserve its weight explicitly.
 # This native single-normal approximation still needs visual parity review.
 for n in list(M.get_material_expressions(leaf)):
  if str(n.get_editor_property('desc'))=='PineSourceMix':M.delete_material_expression(leaf,n)
 g=Graph(leaf,'PineSourceMix')
 pigment_node=next(n for n in M.get_material_expressions(leaf) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourcePigment')
 normal=g.node(u.MaterialExpressionVertexNormalWS);side=g.node(u.MaterialExpressionTwoSidedSign)
 weight=g.scalar(slot['diffuse_weight'])
 response=g.custom(['C','N','Side','W'],'float3 n=float3(0,0,1)*(1-W)+normalize(N)*Side*W; LightNormal=normalize(n);return C*length(n);',outputs=[('LightNormal',u.CustomMaterialOutputType.CMOT_FLOAT3)])
 for node,pin,out in [(pigment_node,'C','RGB'),(normal,'N',''),(side,'Side',''),(weight,'W','')]:g.wire(node,response,pin,out)
 g.output(response,u.MaterialProperty.MP_BASE_COLOR);g.output(response,u.MaterialProperty.MP_NORMAL,'LightNormal')
 assert not M.recompile_material(leaf);E.save_loaded_asset(leaf,False)
 if (R/'Art/flora_pine_match_settings.json').exists():
  from flora_pine_match_materials import apply
  report['pine_match_settings']=apply(leaf)
 barkpath=P+'/Assets/M_SourceBark_pine_f002';barkmat=u.load_asset(barkpath) or E.duplicate_asset('/Game/GrandTour/ArtTests/FloraGroup/Assets/M_SourceBark_pine',barkpath)
 for n in M.get_material_expressions(barkmat):
  if isinstance(n,u.MaterialExpressionTextureSampleParameter2D):assert str(n.get_editor_property('parameter_name'))=='SourceBarkColour';n.set_editor_property('texture',bark)
 assert not M.recompile_material(barkmat);E.save_loaded_asset(barkmat,False)
 task=props(u.AssetImportTask(),filename=str(O/'meshes/SM_Exact_pine_f002.fbx'),destination_path=P+'/Assets',destination_name='SM_Exact_pine_f002',automated=True,replace_existing=True,save=True)
 opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE);task.options=opt;fm.T.import_asset_tasks([task])
 mesh=u.load_asset(P+'/Assets/SM_Exact_pine_f002');assert mesh
 for i,s in enumerate(mesh.static_materials):
  name=str(s.get_editor_property('imported_material_slot_name'));assert name.startswith(('Wood_material','Leaf_0'))
  mesh.set_material(i,barkmat if name.startswith('Wood_material') else leaf)
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);build=sm.get_lod_build_settings(mesh,0)
 props(build,recompute_normals=False,recompute_tangents=True,use_full_precision_u_vs=True,generate_lightmap_u_vs=False);sm.set_lod_build_settings(mesh,0,build)
 opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False
 opts.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in [(1.,1.),(.65,.22),(.35,.06)]]
 assert sm.set_lods(mesh,opts)==3;E.save_loaded_asset(mesh,False)
 bgpath=P+'/Assets/M_SourceBackdrop';bg=u.load_asset(bgpath) or fm.T.create_asset('M_SourceBackdrop',P+'/Assets',u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(bg);props(bg,two_sided=True,shading_model=u.MaterialShadingModel.MSM_UNLIT)
 g=Graph(bg);g.output(g.vector((.58*.8,.74*.8,.8)),u.MaterialProperty.MP_EMISSIVE_COLOR);assert not M.recompile_material(bg);E.save_loaded_asset(bg,False)
 report['source_leaf']=slot
 return mesh
def components():
 return [c for a in A.get_all_level_actors() for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.get_instance_count() and c.static_mesh.get_name()=='SM_Exact_pine']
def run():
 global world,pc,car,camera
 protected()
 assert L.load_level(D+'/L_FloraTrail')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for s in json.loads((R/'Art/flora_trail_settings.json').read_text())['console']:cmd(s)
 yield 8;yield from await_bark_textures();report['baseline_assets']=audit_baseline(world)
 if stage=='install':
  cmd('Interchange.FeatureFlags.Import.FBX 0')
  data=json.loads((O/'export-report.json').read_text());assert data['ok'] and data['source_unchanged']
  mesh=import_tree(data)
  assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
  assert L.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  changed=[]
  for c in components():
   old=c.static_mesh;ratio=old.get_bounds().box_extent.z/mesh.get_bounds().box_extent.z
   transforms=[c.get_instance_transform(i,False) for i in range(c.get_instance_count())]
   assert c.set_static_mesh(mesh)
   for j,s in enumerate(mesh.static_materials):c.set_material(j,s.material_interface)
   for i,t in enumerate(transforms):
    t.scale3d=t.scale3d*ratio;c.update_instance_transform(i,t,False,i==len(transforms)-1,True)
   changed.append({'instances':len(transforms),'height_scale':ratio})
  assert sum(x['instances'] for x in changed)==193,changed
  assert L.save_current_level();report['replaced']=changed
 else:
  assert L.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 # Reload saved trial before evidence or audit; never certify only in-memory changes.
 assert L.load_level('/Engine/Maps/Entry');assert L.load_level(LEVEL)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 mesh=u.load_asset(P+'/Assets/SM_Exact_pine_f002');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 bark=u.load_asset(P+'/Assets/T_SourceBark_pine_f002');deadline=time.monotonic()+180
 while bark.blueprint_get_size_x()!=4096:
  assert time.monotonic()<deadline,'4K bark still loading';yield .5
 assert sm.get_lod_count(mesh)==3 and sm.get_num_uv_channels(mesh,0)==2
 report['new_tree']={'lods':sm.get_lod_count(mesh),'triangles':mesh.get_static_mesh_description(0).get_triangle_count(),'bark_dimensions':[bark.blueprint_get_size_x(),bark.blueprint_get_size_y()]}
 if (R/'Art/flora_pine_match_settings.json').exists():
  leaf=u.load_asset(P+'/Assets/M_Source34_pine_f002')
  coverage=next(n.get_editor_property('texture') for n in M.get_material_expressions(leaf) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourceCoverage')
  assert coverage.get_path_name().startswith(P+'/SourceMatch/T_SourceMask4K') and not coverage.get_editor_property('srgb')
  deadline=time.monotonic()+180
  while coverage.blueprint_get_size_x()!=4096:
   assert time.monotonic()<deadline,'4K coverage still loading';yield .5
  assert any('saturate(1.5*A*' in str(n.get_editor_property('code')) for n in M.get_material_expressions(leaf) if isinstance(n,u.MaterialExpressionCustom))
  report['new_tree']['coverage_dimensions']=[coverage.blueprint_get_size_x(),coverage.blueprint_get_size_y()]
 rows=[]
 for a in A.get_all_level_actors():
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.static_mesh or not c.get_instance_count() or c.static_mesh!=mesh:continue
   assert all(c.get_material(i)==s.material_interface for i,s in enumerate(mesh.static_materials))
   rows.append({'instances':c.get_instance_count(),'shadow':bool(c.get_editor_property('cast_shadow'))})
 assert sum(r['instances'] for r in rows)==193 and len(rows)==2
 report['saved_pine_components']=rows
 report['saved_packages']={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/PineTrial').rglob('*') if p.suffix in ('.umap','.uasset')}
 report['lighting']=configure(world,settings());yield 8
 if stage=='verify':
  u.GTPlayWindowLibrary.request_play_in_new_window(*cfg['requested_size']);yield 12
  world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
  for c in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.ScreenPercentage 100','r.DynamicRes.OperationMode 0','r.VSync 0','t.MaxFPS 0','r.Streaming.FullyLoadUsedTextures 1']:cmd(c)
  camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector()),'PineTrialReview')
  camera.camera_component.set_field_of_view(cfg['fov']);camera.camera_component.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);cmd('ShowHUD');yield 12
  for view in cfg['views']:
   if view['name'] not in ('road','canopy','bank','valley'):continue
   pos=u.Vector(*view['position']);camera.set_actor_location(pos,False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,u.Vector(*view['target'])),False)
   yield from shot('pine_'+view['name'])
  # A short continuous camera move, with frame samples for temporal review.
  view=next(v for v in cfg['views'] if v['name']=='road');pos=u.Vector(*view['position']);target=u.Vector(*view['target'])
  for i in range(48):
   p=pos+u.Vector(i*4,0,0);camera.set_actor_location(p,False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(p,target),False)
   yield from frames(1)
   if i%4==0:yield from shot('motion_%02d'%i,0)
  report['motion_capture']='48-frame moving camera; 12 samples. Offscreen speed is not realtime performance.'
  # Additional source comparison: remote isolated tree, uniform source backdrop,
  # no atmosphere, same native sun/sky, scale and viewing rays as Blender.
  data=json.loads((SOURCE/'export-report.json').read_text());origin=u.Vector(100000,0,100000)
  isolate=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=origin),'PineSourceComparison')
  isolate.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE);assert isolate.static_mesh_component.set_static_mesh(mesh);isolate.static_mesh_component.set_forced_lod_model(1)
  bg=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=origin),'PineSourceBackdrop')
  bg.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE);assert bg.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'))
  bg.set_actor_scale3d(u.Vector(100,100,100));bg.static_mesh_component.set_material(0,u.load_asset(P+'/Assets/M_SourceBackdrop'));props(bg.static_mesh_component,cast_shadow=False)
  def convert(v):return origin+u.Vector(v[0]*100,-v[1]*100,v[2]*100)
  source=data['source_camera'];pos=convert(source['position']);target=convert(source['target'])
  size=report['images'][0]['size'];fov=math.degrees(2*math.atan(math.tan(math.radians(source['horizontal_fov']/2))*size[0]/size[1]))
  camera.camera_component.set_editor_property('aspect_ratio',size[0]/size[1]);camera.camera_component.set_field_of_view(fov);camera.set_actor_location(pos,False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
  cmd('ShowFlag.Fog 0');yield from shot('pine_isolated');cmd('ShowFlag.Fog 1')
  report['isolated_comparison']={'source_camera':source,'unreal_horizontal_fov':fov,'lod':0,'fog':False,'sun_sky':'unchanged','note':'Match vertical field of view; native engine shadow and shader differences remain under review.'}
  isolate.destroy_actor();bg.destroy_actor()
  pc.set_view_target_with_blend(car,0);u.EditorLevelLibrary.editor_end_play();yield 4
 for path,digest in report['saved_packages'].items():assert hashlib.sha256((R/path).read_bytes()).hexdigest()==digest,path
 report.update(ok=True,protected_unchanged=True);protected();save()
 assert L.load_level('/Engine/Maps/Entry');world=pc=car=camera=None;yield 3
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
 if state['busy']:return
 state['busy']=True;state['frame']+=1
 try:
  if time.monotonic()>=state['due']:state['due']=time.monotonic()+next(steps)
 except StopIteration:steps=None;u.unregister_slate_post_tick_callback(handle);close()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);close()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
