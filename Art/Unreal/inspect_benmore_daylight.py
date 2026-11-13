import unreal as u,json,time,traceback
from pathlib import Path
OUT=Path(u.Paths.project_dir()).resolve()/'Art/Export/BenmoreDaylight';OUT.mkdir(exist_ok=True)
u.EditorPythonScripting.set_keep_python_script_alive(True);phase='start'
def tick(dt):
 global phase
 if phase!='start':return
 phase='busy';r={}
 try:
  u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
  for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
   if isinstance(a,(u.DirectionalLight,u.SkyLight,u.PostProcessVolume,u.SkyAtmosphere,u.VolumetricCloud)):
    row={'class':a.get_class().get_name(),'rotation':str(a.get_actor_rotation())}
    c=a.get_component_by_class(u.LightComponent)
    if c:
     for k in ['intensity','mobility','light_color','source_type','cubemap','real_time_capture','atmosphere_sun_light']:
      try:row[k]=str(c.get_editor_property(k))
      except:pass
    r[a.get_actor_label()]=row
  mi=u.load_asset('/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst');m=mi.get_editor_property('parent');mel=u.MaterialEditingLibrary
  r['cloud_parameters']={str(n):mel.get_material_instance_scalar_parameter_value(mi,n) for n in mel.get_scalar_parameter_names(m)}
  r['cloud_base']=m.get_path_name();r['cloud_dir']=[n for n in dir(m) if 'expression' in n or 'editor' in n]
  for name in ['expressions','expression_collection','editor_only_data']:
   try:r['cloud_'+name]=str(m.get_editor_property(name))[:2000]
   except Exception as e:r['cloud_'+name]=str(e)
  r['object_functions']=[n for n in dir(u) if 'objects' in n or n=='ObjectIterator']
  r['ok']=True
 except:r['error']=traceback.format_exc()
 (OUT/'inspection.json').write_text(json.dumps(r,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
