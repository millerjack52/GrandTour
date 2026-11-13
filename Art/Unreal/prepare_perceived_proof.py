import unreal as u,json,math,hashlib,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_first_section as section
QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail';actors=u.get_editor_subsystem(u.EditorActorSubsystem)
def run():
 allactors=actors.get_all_level_actors();forest=next(a for a in allactors if a.get_actor_label()=='LidarStudy_Forest');stand=next(a for a in allactors if a.get_actor_label()=='LidarStudy_PD_Stand')
 source=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_Canopy_0')
 dest=stand.get_components_by_class(u.InstancedStaticMeshComponent)[0]
 assert source.get_editor_property('num_custom_data_floats')==0
 def digest():
  rows=[tuple(round(v,7) for v in section.tfkey(c.get_instance_transform(i,True))) for c in [source,dest] for i in range(c.get_instance_count())]
  return dict(count=len(rows),hash=hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest())
 before=digest()
 for i in range(dest.get_instance_count()):source.add_instance(dest.get_instance_transform(i,True),True)
 dest.clear_instances();selected=[]
 camera_pos=u.Vector(-46415.7081,29792.7362,10766.4043)
 ground=section.GroundSampler(next(a for a in allactors if isinstance(a,u.GTProceduralGround)))
 for i in range(source.get_instance_count()):
  t=source.get_instance_transform(i,True);p=t.translation
  dx,dy=p.x-camera_pos.x,p.y-camera_pos.y;distance=math.hypot(dx,dy)
  if not (3500<distance<35000 and dy>0 and abs(dx/dy)<.68):continue
  top=p.z+1700*t.scale3d.z
  if any(ground.height(camera_pos.x+dx*f,camera_pos.y+dy*f)>camera_pos.z+(top-camera_pos.z)*f-100 for f in [.2,.4,.6,.8]):continue
  selected.append((i,t))
 selected.sort(key=lambda row:(row[1].translation-camera_pos).length_squared())
 selected=selected[:48]
 assert len(selected)==48,len(selected)
 for _,t in selected:dest.add_instance(t,True)
 assert source.remove_instances(sorted([i for i,_ in selected],reverse=True));after=digest();assert before==after,(before,after)
 views=json.loads((QA/'cameras.json').read_text());views=[v for v in views if v['view'] not in ('G01','T01')]
 z=ground.height(-46000,-31800)+max(0,section.S.relief(-46000,-31800))
 centre=tuple(sum([t.translation.x,t.translation.y,t.translation.z+1300*t.scale3d.z][k] for _,t in selected)/len(selected) for k in range(3))
 specs=[('G01',(-46300,-32150,z+210),(-46000,-31800,z+10)),('T01',(-44415,21793,ground.height(-44415,21793)+260),centre)]
 for name,pos,target in specs:
  label='PD_'+name;cam=next((a for a in allactors if a.get_actor_label()==label),None) or actors.spawn_actor_from_class(u.CameraActor,u.Vector(*pos))
  cam.set_actor_label(label);cam.set_actor_location(u.Vector(*pos),False,True);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
  cam.camera_component.set_field_of_view(68);cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
  views.append(dict(view=name,actor=cam.get_name(),position=list(pos),target=list(target),fov=68))
 (QA/'cameras-proof.json').write_text(json.dumps(views,indent=2));(QA/'stand-proof.json').write_text(json.dumps(dict(before=before,after=after,transforms=[section.tfkey(t) for _,t in selected],count=48,custom_data_floats=0),indent=2))
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
