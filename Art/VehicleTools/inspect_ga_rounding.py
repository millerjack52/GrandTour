import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-interior-v01/GraphicAdventure_Interior.blend')
rows=[]
for o in bpy.context.scene.objects:
 if o.type=='MESH' and o.name.startswith('RET |') and not o.name.startswith('RET | Interior'):
  rows.append({'name':o.name,'v':len(o.data.vertices),'f':len(o.data.polygons),'modifiers':[(m.name,m.type, getattr(m,'width',None),getattr(m,'segments',None)) for m in o.modifiers],'materials':[m.name for m in o.data.materials]})
Path('C:/GrandTour/Art/VehicleTools/ga-rounding-inventory.json').write_text(json.dumps(rows,indent=2))
