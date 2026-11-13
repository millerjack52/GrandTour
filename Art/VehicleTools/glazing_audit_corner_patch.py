import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01');O=P.parent/'prado-glazing-audit'
A=json.loads((P/'islands.json').read_text())[0];d=json.loads((O/'adjacent-loops.json').read_text())['Windscreen'];me=bpy.data.meshes.new('source');me.from_pydata(A['verts'],[],A['polys']);bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table()
fs={bm.faces[i] for i in d[2]['faces']}
for i in [748,2612]:
 print('CORNER FAN',i,[(f.index,[v.index for v in f.verts],list(f.calc_center_median())) for f in bm.verts[i].link_faces if f not in fs])
 fs.update(bm.verts[i].link_faces)
def loop(fs):
 es={e for f in fs for e in f.edges if sum(g in fs for g in e.link_faces)==1};vs=set(v for e in es for v in e.verts)
 if not all(sum(e in es for e in v.link_edges)==2 for v in vs):return None
 start=min(vs,key=lambda v:(v.co.z,v.co.x));order=[start];prev=None;cur=start
 while True:
  nxt=next(e.other_vert(cur) for e in cur.link_edges if e in es and e.other_vert(cur)!=prev)
  if nxt==start:break
  order.append(nxt);prev,cur=cur,nxt
 if len(order)!=len(vs):return None
 return order
for iteration in range(5):
 es={e for f in fs for e in f.edges if sum(g in fs for g in e.link_faces)==1}
 faces={g for e in es for g in e.link_faces if g not in fs};candidates=[]
 for f in faces:
  c=f.calc_center_median()
  if .125<abs(c.x)<.155 and .386<c.z<.417:
   degree=sum(e in es for e in f.edges);order=loop(fs|{f});path=[(v.co.x,v.co.z) for v in order] if order else []
   poly=Polygon(path) if path else None
   candidates.append((degree,f.index,poly.length if poly else 9,[v.index for v in f.verts]))
 print('ITER',iteration,'loop',len(loop(fs)), 'candidates',sorted(candidates,reverse=True))
 acceptable=[c for c in candidates if c[0]>=2 and c[2]<9]
 if not acceptable:break
 for degree,idx,length,verts in acceptable:fs.add(bm.faces[idx])
order=loop(fs);poly=Polygon([(v.co.x,v.co.z) for v in order]);print('VALID',poly.is_valid,'faces',len(fs),'loop',len(order))
print('TOPCO',[(v.index,list(v.co)) for v in order if v.co.z>.39])
rep={'outer_ring':[{'source_vertex':v.index,'co':list(v.co)} for v in order],
 'surround_source_faces_to_remove':sorted(f.index for f in fs if f.index not in d[0]['faces']),
 'pane_source_faces_already_removed':d[0]['faces'],
 'added_to_depth2':sorted(f.index for f in fs if f.index not in d[2]['faces']),
 'verified_simple_loop':poly.is_valid,
 'construction':'Depth2 plus topcorner ear triangles to remove boundary spikes. Same outer silhouette and position; exact shared sourcevertices.'}
(O/'windscreen-corner-repair-contract.json').write_text(json.dumps(rep,indent=2))
