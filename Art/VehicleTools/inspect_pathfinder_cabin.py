import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/pathfinder-bonnet-wheels-v05/Pathfinder_Bonnet_Wheels.blend')
r=[]
for o in bpy.context.scene.objects:
 if o.type=='MESH' and any(w in o.name.lower() for w in ['floor','cabin','screen','glass','roof','tub']):
  vs=[o.matrix_world@v.co for v in o.data.vertices];r.append({'name':o.name,'bounds':[[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)],'mats':[m.name if m else None for m in o.data.materials],'vertices':len(vs),'modifiers':[(m.name,m.type) for m in o.modifiers]})
Path('C:/GrandTour/Art/VehicleTools/pathfinder-cabin-inspection.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r,indent=2))

