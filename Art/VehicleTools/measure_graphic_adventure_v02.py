import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-source-v01')
d=json.loads((P/'island-geometry.json').read_text())[0];tree=BVHTree.FromPolygons(d['vertices'],d['faces'])
def hit(p,d):
 h=tree.ray_cast(Vector(p),Vector(d))[0]
 return [round(v,6) for v in h] if h is not None else None
out={}
out['rear']=[{'z':z,'hits':[hit((x,.8,z),(0,-1,0)) for x in [0,.1,.16,.19,.21]]} for z in [.139,.15,.16,.175,.18,.19,.20,.22,.24,.25,.26,.27,.28,.29,.30,.308,.32,.35,.4,.424]]
out['hood']=[{'y':y,'hits':[hit((x,y,.40),(0,0,-1)) for x in [0,.08,.14,.18,.20,.21,.218,.225]]} for y in [-.45,-.44,-.42,-.4,-.35,-.30,-.25,-.22,-.20,-.185,-.177]]
out['roof']=[{'y':y,'hits':[hit((x,y,.449),(0,0,-1)) for x in [0,.1,.15,.165,.17,.175,.18,.185]]} for y in [-.125,-.11,-.10,0,.15,.30,.40,.414]]
out['side']=[{'z':z,'hits':[hit((.6,y,z),(-1,0,0)) for y in [-.17,-.1,0,.05,.12,.25,.4]]} for z in [.139,.15,.18,.22,.25,.265,.27,.28,.29,.30,.308,.32,.35,.4,.424]]
(P/'shape-measurements-v02.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
