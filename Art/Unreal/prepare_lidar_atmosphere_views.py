import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from lidar_grounding import GroundSampler
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
ground=GroundSampler(next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround)))
qa=ROOT/'Saved/LidarAuthoringQA/Atmosphere'
views=[v for v in json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/cameras.json').read_text()) if v['view'] in ('B04','B01')]
data=json.loads((ROOT/'Art/Export/LidarStudy/Place/prepare.json').read_text())['captures']
for key,name in [('Paddock_gate','F01'),('Bush_track','F02')]:
 row=data[key];x,y=row['pos_cm'];tx,ty=row['target_cm']
 pos=u.Vector(x,y,ground.height(x,y)+170);target=u.Vector(tx,ty,ground.height(tx,ty)+row.get('target_up_cm',350))
 label='LidarAtmosphere_'+name
 cam=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None) or actors.spawn_actor_from_class(u.CameraActor,pos)
 cam.set_actor_label(label);cam.set_actor_location(pos,False,True);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
 cam.camera_component.set_field_of_view(68);cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
 views.append(dict(view=name,actor=cam.get_name(),position=[pos.x,pos.y,pos.z],target=[target.x,target.y,target.z],fov=68,description=key))
(qa/'cameras.json').write_text(json.dumps(views,indent=2))
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
print('ATMOSPHERE_VIEWS_READY')
