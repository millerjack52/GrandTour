"""Fresh editor reload checks for the bounded detail trial."""
import unreal as u,json,runpy,sys,hashlib,time
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_first_section as section
QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail'
def run():
 original=json.loads((QA/'survey.json').read_text())
 assert section.snapshot()==original['snapshot']
 assert section.outside_snapshot()==original['outside']
 runpy.run_path(str(ROOT/'Art/Unreal/validate_bank_physical_relief.py'),run_name='__pd_validation__')
 report=json.loads((ROOT/'Saved/LidarAuthoringQA/RS7Relief/validation.json').read_text())
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 forest=next(a for a in actors if a.get_actor_label()=='LidarStudy_Forest')
 stand=next(a for a in actors if a.get_actor_label()=='LidarStudy_PD_Stand')
 treecount=0;colliders=0
 for actor in [forest,stand]:
  for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
   if 'PD_ShadowProxy' in [str(t) for t in c.get_editor_property('component_tags')]:continue
   name=c.static_mesh.get_name() if c.static_mesh else ''
   if name.startswith(('SM_Canopy_','SM_PD_Canopy_')):treecount+=c.get_instance_count()
   if name=='Cylinder':colliders+=c.get_instance_count()
 local_trees=len(json.loads((section.QA/'forest-sources.json').read_text()))
 assert treecount==148373 and local_trees==12 and colliders==treecount+local_trees,(treecount,local_trees,colliders)
 c=next(c for c in stand.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh.get_name()=='SM_PD_Canopy_0')
 proxy=next(p for p in stand.get_components_by_class(u.InstancedStaticMeshComponent) if 'PD_ShadowProxy' in [str(t) for t in p.get_editor_property('component_tags')])
 assert proxy.get_instance_count()==48 and proxy.get_editor_property('hidden_in_game') and proxy.get_editor_property('cast_hidden_shadow') and not proxy.get_editor_property('render_in_main_pass')
 assert not c.get_editor_property('cast_shadow')
 expected=json.loads((QA/'stand-proof.json').read_text())['transforms'];actual=[section.tfkey(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())]
 error=max(abs(x-y) for a,b in zip(expected,actual) for x,y in zip(a,b));assert len(actual)==len(expected)==48 and error<.01
 shadow_error=max(abs(x-y) for i,a in enumerate(actual) for x,y in zip(a,section.tfkey(proxy.get_instance_transform(i,True))));assert shadow_error<.01
 source=next(p for p in forest.get_components_by_class(u.InstancedStaticMeshComponent) if p.static_mesh and p.static_mesh.get_name()=='SM_Canopy_0')
 rows=[tuple(round(v,7) for v in section.tfkey(p.get_instance_transform(i,True))) for p in [source,c] for i in range(p.get_instance_count())]
 stand_population=dict(count=len(rows),hash=hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest())
 assert stand_population==json.loads((QA/'stand-proof.json').read_text())['before']
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 fern=u.load_asset(section.DEST+'/SM_RS7_Cascade_0')
 report.update(ok=True,validated_at_unix=time.time(),forest_geometry_instances=treecount,forest_collision_instances=colliders,trial_instances=48,original_canopy_population=stand_population,shadow_proxy_instances=48,shadow_transform_error=shadow_error,tsr_thin_geometry=u.SystemLibrary.get_console_variable_int_value('r.TSR.ThinGeometryDetection'),stand_max_component_error=error,fern_uv_channels=sm.get_num_uv_channels(fern,0),fern_vertices=[sm.get_number_verts(fern,i) for i in range(3)],tree_nanite=str(c.static_mesh.get_editor_property('nanite_settings')),scope='Fresh map reload; 148373 main forest trees include the 48-tree trial. Twelve local section trees are unchanged and included in the local instance hash; their colliders remain in the main forest component, for 148385 colliders total.')
 (QA/'final-validation.json').write_text(json.dumps(report,indent=2));print('PERCEIVED_DETAIL_VALIDATED',report)
