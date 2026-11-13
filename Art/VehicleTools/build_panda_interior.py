"""Fitted Panda-specific cockpit, derived from the protected rounded v03."""
import bpy,bmesh,ast,math,json,hashlib,shutil
from pathlib import Path
from mathutils import Vector,Matrix
BASE=Path('C:/GrandTour/Art/Export/VehicleTools');SRC=BASE/'panda-rounded-v03';OUT=BASE/'panda-interior-v01';OUT.mkdir(exist_ok=True)
if (OUT/'delivery-manifest.json').exists():raise RuntimeError('Delivered revision protected; use a new folder')
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Panda_Assembly.blend'));sc=bpy.context.scene;S=3.6
def fingerprint(o):return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],list(map(tuple,o.matrix_world)))).encode()).hexdigest()
old_interior=list(bpy.data.collections['Interior'].objects);removed=[o.name for o in old_interior if o.type=='MESH']
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH' and o not in old_interior}
for o in old_interior:
 if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
root=bpy.data.objects['PANDA | assembly'];cols={c.name:c for c in bpy.data.collections};owned=[]
for n in ['Panda cabin | seating','Panda cabin | dashboard','Panda cabin | trim','Panda cabin | controls']:
 c=bpy.data.collections.get(n) or bpy.data.collections.new(n)
 if c.name not in sc.collection.children:sc.collection.children.link(c)
 cols[n]=c
M={m.name.split(' | ')[-1]:m for m in bpy.data.materials if m.name.startswith('Panda | ')}
for n,col,rough in [('Cabin charcoal',(.028,.034,.032,1),.72),('Cabin olive',(.18,.22,.15,1),.82),('Cabin canvas',(.46,.42,.29,1),.88),('Cabin stripe',(.66,.60,.41,1),.8),('Cabin floor',(.047,.058,.045,1),.91),('Cabin marking',(.84,.81,.68,1),.6),('Cabin red',(.48,.035,.022,1),.58)]:
 m=bpy.data.materials.new('Panda | '+n);m.diffuse_color=col;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=col;p.inputs['Roughness'].default_value=rough;M[n]=m
code=ast.parse(Path('C:/GrandTour/Art/VehicleTools/build_panda_assembly.py').read_text())
for node in code.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['parent_keep','make','orient','grid','box','tube','cyl','rotate_about','interp','sx']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'panda_helpers','exec'))
spec=json.loads((SRC/'vehicle-spec.json').read_text());WIDTH=spec['width_profile'];ARCH=spec['arches']
SEAT='Panda cabin | seating';DASH='Panda cabin | dashboard';TRIM='Panda cabin | trim';CTRL='Panda cabin | controls'
def cb(n,c,d,mat='Cabin charcoal',bevel=.003,group=DASH,parent=None):
 o=box('CAB | '+n,c,d,group,mat,bevel,parent)
 for m in o.modifiers:
  if m.type=='BEVEL':m.segments=4
 for p in o.data.polygons:p.use_smooth=True
 o.data.set_sharp_from_angle(angle=.6)
 if bevel:m=o.modifiers.new('Broad face normals','WEIGHTED_NORMAL');m.keep_sharp=True
 return o
def ct(n,pts,r=.0015,mat='Cabin charcoal',group=CTRL,parent=None,closed=False):return tube('CAB | '+n,pts,r,group,mat,parent,segments=12,closed=closed)
def cc(n,a,b,r,mat='Cabin charcoal',group=CTRL,parent=None):return cyl('CAB | '+n,a,b,r,group=group,mat=mat,parent=parent,segments=24)
def txt(n,value,p,size=.006,mat='Cabin marking',parent=None):
 cu=bpy.data.curves.new(n,'FONT');cu.body=value;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size*S;cu.extrude=.00005*S;cu.resolution_u=2
 o=bpy.data.objects.new('CAB | '+n,cu);cols[DASH].objects.link(o);o.location=Vector(p)*S;o.rotation_euler=Matrix(((-1,0,0),(0,0,1),(0,1,0))).to_euler();cu.materials.append(M[mat]);bpy.context.view_layer.update();parent_keep(o,parent or root)
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');owned.append(o);return o

# Carpet follows each existing floor bay instead of hiding an undersized floor
# with one rectangular slab. The structural floor stays untouched.
for floor in [o for o in sc.objects if o.name.startswith('Fitted floor bay')]:
 v=[floor.matrix_world@p.co/S for p in floor.data.vertices];x0,x1=min(p.x for p in v),max(p.x for p in v);y0,y1=min(p.y for p in v),max(p.y for p in v)
 a=max(y0,-.188);b=min(y1,.462)
 if b<=a:continue
 cb('Floor carpet '+floor.name,(0,(a+b)/2,.137),(x1-x0-.002,b-a,.004),'Cabin floor',0,TRIM)
for sign in [-1,1]:
 for axle in ['F','R']:
  for part in ['wheelhouse roof','inner wheelhouse wall']:
   old=bpy.data.objects[('L' if sign>0 else 'R')+axle+' '+part];me=old.data.copy();me.transform(old.matrix_world);me.materials.clear();me.materials.append(M['Cabin floor'])
   for v in me.vertices:
    if part=='inner wheelhouse wall':v.co.x-=sign*.002*S
    else:v.co.z+=.002*S
   o=bpy.data.objects.new('CAB | Tub lining '+str(sign)+axle+' '+part,me);cols[TRIM].objects.link(o);parent_keep(o,root);owned.append(o)

# Soft front seats with dedicated rails, connected floor feet and framed inserts.
def seat_back_y(z):return .077+(z-.216)*.14
for sign,label in [(1,'Driver'),(-1,'Passenger')]:
 x=sign*.096
 for dx in [-.042,.042]:
  cb(label+' seat rail',(x+dx,.018,.152),(.009,.153,.008),'Steel',.001,SEAT)
  for y in [-.043,.078]:cb(label+' floor foot '+str(dx)+' '+str(y),(x+dx,y,.1445),(.017,.018,.011),'Steel',.001,SEAT)
  cb(label+' seat riser',(x+dx,.018,.171),(.008,.114,.030),'Cabin charcoal',.002,SEAT)
 cb(label+' seat cushion',(x,.014,.201),(.127,.151,.035),'Cabin olive',.009,SEAT)
 cb(label+' cushion fabric',(x,.010,.218),(.091,.119,.010),'Cabin canvas',.005,SEAT)
 for k in range(5):cb(label+' cushion stripe '+str(k),(x-.033+k*.0165,.010,.2231),(.003,.109,.0008),'Cabin stripe',.0003,SEAT)
 back=cb(label+' seat back',(x,.094,.284),(.125,.030,.145),'Cabin olive',.008,SEAT);rotate_about(back,(x,.094,.284),-.14)
 insert=cb(label+' backrest fabric',(x,.076,.288),(.091,.006,.111),'Cabin canvas',.004,SEAT);rotate_about(insert,(x,.094,.284),-.14)
 for k in range(5):
  ob=cb(label+' backrest stripe '+str(k),(x-.033+k*.0165,.0726,.288),(.003,.0008,.099),'Cabin stripe',.0003,SEAT);rotate_about(ob,(x,.094,.284),-.14)
 for dx in [-.027,.027]:cc(label+' headrest post',(x+dx,.103,.345),(x+dx,.103,.376),.0018,'Steel',SEAT)
 cb(label+' headrest',(x,.105,.379),(.088,.034,.046),'Cabin olive',.008,SEAT)
 cb(label+' headrest cloth',(x,.087,.379),(.065,.003,.029),'Cabin canvas',.004,SEAT)
 ct(label+' seat slide lever',[(x-.031,-.060,.180),(x-.031,-.072,.178),(x+.031,-.072,.178)],.0015,'Steel',SEAT)
 bx=x-sign*.070
 ct(label+' buckle stalk',[(bx,.051,.151),(bx,.051,.220)],.0017,'Cabin charcoal',SEAT)
 cb(label+' buckle housing',(bx,.051,.224),(.009,.015,.019),'Cabin charcoal',.002,SEAT)
 cb(label+' buckle release',(bx,.0588,.229),(.006,.001,.005),'Cabin red',.0005,SEAT)

# Rear bench stays between inner tubs; its support frame meets the floor.
for x in [-.104,.104]:
 for y in [.193,.275]:cb('Rear bench floor foot '+str(x)+' '+str(y),(x,y,.141),(.025,.025,.008),'Steel',.001,SEAT)
 for y in [.193,.275]:cb('Rear bench support '+str(x)+' '+str(y),(x,y,.181),(.012,.016,.072),'Steel',.001,SEAT)
cb('Rear bench crossmember',(0,.25,.214),(.258,.028,.012),'Cabin charcoal',.002,SEAT)
cb('Rear bench cushion',(0,.234,.235),(.263,.142,.035),'Cabin olive',.009,SEAT)
cb('Rear bench back',(0,.310,.313),(.263,.027,.123),'Cabin olive',.008,SEAT)
for x in [-.069,.069]:
 cb('Rear cushion fabric '+str(x),(x,.231,.252),(.110,.112,.009),'Cabin canvas',.005,SEAT)
 cb('Rear back fabric '+str(x),(x,.2945,.314),(.110,.005,.092),'Cabin canvas',.004,SEAT)
 for k in range(5):
  xx=x-.040+k*.020
  cb('Rear cushion stripe '+str(xx),(xx,.231,.2567),(.003,.102,.0008),'Cabin stripe',.0003,SEAT)
  cb('Rear back stripe '+str(xx),(xx,.2916,.314),(.003,.0008,.085),'Cabin stripe',.0003,SEAT)
 for dx in [-.024,.024]:cc('Rear headrest post',(x+dx,.313,.369),(x+dx,.313,.390),.0015,'Steel',SEAT)
 cb('Rear headrest '+str(x),(x,.313,.398),(.08,.028,.035),'Cabin olive',.006,SEAT)
 cb('Rear belt clasp '+str(x),(x*.40,.292,.260),(.009,.012,.010),'Cabin red',.001,SEAT)

# Dashboard: open fabric sling and rounded cross-tube; no giant filled slab.
for x in [-.174,.174]:cb('Dash mounting foot '+str(x),(x,-.182,.283),(.013,.017,.043),'Cabin charcoal',.002,DASH)
ct('Dashboard cross tube',[(-.198,-.143,.286),(.198,-.143,.286)],.0045,'Cabin charcoal',DASH)
rows=[]
for y,z in [(-.184,.310),(-.173,.280),(-.151,.270),(-.122,.275),(-.114,.286)]:rows.append([(x,y,z) for x in [-.194,-.15,-.08,0,.08,.15,.194]])
grid('CAB | Fabric dashboard sling',rows,(0,1,1),group=DASH,mat='Cabin canvas',thick=.002)
ct('Sling upper rolled lip',[(-.194,-.114,.286),(.194,-.114,.286)],.0024,'Cabin olive',DASH)
for x in [-.194,.194]:
 pts=[(x,y,z) for y,z in [(-.184,.310),(-.173,.280),(-.151,.270),(-.122,.275),(-.114,.286)]]
 make('CAB | Sling end '+str(x),pts,[tuple(range(len(pts)))],DASH,'Cabin canvas',thick=.0015)
cb('Upper dash rail',(0,-.174,.316),(.394,.020,.016),'Cabin charcoal',.004,DASH)
for x in [-.15,.15]:
 cb('Demister slot '+str(x),(x,-.174,.3245),(.065,.006,.001),'Cabin charcoal',.0005,DASH)
 for k in range(8):cb('Demister vane',(x-.027+k*.0077,-.174,.3251),(.002,.005,.0008),'Cabin olive',.0002,DASH)

# Instrument cassette consists of four real rim strips, rear wall and recessed
# face. The speedometer and auxiliary gauges remain readable from the driver.
cx=.088;cy=-.128;cz=.328
cb('Instrument rear shell',(cx,cy-.018,cz),(.143,.010,.061),'Cabin charcoal',.005,DASH)
for name,pos,dim in [('top',(cx,cy,cz+.027),(.145,.038,.009)),('bottom',(cx,cy,cz-.027),(.145,.038,.009)),('left',(cx+.068,cy,cz),(.009,.038,.05)),('right',(cx-.068,cy,cz),(.009,.038,.05))]:cb('Instrument rim '+name,pos,dim,'Cabin charcoal',.003,DASH)
cb('Recessed instrument face',(cx,cy+.009,cz),(.129,.003,.044),'Cabin charcoal',.001,DASH)
def gauge(n,x,z,r,y=-.115):
 cc(n+' bezel',(x,y-.001,z),(x,y+.001,z),r,'Steel',DASH)
 cc(n+' dark face',(x,y+.001,z),(x,y+.0018,z),r*.91,'Cabin charcoal',DASH)
 return y+.0022
gy=gauge('Speedometer',.110,.329,.0215)
for i in range(33):
 a=math.radians(-30+i*240/32);rr=.018;end=.0158 if i%4==0 else .017
 ct('Speedometer tick '+str(i),[(.110+rr*math.cos(a),gy,.329+rr*math.sin(a)),(.110+end*math.cos(a),gy,.329+end*math.sin(a))],.00024,'Cabin marking',DASH)
 if i%8==0:txt('Speed label '+str(i),str(i*5),(.110+.0128*math.cos(a),gy+.0002,.329+.0128*math.sin(a)),.0032)
ct('Speed needle',[(.110,gy+.0007,.329),(.110+.014*math.cos(.45),gy+.0007,.329+.014*math.sin(.45))],.00045,'Cabin red',DASH)
cc('Speed needle hub',(.110,gy,.329),(.110,gy+.0013,.329),.0016,'Steel',DASH)
txt('Speed units','km/h',(.110,gy+.0003,.320),.0026)
for x,label,ang in [(.066,'FUEL',1.8),(.042,'TEMP',1.1)]:
 yy=gauge(label,x,.335,.009)
 for i in range(5):
  a=math.radians(15+i*37.5);ct(label+' tick',[(x+.007*math.cos(a),yy,.335+.007*math.sin(a)),(x+.0056*math.cos(a),yy,.335+.0056*math.sin(a))],.00025,'Cabin marking',DASH)
 ct(label+' needle',[(x,yy+.0003,.335),(x+.0055*math.cos(ang),yy+.0003,.335+.0055*math.sin(ang))],.00035,'Cabin red',DASH)
 txt(label+' label',label,(x,yy,.326),.0026)
for i,mat in enumerate(['Cabin red','Amber','Cabin olive','Cabin red']):cb('Warning lamp '+str(i),(.040+i*.011,-.114,.315),(.005,.001,.003),mat,.0005,DASH)
cb('Odometer recess',(.110,-.113,.312),(.029,.002,.005),'Cabin floor',.0005,DASH);txt('Odometer','084219',(.110,-.1117,.312),.003)

# Central open vents, simple slider controls and radio below the rail.
cb('Centre control back',(-.025,-.151,.320),(.062,.019,.061),'Cabin charcoal',.003,DASH)
for x in [-.041,-.010]:
 cb('Vent recess '+str(x),(x,-.139,.337),(.026,.003,.023),'Cabin charcoal',.001,DASH)
 for k in range(5):cb('Vent louvre',(x,-.1367,.328+k*.004),(.024,.002,.0015),'Cabin olive',.0003,DASH)
for z in [.317,.306]:
 cb('Heater slider slot',(-.025,-.139,z),(.048,.002,.0025),'Cabin floor',.0005,DASH)
 cb('Heater slider grip',(-.031 if z>.31 else -.018,-.136,z),(.006,.006,.005),'Cabin marking',.001,DASH)
cb('Hazard switch',(-.025,-.137,.351),(.010,.006,.007),'Cabin red',.001,DASH);txt('Hazard mark','!',(-.025,-.1338,.351),.005)
cb('Radio housing',(-.022,-.145,.279),(.075,.045,.022),'Cabin charcoal',.003,DASH)
cb('Radio display',(-.022,-.1215,.282),(.038,.001,.008),'Cabin floor',.0005,DASH);txt('Radio display digits','FM  94.2',(-.022,-.1208,.282),.0038)
for x in [-.052,.008]:cc('Radio knob',(x,-.122,.280),(x,-.116,.280),.004,'Cabin charcoal',DASH)
txt('Passenger dash badge','PANDA  4x4',(-.125,-.1130,.309),.004)
for o in owned:
 if o.name.startswith('CAB | Radio'):o.location+=Vector((-.101,.009,.022))*S
 if any(o.name.startswith('CAB | '+k) for k in ['Instrument','Recessed instrument','Speed','FUEL','TEMP','Warning lamp','Odometer']):o.location.y+=.014*S
 if any(o.name.startswith('CAB | '+k) for k in ['Centre control','Vent recess','Vent louvre','Heater slider','Hazard']):o.location.y+=.012*S
for x in [-.147,-.099]:cb('Radio support '+str(x),(x,-.143,.290),(.009,.010,.012),'Cabin charcoal',.001,DASH)

# Steering ring and spokes share one inclined plane and real column mounting.
hub=Vector((.096,-.065,.310));up=Vector((0,-.34,.94)).normalized();right=Vector((1,0,0));axis=right.cross(up)
cc('Steering column',(.096,-.158,.283),tuple(hub),.006,'Cabin charcoal',CTRL)
ring=[tuple(hub+.041*(math.cos(a)*right+math.sin(a)*up)) for a in [i*math.tau/48 for i in range(48)]]
ct('Steering rim',ring,.0035,'Cabin charcoal',CTRL,closed=True)
for a in [math.radians(10),math.radians(170),math.radians(270)]:ct('Steering spoke',[tuple(hub),tuple(hub+.037*(math.cos(a)*right+math.sin(a)*up))],.0035,'Cabin charcoal',CTRL)
cc('Steering boss',tuple(hub+axis*.001),tuple(hub-axis*.005),.010,'Cabin charcoal',CTRL)
txt('Steering badge','FIAT',(.096,-.059,.310),.0045)
for sign in [-1,1]:
 ct('Column stalk '+str(sign),[(.096+sign*.004,-.088,.301),(.096+sign*.042,-.085,.301)],.0015,'Cabin charcoal',CTRL)
 cb('Stalk grip '+str(sign),(.096+sign*.045,-.084,.301),(.015,.006,.006),'Cabin charcoal',.002,CTRL)
cc('Ignition barrel',(.073,-.088,.299),(.073,-.081,.299),.0035,'Steel',CTRL)
cb('Ignition key',(.073,-.078,.296),(.005,.0015,.013),'Cabin charcoal',.001,CTRL)

cb('Centre tunnel',(0,-.008,.153),(.035,.304,.026),'Cabin charcoal',.005,CTRL)
cb('Gear boot base',(0,-.036,.169),(.028,.036,.008),'Cabin charcoal',.003,CTRL)
for i in range(5):cb('Gear boot fold '+str(i),(0,-.036,.174+i*.003),(.026-i*.003,.033-i*.003,.003),'Cabin charcoal',.001,CTRL)
ct('Gear stick',[(0,-.036,.183),(0,-.017,.238)],.002,'Steel',CTRL)
cb('Gear knob',(0,-.017,.241),(.013,.014,.017),'Cabin charcoal',.004,CTRL)
ct('Handbrake lever',[(0,.04,.167),(0,.091,.189)],.0028,'Steel',CTRL)
cb('Handbrake grip',(0,.087,.189),(.008,.031,.010),'Cabin charcoal',.003,CTRL)
for x,name in [(.133,'Clutch'),(.100,'Brake'),(.069,'Accelerator')]:
 ct(name+' pedal arm',[(x,-.177,.237),(x,-.149,.178)],.0018,'Steel',CTRL)
 cb(name+' pedal pad',(x,-.146,.179),(.017,.007,.027),'Cabin charcoal',.002,CTRL)
 for k in range(4):cb(name+' pedal rib',(x,-.142,.171+k*.005),(.014,.001,.001),'Cabin olive',.0002,CTRL)
for sign in [-1,1]:
 x=sign*.096;cb('Footwell mat '+str(sign),(x,-.101,.141),(.122,.137,.003),'Cabin charcoal',.003,TRIM)
 for k in range(10):cb('Mat groove '+str(sign)+' '+str(k),(x-.052+k*.0115,-.101,.143),(.002,.125,.0008),'Cabin floor',.0003,TRIM)

# Door cards follow body taper; accessories are parented to the actual doors.
for sign,side in [(1,'L'),(-1,'R')]:
 dp=bpy.data.objects[side+' door hinge'];levels=[.145,.16,.19,.22,.27,.303,.318]
 grid('CAB | '+side+' shaped door card',[[(sign*(sx(z)-.010),y,z) for y in [-.158,-.11,0,.115]] for z in levels],(-sign,0,0),group=TRIM,mat='Cabin olive',thick=.003,parent=dp)
 grid('CAB | '+side+' door cloth insert',[[(sign*(sx(z)-.014),y,z) for y in [-.140,.100]] for z in [.205,.22,.27,.290]],(-sign,0,0),group=TRIM,mat='Cabin canvas',thick=.001,parent=dp)
 cb(side+' armrest',(sign*.193,-.006,.258),(.023,.094,.018),'Cabin charcoal',.004,TRIM,dp)
 for y in [-.041,.031]:cb(side+' armrest bracket',(sign*.211,y,.252),(.017,.014,.021),'Cabin charcoal',.002,TRIM,dp)
 cb(side+' latch recess',(sign*.209,-.116,.294),(.004,.027,.013),'Cabin charcoal',.002,TRIM,dp)
 cb(side+' latch lever',(sign*.205,-.116,.295),(.004,.019,.004),'Steel',.001,TRIM,dp)
 x=sign*(sx(.236)-.016)
 cc(side+' window winder base',(x,-.080,.236),(x-sign*.006,-.080,.236),.006,'Cabin charcoal',TRIM,dp)
 ct(side+' manual window winder',[(x-sign*.006,-.080,.236),(x-sign*.008,-.056,.218)],.002,'Steel',TRIM,dp)
 cc(side+' winder knob',(x-sign*.008,-.056,.218),(x-sign*.017,-.056,.218),.004,'Cabin charcoal',TRIM,dp)
 cb(side+' map pocket',(sign*.203,.048,.181),(.019,.096,.035),'Cabin charcoal',.003,TRIM,dp)
 # Parked belt at B pillar has upper guide and lower reel, not a floating strip.
 bx=sign*.183
 cb(side+' belt reel',(bx,.117,.173),(.014,.022,.030),'Cabin charcoal',.002,TRIM)
 ct(side+' upper belt guide',[(sign*.185,.125,.404),(sign*.176,.119,.404)],.003,'Steel',TRIM)
 grid('CAB | '+side+' parked front belt',[[(bx+dx,y,z) for dx in [-.005,.005]] for y,z in [(.117,.178),(.115,.294),(.119,.404)]],(0,-1,0),group=TRIM,mat='Cabin charcoal',thick=.0007)
 cb(side+' belt tongue',(bx,.113,.267),(.012,.002,.014),'Steel',.001,TRIM)
 # Inner A/B/rear pillar cover strips sit inboard of glazing.
 ct(side+' A pillar lining',[(sign*(sx(z)-.007),interp(z,[(.322,-.184),(.455,-.041)])+.004,z) for z in [.328,.36,.40,.444]],.003,'Cabin charcoal',TRIM)
 ct(side+' B pillar lining',[(sign*(sx(z)-.007),.126,z) for z in [.323,.36,.4,.443]],.003,'Cabin charcoal',TRIM)
 ct(side+' rear pillar lining',[(sign*(sx(z)-.008),interp(z,[(.322,.474),(.455,.394)])-.009,z) for z in [.328,.36,.40,.444]],.003,'Cabin charcoal',TRIM)
 grid('CAB | '+side+' rear quarter trim',[[(sign*(sx(z)-.012),y,z) for y in [.149,.30,.433]] for z in [.239,.27,.303,.319]],(-sign,0,0),group=TRIM,mat='Cabin olive',thick=.002)
 grid('CAB | '+side+' rear parked belt',[[(sign*.134+dx,y,z) for dx in [-.004,.004]] for y,z in [(.332,.255),(.338,.339),(.346,.392)]],(0,-1,0),group=TRIM,mat='Cabin charcoal',thick=.0006)
 ct(side+' rear belt upper bracket',[(sign*.134,.346,.392),(sign*(sx(.392)-.012),.346,.392)],.0018,'Steel',TRIM)

# Cargo bulkhead fits the inward tail profile and retains useful load space.
grid('CAB | Tailgate inner lining',[[(x,interp(z,spec['tail_profile'])-.010,z) for x in [-.166,0,.166]] for z in [.15,.19,.22,.27,.301]],(0,-1,0),group=TRIM,mat='Cabin olive',thick=.002,parent=bpy.data.objects['Tailgate upper hinge'])
for x in [-.11,.11]:
 ct('Cargo tie-down '+str(x),[(x-.008,.417,.143),(x-.008,.417,.151),(x+.008,.417,.151),(x+.008,.417,.143)],.0015,'Steel',TRIM)
cb('Cargo threshold',(0,.444,.144),(.272,.016,.010),'Cabin charcoal',.002,TRIM)
for x in [-.105,-.07,-.035,0,.035,.07,.105]:cb('Threshold rib',(x,.444,.1495),(.003,.014,.001),'Steel',.0003,TRIM)

# A curved light-coloured roof lining and attached small fittings finish views
# through the windows without reducing the established exterior roof profile.
rows=[]
for i in range(13):
 y=-.023+i*.405/12;row=[]
 for j in range(17):
  t=-1+j/8;z=.447+.010*max(0,1-abs(t)**6)**.6*max(0,math.sin(math.pi*(y+.041)/.435))**.65;row.append((t*.169,y,z))
 rows.append(row)
o=grid('CAB | Headlining',rows,(0,0,-1),group=TRIM,mat='Cabin canvas',thick=.002,smooth=True)
for sign in [-1,1]:
 cb('Sun visor '+str(sign),(sign*.098,-.017,.437),(.095,.012,.025),'Cabin olive',.004,TRIM)
 ct('Visor hinge '+str(sign),[(sign*.144,-.020,.445),(sign*.051,-.020,.445)],.0015,'Steel',TRIM)
 ct('Grab handle '+str(sign),[(sign*.168,.055,.428),(sign*.158,.06,.423),(sign*.158,.095,.423),(sign*.168,.100,.428)],.0025,'Cabin charcoal',TRIM)
 for y in [.055,.100]:cb('Grab handle mount '+str(sign)+' '+str(y),(sign*.167,y,.438),(.012,.013,.020),'Cabin charcoal',.002,TRIM)
 for x in [sign*.052,sign*.142]:cb('Visor roof mount',(x,-.02,.448),(.012,.013,.011),'Cabin charcoal',.002,TRIM)
cb('Dome light housing',(0,.06,.450),(.028,.040,.015),'Cabin charcoal',.003,TRIM)
cb('Dome light lens',(0,.06,.4415),(.020,.026,.003),'Cabin marking',.002,TRIM)
ct('Rearview mirror stem',[(0,-.018,.448),(0,-.042,.416)],.0017,'Cabin charcoal',TRIM)
cb('Rearview mirror shell',(0,-.042,.414),(.060,.010,.022),'Cabin charcoal',.003,TRIM)
cb('Rearview mirror face',(0,-.0365,.414),(.051,.001,.015),'Steel',.002,TRIM)

# Bake only new components, preserving every exterior mesh exactly. New pieces
# have UVs and named materials, but no texture atlas or runtime mechanisms.
for o in owned:
 if any(o.name.startswith('CAB | '+k) for k in ['Steering','Column stalk','Stalk grip','Ignition']):o.location.z-=.012*S
for o in owned:
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.validate()
 o['component_group']='Interior';o['panda_cabin']=True
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
unexpected=[n for n,h in before.items() if bpy.data.objects.get(n) is None or fingerprint(bpy.data.objects[n])!=h];assert not unexpected,unexpected
report={'source':str(SRC/'Panda_Assembly.blend'),'source_sha256':hashlib.sha256((SRC/'Panda_Assembly.blend').read_bytes()).hexdigest(),'replaced_basic_interior':removed,'new_cabin_meshes':len(owned),'preserved_meshes_and_transforms':len(before),'unexpected_changes':unexpected,'driver_eye_raw':[.096,.055,.411],'style':'Rounded utilitarian Panda cockpit with fabric dash sling and striped olive/canvas seats','reference':'https://www.carandclassic.com/car/C1950673','limits':['Static interior controls and parked belts.','No animation, ergonomics certification, texture atlas or Unreal integration.']}
(OUT/'interior-manifest.json').write_text(json.dumps(report,indent=2));shutil.copy2(SRC/'vehicle-spec.json',OUT/'vehicle-spec.json')
bpy.ops.object.select_all(action='DESELECT')
for o in sc.objects:
 if o.type in ['MESH','EMPTY'] and not o.name.startswith('SOURCE'):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Panda_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Panda_Assembly.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda_Assembly.blend'));print('INTERIOR_BUILT',json.dumps(report),flush=True)
