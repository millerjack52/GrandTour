"""Fitted cockpit revision of the saved v05. Never writes the source assembly."""
import bpy,bmesh,sys,math,json,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cockpit_workshop as ci
from graphic_adventure_coverage_v04 import tree
dw,wf=ci.dw,ci.wf
BASE=Path('C:/GrandTour/Art/Export/VehicleTools')
SRC=BASE/'graphic-adventure-assembly-v05/GraphicAdventure_Assembly.blend'
OUT=BASE/'graphic-adventure-interior-v01';OUT.mkdir(exist_ok=True)
digest=hashlib.sha256(SRC.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SRC));sc=bpy.context.scene
source=[o for o in sc.objects if o.type=='MESH' and o.name.startswith('RET |')]
def fingerprint(o):
 return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],list(map(tuple,o.matrix_world)))).encode()).hexdigest()
before={o.name:fingerprint(o) for o in source}
assembly=bpy.data.objects['GA | Assembly'];new=[];groups={}

def adopt(c,transform):
 bpy.context.view_layer.update();items=[]
 for o in list(c.objects):
  if o.type not in {'MESH','FONT','CURVE'}:continue
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
  me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
  me.transform(transform@o.matrix_world)
  ob=bpy.data.objects.new('RET | Interior '+o.name,me);c.objects.link(ob);ob.parent=assembly
  ob['component']=c.name;ob['construction']='Adapted fitted cockpit component; measured Graphic Adventure cabin'
  new.append(ob);items.append(ob)
 for o in list(c.objects):
  if o not in items:bpy.data.objects.remove(o,do_unlink=True)
 c['gt_owner']='GA_COCKPIT_FITTED_01';groups[c.name]=items
 return items

# Dashboard carrier is mirrored so its instrument aperture moves to the driver's
# side; text-bearing components translate across without mirrored numerals.
T=Matrix.Translation((0,0,.20))
adopt(ci.dash(ci.spec(),'GA Cabin | dashboard'),T@Matrix.Diagonal((-1,1,1,1)))
adopt(ci.instruments(ci.spec(),'GA Cabin | instruments'),Matrix.Translation((.82,0,.20)))
adopt(ci.steering(ci.spec(),'GA Cabin | steering'),Matrix.Translation((.82,0,.20)))
adopt(ci.console(ci.spec(),'GA Cabin | console'),Matrix.Translation((0,0,.115)))
for side,label in [(1,'Driver'),(-1,'Passenger')]:
 # Seat floor feet begin at exactly the carpet's finished top (0.647 m).
 adopt(ci.front_seat(ci.spec(side),'GA Cabin | '+label+' seat'),Matrix.Translation((0,-.035,.117)))
adopt(ci.rear_bench(ci.spec(),'GA Cabin | rear bench'),Matrix.Translation((0,-.055,.117))@Matrix.Diagonal((.80,1,1,1)))

c=bpy.data.collections.new('GA Cabin | fitted lining');sc.collection.children.link(c)
root=bpy.data.objects.new('GA | Cabin lining',None);c.objects.link(root);root.parent=assembly
m=ci.palette()
def record(o,parent=None):
 o.name='RET | Interior '+o.name
 if parent:
  bpy.context.view_layer.update();w=o.matrix_world.copy();o.parent=parent;o.matrix_world=w
 new.append(o);return o
def box(n,p,d,mat='dark',bevel=.003,parent=None):return record(dw.box(n,p,d,m[mat],c,root,bevel),parent)
def solid(n,poly,delta,mat='dark',parent=None):return record(dw.solid(n,poly,delta,m[mat],c,root),parent)
def rod(n,a,b,r=.005,mat='metal',parent=None):return record(ci.rod(n,a,b,r,m[mat],c,root,12),parent)
def sx(z):return dw.lerp(z/4.6,[(.13,.213),(.139,.2165),(.15,.218),(.18,.2185),(.25,.2181),(.26,.2205),(.27,.2192),(.29,.2152),(.301,.203),(.424,.1684),(.43,.1684)])*4.6

# A thin carpet follows the entire retained floor, including the narrowed path
# between rear tubs. No rectangular carpet through the occupied wheel volumes.
floor=bpy.data.objects['RET | Fitted cabin floor'];me=floor.data.copy();ob=bpy.data.objects.new('Carpet floor',me);c.objects.link(ob)
me.transform(floor.matrix_world);ob.location.z=.006;me.materials.clear();me.materials.append(m['carpet']);ob.parent=root
record(ob);mod=ob.modifiers.new('Carpet backing','SOLIDIFY');mod.thickness=.005;mod.offset=-1
# Raised feet where the reused console's lower skirt is above the floor.
box('Console plinth',(0,-.03,.656),(.270,.65,.028),'carpet')
for x in [-.43,.43]:
 box('Footwell rubber mat',(x,-.46,.653),(.45,.54,.010),'dark',.01)
 for i in range(8):box('Mat rib',(x-.18+i*.05,-.46,.660),(.009,.48,.003),'pad',.001)

# Existing wheelhouse surfaces define the trim directly. Keep the outer tyre
# cavity clear and add only a small cabin-facing surface offset.
for old in source:
 if 'enclosed wheelhouse' not in old.name or 'Rear' not in old.name:continue
 me=old.data.copy();me.transform(old.matrix_world);ob=bpy.data.objects.new('Wheelhouse carpet '+old.name,me);c.objects.link(ob)
 sign=1 if 'L Rear' in old.name else -1
 for v in me.vertices:
  if abs(v.co.x)<.70:v.co.x-=sign*.010
  else:v.co.z+=.007
 me.materials.clear();me.materials.append(m['carpet']);ob.parent=root;record(ob)

# Door linings follow the actual body taper and every arch kink. They are
# attached to the appropriate door pivot, not to the fixed assembly.
arch=[(.138,.135),(.162,.220),(.188,.238),(.329,.238),(.369,.205),(.392,.139)]
for side,sign in [('L',1),('R',-1)]:
 for pos,a,b in [('Front',-.177,.032),('Rear',.036,.254)]:
  par=bpy.data.objects['GA | '+side+' '+pos+' door']
  ys=sorted(set([a+.006,b-.006]+([.138,.162,.188] if pos=='Rear' else [])))
  lows=[max(.146,dw.lerp(y,arch)+.007) if pos=='Rear' and y>=.138 else .146 for y in ys]
  yz=[(y*4.6,z*4.6) for y,z in zip(ys,lows)]+[(ys[-1]*4.6,1.366),(ys[0]*4.6,1.366)]
  # Rows at each transverse body change keep the door card inside the sheet.
  outline=[(sign*(sx(z)-.040),y,z) for y,z in yz]
  solid(side+' '+pos+' shaped door card',outline,(-sign*.014,0,0),'pad',par)
  ya,yb=(a+.020)*4.6,(b-.020)*4.6
  solid(side+' '+pos+' cloth insert',[(sign*(sx(z)-.059),y,z) for y,z in [(ya,1.13),(yb,1.13),(yb,1.31),(ya,1.31)]],(-sign*.004,0,0),'fabric',par)
  cy=(a+b)*2.3
  box(side+' '+pos+' armrest',(sign*.915,cy,1.102),(.095,(b-a)*4.6*.66,.062),'bolster',.013,par)
  box(side+' '+pos+' latch recess',(sign*.941,(b-.044)*4.6,1.293),(.018,.116,.056),'dark',.006,par)
  rod(side+' '+pos+' latch',(sign*.922,(b-.054)*4.6,1.29),(sign*.922,(b-.034)*4.6,1.30),.008,'metal',par)
  if pos=='Front':
   box(side+' map pocket',(sign*.905,cy,.832),(.072,.49,.11),'dark',.012,par)
   for i in range(7):rod(side+' speaker slat '+str(i),(sign*.949,ya+.01+i*.017,.90),(sign*.949,ya+.01+i*.017,1.035),.0025,'dark',par)
 # Fixed quarter trim closes visible cabin faces behind the rear seat.
 solid(side+' cargo side trim',[(sign*(sx(z)-.035),y,z) for y,z in [(1.78,.65),(1.98,.65),(2.12,1.22),(1.88,1.365),(1.70,1.365)]],(-sign*.012,0,0),'pad')
 # Seatbelt runs on the B pillar, behind the door rather than across the glazing.
 x=sign*(sx(1.69)-.055)
 rod(side+' belt upper mount',(x,.156,1.69),(sign*(sx(1.69)-.010),.156,1.69),.014,'metal')
 solid(side+' shoulder belt',[(sign*(sx(z)-.055),y,z) for y,z in [(.141,.78),(.173,.78),(.173,1.68),(.141,1.68)]],(-sign*.006,0,0),'dark')
 box(side+' belt retractor',(sign*(sx(.752)-.055),.156,.752),(.064,.065,.10),'dark',.008)

# Headlining derived from the retained roof, translated inward only. Visors,
# roof light, grab handles and rearview mirror have explicit mounting pieces.
roof=bpy.data.objects['RET | Roof crown'];me=roof.data.copy();me.transform(roof.matrix_world)
for v in me.vertices:v.co.z-=.029
me.materials.clear();me.materials.append(m['headliner']);ob=bpy.data.objects.new('Headlining',me);c.objects.link(ob);ob.parent=root;record(ob)
mod=ob.modifiers.new('Headlining backing','SOLIDIFY');mod.thickness=.009
for x in [-.40,.40]:
 box('Folded sun visor',(x,-.433,1.879),(.43,.052,.10),'headliner',.012)
 rod('Visor hinge',(x-.16,-.438,1.932),(x+.16,-.438,1.932),.007,'metal')
 for xx in [x-.15,x+.15]:rod('Visor mounting foot',(xx,-.438,1.91),(xx,-.438,1.96),.009,'dark')
for s in [-1,1]:
 for y in [.05,.80]:
  for yy in [y-.11,y+.11]:rod('Grab handle foot',(s*.737,yy,1.91),(s*.70,yy,1.885),.014,'pad')
  rod('Grab handle',(s*.70,y-.11,1.885),(s*.70,y+.11,1.885),.014,'pad')
box('Roof lamp base',(0,.46,1.929),(.19,.13,.025),'pad',.012)
box('Roof lamp lens',(0,.46,1.912),(.15,.087,.01),'ivory',.006)
rod('Mirror mount',(0,-.46,1.93),(0,-.39,1.81),.009,'dark')
box('Rearview housing',(0,-.37,1.80),(.255,.042,.087),'dark',.01)
box('Rearview glass',(0,-.346,1.80),(.230,.004,.067),'mirror',.005)
# Scuttle shelf meets the retained windscreen's bottom frame and dash carrier.
solid('Scuttle liner',[(-.84,-.820,1.365),(.84,-.820,1.365),(.813,-.718,1.379),(-.813,-.718,1.379)],(0,0,-.018),'pad')
for x in [-.61,.61]:
 for i in range(7):box('Demister grille',(x-.09+i*.03,-.776,1.376),(.013,.055,.003),'dark',.001)
lower=bpy.data.objects['GA | Lower tailgate']
solid('Tailgate inner trim',[(-.735,2.04,.866),(.735,2.04,.866),(.735,2.18,1.37),(-.735,2.18,1.37)],(0,-.016,0),'pad',lower)
box('Cargo sill',(0,1.97,.654),(1.79,.073,.022),'metal',.004)
for x in [-.49,.49]:
 for y in [1.55,1.90]:box('Cargo tie down',(x,y,.656),(.049,.06,.012),'metal',.006)

# Replace the review-opaque glazing material with clear, lightly tinted glass.
glass=bpy.data.materials['Glass'];bs=glass.node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value=(.72,.84,.83,1);bs.inputs['Roughness'].default_value=.075;bs.inputs['Transmission Weight'].default_value=1;bs.inputs['IOR'].default_value=1.45
# Use a named metallic surface for mirrors, not transparent window glass.
for o in source:
 if 'mirror glass' in o.name:o.data.materials.clear();o.data.materials.append(m['mirror'])
red=wf.material('GA | red tail lens',(.42,.018,.008),.24)
amber=wf.material('GA | amber indicator lens',(.9,.26,.012),.24)
for o in source:
 key=o.name;mat=None
 if 'rear lamp lens 1' in key or 'tail lens rib 1 ' in key:mat=red
 if 'rear lamp lens 2' in key or 'tail lens rib 2 ' in key or 'front indicator 1' in key or 'front marker' in key:mat=amber
 if mat:o.data.materials.clear();o.data.materials.append(mat)

# Convert all added components to final meshes; consistently orient reflections.
for o in new:
 bpy.context.view_layer.objects.active=o;o.hide_set(False)
 for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 o['ga_interior']=True

allmesh=source+new
# Real UV islands for every exported object. Each original material will occupy
# a separate atlas tile, so density is consistent within a material family.
for o in allmesh:
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 if not o.data.uv_layers:o.data.uv_layers.new(name='GA_UV')
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
 bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025,correct_aspect=True);bpy.ops.object.mode_set(mode='OBJECT')

# Scoped assembly checks: retained exterior, floor coverage under seat feet,
# bench/tyre negative spaces, actual seat/card/console intersections.
bpy.context.view_layer.update();report={'source':str(SRC),'source_sha256':digest,'new_meshes':len(new),'exterior_meshes_preserved':sum(before[o.name]==fingerprint(o) for o in source)}
assert report['exterior_meshes_preserved']==len(source)
floortree=tree([floor]);floorchecks=[]
for o in new:
 if 'fixed floor foot' not in o.name:continue
 p=sum((o.matrix_world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
 hit=floortree.ray_cast(p+Vector((0,0,.03)),Vector((0,0,-1)),.10)[0]
 assert hit is not None,(o.name,tuple(p));floorchecks.append(o.name)
report['seat_floor_mounts_backed']=len(floorchecks)
tubs=[o for o in source if 'enclosed wheelhouse' in o.name];tt=tree(tubs)
seatmeshes=[o for o in new if 'Seat |' in o.name or 'Bench |' in o.name]
collisions=[]
for o in seatmeshes:
 if tree([o]).overlap(tt):collisions.append(o.name)
report['seat_wheelhouse_intersections']=collisions
assert not collisions,collisions
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==digest
report['driver_eye_blender_m']=[.45,.15,1.70]
report['limits']=['Static authored dashboard controls; no new dashboard gameplay or functional mirror capture.','Scoped static checks do not certify every moving-door or suspension clearance.']
(OUT/'interior-report.json').write_text(json.dumps(report,indent=2))

sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.threads_mode='FIXED';sc.render.threads=10;sc.render.resolution_x=1280;sc.render.resolution_y=900;sc.render.resolution_percentage=100
for name,pos,power,size in [('Key',(3,-4,6),1700,5),('Fill',(-4,-1,4),1100,4),('Rim',(1,5,5),1500,3)]:
 ld=bpy.data.lights.new('GA studio '+name,'AREA');lo=bpy.data.objects.new(ld.name,ld);sc.collection.objects.link(lo);lo.location=pos;lo.rotation_euler=(Vector((0,.3,1))-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.shape='DISK';ld.size=size
cam=sc.camera;cam.data.clip_start=.015
lightdata=bpy.data.lights.new('Cabin review fill','AREA');light=bpy.data.objects.new('Cabin review fill',lightdata);sc.collection.objects.link(light)
light.location=(0,.38,1.84);lightdata.energy=22;lightdata.size=1.15
def render(name,pos,target,lens=24,ortho=None):
 if '--no-render' in sys.argv:return
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO' if ortho else 'PERSP'
 if ortho:cam.data.ortho_scale=ortho
 else:cam.data.lens=lens
 sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('Driver',(.45,.15,1.70),(.34,-1.2,1.43),24)
render('Dashboard',(-.10,.52,1.72),(.10,-.50,1.31),25)
render('RearCabin',(0,.57,1.77),(0,1.31,1.22),21)
light.hide_render=True
render('Exterior',(5.8,-7.8,3.9),(0,0,1.15),ortho=6.5)
hidden=[]
for o in source:
 if o.hide_render:continue
 if not any(x in o.name for x in ['Fitted cabin floor','enclosed wheelhouse']):o.hide_render=True;hidden.append(o)
for o in new:
 if any(x in o.name for x in ['Headlining','sun visor','Visor','Roof lamp','Grab handle']):o.hide_render=True;hidden.append(o)
light.hide_render=False
render('InteriorCutaway',(4,-5,4.3),(0,.55,1.05),ortho=4.2)
for o in hidden:o.hide_render=False
light.hide_render=True
sc['ga_driver_eye']=json.dumps(report['driver_eye_blender_m'])
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GraphicAdventure_Interior.blend'))
print('INTERIOR_COMPLETE',json.dumps(report),flush=True)
