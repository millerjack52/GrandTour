import bpy
from pathlib import Path
from mathutils import Vector
out=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-expedition-v01')
bpy.ops.wm.open_mainfile(filepath=str(out/'Ferrari288_Expedition.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100
cam=s.camera;cam.data.type='ORTHO';cam.data.ortho_scale=5.5
for name,pos,target in [('side',(7,0,1.1),(0,0,1.1)),('front',(0,-7,1.1),(0,0,1.1)),('top',(0,0,8),(0,0,0))]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
