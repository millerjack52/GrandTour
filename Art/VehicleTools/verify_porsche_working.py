import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-working-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Assembly.blend'))
sc=bpy.context.scene;parts=bpy.data.collections['Porsche - separated assembly'];body=bpy.data.objects['Body_and_cabin']
def mesh_bvh(o):
 o.data.calc_loop_triangles();vs=[o.matrix_world@v.co for v in o.data.vertices];return BVHTree.FromPolygons(vs,[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
bodytree=mesh_bvh(body);meshes=[o for o in parts.objects if o.type=='MESH'];report={'source_sha256':hashlib.sha256(Path('C:/Users/mille/Downloads/porshceoffroadtripo.glb').read_bytes()).hexdigest(),'topology':{},'static_wheels':[]}
for o in meshes:
 bm=bmesh.new();bm.from_mesh(o.data)
 report['topology'][o.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'overconnected_edges':sum(len(e.link_faces)>2 for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-12 for f in bm.faces)};bm.free()
for name in ['FL','FR','RL','RR']:
 root=bpy.data.objects['Wheel_'+name];t=bpy.data.objects[root.name+'_Tyre'];tr=bpy.data.objects[root.name+'_Tread']
 report['static_wheels'].append({'name':root.name,'centre_m':list(root.location),'tyre_body_overlapping_tri_pairs':len(bodytree.overlap(mesh_bvh(t))),'tread_body_overlapping_tri_pairs':len(bodytree.overlap(mesh_bvh(tr)))})
points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices];bounds=([min(p[k] for p in points) for k in range(3)],[max(p[k] for p in points) for k in range(3)])
report['bounds_m']=bounds;report['triangles']=sum(len(o.data.loop_triangles) for o in meshes);report['mesh_count']=len(meshes)
report['status']='WORKING CLEANUP - NOT GAME READY'
report['remaining']=['Body still retains donor topology and rough arch/window borders','Windscreen/rear/quarter glazing still uses opaque donor texture','Body panels remain a shared body mesh; accessories, interior and wheels are separated','No finished cockpit, opening panel articulation, steering/suspension sweep, LOD, collision or Unreal test']
# The exported assembly must contain the same geometry, scale and no hidden reference.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/'Porsche_Assembly.glb'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];vs=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
rb=([min(p[k] for p in vs) for k in range(3)],[max(p[k] for p in vs) for k in range(3)])
for o in objects:o.data.calc_loop_triangles()
report['roundtrip']={'mesh_count':len(objects),'triangles':sum(len(o.data.loop_triangles) for o in objects),'max_bounds_error_m':max(abs(bounds[j][k]-rb[j][k]) for j in range(2) for k in range(3)),'contains_reference':any('REFERENCE' in o.name for o in objects)}
assert report['roundtrip']['mesh_count']==len(meshes)
assert report['roundtrip']['max_bounds_error_m']<1e-4
assert not report['roundtrip']['contains_reference']
(P/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='topology'},indent=2))

