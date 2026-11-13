import bpy
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v07')
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Studio_Review.blend'))
sc=bpy.context.scene;cam=sc.camera
cam.data.type='PERSP';cam.data.lens=20;cam.data.clip_start=.015;cam.location=Vector((.085,-.020,.387))*5;target=Vector((.04,-.17,.285))*5;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/'driver-view-fitted.png');bpy.ops.render.render(write_still=True)
# This derivative changes only the review camera, not the vehicle model.
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Prado_Driver_Review.blend'))
