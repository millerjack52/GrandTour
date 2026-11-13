"""Independent reference-led wagon study; never loads or replaces previous models.
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
car=bpy.data.collections.new('Wagon — reference silhouette'); scene.collection.children.link(car)
studio=bpy.data.collections.new('Review studio'); scene.collection.children.link(studio)

def mat(name,c,rough=.6,metal=0):
 m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*c,1)
 bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
 return m
paint=mat('Terracotta',(.55,.135,.042),.57)
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
def interp(t,points):
 for (a,x),(b,y) in zip(points,points[1:]):
  if t<=b: return x+(y-x)*max(0,min(1,(t-a)/(b-a)))
 return points[-1][1]

NOSE=-2.02; TAIL=2.02; SCUTTLE=-.84; RF=-.31; RR=1.61
SILL=.34; BELT=1.01; ROOF=1.57
AXLES=[-1.31,1.25]; R=.335; TRACK=1.57
def width(y): return interp(y,[(NOSE,.86),(-1.745,.925),(TAIL,.925)])
def shoulder(y): return interp(y,[(NOSE,.865),(SCUTTLE,BELT),(TAIL,BELT)])

# Connected primary side surfaces. Each arch lip is part of the same mesh.
for sign,label in [(1,'Left'),(-1,'Right')]:
 verts=[]; faces=[]
 def face(points):
  n=len(verts); verts.extend(points); faces.append(tuple(range(n,n+len(points))))
 def point(y,z,offset=0):
  # Large planar door skin with a slight lower-body tuck.
  w=width(y)
  return (sign*(w+offset),y,z)
 lower=[(NOSE,SILL,0)]
 for axle in AXLES:
  outer=[(-.415,SILL),(-.415,.565),(-.27,.77),(.27,.77),(.415,.565),(.415,SILL)]
  inner=[(-.365,SILL),(-.365,.54),(-.23,.712),(.23,.712),(.365,.54),(.365,SILL)]
  lower.extend([(axle+dy,z,0) for dy,z in outer])
  for i in range(5):
   a,b=outer[i],outer[i+1]; c,d=inner[i+1],inner[i]
   face([point(axle+a[0],a[1]),point(axle+b[0],b[1]),point(axle+c[0],c[1],.025),point(axle+d[0],d[1],.025)])
   face([point(axle+d[0],d[1],.025),point(axle+c[0],c[1],.025),point(axle+c[0],c[1],-.065),point(axle+d[0],d[1],-.065)])
 lower.append((TAIL,SILL,0))
 for yy in [-1.745,SCUTTLE]:
  for i,(a,b) in enumerate(zip(lower,lower[1:])):
   if a[0]<yy<b[0]:
    t=(yy-a[0])/(b[0]-a[0]); lower.insert(i+1,(yy,a[1]+t*(b[1]-a[1]),0)); break
 # Omit vertical runs from broad upper panels; those belong to arch lips.
 for a,b in zip(lower,lower[1:]):
  if abs(a[0]-b[0])<.00001: continue
  y0,z0,o0=a; y1,z1,o1=b
  face([point(y0,z0,o0),point(y1,z1,o1),point(y1,shoulder(y1)-.035),point(y0,shoulder(y0)-.035)])
  face([point(y0,shoulder(y0)-.035),point(y1,shoulder(y1)-.035),(sign*(width(y1)-.055),y1,shoulder(y1)),(sign*(width(y0)-.055),y0,shoulder(y0))])
 mesh(label+' connected body and arch lips',verts,faces,paint)

# Bonnet is a broad, shallow folded plane, bounded by the same shoulder landmarks.
hood_y=[NOSE,-1.745,SCUTTLE]
v=[]
for y in hood_y:
 w=width(y)-.055; z=shoulder(y)
 v.extend([(-w,y,z),(-w*.68,y,z+.016),(w*.68,y,z+.016),(w,y,z)])
mesh('Broad folded bonnet',v,[(j*4+i,j*4+i+1,(j+1)*4+i+1,(j+1)*4+i) for j in range(2) for i in range(3)],paint)
for y in [NOSE,SCUTTLE]:
 w=width(y)-.055; z=shoulder(y)
 mesh('Bonnet end fold', [(-w,y,z),(-w*.68,y,z+.016),(w*.68,y,z+.016),(w,y,z)],[(0,1,2,3)],paint)
for name,y in [('Nose fascia',NOSE),('Tailgate lower panel',TAIL)]:
 w=width(y); z=shoulder(y)
 mesh(name,[(-w,y,SILL),(w,y,SILL),(w,y,z-.035),(w-.055,y,z),(-w+.055,y,z),(-w,y,z-.035)],[(0,1,2,3,4,5)],paint)
box('Cabin floor',(0,.5,.38),(1.58,2.84,.065),dark)

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

WBASE=width(SCUTTLE)-.055; WROOF=.735
opening('Windscreen',[(-WBASE,SCUTTLE,BELT),(WBASE,SCUTTLE,BELT),(WROOF,RF,ROOF-.035),(-WROOF,RF,ROOF-.035)],.05)
for s,l in [(1,'Left'),(-1,'Right')]:
 def cp(y,z): return (s*(WBASE+(WROOF-WBASE)*(z-BELT)/(ROOF-.035-BELT)),y,z)
 Z=ROOF-.035
 opening(l+' front side window',[cp(SCUTTLE,BELT),cp(.32,BELT),cp(.32,Z),cp(RF,Z)],.044)
 opening(l+' rear door window',[cp(.32,BELT),cp(1.13,BELT),cp(1.05,Z),cp(.32,Z)],.036,trim)
 opening(l+' cargo window',[cp(1.13,BELT),cp(TAIL,BELT),cp(RR,Z),cp(1.05,Z)],.059)
 # Upper shoulder ledge under the window band.
 quad(l+' window base',[cp(SCUTTLE,BELT),cp(TAIL,BELT),(s*(width(TAIL)-.055),TAIL,BELT),(s*(width(SCUTTLE)-.055),SCUTTLE,BELT)],paint)
opening('Rear screen',[(-WBASE,TAIL,BELT),(WBASE,TAIL,BELT),(WROOF,RR,ROOF-.035),(-WROOF,RR,ROOF-.035)],.064)
v=[]
for y in [RF,RR]:
 v.extend([(-WROOF,y,ROOF-.035),(-WROOF+.065,y,ROOF), (WROOF-.065,y,ROOF),(WROOF,y,ROOF-.035)])
mesh('Roof with narrow edge folds',v,[(i,i+1,5+i,4+i) for i in range(3)],paint)
for y in [RF,RR]:
 mesh('Roof end fold',[(-WROOF,y,ROOF-.035),(-WROOF+.065,y,ROOF),(WROOF-.065,y,ROOF),(WROOF,y,ROOF-.035)],[(0,1,2,3)],paint)

# Bumpers are single wraparound extrusions, with cut corners and a lower bevel.
def bumper(name,front):
 y=-1 if front else 1
 poly=[(-.90,y*1.72),(-.96,y*2.015),(-.86,y*2.115),(.86,y*2.115),(.96,y*2.015),(.90,y*1.72),(.855,y*1.72),(.86,y*1.98),(-.86,y*1.98),(-.855,y*1.72)]
 verts=[]
 for z,scale in [(.335,.965),(.385,1),(.565,1),(.585,.99)]:
  verts.extend([(x*scale,py,z) for x,py in poly])
 n=len(poly); faces=[tuple(range(n-1,-1,-1)),tuple(range(3*n,4*n))]
 faces.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(3) for i in range(n))
 mesh(name,verts,faces,trim)
bumper('Front fitted wrap bumper',True); bumper('Rear fitted wrap bumper',False)
for s,l in [(1,'Left'),(-1,'Right')]:
 box(l+' sill strip',(s*.902,-.03,.365),(.055,1.65,.073),trim,.01)
 # Modest door reveals are lines on the continuous outer shell, not floating slabs.
 for y in [SCUTTLE,.32,1.13]:
  zbottom=.36 if y<.7 else .77
  box(l+' door reveal '+str(y),(s*(width(y)+.001),y,(zbottom+.965)/2),(.003,.005,.965-zbottom),trim)
 for y in [.16,.97]: box(l+' door handle '+str(y),(s*(width(y)+.013),y,.945),(.032,.145,.032),trim,.006)
 box(l+' mirror foot',(s*.925,-.73,1.045),(.095,.072,.055),trim,.007)
 box(l+' mirror',(s*1.003,-.75,1.093),(.14,.17,.095),trim,.014)

# Simple fitted face band with restrained detail to keep comparison legible.
box('Front lamp and grille recess',(0,NOSE-.006,.742),(1.66,.016,.216),trim,.006)
for s in [-1,1]:
 for x in [.425,.615]: box('Headlamp', (s*x,NOSE-.017,.746),(.177,.016,.178),lamp,.008)
 box('Front indicator',(s*.789,NOSE-.017,.746),(.115,.016,.178),amber,.004)
 box('Grille steel rim',(s*.183,NOSE-.018,.746),(.329,.024,.205),steel,.015)
 box('Grille dark inset',(s*.183,NOSE-.033,.746),(.300,.011,.178),trim,.010)
 for i in range(6): box('Grille slat',(s*(.066+i*.046),NOSE-.041,.746),(.011,.015,.157),steel,.002)
 for z,m in [(.84,red),(.744,amber),(.67,lamp)]: box('Rear lamp',(s*.792,TAIL+.009,z),(.125,.022,.070),m,.004)
box('Tail number plate recess',(0,TAIL+.008,.735),(.43,.012,.135),trim,.006)

# Ring-based tyres and steel wheels. No bulky arch extensions or off-road stance.
def wheel(name,s,y):
 cx=s*TRACK/2; z=R; N=16
 def rings(name,profile,material):
  verts=[(cx+s*d,y+rad*math.sin(2*math.pi*i/N),z+rad*math.cos(2*math.pi*i/N)) for d,rad in profile for i in range(N)]
  faces=[(j*N+i,j*N+(i+1)%N,((j+1)%len(profile))*N+(i+1)%N,((j+1)%len(profile))*N+i) for j in range(len(profile)) for i in range(N)]
  return mesh(name,verts,faces,material)
 rings(name+' tyre',[(-.115,.265),(-.105,.31),(-.065,R),(.075,R),(.117,.303),(.119,.215),(-.105,.215)],rubber)
 rings(name+' steel rim',[(.115,.212),(.128,.205),(.13,.175),(.109,.15),(.11,.066),(.09,.066),(.09,.212)],steel)
 # Dark ventilation slots lie on the recessed steel face.
 for i in range(8):
  a=2*math.pi*i/8
  yy=y+.157*math.sin(a); zz=z+.157*math.cos(a)
  bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.020,depth=.004,location=(cx+s*.126,yy,zz),rotation=(0,math.pi/2,0))
  ob=bpy.context.object; ob.name=name+' ventilation'; ob.data.materials.append(trim)
  for coll in list(ob.users_collection):coll.objects.unlink(ob)
  car.objects.link(ob)
 rings(name+' hub',[(.11,.075),(.139,.067),(.139,0),(.10,0)],steel)
for s,l in [(1,'Left'),(-1,'Right')]:
 for y,label in zip(AXLES,['front','rear']):wheel(l+' '+label,s,y)
 # Closed inner wheelhouse and curved upper liner hide the far side of each arch.
 for y in AXLES:
  vv=[]; N=12
  for x in [s*.61,s*.923]:
   vv.extend([(x,y+.40*math.cos(math.pi*i/N),R+.40*math.sin(math.pi*i/N)) for i in range(N+1)])
  ff=[tuple(range(N+1))]
  ff.extend((i,i+1,N+2+i,N+1+i) for i in range(N))
  mesh(l+' dark wheelhouse',vv,ff,trim)

# Interior masses only: enough depth behind glass to judge the cabin proportions.
box('Dashboard mass',(0,-.69,.98),(1.50,.25,.11),dark,.035)
for y in [.07,1.0]:
 for x in [-.4,.4]:
  box('Seat cushion',(x,y,.57),(.48,.47,.12),fabric,.04)
  ob=box('Seat back',(x,y+.18,.89),(.47,.13,.53),fabric,.055)
  box('Head restraint',(x,y+.20,1.22),(.26,.12,.15),fabric,.03)
# Steering wheel silhouette, deliberately not a functional cockpit.
bpy.ops.mesh.primitive_torus_add(major_segments=16,minor_segments=6,location=(.40,-.43,1.075),major_radius=.145,minor_radius=.013,rotation=(math.radians(67),0,0))
ob=bpy.context.object; ob.name='Steering silhouette'; ob.data.materials.append(trim)
for coll in list(ob.users_collection):coll.objects.unlink(ob)
car.objects.link(ob)

# Save landmarks and honest scope directly in the file.
spec={'name':'Reference-led angular family wagon','basis':'Artistic silhouette; generated concept is not a calibrated blueprint','length_body':TAIL-NOSE,'width_body':1.85,'roof_height':ROOF,'wheel_radius':R,'axles_y':AXLES,'wheel_track':TRACK,'scuttle_y':SCUTTLE,'roof_front_y':RF,'roof_rear_y':RR,'scope':'Exterior shape study; interior masses only. No articulation, UVs, collision, export or game-readiness validation.'}
scene['study_spec']=json.dumps(spec)
(out/'spec.json').write_text(json.dumps(spec,indent=2))
shutil.copy2(__file__,out/Path(__file__).name)
refs=bpy.data.collections.new('Reference — hidden from renders');scene.collection.children.link(refs)
im=bpy.data.images.load('C:/GrandTour/Art/References/Vehicles/E39StyleExploration/2026-09-30/reference-led-wagon-v3.png'); im.pack()
ob=bpy.data.objects.new('Visual target — concept, not blueprint',None);refs.objects.link(ob);ob.empty_display_type='IMAGE';ob.data=im;ob.hide_render=True;ob.hide_viewport=True

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
views=[('three-quarter',(5,-7,3.3),(0,0,.78),5.35),('side',(7,0,.83),(0,0,.83),4.95),('front',(0,-7,.83),(0,0,.83),2.8),('top',(0,0,8),(0,0,0),6.2),('rear-quarter',(5,7,3.2),(0,0,.78),5.35)]
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
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Reference_Wagon.blend'))
print('REFERENCE_WAGON_SAVED '+str(out))
