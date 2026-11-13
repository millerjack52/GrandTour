"""Import the same beech geometry with baked cavity colours into the trial clone."""
import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
from perceived_detail_variants import save,BASE,PD,QA
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/PerceivedDetail'
assets=u.EditorAssetLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
def run():
 source=u.load_asset(BASE+'/CanopyKit/SM_Canopy_0');path=PD+'/SM_PD_Canopy_0'
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 task=props(u.AssetImportTask(),filename=str(OUT/'SM_PD_CanopyAO_LOD0.fbx'),destination_path=PD,destination_name='SM_PD_Canopy_0',automated=True,replace_existing=True,save=True)
 opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS);task.options=opt
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path)
 ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;sm.set_nanite_settings(mesh,ns,True)
 sm.remove_lods(mesh);sm.remove_collisions(mesh);mesh.set_editor_property('static_materials',list(source.get_editor_property('static_materials'))[:2])
 for i,name in enumerate(['M_PD_Bark','MI_PD_Canopy']):
  local=u.load_asset(PD+'/'+name)
  if local:mesh.set_material(i,local)
 source_vertices=sm.get_number_verts(mesh,0)
 assert source_vertices==sm.get_number_verts(source,0),(source_vertices,sm.get_number_verts(source,0))
 # The installed canopy bounds include distant billboard planes. Compare the
 # actual source geometry, which is the invariant for this LOD0-only candidate.
 shape=u.load_asset(BASE+'/ForestShapes/SM_FS1_Beech_Mature')
 a,b=mesh.get_bounds(),shape.get_bounds();error=(a.origin-b.origin).length()+(a.box_extent-b.box_extent).length();assert error<.01,error
 rows=[]
 for label,mode in [('ao-preserve',u.NaniteShapePreservation.PRESERVE_AREA),('ao-voxel',u.NaniteShapePreservation.VOXELIZE)]:
  ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;ns.shape_preservation=mode;sm.set_nanite_settings(mesh,ns,True);assets.save_loaded_asset(mesh,False);save(path,label)
  rows.append(dict(variant=label,source_vertices_verified_before_nanite=source_vertices,fallback_vertices=sm.get_number_verts(mesh,0),bounds_error_cm=error,nanite=str(mesh.get_editor_property('nanite_settings'))))
 (QA/'canopy-occlusion-install.json').write_text(json.dumps(rows,indent=2));print('PD_CANOPY_AO_IMPORTED')
