import bpy
from pathlib import Path
out=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-articulation-v08');bpy.ops.wm.open_mainfile(filepath=str(out/'Pathfinder_Articulation.blend'));sc=bpy.context.scene;r=bpy.data.objects['GT | Pathfinder controls']
for k in ['left_front_door','right_front_door','left_rear_door','right_rear_door']:r[k]=55.
r.update_tag();sc.frame_set(1);bpy.context.view_layer.update();sc.camera=bpy.data.objects['Review | top'];sc.camera.data.ortho_scale*=1.5;sc.render.resolution_x=1200;sc.render.resolution_y=1200;sc.cycles.samples=32;sc.render.filepath=str(out/'open-top.png');bpy.ops.render.render(write_still=True)
