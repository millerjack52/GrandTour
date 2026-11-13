import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-authored-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Safari_Complete.blend'))
sc=bpy.context.scene
meshes=[o for o in sc.objects if o.type=='MESH' and not o.name.startswith('STUDIO_')]
def tree(o):
 o.data.calc_loop_triangles();return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
def combined(obs):
 vs=[];fs=[]
 for o in obs:
  o.data.calc_loop_triangles();base=len(vs);vs += [o.matrix_world@v.co for v in o.data.vertices];fs += [[base+i for i in t.vertices] for t in o.data.loop_triangles]
 return BVHTree.FromPolygons(vs,fs,all_triangles=True)
report={'scope':'Saved full static modelling assembly','mesh_count':len(meshes),'triangles':sum(len(o.data.loop_triangles) for o in meshes),'topology':{},'self_intersections':{},'static_wheel_collisions':{},'coverage':{}}
for o in meshes:
 o.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(o.data)
 z=sum(f.calc_area()<1e-12 for f in bm.faces);nm=sum(not e.is_manifold for e in bm.edges);lo=sum(not v.link_faces for v in bm.verts)
 if z or nm or lo:report['topology'][o.name]={'nonmanifold_edges':nm,'zero_area_faces':z,'loose_vertices':lo}
 bm.free()
 if o.name.startswith(('Body_','Wheelhouse_','Cabin_full_floor','Cabin_front_bulkhead','Cabin_rear_bulkhead','Glass_')) and 'gasket' not in o.name:
  b=tree(o);tris=o.data.loop_triangles;hits=[]
  for a,c in b.overlap(b):
   if a>=c or set(tris[a].vertices)&set(tris[c].vertices):continue
   hits.append([a,c])
  if hits:report['self_intersections'][o.name]={'count':len(hits),'samples':hits[:12]}
  print('CHECKED',o.name,'self hits',len(hits),flush=True)
report['triangles']=sum(len(o.data.loop_triangles) for o in meshes)
body=[o for o in meshes if o.name.startswith(('Body_','Wheelhouse_','Cabin_full_floor','Rocker','Mudflap','Door inward','Front_overhang','Rear_overhang'))]
trees={o.name:tree(o) for o in body}
for w in meshes:
 if w.name.startswith('Wheel_') and w.name.endswith(('_Tyre','_Tread','_Rim_barrel')):
  bt=tree(w);hits={n:len(bt.overlap(t)) for n,t in trees.items() if bt.overlap(t)}
  if hits:report['static_wheel_collisions'][w.name]=hits
floor=tree(bpy.data.objects['Cabin_full_floor']);miss=[];total=0
for x in [-.70+i*.05 for i in range(29)]:
 for y in [-.56+i*.04 for i in range(30)]:
  total+=1
  if floor.ray_cast((x,y,-.1),(0,0,1),1)[0] is None:miss.append([x,y])
report['coverage']['cabin_floor']={'samples':total,'misses':len(miss),'examples':miss[:8]}
bt=combined(body);miss=[];total=0
for s in [-1,1]:
 for yy in [-.155,.12]:
  for dy in [-.001,-.0005,0,.0005,.001]:
   for z in [.10+i*.005 for i in range(25)]:
    for slope in [-.3,0,.3]:
     total+=1;origin=Vector((s*1.35,(yy+dy)*4.5,z*4.5));di=Vector((-s,slope*.03,0)).normalized()
     if bt.ray_cast(origin,di,.65)[0] is None:miss.append([s,yy,dy,z,slope])
report['coverage']['door_seams']={'samples':total,'misses':len(miss),'examples':miss[:8]}
# Above each wheel opening the inner wall must close the cabin sightline.
miss=[];total=0
for s in [-1,1]:
 for y in [-.29126,.26758]:
  for dy in [-.06,-.03,0,.03,.06]:
   for z in [.10,.12,.14,.16,.18]:
    total+=1
    if bt.ray_cast((s*1.35,(y+dy)*4.5,z*4.5),(-s,0,0),1.0)[0] is None:miss.append([s,y,dy,z])
report['coverage']['wheelhouse_backing']={'samples':total,'misses':len(miss),'examples':miss[:8]}
# Deliberate faults verify these checks detect failures, without changing the saved scene.
fob=bpy.data.objects['Cabin_full_floor'];fob.data.calc_loop_triangles()
badfloor=BVHTree.FromPolygons([(v.co.x*.3,v.co.y,v.co.z) for v in fob.data.vertices],[list(t.vertices) for t in fob.data.loop_triangles],all_triangles=True)
negmiss=sum(badfloor.ray_cast((x,y,-.1),(0,0,1),1)[0] is None for x in [-.70+i*.05 for i in range(29)] for y in [-.56+i*.04 for i in range(30)])
wt=bpy.data.objects['Wheel_FL_Tyre'];wt.data.calc_loop_triangles();badwheel=BVHTree.FromPolygons([wt.matrix_world@v.co+Vector((0,0,.20)) for v in wt.data.vertices],[list(t.vertices) for t in wt.data.loop_triangles],all_triangles=True)
neghits=len(badwheel.overlap(trees['Body_FrontWing_L']))
report['negative_controls']={'floor_scaled_to_30_percent_width_misses':negmiss,'wheel_raised_200mm_intersections':neghits}
assert negmiss>0 and neghits>0,'QA negative control failed to detect injected defect'
glass=[o for o in meshes if o.name.startswith('Glass_') and 'gasket' not in o.name]
report['glazing']={o.name:{'transmission':o.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value,'triangles':len(o.data.loop_triangles)} for o in glass}
report['original_donor_body_present']=any(o.name=='Body_and_cabin' or o.name.startswith('REFERENCE_Porsche') for o in meshes)
report['uv_maps_missing']=[o.name for o in meshes if not o.data.uv_layers]
report['not_validated']=['Opening-panel animation','Steering and suspension sweep','LOD/collision meshes','Unreal setup and driving']
report['status']='PASS' if not any([report['topology'],report['self_intersections'],report['static_wheel_collisions'],report['original_donor_body_present'],report['uv_maps_missing'],any(a['misses'] for a in report['coverage'].values())]) else 'REPAIR_REQUIRED'
(P/'validation-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
