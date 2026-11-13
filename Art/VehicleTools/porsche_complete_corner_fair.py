"""Constrain the damaged 70-mm bumper crease to the surrounding measured skin."""
guide=tree(body);changes=[]
for sign in [-1,1]:
 samples=[]
 for y in np.linspace(-1.96,-1.64,22):
  for z in [.555,.565,.578,.697,.710,.725]:
   h=guide.ray_cast(Vector((sign*1.3,float(y),z)),Vector((-sign,0,0)),.60)
   if h[0] is not None and sign*h[0].x>.76:samples.append(h[0])
 arr=np.array([[p.y+1.8,p.z-.64,sign*p.x] for p in samples]);a=np.column_stack([np.ones(len(arr)),arr[:,0],arr[:,1],arr[:,0]**2,arr[:,0]*arr[:,1],arr[:,1]**2,arr[:,0]**3]);coef=np.linalg.lstsq(a,arr[:,2],rcond=None)[0]
 for v in body.data.vertices:
  p=v.co
  if not (sign*p.x>.77 and -1.94<p.y<-1.65 and .587<p.z<.688):continue
  y=p.y+1.8;z=p.z-.64;target=float(np.array([1,y,z,y*y,y*z,z*z,y**3])@coef);delta=max(-.018,min(.018,target-sign*p.x));fade=min(1,(p.z-.587)/.012,(.688-p.z)/.012,(p.y+1.94)/.025,(-1.65-p.y)/.025)
  p.x+=sign*delta*max(0,fade);changes.append(abs(delta*fade))
body.data.update();bm=bmesh.new();bm.from_mesh(body.data)
for f in bm.faces:
 c=f.calc_center_median()
 if abs(c.x)>.77 and -1.94<c.y<-1.65 and .587<c.z<.688 and f.normal.x*c.x>0:f.normal_flip()
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0002);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00004);bm.to_mesh(body.data);bm.free();finish(body,1.4)
report['repairs'].append({'part':'Bumper corner creases','method':'Measured surrounding-skin fit on source vertices; topology retained','vertices':len(changes),'max_local_change_m':max(changes,default=0)})
# The folded seam contains overlapping triangles, so fairing alone cannot repair
# it. Replace the small rectangular outer-skin region with a fitted surface.
from mathutils.geometry import delaunay_2d_cdt
def split(poly,axis,value,sign):
 a=[];b=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  u=(p[axis]-value)*sign;v=(q[axis]-value)*sign;ip=u>=0;iq=v>=0;(a if ip else b).append(p)
  if ip!=iq:h=p.lerp(q,u/(u-v));a.append(h);b.append(h)
 return a,b
for sign in [-1,1]:
 me=body.data;me.calc_loop_triangles();guide=tree(body);y0,y1=-1.915,-1.715;z0,z1=.595,.690;vs=[];fs=[];mats=[];edgeuv=[];removed=0
 for t in me.loop_triangles:
  ps=[me.vertices[k].co.copy() for k in t.vertices];pieces=[];work=ps
  for axis,val,sgn in [(0,sign*.78,sign),(1,y0,1),(1,y1,-1),(2,z0,1),(2,z1,-1)]:
   if not work:break
   work,out=split(work,axis,val,sgn)
   if len(out)>2:pieces.append(out)
  if len(work)>2:
   removed+=1
   for p in work:
    if min(abs(p.y-y0),abs(p.y-y1),abs(p.z-z0),abs(p.z-z1))<1e-6 and sign*p.x>.79:edgeuv.append(Vector((p.y,p.z)))
  for p in pieces:
   for j in range(1,len(p)-1):fs.append((len(vs),len(vs)+1,len(vs)+2));vs.extend([p[0],p[j],p[j+1]]);mats.append(me.polygons[t.polygon_index].material_index)
 # Ordered boundary including all source cut intersections, sampled to 5 mm.
 border=[]
 for a,b in [(Vector((y0,z0)),Vector((y1,z0))),(Vector((y1,z0)),Vector((y1,z1))),(Vector((y1,z1)),Vector((y0,z1))),(Vector((y0,z1)),Vector((y0,z0)))]:
  d=b-a;pts=[a.lerp(b,j/max(1,int(d.length/.005))) for j in range(max(1,int(d.length/.005)))];pts+=[p for p in edgeuv if abs((p-a).x*d.y-(p-a).y*d.x)<1e-7 and 0<=(p-a).dot(d)<d.length_squared];pts.sort(key=lambda p:(p-a).dot(d));border+=pts
 inp=border.copy()
 for y in np.arange(y0+.006,y1,.008):
  for z in np.arange(z0+.006,z1,.008):inp.append(Vector((y,z)))
 cv,ce,cf,ov,*_=delaunay_2d_cdt(inp,[],[list(range(len(border)))],1,1e-7);offset=len(vs)
 # Fit a quadratic from intact skin immediately above/below the crease.
 samples=[]
 for y in np.linspace(y0,y1,22):
  for z in [z0-.018,z0-.010,z1+.01,z1+.018]:
   h=guide.ray_cast(Vector((sign*1.3,float(y),z)),Vector((-sign,0,0)),.53)
   if h[0] is not None:samples.append(h[0])
 ar=np.array([[p.y+1.8,p.z-.64,sign*p.x] for p in samples]);a=np.column_stack([np.ones(len(ar)),ar[:,0],ar[:,1],ar[:,0]**2,ar[:,0]*ar[:,1],ar[:,1]**2]);coef=np.linalg.lstsq(a,ar[:,2],rcond=None)[0]
 for q in cv:
  h=guide.ray_cast(Vector((sign*1.3,q.x,q.y)),Vector((-sign,0,0)),.53)
  y=q.x+1.8;z=q.y-.64;target=float(np.array([1,y,z,y*y,y*z,z*z])@coef);vs.append(Vector((sign*target,q.x,q.y)))
 # Move the shared border and a small transition skirt to the same surface,
 # rather than reproducing the torn source depths at the patch edge.
 for p in vs[:offset]:
  if sign*p.x<.78:continue
  dy=max(y0-p.y,0,p.y-y1);dz=max(z0-p.z,0,p.z-z1);fall=max(dy,dz)
  if fall>=.035:continue
  y=p.y+1.8;z=p.z-.64;target=float(np.array([1,y,z,y*y,y*z,z*z])@coef);weight=1-fall/.035
  p.x+=sign*max(-.04,min(.04,target-sign*p.x))*weight
 for f in cf:
  ids=[offset+k for k in f];n=(vs[ids[1]]-vs[ids[0]]).cross(vs[ids[2]]-vs[ids[0]])
  if n.x*sign>0:ids.reverse()
  fs.append(ids);mats.append(0)
 new=bpy.data.meshes.new('Source fitted bumper-corner repair');new.from_pydata(vs,[],fs);new.update()
 for m in me.materials:new.materials.append(m)
 for f,mi in zip(new.polygons,mats):f.material_index=mi
 bm=bmesh.new();bm.from_mesh(new);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001);bm.to_mesh(new);bm.free();body.data=new;finish(body,1.4)
 report['repairs'].append({'part':'Folded bumper seam '+str(sign),'source_triangles_cut':removed,'new_surface_triangles':len(cf),'scope_m':{'y':[y0,y1],'z':[z0,z1]}})
