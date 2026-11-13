"""Reimport water with the OBJ importer handedness explicitly compensated."""
import unreal as u
import sys,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
OUT=ROOT/'Art/Export/BigMountain';BASE='/Game/GrandTour/ArtTests/BigMountain';report={'ok':False}
try:
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.OBJ 0')
 ui=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(ui.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,generate_lightmap_u_vs=False)
 task=props(u.AssetImportTask(),filename=str(OUT/'Water.obj'),destination_path=BASE,destination_name='SM_Water',automated=True,replace_existing=True,save=True,options=ui)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(BASE+'/SM_Water');assert mesh
 mesh.set_material(0,u.load_asset(BASE+'/M_Water'));assert u.EditorAssetLibrary.save_loaded_asset(mesh)
 d=mesh.get_static_mesh_description(0);first=d.get_vertex_position(u.VertexID(0));assert abs(first.x+250000)<.1 and abs(first.y+250000)<.1
 probe=json.loads((OUT/'water-probe.json').read_text());x,y=probe['point'];near=[]
 for i in range(d.get_vertex_count()):
  p=d.get_vertex_position(u.VertexID(i));dist=(p.x-x)**2+(p.y-y)**2
  if dist<1500**2:near.append([dist,p.x,p.y,p.z])
 assert near and abs(min(near)[3]-probe['surface_cm'])<1
 report.update(ok=True,first_vertex=list(first.to_tuple()),nearest_vertices=sorted(near)[:4],handedness_verified=True)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'waterrepair.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
