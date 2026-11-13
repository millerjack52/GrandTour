"""Replace only the notched rear glazing interface with a common curved surface."""
def repair_rear_glazing(body,pane,rim):
 import bpy,bmesh,sys,numpy as np,math
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 from mathutils.geometry import barycentric_transform,delaunay_2d_cdt
 sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
 from shapely.geometry import Polygon,MultiPoint,Point,LineString
 from shapely.ops import triangulate
 col=pane.users_collection[0];glassmat=pane.data.materials[0];paint=body.data.materials[0];rubber=bpy.data.materials['Fitted rubber glazing seals']
 ps=np.array([list(v.co) for v in pane.data.vertices]);x,y,z=ps.T;A=np.column_stack([np.ones(len(x)),x,z,x*x,x*z,z*z]);co=np.linalg.lstsq(A,y,rcond=None)[0]
 def depth(x,z):return float(np.dot(co,[1,x,z,x*x,x*z,z*z]))
 poly=MultiPoint([(p[0],p[2]) for p in ps]).convex_hull.buffer(-.004,quad_segs=4).buffer(.004,quad_segs=4);outer=poly.buffer(.034,quad_segs=6)
 oldme=body.data;oldme.calc_loop_triangles();bt=BVHTree.FromPolygons([v.co for v in oldme.vertices],[list(t.vertices) for t in oldme.loop_triangles],all_triangles=True)
 vv=[];ff=[];cut=0
 for t in oldme.loop_triangles:
  points=[oldme.vertices[i].co.copy() for i in t.vertices];c=sum(points,Vector())/3;tp=Polygon([(p.x,p.z) for p in points])
  if c.y>.95 and abs(c.y-depth(c.x,c.z))<.12 and tp.area>1e-10 and tp.intersects(poly):
   diff=tp.difference(poly);chunks=[diff] if diff.geom_type=='Polygon' else [g for g in getattr(diff,'geoms',[]) if g.geom_type=='Polygon'];cut+=1;flat=[Vector((p.x,p.z,0)) for p in points]
   for chunk in chunks:
    for tri in triangulate(chunk):
     if not chunk.covers(tri.representative_point()):continue
     vs=[barycentric_transform(Vector((x,z,0)),*flat,*points) for x,z in list(tri.exterior.coords)[:-1]]
     if (vs[1]-vs[0]).cross(vs[2]-vs[0]).dot((points[1]-points[0]).cross(points[2]-points[0]))<0:vs.reverse()
     ff.append(tuple(range(len(vv),len(vv)+3)));vv.extend(vs)
  else:ff.append(tuple(range(len(vv),len(vv)+3)));vv.extend(points)
 def make_data(n,vs,fs,materials):
  me=bpy.data.meshes.new(n);me.from_pydata(vs,[],fs);me.update()
  for m in materials:me.materials.append(m)
  bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001);bm.to_mesh(me);bm.free()
  for p in me.polygons:p.use_smooth=True
  me.set_sharp_from_angle(angle=1.4);return me
 body.data=make_data('Retained body with rear glazing interface',vv,ff,[paint])
 centre=poly.centroid;N=238;innerpts=[];outerpts=[]
 for i in range(N):
  a=2*math.pi*i/N;ray=LineString([(centre.x,centre.y),(centre.x+3*math.cos(a),centre.y+3*math.sin(a))])
  for shape,arr in [(poly,innerpts),(outer,outerpts)]:
   p=shape.exterior.intersection(ray);arr.append(Vector((p.x,p.y)))
 p2=list(innerpts)
 for x in np.arange(poly.bounds[0],poly.bounds[2],.030):
  for z in np.arange(poly.bounds[1],poly.bounds[3],.025):
   if poly.contains(Point(x,z)):p2.append(Vector((x,z)))
 cv,ce,cf,*_=delaunay_2d_cdt(p2,[],[list(range(N))],1,1e-7)
 pane.data=make_data('Continuous rear optical pane',[(p.x,depth(p.x,p.y),p.y) for p in cv],cf,[glassmat])
 rows=[];outerdepth=[]
 for p in outerpts:
  h=bt.ray_cast(Vector((p.x,2.4,p.y)),Vector((0,-1,0)),1.6);yy=h[0].y if h[0] is not None and abs(h[0].y-depth(p.x,p.y))<.15 else depth(p.x,p.y)
  outerdepth.append(yy)
 for t,raise_y in [(0,.002),(.18,.007),(.80,.007),(1,.001)]:
  for p,q,yy in zip(outerpts,innerpts,outerdepth):
   v=p.lerp(q,t);rows.append((v.x,yy*(1-t)+depth(q.x,q.y)*t+raise_y,v.y))
 rim.data=make_data('Common rear glazing seal',rows,[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(3) for i in range(N)],[paint,rubber])
 for f in rim.data.polygons:f.material_index=0 if f.index<N else 1
 rt=BVHTree.FromPolygons([v.co for v in rim.data.vertices],[list(f.vertices) for f in rim.data.polygons])
 for v in body.data.vertices:
  p=v.co
  if p.y>.95 and outer.contains(Point(p.x,p.z)):
   h=rt.ray_cast(p+Vector((0,.15,0)),Vector((0,-1,0)),.30)
   if h[0] is not None and 0<p.y-h[0].y+.005<.10:p.y=h[0].y-.005
 for ob,t in [(pane,.002),(rim,.004)]:
  bm=bmesh.new();bm.from_mesh(ob.data);bm.normal_update()
  if sum(f.normal.y*f.calc_area() for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
  bm.to_mesh(ob.data);bm.free()
  bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
  md=ob.modifiers.new('Closed glazing thickness','SOLIDIFY');md.thickness=t;md.offset=-1;md.use_even_offset=False;bpy.ops.object.modifier_apply(modifier=md.name)
 return {'part':'Rear pane and seal','method':'Original pane extent with corrected local notch, shared curved depth and body opening','body_triangles_cut':cut}
