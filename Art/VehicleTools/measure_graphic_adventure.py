import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-source-v01')
d=json.loads((P/'island-geometry.json').read_text())[0];bvh=BVHTree.FromPolygons(d['vertices'],d['faces'])
out={}
for axis,points in [('roof',[(x,y,.46) for y in [-.12,-.1,0,.15,.3,.4,.42,.44] for x in [0,.1,.17,.19,.20]]),('hood',[(x,y,.31) for y in [-.46,-.44,-.40,-.30,-.22,-.18] for x in [0,.08,.16,.20,.22]]),('side',[(1,y,z) for y in [-.1,.1,.4] for z in [.13,.15,.18,.22,.25,.27,.29,.31,.32,.35,.4,.43]]),('rear',[(x,1,z) for x in [0,.15,.20,.22] for z in [.13,.15,.18,.25,.29,.31,.35,.42]])]:
 direction=(0,0,-1) if axis in ['roof','hood'] else (-1,0,0) if axis=='side' else (0,-1,0)
 samples=[]
 for p in points:
  hit,n,i,dist=bvh.ray_cast(Vector(p),Vector(direction));samples.append({'ray':p,'hit':[round(t,5) for t in hit] if hit else None})
 out[axis]=samples
(P/'surface-measurements.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
