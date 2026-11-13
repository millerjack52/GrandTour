import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04')
A=json.loads(Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01/islands.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Exterior.blend'))
dg=bpy.context.evaluated_depsgraph_get();body=bpy.data.objects['Prado | source-fitted body']
preserved=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or 'source_component' not in o or o.name.startswith('Glass |'):continue
 idx=o['source_component']
 if idx in [224,233,234,236,237,240]:continue
 kd=KDTree(len(A[idx]['verts']))
 for i,v in enumerate(A[idx]['verts']):kd.insert(Vector(v)*5,i)
 kd.balance();dist=max(kd.find(o.matrix_world@v.co)[2] for v in o.data.vertices)
 assert dist<.00001,(o.name,dist)
 preserved.append({'object':o.name,'source_component':idx,'max_vertex_displacement_m':dist})
def tree(o):
 ob=o.evaluated_get(dg);me=ob.to_mesh();v=[ob.matrix_world@v.co for v in me.vertices];p=[list(p.vertices) for p in me.polygons];t=BVHTree.FromPolygons(v,p);ob.to_mesh_clear();return t
bt=tree(body);clearance=[]
for o in bpy.data.collections['03 Road wheels'].objects:
 if o.type=='MESH' and ('tyre carcass' in o.name or 'all-terrain tread' in o.name):
  intersections=len(bt.overlap(tree(o)));clearance.append({'object':o.name,'body_surface_intersections':intersections})
  assert intersections==0,(o.name,intersections)
top=[];triangles=0
for o in bpy.context.scene.objects:
 if o.type!='MESH' or o.name.startswith('REFERENCE'):continue
 ev=o.evaluated_get(dg);me=ev.to_mesh();triangles+=sum(len(p.vertices)-2 for p in me.polygons);bm=bmesh.new();bm.from_mesh(me)
 top.append({'object':o.name,'boundary_edges':sum(e.is_boundary for e in bm.edges),'overconnected_edges':sum(len(e.link_faces)>2 for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces)})
 bm.free();ev.to_mesh_clear()
report={'body_and_retained_source_components':preserved,'static_tyre_body_checks':clearance,'evaluated_triangles':triangles,'mesh_audit':top,'scope':'Static exterior only. Source shell still needs a complete topology/assembly pass. No interior, UV, collision, LOD, rig or engine readiness claim.','original_glb_sha256':hashlib.sha256(Path('C:/Users/mille/Downloads/pradotripo.glb').read_bytes()).hexdigest()}
(P/'verification.json').write_text(json.dumps(report,indent=2))
print('PRESERVED',len(preserved),'MAX',max(p['max_vertex_displacement_m'] for p in preserved),'TRIANGLES',triangles)
print('TYRE CLEARANCE',clearance)
print('GLASS', [a for a in top if a['object'].startswith('Glass')])
print('BODY',next(a for a in top if a['object']==body.name))
