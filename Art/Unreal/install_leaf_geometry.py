"""Replace only the nearest tree LOD, keeping map, lower LODs and proxies intact."""
import unreal as u,sys,json,traceback,shutil,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
from forest_shaders import connected_nodes
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/LeafGeometry';CD=BASE+'/CanopyDepth';OUT=ROOT/'Art/Export/LidarStudy/LeafGeometry';QA=ROOT/'Saved/LidarAuthoringQA/LeafGeometry'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def protected():
 root=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
 files=[root/'L_LidarStudy.umap']+list((root/'CohesiveStyle').glob('*.uasset'))+list((root/'CanopyDepth').rglob('*.uasset'))
 return {str(p.relative_to(ROOT)):sha(p) for p in files if not p.name.startswith('SM_CD_Canopy_')}
def material():
 path=DEST+'/M_LeafGeometry';m=u.load_asset(path) or assets.duplicate_asset(BASE+'/CohesiveStyle/M_EvergreenFoliage',path);g=Graph(m,'LeafGeometry')
 if not assets.get_metadata_tag(m,'LeafGeometry'):
  n=next(n for n in connected_nodes(m) if str(n.get_editor_property('desc'))=='LeafSurface' and isinstance(n,u.MaterialExpressionCustom))
  names=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')];sources=mel.get_inputs_for_material_expression(m,n)
  # Base colour comes from the same palette program; normals are authored curved geometry.
  src=sources[names.index('Base')];out=''
  g.output(src,u.MaterialProperty.MP_BASE_COLOR,out)
  g.output(g.node(u.MaterialExpressionVertexNormalWS),u.MaterialProperty.MP_NORMAL)
  sub=g.node(u.MaterialExpressionMultiply);g.wire(src,sub,'A');g.wire(g.scalar(.30),sub,'B');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
  g.output(g.scalar(.72),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.12),u.MaterialProperty.MP_SPECULAR);g.output(g.scalar(1),u.MaterialProperty.MP_OPACITY_MASK)
  props(m,blend_mode=u.BlendMode.BLEND_OPAQUE,two_sided=True,tangent_space_normal=False,dithered_lod_transition=True)
  assets.set_metadata_tag(m,'LeafGeometry','1')
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False);return m
def run():
 manifest=json.loads((OUT/'manifest.json').read_text());audit=json.loads((QA/'audit.json').read_text())
 if not (QA/'before.json').exists():
  folder=QA/'Before';folder.mkdir(exist_ok=True)
  for k in range(3):
   path=ROOT/'Content/GrandTour/ArtTests/LidarStudy/CanopyDepth'/f'SM_CD_Canopy_{k}.uasset';shutil.copy2(path,folder/path.name)
  (QA/'before.json').write_text(json.dumps(dict(protected=protected(),audit=audit),indent=2))
 before=json.loads((QA/'before.json').read_text());assets.make_directory(DEST);mat=material();rows=[]
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 for k,row in enumerate(manifest['models']):
  name=row['name'];task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
  opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
  props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
  task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);source=u.load_asset(DEST+'/'+name);assert source
  for i,s in enumerate(source.get_editor_property('static_materials')):source.set_material(i,mat if 'LeafGeometry' in str(s.material_slot_name) else u.load_asset('/Game/GrandTour/Environment/NativePlants/v01/M_NZ_Bark'))
  ns=sm.get_nanite_settings(source);ns.enabled=False;sm.set_nanite_settings(source,ns,True);sm.remove_collisions(source);assert assets.save_loaded_asset(source,False)
  mesh=u.load_asset(CD+'/SM_CD_Canopy_'+str(k));old=before['audit'][k]
  baseline=DEST+'/SM_Before_'+str(k)
  if not u.load_asset(baseline):assert assets.duplicate_asset(CD+'/SM_CD_Canopy_'+str(k),baseline)
  assert sm.set_lod_from_static_mesh(mesh,0,source,0,True)==0
  assert sm.set_lod_screen_sizes(mesh,old['screens'])
  counts=[mesh.get_static_mesh_description(i).get_triangle_count() for i in range(sm.get_lod_count(mesh))]
  assert counts[0]==row['triangles'] and counts[1:]==old['triangles'][1:]
  assert [sm.get_lod_material_slot(mesh,3,j) for j in range(mesh.get_num_sections(3))]==old['section_slots'][3]
  leafslots=[i for i,s in enumerate(mesh.get_editor_property('static_materials')) if s.material_interface==mat];assert leafslots
  assert leafslots[0] in [sm.get_lod_material_slot(mesh,0,j) for j in range(mesh.get_num_sections(0))]
  assert assets.save_loaded_asset(mesh,False)
  rows.append(dict(kind=row['kind'],before_triangles=old['triangles'],after_triangles=counts,screens=list(sm.get_lod_screen_sizes(mesh)),opaque_leaf_slot=leafslots[0],length_cm=row['length_cm']))
 assert protected()==before['protected'],'Protected map/material/proxy changed'
 return dict(ok=True,meshes=rows,protected_packages_unchanged=True,lower_lods_unchanged=True,performance_verified=False)
if __name__=='__main__':
 try:result=run()
 except Exception:result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
 (QA/'install.json').write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
