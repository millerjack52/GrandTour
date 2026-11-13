import unreal as u,json
from pathlib import Path
p='/Game/GrandTour/Vehicles/GraphicAdventure/Finished/BP_GraphicAdventure'
bp=u.EditorAssetLibrary.load_asset(p);pawn=u.get_default_object(bp.generated_class())
pawn.set_editor_property('driver_eye_offset',u.Vector(-25,-43.2,157))
for camera in pawn.get_components_by_class(u.CameraComponent):
 if camera.get_name()=='DriverCamera':camera.set_field_of_view(100.)
assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
f=Path(u.Paths.project_dir()).resolve()/'Art/Export/VehicleTools/graphic-adventure-unreal-v02/unreal-import-report.json'
r=json.loads(f.read_text());r.update(driver_eye_cm=[-25,-43.2,157],driver_horizontal_fov=100);f.write_text(json.dumps(r,indent=2))
u.log('GA_COCKPIT_CAMERA_UPDATED')
