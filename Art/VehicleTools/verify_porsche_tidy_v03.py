import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path('C:/GrandTour/Art/Export/VehicleTools');O=R/'porsche-tidy-v03';BASE=R/'porsche-preserved-repair-v02/Porsche_Preserved_Repair.blend'
bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Tidy.blend'));s=bpy.context.scene;body=bpy.data.objects['Porsche original body - locally repaired'];parts=bpy.data.collections['Porsche - repaired original components']
def tree(ob):
 ob.data.calc_loop_triangles();return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[list(t.vertices) for t in ob.data.loop_triangles],all_triangles=True)
current=tree(body);report={'status':'Static construction and source-preservation checks, not game certification','topology':{},'window_contact':{},'tyre_liner_intersections':{},'floor_coverage':{}}
with bpy.data.libraries.load(str(BASE),link=False) as (a,b):b.objects=['Porsche original body - locally repaired']
base=b.objects[0];base.name='Accepted shape reference';s.collection.objects.link(base);base.hide_render=True;base.hide_set(True);bt=tree(base)
dist=[bt.find_nearest(v.co)[3] for v in body.data.vertices];report['body_vertex_to_baseline_max_m']=max(dist)
dirs=[Vector((math.cos(y)*math.cos(e),math.sin(y)*math.cos(e),math.sin(e))) for y in [math.radians(k) for k in range(0,360,10)] for e in [math.radians(k) for k in [-60,-30,0,30,60,90]]]
report['body_support_difference_max_m']=max(abs(max(v.co.dot(d) for v in body.data.vertices)-max(v.co.dot(d) for v in base.data.vertices)) for d in dirs)
spec=json.loads((O/'tidy-report.json').read_text())
for w in spec['windows']:
 ob=bpy.data.objects[w['name']+' fitted surround'];n=w['outer_ring_vertices'];ds=[current.find_nearest(ob.data.vertices[i].co)[3] for i in range(n)]
 report['window_contact'][w['name']]={'sample_count':n,'max_distance_m':max(ds),'samples_over_1mm':sum(d>.001 for d in ds)}
for tag in ['FL','FR','RL','RR']:
 lt=current;hits=[];checked=[]
 for ob in parts.objects:
  if ob.name.startswith('Wheel_'+tag) and ('Tyre' in ob.name or 'Tire' in ob.name or 'tyre' in ob.name.lower() or 'tread' in ob.name.lower()):
   checked.append(ob.name)
   count=len(lt.overlap(tree(ob)))
   if count:hits.append({'object':ob.name,'triangle_pairs':count})
 report['tyre_liner_intersections'][tag]=hits
 assert checked,('No tyre objects checked',tag)
 report.setdefault('tyre_objects_checked',{})[tag]=checked
report['tyre_liner_intersections_scope']='Tyres against retained body/wheelhouse mesh; no duplicate liner inserts'
for ob in parts.objects:
 if ob.get('source_island') not in [10,11]:continue
 p=[ob.matrix_world@v.co for v in ob.data.vertices];lo=Vector([min(v[k] for v in p) for k in range(3)]);hi=Vector([max(v[k] for v in p) for k in range(3)]);missing=[]
 for i in range(12):
  for j in range(12):
   x=lo.x+(hi.x-lo.x)*(i+.5)/12;y=lo.y+(hi.y-lo.y)*(j+.5)/12;origin=Vector((x,y,lo.z-.003))
   if current.ray_cast(origin,Vector((0,0,-1)),.5)[0] is None:missing.append([x,y])
 report['floor_coverage'][ob.name]={'tested':144,'misses':len(missing),'missing_xy':missing}
for ob in parts.objects:
 if ob.type!='MESH':continue
 bm=bmesh.new();bm.from_mesh(ob.data);report['topology'][ob.name]={'verts':len(bm.verts),'faces':len(bm.faces),'boundary':sum(e.is_boundary for e in bm.edges),'overconnected':sum(len(e.link_faces)>2 for e in bm.edges),'zero_area':sum(f.calc_area()<1e-12 for f in bm.faces)};bm.free()
(O/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='topology'},indent=2),flush=True)
def render(name,pos,target,scale):
 c=s.camera;c.location=pos;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=scale;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
s.render.resolution_x=1500;s.render.resolution_y=1100
for ob in parts.objects:
 if ob.name.startswith('Wheel_'):ob.hide_render=True
render('arch-after',(5,-2,1.1),(.75,-1.25,.65),1.6)
render('underside-after',(4,-5,-3),(0,0,.5),5.5)
for ob in parts.objects:
 if ob.name.startswith('Wheel_'):ob.hide_render=False
render('windows-other-side',(-5,2,2.5),(-.65,.15,1.23),2.8)
# Same framing, accepted body above and revised body below; both without accessories.
for ob in parts.objects:ob.hide_render=True
body.hide_render=False;base.hide_render=False;base.hide_set(False);body.location.z=-1.1;base.location.z=1.1
s.display.shading.color_type='SINGLE';s.display.shading.single_color=(.58,.60,.59);s.render.resolution_y=1250
render('body-comparison',(8,0,.9),(0,0,.9),6)
