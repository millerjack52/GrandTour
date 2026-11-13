import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
d=json.loads(Path('C:/GrandTour/Art/Export/VehicleTools/defender-tripo-v01/island-geometry.json').read_text())[0]
bvh=BVHTree.FromPolygons(d['vertices'],d['faces'])
for axis,points in [('roof',[(x,y,1) for y in [-.14,-.13,-.10,0,.2,.4,.435] for x in [0,.1,.18,.2,.21]]),('hood',[(x,y,.34) for y in [-.47,-.45,-.4,-.3,-.22,-.205] for x in [0,.08,.11,.16,.19]]),('side',[(1,y,z) for y in [-.1,.1,.4] for z in [.15,.20,.265,.28,.295,.31,.34,.4,.435]]),('rear',[(x,1,z) for x in [0,.14,.20] for z in [.15,.18,.25,.30,.35,.42]])]:
 print(axis)
 direction=(0,0,-1) if axis in ['roof','hood'] else (-1,0,0) if axis=='side' else (0,-1,0)
 for p in points:
  hit,n,i,dist=bvh.ray_cast(Vector(p),Vector(direction))
  print(tuple(round(t,3) for t in p), tuple(round(t,4) for t in hit) if hit else None)
