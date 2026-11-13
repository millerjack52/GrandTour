import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-prepared-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_Safari.blend'))
body=bpy.data.objects.get('Body | source silhouette, repaired apertures');sc=bpy.context.scene
print('HOOD',[(p.index,tuple(round(c/4.5,4) for c in p.center),tuple(round(c,3) for c in p.normal),p.material_index) for p in body.data.polygons if -.4<p.center.y/4.5<-.28 and abs(p.center.x/4.5)<.15 and p.center.z/4.5>.15][:80])
for m in body.modifiers:m.show_render=False
sc.render.filepath=str(P/'no-weighted.png');bpy.ops.render.render(write_still=True)
for o in sc.objects:
 if o.type in ['MESH','CURVE'] and o!=body:o.hide_render=True
sc.display.shading.color_type='SINGLE';sc.display.shading.single_color=(.6,.6,.6)
sc.render.filepath=str(P/'body-isolated.png');bpy.ops.render.render(write_still=True)
