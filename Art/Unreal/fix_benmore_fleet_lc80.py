import unreal as u,json,hashlib
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet')
report=json.loads((OUT/'placement-report.json').read_text());assert report['ok']
les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(report['map'])
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
a=next(a for a in actors if a.get_actor_label()=='Benmore_Fleet_LandCruiser80')
row=next(c for c in report['cars'] if c['name']=='LandCruiser80')
c=a.get_component_by_class(u.SkeletalMeshComponent)
# Socket transforms in actor space provide the reference pose independently
# of the root collision box used by component bounds.
bottom=min(c.get_socket_transform(b,u.RelativeTransformSpace.RTS_ACTOR).translation.z-41.5 for b in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR'])
assert abs(bottom)<1,bottom
delta=row['local_bottom_cm']-bottom
a.set_actor_location(a.get_actor_location()+a.get_actor_up_vector()*delta,False,True)
row['location']=a.get_actor_location().to_tuple();row['local_bottom_cm']=bottom
assert les.save_current_level()
report['corrections']=['LC80 grounded from wheel bones and tyre radius; skeletal collision bounds excluded its wheels.']
report['saved_sha256']=hashlib.sha256(Path('C:/GrandTour/Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap').read_bytes()).hexdigest()
(OUT/'placement-report.json').write_text(json.dumps(report,indent=2))
p=Path('C:/GrandTour/Art/Unreal/review_benmore_fleet.py');exec(compile(p.read_text(),str(p),'exec'))
