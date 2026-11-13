"""Small source-derived skin charts at the damaged bumper/wing junctions."""
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from mathutils.geometry import delaunay_2d_cdt,barycentric_transform
def repair_chart(name,selector,axes,sign):
 me=body.data;me.calc_loop_triangles();coords=[v.co.copy() for v in me.vertices];chosen=[];keep=[]
 for t in me.loop_triangles:
  ps=[coords[i] for i in t.vertices];c=sum(ps,Vector())/3;normal=(ps[1]-ps[0]).cross(ps[2]-ps[0]).normalized()
  (chosen if selector(c,normal) else keep).append((list(t.vertices),me.polygons[t.polygon_index].material_index))
 if len(chosen)<4:return
 d=next(k for k in range(3) if k not in axes)
 polygons=[Polygon([(coords[i][axes[0]],coords[i][axes[1]]) for i in ids]) for ids,m in chosen];union=unary_union([p for p in polygons if p.area>1e-10]).buffer(0)
 # Close only millimetric cracks inside the retained local patch footprint.
 union=union.buffer(.003,join_style=2).buffer(-.003,join_style=2)
 polys=[union] if union.geom_type=='Polygon' else [p for p in union.geoms if p.geom_type=='Polygon']
 ids=[i for tri,m in chosen for i in tri];flat=[Vector((coords[i][axes[0]],coords[i][axes[1]],0)) for i in ids];local=BVHTree.FromPolygons(flat,[(i,i+1,i+2) for i in range(0,len(ids),3)],all_triangles=True)
 unique=list(set(ids));arr=np.array([[coords[i][axes[0]],coords[i][axes[1]],coords[i][d]] for i in unique]);made=[];moves=[]
 def depth(q,fair):
  h=local.find_nearest(Vector((q[0],q[1],0)));ind=h[2]*3;p=barycentric_transform(h[0],*flat[ind:ind+3],*[coords[k] for k in ids[ind:ind+3]])
  if not fair:return p[d]
  delta=arr[:,:2]-np.array(q);ds=np.sum(delta*delta,axis=1);ix=np.argsort(ds)[:min(35,len(arr))];uv=delta[ix];w=np.exp(-ds[ix]/.008);a=np.column_stack([np.ones(len(ix)),uv[:,0],uv[:,1],uv[:,0]**2,uv[:,0]*uv[:,1],uv[:,1]**2]);coef=np.linalg.lstsq(a*np.sqrt(w[:,None]),arr[ix,2]*np.sqrt(w),rcond=1e-8)[0];value=float(np.clip(coef[0],p[d]-.010,p[d]+.010));moves.append(abs(value-p[d]));return value
 allvs=coords.copy();allfs=[tri for tri,m in keep];mats=[m for tri,m in keep]
 for poly in polys:
  if poly.area<.00001:continue
  boundary=[Vector(p) for p in list(poly.exterior.coords)[:-1]];points=boundary.copy();lo=poly.bounds[:2];hi=poly.bounds[2:]
  for a in np.arange(lo[0]+.008,hi[0],.016):
   for b in np.arange(lo[1]+.008,hi[1],.016):
    p=Point(a,b)
    if poly.contains(p) and poly.exterior.distance(p)>.004:points.append(Vector((a,b)))
  cv,ce,cf,ov,*_=delaunay_2d_cdt(points,[],[list(range(len(boundary)))],1,1e-7);offset=len(allvs)
  for j,q in enumerate(cv):
   fixed=bool(ov[j] and min(ov[j])<len(boundary));p=Vector((0,0,0));p[axes[0]]=q[0];p[axes[1]]=q[1];p[d]=depth(q,not fixed);allvs.append(p)
  for f in cf:
   center=sum((cv[k] for k in f),Vector((0,0)))/len(f)
   if not poly.covers(Point(center)):continue
   vv=[offset+i for i in f];normal=(allvs[vv[1]]-allvs[vv[0]]).cross(allvs[vv[2]]-allvs[vv[0]])
   if normal[d]*sign>0:vv.reverse()
   allfs.append(vv);mats.append(0);made.append(vv)
 oldmats=list(me.materials);new=bpy.data.meshes.new(name);new.from_pydata(allvs,[],allfs);new.update()
 for m in oldmats:new.materials.append(m)
 for f,m in zip(new.polygons,mats):f.material_index=m
 bm=bmesh.new();bm.from_mesh(new);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00015);loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bm.to_mesh(new);bm.free();body.data=new;finish(body,1.5)
 report['repairs'].append({'part':name,'source_triangles':len(chosen),'replacement_triangles':len(made),'maximum_local_depth_change_m':max(moves,default=0)})
for sign in [-1,1]:
 repair_chart('Wing bumper corner '+str(sign),lambda c,n:sign*c.x>.80 and -1.90<c.y<-1.12 and .575<c.z<.725 and sign*n.x<-.32,(1,2),sign)
repair_chart('Nose bumper seam',lambda c,n:abs(c.x)<.76 and c.y<-1.78 and .55<c.z<.74 and n.y>.65,(0,2),-1)
