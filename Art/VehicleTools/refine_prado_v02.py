"""Local repair of the prepared Prado; never recreates its body silhouette."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
from mathutils.geometry import tessellate_polygon
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon,Point
from shapely.ops import nearest_points
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v01')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v02');OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'Prado_Exterior.blend').exists(),'Preserve saved output'
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Prado_Prepared.blend'))
S=5.;sc=bpy.context.scene;body=bpy.data.objects['Prado | source-fitted body'];report={'body_changes':[],'windows':[],'micro_caps':[],'wheel_webs':[]}
def boundary_loops(me):
 bm=bmesh.new();bm.from_mesh(me);todo={e for e in bm.edges if e.is_boundary};loops=[]
 while todo:
  seed=todo.pop();es={seed};vs=set(seed.verts);q=list(vs)
  while q:
   v=q.pop()
   for e in v.link_edges:
    if e in todo:todo.remove(e);es.add(e);w=e.other_vert(v);vs.add(w);q.append(w)
  if not all(sum(e in es for e in v.link_edges)==2 for v in vs):continue
  ordered=[next(iter(vs))];edge=next(e for e in ordered[0].link_edges if e in es);prev=ordered[0];cur=edge.other_vert(prev)
  while cur!=ordered[0]:
   ordered.append(cur);edge=next(e for e in cur.link_edges if e in es and e.other_vert(cur)!=prev);prev,cur=cur,edge.other_vert(cur)
  loops.append([v.co.copy() for v in ordered])
 bm.free();return loops
loops=boundary_loops(body.data)
for o in list(bpy.data.collections['02 Glass'].objects):
 kd=KDTree(len(o.data.vertices))
 for i,v in enumerate(o.data.vertices):kd.insert(v.co,i)
 kd.balance()
 matched=[loop for loop in loops if len(loop)>=6 and all(kd.find(p)[2]<.03 for p in loop) and sum(kd.find(p)[2]<.0001 for p in loop)>=len(loop)*.7]
 if not matched:
  print('NEAREST LOOPS',o.name,sorted([(len(loop),max(kd.find(p)[2] for p in loop),sum(kd.find(p)[2]<.0001 for p in loop)) for loop in loops],key=lambda q:q[1])[:4],flush=True)
  raise RuntimeError('No body aperture found for '+o.name)
 allv=[];allf=[]
 for loop in matched:
  tris=tessellate_polygon([loop]);start=len(allv);allv+=loop
  for tri in tris:allf.append(tuple(start+(v if isinstance(v,int) else min(range(len(loop)),key=lambda i:(loop[i]-v).length_squared)) for v in tri))
 me=bpy.data.meshes.new(o.name+' | exact aperture surface');me.from_pydata(allv,[],allf);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=3,use_grid_fill=True)
 interior=[v for v in bm.verts if not v.is_boundary]
 for it in range(12):bmesh.ops.smooth_vert(bm,verts=interior,factor=.35,use_axis_x=True,use_axis_y=True,use_axis_z=True)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 expected=Vector((0,-.8,.6)) if 'Windscreen' in o.name else Vector((0,1,.1)) if 'RearWindow' in o.name else Vector((1 if o.name.endswith('_L') else -1,0,.15))
 if sum((f.normal*f.calc_area() for f in bm.faces),Vector()).dot(expected)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=True
 bm.to_mesh(me);bm.free();me.materials.append(bpy.data.materials['Prado | Glass']);o.data=me
 for m in list(o.modifiers):o.modifiers.remove(m)
 m=o.modifiers.new('3.25 mm pane — inward','SOLIDIFY');m.thickness=.00325;m.offset=-1
 report['windows'].append({'name':o.name,'aperture_loops':len(matched),'boundary':'copied directly from body; interpolated boundary vertices remain on original edges','faces':len(me.polygons)})
 # Only tiny folded sill/header points projecting into these two openings move.
 # The outer silhouette, body proportions and complete metal aperture stay fixed.
 if 'FrontDoor' in o.name:
  poly=Polygon([(p.y,p.z) for p in matched[0]]).buffer(0);sgn=1 if o.name.endswith('_L') else -1
  aperture_kd=KDTree(len(matched[0]))
  for i,p in enumerate(matched[0]):aperture_kd.insert(p,i)
  aperture_kd.balance()
  for v in body.data.vertices:
   p=v.co;pt=Point(p.y,p.z)
   if .14*S<p.x*sgn<.177*S and poly.contains(pt) and .0005<pt.distance(poly.boundary)<.0125 and aperture_kd.find(p)[2]>.0001:
    dest=nearest_points(pt,poly.boundary)[1];old=list(p);p.y=dest.x;p.z=dest.y
    report['body_changes'].append({'vertex':v.index,'before_m':old,'after_m':list(p),'reason':'folded source trim tip inside window opening'})
body.data.update()

# Fill only genuinely tiny closed holes. Glass boundaries and broad openings
# are excluded; this does not pretend that remaining source seams are repaired.
for o in [body]+[o for o in sc.objects if o.type=='MESH' and 'source_component' in o and o!=body]:
 bm=bmesh.new();bm.from_mesh(o.data);todo={e for e in bm.edges if e.is_boundary};filled=0
 while todo:
  seed=todo.pop();es={seed};vs=set(seed.verts);q=list(vs)
  while q:
   v=q.pop()
   for e in v.link_edges:
    if e in todo:todo.remove(e);es.add(e);w=e.other_vert(v);vs.add(w);q.append(w)
  if not 3<=len(es)<=12 or not all(sum(e in es for e in v.link_edges)==2 for v in vs):continue
  lo=Vector([min(v.co[k] for v in vs) for k in range(3)]);hi=Vector([max(v.co[k] for v in vs) for k in range(3)])
  if (hi-lo).length>.006*S:continue
  result=bmesh.ops.holes_fill(bm,edges=list(es),sides=12);filled+=len(result['faces'])
 if filled:
  bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);report['micro_caps'].append({'name':o.name,'faces':filled,'maximum_hole_bbox_diagonal_mm':30})
 bm.free()

# Replace the preliminary disconnected spoke strips with closed steel dishes
# and six actual cut vents. Wheel centres, tyres, rim barrels and hubs stay fixed.
wr=json.loads((SRC/'preparation-report.json').read_text())['wheels']
for w in wr:
 name=w['name'];r=w['radius_raw']*S;h=w['width_raw']*S/2;c=Vector(w['center_raw'])*S;spare=name=='Rear spare';sign=1 if spare or c.x>0 else -1
 dish=bpy.data.objects[name+' | vented dish'];old=dish.data
 for m in list(dish.modifiers):dish.modifiers.remove(m)
 def xf(x,y,z):return (y,x,z) if spare else (sign*x,y,z)
 profile=[(h*.47,0),(h*.47,r*.22),(h*.58,r*.478),(h*.58-.010,r*.478),(h*.47-.010,r*.22),(h*.47-.010,0)]
 v=[xf(x,rr*math.cos(t*math.tau/64),rr*math.sin(t*math.tau/64)) for x,rr in profile for t in range(64)]
 f=[(j*64+t,j*64+(t+1)%64,((j+1)%len(profile))*64+(t+1)%64,((j+1)%len(profile))*64+t) for j in range(len(profile)) for t in range(64)]
 me=bpy.data.meshes.new(name+' closed vented dish');me.from_pydata(v,[],f);bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.materials.append(bpy.data.materials['Prado | Wheel']);dish.data=me
 cv=[];cf=[]
 for k in range(6):
  angle=k*math.tau/6+math.pi/6;cy=r*.34*math.cos(angle);cz=r*.34*math.sin(angle);st=len(cv)
  for x in [-h,h]:
   for t in range(16):a=t*math.tau/16;cv.append(xf(x,cy+r*.075*math.cos(a),cz+r*.075*math.sin(a)))
  cf += [tuple(st+t for t in reversed(range(16))),tuple(st+16+t for t in range(16))]+[(st+t,st+(t+1)%16,st+16+(t+1)%16,st+16+t) for t in range(16)]
 cm=bpy.data.meshes.new('vent cutter');cm.from_pydata(cv,[],cf);bm=bmesh.new();bm.from_mesh(cm);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cm);bm.free();co=bpy.data.objects.new('temporary vent cutter',cm);sc.collection.objects.link(co);co.location=c
 bpy.ops.object.select_all(action='DESELECT');dish.select_set(True);bpy.context.view_layer.objects.active=dish
 mod=dish.modifiers.new('Six open circular vents','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=co;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(co,do_unlink=True)
 bevel=dish.modifiers.new('Vent rim radius','BEVEL');bevel.width=.0025;bevel.segments=2;bevel.limit_method='ANGLE'
 bm=bmesh.new();bm.from_mesh(dish.data)
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle()<.6
 report['wheel_webs'].append({'name':name,'nonmanifold_base_edges':sum(not e.is_manifold for e in bm.edges)})
 bm.to_mesh(dish.data);bm.free();mod=dish.modifiers.new('Dish normals','WEIGHTED_NORMAL');mod.keep_sharp=True

sc.render.resolution_x=1600;sc.render.resolution_y=1100;cam=sc.camera
def render(name,c,d,scale=1.2):
 center=Vector(c)*S;cam.location=center+Vector(d)*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*S;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
for n,d in [('side',(3,0,0)),('opposite-side',(-3,0,0)),('front',(0,-3,0)),('rear',(0,3,0)),('top',(0,0,3)),('quarter',(2,-3,1.1)),('rear-quarter',(-2,3,1.0)),('underside',(1,-1,-2))]:render(n,(0,0,.27),d)
render('window-close',(0,-.1,.355),(2,-3,.7),.53)
render('rear-close',(0,.32,.27),(-2,3,.45),.65)
render('wheel-close',(.16,-.28,.13),(3,-1,.2),.32)
render('quarter',(0,0,.27),(2,-3,1.1))
report['status']='Source-preserving exterior review. Full retopology, interior and game preparation remain.'
(OUT/'local-repair-report.json').write_text(json.dumps(report,indent=2))
root=bpy.data.objects['PRADO | working assembly'];root['status']=report['status']
bpy.data.texts.new('V02 LOCAL REPAIRS').write(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Exterior.blend'))
print(json.dumps(report,indent=2))
