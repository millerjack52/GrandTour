import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04');bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Safari_Review.blend'));s=bpy.context.scene;body=bpy.data.objects['Porsche original body - locally repaired'];root=bpy.data.objects['Porsche | ROOT'];s.frame_set(1)
def tree(o):
 dg=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();tr=BVHTree.FromPolygons([ev.matrix_world@v.co for v in me.vertices],[list(t.vertices) for t in me.loop_triangles],all_triangles=True);ev.to_mesh_clear();return tr
def coords(o):return [o.matrix_world@v.co for v in o.data.vertices]
def bounds(o):
 p=coords(o);return [[min(v[k] for v in p) for k in range(3)],[max(v[k] for v in p) for k in range(3)]]
def triangles(o):o.data.calc_loop_triangles();return len(o.data.loop_triangles)
rep={'mesh_checks':{},'wheel_motion':[],'interior_body_contacts':{},'seat_glass_contacts':{},'floor_coverage':{},'collision_proxies':[],'limits':'Static modelling review and sampled movement. Final export and Unreal validation await user review.'}
colnames=['01 Exterior','02 Glazing','03 Interior','04 Wheels and running gear','05 Safari equipment'];objs=[o for n in colnames for o in bpy.data.collections[n].objects if o.type=='MESH']
for o in objs:
 bm=bmesh.new();bm.from_mesh(o.data);rep['mesh_checks'][o.name]={'triangles':triangles(o),'boundary':sum(e.is_boundary for e in bm.edges),'overconnected':sum(len(e.link_faces)>2 for e in bm.edges),'zero_area':sum(f.calc_area()<1e-12 for f in bm.faces),'uv':bool(o.data.uv_layers),'bounds':bounds(o)};bm.free()
bt=tree(body);gl=[tree(o) for o in bpy.data.collections['02 Glazing'].objects if o.type=='MESH' and 'surround' not in o.name];tubs=[(o.name,tree(o)) for c in ['03 Interior','04 Wheels and running gear'] for o in bpy.data.collections[c].objects if 'wheelhouse' in o.name]
for o in bpy.data.collections['03 Interior'].objects:
 if o.type!='MESH':continue
 if any(k in o.name for k in ['cushion','backrest','headrest','folding backrest','small seat']):
  tr=tree(o);hits=bt.overlap(tr)
  if hits:rep['interior_body_contacts'][o.name]=len(hits)
  gh=sum(len(g.overlap(tr)) for g in gl)
  if gh:rep['seat_glass_contacts'][o.name]=gh
floor=tree(bpy.data.objects['Cabin | continuous carpet pan'])
for name in ['Driver | cushion','Passenger | cushion']+[o.name for o in bpy.data.collections['03 Interior'].objects if 'small seat' in o.name]:
 ob=bpy.data.objects[name];lo,hi=bounds(ob);miss=0
 for i in range(15):
  for j in range(15):
   p=Vector((lo[0]+(hi[0]-lo[0])*(i+.5)/15,lo[1]+(hi[1]-lo[1])*(j+.5)/15,lo[2]-.002))
   miss+=floor.ray_cast(p,Vector((0,0,-1)),.35)[0] is None
 rep['floor_coverage'][name]={'samples':225,'misses':miss}
dash_trees=[tree(bpy.data.objects[n]) for n in ['Dashboard | continuous padded shell','Dashboard | windscreen-fitted scuttle pad']]
samples=0;exposed=[];outside_aperture=[];windscreen_tree=tree(bpy.data.objects['Windscreen'])
for i in range(25):
 for j in range(11):
  x=-.60+1.2*i/24;y=-.67+.27*j/10;p=Vector((x,y,1.159));dh=[t.ray_cast(p,Vector((0,0,-1)),.30) for t in dash_trees];heights=[h[0].z for h in dh if h[0] is not None]
  if not heights:continue
  samples+=1;h=bt.ray_cast(p,Vector((0,0,-1)),.30)
  if h[0] is not None and h[0].z>max(heights)+.001:
   record=[x,y,h[0].z-max(heights)]
   if windscreen_tree.ray_cast(Vector((x,y,1.8)),Vector((0,0,-1)),.8)[0] is not None:exposed.append(record)
   else:outside_aperture.append(record)
rep['dashboard_source_intrusions']={'samples':samples,'exposed':exposed,'outside_glazing_aperture':outside_aperture,'scope':'Body above fitted dashboard beneath the windscreen; external cowl points separately reported'}
for steer in [-22,-18,-15,-10,-5,0,5,10,15,18,22]:
 for travel in [-.025,0,.015]:
  root['steering_degrees']=steer;root['suspension_m']=travel;root.update_tag();s.frame_set(s.frame_current+1);bpy.context.view_layer.update();hit={}
  for tag in ['FL','FR','RL','RR']:
   for ob in bpy.data.collections['04 Wheels and running gear'].objects:
    if ob.name.startswith('Wheel_'+tag) and ('Tyre' in ob.name or 'Tread' in ob.name):
     wt=tree(ob);pairs=bt.overlap(wt)
     if pairs:hit[ob.name]=len(pairs)
     for name,tb in tubs:
      pairs=tb.overlap(wt)
      if pairs:hit[ob.name+' / '+name]=len(pairs)
  rep['wheel_motion'].append({'steering_deg':steer,'travel_m':travel,'body_intersections':hit})
root['steering_degrees']=0.;root['suspension_m']=0.;root.update_tag();s.frame_set(1);bpy.context.view_layer.update()
with bpy.data.libraries.load('C:/GrandTour/Art/Export/VehicleTools/porsche-tidy-v03/Porsche_Tidy.blend',link=False) as (a,b):b.objects=['Porsche original body - locally repaired']
base=b.objects[0];s.collection.objects.link(base);base.hide_render=True;base.hide_set(True);bc=coords(base);cc=coords(body)
dirs=[Vector((math.cos(y)*math.cos(e),math.sin(y)*math.cos(e),math.sin(e))) for y in [math.radians(k) for k in range(0,360,10)] for e in [math.radians(k) for k in [-60,-30,0,30,60,90]]]
rep['body_support_change_max_m']=max(abs(max(p.dot(d) for p in bc)-max(p.dot(d) for p in cc)) for d in dirs)
rep['total_lod0_triangles']=sum(triangles(o) for o in objs);rep['mesh_count']=len(objs)
rep['collision_proxies']=[o.name for o in bpy.data.collections['07 Collision proxies'].objects]
rep['lod_triangles']={c.name:sum(triangles(o) for o in c.objects if o.type=='MESH') for c in bpy.data.collections if c.name.startswith('LOD')}
rep['static_failures']={'nonmanifold_overconnected_objects':[n for n,c in rep['mesh_checks'].items() if c['overconnected']],'degenerate_objects':[n for n,c in rep['mesh_checks'].items() if c['zero_area']],'missing_uv_objects':[n for n,c in rep['mesh_checks'].items() if not c['uv']]}
rep['wheel_world_centres']={tag:list(bpy.data.objects['Roll | '+tag].matrix_world.translation) for tag in ['FL','FR','RL','RR']}
(O/'verification.json').write_text(json.dumps(rep,indent=2));print(json.dumps({k:v for k,v in rep.items() if k!='mesh_checks'},indent=2))
