"""Save isolated package variants for sequential, cold-process A/B captures."""
import unreal as u,json,shutil,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
BASE='/Game/GrandTour/ArtTests/LidarStudy';PD=BASE+'/FirstSection/PerceivedDetail'
QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail';VAR=QA/'Variants'
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
def file(asset):return ROOT/'Content'/(asset.removeprefix('/Game/')+'.uasset')
def save(asset,variant):
 path=file(asset);dest=VAR/variant/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
def run():
 import perceived_tree_proxy as proxy
 proxy.material(json.loads((ROOT/'Art/Export/LidarStudy/FirstSection/PerceivedDetail/tree-bake.json').read_text()))
 paths=[BASE+'/FirstSection/M_BankSurface',BASE+'/FirstSection/SM_RS7_Cascade_0',PD+'/SM_PD_Canopy_0']
 for path in paths:save(path,'detail')
 m=u.load_asset(paths[0]);param=next(n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='PD_Parallax')
 param.set_editor_property('default_value',1.);mel.recompile_material(m);assets.save_loaded_asset(m,False);save(paths[0],'pom')
 param.set_editor_property('default_value',0.);mel.recompile_material(m);assets.save_loaded_asset(m,False)
 mesh=u.load_asset(paths[2]);original=u.load_asset(BASE+'/CanopyKit/SM_Canopy_0')
 assert sm.set_lod_from_static_mesh(mesh,3,original,3,True)==3
 sm.set_lod_screen_sizes(mesh,list(sm.get_lod_screen_sizes(original)));assets.save_loaded_asset(mesh,False);save(paths[2],'baseline')
 # Copy exact original ground/fern packages; new packages and camera map remain.
 backup=Path(json.loads((QA/'backup.json').read_text())['backup'])
 for path in paths[:2]:
  rel=file(path).relative_to(ROOT);dest=VAR/'baseline'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(backup/rel,dest)
 report=[]
 # Nanite consumes LOD0. Remove legacy billboard LODs and their unused materials
 # so this candidate cannot silently request unsupported far-card permutations.
 assert sm.remove_lods(mesh)
 mesh.set_editor_property('static_materials',list(original.get_editor_property('static_materials'))[:2])
 for i,name in enumerate(['M_PD_Bark','MI_PD_Canopy']):
  local=u.load_asset(PD+'/'+name)
  if local:mesh.set_material(i,local)
 for slot in mesh.get_editor_property('static_materials'):
  parent=slot.material_interface
  while isinstance(parent,u.MaterialInstance):parent=parent.get_editor_property('parent')
  assert parent.get_editor_property('used_with_nanite'),parent.get_path_name()
 for label,mode in [('nanite-preserve',u.NaniteShapePreservation.PRESERVE_AREA),('nanite-voxel',u.NaniteShapePreservation.VOXELIZE)]:
  ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;ns.shape_preservation=mode
  sm.set_nanite_settings(mesh,ns,True);assets.save_loaded_asset(mesh,False);save(paths[2],label)
  report.append(dict(variant=label,settings=str(mesh.get_editor_property('nanite_settings')),mesh=paths[2],source_lods=sm.get_lod_count(mesh),materials=len(mesh.get_editor_property('static_materials'))))
 # Existing real relief with a masked perimeter; no overlapping geometry added.
 ground=BASE+'/FirstSection/SM_RS7_BankSkin';skin=u.load_asset(ground);save(ground,'detail');save(ground,'baseline')
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE);assets.save_loaded_asset(m,False);save(paths[0],'nanite-ground')
 ns=skin.get_editor_property('nanite_settings');ns.enabled=True;sm.set_nanite_settings(skin,ns,True);assets.save_loaded_asset(skin,False);save(ground,'nanite-ground')
 report.append(dict(variant='nanite-ground',settings=str(skin.get_editor_property('nanite_settings')),mesh=ground,scope='Existing relief geometry with masked perimeter; no new protrusion geometry'))
 (QA/'variants.json').write_text(json.dumps(report,indent=2))
 print('PD_VARIANTS_COMPLETE')
