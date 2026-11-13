import bpy,bmesh,math,json,hashlib,sys,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform,delaunay_2d_cdt
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon,MultiPoint,Point
from shapely.ops import unary_union,triangulate
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04/Porsche_Safari_Review.blend')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-window-repair-v05');DEST=OUT/'Porsche_Window_Repair.blend';MAN=OUT/'repair-report.json'
if DEST.exists():assert MAN.exists() and hashlib.sha256(DEST.read_bytes()).hexdigest()==json.loads(MAN.read_text())['blend_sha256'],'Preserve manual changes'
bpy.ops.wm.open_mainfile(filepath=str(SRC));sc=bpy.context.scene;body=bpy.data.objects['Porsche original body - locally repaired'];root=bpy.data.objects['Porsche | ROOT'];paint=body.data.materials[0];rubber=bpy.data.materials['Fitted rubber glazing seals'];glassmat=bpy.data.materials['Porsche clear glass'];trim=bpy.data.materials['Cabin | charcoal soft trim']
COL=bpy.data.collections.new('09 Rebuilt cabin interfaces');sc.collection.children.link(COL)
rep={'source':str(SRC),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'scope':'Rebuild window interfaces; preserve the accepted overall vehicle','patches':[]}
def active(o):bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def clean(me):
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0000001);bm.to_mesh(me);bm.free();me.update()
 for p in me.polygons:p.use_smooth=True
 me.set_sharp_from_angle(angle=1.1)
def mesh(n,vs,fs,m,normal):
 me=bpy.data.meshes.new(n);me.from_pydata(vs,[],fs);me.update();me.materials.append(m);clean(me)
 bm=bmesh.new();bm.from_mesh(me);bm.normal_update()
 if sum(f.normal.dot(normal)*f.calc_area() for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bm.to_mesh(me);bm.free();o=bpy.data.objects.new(n,me);COL.objects.link(o);o.parent=root;return o
def thick(o,t):
 active(o);md=o.modifiers.new('Fitted physical thickness','SOLIDIFY');md.thickness=t;md.offset=-1;md.use_even_offset=False;bpy.ops.object.modifier_apply(modifier=md.name)
 o.data.set_sharp_from_angle(angle=.7)
def tree(o):
 o.data.calc_loop_triangles();return BVHTree.FromPolygons([v.co for v in o.data.vertices],[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
def owners(me):
 a=me.attributes.get('gt_window_patch');return [v.value for v in a.data] if a else [0]*len(me.polygons)
def mark_owners(me,values):
 a=me.attributes.new('gt_window_patch','INT','FACE')
 for p,v in zip(a.data,values):p.value=v
def join_patch(ob,patch,owner):
 vs=[v.co.copy() for v in ob.data.vertices];fs=[tuple(f.vertices) for f in ob.data.polygons];marks=owners(ob.data);off=len(vs)
 vs += [v.co.copy() for v in patch.data.vertices];fs += [tuple(off+i for i in f.vertices) for f in patch.data.polygons];marks += [owner]*len(patch.data.polygons)
 me=bpy.data.meshes.new('Connected cabin interfaces and retained body');me.from_pydata(vs,[],fs);me.materials.append(paint);mark_owners(me,marks);ob.data=me;clean(me);bpy.data.objects.remove(patch,do_unlink=True)
def surface_fit(points,axis):
 other=[i for i in range(3) if i!=axis];a=np.array([[1,p[other[0]],p[other[1]],p[other[0]]**2,p[other[0]]*p[other[1]],p[other[1]]**2] for p in points]);b=np.array([p[axis] for p in points]);co=np.linalg.lstsq(a,b,rcond=None)[0]
 return lambda u,v:float(np.dot(co,[1,u,v,u*u,u*v,v*v]))
def resample(poly,step=.012):
 ring=poly.exterior;n=max(24,math.ceil(ring.length/step));return [Vector(ring.interpolate(i/n,normalized=True).coords[0]) for i in range(n)]
def polygon_points(poly,step=.025):
 pts=resample(poly);return pts
def cut_body(domain,axis,sign,depth):
 other=[k for k in range(3) if k!=axis];me=body.data;me.calc_loop_triangles();vs=[];fs=[];cut=0;boundary=[];refs=[];oldowners=owners(me);marks=[]
 for t in me.loop_triangles:
  ps=[me.vertices[i].co.copy() for i in t.vertices];c=sum(ps,Vector())/3
  owner=oldowners[t.polygon_index]
  if owner==0 and abs(c[axis]-depth(c[other[0]],c[other[1]]))<.16:
   tp=Polygon([(p[other[0]],p[other[1]]) for p in ps])
   if tp.area>1e-11 and tp.intersects(domain):
    diff=tp.difference(domain);pieces=[diff] if diff.geom_type=='Polygon' else [p for p in getattr(diff,'geoms',[]) if p.geom_type=='Polygon'];cut+=1;flat=[Vector((p[other[0]],p[other[1]],0)) for p in ps]
    for piece in pieces:
     for q in list(piece.exterior.coords)[:-1]:
      if domain.exterior.distance(Point(q))<1e-7:
       boundary.append(Vector(q));refs.append((barycentric_transform(Vector((*q,0)),*flat,*ps),t.normal[axis]*sign))
     for tr in triangulate(piece):
      if not piece.covers(tr.representative_point()):continue
      pp=[barycentric_transform(Vector((u,v,0)),*flat,*ps) for u,v in list(tr.exterior.coords)[:-1]]
      if (pp[1]-pp[0]).cross(pp[2]-pp[0]).dot((ps[1]-ps[0]).cross(ps[2]-ps[0]))<0:pp.reverse()
      fs.append(tuple(range(len(vs),len(vs)+3)));vs.extend(pp);marks.append(owner)
    continue
  fs.append(tuple(range(len(vs),len(vs)+3)));vs.extend(ps);marks.append(owner)
 new=bpy.data.meshes.new('Retained source skin with fitted patch boundaries');new.from_pydata(vs,[],fs);new.materials.append(paint);mark_owners(new,marks);body.data=new;clean(new)
 return cut,boundary,refs
def cdt_surface(domain,holes,depth,axis,sign,extra_boundary=[],exact_boundary=False):
 other=[k for k in range(3) if k!=axis];outer=[] if exact_boundary else resample(domain);outer+=extra_boundary;outer=sorted(outer,key=lambda p:domain.exterior.project(Point(p)))
 # Remove coincident points while retaining all actual cut-edge intersections.
 keep=[]
 for p in outer:
  if not keep or (p-keep[-1]).length>1e-6:keep.append(p)
 pts=keep;loops=[list(range(len(pts)))]
 for hole in holes:
  loop=resample(hole);loops.append(list(range(len(pts),len(pts)+len(loop))));pts+=loop
 x0,y0,x1,y1=domain.bounds
 if exact_boundary:
  for d in [.004,.008,.016,.028]:
   inset=domain.buffer(-d)
   if inset.geom_type=='Polygon':
    for p in resample(inset,.009):
     if all(not h.buffer(.001).contains(Point(p)) for h in holes):pts.append(p)
 for u in np.arange(x0,x1,.025):
  for v in np.arange(y0,y1,.025):
   p=Point(u,v)
   if domain.contains(p) and all(not h.buffer(.001).contains(p) for h in holes):pts.append(Vector((u,v)))
 cv,ce,cf,*_=delaunay_2d_cdt(pts,[],loops,0,1e-7);faces=[]
 for f in cf:
  p=sum((cv[i] for i in f),Vector((0,0)))/len(f);q=Point(p)
  if domain.buffer(1e-6).covers(q) and all(not h.contains(q) for h in holes):faces.append(f)
 vs=[]
 for p in cv:
  q=Vector();q[other[0]]=p.x;q[other[1]]=p.y;q[axis]=depth(p.x,p.y);vs.append(q)
 return vs,faces

# Rebuild each complete side as one metal surface around all three openings.
for sign,tag in [(1,'L'),(-1,'R')]:
 names=['Vent glass '+tag,'Door glass '+tag,'Quarter glass '+tag];panes=[bpy.data.objects[n] for n in names];points=[v.co.copy() for p in panes for v in p.data.vertices];fit=surface_fit(points,0)
 holes=[]
 for pane in panes:
  poly=MultiPoint([(v.co.y,v.co.z) for v in pane.data.vertices]).convex_hull.buffer(-.008,quad_segs=6).buffer(.008,quad_segs=6)
  holes.append(poly.buffer(.012,quad_segs=6))
 domain=unary_union(holes).convex_hull.buffer(.045,quad_segs=6)
 oldtree=tree(body);misses=[]
 def smooth(u,v):return fit(u,v)+sign*.014
 def fitted(u,v):return smooth(u,v)
 cut,boundary,refs=cut_body(domain,0,sign,smooth)
 # Both sides of the physical joint share the same surface. The transition
 # extends into retained metal; noisy source depths are not fed into the trim.
 body.data.update()
 for v in body.data.vertices:
  p=v.co;d=domain.distance(Point(p.y,p.z))
  if p.x*sign>.45 and d<.055 and abs(p.x-smooth(p.y,p.z))<.115:
   t=1-d/.055;w=t*t*(3-2*t);inner=v.normal.x*sign<-.25
   target=smooth(p.y,p.z)-(sign*.004 if inner else 0);p.x=p.x*(1-w)+target*w
 vs,fs=cdt_surface(domain,holes,fitted,0,sign,boundary);metal=mesh('Cabin side '+tag+' | continuous metal frame',vs,fs,paint,Vector((sign,0,0)));thick(metal,.004)
 # Weld the new outer skin to the actual body cut-edge vertices.
 join_patch(body,metal,1)
 for name,pane,hole in zip(names,panes,holes):
  glasspoly=hole.buffer(-.012,quad_segs=6);outerpts=resample(hole);innerpts=[]
  from shapely.ops import nearest_points
  for p in outerpts:innerpts.append(Vector(nearest_points(glasspoly.exterior,Point(p))[0].coords[0]))
  N=len(outerpts);vs=[]
  for t,offset in [(0,.000),(.2,.004),(.80,.004),(1,-.003)]:
   for p,q in zip(outerpts,innerpts):
    v=p.lerp(q,t);vs.append((fit(v.x,v.y)+sign*(.014+offset),v.x,v.y))
  seal=mesh(name+' | clean gasket',vs,[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(3) for i in range(N)],rubber,Vector((sign,0,0)));thick(seal,.005)
  gv,gf=cdt_surface(glasspoly,[],lambda u,v:fit(u,v)+sign*.008,0,sign);glass=mesh(name+' | fitted pane',gv,gf,glassmat,Vector((sign,0,0)));thick(glass,.002)
  # The inner reveal follows the same complete aperture, closing the sightline.
  vs=[(fit(p.x,p.y)+sign*off,p.x,p.y) for off in [.014,-.016] for p in outerpts]
  reveal=mesh(name+' | cabin reveal',vs,[(i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N)],trim,Vector((sign,0,0)));thick(reveal,.003)
  for oldname in [name,name+' fitted surround','Cabin | '+name+' aperture return']:
   if oldname in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[oldname],do_unlink=True)
 rep['patches'].append({'side':tag,'removed_source_faces':cut,'cut_boundary_vertices':len(boundary),'domain_bounds_yz':list(domain.bounds),'missing_outer_surface_rays':len(misses)})

# The windscreen receives the same connected construction, including its A-pillars.
for name,sign in [('Windscreen',-1),('Rear glass',1)]:
 pane=bpy.data.objects[name];fit=surface_fit([v.co.copy() for v in pane.data.vertices],1)
 glasspoly=MultiPoint([(v.co.x,v.co.z) for v in pane.data.vertices]).convex_hull.buffer(-.010,quad_segs=6).buffer(.010,quad_segs=6)
 hole=glasspoly.buffer(.015,quad_segs=6);domain=hole.buffer(.032,quad_segs=6)
 def smooth(u,v):return fit(u,v)+sign*.014
 cut,boundary,refs=cut_body(domain,1,sign,smooth)
 # Sample the actual retained cut edge, never the first hit on unrelated hood
 # or roof geometry. These exact positions define the outer mating boundary.
 groups={};length=domain.exterior.length
 for p,n in refs:
  t=domain.exterior.project(Point(p.x,p.z));groups.setdefault(round(t,6),[]).append((p,n))
 knots=[];depths=[]
 for t,items in sorted(groups.items()):
  outside=[p for p,n in items if n>.20];pool=outside or [p for p,n in items]
  p=min(pool,key=lambda p:abs(p.y-smooth(p.x,p.z)));knots.append(t);depths.append(p.y)
 xx=np.array([knots[-1]-length]+knots+[knots[0]+length]);yy=np.array([depths[-1]]+depths+[depths[0]])
 # Smooth the complete cut contour and fit both sides of the joint to it.
 samples=np.arange(1024)*length/1024
 sampled=np.interp(samples,xx,yy)
 fft=np.fft.rfft(sampled);fft[35:]=0
 smoothdepth=np.fft.irfft(fft,n=1024)
 def edge_depth(s):return float(np.interp(s,np.append(samples,length),np.append(smoothdepth,smoothdepth[0])))
 protected=set()
 for f,m in zip(body.data.polygons,owners(body.data)):
  if m:protected.update(f.vertices)
 for vert in body.data.vertices:
  if vert.index in protected:continue
  p=vert.co;q=Point(p.x,p.z);d=domain.exterior.distance(q)
  if d<.045 and abs(p.y-smooth(p.x,p.z))<.16:
   s=domain.exterior.project(q);delta=edge_depth(s)-float(np.interp(s,xx,yy))
   t=1-d/.045;w=t*t*(3-2*t)
   p.y+=delta*w
   if d<.00001:p.y=edge_depth(s)
 def fitted(u,v):
  d=domain.exterior.distance(Point(u,v));t=max(0.,1-d/.031);w=t*t*(3-2*t);s=domain.exterior.project(Point(u,v));return smooth(u,v)*(1-w)+edge_depth(s)*w
 vs,fs=cdt_surface(domain,[hole],fitted,1,sign,boundary);metal=mesh(name+' | continuous metal frame',vs,fs,paint,Vector((0,sign,0)));thick(metal,.004)
 join_patch(body,metal,2)
 outerpts=resample(hole);innerpts=[Vector(nearest_points(glasspoly.exterior,Point(p))[0].coords[0]) for p in outerpts];N=len(outerpts);vs=[]
 for t,offset in [(0,0),(.2,.004),(.80,.004),(1,-.003)]:
  for p,q in zip(outerpts,innerpts):
   v=p.lerp(q,t);vs.append((v.x,fit(v.x,v.y)+sign*(.014+offset),v.y))
 seal=mesh(name+' | clean gasket',vs,[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(3) for i in range(N)],rubber,Vector((0,sign,0)));thick(seal,.005)
 gv,gf=cdt_surface(glasspoly,[],lambda u,v:fit(u,v)+sign*.008,1,sign);glass=mesh(name+' | fitted pane',gv,gf,glassmat,Vector((0,sign,0)));thick(glass,.002)
 vs=[(p.x,fit(p.x,p.y)+sign*off,p.y) for off in [.014,-.016] for p in outerpts]
 reveal=mesh(name+' | cabin reveal',vs,[(i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N)],trim,Vector((0,sign,0)));thick(reveal,.003)
 for oldname in [name,name+' fitted surround','Cabin | '+name+' aperture return']:
  if oldname in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[oldname],do_unlink=True)
 rep['patches'].append({'window':name,'removed_source_faces':cut,'cut_boundary_vertices':len(boundary),'domain_bounds_xz':list(domain.bounds)})

# Repaired geometry needs new charts; unchanged parts retain their existing UVs.
for o in [body]+list(COL.objects):
 if o.type!='MESH':continue
 active(o)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
for c in bpy.data.collections:
 if c.name.startswith('LOD'):c.hide_render=True;c.hide_viewport=True
active(body);md=body.modifiers.new('Retained surface shading','WEIGHTED_NORMAL');md.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=md.name)
sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100;sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_cavity=False;sc.display.shading.show_shadows=False
cam=sc.camera;cam.data.type='ORTHO'
for n,p,t,z in [('side',(7,0,1.1),(0,0,1.0),5.5),('window-left',(4,-3,2.4),(.68,.05,1.25),2.0),('window-right',(-4,-3,2.4),(-.68,.05,1.25),2.0),('quarter',(5,-7,3.5),(0,0,.9),5.5)]:
 cam.location=p;cam.rotation_euler=(Vector(t)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=z;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
active(root);bpy.ops.wm.save_as_mainfile(filepath=str(DEST));rep['blend_sha256']=hashlib.sha256(DEST.read_bytes()).hexdigest();rep['status']='Under construction and close-up review';MAN.write_text(json.dumps(rep,indent=2));print(json.dumps(rep),flush=True)
