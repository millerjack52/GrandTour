import bpy
from pathlib import Path

folder=Path('C:/GrandTour/Art/Export/VehicleTools/crafted-character-detailed-v05')
bpy.ops.wm.open_mainfile(filepath=str(folder/'Crafted_Utility_Detailed.blend'))
sc=bpy.context.scene
sc.camera=bpy.data.objects['QA | rear low']
# Orthographic rays below the car intersect the infinite studio floor.
# Hide only that presentation object for this diagnostic view; do not save.
bpy.data.objects['Ground'].hide_render=True
sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
sc.render.filepath=str(folder/'rear-low.png')
bpy.ops.render.render(write_still=True)
