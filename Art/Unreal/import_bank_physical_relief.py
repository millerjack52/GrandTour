import unreal as u,sys,json,importlib
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
import lidar_first_section as section
import lidar_bank_relief_detail as detail
import lidar_section_surface as surface
importlib.reload(detail);importlib.reload(surface)
qa=root/'Saved/LidarAuthoringQA/RS7Relief';survey=json.loads((qa/'survey.json').read_text())
assert section.snapshot()==survey['snapshot'];assert section.outside_snapshot()==survey['outside']
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
name='SM_RS7_BankSkin';task=u.AssetImportTask();task.filename=str(root/f'Art/Export/LidarStudy/FirstSection/{name}_LOD0.fbx');task.destination_path=section.DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(section.DEST+'/'+name);assert mesh
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,u.load_asset(section.DEST+'/M_BankSurface'))
assert u.EditorAssetLibrary.save_loaded_asset(mesh)
assert section.snapshot()==survey['snapshot'];assert section.outside_snapshot()==survey['outside']
(qa/'import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'size':str(mesh.get_bounds().box_extent*2),'planting_unchanged':True,'map_not_resaved':True,'collision':'complex-as-simple; same fitted mesh as rendering','grid_spacing_cm':10},indent=2))
print('BANK_PHYSICAL_RELIEF_IMPORTED')
