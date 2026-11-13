import bpy,json,importlib.util
from pathlib import Path
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02/Porsche_Preserved_Repair.blend')
r=[]
for o in bpy.data.collections['Porsche - repaired original components'].objects:
 if o.type!='MESH' or o.name.startswith('Wheel_'):continue
 ps=[o.matrix_world@v.co for v in o.data.vertices]
 r.append({'name':o.name,'island':o.get('source_island'),'n':len(ps),'lo':[min(p[k] for p in ps) for k in range(3)],'hi':[max(p[k] for p in ps) for k in range(3)]})
Path('C:/GrandTour/Art/Export/VehicleTools/porsche-tidy-v03/inventory.json').write_text(json.dumps(r,indent=2))
print('LIBRARIES',[(x, bool(importlib.util.find_spec(x))) for x in ['scipy','shapely','numpy']])
