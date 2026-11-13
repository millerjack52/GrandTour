import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-source-v01');O=P.parent/'ferrari288-good-working-v01';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_LowPoly_Source.blend'))
sc=bpy.context.scene;src=next(o for o in sc.objects if o.type=='MESH');me=src.data;matrix=src.matrix_world.copy();normals=[n.vector.copy() for n in me.corner_normals]
bm=bmesh.new();bm.from_mesh(me);layer=bm.faces.layers.int.new('source_face')
for i,f in enumerate(bm.faces):f[layer]=i
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);todo=set(bm.verts);parts=[]
while todo:
 v=todo.pop();vs={v};stack=[v]
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in todo:todo.remove(w);vs.add(w);stack.append(w)
 fs={f for v in vs for f in v.link_faces};parts.append({'faces':sorted(f[layer] for f in fs),'world_bounds':[[min((matrix@v.co)[k] for v in vs) for k in range(3)],[max((matrix@v.co)[k] for v in vs) for k in range(3)]]})
parts.sort(key=lambda p:-len(p['faces']));col=bpy.data.collections.new('Ferrari | preserved source components');sc.collection.children.link(col)
covered=set();report=[]
for k,part in enumerate(parts):
 faceids=part['faces'];covered.update(faceids);polys=[me.polygons[i] for i in faceids];ids=sorted({v for f in polys for v in f.vertices});remap={v:i for i,v in enumerate(ids)};out=bpy.data.meshes.new('Component mesh');out.from_pydata([me.vertices[i].co for i in ids],[],[[remap[v] for v in f.vertices] for f in polys]);out.update()
 for m in me.materials:out.materials.append(m)
 for uf in me.uv_layers:
  uv=out.uv_layers.new(name=uf.name)
  for old,new in zip(polys,out.polygons):
   for a,b in zip(old.loop_indices,new.loop_indices):uv.data[b].uv=uf.data[a].uv
 ns=[]
 for old,new in zip(polys,out.polygons):new.material_index=old.material_index;new.use_smooth=old.use_smooth;ns.extend(normals[i] for i in old.loop_indices)
 out.normals_split_custom_set(ns)
 obj=bpy.data.objects.new('Body | original textured shell' if k==0 else f'Source component {k:02d}',out);col.objects.link(obj);obj.matrix_world=matrix;obj.color=src.color;obj['source_face_ids']=json.dumps(faceids)
 report.append({'object':obj.name,'triangles':len(faceids),'bounds':part['world_bounds']})
missing=sorted(set(range(len(me.polygons)))-covered);assert not missing,('Unassigned source triangles',missing)
# The split must preserve every triangle corner, UV coordinate and source normal.
maxpos=maxuv=maxnormal=0.
for obj in col.objects:
 for old_id,new in zip(json.loads(obj['source_face_ids']),obj.data.polygons):
  old=me.polygons[old_id]
  for ai,bi in zip(old.loop_indices,new.loop_indices):
   av=me.vertices[me.loops[ai].vertex_index].co;bv=obj.data.vertices[obj.data.loops[bi].vertex_index].co
   maxpos=max(maxpos,(av-bv).length);maxuv=max(maxuv,(me.uv_layers[0].data[ai].uv-obj.data.uv_layers[0].data[bi].uv).length);maxnormal=max(maxnormal,(normals[ai]-obj.data.corner_normals[bi].vector).length)
assert maxpos<1e-7 and maxuv<1e-7 and maxnormal<.001,(maxpos,maxuv,maxnormal)
ref=bpy.data.collections.new('REFERENCE | unmodified import');sc.collection.children.link(ref)
for c in list(src.users_collection):c.objects.unlink(src)
ref.objects.link(src);ref.hide_render=True;ref.hide_viewport=True;src.hide_set(True)
# Actual welded boundary loops for subsequent fitted-pane repair.
edges={e for e in bm.edges if e.is_boundary};loops=[]
while edges:
 edge=edges.pop();vs=[edge.verts[0],edge.verts[1]];closed=False
 while True:
  available=[e for e in vs[-1].link_edges if e in edges]
  if not available:break
  e=available[0];edges.remove(e);v=e.other_vert(vs[-1])
  if v==vs[0]:closed=True;break
  vs.append(v)
  if len(vs)>5000:raise RuntimeError('loop limit')
 pts=[matrix@v.co for v in vs];loops.append({'closed':closed,'points':[list(p) for p in pts],'bounds':[[min(p[k] for p in pts),max(p[k] for p in pts)] for k in range(3)]})
bm.free();(O/'boundaries.json').write_text(json.dumps(loops,indent=2));(O/'separation-report.json').write_text(json.dumps({'parts':report,'source_triangles':len(me.polygons),'max_corner_position_change':maxpos,'max_uv_change':maxuv,'max_corner_normal_change':maxnormal,'status':'Components separated. No geometry repair or game readiness claimed.'},indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'Ferrari288_LowPoly_Working.blend'))
print('SEPARATED',len(parts),'POS',maxpos,'UV',maxuv,'NORMAL',maxnormal)
for i,l in enumerate(loops):
 if len(l['points'])>5:print('BOUNDARY',i,len(l['points']),l['closed'],l['bounds'])
