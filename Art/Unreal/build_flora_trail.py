"""Build an isolated playable Flora Paint section, preserving proven mud/water physics."""
import unreal as u,json,sys,time,traceback,hashlib,gc,math,shutil
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail';D='/Game/GrandTour/ArtTests/FloraTrail';LEVEL=D+'/L_FloraTrail'
sys.path[:0]=[str(R/'Art/Unreal'),str(R/'Art/tools')]
from benmore_river_life_materials import props,Graph
from make_mud_road import centre
from flora_trail_canopy_materials import install_component
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
cfg=json.loads((R/'Art/flora_trail_settings.json').read_text());O.mkdir(parents=True,exist_ok=True)
report={'ok':False,'level':LEVEL,'components':[],'performance_verified':False,'materials':{}}
materials={};collections={}
def save():(O/'build-report.json').write_text(json.dumps(report,indent=2))
def local(source):
 if not source:return None
 if source.get_path_name().startswith('/Engine/'):return source
 if not isinstance(source,(u.Material,u.MaterialInstanceConstant)):return source
 key=source.get_path_name()
 if key in materials:return materials[key]
 path=D+'/Materials/'+source.get_name();m=u.load_asset(path) or E.duplicate_asset(key.split('.')[0],path);assert m,key
 materials[key]=m;report['materials'][key]=m.get_path_name()
 if isinstance(m,u.MaterialInstanceConstant):M.set_material_instance_parent(m,local(source.get_editor_property('parent')))
 elif isinstance(m,u.Material):
  for n in M.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionCollectionParameter):
    c=n.get_editor_property('collection')
    if c and (c.get_name()=='MPC_SourceLighting' or c.get_path_name().startswith(D)):
     k=c.get_path_name()
     if k not in collections:
      p=D+'/Controls/'+c.get_name();collections[k]=u.load_asset(p) or E.duplicate_asset(k.split('.')[0],p)
     n.set_editor_property('collection',collections[k])
   if isinstance(n,u.MaterialExpressionScalarParameter):
    name=str(n.get_editor_property('parameter_name'))
    if name in cfg['material_scalars']:n.set_editor_property('default_value',cfg['material_scalars'][name])
  from flora_trail_surface_palette import apply
  apply(m,cfg)
  assert not M.recompile_material(m),key
 E.save_loaded_asset(m,False);return m

def run():
 global world
 # Fingerprint approved inputs, including source shader and bark assets.
 files=[]
 for folder in ['FloraGroup','FloraDrive','LidarStudy','FloraPath']:
  base=R/'Content/GrandTour/ArtTests'/folder
  files+=list(base.glob('*.umap'))
  if folder in ['FloraGroup','FloraDrive']:files+=list(base.rglob('*.uasset'))
 protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
 (O/'protected-before.json').write_text(json.dumps(protected,indent=2))
 if E.does_asset_exist(LEVEL):
  backup=R/'Saved/FloraTrailBackups'/str(time.time_ns());backup.mkdir(parents=True)
  shutil.copy2(R/'Content/GrandTour/ArtTests/FloraTrail/L_FloraTrail.umap',backup/'L_FloraTrail.umap')
  assert E.delete_asset(LEVEL)
 assert L.load_level('/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive')
 assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
 assert L.load_level(LEVEL)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for s in cfg['console']:u.SystemLibrary.execute_console_command(world,s)
 models={k:u.load_asset('/Game/GrandTour/ArtTests/FloraGroup/Assets/SM_Exact_'+k) for k in ['tree','pine','fern','shrub','grass','drygrass']};assert all(models.values())
 # Local LODs preserve the approved study meshes and source normals at LOD0.
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 for key,source in list(models.items()):
  path=D+'/Meshes/'+source.get_name();mesh=u.load_asset(path) or E.duplicate_asset(source.get_path_name().split('.')[0],path)
  if E.get_metadata_tag(mesh,'FloraTrailLODs')!='1':
   opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False
   thresholds=[(1.,1.),(.65,.22),(.35,.06)] if key in ['tree','pine'] else [(1.,1.),(.65,.06),(.35,.02)]
   opts.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in thresholds];assert sm.set_lods(mesh,opts)==3
   E.set_metadata_tag(mesh,'FloraTrailLODs','1');E.save_loaded_asset(mesh,False)
  models[key]=mesh
 owner=A.spawn_actor_from_class(u.Actor,u.Vector());owner.set_actor_label('FloraTrail_SourceFoliage')
 buckets={};removed=0
 for a in list(A.get_all_level_actors()):
  if a.get_actor_label()=='FloraDrive_PaintedSky':a.tags=[]
  if isinstance(a,(u.DirectionalLight,u.SkyLight,u.ExponentialHeightFog,u.PostProcessVolume,u.SkyAtmosphere)):A.destroy_actor(a);continue
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if isinstance(c,u.LandscapeNaniteComponent):continue
   mesh=c.static_mesh
   if not mesh:continue
   name=mesh.get_name();key=None
   if 'Tree_D' in name:key='pine'
   elif 'Tree_B' in name:key='tree'
   elif 'Ferns' in name:key='fern'
   elif 'Shrubbery' in name or 'Small_Plants' in name:key='shrub'
   elif 'Dry_Grass' in name:key='drygrass'
   elif 'Grass' in name or 'Miscanthus' in name:key='grass'
   if isinstance(c,u.InstancedStaticMeshComponent) and (key or 'Flower' in name):
    count=c.get_instance_count()
    if key:
     old=mesh.get_bounds();new=models[key].get_bounds()
     ratio=old.box_extent.z/max(new.box_extent.z,.01)
     oldmin=old.origin.z-old.box_extent.z;newmin=new.origin.z-new.box_extent.z
     far=c.get_editor_property('forced_lod_model')>0
     bucket=buckets.setdefault((key,far),[])
     for i in range(count):
      t=c.get_instance_transform(i,True);scale=t.scale3d;pos=t.translation
      pos.z+=oldmin*scale.z-newmin*scale.z*ratio
      t.translation=pos;t.scale3d=u.Vector(scale.x*ratio,scale.y*ratio,scale.z*ratio);bucket.append(t)
    else:removed+=count
    c.clear_instances();c.set_visibility(False);continue
   if c.get_editor_property('hidden_in_game'):continue
   for i,m in enumerate(c.get_materials()):
    if m:c.set_material(i,local(m))
 # Merge palette families into a few instanced components, preserving clustered transforms.
 for (key,far),transforms in buckets.items():
  mesh=models[key];shadow=not far and key in ['tree','pine','fern','shrub']
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,transforms,'FloraTrail','NoCollision',shadow)
  props(c,cast_contact_shadow=True,visible_in_ray_tracing=False,affect_distance_field_lighting=False,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  c.set_cull_distances(14000,19000) if key in ['tree','pine'] else c.set_cull_distances(4500,8500)
  for i,m in enumerate(c.get_materials()):c.set_material(i,local(m))
  install_component(c,json.loads((R/'Art/flora_trail_canopy_settings.json').read_text()))
  report['components'].append({'family':key,'far':far,'instances':len(transforms),'mesh':mesh.get_path_name(),'casts_shadows':shadow})
 report['removed_flower_instances']=removed
 visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
 for field in ['material','track_material','water_simulation_material','sediment_simulation_material']:visual.set_editor_property(field,local(visual.get_editor_property(field)))
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 water=surface.simulated_water;water.set_editor_property('surface_material_path',local(u.load_asset(water.get_editor_property('surface_material_path'))).get_path_name().split('.')[0])
 from flora_lidar_mud import local_visual_window
 for field in ['material','track_material']:
  m=visual.get_editor_property(field);report['visual_window']=local_visual_window(m,visual);M.recompile_material(m);E.save_loaded_asset(m,False)
 ref=json.loads((R/'Art/Export/FloraDrive/LidarMud/reference.json').read_text())
 report['mud_settings']={k:surface.get_editor_property(k) for k in ref['settings']};assert report['mud_settings']==ref['settings']
 route=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRoute));props(route,title='FLORA TRAIL / source foliage + live mud + water',checkpoint_labels='1 Forest entry   2 Mud trail   3 Water crossing')
 def spawn(cls,name,pos=(0,0,0),rot=None):
  a=A.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());a.set_actor_label('FloraTrail_'+name);a.tags=[u.Name('GTWeatherUnmanaged')];return a
 sun=spawn(u.DirectionalLight,'Sun',rot=u.MathLibrary.find_look_at_rotation(u.Vector(),u.Vector(*cfg['sun_ray'])))
 sun.light_component.set_mobility(u.ComponentMobility.MOVABLE);sun.light_component.set_intensity(cfg['sun']*.96457146);sun.light_component.set_light_color(u.LinearColor(*cfg['sun_colour'],1))
 props(sun.light_component,light_source_angle=2.,volumetric_scattering_intensity=.25,contact_shadow_length=60.,contact_shadow_length_in_ws=True,contact_shadow_non_casting_intensity=.65)
 sky=spawn(u.SkyLight,'Sky');sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
 props(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=u.load_asset('/Game/GrandTour/ArtTests/FloraParity/AssetMatch/T_ParityWhite'),real_time_capture=False,lower_hemisphere_is_black=False,cast_shadows=False)
 sky.light_component.set_intensity(cfg['sky']*.89832447);sky.light_component.set_light_color(u.LinearColor(*cfg['sky_colour'],1));sky.light_component.recapture_sky()
 for c in collections.values():
  if c.get_name()=='MPC_SourceLighting':
   ps=c.get_editor_property('vector_parameters')
   for p in ps:
    name=str(p.get_editor_property('parameter_name'))
    if name=='SunDirection':p.set_editor_property('default_value',u.LinearColor(*[-v for v in cfg['sun_ray']],0))
    if name=='SkyRadiance':p.set_editor_property('default_value',u.LinearColor(*[v*cfg['sky']*.92909 for v in cfg['sky_colour']],0))
   c.set_editor_property('vector_parameters',ps)
  E.save_loaded_asset(c,False)
 fog=spawn(u.ExponentialHeightFog,'Haze',(0,0,150));props(fog.component,fog_density=cfg['fog'],fog_inscattering_luminance=u.LinearColor(*cfg['fog_colour'],1),fog_height_falloff=.08,start_distance=200.,fog_max_opacity=.94,enable_volumetric_fog=True,volumetric_fog_scattering_distribution=.5,volumetric_fog_albedo=u.Color(185,207,235,255),volumetric_fog_distance=9000.)
 from flora_trail_atmosphere import apply as apply_atmosphere
 apply_atmosphere(fog.component,sun.light_component,json.loads((R/'Art/flora_trail_atmosphere_settings.json').read_text()))
 pp=spawn(u.PostProcessVolume,'Display');props(pp,unbound=True,priority=1000.,blend_weight=1.)
 ps=pp.settings
 for k,v in dict(auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,auto_exposure_apply_physical_camera_exposure=False,auto_exposure_bias=0.,bloom_intensity=.02,vignette_intensity=0.,film_grain_intensity=0.,lens_flare_intensity=0.,motion_blur_amount=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.,tone_curve_amount=0.,expand_gamut=0.,blue_correction=0.,dynamic_global_illumination_method=u.DynamicGlobalIlluminationMethod.NONE).items():props(ps,**{'override_'+k:True,k:v})
 pp.settings=ps
 from flora_group_display import viewport_material
 ps=pp.settings;ps.weighted_blendables=props(u.WeightedBlendables(),array=[props(u.WeightedBlendable(),weight=1.,object=local(viewport_material()))]);pp.settings=ps
 u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(u.Vector(-2850,-150,230),u.Rotator(pitch=4,yaw=8))
 assert L.save_current_level();yield 5
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items()),'Approved input changed'
 report.update(ok=True,settings=cfg,source_assets_unchanged=True,instances=sum(x['instances'] for x in report['components']),route_length_m=52.3)
 report['package_hashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail').rglob('*') if p.suffix in ['.uasset','.umap']};save()
 assert L.load_level('/Engine/Maps/Entry');yield 3
 world=None;materials.clear();collections.clear();gc.collect();u.SystemLibrary.collect_garbage();yield 2
def close_safely():
 global world
 world=None;materials.clear();collections.clear()
 L.load_level('/Engine/Maps/Entry');gc.collect();u.SystemLibrary.collect_garbage()
 end=time.monotonic()+3
 def quit(dt):
  if time.monotonic()>end:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 handle=u.register_slate_post_tick_callback(quit)
steps=run();state={'busy':False,'deadline':0}
def tick(dt):
 global steps
 if state['busy'] or time.monotonic()<state['deadline']:return
 state['busy']=True
 try:state['deadline']=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;u.unregister_slate_post_tick_callback(state['handle']);close_safely()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(state['handle']);steps=None;close_safely()
 finally:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);state['handle']=u.register_slate_post_tick_callback(tick)
