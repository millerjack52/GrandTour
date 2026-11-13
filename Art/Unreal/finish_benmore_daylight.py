"""Save the final cross-light and exposure balance, then review the saved level."""
import unreal as u,time,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreDaylight';phase='load';last=time.monotonic();u.EditorPythonScripting.set_keep_python_script_alive(True)
def tick(dt):
 global phase,last
 try:
  if phase=='load':
   phase='working';les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
   a=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.SkyAtmosphere));c=a.get_component_by_class(u.SkyAtmosphereComponent)
   c.set_editor_property('rayleigh_scattering_scale',.028);c.set_editor_property('mie_scattering_scale',.002)
   actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
   fog=next(a for a in actors if a.get_actor_label()=='Benmore_DistanceHaze')
   fog.component.set_editor_property('directional_inscattering_luminance',u.LinearColor(.030,.028,.025,1))
   next(a for a in actors if a.get_actor_label()=='ReviewExposure').set_editor_property('enabled',False)
   next(a for a in actors if a.get_actor_label()=='Sun').set_actor_rotation(u.Rotator(pitch=-24,yaw=-80),False)
   pp=next(a for a in actors if a.get_actor_label()=='Benmore_Daylight_Grade');pp.set_editor_property('priority',400.)
   settings=pp.get_editor_property('settings')
   for k in ['auto_exposure_min_brightness','auto_exposure_max_brightness']:settings.set_editor_property(k,13.6)
   pp.set_editor_property('settings',settings)
   assert les.save_current_level();report=json.loads((OUT/'setup-report.json').read_text());report['settings'].update(rayleigh_scattering_scale_per_km=.028,mie_scattering_scale_per_km=.002,exposure_ev100=13.6,sun_yaw=-80,cloud_clear_coverage=-.14);(OUT/'setup-report.json').write_text(json.dumps(report,indent=2));phase='warm';last=time.monotonic()
  elif phase=='warm' and time.monotonic()-last>20:
   phase='checking';u.unregister_slate_post_tick_callback(handle);p=ROOT/'Art/Unreal/check_benmore_daylight.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
 except Exception:
  phase='error';(OUT/'finish-error.txt').write_text(traceback.format_exc());u.log_error(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
