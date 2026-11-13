"""Apply map-local art controls without rebuilding meshes or touching woodland."""
import unreal as u,json,traceback
from pathlib import Path
O=Path(u.Paths.project_dir()).resolve()/'Art/Export/LidarStudy/FloraPath';r={'ok':False}
def p(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
try:
 cfg=json.loads((O/'look-settings.json').read_text());les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/ArtTests/FloraPath/L_FloraPath')
 for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  if a.get_actor_label()=='FloraPath_Sun':p(a.light_component,intensity=cfg['sun_lux'],light_color=u.Color(*cfg['sun_rgb8'],255),light_source_angle=cfg['sun_angle_degrees'],volumetric_scattering_intensity=cfg['sun_volumetric_strength'])
  elif a.get_actor_label()=='FloraPath_Sky':
   if cfg.get('sky_source')=='constant':p(a.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=u.load_asset('/Game/GrandTour/ArtTests/FloraMatch/T_SourceWorld'),real_time_capture=False,lower_hemisphere_is_black=False,occlusion_max_distance=100.)
   p(a.light_component,intensity=cfg['sky_intensity']);a.light_component.recapture_sky()
  elif a.get_actor_label()=='FloraPath_Haze':
   p(a,tags=[u.Name('GTWeatherUnmanaged')])
   a.set_actor_location(u.Vector(0,0,cfg['fog_height_cm']),False,True)
   p(a.component,fog_density=cfg['fog_density'],fog_height_falloff=cfg['fog_height_falloff'],start_distance=cfg['fog_start_cm'],fog_inscattering_luminance=u.LinearColor(*cfg['fog_colour'],1),enable_volumetric_fog=cfg['volumetric_fog'],volumetric_fog_scattering_distribution=cfg['volumetric_scattering'],volumetric_fog_albedo=u.Color(*cfg['fog_albedo_rgb8'],255),volumetric_fog_distance=cfg['volumetric_distance_cm'])
  elif a.get_actor_label()=='FloraPath_Exposure':
   s=a.settings;p(s,auto_exposure_min_brightness=cfg['exposure_ev'],auto_exposure_max_brightness=cfg['exposure_ev'],bloom_intensity=cfg['bloom'])
   if cfg.get('indirect_method')=='none':p(s,override_dynamic_global_illumination_method=True,dynamic_global_illumination_method=u.DynamicGlobalIlluminationMethod.NONE)
   a.settings=s
 assert les.save_current_level();r.update(ok=True,settings=cfg)
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'tune-report.json').write_text(json.dumps(r,indent=2))
def quit(dt):u.unregister_slate_post_tick_callback(h);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);h=u.register_slate_post_tick_callback(quit)
