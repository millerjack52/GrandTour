import bpy
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04')
bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Safari_Review.blend'))
exec(Path('C:/GrandTour/Art/VehicleTools/porsche_rear_glazing_patch.py').read_text())
print(repair_rear_glazing(bpy.data.objects['Porsche original body - locally repaired'],bpy.data.objects['Rear glass'],bpy.data.objects['Rear glass fitted surround']))
s=bpy.context.scene;c=s.camera;c.location=(5,7,3.5);c.rotation_euler=(Vector((0,0,.90))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=5.5;s.render.engine='BLENDER_WORKBENCH';s.render.filepath=str(O/'rear-interface-test.png');bpy.ops.render.render(write_still=True)
