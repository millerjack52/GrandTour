"""Install dedicated source bark maps only in the isolated group assets."""
import unreal as u,json,hashlib
from pathlib import Path
from benmore_river_life_materials import Graph,props
O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraGroup');D='/Game/GrandTour/ArtTests/FloraGroup/Assets'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
def install(models):
 t=u.AssetToolsHelpers.get_asset_tools();s=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 data=json.loads((O/'bark-report.json').read_text());assert data['ok'] and data['source_unchanged'];rows=[]
 for row in data['meshes']:
  mesh=models[row['key']];oldbounds=mesh.get_bounds();oldmats={}
  for x in mesh.get_editor_property('static_materials'):
   name=str(x.get_editor_property('imported_material_slot_name'))
   canonical=next((k for k in ['Wood_material','Leaf_0'] if name==k or name.startswith(k+'.') or name.startswith(k+'_')),None)
   assert canonical and canonical not in oldmats,name
   oldmats[canonical]=x.material_interface
  digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()
  if E.get_metadata_tag(mesh,'FloraBarkSHA256')!=digest:
   task=props(u.AssetImportTask(),filename=row['fbx'],destination_path=D,destination_name=mesh.get_name(),automated=True,replace_existing=True,save=True)
   opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
   props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE);task.options=opt;t.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+mesh.get_name())
  assert (mesh.get_bounds().origin-oldbounds.origin).length()<.1 and (mesh.get_bounds().box_extent-oldbounds.box_extent).length()<.1
  name=Path(row['colour']).stem;texture=u.load_asset(D+'/'+name);texhash=hashlib.sha256(Path(row['colour']).read_bytes()).hexdigest()
  if not texture or E.get_metadata_tag(texture,'FloraSourceSHA256')!=texhash:
   task=props(u.AssetImportTask(),filename=row['colour'],destination_path=D,destination_name=name,automated=True,replace_existing=True,save=True);t.import_asset_tasks([task]);texture=u.load_asset(D+'/'+name)
  props(texture,srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,max_texture_size=4096,lod_bias=0)
  E.set_metadata_tag(texture,'FloraSourceSHA256',texhash);E.save_loaded_asset(texture,False)
  name='M_SourceBark_'+row['key'];mat=u.load_asset(D+'/'+name) or t.create_asset(name,D,u.Material,u.MaterialFactoryNew())
  M.delete_all_material_expressions(mat);props(mat,two_sided=True,tangent_space_normal=False,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,blend_mode=u.BlendMode.BLEND_OPAQUE);M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
  g=Graph(mat);uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=1);c=g.node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourceBarkColour',texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(uv,c,'UVs');g.output(c,u.MaterialProperty.MP_BASE_COLOR,'RGB')
  g.output(g.scalar(0),u.MaterialProperty.MP_SPECULAR);g.output(g.scalar(.95),u.MaterialProperty.MP_ROUGHNESS)
  n=g.node(u.MaterialExpressionVertexNormalWS);side=g.node(u.MaterialExpressionTwoSidedSign);normal=g.custom(['N','S'],'return normalize(N)*S;');g.wire(n,normal,'N');g.wire(side,normal,'S');g.output(normal,u.MaterialProperty.MP_NORMAL)
  assert not M.recompile_material(mat);E.save_loaded_asset(mat,False)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   name=str(slot.get_editor_property('imported_material_slot_name'))
   if name.startswith('Wood_material'):mesh.set_material(i,mat)
   else:
    assert name=='Leaf_0' or name.startswith('Leaf_0.') or name.startswith('Leaf_0_'),name
    mesh.set_material(i,oldmats['Leaf_0'])
  build=s.get_lod_build_settings(mesh,0);props(build,recompute_normals=False,recompute_tangents=True,generate_lightmap_u_vs=False,use_full_precision_u_vs=True);s.set_lod_build_settings(mesh,0,build)
  E.set_metadata_tag(mesh,'FloraBarkSHA256',digest);E.save_loaded_asset(mesh,False);models[row['key']]=mesh
  rows.append({'key':row['key'],'material':mat.get_path_name(),'colour_texture':texture.get_path_name(),'resolution':[texture.blueprint_get_size_x(),texture.blueprint_get_size_y()],'srgb':texture.get_editor_property('srgb'),'compression':str(texture.get_editor_property('compression_settings')),'max_size':texture.get_editor_property('max_texture_size'),'lod_bias':texture.get_editor_property('lod_bias'),'source_graph':data['active_source_bark'],'normal_policy':data['normal_policy'],'leaf_uv_and_geometry_unchanged':row['before']==row['after'],'bark_texture_samples':1})
 return rows
