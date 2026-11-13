# Connected cabin reconstruction around the accepted glazing and roof envelope.
exec(open('C:/GrandTour/Art/VehicleTools/repair_porsche_windows_v05.py').read().split('# Rebuild each complete side')[0])
from shapely.ops import nearest_points
from shapely.geometry import LineString
original=tree(body)
fits={}
panepolys={}
for key,names,axis in [('L',['Vent glass L','Door glass L','Quarter glass L'],0),('R',['Vent glass R','Door glass R','Quarter glass R'],0),('F',['Windscreen'],1),('B',['Rear glass'],1)]:
 points=[v.co.copy() for n in names for v in bpy.data.objects[n].data.vertices];fits[key]=surface_fit(points,axis)
 for name in names:
  other=[i for i in range(3) if i!=axis]
  panepolys[name]=MultiPoint([(v.co[other[0]],v.co[other[1]]) for v in bpy.data.objects[name].data.vertices]).convex_hull.buffer(-.008,quad_segs=8).buffer(.008,quad_segs=8)
def S(side,y,z):return fits[side](y,z)+(1 if side=='L' else -1)*.014
def F(x,z):return fits['F'](x,z)-.014
def B(x,z):return fits['B'](x,z)+.014-.30*(max(0,abs(x)-.59)/.17)**2
def terms(x,y):return [1,y,y*y,y**3,x*x,x**4,x**6,x*x*y,x*x*y*y]
rp=[]
for x in np.linspace(-.66,.66,35):
 for y in np.linspace(-.18,1.12,48):
  hit=original.ray_cast(Vector((x,y,1.8)),Vector((0,0,-1)),.45)
  if hit[0] is not None and hit[1].z>.40 and hit[0].z>1.35:rp.append(hit[0])
co=np.linalg.lstsq(np.array([terms(p.x,p.y) for p in rp]),np.array([p.z for p in rp]),rcond=None)[0]
print('ROOF CO',co.tolist(),flush=True)
def R(x,y):
 t=max(0,min(1,(y-.65)/.35));return float(np.dot(co,terms(x,y)))+.012*t*t*(3-2*t)
def bisect(fn,a,b):
 xs=np.linspace(a,b,101);pairs=[(x,y) for x,y in zip(xs,xs[1:]) if fn(x)*fn(y)<=0]
 if not pairs:raise ValueError(('Unbracketed surface intersection',a,b,fn(a),fn(b)))
 a,b=pairs[-1]
 for _ in range(45):
  m=(a+b)/2
  if fn(a)*fn(m)<=0:b=m
  else:a=m
 return (a+b)/2
def side_y(side,fun,z):return bisect(lambda y:y-fun(S(side,y,z),z),-1.2,2.1)
def side_z(side,y):return bisect(lambda z:z-R(S(side,y,z),y),.995,1.65)
def corner(side,fun):
 z=bisect(lambda z:z-R(S(side,side_y(side,fun,z),z),side_y(side,fun,z)),.995,1.58)
 y=side_y(side,fun,z);return Vector((S(side,y,z),y,z))
corners={(s,k):corner(s,f) for s in ['L','R'] for k,f in [('F',F),('B',B)]}
print('CORNERS',dict((str(k),list(v)) for k,v in corners.items()),flush=True)
ZBASE=.995
# Shared boundary polylines: side/front, side/rear, roof/side, roof/front/rear.
curves={}
for s in ['L','R']:
 for k,fun in [('F',F),('B',B)]:
  cs=corners[s,k];curve=[]
  for z in np.linspace(ZBASE,cs.z,61):
   y=side_y(s,fun,z);curve.append(Vector((S(s,y,z),y,z)))
  curves[s,k]=curve
 curves[s,'roof']=[Vector((S(s,y,side_z(s,y)),y,side_z(s,y))) for y in np.linspace(corners[s,'F'].y,corners[s,'B'].y,151)]
for k,fun in [('F',F),('B',B)]:
 curve=[]
 for x in np.linspace(corners['R',k].x,corners['L',k].x,151):
  z=bisect(lambda z:z-R(x,fun(x,z)),.995,1.62);curve.append(Vector((x,fun(x,z),z)))
 curves[k,'roof']=curve

# Remove all old upper-cabin layers, preserving the bonnet and rear deck.
# Plane cuts retain original interpolated coordinates at every boundary.
Y0=-.96;Y1=1.88
def clip(poly,axis,bound,positive):
 inside=[];outside=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=(a[axis]-bound)*(1 if positive else -1);db=(b[axis]-bound)*(1 if positive else -1)
  (inside if da>=-1e-9 else outside).append(a)
  if (da>=0)!=(db>=0):
   q=a.lerp(b,da/(da-db));inside.append(q);outside.append(q)
 return inside,outside
me=body.data;me.calc_loop_triangles();vs=[];fs=[]
for t in me.loop_triangles:
 poly=[me.vertices[i].co.copy() for i in t.vertices];kept=[]
 for ax,b,positive in [(2,ZBASE,True),(1,Y0,True),(1,Y1,False)]:
  if len(poly)<3:break
  poly,out=clip(poly,ax,b,positive)
  if len(out)>=3:kept.append(out)
 for p in kept:
  for i in range(1,len(p)-1):fs.append((len(vs),len(vs)+1,len(vs)+2));vs.extend([p[0],p[i],p[i+1]])
me=bpy.data.meshes.new('Retained lower body and decks');me.from_pydata(vs,[],fs);me.materials.append(paint);body.data=me;clean(me)
# Save the newly cut donor boundaries for the lower mating skirt.
bm=bmesh.new();bm.from_mesh(me)
cutedges=[]
for e in bm.edges:
 if not e.is_boundary:continue
 a,b=[v.co.copy() for v in e.verts]
 onz=abs(a.z-ZBASE)<1e-5 and abs(b.z-ZBASE)<1e-5
 ony=any(abs(a.y-y)<1e-5 and abs(b.y-y)<1e-5 for y in [Y0,Y1])
 if (onz and Y0-.001<a.y<Y1+.001) or (ony and min(a.z,b.z)>=ZBASE-.001):cutedges.append((a,b))
bm.free()

panels=[];basecurves=[]
for s,sgn in [('L',1),('R',-1)]:
 front=curves[s,'F'];back=curves[s,'B'];roof=curves[s,'roof'];base=[Vector((S(s,y,ZBASE),y,ZBASE)) for y in np.linspace(front[0].y,back[0].y,151)];basecurves+=list(zip(base,base[1:]))
 loop=front+roof[1:]+list(reversed(back))[1:]+list(reversed(base))[1:]
 panels.append((s,0,sgn,Polygon([(p.y,p.z) for p in loop]),lambda y,z,s=s:S(s,y,z),['Vent glass '+s,'Door glass '+s,'Quarter glass '+s],[Vector((p.y,p.z)) for p in loop]))
for k,sgn,fun,name in [('F',-1,F,'Windscreen'),('B',1,B,'Rear glass')]:
 left=curves['L',k];right=curves['R',k];top=curves[k,'roof'];base=[Vector((x,fun(x,ZBASE),ZBASE)) for x in np.linspace(right[0].x,left[0].x,151)];basecurves+=list(zip(base,base[1:]))
 loop=right+top[1:]+list(reversed(left))[1:]+list(reversed(base))[1:]
 panels.append((k,1,sgn,Polygon([(p.x,p.z) for p in loop]),fun,[name],[Vector((p.x,p.z)) for p in loop]))
roofloop=curves['F','roof']+curves['L','roof'][1:]+list(reversed(curves['B','roof']))[1:]+list(reversed(curves['R','roof']))[1:]
roofpoly=Polygon([(p.x,p.y) for p in roofloop]).buffer(0)
vs,fs=cdt_surface(roofpoly,[],R,2,1,[Vector((p.x,p.y)) for p in roofloop],True);shell=mesh('Connected roof and aperture shell',vs,fs,paint,Vector((0,0,1)))
if 'Cabin | fitted headliner' in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects['Cabin | fitted headliner'],do_unlink=True)
iv,iff=cdt_surface(roofpoly.buffer(-.016),[],lambda x,y:R(x,y)-.018,2,-1)
liner=mesh('Cabin | fitted headliner',iv,iff,trim,Vector((0,0,-1)));thick(liner,.003)
for key,axis,sign,domain,fit,names,sharedpoints in panels:
 domain=domain.buffer(0);holes=[panepolys[n].buffer(.012,quad_segs=8) for n in names]
 for h in holes:assert domain.covers(h),str((key,domain.bounds,h.bounds))
 vs,fs=cdt_surface(domain,holes,fit,axis,sign,sharedpoints,True);normal=Vector();normal[axis]=sign
 metal=mesh(key+' connected aperture metal',vs,fs,paint,normal);join_patch(shell,metal,1)
 other=[i for i in range(3) if i!=axis]
 def lift(p,off=0):
  q=Vector();q[other[0]]=p.x;q[other[1]]=p.y;q[axis]=fit(p.x,p.y)+sign*off;return q
 for name,hole in zip(names,holes):
  gp=panepolys[name];outerpts=resample(hole);innerpts=[Vector(nearest_points(gp.exterior,Point(p))[0].coords[0]) for p in outerpts];N=len(outerpts);vs=[]
  for t,off in [(0,0),(.2,.003),(.8,.003),(1,-.004)]:
   vs += [lift(p.lerp(q,t),off) for p,q in zip(outerpts,innerpts)]
  seal=mesh(name+' | clean gasket',vs,[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(3) for i in range(N)],rubber,normal);thick(seal,.004)
  gv,gf=cdt_surface(gp,[],lambda u,v:fit(u,v)-sign*.006,axis,sign);gl=mesh(name+' | fitted pane',gv,gf,glassmat,normal);thick(gl,.002)
  rv=[lift(p,off) for off in [0,-.026] for p in outerpts];ro=mesh(name+' | cabin reveal',rv,[(i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N)],trim,normal);thick(ro,.003)
  for oldname in [name,name+' fitted surround','Cabin | '+name+' aperture return']:
   if oldname in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[oldname],do_unlink=True)
 rep['patches'].append({'panel':key,'apertures':names,'domain':list(domain.bounds),'projection_boundary':list(domain.exterior.coords)})

# Close the bottom interface to the retained source cut with a complete annulus.
# Its outer contour follows the actual bonnet, beltline and rear-deck cuts.
outer=[]
def sidex(y,sgn):
 h=original.ray_cast(Vector((sgn*1.25,y,ZBASE)),Vector((-sgn,0,0)),.7)[0]
 return h.x if h else sgn*.84
def deckz(x,y):
 h=original.ray_cast(Vector((x,y,1.14)),Vector((0,0,-1)),.30)[0]
 return max(ZBASE,h.z if h else ZBASE)
for y in np.linspace(Y0,Y1,251):outer.append(Vector((sidex(y,1),y,ZBASE)))
for x in np.linspace(sidex(Y1,1),sidex(Y1,-1),151)[1:]:outer.append(Vector((x,Y1,deckz(x,Y1))))
for y in np.linspace(Y1,Y0,251)[1:]:outer.append(Vector((sidex(y,-1),y,ZBASE)))
for x in np.linspace(sidex(Y0,-1),sidex(Y0,1),151)[1:]:outer.append(Vector((x,Y0,deckz(x,Y0))))
outer2=LineString([(p.x,p.y) for p in outer+[outer[0]]])
outerseg=list(zip(outer,outer[1:]+outer[:1]))
basepoints=[a for a,b in basecurves]
basecenter=Vector((0,.45,0));basepoints.sort(key=lambda p:math.atan2(p.y-.45,p.x))
inner2=LineString([(p.x,p.y) for p in basepoints+[basepoints[0]]])
def at_ring(line,segments,theta):
 ray=LineString([(0,.45),(4*math.cos(theta),.45+4*math.sin(theta))]);q=ray.intersection(line)
 if q.geom_type=='MultiPoint':q=min(q.geoms,key=lambda q:q.distance(Point(0,.45)))
 xy=Vector(q.coords[0]);best=None;dist=1e9
 for a,b in segments:
  av=Vector((a.x,a.y));bv=Vector((b.x,b.y));d=bv-av;t=max(0,min(1,(xy-av).dot(d)/max(d.length_squared,1e-12)));ds=(av+d*t-xy).length_squared
  if ds<dist:dist=ds;best=a.lerp(b,t)
 return best
innerseg=list(zip(basepoints,basepoints[1:]+basepoints[:1]));vs=[];N=720
for i in range(N):
 theta=math.tau*i/N;vs.extend([at_ring(inner2,innerseg,theta),at_ring(outer2,outerseg,theta)])
fs=[(2*i,2*i+1,2*((i+1)%N)+1,2*((i+1)%N)) for i in range(N)]
bridge=mesh('Complete cabin beltline and deck transition',vs,fs,paint,Vector((0,0,1)));thick(bridge,.004);join_patch(body,bridge,4)
bm=bmesh.new();bm.from_mesh(shell.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
round_edges=[e for e in bm.edges if e.is_manifold and min(v.co.z for v in e.verts)>1.05 and e.calc_face_angle()>.20]
# Shared vertices carry a continuous fitted normal; no independent edge strips.
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(shell.data);bm.free();clean(shell.data);thick(shell,.004);shell.name='Cabin | rebuilt exterior shell'
# Surface-derived normals avoid triangle-size dependent ripples at shared joins.
surfaces=[(2,1,R,roofpoly)]+[(a,sg,f,d) for k,a,sg,d,f,n,pts in panels]
def surface_normal(p):
 total=Vector();weight=0
 for ax,sg,fn,dom in surfaces:
  oth=[k for k in range(3) if k!=ax];u,v=p[oth[0]],p[oth[1]]
  if dom.distance(Point(u,v))>.035:continue
  h=.0001;du=(fn(u+h,v)-fn(u-h,v))/(2*h);dv=(fn(u,v+h)-fn(u,v-h))/(2*h);n=Vector();n[ax]=sg;n[oth[0]]=-sg*du;n[oth[1]]=-sg*dv
  dist=abs(p[ax]-fn(u,v))/n.length
  if dist>.035:continue
  w=(1-dist/.035)**2/(dist+.004)**2;total+=n.normalized()*w;weight+=w
 return total.normalized() if weight else p.normalized()
vn=[surface_normal(v.co) for v in shell.data.vertices];ln=[None]*len(shell.data.loops)
for f in shell.data.polygons:
 for li in f.loop_indices:
  n=vn[shell.data.loops[li].vertex_index];dot=f.normal.dot(n)
  ln[li]=n if dot>.25 else (-n if dot<-.25 else f.normal)
shell.data.normals_split_custom_set(ln)

# Match the retained cut vertices to the smooth, sampled outer mating contour.
def nearest_contour(p,segments):
 best=None;bd=1e9
 for a,b in segments:
  ab=b-a;t=max(0,min(1,(p-a).dot(ab)/max(ab.length_squared,1e-12)));q=a+ab*t;d=(q-p).length_squared
  if d<bd:best=q;bd=d
 return best,math.sqrt(bd)
for v in body.data.vertices:
 p=v.co;oncut=(abs(p.z-ZBASE)<1e-5 and Y0-.001<p.y<Y1+.001) or (any(abs(p.y-y)<1e-5 for y in [Y0,Y1]) and p.z>=ZBASE-.001)
 if oncut:
  q,d=nearest_contour(p,outerseg)
  if d<.02:v.co=q
clean(body.data)
# Coincident source skin layers must retain separate topology at point contacts.
bm=bmesh.new();bm.from_mesh(body.data);touching=[e for e in bm.edges if len(e.link_faces)>2]
if touching:bmesh.ops.split_edges(bm,edges=touching)
bm.to_mesh(body.data);bm.free()
rep['retained_skin_point_contacts_separated']=len(touching)

"""
def nearestbase(p):
 best=None;bd=1e9
 for a,b in basecurves:
  ab=b-a;t=max(0,min(1,(p-a).dot(ab)/max(ab.length_squared,1e-12)));q=a+ab*t;d=(q-p).length_squared
  if d<bd:best=q;bd=d
 return best,math.sqrt(bd)
vs=[];fs=[];maxbridge=0
for a,b in cutedges:
 c,dc=nearestbase(b);d,dd=nearestbase(a)
 if max(dc,dd)>.25:continue
 maxbridge=max(maxbridge,dc,dd);fs.append(tuple(range(len(vs),len(vs)+4)));vs.extend([a,b,c,d])
bridge=mesh('Cabin to retained body interface',vs,fs,paint,Vector((0,0,1)));thick(bridge,.004);join_patch(body,bridge,4)
rep['base_interface']={'source_edges':len(cutedges),'maximum_bridge_m':maxbridge}
"""
rep['base_interface']={'source_edges':len(cutedges),'continuous_transition_quads':N}
# The old footwell bulkhead extended through the newly fitted cowl.
for o in bpy.data.collections['03 Interior'].objects:
 if o.type=='MESH' and (o.name=='Cabin | front footwell bulkhead' or o.name.startswith('Cabin | front kick panel')):
  for v in o.data.vertices:
   if v.co.z>.982:v.co.z=.982
# Discard obsolete reduced meshes; these cannot represent the new aperture topology.
for c in list(bpy.data.collections):
 if c.name.startswith('LOD'):
  for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.collections.remove(c)
for o in [body]+list(COL.objects):
 if o.type!='MESH':continue
 active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
active(body);md=body.modifiers.new('Retained surface shading','WEIGHTED_NORMAL');md.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=md.name)
shell.data.normals_split_custom_set(ln)
sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100;sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_cavity=False;sc.display.shading.show_shadows=False
cam=sc.camera;cam.data.type='ORTHO'
for n,p,t,z in [('side',(7,0,1.1),(0,0,1.0),5.5),('window-left',(4,-3,2.4),(.68,.05,1.25),2.0),('window-right',(-4,-3,2.4),(-.68,.05,1.25),2.0),('quarter',(5,-7,3.5),(0,0,.9),5.5),('rear-window',(4,5,2.4),(0,1.2,1.25),2.4)]:
 cam.location=p;cam.rotation_euler=(Vector(t)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=z;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
active(root);bpy.ops.wm.save_as_mainfile(filepath=str(DEST));rep['blend_sha256']=hashlib.sha256(DEST.read_bytes()).hexdigest();rep['status']='Under construction and close-up review';MAN.write_text(json.dumps(rep,indent=2));print(json.dumps(rep),flush=True)
