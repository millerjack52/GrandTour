"""Install dedicated bark atlases in the isolated FloraPath assets only."""
import unreal as u,json,traceback
from pathlib import Path
O=Path(u.Paths.project_dir()).resolve()/'Art/Export/LidarStudy/FloraPath';D=O/'BarkFix';DEST='/Game/GrandTour/ArtTests/FloraPath';r={'ok':False,'meshes':[]}
eal=u.EditorAssetLibrary;at=u.AssetToolsHelpers.get_asset_tools();sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);mel=u.MaterialEditingLibrary

def p(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
try:
 report=json.loads((D/'export-report.json').read_text());assert report['ok']
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(DEST+'/L_FloraPath')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 for row in report['meshes']:
  mesh=u.load_asset(DEST+'/'+row['name']);assert mesh
  mats=[x.material_interface for x in mesh.get_editor_property('static_materials')];triangles=mesh.get_static_mesh_description(0).get_triangle_count();before=mesh.get_bounds()
  t=p(u.AssetImportTask(),filename=str(D/(row['name']+'.fbx')),destination_path=DEST,destination_name=row['name'],automated=True,replace_existing=True,save=True)
  opt=p(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
  p(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE);t.options=opt;at.import_asset_tasks([t]);mesh=u.load_asset(DEST+'/'+row['name'])
  assert mesh.get_static_mesh_description(0).get_triangle_count()==triangles
  assert sm.get_num_uv_channels(mesh,0)==2
  after=mesh.get_bounds();assert (after.origin-before.origin).length()<.1 and (after.box_extent-before.box_extent).length()<.1
  for i,mat in enumerate(mats):mesh.set_material(i,mat)
  bs=sm.get_lod_build_settings(mesh,0);p(bs,recompute_normals=False,recompute_tangents=True,use_full_precision_u_vs=True);sm.set_lod_build_settings(mesh,0,bs);sm.remove_collisions(mesh)
  opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False;opts.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=a,screen_size=b) for a,b in [(1.,1.),(.5,.12),(.22,.035)]];assert sm.set_lods(mesh,opts)==3
  texname='T_Bark_'+row['source'];task=p(u.AssetImportTask(),filename=str(D/(row['source']+'_bark.png')),destination_path=DEST,destination_name=texname,automated=True,replace_existing=True,save=True);at.import_asset_tasks([task]);tex=u.load_asset(DEST+'/'+texname);assert tex
  p(tex,srgb=True,compression_settings=u.TextureCompressionSettings.TC_DEFAULT,max_texture_size=2048);eal.save_loaded_asset(tex)
  mi=mats[row['bark_slot']];assert isinstance(mi,u.MaterialInstanceConstant)
  u.log('BARK_MI '+mi.get_path_name()+' PARAMS '+str(mel.get_texture_parameter_names(mi)))
  changed=mel.set_material_instance_texture_parameter_value(mi,'PaintedColour',tex);mel.update_material_instance(mi)
  actual=mel.get_material_instance_texture_parameter_value(mi,'PaintedColour');u.log('BARK_PARAM '+str(changed)+' ACTUAL '+str(actual))
  assert actual==tex,(mi.get_path_name(),actual)
  eal.save_loaded_asset(mi);eal.save_loaded_asset(mesh)
  r['meshes'].append({'name':row['name'],'triangles':triangles,'bounds_unchanged':True,'leaf_uv_unchanged':row['leaf_uv_unchanged'],'bark_resolution':2048,'lods':sm.get_lod_count(mesh),'added_shader_texture_samples':0})
 r['ok']=True
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'bark-report.json').write_text(json.dumps(r,indent=2))
def quit(dt):u.unregister_slate_post_tick_callback(h);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);h=u.register_slate_post_tick_callback(quit)
