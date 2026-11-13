"""Map-owned terrain and cloud composition study, with a recoverable baseline."""
import unreal as u,sys,time,json,traceback,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreVistaStudy'
DEST='/Game/GrandTour/Demo/BenmoreRoads/VistaStudy';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_vista_study_surface as surface
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
phase='load';last=time.monotonic();report={'ok':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def copy_asset(source,name):
 return u.load_asset(DEST+'/'+name) if eal.does_asset_exist(DEST+'/'+name) else eal.duplicate_asset(source,DEST+'/'+name)
def finish(error):
 report['error']=error;(OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.log_error(error)
 u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
 global phase,last
 try:
  if phase=='load':
   phase='building';assert les.load_level(LEVEL);eal.make_directory(DEST)
   world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
   backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeVistaStudy'
   if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
   for name in ['High_Overlook','Hillside_Vista','High_Overlook_Rain']:
    target=OUT/('Before_'+name+'.png')
    if not target.exists():shutil.copy2(ROOT/'Art/Export/BenmorePainterly'/(name+'.png'),target)
   task=props(u.AssetImportTask(),filename=str(OUT/'T_Benmore_GeographicZones.png'),destination_path=DEST,destination_name='T_Benmore_GeographicZones',automated=True,replace_existing=True,save=True)
   u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(DEST+'/T_Benmore_GeographicZones');assert tex
   props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True)
   assert eal.save_loaded_asset(tex)
   mats={}
   for original,name in [('M_Painterly_Terrain','M_VistaStudy_Terrain'),('M_Painterly_Hills','M_VistaStudy_Hills')]:
    m=copy_asset('/Game/GrandTour/Demo/BenmoreRoads/Painterly/'+original,name);changed=0;data_nodes=0
    for n in mel.get_material_expressions(m):
     if isinstance(n,u.MaterialExpressionCustom):
      names=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]
      if 'CoverDetail' in names:n.set_editor_property('code',surface.COLOR);changed+=1
     elif isinstance(n,u.MaterialExpressionTextureObject):
      t=n.get_editor_property('texture')
      if t and t.get_name() in ['T_Benmore_CoverStructure','T_Benmore_GeographicZones']:n.set_editor_property('texture',tex);data_nodes+=1
    assert changed>=1 and data_nodes>=1,(name,changed,data_nodes)
    if name.endswith('Terrain'):
     gout=next(n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionLandscapeGrassOutput))
     links=mel.get_inputs_for_material_expression(m,gout)
     assert len(links)==5 and all(n and isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture').get_name()=='T_Benmore_VegetationMask' for n in links)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);mats[name]=m
   actors=act.get_all_level_actors();counts={'terrain':0,'hills':0}
   for a in actors:
    if isinstance(a,u.LandscapeProxy):a.set_editor_property('landscape_material',mats['M_VistaStudy_Terrain']);counts['terrain']+=1
    elif a.get_actor_label().startswith('Benmore_Hills_'):a.static_mesh_component.set_material(0,mats['M_VistaStudy_Hills']);counts['hills']+=1
   assert counts=={'terrain':1,'hills':4},counts
   mi=copy_asset('/Game/GrandTour/Demo/BenmoreRoads/Daylight/MI_Benmore_CloudWeather','MI_VistaStudy_CloudWeather')
   for k,v in [('Cloud_GlobalCoverage',-.09),('Cloud_GlobalDensity',.008),('Layout_CloudGlobalScale',320.),('StormClouds',0.)]:mel.set_material_instance_scalar_parameter_value(mi,k,v)
   mel.update_material_instance(mi);assert eal.save_loaded_asset(mi)
   cloud=next(a for a in actors if a.get_actor_label()=='Benmore_Daylight_Clouds');cloud.get_component_by_class(u.VolumetricCloudComponent).set_material(mi)
   sun=next(a for a in actors if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='Sun')
   sun.set_actor_rotation(u.Rotator(pitch=-24,yaw=-80),False)
   props(sun.light_component,cloud_shadow_strength=.80,cloud_shadow_on_surface_strength=.70)
   sky=next(a for a in actors if isinstance(a,u.SkyLight) and a.get_actor_label()=='Sky').get_component_by_class(u.SkyLightComponent);sky.set_intensity(1.15)
   report.update(assignments=counts,mask_channels=json.loads((OUT/'geography-report.json').read_text())['channels'],sun_pitch=-24,sun_yaw=-80,skylight_intensity=1.15,cloud_pattern_scale=320,cloud_coverage=-.09,cloud_surface_shadow_strength=.70,original_grass_masks=True,height_changed=False)
   phase='warm';last=time.monotonic()
  elif phase=='warm' and time.monotonic()-last>45:
   phase='saved';assert les.save_current_level();report['ok']=True;(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
   u.unregister_slate_post_tick_callback(handle)
   p=ROOT/'Art/Unreal/check_benmore_vista_study.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
 except Exception:phase='error';finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
