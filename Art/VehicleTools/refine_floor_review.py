import bpy
from pathlib import Path
folder=Path('C:/GrandTour/Art/Export/VehicleTools/crafted-character-detailed-v06')
bpy.ops.wm.open_mainfile(filepath=str(folder/'Crafted_Utility_Detailed.blend'));sc=bpy.context.scene
for ob in sc.objects:
    if not ob.name.startswith('Floor pan | sill return'):continue
    for v in ob.data.vertices:
        if v.co.z<.50:v.co.x-=.003 if v.co.x>0 else -.003
    mod=ob.modifiers['Sheet thickness'];mod.thickness=.004;mod.offset=0
for key,name in [('underside','QA | floor straight underside'),('underside-quarter','QA | floor oblique'),('quarter','Front quarter | volume review'),('side','Side | fixed reference registration')]:
    sc.camera=bpy.data.objects[name];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
    bpy.data.objects['Ground'].hide_render=key.startswith('underside')
    sc.render.filepath=str(folder/(key+'.png'));bpy.ops.render.render(write_still=True)
bpy.data.objects['Ground'].hide_render=False
sc.camera=bpy.data.objects['Front quarter | volume review'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Crafted_Utility_Detailed.blend'))
