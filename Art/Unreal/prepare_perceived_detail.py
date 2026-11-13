import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_first_section as section
QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail';QA.mkdir(exist_ok=True)
actors=u.get_editor_subsystem(u.EditorActorSubsystem);mel=u.MaterialEditingLibrary
report=dict(snapshot=section.snapshot(),outside=section.outside_snapshot(),materials={})
for name in ['M_BankLeaf','M_BankSurface']:
 m=u.load_asset(section.DEST+'/'+name)
 report['materials'][name]=[dict(type=n.get_class().get_name(),desc=str(n.get_editor_property('desc'))) for n in mel.get_material_expressions(m)]
views=json.loads((ROOT/'Saved/LidarAuthoringQA/Atmosphere/cameras.json').read_text())
pos=u.Vector(-46500,-32300,4770);target=u.Vector(-46000,-31800,4880)
cam=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='PD_D01'),None) or actors.spawn_actor_from_class(u.CameraActor,pos)
cam.set_actor_label('PD_D01');cam.set_actor_location(pos,False,True);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
cam.camera_component.set_field_of_view(68);cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
views.insert(0,dict(view='D01',actor=cam.get_name(),position=[pos.x,pos.y,pos.z],target=[target.x,target.y,target.z],fov=68))
(QA/'cameras.json').write_text(json.dumps(views,indent=2))
for path in ['/ImpostorBaker/BP/BP_Generate_ImpostorSprites','/ImpostorBaker/BP/EUW_Impostor_Editor','/ImpostorBaker/BP/EUW_Generate_Impostor_using_Preset']:
 try:
  cls=u.EditorAssetLibrary.load_blueprint_class(path);obj=u.get_default_object(cls)
  report[path]=[x for x in dir(obj) if any(k in x.lower() for k in ['impost','render','bake','save','generat','preset','frame','texture','static_mesh'])]
 except Exception as e:report[path]=str(e)
(QA/'survey.json').write_text(json.dumps(report,indent=2))
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
print('PD_PREPARED')
