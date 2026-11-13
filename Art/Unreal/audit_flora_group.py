"""Reopen the saved scene, verify every texture binding, capture the editor camera."""
import unreal as u,json,sys,time,hashlib,traceback,gc
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraGroup';B=R/'Art/Export/LidarStudy/FloraParity/AssetMatch';P=R/'Art/Export/LidarStudy/FloraPath'
sys.path.insert(0,str(R/'Art/Unreal'))
D='/Game/GrandTour/ArtTests/FloraGroup';E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'ok':False,'textures':[],'slots':[],'viewport_image':None};state={'phase':0,'due':0,'busy':False}
def save():(O/'audit-report.json').write_text(json.dumps(report,indent=2))
def audit():
 global camera,world
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(D+'/L_FloraGroup')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for cmd in ['gt.Look.Post 0','r.LUT.TonemappingMethod 0','r.LUT.TonemappingSDRInvEOTF 0','r.AntiAliasingMethod 4','r.HighResScreenshotDelay 64','r.ScreenPercentage 100','r.MotionBlurQuality 0','r.EyeAdaptationQuality 0','r.DistanceFieldAO 0','r.Lumen.DiffuseIndirect.Allow 0','r.Lumen.Reflections.Allow 0']:u.SystemLibrary.execute_console_command(world,cmd)
 assets=json.loads((B/'recipe.json').read_text())['assets']+json.loads((O/'extra-assets.json').read_text())['assets'];assets={a['exact_mesh']:a for a in assets};bark={x['key']:x for x in json.loads((O/'bark-report.json').read_text())['meshes']}
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();camera=next(a for a in actors if a.get_actor_label()=='FloraGroup_ReferenceCamera')
 from flora_group_display import apply_to_volume
 apply_to_volume(next(a for a in actors if a.get_actor_label()=='FloraGroup_Display'))
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
 u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
 seen=set();textures={};triangles=0;instances=0
 for actor in actors:
  for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
   mesh=c.static_mesh;count=c.get_instance_count();instances+=count;triangles+=mesh.get_static_mesh_description(0).get_triangle_count()*count
   for i,mat in enumerate(c.get_materials()):
    assert mat and not mat.get_path_name().startswith('/Engine/EngineMaterials/'),(mesh.get_name(),i)
    slot=str(mesh.get_editor_property('static_materials')[i].get_editor_property('imported_material_slot_name'));root=mat
    while isinstance(root,u.MaterialInstanceConstant):root=root.get_editor_property('parent')
    bound={}
    for node in M.get_material_expressions(root):
     if not isinstance(node,u.MaterialExpressionTextureSampleParameter2D):continue
     name=str(node.get_editor_property('parameter_name'));tex=M.get_material_instance_texture_parameter_value(mat,name) if isinstance(mat,u.MaterialInstanceConstant) else node.get_editor_property('texture')
     assert tex,(mat.get_path_name(),name);bound[name]=tex
     if tex.get_path_name() not in textures:
      imported=tex.get_editor_property('asset_import_data');paths=list(imported.extract_filenames()) if imported else []
      textures[tex.get_path_name()]={'texture':tex.get_path_name(),'sources':paths,'dimensions':[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()],'srgb':bool(tex.get_editor_property('srgb')),'compression':str(tex.get_editor_property('compression_settings')),'max_size':tex.get_editor_property('max_texture_size'),'lod_bias':tex.get_editor_property('lod_bias')}
     if name in ['SourceCoverage','PaintedMask']:assert not tex.get_editor_property('srgb'),(name,tex)
     if name in ['SourcePigment','SourceBarkColour','PaintedColour']:assert tex.get_editor_property('srgb'),(name,tex)
    evidence={'mesh':mesh.get_path_name(),'slot':slot,'material':mat.get_path_name(),'textures':{k:v.get_path_name() for k,v in bound.items()}}
    if mesh.get_name() in assets:
     source=assets[mesh.get_name()];expected={}
     if slot.startswith('Wood_material'):expected['SourceBarkColour']=bark[source['key']]['colour'];evidence['expected_size']=4096
     else:
      matches=[s for s in source['exact_slots'] if slot==s['name'] or slot==s['name'].replace('.','_') or slot.startswith(s['name'].replace('.','_')+'_') or slot.startswith(s['name']+'.')]
      assert len(matches)==1,(slot,matches);s=matches[0];expected={'SourcePigment':source['textures']['Colour'],'SourceCoverage':s['shared_mask']}
     for name,path in expected.items():
      assert name in bound,(mesh,slot,name)
      assert E.get_metadata_tag(bound[name],'FloraSourceSHA256')==hashlib.sha256(Path(path).read_bytes()).hexdigest(),(mesh,slot,name,'source hash mismatch')
      if name=='SourceBarkColour':assert bound[name].get_editor_property('max_texture_size')==4096,(bound[name].get_name(),'unexpected size cap')
     evidence['source_files_verified']=expected
    else:evidence['source_files_verified']='Pre-existing scenery: imported sources recorded, no new conversion claimed'
    identity=(mesh.get_path_name(),i)
    if identity not in seen:seen.add(identity);report['slots'].append(evidence)
 report.update(textures=list(textures.values()),instances=instances,lod0_triangle_upper_bound=triangles,performance_verified=False)
 report['shader_fallbacks']=False;save()
def tick(dt):
 global camera,world,task
 if state['busy'] or time.monotonic()<state['due']:return
 state['busy']=True
 try:
  if state['phase']==0:audit();state.update(phase=1,due=time.monotonic()+10)
  elif state['phase']==1:
   for row in report['textures']:
    texture=u.load_asset(row['texture']);row['dimensions_after_warmup']=[texture.blueprint_get_size_x(),texture.blueprint_get_size_y()]
    if texture.get_name().startswith('T_SourceBark_'):assert row['dimensions_after_warmup']==[4096,4096],row
   save()
   path=O/'viewport-reference.png'
   if path.exists():path.rename(O/('viewport-reference-previous-'+str(int(time.time()))+'.png'))
   task=u.AutomationLibrary.take_high_res_screenshot(1200,600,str(path),camera);state.update(phase=2,due=time.monotonic()+4)
  elif state['phase']==2:
   assert (O/'viewport-reference.png').is_file(),'Editor screenshot missing';report.update(ok=True,viewport_image=str(O/'viewport-reference.png'));save()
   u.unregister_slate_post_tick_callback(handle);camera=world=task=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
