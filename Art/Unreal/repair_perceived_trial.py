"""Local voxel-compatible material copies and a verified open-field review camera."""
import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from perceived_detail_variants import PD,BASE,QA
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem)
def prepare_materials():
 materials=[]
 for label,source in [('Bark','/Game/GrandTour/Environment/NativePlants/v01/M_NZ_Bark'),('Foliage','/Game/GrandTour/Environment/NativePlants/v01/M_NZ_Foliage')]:
  path=PD+'/M_PD_'+label;m=u.load_asset(path) or assets.duplicate_asset(source,path)
  for usage in [u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,u.MaterialUsage.MATUSAGE_NANITE,u.MaterialUsage.MATUSAGE_VOXELS]:mel.set_material_usage(m,usage)
  mel.recompile_material(m);assets.save_loaded_asset(m,False);materials.append(m)
 path=PD+'/MI_PD_Canopy';mi=u.load_asset(path) or assets.duplicate_asset(BASE+'/MI_NZ_Foliage_Canopy',path)
 mel.set_material_instance_parent(mi,materials[1]);mel.update_material_instance(mi);assets.save_loaded_asset(mi,False)
 return materials,mi
def run():
 materials,mi=prepare_materials()
 stand=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_PD_Stand')
 for c in stand.get_components_by_class(u.InstancedStaticMeshComponent):c.set_material(0,materials[0]);c.set_material(1,mi)
 views=json.loads((QA/'cameras-proof.json').read_text());view=next(v for v in views if v['view']=='T01')
 # This eye position was already captured unobstructed in pd-base-proof-T01.
 view['position']=[-51500,30000,10715.99609375]
 cam=next(a for a in actors.get_all_level_actors() if a.get_name()==view['actor']);pos=u.Vector(*view['position']);target=u.Vector(*view['target'])
 cam.set_actor_location(pos,False,True);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
 (QA/'cameras-proof.json').write_text(json.dumps(views,indent=2));(QA/'cameras-trial.json').write_text(json.dumps([v for v in views if v['view'] in ['G01','F01','T01']],indent=2))
 import build_perceived_detail_motion as motion;motion.run()
 (QA/'voxel-materials.json').write_text(json.dumps(dict(materials=[m.get_path_name() for m in materials],instance=mi.get_path_name(),parent=mi.get_editor_property('parent').get_path_name(),voxel_flags=[m.get_editor_property('used_with_voxels') for m in materials],original_materials_modified=False),indent=2))
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
