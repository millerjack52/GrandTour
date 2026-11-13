import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path('C:/GrandTour'); OUT=ROOT/'Saved/WorkshopQA';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Art/Export/VehicleTools/rr-wheels-tyres-v04/RangeRover_Wheel_Fit.blend'))
dg=bpy.context.evaluated_depsgraph_get(); vs=[];fs=[];bounds={}
for o in bpy.context.scene.objects:
 if o.type!='MESH' or o.name.lower().startswith('wheel'):continue
 e=o.evaluated_get(dg);m=e.to_mesh();v=[o.matrix_world@p.co for p in m.vertices];start=len(vs)
 bounds[o.name]=[[min(p[i] for p in v),max(p[i] for p in v)] for i in range(3)]
 vs+=v;fs += [tuple(start+i for i in f.vertices) for f in m.polygons];e.to_mesh_clear()
bt=BVHTree.FromPolygons(vs,fs);records=[]
# Conservative closed tyre envelope includes the tread peaks; avoids missing a collision in tread gaps.
with bpy.data.libraries.load(str(ROOT/'Art/Export/VehicleTools/rr-wheels-tyres-v04/GT_RangeRover_Wheel_Components.blend')) as (src,dst):
 dst.collections=[n for n in src.collections if n.startswith('TYRE |')]
vv=[]
for c in dst.collections:
 bpy.context.scene.collection.children.link(c)
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
for c in dst.collections:
 for o in c.objects:
  if o.type!='MESH':continue
  e=o.evaluated_get(dg);m=e.to_mesh();vv += [v.co.copy() for v in m.vertices];e.to_mesh_clear()
bm=bmesh.new()
for v in vv:bm.verts.new(v)
bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
bm.verts.ensure_lookup_table();bm.verts.index_update();verts=[v.co.copy() for v in bm.verts];faces=[tuple(v.index for v in f.verts) for f in bm.faces];bm.free()
spec=json.loads((ROOT/'Art/Export/VehicleTools/rr-wheels-tyres-v04/spec.json').read_text())
for c in spec['measured_hub_centres_m']:
 for bump in [i*.01 for i in range(-21,1)]+([.025] if c[1]>0 else [])+[.12]:
  for steer in (list(range(-35,36,5)) if c[1]<0 else [0]):
   tr=Matrix.Translation(Vector(c)+Vector((0,0,bump)))@Matrix.Rotation(math.radians(steer),4,'Z')
   hits=BVHTree.FromPolygons([tr@v for v in verts],faces).overlap(bt)
   records.append(dict(centre=c,bump=bump,steer=steer,hits=len(hits)))
active=[r for r in records if r['bump']!=.12]
ok=all(r['hits']==0 for r in active)
(OUT/'suspension-clearance-scan.json').write_text(json.dumps(dict(ok=ok,bounds=bounds,records=records,
 scope='Convex hull enclosing all three actual tyre models against evaluated source body. 10mm vertical increments, 5deg steering increments, rear 25mm bump limit; includes old 120mm bump negative control. Discrete sampling, not continuous certification.'),indent=2))
print('Colliding poses by bump', {b:sum(r['hits']>0 for r in records if r['bump']==b) for b in sorted(set(r['bump'] for r in records))})
assert ok,'Unsafe kit clearance; see report'
