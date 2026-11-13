"""Stylized four-door Range Rover Classic, in the accepted Grand Tour shape language.
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
car=bpy.data.collections.new('Range Rover Classic — stylized study'); scene.collection.children.link(car)
studio=bpy.data.collections.new('Review studio'); scene.collection.children.link(studio)

def mat(name,c,rough=.6,metal=0):
 m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*c,1)
 bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
 return m
paint=mat('Muted heritage green',(.125,.265,.205),.57)
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

NOSE=-2.03; TAIL=2.24; SCUTTLE=-.77; RF=-.43; RR=1.93
SILL=.43; BELT=1.16; ROOF=1.79; CLADDING=.505
AXLES=[-1.36,1.27]; R=.38; TRACK=1.56
def width(y): return interp(y,[(NOSE,.875),(-1.84,.92),(TAIL,.92)])
def shoulder(y): return interp(y,[(NOSE,1.135),(SCUTTLE,BELT),(TAIL,BELT)])
def side_x(y,z): return width(y)

# Connected primary side surfaces. Each arch lip is part of the same mesh.
for sign,label in [(1,'Left'),(-1,'Right')]:
 verts=[]; faces=[]; material_ids=[]
 def face(points,material_id=0):
  n=len(verts); verts.extend(points); faces.append(tuple(range(n,n+len(points))));material_ids.append(material_id)
 def point(y,z,offset=0):
  # Continuous flat side plane, including the sill/arch junction.
  w=side_x(y,z)
  return (sign*(w+offset),y,z)
 lower=[(NOSE,SILL,0)]
 for axle in AXLES:
  # Close, faceted semicircular wheel cuts with a narrow body-colour lip.
  outer=[];inner=[]
  for i in range(9):
   a=math.pi-i*math.pi/8
   outer.append((.475*math.cos(a),max(SILL,R+.475*math.sin(a))))
   inner.append((.435*math.cos(a),max(SILL,R+.435*math.sin(a))))
  lower.extend([(axle+dy,z,0) for dy,z in outer])
  for i in range(8):
   a,b=outer[i],outer[i+1]; c,d=inner[i+1],inner[i]
   face([point(axle+a[0],a[1]),point(axle+b[0],b[1]),point(axle+c[0],c[1],.016),point(axle+d[0],d[1],.016)],0)
   face([point(axle+d[0],d[1],.016),point(axle+c[0],c[1],.016),point(axle+c[0],c[1],-.085),point(axle+d[0],d[1],-.085)],1)
 lower.append((TAIL,SILL,0))
 for yy in [-1.84,SCUTTLE]:
  for i,(a,b) in enumerate(zip(lower,lower[1:])):
   if a[0]<yy<b[0]:
    t=(yy-a[0])/(b[0]-a[0]); lower.insert(i+1,(yy,a[1]+t*(b[1]-a[1]),0)); break
 # Omit vertical runs from broad upper panels; those belong to arch lips.
 for a,b in zip(lower,lower[1:]):
  if abs(a[0]-b[0])<.00001: continue
  y0,z0,o0=a; y1,z1,o1=b
  # Clip each surface polygon at a level belt for fitted two-tone lower panels.
  poly=[(y0,z0),(y1,z1),(y1,shoulder(y1)-.030),(y0,shoulder(y0)-.030)]
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
  face([point(y0,shoulder(y0)-.030),point(y1,shoulder(y1)-.030),(sign*(width(y1)-.035),y1,shoulder(y1)),(sign*(width(y0)-.035),y0,shoulder(y0))])
 ob=mesh(label+' connected body and flares',verts,faces,paint);ob.data.materials.append(trim)
 for f,mi in zip(ob.data.polygons,material_ids):f.material_index=mi

# Bonnet is a broad, shallow folded plane, bounded by the same shoulder landmarks.
hood_y=[NOSE,-1.84,SCUTTLE]
v=[]
for y in hood_y:
 w=width(y)-.035; z=shoulder(y)
 v.extend([(-w,y,z),(-w*.77,y,z+.012),(w*.77,y,z+.012),(w,y,z)])
mesh('Broad folded bonnet',v,[(j*4+i,j*4+i+1,(j+1)*4+i+1,(j+1)*4+i) for j in range(2) for i in range(3)],paint)
for y in [NOSE,SCUTTLE]:
 w=width(y)-.035; z=shoulder(y)
 mesh('Bonnet end fold', [(-w,y,z),(-w*.77,y,z+.012),(w*.77,y,z+.012),(w,y,z)],[(0,1,2,3)],paint)
for name,y in [('Nose fascia',NOSE),('Tailgate lower panel',TAIL)]:
 w=width(y); z=shoulder(y)
 mesh(name,[(-w,y,SILL),(w,y,SILL),(w,y,z-.030),(w-.035,y,z),(-w+.035,y,z),(-w,y,z-.030)],[(0,1,2,3,4,5)],paint)
box('Cabin floor',(0,.66,.49),(1.64,3.08,.075),dark)

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

WBASE=width(SCUTTLE)-.035; WROOF=.76
opening('Windscreen',[(-WBASE,SCUTTLE,BELT),(WBASE,SCUTTLE,BELT),(WROOF,RF,ROOF-.050),(-WROOF,RF,ROOF-.050)],.045,trim)
for s,l in [(1,'Left'),(-1,'Right')]:
 def cp(y,z): return (s*(WBASE+(WROOF-WBASE)*(z-BELT)/(ROOF-.050-BELT)),y,z)
 Z=ROOF-.050
 opening(l+' front side window',[cp(SCUTTLE,BELT),cp(.23,BELT),cp(.23,Z),cp(RF,Z)],.040,trim)
 opening(l+' rear door window',[cp(.23,BELT),cp(1.17,BELT),cp(1.08,Z),cp(.23,Z)],.038,trim)
 opening(l+' cargo window',[cp(1.17,BELT),cp(TAIL,BELT),cp(RR,Z),cp(1.08,Z)],.052,trim)
 # Upper shoulder ledge under the window band.
opening('Rear screen',[(-WBASE,TAIL,BELT),(WBASE,TAIL,BELT),(WROOF,RR,ROOF-.050),(-WROOF,RR,ROOF-.050)],.045,trim)
v=[]
for y in [RF,RR]:
 v.extend([(-WROOF,y,ROOF-.050),(-WROOF+.070,y,ROOF), (WROOF-.070,y,ROOF),(WROOF,y,ROOF-.050)])
mesh('Roof with narrow edge folds',v,[(i,i+1,5+i,4+i) for i in range(3)],paint)
for y in [RF,RR]:
 mesh('Roof end fold',[(-WROOF,y,ROOF-.050),(-WROOF+.070,y,ROOF),(WROOF-.070,y,ROOF),(WROOF,y,ROOF-.050)],[(0,1,2,3)],paint)
# Fine roof gutter and bonnet wrap seam carry the Classic's horizontal lines.
for s,l in [(1,'Left'),(-1,'Right')]:
 box(l+' roof gutter',(s*(WROOF+.004),(RF+RR)/2,ROOF-.048),(.027,RR-RF+.028,.023),paint,.004)
 box(l+' clamshell seam',(s*(width(-1.39)+.002),-1.365,1.071),(.005,1.00,.006),trim)

# Slim wraparound bumpers, separate from the deep painted body.
def bumper(name,front):
 sign=-1 if front else 1; end=abs(NOSE if front else TAIL)
 poly=[(-.925,sign*(end-.23)),(-.96,sign*(end+.025)),(-.88,sign*(end+.11)),(.88,sign*(end+.11)),(.96,sign*(end+.025)),(.925,sign*(end-.23)),(.875,sign*(end-.23)),(.87,sign*(end-.035)),(-.87,sign*(end-.035)),(-.875,sign*(end-.23))]
 verts=[]
 for z,scale in [(.495,.975),(.525,1),(.640,1),(.660,.99)]:
  verts.extend([(x*scale,y,z) for x,y in poly])
 n=len(poly);faces=[tuple(range(n-1,-1,-1)),tuple(range(3*n,4*n))]
 faces.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(3) for i in range(n))
 mesh(name,verts,faces,trim)
bumper('Front slim wrap bumper',True);bumper('Rear slim wrap bumper',False)
for s,l in [(1,'Left'),(-1,'Right')]:
 box(l+' sill trim',(s*.905,-.045,.471),(.052,1.64,.064),trim,.008)
 for ya,yb in [(AXLES[0]+.49,AXLES[1]-.49),(AXLES[1]+.49,TAIL-.12)]:
  if yb>ya:box(l+' body rubbing strip',(s*(width((ya+yb)/2)+.008),(ya+yb)/2,.795),(.022,yb-ya,.035),trim,.004)
 for y in [SCUTTLE,.23,1.17]:
  zbottom=CLADDING if y<.7 else .861
  box(l+' door reveal '+str(y),(s*(width(y)+.001),y,(zbottom+1.124)/2),(.003,.005,1.124-zbottom),trim)
 for y in [.085,.99]:box(l+' door handle',(s*(width(y)+.012),y,1.055),(.032,.136,.037),trim,.005)
 box(l+' mirror foot',(s*.90,-.665,1.205),(.105,.073,.060),trim,.008)
 box(l+' mirror',(s*.990,-.665,1.277),(.155,.186,.130),trim,.016)

# Small utility for lamps, wheel holes and understated exterior rods.
def cylinder(name,loc,r,depth,material,axis='X',segments=16):
 rotation=(0,math.pi/2,0) if axis=='X' else (math.pi/2,0,0)
 bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=r,depth=depth,location=loc,rotation=rotation)
 ob=bpy.context.object;ob.name=name;ob.data.materials.append(material)
 for c in list(ob.users_collection):c.objects.unlink(ob)
 car.objects.link(ob);return ob

def rod(name,a,b,r,material,segments=6):
 av=Vector(a);bv=Vector(b);d=bv-av
 ob=cylinder(name,(av+bv)/2,r,d.length,material,segments=segments)
 ob.rotation_euler=d.to_track_quat('Z','Y').to_euler();return ob

def label(name,text,loc,size,material,front=True):
 cu=bpy.data.curves.new(name,'FONT');cu.body=text;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size;cu.space_character=1.18;cu.extrude=.0003;cu.resolution_u=1
 ob=bpy.data.objects.new(name,cu);car.objects.link(ob);ob.location=loc;ob.rotation_euler=(math.pi/2 if front else math.pi/2,0,0 if front else math.pi);cu.materials.append(material)
 return ob

# The front is specific to the Classic: separate round lamps, horizontal bonnet edge,
# a rectangular dark grille and low rectangular indicator/side-lamp clusters.
box('Front grille surround',(0,NOSE-.012,.937),(1.70,.025,.324),trim,.008)
box('Grille inset',(0,NOSE-.028,.940),(1.04,.021,.274),dark,.005)
for x in [-.47+i*.052 for i in range(19)]:box('Grille vertical rib',(x,NOSE-.045,.940),(.019,.017,.253),trim,.002)
for z in [.826,1.054]:box('Grille horizontal edge',(0,NOSE-.048,z),(1.025,.022,.018),trim,.003)
for s in [-1,1]:
 cylinder('Round headlamp bezel',(s*.690,NOSE-.035,.945),.136,.037,steel,'Y',16)
 cylinder('Round ivory headlamp',(s*.690,NOSE-.059,.945),.115,.023,lamp,'Y',16)
 box('Indicator housing',(s*.735,NOSE-.014,.741),(.253,.026,.082),trim,.007)
 box('Amber indicator',(s*.805,NOSE-.032,.741),(.108,.014,.060),amber,.005)
 box('White side lamp',(s*.674,NOSE-.032,.741),(.124,.014,.060),lamp,.005)
# Lettering sits on the front of the bonnet rather than on a grille badge.
label('Bonnet lettering','RANGE ROVER',(0,NOSE-.014,1.114),.049,trim)
box('Front registration plate',(0,NOSE-.123,.578),(.31,.014,.091),dark,.004)
# A shallow black valance gives the thin bumper something to sit against.
box('Front lower valance',(0,NOSE+.022,.470),(1.67,.08,.068),trim,.008)

# Rear split tailgate and simple stacked lamps, entirely below the black glass band.
box('Tailgate horizontal seam',(0,TAIL+.003,1.116),(1.68,.006,.006),trim)
box('Tailgate handle',(0,TAIL+.022,1.071),(.19,.025,.034),trim,.005)
box('Rear registration panel',(0,TAIL+.009,.914),(.41,.014,.132),trim,.008)
label('Tailgate lettering','RANGE ROVER',(0,TAIL+.012,1.031),.041,trim,False)
for s in [-1,1]:
 box('Rear lamp surround',(s*.811,TAIL+.010,.89),(.143,.024,.280),trim,.009)
 for z,h,m in [(.980,.072,amber),(.901,.059,lamp),(.813,.092,red)]:box('Rear lamp lens',(s*.811,TAIL+.026,z),(.118,.015,h),m,.004)
for x in [-.41,.37]:
 rod('Wiper arm',(x,SCUTTLE-.012,BELT+.013),(x+.13,SCUTTLE+.024,BELT+.063),.007,trim)
 rod('Wiper blade',(x-.04,SCUTTLE+.035,BELT+.090),(x+.27,SCUTTLE+.035,BELT+.090),.008,trim)
# Tailgate wiper follows the rear screen's plane.
rod('Rear wiper arm',(.30,TAIL-.035,BELT+.082),(.06,TAIL-.069,BELT+.145),.007,trim)
rod('Rear wiper blade',(-.11,TAIL-.071,BELT+.148),(.23,TAIL-.071,BELT+.148),.008,trim)

# Road-oriented tyres and a simple three-spoke alloy graphic distinguish it from the LC.
def wheel(name,s,y):
 cx=s*TRACK/2;z=R;N=24
 def rings(name,profile,material):
  verts=[(cx+s*d,y+rad*math.sin(2*math.pi*i/N),z+rad*math.cos(2*math.pi*i/N)) for d,rad in profile for i in range(N)]
  faces=[(j*N+i,j*N+(i+1)%N,((j+1)%len(profile))*N+(i+1)%N,((j+1)%len(profile))*N+i) for j in range(len(profile)) for i in range(N)]
  return mesh(name,verts,faces,material)
 rings(name+' tyre',[(-.126,.28),(-.118,.346),(-.078,R),(.078,R),(.127,.348),(.131,.225),(-.119,.225)],rubber)
 rings(name+' alloy rim',[(.128,.225),(.145,.215),(.145,.191),(.126,.184),(.114,.192),(.114,.225)],steel)
 cylinder(name+' dark wheel recess',(cx+s*.118,y,z),.192,.015,dark,'X',24)
 # Three tapered spokes, each closed and chamfered only by its broad planar shape.
 for j in range(3):
  a=2*math.pi*j/3
  outline=[(-.057,.025),(-.047,.181),(.042,.191),(.071,.090)]
  verts=[]
  for xx in [.128,.155]:
   for yy,zz in outline:
    verts.append((cx+s*xx,y+yy*math.cos(a)-zz*math.sin(a),z+yy*math.sin(a)+zz*math.cos(a)))
  mesh(name+' alloy spoke',verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],steel)
 cylinder(name+' centre cap',(cx+s*.157,y,z),.077,.023,steel,'X',16)
 cylinder(name+' hub badge',(cx+s*.171,y,z),.041,.006,trim,'X',12)
for s,l in [(1,'Left'),(-1,'Right')]:
 for y,name in zip(AXLES,['front','rear']):wheel(l+' '+name,s,y)
 for y in AXLES:
  vv=[];N=12
  for x in [s*.60,s*.924]:vv.extend([(x,y+.435*math.cos(math.pi*i/N),R+.435*math.sin(math.pi*i/N)) for i in range(N+1)])
  ff=[tuple(range(N+1))];ff.extend((i,i+1,N+2+i,N+1+i) for i in range(N))
  mesh(l+' dark wheelhouse',vv,ff,trim)
box('Underbody mass',(0,.15,.44),(1.20,3.32,.10),dark,.020)
for y in AXLES:
 rod('Axle silhouette',(-.78,y,.345),(.78,y,.345),.049,dark,8)
 box('Differential silhouette',(0,y,.325),(.22,.21,.16),dark,.04)
# Cabin masses support the outside glass view; this is not a finished cockpit.
box('Dashboard mass',(0,-.62,1.11),(1.60,.27,.13),dark,.03)
for y in [.03,1.02]:
 for x in [-.41,.41]:
  box('Seat cushion',(x,y,.66),(.50,.48,.13),fabric,.04)
  box('Seat back',(x,y+.19,1.015),(.49,.15,.58),fabric,.055)
  box('Head restraint',(x,y+.20,1.36),(.26,.13,.16),fabric,.025)
bpy.ops.mesh.primitive_torus_add(major_segments=16,minor_segments=6,location=(-.41,-.35,1.20),major_radius=.15,minor_radius=.014,rotation=(math.radians(67),0,0))
ob=bpy.context.object;ob.name='Steering silhouette';ob.data.materials.append(trim)
for coll in list(ob.users_collection):coll.objects.unlink(ob)
car.objects.link(ob)
# Save landmarks and honest scope directly in the file.
spec={'name':'Stylized four-door Range Rover Classic','basis':'Artistic proportions in the accepted wagon and Land Cruiser style. Independent study; does not load or modify the user-modelled Art/rangerover.blend.','length_body':TAIL-NOSE,'width_body':1.84,'roof_height':ROOF,'wheel_radius':R,'axles_y':AXLES,'wheel_track':TRACK,'scuttle_y':SCUTTLE,'roof_front_y':RF,'roof_rear_y':RR,'reference_url':'https://media.jlr.com/classic/en-gb/news/2010/06/range-rover-celebrates-its-40th-birthday','scope':'Exterior shape study; interior and underbody masses only. No articulation, UVs, collision, export or game-readiness validation.'}
scene['study_spec']=json.dumps(spec)
(out/'spec.json').write_text(json.dumps(spec,indent=2))
# Narrow, meaningful static fit checks. These do not establish articulation or game readiness.
from mathutils.bvhtree import BVHTree
dg=bpy.context.evaluated_depsgraph_get()
def tree(ob):
 evaluated=ob.evaluated_get(dg);me=evaluated.to_mesh();me.calc_loop_triangles()
 vv=[evaluated.matrix_world@v.co for v in me.vertices];ff=[tuple(t.vertices) for t in me.loop_triangles]
 result=BVHTree.FromPolygons(vv,ff,all_triangles=True);evaluated.to_mesh_clear();return result
stationary=[o for o in car.objects if o.type=='MESH' and ('connected body' in o.name or 'sill trim' in o.name)]
contacts=[]
for tyre in [o for o in car.objects if o.name.endswith(' tyre')]:
 tyre_tree=tree(tyre)
 for fixed in stationary:
  if tyre_tree.overlap(tree(fixed)):contacts.append([tyre.name,fixed.name])
finite=all(math.isfinite(c) for o in car.objects if o.type=='MESH' for v in o.data.vertices for c in v.co)
report={'finite_mesh_coordinates':finite,'static_tyre_to_body_and_sill_intersections':contacts,'scope':'Triangle surface intersection only for four tyre shells against body/arch meshes and sill trims. Steering, suspension, containment, other components and export excluded.'}
(out/'static-fit-report.json').write_text(json.dumps(report,indent=2))
if not finite or contacts:raise RuntimeError('Static geometry check failed: '+str(report))
shutil.copy2(__file__,out/Path(__file__).name)
refs=bpy.data.collections.new('Reference — hidden from renders');scene.collection.children.link(refs)
for name,path in [('Accepted Land Cruiser style','C:/GrandTour/Art/Export/VehicleTools/stylized-landcruiser-v02/three-quarter.png'),('Accepted wagon style','C:/GrandTour/Art/Export/VehicleTools/reference-wagon-v03/three-quarter.png')]:
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
views=[('three-quarter',(5,-7,3.5),(0,.04,.88),5.65),('side',(7,.05,.96),(0,.05,.96),5.15),('front',(0,-7,.96),(0,0,.96),3.2),('top',(0,0,8),(0,0,0),6.5),('rear-quarter',(5,7,3.4),(0,.04,.88),5.65),('arch-joint',(3,-2.5,1.5),(.89,-.9,.84),1.45)]
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
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Stylized_RangeRoverClassic.blend'))
print('STYLIZED_RANGEROVER_SAVED '+str(out))
