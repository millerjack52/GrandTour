"""Authored safari Porsche. Donor measurements, never donor body polygons.
Front -Y, left +X, up Z. Design table in donor units, output metres.
"""
import bpy,bmesh,math,json,hashlib
import faulthandler
faulthandler.enable();faulthandler.dump_traceback_later(180,repeat=True)
from pathlib import Path
from math import sin,cos,pi,sqrt
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
S=4.5
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
OUT=ROOT/'porsche-authored-v01';OUT.mkdir(exist_ok=True)
DEST=OUT/'Porsche_Safari_Complete.blend'
MAN=OUT/'delivery-manifest.json'
if DEST.exists() and MAN.exists():
 if hashlib.sha256(DEST.read_bytes()).hexdigest()!=json.loads(MAN.read_text())['blend_sha256']:
  raise RuntimeError('Delivery edited outside generator. Use a new revision, preserve current file.')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'porsche-wing-study-v01/Porsche_FL_Wing_Study.blend'))
sc=bpy.context.scene
# Reuse only the deliberately rebuilt wheels; no rejected donor surfaces survive.
for o in list(bpy.data.objects):
 if not o.name.startswith('Wheel_'):bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):
 if not c.objects and not c.children:bpy.data.collections.remove(c)
cols={}
for n in ['01 Body panels','02 Glass and seals','03 Lights and trim','04 Interior','05 Running gear','06 Safari equipment','07 Studio']:
 c=bpy.data.collections.new(n);sc.collection.children.link(c);cols[n]=c
BODY=cols['01 Body panels'];GLASS=cols['02 Glass and seals'];TRIM=cols['03 Lights and trim'];CABIN=cols['04 Interior'];GEAR=cols['05 Running gear'];KIT=cols['06 Safari equipment'];STUDIO=cols['07 Studio']
for o in list(sc.objects):
 for c in list(o.users_collection):c.objects.unlink(o)
 GEAR.objects.link(o);o.hide_render=False;o.hide_set(False)
 for m in o.data.materials if o.type=='MESH' else []:
  if m and m.use_nodes:
   p=m.node_tree.nodes.get('Principled BSDF')
   if p and 'steel' in m.name:p.inputs['Roughness'].default_value=.38

def mat(name,c,metal=0,rough=.42):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
paint=mat('Safari - warm ivory enamel',(.64,.66,.61),.27,.30)
black=mat('Safari - rubber and gaskets',(.019,.025,.028),0,.68)
under=mat('Safari - wheelhouse coating',(.035,.042,.044),0,.72)
metal=mat('Safari - graphite hardware',(.09,.112,.12),.65,.31)
silver=mat('Safari - satin alloy',(.48,.52,.54),.8,.24)
amber=mat('Safari - amber lens',(.9,.235,.022),.05,.24)
red=mat('Safari - red lens',(.48,.025,.018),.05,.22)
cream=mat('Safari - lamp reflector',(.72,.75,.68),.8,.18)
glass=mat('Safari - transparent window glass',(.36,.49,.53),.0,.075)
gp=glass.node_tree.nodes.get('Principled BSDF');gp.inputs['Transmission Weight'].default_value=.98;gp.inputs['IOR'].default_value=1.45
lens=mat('Safari - clear lamp glass',(.86,.90,.89),0,.12);lens.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.75
cloth=mat('Safari - tobacco upholstery',(.24,.13,.076),0,.87)
stitch=mat('Safari - seat insert',(.34,.225,.13),0,.85)
dashmat=mat('Safari - charcoal cabin',(.055,.064,.06),0,.84)
accent=mat('Safari - muted ochre',(.52,.30,.07),.15,.40)
labelmat=mat('Safari - lettering',(.76,.78,.7),0,.5)

def active(o):
 for a in bpy.context.selected_objects:a.select_set(False)
 o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def finish(o,smooth=True):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 for p in o.data.polygons:p.use_smooth=smooth
 o.data.set_sharp_from_angle(angle=.85)
 return o
def mesh(n,vs,fs,m=paint,c=BODY,smooth=True):
 me=bpy.data.meshes.new(n);me.from_pydata([tuple(Vector(p)*S) for p in vs],[],fs);me.update();o=bpy.data.objects.new(n,me);c.objects.link(o);me.materials.append(m)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bm.to_mesh(me);bm.free()
 finish(o,smooth);return o
def sheet(o,thick=.0015):
 active(o);md=o.modifiers.new('Physical sheet thickness','SOLIDIFY');md.thickness=thick;md.offset=-1;md.use_even_offset=False;md.thickness_clamp=.5;md.use_thickness_angle_clamp=True;bpy.ops.object.modifier_apply(modifier=md.name);return finish(o)
def bevel(o,w=.001,seg=3):
 active(o);md=o.modifiers.new('Crafted edge radius','BEVEL');md.width=w*S;md.segments=seg;bpy.ops.object.modifier_apply(modifier=md.name);finish(o);return o
def box(n,loc,dim,m=paint,c=TRIM,r=.002):
 bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(loc)*S);o=bpy.context.object;o.name=n;o.dimensions=Vector(dim)*S;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for co in list(o.users_collection):co.objects.unlink(o)
 c.objects.link(o);o.data.materials.append(m)
 if r:bevel(o,min(r,min(dim)*.4))
 return finish(o)
def rod(n,pts,r,m=black,c=TRIM,cyclic=False,res=8):
 cu=bpy.data.curves.new(n,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r*S;cu.bevel_resolution=2;cu.resolution_u=2;cu.use_fill_caps=True
 sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,co in zip(sp.points,pts):p.co=(*tuple(Vector(co)*S),1)
 sp.use_cyclic_u=cyclic;o=bpy.data.objects.new(n,cu);c.objects.link(o);cu.materials.append(m);active(o);bpy.ops.object.convert(target='MESH');o=bpy.context.object
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.to_mesh(o.data);bm.free();return finish(o)
def cylinder(n,loc,r,depth,m=metal,c=TRIM,axis=(0,0,1),verts=32):
 bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r*S,depth=depth*S,location=Vector(loc)*S);o=bpy.context.object;o.name=n;o.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler()
 for co in list(o.users_collection):co.objects.unlink(o)
 c.objects.link(o);o.data.materials.append(m);bevel(o,min(.0006,depth*.12));return o
def interp(vals,x):
 xs=[v[0] for v in vals];ys=[v[1] for v in vals];n=len(xs)
 if x<=xs[0]:return ys[0]
 if x>=xs[-1]:return ys[-1]
 h=[xs[i+1]-xs[i] for i in range(n-1)];d=[(ys[i+1]-ys[i])/h[i] for i in range(n-1)];sl=[d[0]]+[0.]*(n-2)+[d[-1]]
 for i in range(1,n-1):
  if d[i-1]*d[i]>0:
   a=2*h[i]+h[i-1];b=h[i]+2*h[i-1];sl[i]=(a+b)/(a/d[i-1]+b/d[i])
 k=next(i for i in range(n-1) if xs[i]<=x<=xs[i+1]);t=(x-xs[k])/h[k]
 return (2*t**3-3*t*t+1)*ys[k]+(t**3-2*t*t+t)*h[k]*sl[k]+(-2*t**3+3*t*t)*ys[k+1]+(t**3-t*t)*h[k]*sl[k+1]
def sample_profile(ps,steps=3):
 curves=[[(i,p[k]) for i,p in enumerate(ps)] for k in range(3)]
 return [tuple(interp(curves[k],j/steps) for k in range(3)) for j in range((len(ps)-1)*steps+1)]
def grid(n,rows,m=paint,c=BODY,thickness=True):
 N=len(rows[0]);vs=[p for row in rows for p in row];fs=[(i*N+j,(i+1)*N+j,(i+1)*N+j+1,i*N+j+1) for i in range(len(rows)-1) for j in range(N-1)]
 o=mesh(n,vs,fs,m,c)
 if thickness:sheet(o)
 return o
def mirror(o,n):
 cp=o.copy();cp.data=o.data.copy();cp.name=n;BODY.objects.link(cp)
 for v in cp.data.vertices:v.co.x=-v.co.x
 finish(cp);return cp
def bvh(o):
 o.data.calc_loop_triangles();return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)

sections=[[-.455,.139,.135,.132,.127],[-.44,.147,.142,.139,.132],[-.425,.156,.150,.148,.138],[-.419,.160,.155,.155,.140],[-.410,.1665,.174,.187,.170],[-.400,.172,.190,.206,.181],[-.390,.1778,.199,.212,.189],[-.370,.186,.203,.215,.199],[-.350,.195,.207,.217,.208],[-.330,.202,.212,.220,.212],[-.300,.212,.216,.223,.216],[-.270,.219,.220,.225,.218],[-.240,.225,.224,.227,.219],[-.210,.229,.227,.229,.219],[-.180,.233,.231,.230,.217],[-.155,.235,.234,.231,.215]]
def fh(y,k):return interp([(r[0],r[k]) for r in sections],y)
YC=-.29126;ZC=.085205;RY=.1055;RZ=.0995
def archdata(yc,ry=RY,rz=RZ,n=32):
 a0=math.asin((.091-ZC)/rz);return [(yc-ry*cos(a),ZC+rz*sin(a),a) for a in [a0+(pi-2*a0)*i/n for i in range(n+1)]]
fa=archdata(YC);frontys=sorted(set([-.455,-.449,-.44,-.43,-.425,-.419,-.414]+[r[0] for r in fa]+[-.170,-.162,-.155]))
# Front wing primary rows preserve the successful component section controls.
frontrows=[];fouter=[];findices=[]
for y in frontys:
 ar=min(fa,key=lambda q:abs(q[0]-y));isarc=abs(ar[0]-y)<1e-7
 if isarc:z=ar[1];xo=.214+.0085*sin(ar[2]);findices.append(len(frontrows))
 elif y<fa[0][0]:z=.091;xo=interp([(-.455,.16),(-.44,.176),(-.419,.193),(fa[0][0],.214)],y)
 else:z=.091;xo=interp([(fa[-1][0],.214),(-.155,.198)],y)
 zs=max(fh(y,4),z+.020)
 # Nose widths taper before the headlamp, preserving the wing/bonnet boundary.
 k=max(0,min(1,(y+.455)/.036));x2=.137+.003*k;x3=.149+.011*k;x4=.155+.021*k;x5=.157+.035*k
 controls=[(.125,y,fh(y,1)),(x2,y,fh(y,2)),(x3,y,fh(y,3)),(x4,y,fh(y,3)-.001),(x5,y,zs),((x5+xo-.003)/2,y,(zs+z+.014)/2),(xo-.003,y,z+.012),(xo,y,z+.006),(xo-.0005,y,z+.002),(xo-.003,y,z)]
 frontrows.append(sample_profile(controls,4));fouter.append((xo-.003,y,z))
front=grid('Body_FrontWing_L',frontrows,thickness=False)
def add_returns(o,outer):
 rows=[[(x-d,y,z+(.0006 if d else 0)) for d in [0,.002,.005,.010,.017]] for x,y,z in outer]
 ret=grid('Temporary return',rows,thickness=False);active(o);ret.select_set(True);bpy.ops.object.join()
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 # Lock tessellation before the headlight boolean to keep both skin layers consistent.
 if o.name=='Body_FrontWing_L':bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if f.calc_center_median().y<-.39*S and f.calc_center_median().z>.14*S])
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();sheet(o,.001)
def tub(name,outer,ids):
 rows=[]
 for i in ids:
  x,y,z=outer[i];rows.append([(x-.017,y,z+.0006),(x-.042,y,z+.0006),(.132,y,z+.0006),(.132,y,.073)])
 o=grid(name,rows,under,GEAR);return o
add_returns(front,fouter);fl=tub('Wheelhouse_FL',fouter,findices)
# Circular real headlight aperture, projected bezel follows the new wing surface.
def headlamp(wing,s):
 center=Vector((s*.159,-.402,.183));normal=Vector((0,-.956,.293)).normalized();u=Vector((1,0,0));v=normal.cross(u).normalized();tree=bvh(wing)
 cutter=cylinder('TEMP lamp aperture',center,.023,.10,black,TRIM,normal,64)
 active(wing);md=wing.modifiers.new('Actual headlamp aperture','BOOLEAN');md.operation='DIFFERENCE';md.solver='EXACT';md.object=cutter;bpy.ops.object.modifier_apply(modifier=md.name);bpy.data.objects.remove(cutter,do_unlink=True)
 loops=[]
 for radius,offset in [(.027,.0001),(.0248,.0020),(.022,.0038),(.0207,.0035)]:
  loop=[]
  for j in range(64):
   a=2*pi*j/64;p=center+(u*cos(a)+v*sin(a))*radius
   hit=tree.ray_cast((p+normal*.09)*S,-normal,.20*S)[0]
   if hit is None:hit=p*S
   loop.append(tuple(hit/S+normal*offset))
  loops.append(loop)
 fs=[(i*64+j,i*64+(j+1)%64,(i+1)*64+(j+1)%64,(i+1)*64+j) for i in range(3) for j in range(64)]
 o=mesh('Headlamp_'+str(s)+'_fitted_bezel',[p for l in loops for p in l],fs,silver,TRIM);sheet(o,.001)
 # Lens follows the fitted inner rim, with a deliberately shallow crown.
 rim=[Vector(p) for p in loops[-1]];mid=sum(rim,Vector())/64
 vr=[tuple(mid+normal*.0015)]+[tuple(p) for p in rim];o=mesh('Headlamp_'+str(s)+'_lens',vr,[(0,j+1,(j+1)%64+1) for j in range(64)],lens,TRIM);sheet(o,.001)
 cylinder('Headlamp_'+str(s)+'_reflector',mid-normal*.006,.0205,.010,cream,TRIM,normal,48)
 for a in [-.012,-.006,0,.006,.012]:
  h=sqrt(.019**2-a*a);rod('Headlamp fluting', [mid+u*a-v*h-normal*.0004,mid+u*a+v*h-normal*.0004],.00024,cream,TRIM)
print('Constructed front surface',flush=True)
headlamp(front,1)
print('Fitted front lamps',flush=True)
fr=mirror(front,'Body_FrontWing_R');flr=mirror(fl,'Wheelhouse_FR')
# Mirror the deliberately authored optical parts, not the donor.
for o in list(TRIM.objects):
 if o.name.startswith('Headlamp'):
  cp=o.copy();cp.data=o.data.copy();cp.name=o.name+'_R';TRIM.objects.link(cp);cp.location.x=-cp.location.x
  if abs(o.location.length)<1e-7:
   for vv in cp.data.vertices:vv.co.x=-vv.co.x
  else:cp.scale.x*=-1
  if cp.type=='MESH':finish(cp)
# Bonnet surface shares every longitudinal station with the front wings.
hoodrows=[]
for i,y in enumerate(frontys):
 edge=frontrows[i][0][2];crown=interp([(-.455,.008),(-.4,.005),(-.3,.004),(-.2,.010),(-.155,.013)],y)
 hoodrows.append([(x,y,edge+crown*(1-(x/.125)**2)) for x in [-.125+.25*j/32 for j in range(33)]])
hood=grid('Body_Bonnet',hoodrows)
for s in [-1,1]:rod('Bonnet reveal seal '+str(s),[(s*.125,y,fh(y,1)-.0002) for y in frontys],.00048,black)

# Door pressing shares the successful rear row's shoulder, crown and sill.
doorY=[-.155+i*.275/32 for i in range(33)]
def belt(y):return interp([(-.155,.230),(-.05,.232),(.10,.234),(.16,.232),(.24,.229),(.30,.221),(.35,.211),(.40,.200),(.465,.174)],y)
def beltx(y):return interp([(-.155,.176),(.35,.176),(.465,.158)],y)
doorrows=[]
for y in doorY:
 t=(y+.155)/.275;bulge=.0018*sin(pi*t);z=belt(y)
 ps=[(.176,y,z),(.192,y,.215),(.1935+bulge,y,.160),(.195,y,.103),(.198,y,.097),(.1975,y,.093),(.195,y,.091)]
 row=sample_profile(ps,4)
 # End is exactly the front wing section excluding its upper brow, resampled by height.
 if abs(y+.155)<1e-7:row=list(frontrows[-1][12:])
 doorrows.append(row)
door=grid('Body_Door_L',doorrows);mirror(door,'Body_Door_R')
# New broad rear haunch uses the same rounded lip/return construction as the front.
RYR=.1055;RZR=.0995;rc=.26758;ra=archdata(rc,RYR,RZR)
rearys=sorted(set([.12,.13,.14,.15]+[p[0] for p in ra]+[.383,.397,.411,.425,.44,.455,.465]))
rrows=[];router=[];rindices=[]
for y in rearys:
 ar=min(ra,key=lambda q:abs(q[0]-y));isarc=abs(ar[0]-y)<1e-7
 if isarc:z=ar[1];xo=.216+.010*sin(ar[2]);rindices.append(len(rrows))
 elif y<ra[0][0]:z=.091;xo=interp([(.12,.198),(ra[0][0],.216)],y)
 else:z=.091;xo=interp([(ra[-1][0],.216),(.425,.20),(.465,.185)],y)
 zs=max(belt(y)-.015,z+.020);sx=min(.192,xo-.007)
 ps=[(beltx(y),y,belt(y)),(sx,y,zs),((sx+xo-.003)/2,y,(zs+z+.014)/2),(xo-.003,y,z+.012),(xo,y,z+.006),(xo-.0005,y,z+.002),(xo-.003,y,z)]
 row=sample_profile(ps,4)
 if abs(y-.12)<1e-7:
  # Resample the exact door trailing boundary; stitch interface has one coordinate owner.
  row=list(doorrows[-1])
 rrows.append(row);router.append(row[-1])
rearwing=grid('Body_RearQuarter_L',rrows,thickness=False);add_returns(rearwing,router);mirror(rearwing,'Body_RearQuarter_R')
rl=tub('Wheelhouse_RL',router,rindices);mirror(rl,'Wheelhouse_RR')

# Roof eave and centre crown are measured separately, not extruded from a side outline.
roofspec=[[-.155,.248,.176,.230],[-.12,.279,.158,.249],[-.08,.3106,.155,.278],[-.04,.3387,.149,.303],[-.02,.341,.147,.315],[0,.3429,.148,.321],[.04,.3441,.150,.325],[.08,.3444,.150,.326],[.12,.3421,.148,.323],[.16,.3375,.146,.316],[.20,.3317,.143,.305],[.24,.324,.137,.291],[.28,.3072,.129,.270],[.32,.2808,.122,.245],[.35,.260,.119,.230]]
def roofval(y,k):return interp([(r[0],r[k]) for r in roofspec],y)
def rooffn(y,u):
 width=roofval(y,2);z=roofval(y,1)+(roofval(y,3)-roofval(y,1))*abs(u)**3;x=width*u
 if y<-.142:
  w=(y+.155)/.013
  if abs(x)<=.125:base=fh(-.155,1)+.013*(1-(x/.125)**2)
  else:
   sec=frontrows[-1][:13];base=interp([(p[0],p[2]) for p in sec],abs(x))
  z=base*(1-w)+z*w
 return (x,y,z)
roofYs=sorted(set([-.155+i*.505/70 for i in range(71)]+[-.142,-.046,.185,.315]))
us=[-1+i/20 for i in range(41)]
roofrows=[[rooffn(y,u) for u in us] for y in roofYs]
def partition_grid(name,rows,predicate,c=BODY):
 N=len(rows[0]);vs=[p for row in rows for p in row];shell=[];panes={}
 for i in range(len(rows)-1):
  for j in range(N-1):
   f=(i*N+j,(i+1)*N+j,(i+1)*N+j+1,i*N+j+1);tag=predicate(i,j)
   if tag:panes.setdefault(tag,[]).append(f)
   else:shell.append(f)
 def compact(n,faces,ma,co):
  ids=sorted(set(a for f in faces for a in f));mp={a:i for i,a in enumerate(ids)};return mesh(n,[vs[a] for a in ids],[tuple(mp[a] for a in f) for f in faces],ma,co)
 body=compact(name,shell,paint,c);sheet(body,.002)
 for tag,faces in panes.items():
  o=compact(tag,faces,glass,GLASS);sheet(o,.001)
  edgecounts={}
  for f in faces:
   for a,b in zip(f,f[1:]+f[:1]):key=tuple(sorted((a,b)));edgecounts[key]=edgecounts.get(key,0)+1
  boundary={k for k,num in edgecounts.items() if num==1}
  while boundary:
   a,b=boundary.pop();loop=[a,b]
   while loop[-1]!=loop[0]:
    edge=next((k for k in boundary if loop[-1] in k),None)
    if edge is None:break
    boundary.remove(edge);loop.append(edge[0] if edge[1]==loop[-1] else edge[1])
   rod(tag+' gasket',[vs[k] for k in loop[:-1]],.0010,black,GLASS,True)
 return body
def rooftags(i,j):
 y=(roofYs[i]+roofYs[i+1])/2;u=(us[j]+us[j+1])/2
 if -.142<y<-.046 and abs(u)<.90:return 'Glass_Windscreen'
 if .185<y<.315 and abs(u)<.85:return 'Glass_Rear'
 return None
roof=partition_grid('Body_Roof_and_pillars',roofrows,rooftags)
# Side windows have real openings, continuous seals and curved panes.
sideYs=sorted(set([-.155+i*.505/82 for i in range(83)]+[-.12,.108,.128,.288,.12]))
ts=[i/16 for i in range(17)]
def sidefn(y,t,s=1):
 x=.176*(1-t)+roofval(y,2)*t+.001*sin(pi*t)*min(1,max(0,(roofval(y,3)-belt(y))/.025));z=belt(y)*(1-t)+roofval(y,3)*t
 return (s*x,y,z)
for s in [1,-1]:
 rows=[[sidefn(y,t,s) for t in ts] for y in sideYs]
 def tags(i,j):
  y=(sideYs[i]+sideYs[i+1])/2;t=(ts[j]+ts[j+1])/2
  if -.12<y<.108 and .125<t<.875:return 'Glass_Door_'+str(s)
  if .128<y<.288 and .18<t<.85:return 'Glass_Quarter_'+str(s)
  return None
 partition_grid('Body_Cabin_side_'+str(s),rows,tags)
 # Rain gutter follows the roof edge; door waist trim follows the body boundary.
 rod('Roof drip rail '+str(s),[(s*roofval(y,2),y,roofval(y,3)) for y in roofYs],.0008,paint)
 rod('Window waist seal '+str(s),[(s*.176,y,belt(y)+.0001) for y in sideYs if y<.29],.0007,black)

# Rear engine cover: explicit cross-sections meet cabin end and rear-quarter shoulder.
tailYs=[.35,.36,.375,.39,.41,.43,.45,.465];tailrows=[]
tailstart=[sidefn(.35,t,-1) for t in ts[:-1]]+list(roofrows[-1])+[sidefn(.35,t,1) for t in reversed(ts[:-1])]
for y in tailYs:
 cz=interp([(.35,.260),(.36,.253),(.4,.2327),(.43,.218),(.465,.192)],y);ze=belt(y)
 row=[]
 for p in tailstart:
  x=p[0]/.176*beltx(y)
  if abs(x)<.119:z=cz+(interp([(.35,.230),(.40,.221),(.465,.182)],y)-cz)*(abs(x)/.119)**3
  else:z=interp([( .119,interp([(.35,.230),(.40,.221),(.465,.182)],y)),(beltx(y),ze)],abs(x))
  row.append((x,y,z))
 tailrows.append(tailstart if y==.35 else row)
tail=grid('Body_Engine_cover',tailrows)
# Closed front and rear fascia use perimeter rows as their exact top edges.
def fascia(n,top,w,y):
 vs=top+[(w,y,.080),(-w,y,.080)];o=mesh(n,vs,[tuple(range(len(vs)))],paint,BODY,False)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();sheet(o,.002);return o
fronttop=[(-p[0],p[1],p[2]) for p in reversed(frontrows[0])]+hoodrows[0][1:-1]+frontrows[0]
fascia('Body_Nose_fascia',fronttop,.157,-.455)
backtop=[(-p[0],p[1],p[2]) for p in reversed(rrows[-1])]+tailrows[-1][1:-1]+rrows[-1]
fascia('Body_Tail_fascia',backtop,.182,.465)
print('Body and cabin openings constructed',flush=True)
# Explicit backed seams. These sit inward of the exterior and never chord across an arch.
for s in [-1,1]:
 for yy,row in [(-.155,doorrows[0]),(.12,doorrows[-1])]:
  rr=[(s*p[0],p[1],p[2]) for p in row];rod('Door vertical seal',rr,.00065,black)
  grid('Door inward jamb',[[tuple(p) for p in rr],[(p[0]-s*.004,p[1],p[2]) for p in rr]],under,GEAR)
 rod('Door bottom seal',[(s*row[-1][0],row[-1][1],row[-1][2]) for row in doorrows],.00065,black)
 # Rocker terminates before wheel openings; it does not run through either arch.
 box('Rocker '+str(s),(s*.192,-.0175,.080),(.016,.275,.018),paint,BODY,.003)
 box('Sill scuff insert '+str(s),(s*.194,-.0175,.090),(.010,.253,.003),black,TRIM,.0008)

# Cabin pan full width between inner wheelhouse walls, wings under both seats.
floorrows=[]
for y in [-.40,-.35,-.20,-.16,-.1,0,.10,.15,.20,.35,.43]:
 width=.132 if y<-.17 or y>.16 else .188
 floorrows.append([(-width,y,.073),(0,y,.073),(width,y,.073)])
floor=grid('Cabin_full_floor',floorrows,under,CABIN)
# Nose and engine-bay pans close the remaining overhangs, forward/behind tyre keep-outs.
for name,edge in [('Front_overhang_undertray',[(x,y,z) for x,y,z in fouter if y<=fa[0][0]+1e-7]),('Rear_overhang_undertray',[(x,y,z) for x,y,z in router if y>=ra[-1][0]-1e-7])]:
 panrows=[]
 for x,y,z in edge:
  w=x-.017;panrows.append([(-w,y,z+.0006),(-.12,y,.083),(0,y,.083),(.12,y,.083),(w,y,z+.0006)])
 grid(name,panrows,under,GEAR)
grid('Cabin_front_bulkhead',[[(-.132,-.166,.073),(.132,-.166,.073)],[(-.172,-.155,.23),(.172,-.155,.23)]],dashmat,CABIN)
grid('Cabin_rear_bulkhead',[[(-.132,.174,.073),(.132,.174,.073)],[(-.165,.174,.232),(.165,.174,.232)]],dashmat,CABIN)
box('Central tunnel',(0,-.017,.101),(.044,.292,.053),dashmat,CABIN,.009)
for s in [-1,1]:
 box('Chassis longitudinal rail',(s*.10,0,.069),(.013,.78,.012),under,GEAR,.002)
 for y in [YC,rc]:
  rod('Axle',[(s*.03,y,.070),(s*.198,y,.0852)],.008,metal,GEAR)
  rod('Suspension arm',[(s*.095,y-.025,.071),(s*.197,y,.0852)],.006,metal,GEAR)
  rod('Damper',[(s*.14,y-.012,.13),(s*.195,y,.082)],.0035,silver,GEAR)
 # Seats kept between the tubs, bolsters formed with rounded solids.
 x=s*.091
 for xx in [x-.031,x+.031]:
  box('Seat floor rail',(xx,.005,.079),(.009,.152,.007),metal,CABIN,.001)
  for yfoot in [-.047,.057]:box('Seat mounting foot',(xx,yfoot,.075),(.014,.017,.007),metal,CABIN,.001)
 box('Seat base',(x,.025,.108),(.098,.120,.041),cloth,CABIN,.01)
 box('Seat cushion insert',(x,.016,.130),(.062,.092,.012),stitch,CABIN,.005)
 back=box('Seat back',(x,.074,.205),(.102,.033,.15),cloth,CABIN,.012);back.rotation_euler.x=.11
 box('Seat back insert',(x,.055,.201),(.064,.008,.100),stitch,CABIN,.003)
 for xx in [x-.015,x+.015]:rod('Headrest post',[(xx,.074,.265),(xx,.074,.283)],.002,silver,CABIN)
 box('Seat headrest',(x,.073,.284),(.075,.029,.039),cloth,CABIN,.009)
 for xx in [x-.028,x+.028]:rod('Seat piping',[(xx,-.029,.133),(xx,.055,.133)],.0007,labelmat,CABIN)
 # Belt webbing and buckle mounted beside each seat.
 grid('Seat belt webbing', [[(s*x,y-.004,z),(s*x,y+.004,z)] for x,y,z in [(.145,.113,.288),(.140,.060,.14),(.126,.04,.109)]],black,CABIN)
 box('Belt buckle',(x-s*.052,.055,.132),(.009,.017,.024),metal,CABIN,.002)
 box('Belt release',(x-s*.052,.052,.146),(.007,.008,.003),red,CABIN,.0005)
 # Fitted internal door panel and mechanical fittings.
 card=box('Door card '+str(s),(s*.182,-.018,.162),(.008,.233,.123),dashmat,CABIN,.005)
 box('Interior door insert',(s*.176,-.01,.174),(.006,.164,.058),cloth,CABIN,.004)
 rod('Interior grab handle',[(s*.171,-.022,.181),(s*.164,-.015,.177),(s*.164,.036,.177),(s*.171,.044,.181)],.0025,black,CABIN)
 box('Door pocket',(s*.173,.001,.119),(.017,.126,.026),black,CABIN,.003)
 # Exterior pull and mirror mount physically contact the panel.
 box('Door handle base',(s*.1935,.088,.202),(.004,.044,.012),black,TRIM,.003)
 rod('Door handle',[(s*.196,.073,.204),(s*.202,.078,.204),(s*.202,.102,.204),(s*.196,.106,.204)],.0026,metal,TRIM)
 box('Mirror mounting shoe',(s*.179,-.092,.23),(.012,.026,.008),black,TRIM,.002)
 rod('Mirror stalk',[(s*.181,-.092,.23),(s*.204,-.085,.247),(s*.214,-.077,.249)],.003,metal,TRIM)
 box('Mirror cap',(s*.215,-.078,.252),(.037,.021,.026),paint,TRIM,.006)
 box('Mirror glass',(s*.215,-.0665,.252),(.029,.0016,.019),silver,TRIM,.003)
 # Mud flap and fastened bracket seated at each rear arch endpoint.
 for ar,lab in [(fa,'F'),(ra,'R')]:
  y=ar[-1][0]+.003
  box('Mudflap clamp '+lab,(s*.193,y,.086),(.054,.006,.009),metal,GEAR,.001)
  box('Mudflap rubber '+lab,(s*.193,y+.001,.061),(.054,.003,.052),black,GEAR,.001)
  for xx in [s*.175,s*.21]:cylinder('Flap fixing',(xx,y+.003,.086),.0016,.002,silver,GEAR,(0,1,0),8)
# Dashboard: curved upper pad, visible five-dial cluster and proper steering column.
box('Dashboard upper pad',(0,-.117,.220),(.30,.05,.030),dashmat,CABIN,.007)
box('Dashboard face',(0,-.096,.207),(.311,.008,.035),dashmat,CABIN,.004)
for i,x in enumerate([.034,.062,.092,.122,.148]):
 r=.014 if i==2 else .011
 cylinder('Instrument bezel '+str(i),(x,-.089,.215),r,.005,silver,CABIN,(0,1,0),40)
 cylinder('Instrument dial '+str(i),(x,-.0858,.215),r*.87,.0008,black,CABIN,(0,1,0),40)
 for j in range(12):
  a=j*2*pi/12;rod('Dial tick',[(x+r*.68*cos(a),-.0849,.215+r*.68*sin(a)),(x+r*.82*cos(a),-.0849,.215+r*.82*sin(a))],.00026,labelmat,CABIN)
 rod('Dial needle',[(x,-.0845,.215),(x+r*.65*cos(1.1),-.0845,.215+r*.65*sin(1.1))],.00035,accent,CABIN)
for x in [-.12,-.057]:
 box('Dash vent',(x,-.090,.218),(.045,.006,.014),black,CABIN,.001)
 for j in range(4):box('Vent vane',(x,-.086,.213+j*.003),(.040,.001,.0007),metal,CABIN,.0002)
box('Glovebox',( -.10,-.089,.191),(.102,.004,.022),dashmat,CABIN,.002)
box('Glovebox latch',(-.10,-.086,.194),(.017,.002,.004),silver,CABIN,.001)
rod('Steering column',[(.092,-.099,.192),(.092,-.050,.207)],.006,metal,CABIN)
stcent=Vector((.092,-.047,.207));sn=Vector((0,.96,.28));sx=Vector((1,0,0));sy=sn.cross(sx)
rod('Steering rim',[stcent+sx*.034*cos(a)+sy*.034*sin(a) for a in [2*pi*j/64 for j in range(64)]],.0035,black,CABIN,True)
for a in [pi/6,5*pi/6,3*pi/2]:rod('Steering spoke',[stcent,stcent+sx*.031*cos(a)+sy*.031*sin(a)],.003,metal,CABIN)
cylinder('Steering hub',stcent,.010,.007,black,CABIN,sn)
rod('Gear stick',[(0,-.009,.12),(.002,-.014,.169)],.002,metal,CABIN)
box('Gear knob',(.002,-.014,.171),(.011,.012,.013),black,CABIN,.004)
rod('Handbrake',[(.023,.024,.117),(.023,-.003,.137)],.003,black,CABIN)
for x in [.07,.091,.112]:box('Pedal',(x,-.141,.103),(.012,.022,.004),metal,CABIN,.001)
box('Rear luggage shelf',(0,.136,.148),(.26,.067,.036),dashmat,CABIN,.006)

# Bumpers follow the plan taper; all tubes terminate on supports.
for end,y in [('Front',-.462),('Rear',.468)]:
 pts=[(-.18,y+(.018 if y<0 else -.018),.112),(-.145,y,.112),(-.075,y+(-.004 if y<0 else .004),.112),(0,y+(-.006 if y<0 else .006),.112),(.075,y+(-.004 if y<0 else .004),.112),(.145,y,.112),(.18,y+(.018 if y<0 else -.018),.112)]
 rod(end+' painted bumper',pts,.0095,paint,TRIM)
 rod(end+' rubber rub strip',[(x,yy+(-.007 if y<0 else .007),z) for x,yy,z in pts],.0032,black,TRIM)
 for s in [-1,1]:
  box(end+' bumper mount',(s*.105,y+(.022 if y<0 else -.022),.106),(.015,.045,.018),metal,GEAR,.002)
  box(end+' bumper overrider',(s*.13,y,.111),(.018,.018,.036),black,TRIM,.004)
# Clear rectangular signal cassettes, with recess, bezel and fitted lens.
for s in [-1,1]:
 box('Front indicator housing',(s*.15,-.451,.133),(.044,.012,.013),black,TRIM,.002)
 box('Front indicator lens',(s*.15,-.458,.133),(.039,.003,.010),amber,TRIM,.001)
 box('Tail lamp housing',(s*.134,.465,.160),(.077,.010,.020),black,TRIM,.003)
 box('Tail red lens',(s*.12,.471,.160),(.042,.003,.016),red,TRIM,.002)
 box('Tail amber lens',(s*.16,.4705,.160),(.031,.003,.016),amber,TRIM,.002)
 box('Reverse lens',(s*.098,.471,.160),(.013,.003,.016),cream,TRIM,.002)
 for j in range(8):rod('Taillamp lens rib',[(s*(.102+j*.008),.473,.153),(s*(.102+j*.008),.473,.167)],.0003,silver,TRIM)
 cylinder('Tailpipe',(s*.083,.458,.085),.009,.056,metal,TRIM,(0,1,0))
 cylinder('Exhaust dark bore',(s*.083,.4865,.085),.0068,.001,black,TRIM,(0,1,0))
 # Front recovery eye and shackle.
 rod('Front bullbar stanchion',[(s*.15,-.44,.096),(s*.17,-.478,.102),(s*.17,-.482,.150)],.0045,metal,KIT)
 rod('Rear protection stay',[(s*.14,.438,.098),(s*.18,.479,.10),(s*.18,.483,.141)],.0045,metal,KIT)
 rod('Recovery shackle',[(s*.115+.006*cos(a),-.483,.087+.008*sin(a)) for a in [2*pi*j/32 for j in range(32)]],.0018,accent,KIT,True)
rod('Front protection cross tube',[(-.17,-.482,.15),(-.14,-.491,.15),(0,-.497,.15),(.14,-.491,.15),(.17,-.482,.15)],.0045,metal,KIT)
rod('Rear protection cross tube',[(-.18,.483,.141),(-.14,.49,.141),(.14,.49,.141),(.18,.483,.141)],.0045,metal,KIT)
for s in [-1,1]:
 cylinder('Auxiliary lamp case',(s*.10,-.488,.166),.020,.012,metal,KIT,(0,-1,0))
 cylinder('Auxiliary lamp rim',(s*.10,-.495,.166),.0185,.003,silver,KIT,(0,-1,0))
 cylinder('Auxiliary reflector',(s*.10,-.497,.166),.0163,.002,cream,KIT,(0,-1,0))
 rod('Auxiliary lamp bracket',[(s*.10,-.49,.15),(s*.10,-.488,.166)],.003,metal,KIT)
grid('Front alloy bash plate',[[(-.126,-.444,.102),(.126,-.444,.102)],[(-.118,-.407,.06),(.118,-.407,.06)],[(-.105,-.27,.06),(.105,-.27,.06)]],silver,GEAR)
for x in [-.085,-.043,0,.043,.085]:rod('Bash plate formed rib',[(x,-.40,.059),(x,-.29,.059)],.0018,metal,GEAR)
# Ducktail is a closed pedestal whose bottom follows the engine deck across its width.
def deckheight(x,y):
 cz=interp([(.35,.260),(.36,.253),(.4,.2327),(.43,.218),(.465,.192)],y)
 ze=interp([(.35,.230),(.40,.221),(.465,.182)],y)
 if abs(x)<.119:return cz+(ze-cz)*(abs(x)/.119)**3
 return interp([(.119,ze),(beltx(y),belt(y))],abs(x))
spoiler=[]
for x in [-.147+.294*j/36 for j in range(37)]:
 edge=.12+.88*(1-(abs(x)/.147)**8)
 # Each cross-section starts/ends on the actual deck; a modest integral ducktail.
 spoiler.append([(x,.395,deckheight(x,.395)),(x,.414,deckheight(x,.414)+.010*edge),(x,.438,deckheight(x,.438)+.030*edge),(x,.452,deckheight(x,.452)+.040*edge),(x,.456,deckheight(x,.456)+.034*edge),(x,.456,deckheight(x,.456)),(x,.43,deckheight(x,.43)),(x,.41,deckheight(x,.41))])
sv=[p for row in spoiler for p in row];sf=[];N=8
for i in range(len(spoiler)-1):
 for j in range(N):sf.append((i*N+j,(i+1)*N+j,(i+1)*N+(j+1)%N,i*N+(j+1)%N))
sf += [tuple(reversed(range(N))),tuple((len(spoiler)-1)*N+j for j in range(N))]
mesh('Body_Ducktail',sv,sf,paint,BODY)
for j in range(12):
 y=.350+j*.0035;z=interp([(.35,.260),(.36,.253),(.4,.2327)],y)
 rod('Engine grille slat',[(-.077,y,z+.001),(0,y,z+.002),(.077,y,z+.001)],.0012,black,TRIM)
# Wipers lie on the glass instead of occupying the interior or floating above the cowl.
for s in [-1,1]:
 pivot=Vector(rooffn(-.148,s*.55))+Vector((0,0,.0013));middle=Vector(rooffn(-.127,s*.43))+Vector((0,0,.0013));pts=[pivot,middle]
 rod('Wiper arm '+str(s),pts,.0012,metal,TRIM)
 rod('Wiper blade '+str(s),[Vector(rooffn(-.128+.006*u,s*u))+Vector((0,0,.0015)) for u in [.08+i*.74/16 for i in range(17)]],.0011,black,TRIM)
 cylinder('Wiper spindle',pivot,.003,.004,metal,TRIM)
# Rack built from repeatable rails with four roof-mounted pads.
for s in [-1,1]:
 for y in [.0,.18]:
  z=rooffn(y,.76)[2];x=s*roofval(y,2)*.76
  box('Rack foot pad',(x,y,z+.0015),(.026,.021,.005),black,KIT,.003)
  rod('Rack mounting riser',[(x,y,z+.003),(s*.13,y,.358)],.0035,metal,KIT)
for z in [.357,.383]:
 rod('Rack perimeter',[( -.13,-.067,z),(-.145,-.052,z),(-.145,.205,z),(-.13,.221,z),(.13,.221,z),(.145,.205,z),(.145,-.052,z),(.13,-.067,z)],.0032,metal,KIT,True)
for y in [-.035,.025,.085,.145,.20]:
 rod('Rack floor crossbar',[(-.143,y,.357),(.143,y,.357)],.0025,metal,KIT)
 for s in [-1,1]:rod('Rack vertical upright',[(s*.145,y,.357),(s*.145,y,.383)],.0024,metal,KIT)
# Spare wheel occupies the original roof-spare envelope.
def torus(n,loc,major,minor,m,c,rot=(0,0,0)):
 bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=12,location=Vector(loc)*S,major_radius=major*S,minor_radius=minor*S,rotation=rot);o=bpy.context.object;o.name=n
 for cc in list(o.users_collection):cc.objects.unlink(o)
 c.objects.link(o);o.data.materials.append(m);finish(o);return o
torus('Roof spare tyre',(-.028,.023,.379),.058,.018,black,KIT)
cylinder('Roof spare steel centre',(-.028,.023,.384),.042,.016,metal,KIT)
for j in range(5):
 a=j*2*pi/5;cylinder('Spare wheel lug',(-.028+.022*cos(a),.023+.022*sin(a),.394),.0028,.004,silver,KIT,verts=8)
for x in [-.068,.012]:
 rod('Spare retention strap',[(x,-.055,.357),(x,-.048,.400),(x,.026,.402),(x,.098,.399),(x,.103,.357)],.0036,accent,KIT)
box('Roof equipment case',(0,.157,.384),(.202,.091,.047),accent,KIT,.006)
for x in [-.068,.068]:box('Case rubber mounting foot',(x,.157,.360),(.025,.060,.006),black,KIT,.002)
box('Roof case lid',(0,.157,.410),(.205,.094,.009),accent,KIT,.003)
for x in [-.065,.065]:
 rod('Case tie down',[(x,.107,.359),(x,.108,.416),(x,.205,.416),(x,.207,.359)],.0025,black,KIT)
 box('Case buckle',(x,.106,.388),(.014,.003,.013),metal,KIT,.001)
rod('Case handle',[(-.023,.106,.398),(-.018,.098,.398),(.018,.098,.398),(.023,.106,.398)],.0025,black,KIT)

# A few readable exterior details without hiding the body under decals.
box('Rear numberplate carrier',(0,.474,.133),(.092,.005,.025),black,TRIM,.002)
box('Rear numberplate',(0,.477,.134),(.085,.001,.019),labelmat,TRIM,.001)
def textobj(n,txt,loc,size,rot,m):
 cu=bpy.data.curves.new(n,'FONT');cu.body=txt;cu.align_x='CENTER';cu.size=size*S;cu.extrude=.00008*S;o=bpy.data.objects.new(n,cu);TRIM.objects.link(o);o.location=Vector(loc)*S;o.rotation_euler=rot;cu.materials.append(m);active(o);bpy.ops.object.convert(target='MESH');o=bpy.context.object;bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.to_mesh(o.data);bm.free();return o
textobj('Plate text','GT  /  911',(0,.478,.129),.011,(pi/2,0,pi),black)
textobj('Rear script','S A F A R I',(0,.469,.181),.008,(pi/2,0,pi),silver)
for s in [-1,1]:
 cylinder('Fuel filler cap',(s*.196,-.184,.196),.012,.002,paint,TRIM,(s,0,0))
 box('Side indicator',(s*.194,-.20,.214),(.003,.013,.005),amber,TRIM,.001)

# Metres, editable per-component objects and genuine wheel-centre pivots.
print('Interior and safari kit constructed',flush=True)
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
for o in list(sc.objects):
 if o.type=='MESH':
  active(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  if not o.data.uv_layers:
   active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.0,island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
  o['asset_role']='authored_component' if not o.name.startswith('Wheel_') else 'reused_authored_wheel'

sc.world=bpy.data.worlds.new('Porsche studio');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.36,.40,.45,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.55
print('UV layouts created',flush=True)
for loc,energy,size in [((3,-4,6),1700,5),((-4,-1,3),1200,4),((1,5,5),1900,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=energy;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,.7))-o.location).to_track_quat('-Z','Y').to_euler()
 for c in list(o.users_collection):c.objects.unlink(o)
 STUDIO.objects.link(o)
bpy.ops.object.camera_add();cam=bpy.context.object;sc.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=5.7
sc.render.resolution_x=1500;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='AgX'
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world.color=(.16,.17,.18)
def render(n,pos,target=(0,0,.90),scale=5.7):
 cam.data.ortho_scale=scale;cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for name,pos in [('clay-quarter',(5,-7,3.3)),('clay-side',(6,0,.9)),('clay-front',(0,-8,.9)),('clay-rear',(0,8,.9)),('clay-top',(0,0,8)),('clay-rear-quarter',(5,7,2.8)),('clay-underside',(4,-5,-4))]:render(name,pos,scale=7.5 if name=='clay-top' else 5.7)
# Diagnostic with wheels hidden exposes actual tubs and their joins.
wheelobs=[o for o in sc.objects if o.name.startswith('Wheel_')]
for o in wheelobs:o.hide_render=True
render('wheel-off',(4,-5,1.8))
for o in wheelobs:o.hide_render=False
# Cabin cutaway shows floor coverage, seat feet and fitted dashboard.
hide=[o for o in BODY.objects]+list(GLASS.objects)+list(KIT.objects)+list(TRIM.objects)
for o in hide:o.hide_render=True
render('interior-cutaway',(3.8,-4,3.8),(0,-.15,.85),3.7)
render('dashboard',(0,.5,1.75),(0,-.45,.91),1.65)
for o in hide:o.hide_render=False
wiremat=mat('Review topology',(.009,.013,.017),0,.7);wirecopies=[]
for o in BODY.objects:
 if o.type!='MESH':continue
 cp=o.copy();cp.data=o.data.copy();STUDIO.objects.link(cp);cp.name='STUDIO_WIRE_'+o.name;cp.data.materials.clear();cp.data.materials.append(wiremat)
 for p in cp.data.polygons:p.material_index=0
 mod=cp.modifiers.new('Actual mesh edges','WIREFRAME');mod.thickness=.00065;mod.use_replace=True;mod.use_boundary=True;wirecopies.append(cp)
render('wireframe',(5,-7,3.3))
for o in wirecopies:bpy.data.objects.remove(o,do_unlink=True)
ground=box('STUDIO_GROUND',(0,0,-.035),(200,200,.04),mat('Studio ground',(.16,.19,.20),0,.82),STUDIO,.0)
sc.render.engine='CYCLES';sc.cycles.samples=48;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=12
render('beauty-quarter',(5,-7,3.3));render('beauty-rear',(5,7,2.8))
ground.hide_set(True);ground.hide_render=True
# Store a sensible review camera and viewport; no donor, cages or guide fragments visible.
cam.location=(5,-7,3.3);cam.rotation_euler=(Vector((0,0,.9))-cam.location).to_track_quat('-Z','Y').to_euler()
for o in sc.objects:o.select_set(False)
hood.select_set(True);bpy.context.view_layer.objects.active=hood
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':a.spaces.active.region_3d.view_location=(0,0,.9);a.spaces.active.region_3d.view_distance=6;a.spaces.active.overlay.show_extras=False;a.spaces.active.shading.type='MATERIAL'
note=bpy.data.texts.new('READ ME - authored Porsche');note.write('Complete static modelling revision. Authored body, real glazed openings, closed wheelhouses and passenger pan, two-seat interior, lights, bumpers and safari kit. Donor body triangles are not reused. Existing clean wheel components retained. Panels separated; no opening-panel animation rig, LODs or Unreal setup. Inspect validation-report.json and all diagnostic renders before claiming game readiness.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(DEST))
for o in sc.objects:o.select_set(o.type=='MESH' and not o.name.startswith('STUDIO_'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'Porsche_Safari_Complete.glb'),export_format='GLB',use_selection=True,export_apply=True)
MAN.write_text(json.dumps({'blend_sha256':hashlib.sha256(DEST.read_bytes()).hexdigest(),'source':'porshceoffroadtripo.glb','body_method':'Authored measured cross-sections; original donor body not reused','status':'Complete static modelling revision pending saved-file QA','remaining_engine_work':['Animation rig','Steering/suspension sweep','LODs','Collision','Unreal integration']},indent=2))
(OUT/'shape-spec.json').write_text(json.dumps({'scale':S,'front_sections':sections,'roof_sections':roofspec,'wheel_centres':[[s*.2,y,ZC] for s in [-1,1] for y in [YC,rc]],'shape_authority':'Original Tripo dimensions and visible form; rejected donor topology replaced','interfaces':'Bonnet/front wing longitudinal stations; cabin eave shared by roof and side; wheel return and tub generated from same arch; doors with inward jambs','not_factory_blueprint':True},indent=2))
print('PORSCHE_AUTHORED_SAVED',str(DEST),flush=True)


