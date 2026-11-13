import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-source-v01')
d=json.loads((P/'islands.json').read_text())[0]
b=BVHTree.FromPolygons(d['verts'],d['polys'])
ys=[-.415,-.4,-.38,-.36,-.33,-.30,-.27,-.24,-.21,-.18,-.155]
print('TOP Z: y, x=.11 .13 .15 .17 .19 .205 .22')
for y in ys:
 out=[]
 for x in [.11,.13,.15,.17,.19,.205,.22]:
  h=b.ray_cast((x,y,.40),(0,0,-1),.32)[0];out.append(None if h is None else round(h.z,4))
 print(y,out)
print('SIDE X: y, z=.09 .12 .16 .19 .21 .23')
for y in ys:
 out=[]
 for z in [.09,.12,.16,.19,.21,.23]:
  h=b.ray_cast((.35,y,z),(-1,0,0),.25)[0];out.append(None if h is None else round(h.x,4))
 print(y,out)
