"""Preserve source shell visibility inside Unreal, then repeat actual renders."""
import unreal as u
from pathlib import Path
import json

OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-unreal-v01')
MAP='/Game/GrandTour/ArtTests/Prado/L_PradoReview'
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
assert les.load_level(MAP)
m=u.EditorAssetLibrary.load_asset('/Game/GrandTour/Vehicles/Prado/Prado/Materials/M_Prado_Prado_Paint')
assert m
m.set_editor_property('two_sided',True)
assert not u.MaterialEditingLibrary.recompile_material(m)
assert u.EditorAssetLibrary.save_loaded_asset(m)
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
car=next(a for a in actors if a.get_actor_label()=='NC_Prado')
z=car.get_actor_location().z
eye=u.Vector(10,-42.5,193.5+z)
target=u.Vector(85,-20,142.5+z)
cockpit=next(a for a in actors if a.get_actor_label()=='NC_Camera_Prado_Cockpit')
cockpit.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye,target),False)
cockpit.camera_component.set_field_of_view(84)
forward=next((a for a in actors if a.get_actor_label()=='NC_Camera_Prado_CabinForward'),None)
if forward is None:
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    forward=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(eye,u.Rotator(pitch=-12,yaw=0,roll=0),u.Vector(1,1,1)),'NC_Camera_Prado_CabinForward')
assert forward
forward.camera_component.set_field_of_view(90)
forward.camera_component.set_editor_property('constrain_aspect_ratio',False)
assert les.save_current_level()
p=OUT/'unreal-import-report.json'
r=json.loads(p.read_text())
r['interior_culling']={'paint_two_sided':True,'reason':'Preserve source shell backside visibility at pillars and roof from the cockpit; glazing remains single-sided closed geometry.'}
p.write_text(json.dumps(r,indent=2))
exec(compile(Path('C:/GrandTour/Art/Unreal/review_prado.py').read_text(),'review_prado.py','exec'))
