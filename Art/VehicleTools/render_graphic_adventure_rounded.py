import bpy
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-rounded-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'GraphicAdventure_Rounded.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.threads_mode='FIXED';s.render.threads=10;s.render.resolution_x=1400;s.render.resolution_y=1000
c=s.camera;c.data.type='ORTHO';c.data.ortho_scale=6.2;c.location=(6.2,-8.5,4.5);c.rotation_euler=(Vector((0,.08,1.25))-c.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(P/'studio-quarter.png');bpy.ops.render.render(write_still=True)
