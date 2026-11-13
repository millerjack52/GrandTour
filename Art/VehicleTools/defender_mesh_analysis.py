import bpy,bmesh,json
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/defender-tripo-v01')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Defender_Source_Inspection.blend'))
o=bpy.data.objects['Tripo_Defender_Source'];bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bm.verts.ensure_lookup_table();todo=set(bm.verts);islands=[]
while todo:
 seed=min(todo,key=lambda v:v.index);todo.remove(seed);seen={seed};q=[seed]
 while q:
  v=q.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in todo:todo.remove(w);seen.add(w);q.append(w)
 islands.append(seen)
islands.sort(key=lambda vs:(-len(vs),sum(v.co.x for v in vs)/len(vs)))
records=[]
for i,vs in enumerate(islands):
 verts=sorted(vs,key=lambda v:v.index);mp={v:k for k,v in enumerate(verts)};fs={f for v in vs for f in v.link_faces}
 records.append(dict(id=i,vertices=[list(v.co) for v in verts],normals=[list(v.normal) for v in verts],faces=[[mp[v] for v in f.verts] for f in fs],bounds=[[min(v.co[k] for v in vs) for k in range(3)],[max(v.co[k] for v in vs) for k in range(3)]],boundary_edges=sum(e.is_boundary for e in {e for v in vs for e in v.link_edges})))
(OUT/'island-geometry.json').write_text(json.dumps(records))
print('ISLANDS',len(records),'body',len(records[0]['vertices']),'boundaries',records[0]['boundary_edges'])
