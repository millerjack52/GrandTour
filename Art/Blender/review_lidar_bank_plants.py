import bpy,math
from mathutils import Vector
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FirstSection')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'bank-plants.blend'))
obs=[o for o in bpy.data.objects if o.type=='MESH' and o.name.endswith('_LOD0')]
for k,o in enumerate(obs):
 o.hide_render=False;o.hide_set(False);o.location=(k%3*3.9,k//3*3.5,0)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.world.color=(.32,.32,.32)
bpy.ops.object.light_add(type='AREA',location=(5,-7,12));bpy.context.object.data.energy=2600;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=8
bpy.ops.object.light_add(type='AREA',location=(-5,8,7));bpy.context.object.data.energy=1900;bpy.context.object.data.size=10
bpy.ops.object.camera_add(location=(22,-20,19));c=bpy.context.object;c.rotation_euler=(Vector((4,5,0))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=19;scene.camera=c
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'plant-forms-review.png');bpy.ops.render.render(write_still=True)
