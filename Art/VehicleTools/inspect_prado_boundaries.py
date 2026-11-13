import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union,nearest_points
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01');Q=Path('C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v01')
A=json.loads((P/'islands.json').read_text())[0];G=json.loads((P/'glass-selections.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(Q/'Prado_Prepared.blend'));o=bpy.data.objects['Prado | source-fitted body']
v=[Vector(p) for p in A['verts']]
for n in ['FrontDoor_L','FrontDoor_R']:
 s=1 if n.endswith('_L') else -1
 poly=unary_union([Polygon([(v[i].y,v[i].z) for i in A['polys'][j]]) for j in G[n]['faces']]).buffer(0)
 print(n)
 for p in o.data.vertices:
  a=p.co/5;pt=Point(a.y,a.z)
  if .14<a.x*s<.177 and poly.contains(pt) and pt.distance(poly.boundary)>.0005:
   print(p.index,list(a),pt.distance(poly.boundary))
bm=bmesh.new();bm.from_mesh(o.data);todo={e for e in bm.edges if e.is_boundary};loops=[]
while todo:
 seed=todo.pop();es={seed};vs=set(seed.verts);q=list(vs)
 while q:
  v=q.pop()
  for e in v.link_edges:
   if e in todo:
    todo.remove(e);es.add(e);w=e.other_vert(v);vs.add(w);q.append(w)
 lo=Vector([min(v.co[k] for v in vs) for k in range(3)])/5;hi=Vector([max(v.co[k] for v in vs) for k in range(3)])/5
 loops.append({'edges':len(es),'closed':all(sum(e in es for e in v.link_edges)==2 for v in vs),'bounds':[list(lo),list(hi)],'diagonal':(hi-lo).length})
print(json.dumps(sorted(loops,key=lambda a:-a['diagonal']),indent=2))
