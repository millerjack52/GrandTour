"""Isolate leaf transmission, interior AO and grading in a saved FloraTrail copy."""
import unreal as u,json,sys,time,traceback,math,os,hashlib,ast,re
from pathlib import Path
R=Path('C:/GrandTour');sys.path[:0]=[str(R/'Art/Unreal'),str(R/'Art')]
from benmore_river_life_materials import Graph,props
from flora_transmission_baseline import verify
CFG=json.loads((R/'Art/flora_transmission_settings.json').read_text())
BASE='/Game/GrandTour/ArtTests/FloraTrail/Woodland/CrownForm/v3/L_FloraTrail_CrownForm'
D='/Game/GrandTour/ArtTests/FloraTrail/Woodland/TransmissionStudy/'+CFG['revision'];MAP=D+'/L_FloraTrail_Transmission'
O=R/'Art/Export/FloraTransmissionStudy'/CFG['revision'];O.mkdir(parents=True,exist_ok=True)
stage=os.environ.get('GT_TRANSMISSION_STAGE','compare')
L=u.get_editor_subsystem(u.LevelEditorSubsystem);A=u.get_editor_subsystem(u.EditorActorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
world=pc=car=camera=grade_mid=None;state={'busy':False,'due':0,'frame':0}
report={'ok':False,'stage':stage,'images':[],'profiles':CFG['profiles'],'grade':CFG['grade'],'performance':'Not tested; visual study only.'}
source=R/'Art/Unreal/trial_flora_mud.py';tree=ast.parse(source.read_text())
tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('cmd','frames','shot','look','centre')]
exec(compile(tree,str(source),'exec'),globals())

def save():(O/(stage+'-report.json')).write_text(json.dumps(report,indent=2))
def actors():return u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
def slots():
 return [(a,c,i,m) for a in actors() for c in a.get_components_by_class(u.StaticMeshComponent) if c.static_mesh for i,m in enumerate(c.get_materials()) if m and ('/CrownForm/v3/M_Crown_' in m.get_path_name() or D+'/M_Transmission_' in m.get_path_name())]
def hashes():
 root=R/'Content'/D.removeprefix('/Game/')
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def snapshot():
 rows=[]
 for a in actors():
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.static_mesh:continue
   ts=[c.get_instance_transform(i,True) for i in range(c.get_instance_count())] if isinstance(c,u.InstancedStaticMeshComponent) else [c.get_world_transform()]
   positions=[[round(v,5) for v in (*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple())] for t in ts]
   mats=[]
   for m in c.get_materials():
    p=m.get_path_name() if m else None
    mats.append('<StudyCanopy>' if p and ('/CrownForm/v3/M_Crown_' in p or D+'/M_Transmission_' in p) else p)
   rows.append({'actor':a.get_actor_label(),'component':c.get_name(),'mesh':c.static_mesh.get_path_name(),'count':len(ts),'transforms':hashlib.sha256(json.dumps(positions).encode()).hexdigest(),'materials':mats,'collision':str(c.get_collision_enabled())})
 text=json.dumps(sorted(rows,key=lambda r:(r['actor'],r['component'])))
 for path in (BASE,MAP):text=text.replace(path+'.'+path.rsplit('/',1)[-1],'<World>').replace(path,'<Map>')
 return json.loads(text)
def lighting():
 def stable(v):
  if hasattr(v,'to_tuple'):return [round(float(x),6) for x in v.to_tuple()]
  if isinstance(v,(int,float,bool,str)):return v
  return re.sub(r'0x[0-9a-fA-F]+','<address>',str(v))
 rows=[]
 for a in actors():
  if isinstance(a,(u.DirectionalLight,u.SkyLight)):
   c=a.light_component;rows.append([a.get_actor_label(),stable(a.get_actor_rotation()),c.intensity,stable(c.light_color)])
  if isinstance(a,u.ExponentialHeightFog):
   c=a.component;rows.append([a.get_actor_label()]+[stable(c.get_editor_property(k)) for k in ('fog_density','fog_height_falloff','start_distance','fog_max_opacity','fog_inscattering_luminance','enable_volumetric_fog')])
  if isinstance(a,u.PostProcessVolume) and a.get_actor_label()!='TransmissionStudy_Grade':
   rows.append([a.get_actor_label()]+[stable(a.settings.get_editor_property(k)) for k in ('auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','color_gain','color_gamma','color_saturation')])
 return sorted(rows,key=lambda row:row[0])
def textures(m):
 return {n.texture.get_path_name():n.texture for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSample) and n.texture}
def clone(src):
 path=D+'/M_Transmission_'+src.get_name();m=u.load_asset(path)
 if not m:
  m=E.duplicate_asset(src.get_path_name().split('.')[0],path);assert m
  old=M.get_material_property_input_node(m,u.MaterialProperty.MP_SUBSURFACE_COLOR);port=str(M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_SUBSURFACE_COLOR));assert old
  g=Graph(m,'TransmissionStudy');p=g.node(u.MaterialExpressionScalarParameter,parameter_name='LeafTransmission',default_value=.12)
  node=g.custom(['Original','Strength'],'return Original*(Strength/.12);');g.wire(old,node,'Original',port);g.wire(p,node,'Strength');g.output(node,u.MaterialProperty.MP_SUBSURFACE_COLOR)
  assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
 assert textures(m)==textures(src)
 for prop in (u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_SPECULAR,u.MaterialProperty.MP_OPACITY_MASK,u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
  a=M.get_material_property_input_node(src,prop);b=M.get_material_property_input_node(m,prop)
  assert (a.get_name() if a else None)==(b.get_name() if b else None),prop
 return m
def grade_actor():
 return next(a for a in actors() if a.get_actor_label()=='TransmissionStudy_Grade')
def set_grade(a,amount):
 # The original replacement tonemapper bypasses UE's colour-grading LUT.
 # Keep its exact sRGB encoding and grade in the same pass, before encoding.
 a.blend_weight=amount
 if grade_mid:grade_mid.set_scalar_parameter_value('GradeStrength',amount)

def display_actor():
 return next(a for a in actors() if isinstance(a,u.PostProcessVolume) and a.get_actor_label()=='FloraTrail_Display')

def bind_display(material):
 a=display_actor();s=a.settings;items=list(s.weighted_blendables.array)
 assert len(items)==1,'Unexpected display stack'
 items[0].object=material;s.weighted_blendables=props(u.WeightedBlendables(),array=items);a.settings=s

def display_shader():
 path=D+'/M_TransmissionDisplay';m=u.load_asset(path)
 if m and E.get_metadata_tag(m,'TransmissionDisplayVersion')=='2':return m
 src=list(display_actor().settings.weighted_blendables.array)[0].object
 assert isinstance(src,u.Material) and src.blendable_location==u.BlendableLocation.BL_REPLACING_TONEMAPPER
 m=m or E.duplicate_asset(src.get_path_name().split('.')[0],path);assert m
 node=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'View.OneOverPreExposure' in str(n.get_editor_property('code')))
 report['original_display_shader']=str(node.get_editor_property('code'))
 assert 'return lerp(12.92*x' in report['original_display_shader'],'Unknown source display response'
 def vec(k):return 'float3('+','.join(str(v) for v in CFG['grade'][k][:3])+')'
 code='''float3 x=max(0.,C*View.OneOverPreExposure);
float lum=dot(x,float3(.2126,.7152,.0722));
float shadow=1-smoothstep(.01,.22,lum);
float highlight=smoothstep(.32,.85,lum);
float3 shaded=pow(max(x,0.),1./SHADOW_GAMMA)*SHADOW_GAIN;
float3 graded=lerp(x,shaded,shadow)*lerp(float3(1,1,1),HIGHLIGHT_GAIN,highlight);
x=lerp(x,graded,saturate(Strength));
return lerp(12.92*x,1.055*pow(x,1./2.4)-.055,step(.0031308,x));'''
 for key,cfg in [('SHADOW_GAMMA','color_gamma_shadows'),('SHADOW_GAIN','color_gain_shadows'),('HIGHLIGHT_GAIN','color_gain_highlights')]:code=code.replace(key,vec(cfg))
 # Assemble disconnected, then replace the output, so editor auto-compilation
 # cannot traverse a partly connected Strength input during construction.
 g=Graph(m,'TransmissionDisplay');p=g.node(u.MaterialExpressionScalarParameter,parameter_name='GradeStrength',default_value=0.)
 graded=g.custom(['C','Strength'],code)
 scene=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionSceneTexture))
 g.wire(scene,graded,'C','Color');g.wire(p,graded,'Strength');g.output(graded,u.MaterialProperty.MP_EMISSIVE_COLOR)
 M.delete_material_expression(m,node)
 assert not M.recompile_material(m);E.set_metadata_tag(m,'TransmissionDisplayVersion','2');assert E.save_loaded_asset(m,False)
 return m

def save_grade_default(amount):
 m=u.load_asset(D+'/M_TransmissionDisplay');assert m
 n=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='GradeStrength')
 n.set_editor_property('default_value',amount);assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
def defaults(m,profile):
 values={'LeafTransmission':profile['transmission'],'CrownOcclusion':profile['occlusion']}
 for n in M.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name')) in values:n.set_editor_property('default_value',values[str(n.get_editor_property('parameter_name'))])
 assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
def run():
 global world,pc,car,camera,grade_mid
 report['protected_packages']=verify();assert L.load_level(BASE);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 original=snapshot();light=lighting();report['source_map']=BASE
 for c in json.loads((R/'Art/flora_trail_settings.json').read_text())['console']:cmd(c)
 if not E.does_asset_exist(MAP):
  assert stage=='compare','Build comparison first'
  source_slots=slots();assert len(source_slots)==4,len(source_slots)
  for a,c,i,m in source_slots:c.set_material(i,clone(m))
  bind_display(display_shader())
  pp=A.spawn_actor_from_class(u.PostProcessVolume,u.Vector());pp.set_actor_label('TransmissionStudy_Grade');props(pp,unbound=True,priority=2000.);set_grade(pp,0.)
  assert u.EditorLoadingAndSavingUtils.save_map(world,MAP)
 assert L.load_level('/Engine/Maps/Entry');assert L.load_level(MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 report['lighting_before']=light;report['lighting_after']=lighting();save()
 assert snapshot()==original,'Geometry or non-canopy materials changed';assert lighting()==light,'Baseline lighting changed'
 if stage=='save':
  selected=CFG['profiles'][CFG['selected']]
  for m in set(m for a,c,i,m in slots()):defaults(m,selected)
  save_grade_default(selected['grade'])
  set_grade(grade_actor(),selected['grade']);assert L.save_current_level()
  assert L.load_level('/Engine/Maps/Entry');assert L.load_level(MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 report.update(saved_map=MAP,geometry_noncanopy_materials_preserved=True,lighting=lighting(),saved_hashes=hashes())
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0];visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
 report['water']=surface.simulated_water.get_editor_property('surface_material_path');assert report['water']=='/Game/GrandTour/ArtTests/FloraTrail/MudTrial/M_WaterFlat.M_WaterFlat'
 report['mud']=visual.material.get_path_name();assert '/BrownMud/' in report['mud']
 tex={}
 for a in actors():
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if c.static_mesh and c.static_mesh.get_name().startswith('SM_Exact_'):
    for m in c.get_materials():
     if isinstance(m,u.Material):tex.update(textures(m))
 cmd('r.Streaming.FullyLoadUsedTextures 1');yield 15
 report['source_textures']={p:[t.blueprint_get_size_x(),t.blueprint_get_size_y()] for p,t in tex.items()}
 assert all(v[0]>=4096 for p,v in report['source_textures'].items() if 'Bark' in p or 'Mask4K' in p)
 save();u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 15
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True);car.set_actor_hidden_in_game(True)
 for c in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.ScreenPercentage 100','r.DynamicRes.OperationMode 0','r.VSync 0','t.MaxFPS 0','r.Streaming.FullyLoadUsedTextures 1']:cmd(c)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'TransmissionReviewCamera');camera.camera_component.set_field_of_view(65);camera.camera_component.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);cmd('ShowHUD');yield 12
 mids=[c.create_dynamic_material_instance(i,m) for a,c,i,m in slots()];assert len(mids)==4
 pp=grade_actor();surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 display=list(display_actor().settings.weighted_blendables.array)[0].object
 assert display.get_path_name().startswith(D+'/M_TransmissionDisplay.')
 grade_mid=u.MaterialLibrary.create_dynamic_material_instance(world,display);bind_display(grade_mid)
 report['saved_display_grade']=grade_mid.get_scalar_parameter_value('GradeStrength')
 report['display_shader']=str(next(n for n in M.get_material_expressions(display) if isinstance(n,u.MaterialExpressionCustom)).get_editor_property('code'))
 if stage!='compare':
  selected=CFG['profiles'][CFG['selected']]
  assert all(abs(m.get_scalar_parameter_value('LeafTransmission')-selected['transmission'])<1e-6 and abs(m.get_scalar_parameter_value('CrownOcclusion')-selected['occlusion'])<1e-6 for m in mids)
  assert abs(pp.blend_weight-selected['grade'])<1e-6
  assert abs(report['saved_display_grade']-selected['grade'])<1e-6
 report['saved_defaults']=[{'transmission':m.get_scalar_parameter_value('LeafTransmission'),'occlusion':m.get_scalar_parameter_value('CrownOcclusion')} for m in mids]
 report['saved_grade_weight']=pp.blend_weight
 pc.set_tickable_when_paused(True);pc.set_editor_property('should_perform_full_tick_when_paused',True);camera.set_tickable_when_paused(True);u.GameplayStatics.set_game_paused(world,True)
 def height(x,y):return surface.contact_height_cm(u.Vector2D(x,y),False)
 x=-1850;y=centre(x)
 views=[('road',[x,y,height(x,y)+150],[-500,centre(-500),height(-500,centre(-500))+60]),('bank',[150,centre(150)-200,160],[650,centre(650)-500,40]),('canopy',[-1200,-900,130],[1500,1300,300]),('crowns',[-1200,-900,130],[500,1300,1550]),('valley',[-3600,-2700,2300],[500,500,400])]
 report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views]
 cases=CFG['profiles'] if stage=='compare' else {CFG['selected']:CFG['profiles'][CFG['selected']]}
 for name,profile in cases.items():
  if stage=='compare':
   for m in mids:m.set_scalar_parameter_value('LeafTransmission',profile['transmission']);m.set_scalar_parameter_value('CrownOcclusion',profile['occlusion'])
   set_grade(pp,profile['grade'])
  report.setdefault('profile_readback',{})[name]={'transmission':mids[0].get_scalar_parameter_value('LeafTransmission'),'occlusion':mids[0].get_scalar_parameter_value('CrownOcclusion'),'grade':grade_mid.get_scalar_parameter_value('GradeStrength')}
  for view,p,t in views:look(p,t);yield from shot(stage+'_'+name+'_'+view)
  if stage!='compare' or name in ('baseline','combined','gentle_grade'):
   for i in range(12):
    look([-1200+i*12,-900,130],[500,1300,1550]);yield from shot(stage+'_'+name+'_move_%02d'%i,8)
 report['surface_report']=surface.get_surface_report()
 u.GameplayStatics.set_game_paused(world,False);pc.set_view_target_with_blend(car,0);u.EditorLevelLibrary.editor_end_play();yield 4
 assert hashes()==report['saved_hashes'];verify();report.update(ok=True,protected_packages_unchanged=True,saved_packages_unchanged=True);save()
 assert L.load_level('/Engine/Maps/Entry');world=pc=car=camera=None;yield 3
def close():
 for key,value in list(globals().items()):
  if not key.startswith('__') and key not in ('u','time'):globals()[key]=None
 value=None
 import gc
 gc.collect();u.SystemLibrary.collect_garbage();globals()['quit_at']=time.monotonic()+3
 def shutdown(dt):
  if time.monotonic()>quit_at:u.unregister_slate_post_tick_callback(quit_handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
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
