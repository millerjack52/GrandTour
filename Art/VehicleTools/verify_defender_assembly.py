import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from defender_coverage import inspect
P=Path('C:/GrandTour/Art/Export/VehicleTools/defender-assembly-v02')
bpy.ops.wm.open_mainfile(filepath=str(P/'Defender_Assembly.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('RET |','Rebuilt')) and not o.hide_render]
dg=bpy.context.evaluated_depsgraph_get();bounds={};trees={};bad=[];triangles=0
for o in objects:
 bm=bmesh.new();bm.from_mesh(o.data)
 invalid={'degenerate':sum(f.calc_area()<1e-12 for f in bm.faces),'loose':sum(not v.link_faces for v in bm.verts),'overconnected':sum(len(e.link_faces)>2 for e in bm.edges)}
 if any(invalid.values()):bad.append((o.name,invalid))
 bm.free();ev=o.evaluated_get(dg);me=ev.to_mesh();v=[o.matrix_world@p.co for p in me.vertices];f=[tuple(p.vertices) for p in me.polygons]
 assert all(math.isfinite(c) for p in v for c in p)
 trees[o.name]=BVHTree.FromPolygons(v,f)
 bounds[o.name]=[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]]
 triangles+=sum(len(p)-2 for p in f);ev.to_mesh_clear()
collisions=[]
for corner,side,axle in [('LF','L','Front'),('RF','R','Front'),('LR','L','Rear'),('RR','R','Rear')]:
 tyre=trees['Rebuilt tyre | '+corner]
 for n in ['RET | '+side+' '+axle+' connected wheelhouse','RET | '+side+' '+axle+' arch flare','RET | Full width fitted floor','RET | '+side+' sill inner upstand']:
  overlap=tyre.overlap(trees[n])
  if overlap:collisions.append({'wheel':corner,'part':n,'intersections':len(overlap)})
report={'coverage':inspect(objects),'mesh_errors':bad,'static_tyre_intersections':collisions,'meshes':len(objects),'evaluated_triangles':triangles}
(P/'verification.json').write_text(json.dumps(report,indent=2))
print('GEOMETRY',json.dumps({k:v for k,v in report.items() if k!='coverage'}))
assert not bad,bad
assert report['coverage']['uncovered']==0
assert not collisions,collisions
# Reimport and rerun coverage so export normals/modifiers/selection cannot silently remove a repair.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'Defender_Assembly.glb'))
got=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert len(got)==len(objects),(len(got),len(objects))
maximum=0
for o in got:
 v=[o.matrix_world@p.co for p in o.data.vertices]
 bb=[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]]
 maximum=max(maximum,max(abs(bb[j][i]-bounds[o.name][j][i]) for j in range(2) for i in range(3)))
assert maximum<.0001,maximum
exported=inspect(got);assert exported['uncovered']==0,exported
report['export_coverage']=exported;report['export_bounds_max_error_m']=maximum
report['status']='PASS: tested static assembly coverage, tyre fit, base meshes and GLB roundtrip'
report['not_certified']=['Steering/suspension travel','Opening panel sweep','UVs/textures (deferred)','LOD/collision assets and Unreal gameplay validation']
(P/'verification.json').write_text(json.dumps(report,indent=2))
print('VERIFIED',len(got),triangles,maximum)
