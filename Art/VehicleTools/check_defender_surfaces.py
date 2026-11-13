import bpy,json
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/defender-separated-v02')
bpy.ops.wm.open_mainfile(filepath=str(P/'Defender_Separated.blend'))
for name in ['Glass | L Front','Glass | L Cargo','Door | L Front','Body | Retained source shell']:
 o=bpy.data.objects[name]
 print(name,'faces',len(o.data.polygons),'normal x/z ranges',[(min(p.normal[i] for p in o.data.polygons),max(p.normal[i] for p in o.data.polygons)) for i in [0,2]])
 print('largefaces',[(p.index,round(p.area,4),list(p.normal)) for p in o.data.polygons if p.area>.02][:12])
for o in bpy.context.scene.objects:
 if o.type=='MESH':
  for m in o.modifiers:m.show_render=False
sc=bpy.context.scene;sc.cycles.samples=16;sc.render.filepath=str(P/'no-thickness.png');bpy.ops.render.render(write_still=True)
