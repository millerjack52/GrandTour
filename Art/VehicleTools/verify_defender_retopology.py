"""Checks accompany, and do not replace, shaded and wireframe inspection."""
import bpy,bmesh,json,math,hashlib
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/defender-retopology-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Defender_Retopology.blend'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('RET |','Rebuilt'))]
report={'objects':[],'checks':{},'scope':'Exterior geometry and component export only'}
bounds={};total=0;errors=[];dg=bpy.context.evaluated_depsgraph_get()
for o in meshes:
 bm=bmesh.new();bm.from_mesh(o.data)
 bad=[f.index for f in bm.faces if f.calc_area()<1e-12]
 loose=sum(not v.link_faces for v in bm.verts)
 nonmanifold=sum(len(e.link_faces)>2 for e in bm.edges)
 if bad or loose or nonmanifold:errors.append((o.name,bad,loose,nonmanifold))
 bm.free()
 ev=o.evaluated_get(dg);me=ev.to_mesh();pts=[o.matrix_world@v.co for v in me.vertices]
 assert all(math.isfinite(c) and abs(c)<8 for p in pts for c in p),o.name
 bounds[o.name]=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]]
 tris=sum(len(p.vertices)-2 for p in me.polygons);total+=tris
 report['objects'].append({'name':o.name,'base_faces':len(o.data.polygons),'evaluated_triangles':tris,'degenerate_faces':bad,'loose_vertices':loose,'overconnected_edges':nonmanifold})
 ev.to_mesh_clear()
assert not errors,errors
report['checks']['no_degenerate_faces_loose_vertices_overconnected_edges']=True
for side in ['L','R']:
 for row in ['Front','Rear']:
  par=bpy.data.objects['Hinge | '+side+' '+row+' door']
  assert bpy.data.objects['RET | '+side+' '+row+' door skin'].parent==par
  assert bpy.data.objects['RET | '+side+' '+row+' door window frame'].parent==par
for corner in ['LF','RF','LR','RR','Spare']:
 tyre=bpy.data.objects['Rebuilt tyre | '+corner];rim=bpy.data.objects['Rebuilt rim barrel | '+corner]
 assert tyre.parent==rim.parent
 axis=1 if corner=='Spare' else 0;t=bounds[tyre.name];r=bounds[rim.name]
 assert t[0][axis]<r[0][axis] and t[1][axis]>r[1][axis],corner
report['checks']['five_wheel_tyre_rim_fit']=True
report['checks']['door_mesh_parenting']=True
report['mesh_count']=len(meshes);report['evaluated_triangles']=total
report['original_glb_sha256']=hashlib.sha256(Path('C:/Users/mille/Downloads/defender110tripo.glb').read_bytes()).hexdigest()
assert report['original_glb_sha256']=='b61c4e6fc6b75d577ed74054d36ff97133f9584fddf1bf102d30636adc53dd28'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'Defender_Retopology.glb'))
got=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(got)==len(bounds),(len(got),len(bounds))
maxerr=0
for o in got:
 assert o.name in bounds,o.name
 pts=[o.matrix_world@v.co for v in o.data.vertices]
 bb=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]]
 maxerr=max(maxerr,max(abs(bb[j][i]-bounds[o.name][j][i]) for i in range(3) for j in range(2)))
assert maxerr<.0001,maxerr
report['checks']['glb_roundtrip_meshes_and_bounds']=True;report['roundtrip_max_bounds_error_m']=maxerr
report['status']='PASS geometry checks; aesthetic approval and gameplay clearance are separate'
(P/'verification.json').write_text(json.dumps(report,indent=2))
print('VERIFIED',len(got),total,maxerr)
