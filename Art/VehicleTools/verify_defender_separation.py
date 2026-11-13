"""Reopen, source-surface preservation, topology and GLB roundtrip checks."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/defender-separated-v07')
bpy.ops.wm.open_mainfile(filepath=str(P/'Defender_Separated.blend'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('SOURCE')]
report={'checks':{},'topology':[],'roundtrip':{}}
refs=[o for o in bpy.data.objects if o.name.startswith('SOURCE')]
verts=[];faces=[]
for o in refs:
 off=len(verts);verts.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend([off+i for i in p.vertices] for p in o.data.polygons)
bvh=BVHTree.FromPolygons(verts,faces)
errors=[];bounds={};total=0
for o in meshes:
 bm=bmesh.new();bm.from_mesh(o.data)
 boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(len(e.link_faces)>2 for e in bm.edges)
 report['topology'].append({'name':o.name,'boundary_edges':boundary,'nonmanifold_edges':nonmanifold})
 bm.free()
 n=o.get('preserved_outer_vertex_count',0)
 if n and not o.name.startswith('Cabin'):
  ds=[bvh.find_nearest(o.matrix_world@v.co)[3] for v in list(o.data.vertices)[:n]]
  errors.append((o.name,max(ds)))
 pts=[o.matrix_world@v.co for v in o.data.vertices]
 bounds[o.name]=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]]
 assert all(math.isfinite(c) and abs(c)<8 for p in pts for c in p),'Non-finite or spike in '+o.name
 total+=sum(len(p.vertices)-2 for p in o.data.polygons)
maxerr=max(v for n,v in errors)
report['checks']['retained_outer_surface_max_error_m']=maxerr
report['checks']['source_surface_checks']=errors
assert maxerr<.0001,('Source shape changed',maxerr)
report['checks']['closed_panel_boundaries']={r['name']:r['boundary_edges'] for r in report['topology'] if r['name'].startswith(('Door |','Bonnet |','Glass |'))}
assert all(v==0 for v in report['checks']['closed_panel_boundaries'].values()),report['checks']['closed_panel_boundaries']
assert all(r['boundary_edges']==0 and r['nonmanifold_edges']==0 for r in report['topology']),[r for r in report['topology'] if r['boundary_edges'] or r['nonmanifold_edges']]
assert len([o for o in meshes if o.name.startswith('Rebuilt tyre')])==5
for corner in ['LF','RF','LR','RR','Spare']:
 tyre=bpy.data.objects['Rebuilt tyre | '+corner];rim=bpy.data.objects['Rebuilt rim barrel | '+corner]
 assert tyre.parent==rim.parent and tyre.parent.name=='Wheel pivot | '+corner
 axis=1 if corner=='Spare' else 0;t=bounds[tyre.name];r=bounds[rim.name]
 assert t[0][axis]<r[0][axis] and t[1][axis]>r[1][axis],corner+' rim protrudes past tyre'
report['checks']['tyre_rim_axial_fit']='PASS five wheels'
report['checks']['mesh_count']=len(meshes);report['checks']['triangles']=total
# The open pose is a visual check of ownership, not an animation collision certificate.
poses={}
for side,sign in [('L',1),('R',-1)]:
 for row in ['Front','Rear']:
  o=bpy.data.objects['Hinge | '+side+' '+row+' door'];poses[o]=o.rotation_euler.copy();o.rotation_euler.z=-sign*math.radians(35)
for name,axis,angle in [('Hinge | Bonnet',0,-35),('Hinge | Rear door',2,35)]:
 o=bpy.data.objects[name];poses[o]=o.rotation_euler.copy();o.rotation_euler[axis]=math.radians(angle)
sc=bpy.context.scene;sc.render.filepath=str(P/'open-panels.png');bpy.ops.render.render(write_still=True)
for o,rot in poses.items():o.rotation_euler=rot
report['checks']['open_pose_render']='open-panels.png'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'Defender_Separated.glb'))
got=[o for o in bpy.context.scene.objects if o.type=='MESH'];report['roundtrip']['mesh_count']=len(got)
assert len(got)==len(bounds),(len(got),len(bounds))
maxround=0
for o in got:
 assert o.name in bounds,o.name
 pts=[o.matrix_world@v.co for v in o.data.vertices]
 bb=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]]
 diff=max(abs(bb[j][i]-bounds[o.name][j][i]) for i in range(3) for j in range(2));maxround=max(maxround,diff)
assert maxround<.0001,maxround
report['roundtrip']['max_bounds_error_m']=maxround
assert not any(o.name.startswith('SOURCE') for o in got)
assert all(bpy.data.objects.get('Wheel pivot | '+c) for c in ['LF','RF','LR','RR','Spare'])
report['status']='PASS'
(P/'verification.json').write_text(json.dumps(report,indent=2))
print('DEFENDER_VERIFY_PASS',len(got),total,maxerr,maxround)
