"""Keep original LOD shadow geometry while the visible trial uses detailed voxels."""
import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from perceived_detail_variants import BASE,QA
def run():
 actors=u.get_editor_subsystem(u.EditorActorSubsystem)
 stand=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_PD_Stand')
 visible=next(c for c in stand.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh.get_name()=='SM_PD_Canopy_0')
 proxy=next((c for c in stand.get_components_by_class(u.InstancedStaticMeshComponent) if 'PD_ShadowProxy' in [str(t) for t in c.get_editor_property('component_tags')]),None)
 transforms=[visible.get_instance_transform(i,True) for i in range(visible.get_instance_count())]
 if not proxy:proxy=u.GTVegetationSubsystem.add_tagged_instances(stand,u.load_asset(BASE+'/CanopyKit/SM_Canopy_0'),transforms,'PD_ShadowProxy','NoCollision',True)
 visible.set_cast_shadow(False)
 proxy.set_cast_shadow(True);proxy.set_editor_property('cast_hidden_shadow',True);proxy.set_hidden_in_game(True)
 proxy.set_render_in_main_pass(False);proxy.set_editor_property('render_in_depth_pass',False)
 proxy.set_editor_property('affect_distance_field_lighting',False);proxy.set_editor_property('visible_in_ray_tracing',False)
 proxy.set_cull_distances(visible.get_editor_property('instance_start_cull_distance'),visible.get_editor_property('instance_end_cull_distance'))
 proxy.set_lod_distance_scale(visible.get_editor_property('instance_lod_distance_scale'))
 for i in range(2):proxy.set_material(i,visible.get_material(i))
 assert proxy.get_instance_count()==visible.get_instance_count()==48
 (QA/'shadow-proxy.json').write_text(json.dumps(dict(visible_instances=48,shadow_only_instances=48,visible_casts_shadow=visible.get_editor_property('cast_shadow'),shadow_mesh=proxy.static_mesh.get_path_name(),casts_hidden_shadow=proxy.get_editor_property('cast_hidden_shadow'),hidden_in_game=proxy.get_editor_property('hidden_in_game'),renders_main_pass=proxy.get_editor_property('render_in_main_pass'),policy='Original canopy LODs and their disabled far-card shadows, retained for exactly the same 48 transforms. Visible voxel mesh no longer supplies VSM geometry.'),indent=2))
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
