"""Import FS1 trees and apply them directly to the saved LiDAR forest.
Run through run_lidar_forest.ps1. No terrain rebuild or extra showcase map.
"""
import unreal as u
from pathlib import Path
import sys,json,time,traceback,shutil,gc,hashlib,os
from collections import Counter
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
OUT=ROOT/'Art/Export/LidarStudy/ForestFS1';PLACE=ROOT/'Art/Export/LidarStudy/Place'
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/ForestShapes'
QA=ROOT/'Saved/LidarAuthoringQA/FS1';QA.mkdir(parents=True,exist_ok=True)
assets=u.EditorAssetLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
mel=u.MaterialEditingLibrary
report={'ok':False};busy=False;deadline=0
CHECK=os.environ.get('GT_FS1_CHECK')=='1'
REPORT_FILE=QA/('check.json' if CHECK else 'install.json')

def import_mesh(rows):
 row=rows[0];name=row['asset'];path=DEST+'/'+name
 digest=hashlib.sha256(b''.join((OUT/(r['name']+'.fbx')).read_bytes() for r in rows)).hexdigest()
 mesh=u.load_asset(path)
 if mesh and assets.get_metadata_tag(mesh,'FS1Digest')==digest:return mesh
 task=u.AssetImportTask();task.filename=str(OUT/(row['name']+'.fbx'));task.destination_path=DEST;task.destination_name=name
 task.automated=True;task.replace_existing=True;task.save=True
 opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
 opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
 d.vertex_color_import_option=u.VertexColorImportOption.REPLACE;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path);assert mesh,path
 options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False
 options.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=1.,screen_size=v) for v in (1.,.22,.08)]
 assert sm.set_lods(mesh,options)==3
 for lod in (1,2):assert sm.import_lod(mesh,lod,str(OUT/(name+'_LOD'+str(lod)+'.fbx')))==lod
 kit='/Game/GrandTour/Environment/NativePlants/v01'
 for i,s in enumerate(mesh.get_editor_property('static_materials')):
  slot=str(s.get_editor_property('material_slot_name')).lower()
  mesh.set_material(i,u.load_asset(kit+('/M_NZ_Foliage' if 'foliage' in slot else '/M_NZ_Bark')))
 ns=sm.get_nanite_settings(mesh);ns.enabled=False;sm.set_nanite_settings(mesh,ns,True);sm.remove_collisions(mesh)
 b=mesh.get_bounds();actual=sorted([2*b.box_extent.x/100,2*b.box_extent.y/100,2*b.box_extent.z/100])
 assert all(abs(a-b)<.025 for a,b in zip(actual,sorted(row['size_m']))),(name,actual,row['size_m'])
 assert all(mesh.get_num_sections(lod)==2 for lod in range(3)),name
 assets.set_metadata_tag(mesh,'FS1Digest',digest);assert assets.save_loaded_asset(mesh)
 return mesh

def tint_far(k,rgb):
 import lidar_canopy_assets
 lidar_canopy_assets.tint_far_card(k,rgb)

def run():
 if CHECK:
  import lidar_canopy_assets as canopy
  assert canopy.cached(),'canopy cache does not match installed sources'
  materials=[]
  for k in range(4):
   m=u.load_asset(BASE+'/CanopyKit/M_FirFar_'+str(k));assert m
   # Migrate the prototype helper's tag to the shared rebuild-safe helper.
   for n in mel.get_material_expressions(m):
    if isinstance(n,u.MaterialExpressionMultiply) and str(n.get_editor_property('desc'))=='FS1Tint':n.set_editor_property('desc','LP3cTint')
   n0=len(mel.get_material_expressions(m));rgb=(.42,.40,.38) if k==3 else (.55,.62,.50)
   canopy.tint_far_card(k,rgb);canopy.tint_far_card(k,rgb)
   nodes=list(mel.get_material_expressions(m))
   assert len(nodes)==n0,(k,'repeated tint grew the graph')
   assert len([n for n in nodes if isinstance(n,u.MaterialExpressionMultiply) and str(n.get_editor_property('desc'))=='LP3cTint'])==1
   tex=u.load_asset(BASE+'/CanopyKit/T_FirAtlas_'+str(k))
   assert tex.get_editor_property('do_scale_mips_for_alpha_coverage')
   materials.append(dict(path=m.get_path_name(),nodes=len(nodes),tint_idempotent=True,alpha_coverage_mips=True))
   yield 1
  report.update(ok=True,cache_matches=True,materials=materials)
  REPORT_FILE.write_text(json.dumps(report,indent=2));yield 5;return
 backup=ROOT/'Saved/LidarAuthoringBackups'/('FS1-'+str(time.time_ns()));backup.mkdir(parents=True)
 content=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
 for folder in ('CanopyKit','ForestShapes'):
  if (content/folder).exists():shutil.copytree(content/folder,backup/folder)
 shutil.copy2(content/'L_LidarStudy.umap',backup/'L_LidarStudy.umap')
 for name in ('canopy-assets.json','forest-shapes.json'):
  if (PLACE/name).exists():shutil.copy2(PLACE/name,backup/name)
 report['backup']=str(backup)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 rows=json.loads((OUT/'manifest.json').read_text())['models'];sources={};imported=[]
 for name in sorted({r['asset'] for r in rows}):
  group=sorted((r for r in rows if r['asset']==name),key=lambda r:r['lod'])
  mesh=import_mesh(group);sources['SM_NZ_Beech_'+group[0]['variant']]=mesh.get_path_name().split('.')[0]
  imported.append(dict(path=mesh.get_path_name(),triangles=[int(mesh.get_static_mesh_description(i).get_triangle_count()) for i in range(3)]));yield .1
 (PLACE/'forest-shapes.json').write_text(json.dumps(dict(version='FS1',sources=sources),indent=2))
 import lidar_canopy_assets as canopy
 meshes=yield from canopy.build(world,force=True)
 for k in range(4):tint_far(k,(.42,.40,.38) if k==3 else (.55,.62,.50))
 import lidar_level_polish
 lidar_level_polish.foliage_materials();yield 3
 assert les.load_level(BASE+'/L_LidarStudy');yield 1
 refs=actors.get_all_level_actors();ground=next(a for a in refs if isinstance(a,u.GTProceduralGround));digest=str(ground.output_digest)
 forest=next(a for a in refs if a.get_actor_label()=='LidarStudy_Forest');counts=[]
 from lidar_grounding import GroundSampler
 sampler=GroundSampler(ground);root_errors=[]
 expected=Counter(int(t[3]) for t in json.loads((PLACE/'trees.json').read_text()))
 leaf=u.load_asset(BASE+'/MI_NZ_Foliage_Canopy');bark=u.load_asset(BASE+'/MI_NZ_Bark_Spar');assert leaf and bark
 for c in forest.get_components_by_class(u.InstancedStaticMeshComponent):
  m=c.static_mesh
  if not m or not m.get_name().startswith('SM_Canopy_'):continue
  k=int(m.get_name().rsplit('_',1)[1]);c.set_static_mesh(meshes[k]);m=meshes[k]
  for i,s in enumerate(m.get_editor_property('static_materials')):
   mat=s.get_editor_property('material_interface')
   # Clear obsolete overrides after replacement, including the baked far slot.
   c.set_material(i,mat)
   if mat and mat.get_name()=='M_NZ_Foliage':c.set_material(i,leaf)
   elif k==3 and mat and mat.get_name()=='M_NZ_Bark' and bark:c.set_material(i,bark)
  counts.append(dict(kind=k,instances=c.get_instance_count(),lods=sm.get_lod_count(m)))
  assert sm.get_lod_count(m)==4
  assert c.get_instance_count()==expected[k],(k,c.get_instance_count(),expected[k])
  for i in range(0,c.get_instance_count(),max(1,c.get_instance_count()//512)):
   p=c.get_instance_transform(i,True).translation
   root_errors.append(abs(p.z+3-sampler.height(p.x,p.y)))
 assert len(counts)==4,counts
 assert max(root_errors)<.1,('floating forest root',max(root_errors))
 assert str(ground.output_digest)==digest
 import canopy_depth
 if canopy_depth.enabled():report['canopy_depth']=canopy_depth.apply()
 assert les.save_current_level()
 report.update(ok=True,saved=True,imports=imported,forest=counts,ground_digest=digest,canopy=canopy.report,
               roots=dict(samples=len(root_errors),max_error_cm=max(root_errors)))
 REPORT_FILE.write_text(json.dumps(report,indent=2));yield 2
 refs=forest=ground=c=m=mesh=meshes=None;gc.collect();les.load_level('/Engine/Maps/Entry');yield 4

steps=run()
def tick(dt):
 global busy,deadline,steps
 if busy:return
 busy=True
 try:
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());REPORT_FILE.write_text(json.dumps(report,indent=2));u.log_error(report['error'])
  u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
