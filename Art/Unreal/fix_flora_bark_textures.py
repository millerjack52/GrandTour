"""Refresh the two repaired source bark bakes without rebuilding geometry."""
import unreal as u,json,traceback
from pathlib import Path
O=Path(u.Paths.project_dir()).resolve()/'Art/Export/LidarStudy/FloraPath';r={'ok':False};DEST='/Game/GrandTour/ArtTests/FloraPath'
try:
 tasks=[]
 for name in ['FP_Tree_B_002','FP_Tree_B_003']:
  t=u.AssetImportTask();t.filename=str(O/'BarkFix'/(name+'_bark.png'));t.destination_path=DEST;t.destination_name='T_Bark_'+name;t.automated=True;t.replace_existing=True;t.save=True;tasks.append(t)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
 for name in ['FP_Tree_B_002','FP_Tree_B_003']:
  tex=u.load_asset(DEST+'/T_Bark_'+name);assert tex;tex.set_editor_property('srgb',True);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT);tex.set_editor_property('max_texture_size',2048);u.EditorAssetLibrary.save_loaded_asset(tex)
 mesh=u.load_asset(DEST+'/SM_Path_FP_Tree_D_004');desc=mesh.get_static_mesh_description(0);uvrows=[]
 for i in range(desc.get_vertex_instance_count()):
  vi=u.VertexInstanceID(i);v=desc.get_vertex_position(desc.get_vertex_instance_vertex(vi));uv=desc.get_vertex_instance_uv(vi,1);uvrows.append([v.x,v.y,v.z,uv.x,uv.y])
 (O/'BarkFix/ue-uv-check.json').write_text(json.dumps(uvrows))
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);bs=sm.get_lod_build_settings(mesh,0)
 r['build_settings']={k:str(bs.get_editor_property(k)) for k in ['generate_lightmap_u_vs','src_lightmap_index','dst_lightmap_index','use_full_precision_u_vs']}
 del desc;del mesh
 r.update(ok=True,repaired_source_uvs=['FP_Tree_B_002','FP_Tree_B_003'],exported_mesh_uvs_changed=False)
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'barktex-report.json').write_text(json.dumps(r,indent=2))
def quit(dt):u.unregister_slate_post_tick_callback(h);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);h=u.register_slate_post_tick_callback(quit)
