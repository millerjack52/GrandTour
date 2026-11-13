import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon
from shapely.ops import triangulate
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-prepared-v03');OUT=P.parent/'ferrari288-refined-v04';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_Safari.blend'))
S=4.5;sc=bpy.context.scene;root=bpy.data.objects.get('FERRARI 288 GTO | Safari assembly');body=bpy.data.objects.get('Body | source silhouette, repaired apertures')
M={m.name.split(' | ')[-1]:m for m in bpy.data.materials if m.name.startswith('Ferrari safari | ')}
cols={c.name:c for c in bpy.data.collections}
def mesh(n,v,f,col,mat):
 me=bpy.data.meshes.new(n);me.from_pydata([Vector(p)*S for p in v],[],f);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6*S);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7*S);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for face in bm.faces:face.smooth=True
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle()<math.radians(55)
 bm.to_mesh(me);bm.free();o=bpy.data.objects.new(n,me);cols[col].objects.link(o);o.parent=root;me.materials.append(M[mat]);o.color=M[mat].diffuse_color;return o
def box(n,c,d,mat,col,bevel=.001):
 c=Vector(c);dx,dy,dz=[t/2 for t in d];v=[c+Vector((x*dx,y*dy,z*dz)) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 o=mesh(n,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],col,mat)
 b=o.modifiers.new('Manufactured edge radius','BEVEL');b.width=bevel*S;b.segments=3;return o
rawverts=[v.co/S for v in body.data.vertices];rawfaces=[tuple(p.vertices) for p in body.data.polygons];bvh=BVHTree.FromPolygons(rawverts,rawfaces,all_triangles=False)
def sx(side,y,z):
 hit=bvh.ray_cast(Vector((side*.5,y,z)),Vector((-side,0,0)),1)
 return abs(hit[0].x) if hit[0] is not None else 0
# Source-conforming arch lips. Their inside edge follows the measured opening.
for side in [-1,1]:
 for axle,cy,cz in [('Front',-.2666,.0913),('Rear',.3066,.092)]:
  count=49;v=[]
  for i in range(count):
   theta=math.radians(-10+200*i/(count-1));dy,dz=math.cos(theta),math.sin(theta)
   lo,hi=.087,.163
   for k in range(22):
    r=(lo+hi)/2
    if sx(side,cy+dy*r,cz+dz*r)>.194:hi=r
    else:lo=r
   r=hi
   for rr,offset in [(r+.00045,.0008),(r+.004,.0010),(r+.009,.0005)]:
    y,z=cy+dy*rr,cz+dz*rr;x=sx(side,y,z)
    v.append((side*(x+offset),y,z))
  f=[(i*3+j,(i+1)*3+j,(i+1)*3+j+1,i*3+j+1) for i in range(count-1) for j in range(2)]
  o=mesh(f'Arch lip | {axle} {side}',v,f,'01 Body','Rubber');sol=o.modifiers.new('Arch lip return thickness','SOLIDIFY');sol.thickness=.001*S;sol.offset=-1
# Replace only the corrupted rear louvre insert, retaining the deck perimeter.
opening=Polygon([(-.109,.212),(.109,.212),(.133,.419),(-.133,.419)])
vv=[];ff=[];materials=[]
for face in body.data.polygons:
 pts=[rawverts[i] for i in face.vertices];c=sum(pts,Vector())/len(pts)
 if .20<c.y<.425 and c.z>.237:
  p=Polygon([(v.x,v.y) for v in pts])
  if p.is_valid and p.area>1e-12 and p.intersects(opening):
   d=p.difference(opening)
   if d.area<p.area-1e-12:
    if d.area<1e-12:continue
    coeff=np.linalg.lstsq(np.array([[v.x,v.y,1] for v in pts]),np.array([v.z for v in pts]),rcond=None)[0]
    parts=list(d.geoms) if hasattr(d,'geoms') else [d]
    for part in parts:
     if part.geom_type!='Polygon':continue
     for tri in triangulate(part):
      if not part.covers(tri.representative_point()):continue
      k=len(vv);vv.extend((x,y,float(coeff@[x,y,1])) for x,y in list(tri.exterior.coords)[:3]);ff.append((k,k+1,k+2));materials.append(face.material_index)
    continue
 k=len(vv);vv.extend(pts);ff.append(tuple(range(k,k+len(pts))));materials.append(face.material_index)
oldmaterials=list(body.data.materials);oldmesh=body.data;me=bpy.data.meshes.new('Locally repaired source panels');me.from_pydata([Vector(v)*S for v in vv],[],ff);me.update()
for m in oldmaterials:me.materials.append(m)
for p,idx in zip(me.polygons,materials):p.material_index=idx
body.data=me;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6*S)
# Remove exact duplicate triangles and collapsed fragments before recalculating.
seen=set();dupes=[]
for f in bm.faces:
 key=frozenset(v for v in f.verts)
 if key in seen or f.calc_area()<1e-11:dupes.append(f)
 else:seen.add(key)
bmesh.ops.delete(bm,geom=dupes,context='FACES_ONLY')
for axis,value in [(1,-.448),(2,.105),(2,.174)]:
 co=[0,0,0];no=[0,0,0];co[axis]=value*S;no[axis]=1
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=co,plane_no=no)
bm.normal_update()
for f in bm.faces:
 c=f.calc_center_median()/S
 if c.y<-.448 and .105<c.z<.174:f.material_index=2
 f.smooth=True
for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle()<math.radians(62)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
def rz(y):return .405-.349*y
# Enclosed rear cover beneath separate blades; no see-through void into rear tyres.
v=[(-.109,.211,rz(.211)-.006),(.109,.211,rz(.211)-.006),(.134,.42,rz(.42)-.006),(-.134,.42,rz(.42)-.006)]
o=mesh('Rear engine cover | dark inset',v,[(0,1,2,3)],'01 Body','Rubber');sol=o.modifiers.new('Enclosed cover thickness','SOLIDIFY');sol.thickness=.003*S;sol.offset=-1
for i in range(9):
 y=.222+i*.0232;w=.218+(y-.211)*.235;v=[]
 for j in range(13):
  x=-w/2+w*j/12;crown=.0015*(1-(2*x/w)**2)
  for dy,dz in [(-.006,0),(.007,.001),(.009,-.002),(-.006,-.002)]:v.append((x,y+dy,rz(y+dy)+crown+dz))
 f=[(j*4+k,(j+1)*4+k,(j+1)*4+(k+1)%4,j*4+(k+1)%4) for j in range(12) for k in range(4)]+[(3,2,1,0),(48,49,50,51)]
 o=mesh(f'Rear louvre | blade {i+1:02d}',v,f,'01 Body','Metal');b=o.modifiers.new('Louvre radius','BEVEL');b.width=.00065*S;b.segments=2
# Real rubber curvature needs interpolated normals, not face-area weighting.
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.endswith(' | tyre'):
  for m in list(o.modifiers):o.modifiers.remove(m)
  bm=bmesh.new();bm.from_mesh(o.data)
  for f in bm.faces:f.smooth=True
  for e in bm.edges:e.smooth=True
  bm.to_mesh(o.data);bm.free()
 # Dark mirrors match the concept and distinguish the glass openings.
 if o.get('source_component') in [21,22]:o.data.materials.clear();o.data.materials.append(M['Rubber'])
# Replace jagged Tripo traction-board chips with coherent moulded boards in-place.
for idx in [3,4]:
 o=next(o for o in bpy.data.objects if o.get('source_component')==idx);bpy.data.objects.remove(o,do_unlink=True)
 y=.0339 if idx==3 else .1812
 box(f'Traction board {idx} | moulded tray',(.10,y,.359),(.047,.091,.007),'Board','06 Roof rack and cargo',.002)
 for row in range(3):
  for j in range(8):box(f'Traction board {idx} | grip {row}-{j}',(.084+row*.016,y-.036+j*.0103,.364),(.006,.006,.005),'Board','06 Roof rack and cargo',.001)
# Uniform gasket beads hide neither holes nor body gaps: they follow each fitted pane boundary.
for o in list(cols['02 Glass'].objects):
 if o.type!='MESH' or not o.name.startswith('Glass |'):continue
 bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update()
 # Source-derived windscreen must face outward for a sensible solidify direction.
 avg=sum((f.normal*f.calc_area() for f in bm.faces),Vector())
 expected=Vector((0,-.5,.866)) if 'windscreen' in o.name else Vector((1 if 'Left' in o.name else -1,0,.4))
 if avg.dot(expected)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=True
 bm.to_mesh(o.data);bm.free()
# Lit QA with a ground grid visible through the actual glass from inside.
sc.render.resolution_x=1600;sc.render.resolution_y=1050;cam=sc.camera
def render(n,c,d,scale):
 c=Vector(c)*S;cam.location=c+Vector(d)*S;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale*S;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
sc.render.engine='BLENDER_WORKBENCH'
for n,d in [('quarter',(2,-3,1.1)),('rear-quarter',(-2,3,.9)),('side',(3,0,0)),('front',(0,-3,0)),('rear',(0,3,0))]:render(n,(0,0,.205),d,1.17)
saved={c.name:c.hide_render for c in cols.values()}
for n in ['05 Front equipment','06 Roof rack and cargo','07 Side equipment','09 Small fittings']:cols[n].hide_render=True
render('bare-body',(0,0,.205),(2,-3,1),1.14)
for n,val in saved.items():cols[n].hide_render=val
render('window-close',(0,-.04,.27),(2,-3,.9),.55)
for o in sc.objects:
 if o.type=='LIGHT':o.hide_render=True
def area(n,pos,power,size):
 data=bpy.data.lights.new(n,'AREA');data.energy=power;data.shape='DISK';data.size=size;o=bpy.data.objects.new(n,data);cols['99 Review'].objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
area('Review key',(3,-4,6),900,5);area('Review fill',(-4,-1,3),700,4);area('Review rim',(1,4,5),800,3)
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.resolution_x=1400;sc.render.resolution_y=1000
render('lit-quarter',(0,0,.205),(2,-3,1.1),1.17)
render('lit-glazing',(0,-.04,.27),(2,-3,.9),.55)
# Neutral floor used only for renders, not part of the vehicle export.
floor=box('REVIEW | floor',(0,0,-.007),(5,5,.012),'Metal','99 Review',0)
for y in [-1,-.75,-.50]:box('REVIEW | floor marking',(0,y,-.0006),(.65,.008,.0005),'Lens','99 Review',0)
cam.data.type='PERSP';cam.data.lens=20;cam.location=(.40,.16,1.27);target=Vector((.40,-3,.95));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/'driver-view.png');bpy.ops.render.render(write_still=True)
for o in cols['99 Review'].objects:
 if o.type=='MESH':o.hide_render=True;o.hide_set(True)
sc.render.engine='BLENDER_WORKBENCH';render('quarter',(0,0,.205),(2,-3,1.1),1.17)
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_Safari_Review.blend'))
print('SAVED',OUT)
