"""PF60: tread capacity, section isolation and foliage material audit in the real LiDAR map; never saves."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
report=dict(ok=False)
def save():(OUT/'treadcheck.json').write_text(json.dumps(report,indent=2))

def run():
 global world,pc,car
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 # Read the actual saved material graphs, not just the asset-builder source.
 mel=u.MaterialEditingLibrary;materials={}
 for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  if actor.get_actor_label() not in ['LidarStudy_Forest','LidarStudy_Understory']:continue
  for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
   for index in range(comp.get_num_materials()):
    mat=comp.get_material(index)
    while isinstance(mat,u.MaterialInstance):mat=mat.get_editor_property('parent')
    if isinstance(mat,u.Material):
     node=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
     materials[mat.get_path_name()]=node.get_name() if node else None
 report['foliage_wpo_inputs']=materials;save()
 assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
 until=time.monotonic()+180
 while not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:
   pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
 visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
 report['initial']=visual.get_research_report();assert 'tread_segments=0 ' in report['initial']
 def components():return sorted([c for c in visual.get_components_by_class(u.ProceduralMeshComponent) if c.get_name().startswith('NativeTread') and c.get_num_sections()],key=lambda c:c.get_name())
 def geometry(c):
  v,idx,n,uv,t=u.ProceduralMeshLibrary.get_section_from_procedural_mesh(c,0)
  return dict(vertices=[tuple(p.to_tuple()) for p in v],indices=list(idx),uv=[tuple(p.to_tuple()) for p in uv])
 # Exactly 256 segments fill the first component, then a new section must leave it unchanged.
 for row in range(2):visual.add_review_tread(u.Vector(-44000,-41200+row*40,0),u.Vector(-42400,-41200+row*40,0),25,.5)
 yield from settle(1)
 first=components();assert len(first)==1 and first[0].get_num_sections()==1
 before=geometry(first[0]);assert before['vertices'] and before['indices']
 visual.add_review_tread(u.Vector(-44000,-41100,0),u.Vector(-42400,-41100,0),25,.5)
 yield from settle(1)
 assert len(components())==2 and geometry(first[0])==before,'Closed tread section changed when next one was appended'
 report['closed_section_unchanged']=True
 # Fill and wrap the existing 4096-segment ring. Same material, bounds and collision flags.
 for row in range(40):visual.add_review_tread(u.Vector(-44000,-41000+row*40,0),u.Vector(-42400,-41000+row*40,0),25,row%2)
 yield from settle(2)
 cs=components();report['capacity']=visual.get_research_report()
 assert 'tread_segments=4096' in report['capacity'] and 'tread_sections=16' in report['capacity']
 assert len(cs)==16 and all(c.get_num_sections()==1 for c in cs)
 report['components']=[dict(name=c.get_name(),sections=c.get_num_sections(),vertices=len(geometry(c)['vertices']),material=c.get_material(0).get_path_name(),collision=str(c.get_collision_enabled())) for c in cs]
 assert all(c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION and c.get_material(0)==cs[0].get_material(0) for c in cs)
 assert all(r['vertices']>0 for r in report['components'])
 report['ok']=True;save()
 cs=first=visual=before=None;yield from finish()

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<600,'Tread check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
