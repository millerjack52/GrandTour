import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01');O=P.parent/'prado-glazing-audit'
A=json.loads((P/'islands.json').read_text())[0];G=json.loads((P/'glass-selections.json').read_text());me=bpy.data.meshes.new('source');me.from_pydata(A['verts'],[],A['polys']);bm=bmesh.new();bm.from_mesh(me);bm.normal_update();bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table();out={}
for name in ['RearWindow','Windscreen']:
 fs={bm.faces[i] for i in G[name]['faces']};out[name]=[]
 for depth in range(4):
  es={e for f in fs for e in f.edges if sum(g in fs for g in e.link_faces)==1};vs=set(v for e in es for v in e.verts)
  bd=[{'index':v.index,'co':list(v.co),'edges':[[e.other_vert(v).index,list(e.other_vert(v).co)] for e in v.link_edges if e in es]} for v in vs]
  out[name].append({'depth':depth,'faces':sorted(f.index for f in fs),'boundary':bd})
  print(name,depth,len(fs),len(es),[[min(v.co[k] for v in vs) for k in range(3)],[max(v.co[k] for v in vs) for k in range(3)]])
  fs|={g for e in es for g in e.link_faces}
(O/'adjacent-loops.json').write_text(json.dumps(out,indent=2))
print('DONE')
