"""Local component reconstruction on the user-accepted Porsche v02 shape."""
import bpy,bmesh,sys,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt,barycentric_transform
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon,Point
from shapely.ops import triangulate,nearest_points
BASE=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02/Porsche_Preserved_Repair.blend')
O=BASE.parent.parent/'porsche-tidy-v03';O.mkdir(exist_ok=True)
DEST=O/'Porsche_Tidy.blend';MAN=O/'tidy-report.json'
if DEST.exists():
 assert MAN.exists() and hashlib.sha256(DEST.read_bytes()).hexdigest()==json.loads(MAN.read_text())['blend_sha256'],'Preserve manual edits: use a fresh revision'
bpy.ops.wm.open_mainfile(filepath=str(BASE));sc=bpy.context.scene;parts=bpy.data.collections['Porsche - repaired original components']
body=bpy.data.objects['Porsche original body - locally repaired'];paint=body.data.materials[0];rubber=bpy.data.materials['Fitted rubber glazing seals'];glassmat=bpy.data.materials['Porsche clear glass'];steel=bpy.data.materials['Original hardware graphite']
body.data.calc_loop_triangles();source_triangles=[tuple(t.vertices) for t in body.data.loop_triangles];source_coords=[v.co.copy() for v in body.data.vertices];source_normals=[[body.data.corner_normals[k].vector.copy() for k in t.loops] for t in body.data.loop_triangles];normal_tree=BVHTree.FromPolygons(source_coords,source_triangles,all_triangles=True)
report={'source':str(BASE),'source_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'shape_authority':'User accepted v02 shape, 2026-10-06','windows':[],'changed_accessories':[]};window_contracts=[]
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def mesh(name,vs,fs,mat,smooth=True):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new(name,me);parts.objects.link(ob);me.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 for f in me.polygons:f.use_smooth=smooth
 me.set_sharp_from_angle(angle=.7);return ob
def thick(o,t):
 active(o);md=o.modifiers.new('Closed component thickness','SOLIDIFY');md.thickness=t;md.offset=-1;bpy.ops.object.modifier_apply(modifier=md.name)
 o.data.set_sharp_from_angle(angle=.3)
def top_boundary(ob):
 N=len(ob.data.vertices)//2;ec={}
 for f in ob.data.polygons:
  ids=list(f.vertices)
  if all(k<N for k in ids):
   for a,b in zip(ids,ids[1:]+ids[:1]):key=tuple(sorted((a,b)));ec[key]=ec.get(key,0)+1
 edges={e for e,n in ec.items() if n==1};a,b=edges.pop();loop=[a,b]
 while loop[-1]!=loop[0]:
  e=next(e for e in edges if loop[-1] in e);edges.remove(e);loop.append(e[0] if e[1]==loop[-1] else e[1])
 return [ob.matrix_world@ob.data.vertices[k].co for k in loop[:-1]]
def components(poly):
 if poly.is_empty:return []
 return [poly] if poly.geom_type=='Polygon' else [p for p in poly.geoms if p.geom_type=='Polygon']
def sampled(poly,step=.012):
 line=poly.exterior;n=max(24,math.ceil(line.length/step));return [Vector(line.interpolate(i/n,normalized=True).coords[0]) for i in range(n)]
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.index_update();orig=[v.co.copy() for v in bm.verts]
faces=[[v.co.copy() for v in f.verts] for f in bm.faces];bm.free()
rawvs=[p for t in faces for p in t];rawtree=BVHTree.FromPolygons(rawvs,[(i,i+1,i+2) for i in range(0,len(rawvs),3)],all_triangles=True)
for name in ['Windscreen','Rear glass','Quarter glass L','Quarter glass R','Door glass L','Door glass R','Vent glass L','Vent glass R']:
 ob=bpy.data.objects[name];axes=(0,2) if name in ['Windscreen','Rear glass'] else (1,2);d=next(k for k in range(3) if k not in axes);sign=(-1 if name=='Windscreen' or name.endswith(' R') else 1)
 boundary=top_boundary(ob);poly=Polygon([(p[axes[0]],p[axes[1]]) for p in boundary]);poly=poly.buffer(0)
 if name.startswith('Quarter'):poly=poly.convex_hull
 inner=poly.simplify(.0015,preserve_topology=True).buffer(-.004,quad_segs=4).buffer(.004,quad_segs=4)
 width=.030 if name in ['Windscreen','Rear glass'] else (.010 if 'Vent' in name else .024)
 outer=inner.buffer(width,quad_segs=3)
 arr=np.array([list(p) for p in boundary]);u=arr[:,axes[0]];v=arr[:,axes[1]]
 # Smooth optical/support surface fitted to original aperture coordinates.
 A=np.column_stack([np.ones(len(arr)),u,v,u*u,u*v,v*v]);coef=np.linalg.lstsq(A,arr[:,d],rcond=None)[0]
 if axes==(1,2):coef=np.concatenate([np.linalg.lstsq(A[:,:3],arr[:,d],rcond=None)[0],np.zeros(3)])
 uvpoints=arr[:,axes];residual=arr[:,d]-A@coef
 def depth(q):
  u,v=q;ds=np.sum((uvpoints-np.array([u,v]))**2,axis=1);weights=1/np.maximum(ds,1e-12)**1.5
  return float(np.array([1,u,v,u*u,u*v,v*v])@coef)+float(np.sum(weights*residual)/np.sum(weights))
 def xyz(q,offset=0):
  p=Vector((0,0,0));p[axes[0]]=q[0];p[axes[1]]=q[1];p[d]=depth(q)+sign*offset;return p
 near=outer.buffer(.028);newfaces=[];removed=0;adjusted=0
 aperture=inner.buffer(-.002)
 def split(poly,fun):
  ins=[];outs=[]
  for p,q in zip(poly,poly[1:]+poly[:1]):
   a=fun(p);b=fun(q);ip=a>=0;iq=b>=0;(ins if ip else outs).append(p)
   if ip!=iq:
    h=p.lerp(q,a/(a-b));ins.append(h);outs.append(h)
  return ins,outs
 work=[]
 for tri in faces:
  tp=Polygon([(p[axes[0]],p[axes[1]]) for p in tri])
  if tp.is_empty or not tp.intersects(aperture):newfaces.append(tri);continue
  center=sum(tri,Vector())/3
  inside,outside=split(tri,lambda p:.060-(p[d]-depth((p[axes[0]],p[axes[1]]))))
  if len(outside)>=3:newfaces.extend([[outside[0],outside[k],outside[k+1]] for k in range(1,len(outside)-1)])
  if len(inside)<3:continue
  inside,outside=split(inside,lambda p:.060+(p[d]-depth((p[axes[0]],p[axes[1]]))))
  if len(outside)>=3:newfaces.extend([[outside[0],outside[k],outside[k+1]] for k in range(1,len(outside)-1)])
  if len(inside)>=3:work.extend([[inside[0],inside[k],inside[k+1]] for k in range(1,len(inside)-1)])
 for tri in work:
  c=sum(tri,Vector())/3;q=(c[axes[0]],c[axes[1]])
  if min(abs(p[d]-depth((p[axes[0]],p[axes[1]]))) for p in tri)>.11:newfaces.append(tri);continue
  tpoly=Polygon([(p[axes[0]],p[axes[1]]) for p in tri])
  if tpoly.area<1e-12 or not tpoly.intersects(near):newfaces.append(tri);continue
  diff=tpoly.difference(aperture);removed+=int(not diff.equals(tpoly))
  flat=[Vector((p[axes[0]],p[axes[1]],0)) for p in tri]
  for pp in components(diff):
   for t in triangulate(pp):
    if not pp.covers(t.representative_point()):continue
    vs=[]
    for u,v in list(t.exterior.coords)[:-1]:
     p=barycentric_transform(Vector((u,v,0)),*flat,*tri)
     vs.append(p)
    if (vs[1]-vs[0]).cross(vs[2]-vs[0]).dot((tri[1]-tri[0]).cross(tri[2]-tri[0]))<0:vs.reverse()
    newfaces.append(vs)
 faces=newfaces
 # Fitted annular surround. Outer row shares the cut curve; stepped bead and
 # return meet glass at the same inner curve. Back flange closes the contact.
 ps=sampled(outer);vs=[];N=len(ps)
 inn=[Vector(nearest_points(inner.exterior,Point(p))[0].coords[0]) for p in ps]
 def outerdepth(q):
  origin=xyz(q);origin[d]+=sign*.16;direction=Vector((0,0,0));direction[d]=-sign;hits=[]
  for _ in range(16):
   h=rawtree.ray_cast(origin,direction,.32)
   if h[0] is None:break
   hits.append(h[0][d]);origin=h[0]+direction*.00005
  hits=[h for h in hits if abs(h-depth(q))<.04]
  return min(hits,key=lambda v:abs(v-depth(q))) if hits else depth(q)+sign*.007
 od=[outerdepth(p) for p in ps]
 for t,h in [(0,.007),(.18,.010),(.78,.010),(1,.0005)]:
  for k,(a,b) in enumerate(zip(ps,inn)):
   q=a.lerp(b,t);p=xyz(q,h);p[d]+=(od[k]-depth(a)-sign*.007)*max(0,1-t/.35);vs.append(p)
 fs=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(3) for i in range(N)]
 rim=mesh(name+' fitted surround',vs,fs,paint);rim.data.materials.append(rubber)
 for f in rim.data.polygons:f.material_index=1 if f.index>=N else 0
 thick(rim,.004)
 window_contracts.append((rim,inner,outer,axes,d,sign,N))
 # Closed pane with a regular triangulation and no distorted inherited shards.
 ips=sampled(inner,.014);points=ips.copy();lo=inner.bounds[:2];hi=inner.bounds[2:]
 for u in np.arange(lo[0]+.015,hi[0],.025):
  for v in np.arange(lo[1]+.015,hi[1],.025):
   if inner.contains(Point(u,v)) and inner.exterior.distance(Point(u,v))>.006:points.append(Vector((u,v)))
 cv,ce,cf,*_=delaunay_2d_cdt(points,[],[list(range(len(ips)))],1,1e-7)
 oldname=ob.name;bpy.data.objects.remove(ob,do_unlink=True)
 gasket=bpy.data.objects.get(name+' - original outline gasket')
 if gasket:bpy.data.objects.remove(gasket,do_unlink=True)
 pane=mesh(oldname,[xyz(p) for p in cv],cf,glassmat);thick(pane,.002)
 report['windows'].append({'name':name,'body_triangles_cut':removed,'original_outline_area_m2':poly.area,'repaired_outline_area_m2':inner.area,'outer_ring_vertices':N,'scope':'Original aperture retained with local corner/tear repair and a fitted annular surround'})
 print('WINDOW',name,'cut',removed,flush=True)
vs=[p for f in faces for p in f];fs=[(i,i+1,i+2) for i in range(0,len(vs),3)]
oldme=body.data;me=bpy.data.meshes.new('Body with reconstructed window apertures');me.from_pydata(vs,[],fs);me.update();body.data=me;me.materials.append(paint)
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00003);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
bm.to_mesh(me);bm.free()
# Reform only the old mounting flange beneath each new seal. This prevents
# torn lips protruding through the seal while retaining the body support.
flange_movement=[]
for rim,inner,outer,axes,d,sign,N in window_contracts:
 rim.data.calc_loop_triangles();rt=BVHTree.FromPolygons([v.co for v in rim.data.vertices],[list(t.vertices) for t in rim.data.loop_triangles],all_triangles=True)
 direction=Vector((0,0,0));direction[d]=-sign
 for v in me.vertices:
  q=Point(v.co[axes[0]],v.co[axes[1]])
  if not outer.contains(q) or inner.buffer(-.003).contains(q) or outer.exterior.distance(q)<.002:continue
  origin=v.co.copy();origin[d]+=sign*.04;h=rt.ray_cast(origin,direction,.08)
  if h[0] is None:continue
  target=h[0][d]-sign*.003;delta=(v.co[d]-target)*sign
  if 0<delta<.025:v.co[d]=target;flange_movement.append(delta)
me.update();me.calc_loop_triangles();mount_tree=BVHTree.FromPolygons([v.co for v in me.vertices],[list(t.vertices) for t in me.loop_triangles],all_triangles=True)
for rim,inner,outer,axes,d,sign,N in window_contracts:
 half=len(rim.data.vertices)//2
 for i in range(N):
  v=rim.data.vertices[i];h=mount_tree.find_nearest(v.co);delta=h[0]-v.co
  if h[3]<.065:
   v.co+=delta;rim.data.vertices[half+i].co+=delta
 rim.data.update()
report['mounting_flange_repairs']={'vertices':len(flange_movement),'max_recess_m':max(flange_movement,default=0),'scope':'Only body lips beneath replacement seals; external body panels retained'}
bm=bmesh.new();bm.from_mesh(me);bad=[e for e in bm.edges if len(e.link_faces)>2]
if bad:bmesh.ops.split_edges(bm,edges=bad)
bm.to_mesh(me);bm.free()
for f in me.polygons:f.use_smooth=True
me.set_sharp_from_angle(angle=1.4)
active(body);mod=body.modifiers.new('Area weighted panel normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=35;bpy.ops.object.modifier_apply(modifier=mod.name)
exec(compile(Path('C:/GrandTour/Art/VehicleTools/porsche_tidy_fittings.py').read_text(),'porsche_tidy_fittings.py','exec'))
sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1500;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
def render(name,pos,target,scale):
 c=sc.camera;c.location=pos;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=scale;sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
render('windows-after',(5,-2,2.5),(.65,.15,1.23),2.8)
render('quarter',(5.4,-7.2,3.7),(0,0,.92),5.65)
render('rear',(5.4,7.2,3.8),(0,0,.92),5.65)
render('side',(7,0,.92),(0,0,.92),5.65)
render('top',(0,0,8),(0,0,.92),5.65)
sc.camera.location=(5.4,-7.2,3.7);sc.camera.rotation_euler=(Vector((0,0,.92))-sc.camera.location).to_track_quat('-Z','Y').to_euler();sc.camera.data.ortho_scale=5.65
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   space=area.spaces.active;space.overlay.show_overlays=False;space.shading.color_type='MATERIAL';space.region_3d.view_location=Vector((0,0,.92));space.region_3d.view_distance=6;space.region_3d.view_rotation=sc.camera.rotation_euler.to_quaternion();space.region_3d.view_perspective='PERSP'
active(body);bpy.ops.wm.save_as_mainfile(filepath=str(DEST));report['blend_sha256']=hashlib.sha256(DEST.read_bytes()).hexdigest();MAN.write_text(json.dumps(report,indent=2))
