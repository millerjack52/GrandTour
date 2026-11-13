import bpy
from mathutils import Vector
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-form-repair-v06');O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-shape-recovery-v01/Porsche_Source_Locked.blend')
s=bpy.context.scene;donor=bpy.data.objects['WORKING - original shape unchanged']
for o in s.objects:
 if o.type=='MESH':o.hide_render=o!=donor
donor.hide_render=False;s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.light='STUDIO';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False
s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100;c=s.camera;c.data.type='ORTHO';c.data.ortho_scale=2.3;c.location=(8,.32,1.25);c.rotation_euler=(Vector((0,.32,1.25))-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'source-window-shapes.png');bpy.ops.render.render(write_still=True)
