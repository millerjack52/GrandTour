"""Executed by tidy_porsche_v03.py with its scene/helper context."""
def source_part(i):return next((o for o in parts.objects if o.get('source_island')==i),None)
def bounds(o):
 p=[o.matrix_world@v.co for v in o.data.vertices];return Vector([min(q[k] for q in p) for k in range(3)]),Vector([max(q[k] for q in p) for k in range(3)])
def remove(o):
 report['changed_accessories'].append({'old_name':o.name,'source_island':o.get('source_island'),'operation':'Measured local reconstruction'});bpy.data.objects.remove(o,do_unlink=True)
def box(name,center,size,material=steel,bevel=.004):
 x,y,z=[v/2 for v in size];c=Vector(center);vs=[c+Vector((a*x,b*y,d*z)) for a,b,d in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 o=mesh(name,vs,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],material)
 active(o);md=o.modifiers.new('Rounded manufactured edges','BEVEL');md.width=bevel;md.segments=3;bpy.ops.object.modifier_apply(modifier=md.name);o.data.set_sharp_from_angle(angle=.7)
 md=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');md.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=md.name);return o
def tube(name,points,r,material=steel,closed=False):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=2;cu.use_fill_caps=True;sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
 for p,q in zip(sp.points,points):p.co=(*q,1)
 sp.use_cyclic_u=closed;o=bpy.data.objects.new(name,cu);parts.objects.link(o);cu.materials.append(material);active(o);bpy.ops.object.convert(target='MESH');o=bpy.context.object
 for f in o.data.polygons:f.use_smooth=True
 return o
def ray_body(x,y):
 h=rawtree.ray_cast(Vector((x,y,2.1)),Vector((0,0,-1)),1.2)
 assert h[0] is not None,('No roof support',x,y)
 return h[0]
# Replace the two misshapen horizontal rack loops at the measured envelopes.
rails=[]
for i,label in [(8,'lower'),(9,'upper')]:
 ob=source_part(i);lo,hi=bounds(ob);radius=.012;corner=.11;points=[]
 for cx,cy,a0 in [(hi.x-radius-corner,hi.y-radius-corner,0),(lo.x+radius+corner,hi.y-radius-corner,90),(lo.x+radius+corner,lo.y+radius+corner,180),(hi.x-radius-corner,lo.y+radius+corner,270)]:
  for j in range(9):
   a=math.radians(a0+j*90/8);points.append((cx+corner*math.cos(a),cy+corner*math.sin(a),(lo.z+hi.z)/2))
 z=(lo.z+hi.z)/2;rails.append(z);remove(ob);tube('Rack '+label+' continuous rail',points,radius,closed=True)
# Source upright artifacts on the rail perimeter, identified by position.
for ob in list(parts.objects):
 if 'source_island' not in ob:continue
 lo,hi=bounds(ob)
 if lo.z>1.58 and hi.z<1.77 and (abs((lo.x+hi.x)/2)>.48 or hi.y<-.20 or lo.y>1.0):remove(ob)
for side in [-1,1]:
 for y in [-.15,.23,.66,.96]:tube('Rack upright',[(side*.514,y,rails[0]),(side*.514,y,rails[1])],.010)
for i in [23,26,30]:
 ob=source_part(i)
 if ob:
  lo,hi=bounds(ob);remove(ob);box('Rack crossmember',(lo+hi)/2,(hi.x-lo.x,.034,.030),steel,.005)
for i in [5,18]:
 ob=source_part(i)
 if ob:remove(ob)
for side in [-1,1]:
 for y in [.055,.875]:
  p=ray_body(side*.55,y);box('Rack rubber foot',p+Vector((0,0,.007)),(.090,.110,.016),rubber,.005)
  tube('Rack fitted stanchion',[p+Vector((0,0,.014)),Vector((side*.51,y,rails[0]-.006))],.014)
  tube('Rack diagonal support',[p+Vector((0,.025,.014)),Vector((side*.51,y+.065,rails[0]-.006))],.009)
for ob in list(parts.objects):
 if 'source_island' not in ob:continue
 lo,hi=bounds(ob)
 if lo.z>1.4 and hi.z<1.67 and max(abs(lo.x),abs(hi.x))>.5:remove(ob)
# Pane-conforming wipers, with body-contact pivots and separate blades/arms.
for i in [6,12]:
 ob=source_part(i)
 if ob:remove(ob)
for ob in list(parts.objects):
 if 'source_island' not in ob:continue
 lo,hi=bounds(ob)
 if lo.z>1.055 and hi.z<1.175 and lo.y>-.87 and hi.y<-.45 and lo.x>-.71 and hi.x<.71:remove(ob)
w=bpy.data.objects['Windscreen'];w.data.calc_loop_triangles();wt=BVHTree.FromPolygons([v.co for v in w.data.vertices],[list(t.vertices) for t in w.data.loop_triangles],all_triangles=True)
for k,(a,b,px) in enumerate([(-.46,-.04,-.07),(.18,.61,.57)]):
 ps=[]
 for j in range(15):
  t=j/14;x=a*(1-t)+b*t
  for y in np.arange(-.81,-.38,.003):
   h=wt.ray_cast(Vector((x,y,2)),Vector((0,0,-1)),1.5)
   if h[0] is not None:break
  y+=.020;h=wt.ray_cast(Vector((x,y,2)),Vector((0,0,-1)),1.5)
  assert h[0] is not None,('wiper pane fit',x,y)
  ps.append(h[0]+Vector((0,-.003,.009)))
 tube('Wiper blade '+str(k),ps,.007,rubber);p=rawtree.ray_cast(Vector((px,-.755,1.8)),Vector((0,0,-1)),1.0)[0]
 assert p is not None
 box('Wiper spindle '+str(k),p+Vector((0,0,.012)),(.037,.034,.025),steel,.005)
 tube('Wiper arm '+str(k),[p+Vector((0,0,.025)),ps[7]+Vector((0,-.006,.013))],.006)
# Solid bent handles, fitted to the actual door surface at original centres.
for i in [13,16]:
 ob=source_part(i);lo,hi=bounds(ob);c=(lo+hi)/2;side=1 if c.x>0 else -1;remove(ob)
 h=rawtree.ray_cast(Vector((side*1.3,c.y,c.z)),Vector((-side,0,0)),.7)[0];assert h is not None
 box('Handle mounting escutcheon',h+Vector((side*.005,0,0)),(.013,.175,.035),rubber,.005)
 x=h.x+side*.016
 tube('Door handle grip',[(x,c.y-.07,c.z),(x+side*.025,c.y-.052,c.z),(x+side*.025,c.y+.054,c.z),(x,c.y+.07,c.z)],.011)
# Fix semantically misassigned seat material while keeping their geometry.
for i in [10,11]:
 ob=source_part(i)
 if ob:ob.name='Seat '+('L' if i==10 else 'R');ob.data.materials.clear();ob.data.materials.append(bpy.data.materials['Original tobacco seats'])
# Locally fair the covered roof spare; retain its boundary and global envelope.
ob=source_part(19)
if ob:
 lo,hi=bounds(ob);center=(lo+hi)/2;rx=(hi.x-lo.x)/2;ry=(hi.y-lo.y)/2;remove(ob);vs=[];fs=[];n=48
 profile=[(lo.z,.84),(lo.z+.024,1),(hi.z-.034,1),(hi.z,.84)]
 for z,r in profile:
  for j in range(n):
   a=2*math.pi*j/n;vs.append((center.x+rx*r*math.cos(a),center.y+ry*r*math.sin(a),z))
 for k in range(3):
  for j in range(n):fs.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
 fs.extend([tuple(reversed(range(n))),tuple(3*n+j for j in range(n))]);cover=mesh('Rounded spare cover',vs,fs,rubber);cover.data.set_sharp_from_angle(angle=.4)
 for axis,r in [(0,rx),(1,ry)]:
  ps=[(-r,lo.z+.022),(-r,hi.z-.035),(-r*.84,hi.z+.002),(r*.84,hi.z+.002),(r,hi.z-.035),(r,lo.z+.022)];vs=[]
  for width in [-.019,.019]:
   for u,z in ps:
    p=center.copy();p[axis]+=u;p[1-axis]+=width;p.z=z;vs.append(p)
  strap=mesh('Spare retaining strap',vs,[(j,j+1,6+j+1,6+j) for j in range(5)],steel);thick(strap,.003)
ob=source_part(38)
if ob:
 lo,hi=bounds(ob);center=(lo+hi)/2;size=hi-lo
 for old in list(parts.objects):
  if 'source_island' not in old:continue
  a,b=bounds(old)
  if a.z>lo.z-.01 and a.x>lo.x-.02 and b.x<hi.x+.02 and a.y>lo.y-.02 and b.y<hi.y+.02:remove(old)
 box('Roof toolcase body',(center.x,center.y,(lo.z+hi.z-.024)/2),(size.x-.012,size.y-.012,size.z-.024),paint,.012)
 box('Roof toolcase lid',(center.x,center.y,hi.z-.012),(size.x,size.y,.024),paint,.008)
 for x in [center.x-size.x*.29,center.x+size.x*.29]:
  box('Case buckle',(x,lo.y-.002,hi.z-.045),(.048,.015,.045),steel,.005)
# The Tripo cargo straps are separate islands; remove their torn remnants now
# that the cover, case and attached straps have been reconstructed.
for old in list(parts.objects):
 if 'source_island' not in old:continue
 lo,hi=bounds(old)
 if lo.z>1.55 and hi.z>1.78:remove(old)
# Fitted upper wheelhouse returns. Their outer border is measured directly on
# the unchanged arch; inner depth remains outside the static tyre envelope.
report['arch_returns']=[]
for suffix in ['FL','FR','RL','RR']:
 wheel=[o for o in parts.objects if o.name.startswith('Wheel_'+suffix) and o.type=='MESH'];wp=[o.matrix_world@v.co for o in wheel for v in o.data.vertices]
 assert wp,suffix
 cy=(max(p.y for p in wp)+min(p.y for p in wp))/2;cz=(max(p.z for p in wp)+min(p.z for p in wp))/2;side=1 if sum(p.x for p in wp)>0 else -1
 radius=max(math.hypot(p.y-cy,p.z-cz) for p in wp);edge=[]
 for j in range(65):
  a=math.pi*j/64;vy,vz=math.cos(a),math.sin(a);hit=None
  for r in np.arange(radius+.006,radius+.24,.002):
   h=rawtree.ray_cast(Vector((side*1.4,cy+r*vy,cz+r*vz)),Vector((-side,0,0)),.8)
   if h[0] is not None and side*h[0].x>.865:
    hit=h[0];break
  if hit is not None:edge.append((hit,a,r))
 assert len(edge)>50,(suffix,len(edge))
 vs=[]
 for t in [0,.18,.65,1]:
  for p,a,r in edge:
   q=p.copy();q.x-=side*(.002+.17*t);offset=.001+min(.006,max(0,r-radius-.005))*t;q.y-=offset*math.cos(a);q.z-=offset*math.sin(a);vs.append(q)
 n=len(edge);fs=[(j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i) for j in range(3) for i in range(n-1)]
 # The original already contains connected inner bowls. Retain those surfaces
 # instead of adding an intersecting second sheet over them.
 if rubber.name not in body.data.materials:body.data.materials.append(rubber)
 material_index=list(body.data.materials).index(rubber);assigned=0
 for f in body.data.polygons:
  ps=[body.data.vertices[k].co for k in f.vertices];c=sum(ps,Vector())/len(ps)
  if all(.38<side*p.x<.865 for p in ps) and math.hypot(c.y-cy,c.z-cz)<radius+.15 and c.z<cz+radius+.13:
   f.material_index=material_index;assigned+=1
 report['arch_returns'].append({'wheel':suffix,'sample_count':n,'measured_border_reference_distance_m':max(rawtree.find_nearest(p)[3] for p,a,r in edge),'retained_inner_bowl_faces':assigned,'note':'Existing connected wheelhouse retained; intersecting liner trial discarded; suspension travel not certified'})
# Original concave lamp inserts become reflectors behind fitted closed lenses.
for idx in [47,50]:
 ob=source_part(idx);bb=bmesh.new();bb.from_mesh(ob.data);edges={e for e in bb.edges if e.is_boundary};loops=[]
 while edges:
  e=edges.pop();a,b=e.verts;loop=[a,b]
  while loop[-1]!=loop[0]:
   es=[ee for ee in loop[-1].link_edges if ee in edges]
   if not es:break
   e=es[0];edges.remove(e);loop.append(e.other_vert(loop[-1]))
  if loop[-1]==loop[0]:loops.append(loop[:-1])
 assert loops,('No lamp aperture',idx)
 pts=[ob.matrix_world@v.co for v in max(loops,key=len)];bb.free();ps=[Vector((p.x,p.z)) for p in pts];poly=Polygon(ps).convex_hull;boundary=sampled(poly,.012);c=Vector(poly.centroid.coords[0]);R=max((p-c).length for p in boundary)
 arr=np.array([[1,p.x,p.z] for p in pts]);coef=np.linalg.lstsq(arr,np.array([p.y for p in pts]),rcond=None)[0]
 p2=boundary+[c];cv,ce,cf,*_=delaunay_2d_cdt(p2,[],[list(range(len(boundary)))],1,1e-8)
 vv=[]
 for p in cv:
  depth=float(np.array([1,p.x,p.y])@coef)-.007*max(0,1-((p-c).length/R)**2)
  vv.append((p.x,depth,p.y))
 lm=glassmat.copy();lm.name='Clear headlamp lens';lm.diffuse_color=(.68,.72,.70,1)
 lensob=mesh('Fitted headlamp glass '+str(idx),vv,cf,lm);thick(lensob,.002)
 report['changed_accessories'].append({'source_island':idx,'operation':'Retained reflector geometry and added fitted closed lens'})
