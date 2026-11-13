"""Remove the donor notch from the rear pane and rebuild its matching seal."""
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import MultiPoint,Polygon,Point
from shapely.ops import triangulate,nearest_points
from mathutils.geometry import delaunay_2d_cdt,barycentric_transform
old=bpy.data.objects['Rear glass'];half=len(old.data.vertices)//2;points=[v.co.copy() for v in old.data.vertices[:half]]
poly=MultiPoint([(p.x,p.z) for p in points]).convex_hull.buffer(-.006,quad_segs=4).buffer(.006,quad_segs=4)
arr=np.array([[p.x,p.z,p.y] for p in points]);a=np.column_stack([np.ones(len(arr)),arr[:,0],arr[:,1],arr[:,0]**2,arr[:,0]*arr[:,1],arr[:,1]**2]);coef=np.linalg.lstsq(a,arr[:,2],rcond=None)[0]
old.data.calc_loop_triangles();oldtri=[t for t in old.data.loop_triangles if all(i<half for i in t.vertices)];optical_flat=[Vector((old.data.vertices[i].co.x,old.data.vertices[i].co.z,0)) for t in oldtri for i in t.vertices];optical_real=[old.data.vertices[i].co.copy() for t in oldtri for i in t.vertices];optical=BVHTree.FromPolygons(optical_flat,[(i,i+1,i+2) for i in range(0,len(optical_flat),3)],all_triangles=True)
def depth(q):
 x,z=q;h=optical.find_nearest(Vector((x,z,0)));idx=h[2]*3;p=barycentric_transform(Vector((x,z,0)),*optical_flat[idx:idx+3],*optical_real[idx:idx+3]);return p.y
me=body.data;me.calc_loop_triangles();vv=[];ff=[];mi=[];cut=0
for t in me.loop_triangles:
 ps=[me.vertices[i].co.copy() for i in t.vertices];c=sum(ps,Vector())/3;flat=[Vector((p.x,p.z,0)) for p in ps];tp=Polygon([(p.x,p.z) for p in ps])
 if abs(c.y-depth((c.x,c.z)))<.055 and tp.area>1e-10 and tp.intersects(poly):
  diff=tp.difference(poly);chunks=[diff] if diff.geom_type=='Polygon' else [g for g in getattr(diff,'geoms',[]) if g.geom_type=='Polygon'];cut+=1
  for chunk in chunks:
   for tri in triangulate(chunk):
    if not chunk.covers(tri.representative_point()):continue
    verts=[barycentric_transform(Vector((x,z,0)),*flat,*ps) for x,z in list(tri.exterior.coords)[:-1]]
    if (verts[1]-verts[0]).cross(verts[2]-verts[0]).dot((ps[1]-ps[0]).cross(ps[2]-ps[0]))<0:verts.reverse()
    ff.append(tuple(range(len(vv),len(vv)+3)));vv.extend(verts);mi.append(me.polygons[t.polygon_index].material_index)
 else:ff.append(tuple(range(len(vv),len(vv)+3)));vv.extend(ps);mi.append(me.polygons[t.polygon_index].material_index)
new=bpy.data.meshes.new('Body with repaired rear glazing aperture');new.from_pydata(vv,[],ff);new.update()
for m in me.materials:new.materials.append(m)
for f,i in zip(new.polygons,mi):f.material_index=i
bm=bmesh.new();bm.from_mesh(new);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001);bm.to_mesh(new);bm.free();body.data=new;finish(body,1.4)
boundary=[Vector(poly.exterior.interpolate(i/200,normalized=True).coords[0]) for i in range(200)];p2=boundary.copy()
for x in np.arange(poly.bounds[0],poly.bounds[2],.035):
 for z in np.arange(poly.bounds[1],poly.bounds[3],.025):
  if poly.contains(Point(x,z)):p2.append(Vector((x,z)))
cv,ce,cf,*_=delaunay_2d_cdt(p2,[],[list(range(200))],1,1e-7)
delete(old);pane=mesh('Rear glass',[(q.x,depth(q),q.y) for q in cv],cf,glassmat,GLASS);thick(pane,.002)
w=next(w for w in spec['windows'] if w['name']=='Rear glass');N=w['outer_ring_vertices'];outer=poly.buffer(.027,quad_segs=4);bt=tree(body);vs=[]
outerpoints=[Vector(outer.exterior.interpolate(i/N,normalized=True).coords[0]) for i in range(N)];innerpoints=[Vector(nearest_points(poly.exterior,Point(p))[0].coords[0]) for p in outerpoints]
for t,h in [(0,.003),(.18,.007),(.80,.007),(1,.001)]:
 for p,q in zip(outerpoints,innerpoints):
  u=p.lerp(q,t);v=Vector((u.x,depth(u)+h,u.y))
  if t==0:
   hit=bt.find_nearest(v)
   if hit[3]<.055:v=hit[0]
  vs.append(v)
delete(bpy.data.objects['Rear glass fitted surround']);rim=mesh('Rear glass fitted surround',vs,[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(3) for i in range(N)],paint,GLASS);rim.data.materials.append(rubber)
for f in rim.data.polygons:f.material_index=1 if f.index>=N else 0
thick(rim,.004)
# Recess old flange lips beneath the continuous replacement seal.
rt=tree(rim)
for v in body.data.vertices:
 q=Point(v.co.x,v.co.z)
 if outer.contains(q) and not poly.buffer(-.002).contains(q):
  h=rt.ray_cast(v.co+Vector((0,.055,0)),Vector((0,-1,0)),.11)
  if h[0] is not None and 0<v.co.y-h[0].y+.003<.04:v.co.y=h[0].y-.003
body.data.update()
report['repairs'].append({'part':'Rear glazing','operation':'Closed source notch within original pane extents; continuous rounded seal and matching aperture','source_triangles_cut':cut})
