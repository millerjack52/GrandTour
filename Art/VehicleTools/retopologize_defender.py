"""Measured, panel-by-panel retopology. Original separated mesh stays hidden.
Authoring topology is quad strips/grids/rings, with flat caps where appropriate.
"""
import bpy,bmesh,math,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
SOURCE=ROOT/'defender-separated-v07/Defender_Separated.blend'
OUT=ROOT/'defender-retopology-v01';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));S=4.6
sourcehash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
root=bpy.data.objects['DEFENDER | assembly'];active=[];cols={}
for n in ['Panels','Cabin frames','Glazing','Front module','Rear module','Hardware','Underbody']:
 c=bpy.data.collections.new('RET | '+n);bpy.context.scene.collection.children.link(c);cols[n]=c
ref=bpy.data.collections.new('REFERENCE | Previous separated assembly');bpy.context.scene.collection.children.link(ref)
for o in list(bpy.data.objects):
 if o.type!='MESH' or o.name.startswith('SOURCE'):continue
 if o.name.startswith('Rebuilt'):
  active.append(o);bm=bmesh.new();bm.from_mesh(o.data)
  bmesh.ops.join_triangles(bm,faces=list(bm.faces),angle_face_threshold=.01,angle_shape_threshold=.8,cmp_seam=True,cmp_sharp=True)
  bm.to_mesh(o.data);bm.free();o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
  for f in o.data.polygons:f.use_smooth=True
  o.data.set_sharp_from_angle(angle=1.15 if 'tyre' in o.name else .48)
 else:
  for c in list(o.users_collection):c.objects.unlink(o)
  ref.objects.link(o);o.hide_render=True;o.hide_set(True)
ref.hide_render=True;ref.hide_viewport=True
M={k:bpy.data.materials['Review | '+k] for k in ['Body','Panel','Glass','Rubber','Metal','Light','Inner']}
def interp(x,knots):
 if x<=knots[0][0]:return knots[0][1]
 for (a,b),(c,d) in zip(knots,knots[1:]):
  if x<=c:return b+(d-b)*(x-a)/(c-a)
 return knots[-1][1]
def side_x(z):return interp(z,[(.13,.209),(.147,.2146),(.263,.2146),(.274,.209),(.295,.207),(.307,.205),(.32,.201),(.44,.193)])
def rear_y(z):return interp(z,[(.145,.411),(.162,.436),(.18,.4417),(.30,.4417),(.44,.429)])
def make(name,verts,faces,group='Panels',mat='Body',thick=0,bevel=0,parent=None,smooth=False):
 me=bpy.data.meshes.new('RET '+name);me.from_pydata([tuple(v*S for v in p) for p in verts],[],faces);me.update()
 ob=bpy.data.objects.new('RET | '+name,me);cols[group].objects.link(ob);me.materials.append(M[mat]);active.append(ob)
 # Consistent orientation within each clean connected sheet.
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 for f in me.polygons:f.use_smooth=smooth
 if thick:
  mod=ob.modifiers.new('Panel thickness','SOLIDIFY');mod.thickness=thick;mod.offset=-1;mod.use_even_offset=False
 if bevel:
  mod=ob.modifiers.new('Controlled edge radius','BEVEL');mod.width=bevel;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=.45
  mod=ob.modifiers.new('Planar face normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
 bpy.context.view_layer.update();world=ob.matrix_world.copy();ob.parent=parent or root;ob.matrix_world=world
 ob['construction']='Measured retopology; regular panels and opening loops'
 return ob
def grid(name,rows,**kw):
 n=len(rows[0]);v=[p for row in rows for p in row];fs=[]
 for j in range(len(rows)-1):
  for i in range(n-1):a=j*n+i;fs.append((a,a+1,a+1+n,a+n))
 return make(name,v,fs,**kw)
def chamfer(poly,r=.003):
 pts=[]
 for i,p in enumerate(poly):
  p=Vector(p);a=Vector(poly[i-1]);b=Vector(poly[(i+1)%len(poly)]);d=min(r,(a-p).length*.25,(b-p).length*.25)
  pts.extend([p+(a-p).normalized()*d,p+(b-p).normalized()*d])
 return pts
def frame(name,outer,inner,mapper,group='Cabin frames',parent=None):
 a=chamfer(outer);b=chamfer(inner);n=len(a)
 rows=[]
 for t in [0,.10,.90,1]:rows.append([mapper(*(p.lerp(q,t))) for p,q in zip(a,b)])
 vs=[p for row in rows for p in row];fs=[]
 for j in range(3):
  for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 ob=make(name,vs,fs,group=group,thick=.012,bevel=.002,parent=parent)
 pane=[mapper(*p) for p in b]
 # Flat glazing caps have no triangle fans in the editable mesh.
 make(name+' pane',pane,[tuple(range(n))],group='Glazing',mat='Glass',thick=.003,parent=parent)
 return ob
def box(name,centre,dimensions,group='Hardware',mat='Metal',bevel=.006,parent=None):
 x,y,z=centre;dx,dy,dz=[v/2 for v in dimensions]
 vs=[(x+sx*dx,y+sy*dy,z+sz*dz) for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 return make(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],group,mat,bevel=bevel,parent=parent)
def tube(name,a,b,r,group='Hardware',mat='Metal',parent=None,n=12):
 a=Vector(a);b=Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.01:u=axis.cross(Vector((0,1,0)))
 u.normalize();v=axis.cross(u);verts=[]
 for c in [a,b]:
  for i in range(n):verts.append(c+r*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)))
 fs=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]+[tuple(reversed(range(n))),tuple(range(n,2*n))]
 return make(name,verts,fs,group,mat,parent=parent,smooth=True)
def ring_lamp(name,c,r,axis='Y',parent=None):
 # Five concentric rings give a real bezel, recess and lens seat.
 x,y,z=c;n=24;profile=[(r*1.13,0),(r*1.13,-.002),(r,-.003),(r*.88,-.002),(r*.88,.0005)]
 vs=[]
 for rad,depth in profile:
  for i in range(n):
   t=i*math.tau/n;vs.append((x+rad*math.cos(t),y+depth,z+rad*math.sin(t)))
 fs=[]
 for j in range(len(profile)-1):
  for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 make(name+' bezel',vs,fs,'Front module','Metal',thick=.003,parent=parent,smooth=True)
 points=[(x+r*.88*math.cos(i*math.tau/n),y+.0003,z+r*.88*math.sin(i*math.tau/n)) for i in range(n)]
 make(name+' lens',points,[tuple(range(n))],'Front module','Light',thick=.004,parent=parent)

# MAIN SIDE PANELS. Shared height stations carry the shoulder around the body.
for side,sign in [('L',1),('R',-1)]:
 for row,ys in [('Front',[-.195,-.193,-.15,-.10,-.05,.005,.007]),('Rear',[.026,.028,.07,.108,.14,.178,.180])]:
  par=bpy.data.objects['Hinge | '+side+' '+row+' door'];rows=[]
  for band in range(8):
   pts=[]
   for y in ys:
    bottom=.149 if row=='Front' or y<=.108 else .149+(y-.108)/.072*.085
    z=[bottom,bottom+.002,(bottom+.262)/2,.262,.272,.294,.304,.307][band]
    pts.append((sign*side_x(z),y,z))
   rows.append(pts)
  grid(side+' '+row+' door skin',rows,mat='Panel',thick=.018,bevel=.002,parent=par)
  outer=[(-.195,.309),(-.135,.440),(.007,.440),(.007,.309)] if row=='Front' else [(.026,.309),(.026,.440),(.180,.440),(.180,.309)]
  inner=[(-.177,.326),(-.130,.420),(-.011,.420),(-.011,.326)] if row=='Front' else [(.039,.326),(.039,.420),(.167,.420),(.167,.326)]
  frame(side+' '+row+' door window frame',outer,inner,lambda y,z:(sign*side_x(z),y,z),parent=par)
  for z in [.170,.293]:
   y=-.186 if row=='Front' else .029
   box(side+' '+row+' hinge leaf',(sign*(side_x(z)+.004),y,z),(.008,.028,.016),parent=par,bevel=.002)
   tube(side+' '+row+' hinge pin '+str(z),(sign*(side_x(z)+.009),y-.005,z-.010),(sign*(side_x(z)+.009),y-.005,z+.010),.0025,parent=par)
  hy=-.022 if row=='Front' else .15
  box(side+' '+row+' handle recess',(sign*.215,hy,.244),(.002,.043,.014),mat='Inner',parent=par,bevel=.004)
  box(side+' '+row+' handle',(sign*.220,hy,.246),(.008,.032,.006),parent=par,bevel=.003)
  if row=='Front':
   tube(side+' mirror arm',(sign*.211,-.181,.292),(sign*.237,-.169,.319),.003,parent=par)
   box(side+' mirror housing',(sign*.237,-.165,.335),(.030,.014,.051),mat='Inner',parent=par,bevel=.012)
   box(side+' mirror face',(sign*.237,-.1568,.335),(.025,.002,.044),mat='Glass',parent=par,bevel=.007)
 # Structural pillars stay on the fixed body, including the continuous lower B post.
 grid(side+' B post lower', [[(sign*(side_x(z)-.001),y,z) for y in [.007,.026]] for z in [.145,.262,.272,.294,.307]],group='Cabin frames',thick=.020,bevel=.002)
 for label,y0,y1 in [('B',.008,.025),('C',.181,.199),('D',.422,.438)]:
  grid(side+' '+label+' pillar',[[(sign*side_x(z),y,z) for y in [y0,y1]] for z in [.307,.32,.43,.441]],group='Cabin frames',thick=.025,bevel=.003)
 frame(side+' cargo window frame',[(.200,.308),(.200,.440),(.421,.440),(.421,.308)],[(.213,.333),(.213,.418),(.406,.418),(.406,.333)],lambda y,z:(sign*side_x(z),y,z))
 # Front wing and arch: regular strips connect the arch edge to the top rail.
 archF=[(-.473,.155),(-.442,.220),(-.402,.247),(-.297,.247),(-.257,.219),(-.237,.140)]
 ys=[-.474,-.473,-.46,-.442,-.42,-.402,-.35,-.297,-.277,-.257,-.237,-.215,-.198]
 rows=[]
 for t in [0,.05,.45,.92,1]:
  rows.append([(sign*.2146,y,interp(y,archF)*(1-t)+.280*t) for y in ys])
 grid(side+' front wing outer',rows,thick=.012,bevel=.002)
 # Inner arch contours and body mounting edges define a connected flare ribbon.
 innerF=[(-.465,.152),(-.429,.207),(-.400,.228),(-.300,.228),(-.274,.207),(-.250,.143)]
 outerR=[(.172,.146),(.198,.226),(.225,.246),(.321,.246),(.355,.220),(.378,.144)]
 innerR=[(.184,.145),(.214,.207),(.238,.226),(.311,.226),(.338,.207),(.357,.145)]
 for label,outer,inner in [('Front',archF,innerF),('Rear',outerR,innerR)]:
  rr=[]
  for t,xx in [(0,.2146),(.12,.228),(.82,.233),(1,.231)]:
   rr.append([(sign*xx,a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t) for a,b in zip(outer,inner)])
  grid(side+' '+label+' arch flare',rr,mat='Inner',thick=.008,bevel=.0015)
  # Open wheelhouse throat continues inward from the visible arch lip.
  grid(side+' '+label+' arch return',[[(sign*x,y,z) for y,z in inner] for x in [.231,.218,.16]],group='Underbody',mat='Inner',thick=.006)
 ys=[.183,.198,.225,.27,.321,.355,.378,.410,.438]
 rows=[]
 for band in range(7):
  points=[]
  for y in ys:
   bottom=interp(y,outerR)
   z=[bottom,bottom+.001,(bottom+.262)/2,.262,.272,.294,.307][band]
   points.append((sign*side_x(z),y,z))
  rows.append(points)
 grid(side+' rear quarter',rows,thick=.012,bevel=.002)
 # Fixed triangular return between the rear door taper and arch start.
 make(side+' rear door arch junction',[(sign*side_x(z),y,z) for y,z in [(.110,.149),(.172,.146),(.198,.226),(.181,.235)]],[(0,1,2,3)],thick=.012,bevel=.002)
 box(side+' sill',(sign*.204,-.005,.137),(.022,.408,.018),'Underbody','Body',.007)
 # Wing top deck has an inner upstand beneath the bonnet skirt.
 grid(side+' front wing top',[[(sign*x,y,z) for x,z in [(.105,.280),(.17,.282),(.210,.282),(.2146,.280)]] for y in [-.466,-.453,-.4,-.3,-.205]],thick=.010,bevel=.002)
 box(side+' front side marker',(sign*.217,-.402,.256),(.004,.017,.009),mat='Light',bevel=.003)

# BONNET: measured shoulder, raised central pressing and a closed peripheral skirt.
par=bpy.data.objects['Hinge | Bonnet'];ys=[-.466,-.461,-.453,-.41,-.36,-.31,-.255,-.215,-.204]
hood=[]
for y in ys:
 w=interp(y,[(-.466,.108),(-.453,.120),(-.41,.133),(-.31,.158),(-.204,.180)])
 centre=interp(y,[(-.466,.284),(-.461,.295),(-.453,.299),(-.41,.302),(-.36,.314),(-.31,.320),(-.255,.311),(-.204,.310)])
 edge=interp(y,[(-.466,.280),(-.453,.292),(-.204,.299)])
 hood.append([(u*w,y,edge+(centre-edge)*interp(abs(u),[(0,1),(.58,1),(.78,.88),(.94,.3),(1,0)])) for u in [-1,-.94,-.78,-.58,0,.58,.78,.94,1]])
grid('Bonnet controlled pressing',hood,mat='Panel',thick=.012,parent=par,smooth=True)
per=hood[0]+[row[-1] for row in hood[1:]]+list(reversed(hood[-1][:-1]))+[row[0] for row in reversed(hood[1:-1])]
grid('Bonnet peripheral skirt',[per+per[:1],[(x,y,min(z-.002,.281)) for x,y,z in per+per[:1]]],mat='Panel',thick=.010,parent=par)

# ROOF: low-order crowned grid with controlled edge rollover and a separate gutter.
par=bpy.data.objects['Mount | Roof cap'];roof=[]
ys=[-.145,-.14,-.13,-.10,-.06,0,.10,.22,.34,.40,.415,.425,.435]
for y in ys:
 z=interp(y,[(-.145,.444),(-.14,.446),(-.13,.455),(-.1,.466),(0,.482),(.12,.486),(.4,.486),(.415,.480),(.425,.462),(.435,.444)])
 roof.append([(u*.200,y,.442+(z-.442)*interp(abs(u),[(0,1),(.5,.93),(.8,.8),(.9,.62),(.97,.28),(1,0)])) for u in [-1,-.97,-.9,-.8,-.5,0,.5,.8,.9,.97,1]])
grid('Roof crowned quad surface',roof,thick=.009,parent=par,smooth=True)
for sign in [-1,1]:
 box(('L' if sign>0 else 'R')+' roof gutter',(sign*.202,.145,.442),(.009,.593,.005),'Cabin frames','Body',.006,parent=par)
 # Glazing follows the same roof surface function, with only a 0.7 mm seat offset.
 alpine=[]
 for y in [.188,.194,.35,.357]:
  alpine.append([(sign*u*.200,y,.442+(.486-.442)*interp(u,[(0,1),(.5,.93),(.8,.8),(.9,.62),(.97,.28),(1,0)])+.00015) for u in [.82,.9,.955]])
 grid(('L' if sign>0 else 'R')+' alpine pane',alpine,group='Glazing',mat='Glass',thick=.002,parent=par,smooth=True)

# WINDSCREEN and cowl, laid out in planar rings with no diagonal shading patches.
def windshield(x,z):return (x,interp(z,[(.31,-.202),(.443,-.14)]),z)
for side,sign in [('L',1),('R',-1)]:
 xa,xb=(.005,.198) if sign>0 else (-.198,-.005)
 outer=[(xa,.313),(xa,.44),(xb*.945,.44),(xb,.313)] if sign>0 else [(xa,.313),(xa*.945,.44),(xb,.44),(xb,.313)]
 ia,ib=(.011,.177) if sign>0 else (-.177,-.011)
 frame(side+' windscreen frame',outer,[(ia,.333),(ia*.97,.427),(ib*.97,.427),(ib,.333)],windshield)
 tube(side+' wiper arm',(sign*.10,-.208,.313),(sign*.055,-.196,.338),.0018)
 tube(side+' wiper blade',(sign*.012,-.191,.34),(sign*.15,-.191,.34),.0018)
grid('Cowl quad rail',[[(x,y,z) for x in [-.208,-.18,-.10,0,.10,.18,.208]] for y,z in [(-.205,.283),(-.205,.305),(-.200,.313)]],thick=.012,bevel=.002)
grid('Windscreen centre mullion',[[windshield(x,z) for x in [-.005,.005]] for z in [.312,.333,.427,.441]],group='Cabin frames',thick=.018,bevel=.002)
for sign in [-1,1]:
 grid(('L' if sign>0 else 'R')+' windscreen corner return',[[windshield(sign*x,z),(sign*side_x(z),y,z)] for x,y,z in [(.198,-.195,.313),(.191,-.155,.4),(.187,-.135,.44)]],group='Cabin frames',thick=.014,bevel=.002)

# FRONT MODULE. Ring topology follows the headlamp apertures.
for side,sign in [('L',1),('R',-1)]:
 cx=sign*.148;cz=.226;r=.018;outer=[];inner=[]
 xmin,xmax=sorted([sign*.112,sign*.201]);zmin,zmax=.171,.266
 angles=sorted([i*math.tau/24 for i in range(24)]+[math.atan2(z-cz,x-cx)%math.tau for x,z in [(xmin,zmin),(xmax,zmin),(xmax,zmax),(xmin,zmax)]])
 n=len(angles)
 for t in angles:
  dx,dz=math.cos(t),math.sin(t)
  tx=(xmax-cx)/dx if dx>1e-8 else (xmin-cx)/dx if dx<-1e-8 else 1e5
  tz=(zmax-cz)/dz if dz>1e-8 else (zmin-cz)/dz if dz<-1e-8 else 1e5
  length=min(tx,tz);outer.append((cx+dx*length,-.472,cz+dz*length));inner.append((cx+dx*r,-.473,cz+dz*r))
 vs=outer+inner;fs=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 make(side+' headlamp aperture panel',vs,fs,'Front module',thick=.012,bevel=.001)
 ring_lamp(side+' main headlamp',(cx,-.475,cz),.0165)
 for z in [.204,.245]:ring_lamp(side+' marker '+str(z),(sign*.182,-.475,z),.008)
 box(side+' nose outer return',(sign*.207,-.466,.215),(.020,.013,.118),'Front module','Body',.012)
box('Front grille recess',(0,-.469,.219),(.208,.014,.098),'Front module','Inner',.010)
for i in range(7):box('Grille horizontal slat '+str(i),(0,-.478,.183+i*.0108),(.194,.005,.0035),'Front module','Metal',.002)
for x in [-.108,.108]:box('Grille side surround '+str(x),(x,-.477,.220),(.007,.010,.103),'Front module','Body',.003)
for z in [.168,.272]:box('Grille horizontal surround '+str(z),(0,-.477,z),(.222,.010,.007),'Front module','Body',.003)
box('Front bumper',(0,-.481,.14),(.426,.036,.034),'Front module','Inner',.018)
grid('Front fascia upper closure',[[(x,-.471,z) for x in [-.207,-.112,0,.112,.207]] for z in [.266,.280]],group='Front module',thick=.012,bevel=.002)
grid('Front fascia lower closure',[[(x,-.471,z) for x in [-.207,-.112,0,.112,.207]] for z in [.155,.172]],group='Front module',thick=.012,bevel=.002)

# REAR DOOR / fixed quarter returns follow the measured rear-face taper.
par=bpy.data.objects['Hinge | Rear door']
grid('Rear door lower pressing',[[(x,rear_y(z),z) for x in [-.121,-.118,-.07,0,.07,.118,.121]] for z in [.162,.165,.18,.25,.304,.309]],group='Rear module',mat='Panel',thick=.018,bevel=.002,parent=par)
frame('Rear door window frame',[(-.121,.310),(-.121,.438),(.121,.438),(.121,.310)],[(-.105,.332),(-.105,.415),(.105,.415),(.105,.332)],lambda x,z:(x,rear_y(z),z),group='Rear module',parent=par)
for sign in [-1,1]:
 grid(('L' if sign>0 else 'R')+' rear fixed face',[[(sign*x,rear_y(z),z) for x in [.124,.155,.185,.207]] for z in [.155,.165,.18,.25,.30]],group='Rear module',thick=.012,bevel=.003)
 grid(('L' if sign>0 else 'R')+' rear upper corner',[[(sign*x,rear_y(z),z) for x in [.124,.16,.193]] for z in [.302,.33,.40,.44]],group='Rear module',thick=.010,bevel=.003)
 grid(('L' if sign>0 else 'R')+' rear corner return',[[(sign*.193,rear_y(z),z),(sign*side_x(z),.438,z)] for z in [.302,.33,.40,.44]],group='Rear module',thick=.010)
 grid(('L' if sign>0 else 'R')+' rear lower corner return',[[(sign*.207,rear_y(z),z),(sign*side_x(z),.438,z)] for z in [.155,.18,.25,.262,.272,.30]],group='Rear module',thick=.010)
 for z in [.188,.253]:
  tube(('L' if sign>0 else 'R')+' rear lamp '+str(z),(sign*.172,.442,z),(sign*.172,.451,z),.012,'Rear module','Light',n=24)
for z in [.194,.285,.41]:
 box('Rear door hinge '+str(z),(-.134,.446,z),(.028,.008,.015),'Rear module','Metal',.003,parent=par)
box('Rear door handle',(.102,.448,.264),(.032,.009,.009),'Rear module','Metal',.003,parent=par)
box('Rear bumper',(0,.454,.14),(.426,.036,.034),'Rear module','Inner',.018)
box('Spare wheel mount',(0,.453,.266),(.068,.035,.06),'Rear module','Inner',.007,parent=par)

# CLEAN UNDERSIDE. The floor reaches the sills and trims around the rear tubs.
outline=[(-.207,-.20),(.207,-.20),(.207,.166),(.151,.20),(.151,.353),(.207,.385),(.207,.432),(-.207,.432),(-.207,.385),(-.151,.353),(-.151,.20),(-.207,.166)]
make('Full width inner floor',[(x,y,.149) for x,y in outline],[tuple(range(len(outline)))],'Underbody','Inner',thick=.028)
for sign in [-1,1]:
 box('Chassis rail '+str(sign),(sign*.111,.015,.119),(.018,.91,.024),'Underbody','Inner',.007)
 for y in [-.345,.266]:tube('Axle '+str(sign)+' '+str(y),(sign*.025,y,.096),(sign*.199,y,.096),.008,'Underbody','Inner')
 for cy in [-.345,.266]:
  rows=[]
  for x in [.158,.20,.22]:rows.append([(sign*x,cy+.108*math.cos(t*math.pi/16),.10+.108*math.sin(t*math.pi/16)) for t in range(17)])
  grid('Wheelhouse roof '+str(sign)+' '+str(cy),rows,group='Underbody',mat='Inner',thick=.008)
  make('Wheelhouse inner wall '+str(sign)+' '+str(cy),rows[0],[tuple(range(17))],'Underbody','Inner',thick=.008)
for y in [-.345,.266]:box('Differential '+str(y),(0,y,.098),(.058,.046,.048),'Underbody','Inner',.025)
box('Transmission enclosure',(0,-.14,.116),(.080,.33,.045),'Underbody','Inner',.015)

# Clear viewport clutter and keep the previous assembly as a hidden comparison.
for c in bpy.data.collections:
 if c.name.startswith('99 Original'):c.hide_render=True;c.hide_viewport=True
for o in bpy.data.objects:
 if o.type in {'EMPTY','LIGHT','CAMERA'}:o.hide_set(True)
sc=bpy.context.scene;sc.cycles.samples=32
cam=sc.camera;cam.hide_set(False)
def render(name,pos,scale=6.7,target=(0,0,1.1)):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('quarter',(7,-9,4.7));render('side',(9,0,1.15),6.4);render('front',(0,-9,1.15),4.2);render('rear',(0,9,1.15),4.2)
render('top',(0,0,10),6.4,target=(0,0,0));render('underside',(5,-7,-4),6.7)
smooth={o:[p.use_smooth for p in o.data.polygons] for o in active}
for o in active:
 for p in o.data.polygons:p.use_smooth=False
render('flat-quarter',(7,-9,4.7))
for o,flags in smooth.items():
 for p,f in zip(o.data.polygons,flags):p.use_smooth=f
wire=bpy.data.materials.new('QA wire');wire.diffuse_color=(.012,.025,.03,1);wire.use_nodes=True;wire.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=wire.diffuse_color
copies=[]
for o in active:
 if not o.name.startswith('RET'):continue
 dup=bpy.data.objects.new('WIRE '+o.name,o.data.copy());sc.collection.objects.link(dup);dup.matrix_world=o.matrix_world.copy()
 dup.data.materials.clear();dup.data.materials.append(wire)
 mod=dup.modifiers.new('Authoring edges','WIREFRAME');mod.thickness=.003;mod.use_replace=True;mod.offset=1
 copies.append(dup)
render('wire-quarter',(7,-9,4.7));render('wire-side',(9,0,1.15),6.4)
for o in copies:bpy.data.objects.remove(o,do_unlink=True)
report={'source':str(SOURCE),'source_sha256':sourcehash,'scope':'Measured exterior retopology; neutral review materials only','objects':[],'limitations':['UVs, textures, LODs, gameplay rig, collision and Unreal validation remain outside this geometry pass.','Interior currently contains a closed floor and wheelhouses, without cockpit fittings.','Refined surfaces intentionally replace reconstruction noise; not an exact vertex match to Tripo.']}
for o in active:
 counts={str(n):sum(len(p.vertices)==n for p in o.data.polygons) for n in [3,4]}
 counts['ngons']=sum(len(p.vertices)>4 for p in o.data.polygons)
 report['objects'].append({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'topology':counts})
report['authoring_faces']=sum(r['faces'] for r in report['objects']);report['quads']=sum(r['topology']['4'] for r in report['objects']);report['triangles']=sum(r['topology']['3'] for r in report['objects'])
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sourcehash
(OUT/'retopology-report.json').write_text(json.dumps(report,indent=2))
for o in bpy.context.selected_objects:o.select_set(False)
for o in active:o.hide_set(False);o.select_set(True)
for o in bpy.data.objects:
 if o.type=='EMPTY':o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=active[0]
bpy.ops.export_scene.gltf(filepath=str(OUT/'Defender_Retopology.glb'),use_selection=True,export_format='GLB',export_apply=True,export_animations=False,export_extras=True)
for o in bpy.data.objects:
 if o.type in {'EMPTY','LIGHT','CAMERA'}:o.hide_set(True)
for o in bpy.context.selected_objects:o.select_set(False)
render('final-quarter',(7,-9,4.7))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Defender_Retopology.blend'))
print('RETOPOLOGY_SAVED',report['authoring_faces'],report['quads'],report['triangles'])
