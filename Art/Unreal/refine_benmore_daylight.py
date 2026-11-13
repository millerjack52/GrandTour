"""Preserve the engine cloud instance defaults and balance daylight exposure."""
import unreal as u,time,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreDaylight';DEST='/Game/GrandTour/Demo/BenmoreRoads/Daylight'
phase='load';last=time.monotonic();u.EditorPythonScripting.set_keep_python_script_alive(True)

def tick(dt):
 global phase,last
 try:
  if phase=='load':
   phase='working';les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
   actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
   next(a for a in actors if a.get_actor_label()=='Benmore_DistanceHaze').component.set_editor_property('directional_inscattering_luminance',u.LinearColor(.030,.028,.025,1))
   pp=next(a for a in actors if a.get_actor_label()=='Benmore_Daylight_Grade');s=pp.get_editor_property('settings')
   for k in ['auto_exposure_min_brightness','auto_exposure_max_brightness']:s.set_editor_property(k,13.6)
   pp.set_editor_property('settings',s)
   next(a for a in actors if a.get_actor_label()=='Sun').set_actor_rotation(u.Rotator(pitch=-24,yaw=-80),False)
   original=u.load_asset('/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst');m=u.load_asset(DEST+'/M_Benmore_VolumeClouds')
   path=DEST+'/MI_Benmore_CloudWeather';mi=u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset(original.get_path_name(),path)
   mel.set_material_instance_parent(mi,m)
   for k,v in [('Cloud_GlobalCoverage',-.14),('Cloud_GlobalDensity',.008),('Layout_CloudGlobalScale',256.),('StormClouds',0.)]:mel.set_material_instance_scalar_parameter_value(mi,k,v)
   mel.update_material_instance(mi);eal.save_loaded_asset(mi)
   cloud=next(a for a in actors if a.get_actor_label()=='Benmore_Daylight_Clouds');cc=cloud.get_component_by_class(u.VolumetricCloudComponent);cc.set_material(mi)
   report={'original_instance':{},'cloud_component':{},'cvars':{},'graph':[]}
   for key,fn in [('scalar',mel.get_scalar_parameter_names),('vector',mel.get_vector_parameter_names),('texture',mel.get_texture_parameter_names),('static_switch',mel.get_static_switch_parameter_names)]:
    getter=getattr(mel,'get_material_instance_'+key+'_parameter_value');report['original_instance'][key]={str(n):str(getter(original,n)) for n in fn(original.get_editor_property('parent'))}
   for k in ['layer_bottom_altitude','layer_height','tracing_start_max_distance','tracing_max_distance','planet_radius','material','visible','hidden_in_game']:
    try:report['cloud_component'][k]=str(cc.get_editor_property(k))
    except:pass
   for k in ['r.VolumetricCloud','r.VolumetricCloud.SampleMinCount','r.VolumetricCloud.ViewRaySampleMaxCount','sg.EffectsQuality','ShowFlag.Cloud']:report['cvars'][k]=u.SystemLibrary.get_console_variable_int_value(k)
   for n in mel.get_material_expressions(m):
    row={'name':n.get_name(),'class':n.get_class().get_name(),'input_names':[str(x) for x in mel.get_material_expression_input_names(n)],'inputs':[x.get_name() if x else None for x in mel.get_inputs_for_material_expression(m,n)]}
    for k in ['parameter_name','default_value','texture','material_function','a','b','r','const_a','const_b','code']:
     try:row[k]=str(n.get_editor_property(k))
     except:pass
    report['graph'].append(row)
   (OUT/'cloud-diagnostics.json').write_text(json.dumps(report,indent=2));assert les.save_current_level();phase='warm';last=time.monotonic()
  elif phase=='warm' and time.monotonic()-last>20:
   phase='checking';u.unregister_slate_post_tick_callback(handle)
   p=ROOT/'Art/Unreal/check_benmore_daylight.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
 except Exception:
  phase='error';(OUT/'refine-error.txt').write_text(traceback.format_exc());u.log_error(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
