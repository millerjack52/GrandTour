"""Map-owned atmospheric daylight, weather-aware volume clouds and exposure."""
import unreal as u,sys,time,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreDaylight';DEST='/Game/GrandTour/Demo/BenmoreRoads/Daylight';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools();les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def finish(err=None):
 global phase
 phase='done';report['ok']=err is None
 if err:report['error']=err;u.log_error(err)
 (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def build_clouds():
 path=DEST+'/M_Benmore_VolumeClouds'
 m=u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset('/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud',path)
 # Always reconnect parameters from the clean engine graph, without editing engine assets.
 if eal.does_asset_exist(path):
  expressions=list(mel.get_material_expressions(m))
  already=any(isinstance(n,u.MaterialExpressionCollectionParameter) for n in expressions)
 else:already=False
 if not already:
  expressions=list(mel.get_material_expressions(m));changed={}
  for name,amount,mode in [('Cloud_GlobalCoverage',.48,'add'),('Cloud_GlobalDensity',1.5,'multiply')]:
   old=next(n for n in expressions if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))==name)
   targets=[]
   for node in expressions:
    names=mel.get_material_expression_input_names(node);inputs=mel.get_inputs_for_material_expression(m,node)
    for i,n in enumerate(inputs):
     if n==old:targets.append((node,names[i]))
   assert targets,name
   rain=props(mel.create_material_expression(m,u.MaterialExpressionCollectionParameter),collection=u.load_asset('/Game/GrandTour/Materials/MPC_Weather'),parameter_name='RainIntensity')
   scaled=props(mel.create_material_expression(m,u.MaterialExpressionMultiply),const_b=amount);assert mel.connect_material_expressions(rain,'',scaled,'A')
   if mode=='multiply':
    plus=props(mel.create_material_expression(m,u.MaterialExpressionAdd),const_b=1.);assert mel.connect_material_expressions(scaled,'',plus,'A');scaled=plus
   combined=mel.create_material_expression(m,u.MaterialExpressionAdd if mode=='add' else u.MaterialExpressionMultiply)
   assert mel.connect_material_expressions(old,'',combined,'A');assert mel.connect_material_expressions(scaled,'',combined,'B')
   for node,pin in targets:assert mel.connect_material_expressions(combined,'',node,pin)
   changed[name]=len(targets)
  assert not mel.recompile_material(m);eal.save_loaded_asset(m);report['cloud_weather_links']=changed
 # The base graph deliberately contains black placeholder textures. Preserve
 # the engine instance's cloud pattern, height profile and volume-noise maps.
 miPath=DEST+'/MI_Benmore_CloudWeather'
 mi=u.load_asset(miPath) if eal.does_asset_exist(miPath) else eal.duplicate_asset('/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst',miPath)
 mel.set_material_instance_parent(mi,m)
 for k,v in [('Cloud_GlobalCoverage',-.14),('Cloud_GlobalDensity',.008),('Layout_CloudGlobalScale',256.),('StormClouds',0.)]:
  mel.set_material_instance_scalar_parameter_value(mi,k,v)
  assert abs(mel.get_material_instance_scalar_parameter_value(mi,k)-v)<.0001,k
 mel.update_material_instance(mi);eal.save_loaded_asset(mi);return mi
def tick(dt):
 global phase,last
 try:
  if phase=='load':
   phase='building';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();eal.make_directory(DEST)
   backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeDaylight'
   if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
   cloudmat=build_clouds()
   for a in act.get_all_level_actors():
    if a.get_actor_label().startswith('Benmore_Daylight_'):act.destroy_actor(a)
   # A zero-opacity compatibility anchor prevents the shared look subsystem spawning a painted dome.
   path=DEST+'/M_Benmore_AtmosphereAnchor';m=u.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset('M_Benmore_AtmosphereAnchor',DEST,u.Material,u.MaterialFactoryNew())
   mel.delete_all_material_expressions(m);props(m,blend_mode=u.BlendMode.BLEND_TRANSLUCENT,shading_model=u.MaterialShadingModel.MSM_UNLIT,two_sided=True)
   zero=props(mel.create_material_expression(m,u.MaterialExpressionConstant),r=0.);mel.connect_material_property(zero,'',u.MaterialProperty.MP_OPACITY);mel.connect_material_property(zero,'',u.MaterialProperty.MP_EMISSIVE_COLOR);mel.recompile_material(m);eal.save_loaded_asset(m)
   actors=act.get_all_level_actors();anchor=next(a for a in actors if a.get_actor_label()=='Benmore_Character_SoftSky');report['previous_dome_material']=anchor.static_mesh_component.get_material(0).get_path_name();anchor.static_mesh_component.set_material(0,m)
   sun=next(a for a in actors if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='Sun');c=sun.light_component;report['previous_sun']={'rotation':str(sun.get_actor_rotation()),'intensity':c.get_editor_property('intensity')}
   c.set_mobility(u.ComponentMobility.MOVABLE);sun.set_actor_rotation(u.Rotator(pitch=-24,yaw=-80),False);c.set_intensity(60000.);c.set_temperature(5900)
   props(c,use_temperature=True,light_source_angle=.75,atmosphere_sun_light=True,cast_cloud_shadows=True,cloud_shadow_strength=.6,cloud_shadow_on_surface_strength=.45,cloud_shadow_extent=12.,cloud_shadow_map_resolution_scale=1.)
   sky=next(a for a in actors if isinstance(a,u.SkyLight) and a.get_actor_label()=='Sky');sc=sky.get_component_by_class(u.SkyLightComponent);report['previous_sky']={k:str(sc.get_editor_property(k)) for k in ['source_type','intensity','real_time_capture','cubemap']}
   sc.set_mobility(u.ComponentMobility.MOVABLE);props(sc,source_type=u.SkyLightSourceType.SLS_CAPTURED_SCENE,real_time_capture=True,lower_hemisphere_is_black=False,cloud_ambient_occlusion=True,cloud_ambient_occlusion_strength=.35);sc.set_intensity(1.0)
   atmos=next(a for a in actors if isinstance(a,u.SkyAtmosphere));ac=atmos.get_component_by_class(u.SkyAtmosphereComponent)
   report['previous_atmosphere']={k:str(ac.get_editor_property(k)) for k in ['rayleigh_scattering_scale','mie_scattering_scale','multi_scattering_factor','aerial_pespective_view_distance_scale']}
   props(ac,rayleigh_scattering_scale=.028,mie_scattering_scale=.002,multi_scattering_factor=1.,aerial_pespective_view_distance_scale=.75)
   cloud=act.spawn_actor_from_class(u.VolumetricCloud,u.Vector());cloud.set_actor_label('Benmore_Daylight_Clouds');cc=cloud.get_component_by_class(u.VolumetricCloudComponent);cc.set_material(cloudmat)
   props(cc,layer_bottom_altitude=2.8,layer_height=3.0,tracing_max_distance=25.,view_sample_count_scale=1.,shadow_view_sample_count_scale=.75)
   for old in actors:
    if old.get_actor_label()=='ReviewExposure':old.set_editor_property('enabled',False)
   pp=act.spawn_actor_from_class(u.PostProcessVolume,u.Vector());pp.set_actor_label('Benmore_Daylight_Grade');props(pp,unbound=True,priority=400.,blend_weight=1.)
   s=pp.get_editor_property('settings')
   values=dict(auto_exposure_method=u.AutoExposureMethod.AEM_HISTOGRAM,auto_exposure_min_brightness=13.6,auto_exposure_max_brightness=13.6,auto_exposure_bias=0.,bloom_intensity=.12,lens_flare_intensity=0.,vignette_intensity=.10,film_grain_intensity=0.,color_saturation=u.Vector4(1.,1.,1.,.96),color_contrast=u.Vector4(1.,1.,1.,1.04),local_exposure_highlight_contrast_scale=.85,local_exposure_shadow_contrast_scale=.92)
   for k,v in values.items():s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
   pp.set_editor_property('settings',s)
   fog=next(a for a in actors if a.get_actor_label()=='Benmore_DistanceHaze');fc=fog.component;report['previous_fog_colour']=str(fc.get_editor_property('fog_inscattering_luminance'))
   # Ambient fog is an absolute luminance; directional fog is multiplied by
   # sun luminance in FogRendering.cpp and must remain a small coefficient.
   props(fc,fog_inscattering_luminance=u.LinearColor(1200,1700,2400,1),directional_inscattering_luminance=u.LinearColor(.030,.028,.025,1))
   report['settings']={'sun_lux':60000,'sun_pitch':-24,'sun_yaw':-80,'exposure_ev100':13.6,'skylight_capture':'real-time atmosphere and clouds','cloud_shadow_on_surface_strength':.45,'weather_cloud_control':'RainIntensity -> coverage and density','height_changed':False}
   phase='warm';last=time.monotonic()
  elif phase=='warm' and time.monotonic()-last>45:
   phase='saving';assert les.save_current_level();finish()
 except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
