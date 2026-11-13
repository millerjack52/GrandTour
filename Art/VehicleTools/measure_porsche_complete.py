import json
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-source-v01')
d=json.loads((P/'islands.json').read_text());b=BVHTree.FromPolygons(d[0]['verts'],d[0]['polys'])
print('TOP y, x=0 .08 .125 .15 .17 .19 .21 .23')
for y in [-.45,-.43,-.42,-.4,-.36,-.3,-.2,-.155,-.12,-.08,-.04,0,.04,.08,.12,.16,.20,.24,.28,.32,.36,.4,.43,.45]:
 print(y,[None if (h:=b.ray_cast((x,y,.5),(0,0,-1),.5)[0]) is None else round(h.z,4) for x in [0,.08,.125,.15,.17,.19,.21,.23]])
print('SIDE y, z=.08 .10 .14 .18 .22 .24 .26 .28 .30 .32 .34')
for y in [-.43,-.4,-.35,-.3,-.2,-.155,-.1,-.05,0,.05,.1,.15,.2,.25,.3,.35,.4,.43,.45]:
 print(y,[None if (h:=b.ray_cast((.4,y,z),(-1,0,0),.4)[0]) is None else round(h.x,4) for z in [.08,.1,.14,.18,.22,.24,.26,.28,.3,.32,.34]])
for i,a in enumerate(d[:51]):print('ISLAND',i,a['vertices'],[round(x,4) for x in a['min']],[round(x,4) for x in a['max']])
