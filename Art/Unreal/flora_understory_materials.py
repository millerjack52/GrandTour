"""Scoped undergrowth controls and source rock atlases; existing packages read-only."""
import unreal as u,json
from pathlib import Path
from benmore_river_life_materials import Graph,props
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/UnderstoryStudy';D='/Game/GrandTour/ArtTests/FloraTrail/UnderstoryTrial'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
PLANTS=('SM_Exact_grass','SM_Exact_drygrass','SM_Exact_fern','SM_Exact_shrub')
def plant(source,variant,build=False):
 path=D+'/Materials/'+source.get_name()+'_'+variant
 m=u.load_asset(path)
 if not build:assert m,path;return m
 if not m:m=E.duplicate_asset(source.get_path_name().split('.')[0],path)
 for n in list(M.get_material_expressions(m)):
  if str(n.get_editor_property('desc'))=='UnderstoryNative':M.delete_material_expression(m,n)
 g=Graph(m,'UnderstoryNative');nodes=M.get_material_expressions(m)
 inputs={str(n.get_editor_property('parameter_name')):n for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter2D)}
 assert set(inputs)=={'SourcePigment','SourceCoverage'}
 if variant in ('coverage','combined'):
  # Original mask and UVs, without stochastic holes through otherwise solid leaves.
  g.output(inputs['SourceCoverage'],u.MaterialProperty.MP_OPACITY_MASK,'R')
  props(m,opacity_mask_clip_value=.35,has_pixel_animation=False)
 if variant in ('lighting','combined'):
  props(m,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,tangent_space_normal=False)
  c=g.custom(['C'],'return C*.45;');g.wire(inputs['SourcePigment'],c,'C','RGB');g.output(c,u.MaterialProperty.MP_BASE_COLOR)
  sub=g.custom(['C'],'return C*.15;');g.wire(inputs['SourcePigment'],sub,'C','RGB');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
  n=g.node(u.MaterialExpressionVertexNormalWS);side=g.node(u.MaterialExpressionTwoSidedSign)
  normal=g.custom(['N','Side'],'return normalize(N)*Side;');g.wire(n,normal,'N');g.wire(side,normal,'Side');g.output(normal,u.MaterialProperty.MP_NORMAL)
  for p,v in [(u.MaterialProperty.MP_EMISSIVE_COLOR,0),(u.MaterialProperty.MP_ROUGHNESS,.8),(u.MaterialProperty.MP_SPECULAR,.08)]:g.output(g.scalar(v),p)
 M.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 assert not M.recompile_material(m);assert E.save_loaded_asset(m,False);return m
def rocks(build=False):
 rows=json.loads((O/'Rocks/manifest.json').read_text())['rocks'];result={};S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 for row in rows:
  path=D+'/Rocks/'+row['name'];mesh=u.load_asset(path)
  if build:
   texpath=D+'/Rocks/T_'+row['name'];tex=u.load_asset(texpath)
   if not tex:
    task=props(u.AssetImportTask(),filename=row['pigment'],destination_path=D+'/Rocks',destination_name='T_'+row['name'],automated=True,save=True)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(texpath)
   props(tex,srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,max_texture_size=2048,lod_bias=0);assert E.save_loaded_asset(tex,False)
   mp=D+'/Rocks/M_'+row['name'];m=u.load_asset(mp) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_'+row['name'],D+'/Rocks',u.Material,u.MaterialFactoryNew())
   M.delete_all_material_expressions(m);g=Graph(m,'SourceRockAtlas');uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=1)
   c=g.node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourceRockPigment',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(uv,c,'UVs');g.output(c,u.MaterialProperty.MP_BASE_COLOR,'RGB')
   g.output(g.scalar(.94),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.04),u.MaterialProperty.MP_SPECULAR)
   M.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
   if not mesh:
    task=props(u.AssetImportTask(),filename=row['fbx'],destination_path=D+'/Rocks',destination_name=row['name'],automated=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE);task.options=opt
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path)
   assert mesh
   for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,m)
   bs=S.get_lod_build_settings(mesh,0);props(bs,recompute_normals=False,recompute_tangents=True,use_full_precision_u_vs=True);S.set_lod_build_settings(mesh,0,bs);S.remove_collisions(mesh)
   ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;S.set_nanite_settings(mesh,ns,True);assert E.save_loaded_asset(mesh,False)
  assert mesh and S.get_num_uv_channels(mesh,0)==2
  result[row['original']]=mesh
 return result
def snapshot(world):
 out=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  if a.get_actor_label() not in ('FloraTrail_SourceFoliage','FloraDrive_FloraPaint_Instances'):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.static_mesh and (c.static_mesh.get_name() in PLANTS or c.static_mesh.get_name().startswith(('SM_Path_FP_Rock','SM_Detail_FP_Rock'))):
    out.append((c,c.static_mesh,list(c.get_materials()),c.get_instance_count()))
 return out
def apply(items,variant,rockmeshes,build=False,gameplay=False):
 audit=[];S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 for c,mesh,mats,count in items:
  assert c.get_instance_count()==count
  if mesh.get_name() in PLANTS:
   for i,m in enumerate(mats):c.set_material(i,m if variant in ('baseline','rocks') else plant(m,variant,build))
  else:
   replacement=rockmeshes[mesh.get_name()] if variant in ('rocks','combined') else mesh
   if not gameplay:
    assert S.get_lod_count(replacement)==S.get_lod_count(mesh)==1
    assert replacement.get_static_mesh_description(0).get_triangle_count()==mesh.get_static_mesh_description(0).get_triangle_count(),mesh.get_name()
   if c.static_mesh!=replacement:
    mobility=c.get_editor_property('mobility')
    if gameplay:c.set_mobility(u.ComponentMobility.MOVABLE)
    assert c.set_static_mesh(replacement)
    if gameplay:c.set_mobility(mobility)
   assert c.static_mesh==replacement
   for i in range(len(mats)):c.set_material(i,replacement.get_material(i) if variant in ('rocks','combined') else mats[i])
  audit.append({'component':c.get_name(),'mesh':c.static_mesh.get_path_name(),'materials':[m.get_path_name() for m in c.get_materials()],'instances':count,'lods':None if gameplay else S.get_lod_count(c.static_mesh)})
 return audit
