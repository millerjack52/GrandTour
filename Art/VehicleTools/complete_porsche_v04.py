"""Complete the accepted Porsche as a review asset, without publishing/exporting it."""
import bpy,bmesh,math,json,hashlib,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from math import sin,cos,pi
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools');OUT=ROOT/'porsche-completion-v04';OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'porsche-tidy-v03/Porsche_Tidy.blend';DEST=OUT/'Porsche_Safari_Review.blend';MAN=OUT/'build-report.json'
if DEST.exists():
 assert MAN.exists() and hashlib.sha256(DEST.read_bytes()).hexdigest()==json.loads(MAN.read_text())['blend_sha256'],'Manual work found; preserve it in a new revision'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));sc=bpy.context.scene
parts=bpy.data.collections['Porsche - repaired original components'];body=bpy.data.objects['Porsche original body - locally repaired']
report={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'scope':'Complete Blender model for user review; export held until approval','repairs':[]}
COL={}
for name in ['01 Exterior','02 Glazing','03 Interior','04 Wheels and running gear','05 Safari equipment','06 Controls','07 Collision proxies','08 Studio']:
 c=bpy.data.collections.new(name);sc.collection.children.link(c);COL[name]=c
EXT=COL['01 Exterior'];GLASS=COL['02 Glazing'];INT=COL['03 Interior'];GEAR=COL['04 Wheels and running gear'];KIT=COL['05 Safari equipment'];RIG=COL['06 Controls'];COLL=COL['07 Collision proxies'];STUDIO=COL['08 Studio']
def move(o,c):
 for x in list(o.users_collection):x.objects.unlink(o)
 c.objects.link(o)
def mat(n,c,rough=.45,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
paint=bpy.data.materials['Porsche ivory enamel'];rubber=bpy.data.materials['Fitted rubber glazing seals'];steel=bpy.data.materials['Original hardware graphite'];glassmat=bpy.data.materials['Porsche clear glass']
cloth=mat('Cabin | warm tobacco leather',(.24,.115,.055),.72);insert=mat('Cabin | woven sand inserts',(.41,.28,.16),.88);dashmat=mat('Cabin | charcoal soft trim',(.029,.036,.034),.82);carpet=mat('Cabin | charcoal carpet',(.045,.05,.046),.96);ivory=mat('Details | warm printed ivory',(.72,.72,.61),.6);silver=mat('Details | satin aluminium',(.48,.51,.52),.3,.8);red=mat('Lights | red lens',(.42,.012,.006),.23);amber=mat('Lights | amber lens',(.88,.19,.008),.25);ochre=mat('Equipment | ochre webbing',(.49,.245,.038),.8)
for m in [cloth,insert,carpet]:
 nt=m.node_tree;n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=190 if m==carpet else 280;n.inputs['Detail'].default_value=2;b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.13;b.inputs['Distance'].default_value=.0005;nt.links.new(n.outputs['Fac'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],nt.nodes.get('Principled BSDF').inputs['Normal'])
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def finish(o,sharp=.75):
 for p in o.data.polygons:p.use_smooth=True
 o.data.set_sharp_from_angle(angle=sharp);return o
def mesh(n,vs,fs,m=paint,c=EXT):
 me=bpy.data.meshes.new(n);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(n,me);c.objects.link(o);me.materials.append(m)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();return finish(o)
def bevel(o,r=.006,n=3):
 active(o);md=o.modifiers.new('Manufactured corner radius','BEVEL');md.width=r;md.segments=n;bpy.ops.object.modifier_apply(modifier=md.name);finish(o)
 md=o.modifiers.new('Planar face normals','WEIGHTED_NORMAL');md.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=md.name);return o
def box(n,p,size,m=steel,c=EXT,r=.006):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=n;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);move(o,c);o.data.materials.append(m)
 return bevel(o,min(r,min(size)*.4)) if r else finish(o)
def tube(n,pts,r=.01,m=steel,c=EXT,closed=False):
 cu=bpy.data.curves.new(n,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=2;cu.use_fill_caps=True;sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,q in zip(sp.points,pts):p.co=(*q,1)
 sp.use_cyclic_u=closed;o=bpy.data.objects.new(n,cu);c.objects.link(o);cu.materials.append(m);active(o);bpy.ops.object.convert(target='MESH');return finish(bpy.context.object)
def cyl(n,p,r,h,m=steel,c=EXT,axis=(0,0,1),num=32):
 bpy.ops.mesh.primitive_cylinder_add(vertices=num,radius=r,depth=h,location=p);o=bpy.context.object;o.name=n;o.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler();o.data.materials.append(m);move(o,c);return bevel(o,min(.002,h*.12),2)
def text(n,value,p,size=.018,m=ivory,c=INT,rot=(pi/2,0,pi)):
 cu=bpy.data.curves.new(n,'FONT');cu.body=value;cu.align_x='CENTER';cu.size=size;cu.extrude=.00015;o=bpy.data.objects.new(n,cu);c.objects.link(o);o.location=p;o.rotation_euler=rot;cu.materials.append(m);active(o);bpy.ops.object.convert(target='MESH');return bpy.context.object
def thick(o,t):
 active(o);md=o.modifiers.new('Physical panel return','SOLIDIFY');md.thickness=t;md.offset=-1;md.use_even_offset=False;bpy.ops.object.modifier_apply(modifier=md.name);return o
def bounds(o):
 ps=[o.matrix_world@v.co for v in o.data.vertices];return Vector([min(p[k] for p in ps) for k in range(3)]),Vector([max(p[k] for p in ps) for k in range(3)])
def tree(o):
 o.data.calc_loop_triangles();return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
def delete(o):bpy.data.objects.remove(o,do_unlink=True)
for o in list(parts.objects):
 if o.type!='MESH':continue
 lo,hi=bounds(o)
 move(o,GEAR if o.name.startswith('Wheel_') else GLASS if ('glass' in o.name.lower() or 'surround' in o.name or o.name=='Windscreen') else KIT if lo.z>1.5 or o.name.startswith(('Rack','Spare','Roof toolcase','Case buckle')) else EXT)
retained=set(o.name for o in sc.objects if o.type=='MESH' and not o.hide_render)
# Delete source interior and fragments by their measured source IDs, not incorrect names.
interior_ids={7,10,11,17,27,28,29,36,41,42,43,46,48,49}
for o in list(EXT.objects):
 if o.get('source_island') in interior_ids or o.get('source_island',0)>50:delete(o)
# Repair tiny tears and fair the original skin locally. No replacement envelope.
original=[v.co.copy() for v in body.data.vertices];bt=tree(body)
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0005);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00005)
bm.verts.ensure_lookup_table();bm.verts.index_update();bm.normal_update()
coords=[v.co.copy() for v in bm.verts];norms=[v.normal.copy() for v in bm.verts];kd=KDTree(len(coords))
for i,p in enumerate(coords):kd.insert(p,i)
kd.balance();moves=[]
# Lock mating boundaries; source irregularity is corrected only inside surfaces.
for v in bm.verts:
 p=coords[v.index];n=norms[v.index]
 if v.is_boundary or p.z<.54 or n.length<.5:continue
 hits=[(j,dist) for q,j,dist in kd.find_range(p,.075) if norms[j].dot(n)>.82]
 if len(hits)<12:continue
 tangent=n.cross(Vector((0,0,1)))
 if tangent.length<.1:tangent=n.cross(Vector((0,1,0)))
 tangent.normalize();bit=n.cross(tangent);delta=[coords[j]-p for j,d in hits]
 a=np.array([[1,q.dot(tangent),q.dot(bit),q.dot(tangent)**2,q.dot(tangent)*q.dot(bit),q.dot(bit)**2] for q in delta]);z=np.array([q.dot(n) for q in delta]);w=np.array([math.exp(-d*d/.003) for j,d in hits]);coef=np.linalg.lstsq(a*np.sqrt(w[:,None]),z*np.sqrt(w),rcond=1e-8)[0]
 shift=float(np.clip(coef[0],-.006,.006))*.75
 v.co+=n*shift;moves.append(abs(shift))
# Fill only compact accidental holes. Large designed apertures stay untouched.
es={e for e in bm.edges if e.is_boundary};filled=0
while es:
 seed=es.pop();group={seed};todo=[seed]
 while todo:
  e=todo.pop()
  for v in e.verts:
   for ee in v.link_edges:
    if ee in es:es.remove(ee);group.add(ee);todo.append(ee)
 vs={v for e in group for v in e.verts};extent=max(max(v.co[k] for v in vs)-min(v.co[k] for v in vs) for k in range(3))
 if extent<.065 and len(group)<80 and all(sum(e in group for e in v.link_edges)==2 for v in vs):
  res=bmesh.ops.holes_fill(bm,edges=list(group),sides=0);filled+=len(res['faces'])
bm.to_mesh(body.data);bm.free();finish(body,1.5)
report['repairs'].append({'part':'Original body','fairing_max_m':max(moves),'small_hole_faces':filled,'method':'Boundary-pinned normal fairing, original source skin retained'})
exec(compile(Path('C:/GrandTour/Art/VehicleTools/porsche_complete_clearance.py').read_text(),'porsche_complete_clearance.py','exec'))
exec(compile(Path('C:/GrandTour/Art/VehicleTools/porsche_complete_cabin_cut.py').read_text(),'porsche_complete_cabin_cut.py','exec'))
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();finish(body,1.4)
# Refit glazing outer mounting row to repaired skin; preserve pane outlines.
bt=tree(body);spec=json.loads((ROOT/'porsche-tidy-v03/tidy-report.json').read_text())
for w in spec['windows']:
 rim=bpy.data.objects[w['name']+' fitted surround'];N=w['outer_ring_vertices'];half=len(rim.data.vertices)//2
 for i in range(N):
  v=rim.data.vertices[i];h=bt.find_nearest(v.co)
  if h[3]<.020:
   d=h[0]-v.co;v.co+=d;rim.data.vertices[half+i].co+=d
 finish(rim,1.4)
bt=tree(body)
# Give the remaining body sheets an actual inward return; exterior coordinates stay fixed.
active(body);skin=body.modifiers.new('Body shell thickness 3 mm','SOLIDIFY');skin.thickness=.003;skin.offset=-1;skin.use_even_offset=False;skin.thickness_clamp=.5;skin.use_thickness_angle_clamp=True;bpy.ops.object.modifier_apply(modifier=skin.name)
finish(body,1.4)
exec(compile(Path('C:/GrandTour/Art/VehicleTools/porsche_rear_glazing_patch.py').read_text(),'porsche_rear_glazing_patch.py','exec'))
report['repairs'].append(repair_rear_glazing(body,bpy.data.objects['Rear glass'],bpy.data.objects['Rear glass fitted surround']))
exec(compile(Path('C:/GrandTour/Art/VehicleTools/porsche_complete_bumper_band.py').read_text(),'porsche_complete_bumper_band.py','exec'))
# Close front/rear bumper reveal tears with a shaped recessed backing ribbon.
# The ribbon is sampled from the accepted skin; it bridges only the panel split.
for sy,label in [(1,'Rear')]:
 ps=[]
 for x in np.linspace(-.93,.93,97):
  z=.642 if sy<0 else .688
  h=bt.ray_cast(Vector((float(x),sy*2.6,z+.016)),Vector((0,-sy,0)),1.6)
  if h[0] is not None:ps.append(h[0])
 vs=[]
 for dz in [-.014,.012]:
  for p in ps:vs.append(p+Vector((0,-sy*.006,dz)))
 n=len(ps)
 if n>20:
  o=mesh(label+' continuous bumper reveal backing',vs,[(i,i+1,n+i+1,n+i) for i in range(n-1)],rubber);thick(o,.009)
# Replace torn source bullbar with same measured extents, continuous bent tube.
for o in list(EXT.objects):
 if o.get('source_island') in {2,22,24,25,34,35,37}:delete(o)
def rounded_loop_xz(cx,y,cz,w,h,r):
 pts=[]
 for x,z,a in [(cx+w/2-r,cz+h/2-r,0),(cx-w/2+r,cz+h/2-r,90),(cx-w/2+r,cz-h/2+r,180),(cx+w/2-r,cz-h/2+r,270)]:
  for k in range(9):
   t=math.radians(a+k*90/8);pts.append((x+r*cos(t),y,z+r*sin(t)))
 return pts
tube('Front protection | bent tube',rounded_loop_xz(0,-2.209,.462,1.70,.285,.09),.029,steel,EXT,True)
for x in [-.51,.51]:
 tube('Front protection | chassis bracket',[(x,-2.205,.37),(x,-1.95,.33),(x,-1.50,.39)],.028,steel,GEAR)
 tube('Front protection | diagonal brace',[(x,-2.208,.345),(x*.6,-2.208,.587)],.020)
box('Protection | central pad',(0,-2.238,.577),(.57,.050,.080),rubber,r=.012)
skid=mesh('Underbody | shaped front skid',[(-.53,-1.92,.34),(.53,-1.92,.34),(-.43,-1.47,.25),(.43,-1.47,.25),(-.43,-1.30,.37),(.43,-1.30,.37)],[(0,1,3,2),(2,3,5,4)],silver,GEAR);thick(skid,.009)
for x in [-.40,.40]:
 box('Fog lamp | rubber mount',(x,-2.158,.54),(.26,.08,.115),rubber,r=.015)
 box('Fog lamp | fluted lens',(x,-2.204,.54),(.226,.012,.086),ivory,r=.011)
 for j in range(11):box('Fog lamp | optical rib',(x-.10+j*.02,-2.212,.54),(.003,.003,.072),silver,r=.001)
# Faithful lamp face details and rear light band; fitted against body surface.
for side in [-1,1]:
 vs=[]
 for z in np.linspace(.772,.858,9):
  for xabs in np.linspace(.27,.82,25):
   x=side*float(xabs);h=bt.ray_cast(Vector((x,2.65,z)),Vector((0,-1,0)),1)
   assert h[0] is not None
   vs.append(h[0]+Vector((0,.007,0)))
 lamp=mesh('Rear lamp | continuous fitted lens '+str(side),vs,[(j*25+i,j*25+i+1,(j+1)*25+i+1,(j+1)*25+i) for j in range(8) for i in range(24)],red);lamp.data.materials.append(amber)
 for f in lamp.data.polygons:f.material_index=1 if f.index%24>18 else 0
 thick(lamp,.012)
 for x in [side*.69]:
  h=bt.ray_cast(Vector((x,-2.6,.58)),Vector((0,1,0)),1)
  if h[0] is not None:box('Front indicator | amber insert',h[0]+Vector((0,-.01,0)),(.12,.016,.047),amber,r=.007)
plate_y=bt.ray_cast(Vector((0,2.65,.555)),Vector((0,-1,0)),1)[0].y+.008
box('Rear | plate recess',(0,plate_y,.555),(.48,.016,.116),rubber,r=.008)
box('Rear | number plate',(0,plate_y+.011,.555),(.435,.005,.087),ivory,r=.004)
text('Rear | plate letters','SAFARI  01',(0,plate_y+.016,.535),.046,steel,EXT)
# Running gear existing source fragments: close open cut ends, remove slivers.
for o in list(EXT.objects):
 if o.get('source_island') in {1,3,4,20,21,31,32,33}:
  move(o,GEAR);o.data.materials.clear();o.data.materials.append(steel);bevel(o,.002,2)
# Small lamp emitters sit behind the existing closed lenses.
lampemit=mat('Lights | headlamp emitter',(.82,.69,.43),.22)
lampemit.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(1,.79,.48,1)
for source_id in [47,50]:
 ob=next((o for o in EXT.objects if o.get('source_island')==source_id),None)
 if ob:
  lo,hi=bounds(ob);center=(lo+hi)/2;ob.data.materials.clear();ob.data.materials.append(silver)
  cyl('Headlamp | bulb',center+Vector((0,.004,0)),.028,.008,lampemit,EXT,(0,-1,.10),24)
exec(compile(Path('C:/GrandTour/Art/VehicleTools/porsche_complete_well_liners.py').read_text(),'porsche_complete_well_liners.py','exec'))
exec(compile(Path('C:/GrandTour/Art/VehicleTools/porsche_complete_interior.py').read_text(),'porsche_complete_interior.py','exec'))
exec(compile(Path('C:/GrandTour/Art/VehicleTools/porsche_complete_delivery.py').read_text(),'porsche_complete_delivery.py','exec'))
