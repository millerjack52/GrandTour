import unreal as u,json,traceback
from pathlib import Path
p=Path('C:/GrandTour/Art/Export/FloraDrive/collision.json');r={}
try:
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive')
 w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 r['all_actors']=[dict(label=a.get_actor_label(),type=a.get_class().get_name()) for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()];r['actors']=[]
 for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  cs=[]
  for c in a.get_components_by_class(u.PrimitiveComponent):
   if c.get_collision_enabled()!=u.CollisionEnabled.NO_COLLISION:
    cs.append(dict(name=c.get_name(),profile=str(c.get_collision_profile_name()),bounds=str(c.get_world_location()),scale=str(c.get_world_scale()),enabled=str(c.get_collision_enabled())))
  if cs:r['actors'].append(dict(name=a.get_actor_label(),components=cs))
 r['materials']={}
 for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  if isinstance(a,u.GTMudRunnerVisual):
   m=a.material;r['materials'][a.get_actor_label()]=dict(path=m.get_path_name(),model=str(m.get_editor_property('shading_model')),expressions=[dict(type=e.get_class().get_name(),code=str(e.get_editor_property('code'))) for e in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCustom)])
 r['overlap_doc']=u.SystemLibrary.box_overlap_actors.__doc__
 r['overlaps']=[a.get_actor_label() for a in u.SystemLibrary.box_overlap_actors(w,u.Vector(-2450,-275,280),u.Vector(350,200,200),[u.ObjectTypeQuery.OBJECT_TYPE_QUERY1,u.ObjectTypeQuery.OBJECT_TYPE_QUERY2,u.ObjectTypeQuery.OBJECT_TYPE_QUERY3],None,[])]
except:r['error']=traceback.format_exc()
p.write_text(json.dumps(r,indent=2));u.SystemLibrary.quit_editor()

