"""Stylized 80-series Land Cruiser, using the accepted wagon's simple shape language.
Independent fresh study; never loads or replaces existing vehicle models.
Blender --background --python this_file -- --output NEW_DIRECTORY
"""
import bpy, math, json, argparse, sys, shutil
from pathlib import Path
from mathutils import Vector

p=argparse.ArgumentParser(); p.add_argument('--output',required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(args.output).resolve()
if out.exists() and any(out.iterdir()): raise RuntimeError('Use an empty revision directory')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
car=bpy.data.collections.new('Land Cruiser 80 — stylized study'); scene.collection.children.link(car)
studio=bpy.data.collections.new('Review studio'); scene.collection.children.link(studio)

def mat(name,c,rough=.6,metal=0):
 m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*c,1)
 bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
 return m
paint=mat('Warm ivory paint',(.63,.575,.425),.57)
rubber=mat('Tyres',(.025,.032,.035),.82)
trim=mat('Charcoal bumpers and seals',(.055,.068,.074),.72)
steel=mat('Satin steel',(.36,.40,.41),.45,.35)
dark=mat('Cabin charcoal',(.055,.059,.056),.92)
fabric=mat('Warm grey seat blocks',(.14,.13,.115),.92)
lamp=mat('Warm ivory lamp',(.80,.78,.61),.34)
amber=mat('Amber indicator',(.95,.37,.025),.35)
red=mat('Rear red',(.55,.025,.016),.34)
glass=mat('Smoky transparent glazing',(.55,.68,.72),.065)
bs=glass.node_tree.nodes.get('Principled BSDF'); bs.inputs['Transmission Weight'].default_value=.95
bs.inputs['IOR'].default_value=1.12

def mesh(name,verts,faces,material,coll=car):
 me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
 ob=bpy.data.objects.new(name,me); coll.objects.link(ob); ob.data.materials.append(material)
 # Weld shared surface boundaries and orient connected faces consistently.
 import bmesh
 bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
 return ob

def box(name,loc,dim,material,bevel=0,coll=car):
 x,y,z=dim; cx,cy,cz=loc
 v=[(cx+a*x/2,cy+b*y/2,cz+c*z/2) for a,b,c in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 ob=mesh(name,v,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],material,coll)
 if bevel:
  mod=ob.modifiers.new('Restrained edge chamfer','BEVEL'); mod.width=bevel; mod.segments=1
  mod=ob.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL')
 return ob

def quad(name,v,material): return mesh(name,v,[(0,1,2,3)],material)
def subtract(target,cutter):
 bpy.context.view_layer.objects.active=target
 mod=target.modifiers.new('Fitted opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
 bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.data.objects.remove(cutter,do_unlink=True)
def interp(t,points):
 for (a,x),(b,y) in zip(points,points[1:]):
  if t<=b: return x+(y-x)*max(0,min(1,(t-a)/(b-a)))
 return points[-1][1]

NOSE=-2.18; TAIL=2.22; SCUTTLE=-.86; RF=-.43; RR=1.98
SILL=.47; BELT=1.23; ROOF=1.86; CLADDING=.69
AXLES=[-1.40,1.35]; R=.405; TRACK=1.68
def width(y): return interp(y,[(NOSE,.91),(-1.945,.975),(TAIL,.975)])
def shoulder(y): return interp(y,[(NOSE,1.10),(-1.945,1.16),(SCUTTLE,BELT),(TAIL,BELT)])
def side_x(y,z): return width(y)-.028*max(0,min(1,(CLADDING-z)/(CLADDING-SILL)))

# Connected primary side surfaces. Each arch lip is part of the same mesh.
for sign,label in [(1,'Left'),(-1,'Right')]:
 verts=[]; faces=[]; material_ids=[]
 def face(points,material_id=0):
  n=len(verts); verts.extend(points); faces.append(tuple(range(n,n+len(points))));material_ids.append(material_id)
 def point(y,z,offset=0):
  # Broad upper door plane; a single restrained tuck below the cladding line.
  w=side_x(y,z)
  return (sign*(w+offset),y,z)
 lower=[(NOSE,SILL,0)]
 for axle in AXLES:
  outer=[(-.54,SILL),(-.54,.70),(-.36,.965),(.36,.965),(.54,.70),(.54,SILL)]
  inner=[(-.455,SILL),(-.455,.67),(-.29,.868),(.29,.868),(.455,.67),(.455,SILL)]
  lower.extend([(axle+dy,z,0) for dy,z in outer])
  for i in range(5):
   a,b=outer[i],outer[i+1]; c,d=inner[i+1],inner[i]
   face([point(axle+a[0],a[1]),point(axle+b[0],b[1]),point(axle+c[0],c[1],.070),point(axle+d[0],d[1],.070)],1)
   face([point(axle+d[0],d[1],.070),point(axle+c[0],c[1],.070),point(axle+c[0],c[1],-.09),point(axle+d[0],d[1],-.09)],1)
 lower.append((TAIL,SILL,0))
 for yy in [-1.945,SCUTTLE]:
  for i,(a,b) in enumerate(zip(lower,lower[1:])):
   if a[0]<yy<b[0]:
    t=(yy-a[0])/(b[0]-a[0]); lower.insert(i+1,(yy,a[1]+t*(b[1]-a[1]),0)); break
 # Omit vertical runs from broad upper panels; those belong to arch lips.
 for a,b in zip(lower,lower[1:]):
  if abs(a[0]-b[0])<.00001: continue
  y0,z0,o0=a; y1,z1,o1=b
  # Clip each surface polygon at a level belt for fitted two-tone lower panels.
  poly=[(y0,z0),(y1,z1),(y1,shoulder(y1)-.055),(y0,shoulder(y0)-.055)]
  def clip(poly,above):
   result=[]
   for a,b in zip(poly,poly[1:]+poly[:1]):
    ina=(a[1]>=CLADDING) if above else (a[1]<=CLADDING)
    inb=(b[1]>=CLADDING) if above else (b[1]<=CLADDING)
    if ina:result.append(a)
    if ina!=inb:
     t=(CLADDING-a[1])/(b[1]-a[1]);result.append((a[0]+t*(b[0]-a[0]),CLADDING))
   return result
  for above,mi in [(True,0),(False,1)]:
   poly2=clip(poly,above)
   if len(poly2)>2:face([point(y,z) for y,z in poly2],mi)
  face([point(y0,shoulder(y0)-.055),point(y1,shoulder(y1)-.055),(sign*(width(y1)-.060),y1,shoulder(y1)),(sign*(width(y0)-.060),y0,shoulder(y0))])
 ob=mesh(label+' connected body and flares',verts,faces,paint);ob.data.materials.append(trim)
 for f,mi in zip(ob.data.polygons,material_ids):f.material_index=mi

# Bonnet is a broad, shallow folded plane, bounded by the same shoulder landmarks.
hood_y=[NOSE,-1.945,SCUTTLE]
v=[]
for y in hood_y:
 w=width(y)-.060; z=shoulder(y)
 v.extend([(-w,y,z),(-w*.70,y,z+.026),(w*.70,y,z+.026),(w,y,z)])
mesh('Broad folded bonnet',v,[(j*4+i,j*4+i+1,(j+1)*4+i+1,(j+1)*4+i) for j in range(2) for i in range(3)],paint)
for y in [NOSE,SCUTTLE]:
 w=width(y)-.060; z=shoulder(y)
 mesh('Bonnet end fold', [(-w,y,z),(-w*.70,y,z+.026),(w*.70,y,z+.026),(w,y,z)],[(0,1,2,3)],paint)
for name,y in [('Nose fascia',NOSE),('Tailgate lower panel',TAIL)]:
 w=width(y); z=shoulder(y)
 mesh(name,[(-w,y,SILL),(w,y,SILL),(w,y,z-.055),(w-.060,y,z),(-w+.060,y,z),(-w,y,z-.055)],[(0,1,2,3,4,5)],paint)
box('Cabin floor',(0,.59,.52),(1.73,3.16,.075),dark)

# Cabin faces use fitted inset openings; all panes share the enclosing plane.
def opening(name,corners,margin=.055,material=paint):
 # Convex planar quad inset. mitered frame widths measured in the face plane.
 vs=[Vector(v) for v in corners]; n=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized()
 center=sum(vs,Vector())/4; inner=[]
 for i,v in enumerate(vs):
  e0=(v-vs[(i-1)%4]).normalized(); e1=(vs[(i+1)%4]-v).normalized()
  a=n.cross(e0); b=n.cross(e1)
  if a.dot(center-v)<0:a=-a
  if b.dot(center-v)<0:b=-b
  bis=(a+b).normalized(); inner.append(v+bis*(margin/max(.15,bis.dot(a))))
 verts=[tuple(v) for v in vs+inner]
 mesh(name+' frame',verts,[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)],material)
 # Thin dark gasket within opening and glazing slightly recessed inward.
 mid=sum(inner,Vector())/4
 ins=[mid+(v-mid)*.98 for v in inner]
 mesh(name+' rubber seal',[tuple(v) for v in inner+ins],[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)],trim)
 # determine outward normal by approximate body center
 outward=n if n.dot(center-Vector((0,.5,.8)))>0 else -n
 quad(name+' glazing',[tuple(v-outward*.006) for v in ins],glass)

WBASE=width(SCUTTLE)-.060; WROOF=.80
opening('Windscreen',[(-WBASE,SCUTTLE,BELT),(WBASE,SCUTTLE,BELT),(WROOF,RF,ROOF-.045),(-WROOF,RF,ROOF-.045)],.060)
for s,l in [(1,'Left'),(-1,'Right')]:
 def cp(y,z): return (s*(WBASE+(WROOF-WBASE)*(z-BELT)/(ROOF-.045-BELT)),y,z)
 Z=ROOF-.045
 opening(l+' front side window',[cp(SCUTTLE,BELT),cp(.28,BELT),cp(.28,Z),cp(RF,Z)],.053)
 opening(l+' rear door window',[cp(.28,BELT),cp(1.18,BELT),cp(1.12,Z),cp(.28,Z)],.042,trim)
 opening(l+' cargo window',[cp(1.18,BELT),cp(TAIL,BELT),cp(RR,Z),cp(1.12,Z)],.070)
 # Upper shoulder ledge under the window band.
opening('Rear screen',[(-WBASE,TAIL,BELT),(WBASE,TAIL,BELT),(WROOF,RR,ROOF-.045),(-WROOF,RR,ROOF-.045)],.074)
v=[]
for y in [RF,RR]:
 v.extend([(-WROOF,y,ROOF-.045),(-WROOF+.075,y,ROOF), (WROOF-.075,y,ROOF),(WROOF,y,ROOF-.045)])
mesh('Roof with narrow edge folds',v,[(i,i+1,5+i,4+i) for i in range(3)],paint)
for y in [RF,RR]:
 mesh('Roof end fold',[(-WROOF,y,ROOF-.045),(-WROOF+.075,y,ROOF),(WROOF-.075,y,ROOF),(WROOF,y,ROOF-.045)],[(0,1,2,3)],paint)

# Bumpers are single wraparound extrusions, with cut corners and a lower bevel.
def bumper(name,front):
 sign=-1 if front else 1; end=abs(NOSE if front else TAIL)
 poly=[(-.970,sign*(end-.26)),(-1.015,sign*(end+.01)),(-.91,sign*(end+.115)),(.91,sign*(end+.115)),(1.015,sign*(end+.01)),(.970,sign*(end-.26)),(.925,sign*(end-.26)),(.91,sign*(end-.04)),(-.91,sign*(end-.04)),(-.925,sign*(end-.26))]
 verts=[]
 for z,scale in [(.485,.96),(.545,1),(.740,1),(.775,.99)]:
  verts.extend([(x*scale,py,z) for x,py in poly])
 n=len(poly); faces=[tuple(range(n-1,-1,-1)),tuple(range(3*n,4*n))]
 faces.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(3) for i in range(n))
 mesh(name,verts,faces,trim)
bumper('Front fitted wrap bumper',True); bumper('Rear fitted wrap bumper',False)
for s,l in [(1,'Left'),(-1,'Right')]:
 # The tread sits below both doors, with clearance to the tyre envelopes.
 box(l+' running board',(s*.979,-.025,.455),(.19,1.54,.075),trim,.020)
 box(l+' running board outer edge',(s*1.055,-.025,.446),(.030,1.47,.04),steel,.008)
 for ya,yb in [(AXLES[0]+.565,AXLES[1]-.565)]:
  if yb>ya:box(l+' lower body moulding',(s*(width((ya+yb)/2)+.007),(ya+yb)/2,.726),(.025,yb-ya,.032),paint,.004)
 # Modest door reveals are lines on the continuous outer shell, not floating slabs.
 for y in [SCUTTLE,.28,1.18]:
  zbottom=CLADDING if y<.7 else .965
  box(l+' door reveal '+str(y),(s*(width(y)+.001),y,(zbottom+1.174)/2),(.003,.005,1.174-zbottom),trim)
 for y in [.12,1.02]: box(l+' door handle '+str(y),(s*(width(y)+.015),y,1.139),(.038,.155,.039),trim,.008)
 box(l+' mirror foot',(s*.954,-.75,1.275),(.10,.090,.065),trim,.009)
 box(l+' mirror',(s*1.065,-.75,1.348),(.17,.22,.15),trim,.020)

# Simple fitted face band with restrained detail to keep comparison legible.
box('Front lamp and grille recess',(0,NOSE-.007,.955),(1.80,.020,.263),trim,.012)
box('Wide grille outer edge',(0,NOSE-.020,.95),(.93,.026,.276),steel,.020)
box('Wide grille inset',(0,NOSE-.039,.95),(.884,.014,.230),trim,.015)
for z in [.875,.938,1.002]:box('Horizontal grille bar',(0,NOSE-.052,z),(.85,.020,.018),steel,.003)
for x in [-.35,-.175,0,.175,.35]:box('Grille backing upright',(x,NOSE-.045,.95),(.014,.01,.21),trim)
cu=bpy.data.curves.new('Toyota grille lettering','FONT');cu.body='TOYOTA';cu.align_x='CENTER';cu.align_y='CENTER';cu.size=.065;cu.extrude=.0005;cu.resolution_u=1
ob=bpy.data.objects.new('Toyota grille lettering',cu);car.objects.link(ob);ob.location=(0,NOSE-.065,.95);ob.rotation_euler=(math.pi/2,0,0);cu.materials.append(lamp)
for s in [-1,1]:
 for x in [.558,.728]:box('Twin rectangular headlamp',(s*x,NOSE-.023,.962),(.155,.026,.188),lamp,.018)
 box('Front amber corner',(s*.863,NOSE-.020,.957),(.092,.022,.216),amber,.010)
 cutter=box('Temporary intake cutter',(s*.40,NOSE-.12,.635),(.29,.16,.073),dark)
 subtract(bpy.data.objects['Front fitted wrap bumper'],cutter)
 box('Bumper intake shadow back',(s*.40,NOSE-.041,.635),(.28,.004,.067),dark)
 box('Rear vertical lamp recess',(s*.875,TAIL+.009,.976),(.143,.025,.356),trim,.012)
 for z,h,m in [(1.093,.096,amber),(1.006,.060,lamp),(.887,.148,red)]:box('Rear lamp',(s*.875,TAIL+.026,z),(.118,.016,h),m,.008)
 box('Rear bumper reflector',(s*.64,TAIL+.120,.62),(.17,.012,.042),red,.006)
box('Front number plate',(0,NOSE-.128,.625),(.265,.018,.115),trim,.007)
box('Tailgate split seam',(0,TAIL+.003,1.075),(1.58,.006,.006),trim)
box('Tailgate handle',(0,TAIL+.023,1.045),(.44,.025,.043),trim,.007)
box('Tail number plate recess',(0,TAIL+.009,.922),(.38,.012,.143),trim,.008)
box('Tail lower cladding',(0,TAIL+.007,.635),(1.79,.018,.165),trim,.007)
# A pair of simple wipers reinforces the broad screen without visual noise.
def rod(name,a,b,r,material,segments=6):
 av=Vector(a);bv=Vector(b);d=bv-av
 bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=r,depth=d.length,location=(av+bv)/2)
 ob=bpy.context.object;ob.name=name;ob.rotation_euler=d.to_track_quat('Z','Y').to_euler();ob.data.materials.append(material)
 for c in list(ob.users_collection):c.objects.unlink(ob)
 car.objects.link(ob);return ob
for x in [-.42,.38]:
 rod('Wiper arm',(x,SCUTTLE-.010,BELT+.010),(x+.15,SCUTTLE+.032,BELT+.068),.008,trim)
 rod('Wiper blade',(x-.03,SCUTTLE+.040,BELT+.084),(x+.31,SCUTTLE+.040,BELT+.084),.009,trim)

# Substantial all-terrain tyres and simple six-vent steel wheels.
def wheel(name,s,y):
 cx=s*TRACK/2; z=R; N=16
 def rings(name,profile,material):
  verts=[(cx+s*d,y+rad*math.sin(2*math.pi*i/N),z+rad*math.cos(2*math.pi*i/N)) for d,rad in profile for i in range(N)]
  faces=[(j*N+i,j*N+(i+1)%N,((j+1)%len(profile))*N+(i+1)%N,((j+1)%len(profile))*N+i) for j in range(len(profile)) for i in range(N)]
  return mesh(name,verts,faces,material)
 rings(name+' tyre',[(-.145,.30),(-.13,.37),(-.085,R),(.085,R),(.145,.37),(.149,.237),(-.13,.237)],rubber)
 rim=rings(name+' steel rim',[(.145,.238),(.157,.228),(.159,.191),(.135,.165),(.139,.073),(.119,.073),(.119,.238)],steel)
 # Actual through-holes in the dish, with tyre interior behind them.
 for i in range(6):
  a=2*math.pi*i/6
  yy=y+.175*math.sin(a); zz=z+.175*math.cos(a)
  bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.030,depth=.14,location=(cx+s*.145,yy,zz),rotation=(0,math.pi/2,0))
  subtract(rim,bpy.context.object)
 rings(name+' hub',[(.14,.079),(.185,.065),(.185,0),(.12,0)],trim)
 for i in range(6):
  a=2*math.pi*i/6
  rod(name+' lug',(cx+s*.145,y+.105*math.sin(a),z+.105*math.cos(a)),(cx+s*.164,y+.105*math.sin(a),z+.105*math.cos(a)),.012,steel)
 # Broad shoulder tread facets; no fine texture noise.
 for i in range(16):
  a=2*math.pi*(i+.5)/16
  for side in [-1,1]:
   ob=box(name+' shoulder tread',(cx+side*.090,y+.390*math.sin(a),z+.390*math.cos(a)),(.074,.072,.022),rubber,.004)
   # Rotate about its own centre, since box vertices are authored in world space.
   center=Vector((cx+side*.090,y+.390*math.sin(a),z+.390*math.cos(a)))
   from mathutils import Matrix
   matrix=Matrix.Rotation(-a,4,'X')
   for vertex in ob.data.vertices:vertex.co=center+matrix.to_3x3()@(vertex.co-center)
for s,l in [(1,'Left'),(-1,'Right')]:
 for y,label in zip(AXLES,['front','rear']):wheel(l+' '+label,s,y)
 # Closed inner wheelhouse and curved upper liner hide the far side of each arch.
 for y in AXLES:
  vv=[]; N=12
  for x in [s*.62,s*1.028]:
   vv.extend([(x,y+.465*math.cos(math.pi*i/N),R+.465*math.sin(math.pi*i/N)) for i in range(N+1)])
  ff=[tuple(range(N+1))]
  ff.extend((i,i+1,N+2+i,N+1+i) for i in range(N))
  mesh(l+' dark wheelhouse',vv,ff,trim)

box('Underbody mass',(0,.15,.48),(1.22,3.38,.11),dark,.025)
for y in AXLES:
 rod('Axle silhouette',(-.83,y,.365),(.83,y,.365),.055,dark,8)
 box('Differential silhouette',(0,y,.345),(.25,.22,.19),dark,.055)
# Interior masses only: enough depth behind glass to judge the cabin proportions.
box('Dashboard mass',(0,-.70,1.20),(1.66,.28,.14),dark,.035)
for y in [.06,1.10]:
 for x in [-.43,.43]:
  box('Seat cushion',(x,y,.74),(.53,.50,.14),fabric,.04)
  ob=box('Seat back',(x,y+.19,1.10),(.52,.15,.61),fabric,.055)
  box('Head restraint',(x,y+.20,1.48),(.28,.14,.17),fabric,.03)
# Steering wheel silhouette, deliberately not a functional cockpit.
bpy.ops.mesh.primitive_torus_add(major_segments=16,minor_segments=6,location=(-.43,-.41,1.295),major_radius=.155,minor_radius=.016,rotation=(math.radians(67),0,0))
ob=bpy.context.object; ob.name='Steering silhouette'; ob.data.materials.append(trim)
for coll in list(ob.users_collection):coll.objects.unlink(ob)
car.objects.link(ob)

# Save landmarks and honest scope directly in the file.
spec={'name':'Stylized Land Cruiser 80','basis':'Artistic proportions following accepted reference-wagon-v03 style; earlier LC80 board supplies identity and colour only, not a calibrated blueprint','length_body':TAIL-NOSE,'width_body':1.95,'roof_height':ROOF,'wheel_radius':R,'axles_y':AXLES,'wheel_track':TRACK,'scuttle_y':SCUTTLE,'roof_front_y':RF,'roof_rear_y':RR,'reference_url':'https://media.toyota.co.uk/images/land-cruiser-vx-exterior-1992-1995/','scope':'Exterior shape study; interior and underbody masses only. No articulation, UVs, collision, export or game-readiness validation.'}
scene['study_spec']=json.dumps(spec)
(out/'spec.json').write_text(json.dumps(spec,indent=2))
# Narrow, meaningful static fit checks. These do not establish articulation or game readiness.
from mathutils.bvhtree import BVHTree
dg=bpy.context.evaluated_depsgraph_get()
def tree(ob):
 evaluated=ob.evaluated_get(dg);me=evaluated.to_mesh();me.calc_loop_triangles()
 vv=[evaluated.matrix_world@v.co for v in me.vertices];ff=[tuple(t.vertices) for t in me.loop_triangles]
 result=BVHTree.FromPolygons(vv,ff,all_triangles=True);evaluated.to_mesh_clear();return result
stationary=[o for o in car.objects if o.type=='MESH' and ('connected body' in o.name or 'running board' in o.name)]
contacts=[]
for tyre in [o for o in car.objects if o.name.endswith(' tyre')]:
 tyre_tree=tree(tyre)
 for fixed in stationary:
  if tyre_tree.overlap(tree(fixed)):contacts.append([tyre.name,fixed.name])
finite=all(math.isfinite(c) for o in car.objects if o.type=='MESH' for v in o.data.vertices for c in v.co)
report={'finite_mesh_coordinates':finite,'static_tyre_to_body_and_running_board_intersections':contacts,'scope':'Triangle surface intersection only for four tyre shells against body/flare meshes and running boards. Tread, steering, suspension, containment, other components and export excluded.'}
(out/'static-fit-report.json').write_text(json.dumps(report,indent=2))
if not finite or contacts:raise RuntimeError('Static geometry check failed: '+str(report))
shutil.copy2(__file__,out/Path(__file__).name)
refs=bpy.data.collections.new('Reference — hidden from renders');scene.collection.children.link(refs)
for name,path in [('Land Cruiser identity','C:/GrandTour/Art/References/Vehicles/LandCruiser80_v01/02_exterior_form_finish.png'),('Accepted style','C:/GrandTour/Art/Export/VehicleTools/reference-wagon-v03/three-quarter.png')]:
 im=bpy.data.images.load(path);im.pack()
 ob=bpy.data.objects.new(name,None);refs.objects.link(ob);ob.empty_display_type='IMAGE';ob.data=im;ob.hide_render=True;ob.hide_viewport=True

ground=mat('Studio blue grey',(.13,.22,.255),.85)
mesh('Ground',[(-200,-200,-.002),(200,-200,-.002),(200,200,-.002),(-200,200,-.002)],[(0,1,2,3)],ground,studio)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_x=1280;scene.render.resolution_y=900;scene.render.resolution_percentage=100
world=bpy.data.worlds.new('Soft neutral world');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.64,.70,1);world.node_tree.nodes['Background'].inputs[1].default_value=.4
scene.view_settings.view_transform='AgX'
for name,loc,power,size in [('Key',( -3,-4,7),950,5),('Fill',(4,-1,4),450,5),('Rim',(0,4,6),700,4)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
 ob=bpy.data.objects.new(name,data);studio.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,.6))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',data);studio.objects.link(cam);scene.camera=cam;data.type='ORTHO'
views=[('three-quarter',(5,-7,3.5),(0,0,.91),5.8),('side',(7,0,.99),(0,0,.99),5.30),('front',(0,-7,.99),(0,0,.99),3.3),('top',(0,0,8),(0,0,0),6.65),('rear-quarter',(5,7,3.4),(0,0,.91),5.8),('arch-joint',(3,-2.5,1.5),(.92,-.9,.86),1.45)]
def view(v):
 name,loc,target,scale=v;cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
for v in views:
 view(v);scene.render.filepath=str(out/(v[0]+'.png'));bpy.ops.render.render(write_still=True)
view(views[0])
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_perspective='CAMERA'
   area.spaces.active.shading.type='MATERIAL'
   area.spaces.active.overlay.show_overlays=False
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Stylized_LandCruiser80.blend'))
print('STYLIZED_LANDCRUISER_SAVED '+str(out))
