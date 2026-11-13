"""Panda-specific, measured reconstruction. Never overwrites the Tripo source.
Raw landmark coordinates are uniformly scaled; exterior interfaces share functions.
"""
import bpy,bmesh,math,json,hashlib,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
S=3.6
SRC=Path('C:/Users/mille/Downloads/pandatripo.glb')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/panda-assembly-v02');OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'Panda_Assembly.blend').exists():raise RuntimeError('Saved Panda revision exists. Choose a new output revision; do not overwrite possible manual edits.')
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.unit_settings.system='METRIC'
cols={}
for n in ['Body','Doors','Bonnet','Tailgate','Glazing','Wheels','Front equipment','Roof and snorkel','Interior','Underbody','Controls','Studio','Source reference']:
 c=bpy.data.collections.new(n);sc.collection.children.link(c);cols[n]=c
M={}
for n,c in {'Paint':(.24,.285,.17,1),'Cream':(.72,.67,.46,1),'Rubber':(.022,.027,.025,1),'Inner':(.035,.041,.039,1),'Steel':(.42,.43,.37,1),'Glass':(.115,.18,.20,1),'Lens':(.7,.74,.70,1),'Amber':(.85,.26,.012,1),'Red':(.48,.025,.015,1),'Seat':(.24,.21,.16,1),'Carpet':(.07,.075,.061,1)}.items():
 m=bpy.data.materials.new('Panda | '+n);m.diffuse_color=c;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=c;p.inputs['Roughness'].default_value=.45 if n in ['Paint','Steel'] else .68
 if n=='Steel':p.inputs['Metallic'].default_value=.65
 if n=='Glass':p.inputs['Roughness'].default_value=.14;p.inputs['Transmission Weight'].default_value=.7;p.inputs['IOR'].default_value=1.45
 M[n]=m
owned=[];roots={}
def parent_keep(o,p):
 w=o.matrix_world.copy();o.parent=p;o.matrix_parent_inverse=p.matrix_world.inverted();o.matrix_world=w
def empty(n,p=(0,0,0),parent=None):
 o=bpy.data.objects.new(n,None);cols['Controls'].objects.link(o);o.location=Vector(p)*S;o.empty_display_size=.1
 if parent:parent_keep(o,parent)
 bpy.context.view_layer.update();roots[n]=o;return o
root=empty('PANDA | assembly')
def make(n,v,f,group='Body',mat='Paint',thick=0,bevel=0,parent=None,smooth=False):
 me=bpy.data.meshes.new(n);me.from_pydata([tuple(Vector(p)*S) for p in v],[],f);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(n,me);cols[group].objects.link(o);me.materials.append(M[mat]);o.color=M[mat].diffuse_color;owned.append(o);parent_keep(o,parent or root)
 for p in me.polygons:p.use_smooth=smooth
 if thick:m=o.modifiers.new('Inward panel return','SOLIDIFY');m.thickness=thick*S;m.offset=-1;m.use_even_offset=True
 if bevel:m=o.modifiers.new('Controlled edge highlight','BEVEL');m.width=bevel*S;m.segments=2
 if smooth:me.set_sharp_from_angle(angle=.7)
 o['construction']='Panda measured interfaces v01';return o
def orient(o,n):
 bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update()
 if sum((f.normal*f.calc_area() for f in bm.faces),Vector()).dot(Vector(n))<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bm.to_mesh(o.data);bm.free();return o
def grid(n,rows,normal=None,**kw):
 v=[p for row in rows for p in row];k=len(rows[0]);f=[(j*k+i,j*k+i+1,(j+1)*k+i+1,(j+1)*k+i) for j in range(len(rows)-1) for i in range(k-1)];o=make(n,v,f,**kw)
 return orient(o,normal) if normal else o
def box(n,c,d,group='Body',mat='Paint',bevel=.001,parent=None):
 v=[(c[0]+x*d[0]/2,c[1]+y*d[1]/2,c[2]+z*d[2]/2) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 return make(n,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],group,mat,bevel=bevel,parent=parent)
def tube(n,points,r,group='Front equipment',mat='Rubber',parent=None,segments=10,closed=False):
 pp=[Vector(p) for p in points];v=[]
 for i,p in enumerate(pp):
  t=(pp[(i+1)%len(pp)]-pp[i-1]) if closed else (pp[min(i+1,len(pp)-1)]-pp[max(0,i-1)])
  t.normalize();a=t.cross(Vector((0,0,1)))
  if a.length<.01:a=t.cross(Vector((0,1,0)))
  a.normalize();b=t.cross(a)
  v += [p+r*(a*math.cos(j*2*math.pi/segments)+b*math.sin(j*2*math.pi/segments)) for j in range(segments)]
 f=[]
 for i in range(len(pp) if closed else len(pp)-1):
  for j in range(segments):f.append((i*segments+j,i*segments+(j+1)%segments,((i+1)%len(pp))*segments+(j+1)%segments,((i+1)%len(pp))*segments+j))
 if not closed:f += [tuple(reversed(range(segments))),tuple((len(pp)-1)*segments+j for j in range(segments))]
 return make(n,v,f,group,mat,parent=parent,smooth=True)
def cyl(n,a,b,r,**kw):return tube(n,[a,b],r,**kw)
def rotate_about(o,p,angle):
 pivot=Vector(p)*S;rot=Matrix.Rotation(angle,4,'X');o.data.transform(Matrix.Translation(pivot)@rot@Matrix.Translation(-pivot))
def interp(t,pts):
 if t<=pts[0][0]:return pts[0][1]
 for (a,b),(c,d) in zip(pts,pts[1:]):
  if t<=c:return b+(d-b)*(t-a)/(c-a)
 return pts[-1][1]
Z=[.135,.15,.19,.22,.27,.303,.322]
WIDTH=[(.135,.218),(.15,.223),(.19,.228),(.22,.23),(.27,.23),(.303,.221),(.322,.213),(.455,.179)]
TAIL=[(.135,.465),(.15,.477),(.19,.487),(.22,.488),(.27,.482),(.303,.478),(.322,.474),(.455,.394)]
def sx(z):return interp(z,WIDTH)
def tail(z):return interp(z,TAIL)
def hood(y):return interp(y,[(-.438,.286),(-.39,.295),(-.26,.313),(-.195,.322)])
ARCH={n:[(cy-.122,.135),(cy-.111,.174),(cy-.084,.207),(cy-.060,.216),(cy+.058,.216),(cy+.084,.203),(cy+.111,.168),(cy+.122,.135)] for n,cy in [('F',-.289),('R',.314)]}
def floor_edge(y):
 return .135
def aperture(y):
 return max([.135]+[interp(y,a) for a in ARCH.values() if a[0][0]<=y<=a[-1][0]])
def side_surface(n,a,b,sign,parent=None,top=None):
 ys=sorted(set([a,b]+[y for ar in ARCH.values() for y,z in ar if a<y<b]+[y for y in [-.438,-.39,-.26,-.195,-.184,.13,.2,.4,.474,.488] if a<y<b]))
 levels=sorted(set(Z+[z for ar in ARCH.values() for y,z in ar]));rows=[]
 for z0 in levels:
  row=[]
  for y in ys:
   z=max(aperture(y),min(z0,top(y) if top else .322));yy=min(y,tail(z));row.append((sign*sx(z),yy,z))
  rows.append(row)
 return grid(n,rows,(sign,0,0),group='Doors' if parent else 'Body',thick=.0025,parent=parent)
def ring(n,outer,inner,group='Glazing',mat='Paint',normal=None,thick=.002,parent=None):
 count=len(outer);o=make(n,outer+inner,[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)],group,mat,thick=thick,parent=parent)
 if normal:orient(o,normal)
 return o
def window(n,outer,inner,normal,parent=None,group='Glazing'):
 ring(n+' metal surround',outer,inner,group=group,normal=normal,thick=.003,parent=parent)
 nv=Vector(normal).normalized();center=sum((Vector(p) for p in inner),Vector())/len(inner)
 inside=[center+(Vector(p)-center)*.965-nv*.0008 for p in inner]
 ring(n+' gasket',[Vector(p)-nv*.0007 for p in inner],inside,mat='Rubber',normal=normal,thick=.002,parent=parent)
 ob=make(n+' glass',inside,[tuple(range(len(inside)))],group='Glazing',mat='Glass',thick=.001,parent=parent);orient(ob,normal)
 return ob
def sidep(sign,pts,inset=0):return [(sign*(sx(z)-inset),y,z) for y,z in pts]
def strip(n,poly,sign,width=.005,parent=None):
 # Backing directly under the boundary, following every vertex, never a chord across an arch.
 center=sum((Vector(p) for p in poly),Vector((0,0)))/len(poly)
 out=[Vector(p)+(Vector(p)-center).normalized()*width for p in poly];ins=[Vector(p)-(Vector(p)-center).normalized()*width for p in poly]
 oo=[];ii=[]
 for i in range(len(poly)):
  oa,ob=out[i],out[(i+1)%len(poly)];ia,ib=ins[i],ins[(i+1)%len(poly)];ts={0,.25,.5,.75}
  for a,b in [(oa,ob),(ia,ib)]:
   if abs(b.y-a.y)>1e-9:ts.update((z-a.y)/(b.y-a.y) for z,x in WIDTH if 0<(z-a.y)/(b.y-a.y)<1)
  for t in sorted(ts):
   for arr,a,b in [(oo,oa,ob),(ii,ia,ib)]:
    p=a.lerp(b,t);p.y=max(p.y,aperture(p.x)+.001);arr.append(p)
 return ring(n,sidep(sign,oo,.003),sidep(sign,ii,.003),group='Body',mat='Inner',normal=(sign,0,0),thick=.004,parent=parent)
doorpoly=[(-.184,aperture(-.184))]+[(y,z) for y,z in ARCH['F'] if y>-.184]+[(.13,.135),(.13,.455),(-.041,.455),(-.184,.322)]
for label,sign in [('L',1),('R',-1)]:
 dp=empty(label+' door hinge',(sign*sx(.30),-.184,.30),root)
 side_surface(label+' front wing',-.438,-.184,sign,top=hood)
 side_surface(label+' door skin',-.1828,.1288,sign,dp)
 side_surface(label+' rear quarter',.1312,.488,sign)
 strip(label+' full door reveal backing',doorpoly,sign)
 # Fixed sill, B pillar and rear quarter frames share the same upper-body cross-section.
 box(label+' sill',(sign*.2165,-.0185,.135),(.015,.297,.009),mat='Rubber',bevel=.002)
 winouter=[(-.1828,.322),(-.040,.455),(.1288,.455),(.1288,.322)]
 wininner=[(-.163,.335),(-.032,.444),(.115,.444),(.115,.335)]
 window(label+' door',sidep(sign,winouter),sidep(sign,wininner),(sign,0,0),dp,'Doors')
 rearout=[(.1312,.322),(.1312,.455),(.394,.455),(.474,.322)]
 rearin=[(.149,.335),(.149,.443),(.382,.443),(.450,.335)]
 window(label+' quarter',sidep(sign,rearout),sidep(sign,rearin),(sign,0,0))
 # Tiny shared B-pillar bridge below the intentional external door reveal.
 grid(label+' B pillar backing',[[ (sign*(sx(z)-.004),y,z) for y in [.125,.138]] for z in [.319,.335,.443,.455]],(sign,0,0),mat='Inner',thick=.004)
 for which,ar in ARCH.items():
  # Body at aperture edge -> projecting bead -> inward return -> full inner wheelhouse cap.
  lip=[(sign*(sx(z)+.0003),y,z) for y,z in ar]
  outer=[(sign*(sx(z)+.006),y,z+.003) for y,z in ar]
  inner=[(sign*.142,y,z+.003) for y,z in ar]
  grid(label+which+' arch bead',[lip,outer],(sign,0,0),thick=.002)
  grid(label+which+' wheelhouse roof',[outer,inner],(0,0,-1),group='Underbody',mat='Inner',thick=.002)
  cap=inner+[(sign*.142,ar[-1][0],.132),(sign*.142,ar[0][0],.132)]
  o=make(label+which+' inner wheelhouse wall',cap,[tuple(range(len(cap)))],group='Underbody',mat='Inner',thick=.002);orient(o,(sign,0,0))
  # Attached mudflaps only behind each wheel.
  y=ar[-1][0]-.002
  box(label+which+' mudflap hanger',(sign*.194,y,.14),(.091,.009,.009),'Underbody','Rubber',.001)
  box(label+which+' mudflap',(sign*.200,y+.003,.099),(.094,.0035,.085),'Underbody','Rubber',.001)
  for z in [.067,.073]:box(label+which+' flap marking '+str(z),(sign*.200,y+.005,.099-(.099-z)),(.077,.0006,.002),'Underbody','Cream',0)
 # Trim is partitioned at doors and arches rather than running across openings.
 for piece,(a,b,par) in enumerate([(-.43,-.184,None),(-.1828,.1288,dp),(.1312,.475,None)]):
  for z0,z1,mat in [(.236,.246,'Cream'),(.218,.234,'Rubber')]:
   ys=sorted(set([a,b]+[p[0] for ar in ARCH.values() for p in ar if a<p[0]<b]))
   for k,(ya,yb) in enumerate(zip(ys,ys[1:])):
    lowa=max(z0,aperture(ya)+.002);lowb=max(z0,aperture(yb)+.002)
    if lowa>=z1 and lowb>=z1:continue
    rows=[[(sign*(sx(z)+.001),y,z) for y,z in [(ya,min(lowa,z1)),(yb,min(lowb,z1))]],[(sign*(sx(z1)+.001),y,z1) for y in [ya,yb]]]
    grid(label+' moulding %s %s %s'%(piece,z0,k),rows,(sign,0,0),mat=mat,thick=.0007,parent=par)
 box(label+' handle recess',(sign*(sx(.299)+.001),.087,.299),(.002,.041,.013),'Doors','Inner',.003,dp)
 box(label+' handle',(sign*(sx(.299)+.0035),.087,.300),(.004,.031,.007),'Doors','Rubber',.002,dp)
 for a in [.323,.355]:
  rows=[]
  for z in [.275,.303,.315]:
   y=a+.049*(z-.275)/.040;rows.append(sidep(sign,[(y,z),(y+.016,z)],-.001))
  grid(label+' cream graphic '+str(a),rows,(sign,0,0),mat='Cream')
 cyl(label+' mirror arm',(sign*.209,-.153,.331),(sign*.251,-.137,.334),.004,group='Doors',parent=dp)
 box(label+' mirror shell',(sign*.254,-.129,.338),(.049,.026,.035),'Doors','Rubber',.005,dp)
 box(label+' mirror glass',(sign*.254,-.1149,.338),(.041,.0015,.027),'Glazing','Steel',.002,dp)
 box(label+' side repeater',(sign*(sx(.273)+.002),-.347,.273),(.004,.022,.009),'Body','Amber',.002)

print('Side modules complete',flush=True)
# Bonnet with matched side heights, subtle crown confined inside its perimeter.
bp=empty('Bonnet hinge',(0,-.196,.323),root)
ys=[-.438,-.435,-.39,-.32,-.26,-.197]
def hp(t,y):
 z=hood(y);crown=.005*math.sin(math.pi*(y+.438)/.243)*max(0,1-t*t)
 return (t*(sx(z)-.0012),y,z+crown)
grid('Bonnet pressing',[[hp(t,y) for t in [-1,-.94,-.60,0,.60,.94,1]] for y in ys],(0,0,1),group='Bonnet',thick=.003,parent=bp)
for sign in [-1,1]:
 grid('Bonnet side seating '+str(sign),[[(sign*(sx(hood(y))-d),y,hood(y)-.0033) for y in ys] for d in [.0005,.010]],(0,0,1),mat='Inner',thick=.002)
 for j in range(4):
  y=-.294+j*.013
  box('Bonnet vent %s %s'%(sign,j),(sign*.105,y,hood(y)+.004),(.047,.005,.003),'Bonnet','Rubber',.001,bp)
grid('Scuttle',[[(-sx(.322),y,.322),(sx(.322),y,.322)] for y in [-.199,-.184]],(0,0,1),thick=.003)
# Screen is bounded by side A pillars at the same endpoints.
def frontmap(x,z):return(x,interp(z,[(.322,-.184),(.455,-.041)]),z)
window('Windscreen',[frontmap(x,z) for x,z in [(-.213,.322),(.213,.322),(.179,.455),(-.179,.455)]],[frontmap(x,z) for x,z in [(-.197,.334),(.197,.334),(.166,.444),(-.166,.444)]],(0,-.68,.73))
# Shallow crowned roof with a matching perimeter, no broad overhanging slab.
grid('Roof cap',[[ (t*.179,y,.455+.016*(1-abs(t)**2)*math.sin(math.pi*(y+.041)/.435)) for t in [-1,-.96,-.72,0,.72,.96,1]] for y in [-.041,-.030,.04,.16,.29,.382,.394]],(0,0,1),thick=.003)
for sign in [-1,1]:tube('Roof gutter '+str(sign),[(sign*.181,y,.456) for y in [-.041,.04,.29,.394]],.002,group='Body',mat='Paint')
# Split geometry of tailgate and fixed lamp corners uses a single tail(z).
tp=empty('Tailgate upper hinge',(0,.397,.453),root)
tailz=Z+[.335,.443,.455]
for sign in [-1,1]:
 grid('Rear fixed corner '+str(sign),[[(sign*x,tail(z),z) for x in [.183,sx(z)]] for z in Z],(0,1,0),thick=.003)
grid('Tailgate lower pressing',[[(-.1818,tail(z),z),(.1818,tail(z),z)] for z in [.191,.22,.27,.303,.322]],(0,1,0),group='Tailgate',thick=.003,parent=tp)
window('Tailgate upper',[(-.1818,tail(.322),.322),(.1818,tail(.322),.322),(.179,tail(.455),.455),(-.179,tail(.455),.455)],[(-.166,tail(.335),.335),(.166,tail(.335),.335),(.163,tail(.443),.443),(-.163,tail(.443),.443)],(0,.85,.52),tp,'Tailgate')
for sign in [-1,1]:
 grid('Rear upper corner wrap '+str(sign),[[(sign*x,tail(z),z) for x in [lerpwidth,sx(z)]] for z,lerpwidth in [(z,interp(z,[(.322,.1818),(.455,.179)])) for z in [.322,.335,.443,.455]]],(0,1,.4),thick=.003)
for sign in [-1,1]:
 grid('Tailgate reveal backing '+str(sign),[[(sign*x,tail(z)-.003,z) for x in [.176,.188]] for z in Z[2:]+[.322,.335,.443,.455]],(0,1,0),mat='Inner',thick=.004)
box('Tailgate handle',(0,tail(.258)+.004,.258),(.042,.008,.018),'Tailgate','Rubber',.003,tp)
for sign in [-1,1]:
 for i,(za,zb,mat) in enumerate([(.215,.24,'Lens'),(.241,.26,'Red'),(.261,.280,'Amber'),(.281,.313,'Red')]):
  grid('Tail lamp %s %s'%(sign,i),[[(sign*x,tail(z)+.001,z) for x in [.187,.217]] for z in [za,zb]],(0,1,0),group='Body',mat=mat,thick=.003)
  for j in range(4):
   x=sign*(.192+j*.006)
   tube('Tail lens rib %s %s %s'%(sign,i,j),[(x,tail(za)+.002,za+.002),(x,tail(zb)+.002,zb-.002)],.0007,group='Body',mat=mat,segments=6)
# Nose: actual grille and headlight apertures backed by fitted inserts.
box('Nose upper header',(0,-.435,.282),(.444,.012,.007),bevel=.001)
box('Nose lower header',(0,-.438,.207),(.451,.014,.010),bevel=.001)
box('Radiator',(0,-.421,.244),(.255,.009,.062),mat='Inner',bevel=.002)
for j in range(5):box('Grille slat '+str(j),(0,-.438,.217+j*.012),(.254,.010,.0045),mat='Rubber',bevel=.001)
for sign in [-1,1]:
 box('Headlamp housing '+str(sign),(sign*.165,-.431,.247),(.075,.024,.061),mat='Inner',bevel=.003)
 box('Headlamp reflector '+str(sign),(sign*.165,-.444,.247),(.067,.006,.052),mat='Steel',bevel=.003)
 box('Headlamp lens '+str(sign),(sign*.165,-.448,.247),(.064,.002,.050),mat='Lens',bevel=.002)
 for j in range(9):box('Headlamp fluting %s %s'%(sign,j),(sign*.165+(j-4)*.006,-.4493,.247),(.001,.001,.044),mat='Lens',bevel=.0003)
 box('Front indicator '+str(sign),(sign*.212,-.44,.247),(.021,.018,.061),mat='Amber',bevel=.002)
 # Continuous front corner cheek between lamp band and wing boundary.
 grid('Nose corner wrap '+str(sign),[[(sign*sx(z),y,z) for y in [-.445,-.438]] for z in [.207,.247,.282]],(sign,0,0),thick=.003)
for n,y in [('Front',-.450),('Rear',.486)]:
 box(n+' bumper',(0,y,.181),(.487,.051,.048),mat='Rubber',bevel=.008)
 box(n+' lower valance',(0,y-.001 if n=='Front' else y+.001,.147),(.456,.043,.033),mat='Rubber',bevel=.004)
 for sign in [-1,1]:box(n+' bumper mount '+str(sign),(sign*.122,y+(.035 if n=='Front' else -.035),.169),(.021,.05,.024),'Underbody','Steel',.002)
 sg=-1 if n=='Front' else 1
 grid(n+' skid plate',[[(-.109,y+sg*.009,.13),(.109,y+sg*.009,.13)],[(-.098,y-sg*.045,.094),(.098,y-sg*.045,.094)]],(0,sg,-.5),group='Underbody',mat='Steel',thick=.003)
 for sign in [-1,1]:box(n+' skid bracket '+str(sign),(sign*.084,y-sg*.018,.127),(.009,.065,.035),'Underbody','Steel',.001)
for sign in [-1,1]:box('Amber foglight '+str(sign),(sign*.172,-.477,.181),(.048,.008,.021),'Front equipment','Amber',.003)
# Compact bull bar swept continuously and joined to bumper brackets.
tube('Bull bar hoop',[(-.12,-.485,.16),(-.12,-.489,.222),(-.108,-.489,.235),(.108,-.489,.235),(.12,-.489,.222),(.12,-.485,.16)],.008)
tube('Bull bar crossbar',[(-.119,-.486,.16),(.119,-.486,.16)],.007)
for sign in [-1,1]:
 tube('Bull bar mounting '+str(sign),[(sign*.107,-.48,.16),(sign*.107,-.428,.16)],.007)
def roundlamp(n,x,y,z,r,group):
 cyl(n+' shell',(x,y+.012,z),(x,y,z),r,group=group,mat='Rubber',segments=24)
 cyl(n+' bezel',(x,y-.001,z),(x,y-.003,z),r*.94,group=group,mat='Steel',segments=24)
 cyl(n+' lens',(x,y-.003,z),(x,y-.004,z),r*.83,group=group,mat='Lens',segments=24)
 for j in [-.5,0,.5]:
  off=r*j;l=math.sqrt((r*.80)**2-off*off)
  tube(n+' guard v'+str(j),[(x+off,y-.006,z-l),(x+off,y-.006,z+l)],.0008,group=group,segments=6)
  tube(n+' guard h'+str(j),[(x-l,y-.006,z+off),(x+l,y-.006,z+off)],.0008,group=group,segments=6)
 box(n+' mount',(x,y+.005,z-r-.004),(.012,.018,.016),group,'Rubber',.001)
for sign in [-1,1]:roundlamp('Bullbar lamp '+str(sign),sign*.061,-.493,.204,.023,'Front equipment')
for name,x,y,z in [('Front',-.122,-.483,.15),('Rear',.125,.515,.156)]:
 tube(name+' red recovery eye',[(x+math.cos(a*math.pi/8)*.008,y,z+math.sin(a*math.pi/8)*.011) for a in range(16)],.0025,mat='Red',closed=True)
 box(name+' recovery mount',(x,y-(.012 if name=='Rear' else -.012),z+.01),(.012,.03,.013),'Front equipment','Steel',.001)
# Empty roof rack: measured source envelope, real rails and feet.
for z in [.487,.516]:
 tube('Basket perimeter '+str(z),[(-.153,.029,z),(.153,.029,z),(.16,.036,z),(.16,.360,z),(.153,.367,z),(-.153,.367,z),(-.16,.360,z),(-.16,.036,z)],.004,'Roof and snorkel',closed=True)
for y in [.050,.14,.24,.345]:
 tube('Basket floor rail '+str(y),[(-.153,y,.485),(.153,y,.485)],.0028,'Roof and snorkel')
 for sign in [-1,1]:tube('Basket upright %s %s'%(sign,y),[(sign*.16,y,.487),(sign*.16,y,.516)],.0028,'Roof and snorkel')
for y in [.055,.335]:
 box('Roof crossbar '+str(y),(0,y,.478),(.332,.012,.009),'Roof and snorkel','Rubber',.002)
 for sign in [-1,1]:box('Rack foot %s %s'%(sign,y),(sign*.157,y,.466),(.022,.029,.021),'Roof and snorkel','Rubber',.003)
for sign in [-1,1]:roundlamp('Roof lamp '+str(sign),sign*.115,.018,.51,.023,'Roof and snorkel')
tube('Left snorkel',[(.226,-.207,.315),(.237,-.193,.320),(.235,-.169,.337),(.192,-.047,.452),(.191,-.031,.475)],.009,'Roof and snorkel')
box('Snorkel intake',(.191,-.034,.482),(.030,.032,.022),'Roof and snorkel','Rubber',.004)
box('Snorkel mouth',(.191,-.051,.482),(.023,.002,.014),'Roof and snorkel','Inner',.001)
for z,y in [(.351,-.151),(.438,-.062)]:tube('Snorkel bracket '+str(z),[(sx(z),y,z),(.23 if z<.4 else .20,y,z)],.004,'Roof and snorkel')
for sign in [-1,1]:
 tube('Front wiper '+str(sign),[(sign*.10,-.195,.327),(sign*.16,-.165,.345)],.002,'Body')
 tube('Front wiper blade '+str(sign),[(sign*.16,-.167,.345),(sign*.032,-.161,.347)],.002,'Body')
tube('Rear wiper',[(0,tail(.333)+.004,.333),(.095,tail(.37)+.004,.37)],.002,'Tailgate',parent=tp)

# Full passenger floor extends to sills and cuts around the same wheelhouse planes.
floor_ys=sorted(set([-.425,.468,-.184,.13]+[y for ar in ARCH.values() for y,z in ar]))
for i,(a,b) in enumerate(zip(floor_ys,floor_ys[1:])):
 mid=(a+b)/2;inarch=any(ar[0][0]<mid<ar[-1][0] for ar in ARCH.values());w=.142 if inarch else sx(.135)
 box('Fitted floor bay '+str(i),(0,(a+b)/2,.132),(w*2,b-a,.006),'Underbody','Inner',0)
box('Cabin carpet',(0,-.006,.139),(.409,.343,.007),'Interior','Carpet',.002)
box('Cargo carpet',(0,.369,.140),(.277,.187,.010),'Interior','Carpet',.002)
box('Firewall upper',(0,-.196,.260),(.415,.012,.097),'Underbody','Inner',.002)
box('Firewall lower',(0,-.196,.173),(.277,.012,.077),'Underbody','Inner',.002)
box('Rear inner panel',(0,.461,.229),(.350,.014,.177),'Interior','Carpet',.002)
for sign in [-1,1]:
 # Inner cards sit behind skins and leave both door reveal and floor closed.
 box('Door card '+str(sign),(sign*.205,-.022,.228),(.010,.288,.171),'Interior','Carpet',.004,roots[('L' if sign>0 else 'R')+' door hinge'])
 box('Door armrest '+str(sign),(sign*.193,.005,.265),(.025,.091,.020),'Interior','Rubber',.004)
 for y in [-.039,.073]:box('Seat foot %s %s'%(sign,y),(sign*.098,y,.166),(.097,.012,.047),'Interior','Steel',.002)
 box('Front seat cushion '+str(sign),(sign*.097,.015,.199),(.121,.159,.035),'Interior','Seat',.011)
 back=box('Front seat back '+str(sign),(sign*.097,.096,.270),(.121,.035,.151),'Interior','Seat',.010);rotate_about(back,(sign*.097,.096,.270),.12)
 for dx in [-.030,.030]:cyl('Headrest stem %s %s'%(sign,dx),(sign*.097+dx,.104,.33),(sign*.097+dx,.104,.365),.002,group='Interior',mat='Steel')
 box('Headrest '+str(sign),(sign*.097,.107,.364),(.082,.035,.049),'Interior','Seat',.008)
 box('Seatbelt buckle '+str(sign),(sign*.029,.050,.214),(.009,.011,.017),'Interior','Red',.002)
box('Rear bench cushion',(0,.234,.228),(.268,.139,.035),'Interior','Seat',.012)
box('Rear bench back',(0,.307,.294),(.265,.032,.123),'Interior','Seat',.01)
for x in [-.078,.078]:
 box('Rear bench headrest '+str(x),(x,.315,.365),(.078,.03,.05),'Interior','Seat',.007)
 for y in [.192,.27]:box('Rear bench support %s %s'%(x,y),(x,y,.181),(.016,.018,.085),'Interior','Steel',.002)
box('Panda dashboard shelf',(0,-.166,.302),(.397,.069,.034),'Interior','Carpet',.006)
box('Instrument pod',(.091,-.133,.324),(.115,.032,.042),'Interior','Rubber',.004)
for x in [.063,.110]:
 cyl('Gauge bezel '+str(x),(x,-.115,.326),(x,-.113,.326),.017,group='Interior',mat='Steel',segments=24)
 cyl('Gauge face '+str(x),(x,-.112,.326),(x,-.111,.326),.015,group='Interior',mat='Inner',segments=24)
 tube('Gauge needle '+str(x),[(x,-.110,.326),(x-.009,-.110,.334)],.0007,'Interior','Cream',segments=6)
cyl('Steering column',(.09,-.166,.284),(.09,-.084,.324),.005,group='Interior',mat='Rubber')
tube('Steering rim',[(.09+.035*math.cos(i*math.pi/16),-.079,.326+.035*math.sin(i*math.pi/16)) for i in range(32)],.0033,'Interior','Rubber',closed=True)
for ang in [0,2.1,4.2]:tube('Steering spoke '+str(ang),[(.09,-.079,.326),(.09+.032*math.cos(ang),-.079,.326+.032*math.sin(ang))],.003,'Interior','Rubber')
box('Centre tunnel',(0,-.008,.158),(.031,.30,.033),'Interior','Rubber',.005)
tube('Gear stick',[(0,-.052,.17),(0,-.038,.224)],.002,'Interior','Steel');box('Gear knob',(0,-.038,.228),(.010,.012,.014),'Interior','Rubber',.004)
for x in [.060,.088,.116]:box('Pedal '+str(x),(x,-.165,.174),(.015,.013,.025),'Interior','Rubber',.002)
box('Headliner',(0,.180,.450),(.343,.414,.004),'Interior','Carpet',.002)

print('Body and interior complete',flush=True)
# Four fitted wheels; closed revolved sections, real dished steel centres and vent holes.
def revolve(n,center,profile,mat,par,seg=48):
 v=[]
 for ax,r in profile:
  v += [(center[0]+ax,center[1]+r*math.cos(i*2*math.pi/seg),center[2]+r*math.sin(i*2*math.pi/seg)) for i in range(seg)]
 f=[(j*seg+i,j*seg+(i+1)%seg,((j+1)%len(profile))*seg+(i+1)%seg,((j+1)%len(profile))*seg+i) for j in range(len(profile)) for i in range(seg)]
 return make(n,v,f,'Wheels',mat,parent=par,smooth=True)
wheel_data=[]
for sign in [-1,1]:
 for code,y in [('F',-.289),('R',.314)]:
  name=('L' if sign>0 else 'R')+code;print('Building wheel '+name,flush=True);c=(sign*.207,y,.095);wp=empty(name+' wheel axle',c,root);wheel_data.append({'name':name,'center':c,'radius':.101,'width':.081})
  prof=[(-.028,.056),(-.037,.066),(-.041,.084),(-.035,.097),(-.028,.101),(.028,.101),(.035,.097),(.041,.084),(.037,.066),(.028,.056)]
  revolve(name+' tyre',c,prof,'Rubber',wp)
  revolve(name+' rim barrel',c,[(-.028,.055),(-.028,.060),(-.024,.062),(.024,.062),(.028,.060),(.028,.055)],'Steel',wp)
  # Dished web with boolean vents, placed inside sidewall envelope.
  web=revolve(name+' steel wheel web',c,[(sign*.017,.014),(sign*.020,.041),(sign*.026,.054),(sign*.023,.056),(sign*.017,.043),(sign*.013,.014)],'Steel',wp,48)
  for j in range(10):
   a=j*2*math.pi/10;yy=y+.043*math.cos(a);zz=.095+.043*math.sin(a)
   cutter=cyl('temporary vent',(c[0]-sign*.002,yy,zz),(c[0]+sign*.034,yy,zz),.0055,group='Wheels',mat='Inner',segments=12)
   mod=web.modifiers.new('Open steel vent','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.context.view_layer.objects.active=web
   bpy.ops.object.modifier_apply(modifier=mod.name);owned.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
  web.data.set_sharp_from_angle(angle=.55)
  nm=web.modifiers.new('Steel web normals','WEIGHTED_NORMAL');nm.keep_sharp=True;nm.weight=40
  cyl(name+' hub',(c[0]+sign*.006,y,.095),(c[0]+sign*.030,y,.095),.015,group='Wheels',mat='Rubber',parent=wp,segments=20)
  for j in range(4):
   a=j*math.pi/2+.78;yy=y+.022*math.cos(a);zz=.095+.022*math.sin(a)
   cyl(name+' lug '+str(j),(c[0]+sign*.021,yy,zz),(c[0]+sign*.029,yy,zz),.0032,group='Wheels',mat='Steel',parent=wp,segments=6)
  # Chunky shoulder tread, evenly spaced and contained within the original wheel envelope.
  for j in range(40):
   a=j*2*math.pi/40
   for ax in [-.025,0,.025]:
    tc=(c[0]+ax,y+.1005*math.cos(a),.095+.1005*math.sin(a));ob=box(name+' tread %s %s'%(j,ax),tc,(.021,.009,.004),'Wheels','Rubber',.0006,wp);rotate_about(ob,tc,a-math.pi/2)
  cyl(name+' axle stub',(sign*.131,y,.095),(c[0],y,.095),.008,group='Underbody',mat='Steel')
  cyl(name+' shock',(sign*.135,y,.095),(sign*.135,y+.02,.21),.008,group='Underbody',mat='Rubber')
for y in [-.289,.314]:
 cyl('Axle beam '+str(y),(-.13,y,.095),(.13,y,.095),.008,group='Underbody',mat='Steel')
 box('Axle centre '+str(y),(0,y,.095),(.048,.033,.03),'Underbody','Inner',.005)
for sign in [-1,1]:box('Longitudinal rail '+str(sign),(sign*.112,.008,.119),(.016,.845,.021),'Underbody','Inner',.003)
tube('Exhaust', [(-.074,-.24,.105),(-.084,.17,.105),(-.091,.35,.10),(-.092,.505,.106)],.006,'Underbody','Steel')

print('Applying modifiers',flush=True)
# Apply only this fresh revision's modifiers, clean tiny degenerates, generate usable UVs.
bpy.ops.object.select_all(action='DESELECT')
for o in owned:
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.validate();o.select_set(False)
 o['component_group']=o.users_collection[0].name
print('Unwrapping',flush=True)
for o in owned:o.select_set(True)
bpy.context.view_layer.objects.active=owned[0];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT');bpy.ops.object.select_all(action='DESELECT')
# Keep original, normalized source in a disabled collection for honest shape comparison.
bpy.ops.import_scene.gltf(filepath=str(SRC))
for o in list(bpy.context.selected_objects):
 for col in list(o.users_collection):col.objects.unlink(o)
 cols['Source reference'].objects.link(o);o.name='SOURCE | '+o.name;o.scale*=S;o.hide_render=True
cols['Source reference'].hide_viewport=True;cols['Source reference'].hide_render=True
spec={'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'scale':S,'front':'-Y','left':'+X','up':'+Z','wheels':wheel_data,'width_profile':WIDTH,'tail_profile':TAIL,'arches':ARCH,'door_outline':doorpoly,'observations':['Wheel centres and original body stance measured from source, symmetric X about centre.','Side shoulder turns inward above z=.27; roof narrower than waist.','Bonnet rises from z=.286 at nose to .322 at scuttle; crown is confined inside mating perimeter.','One door per side, flat wide quarter window, upright sloped rear glass.','Original open windows, uneven skins and wheel cones replaced; no texture data exists in source.','Generated image discrepancies resolved to one left-side snorkel and no rear-facing roof lamps.'],'scope':'Separated fitted geometry, basic interior, material slots and UVs. No textures, LODs, skin rig, Chaos or Unreal validation.'}
(OUT/'vehicle-spec.json').write_text(json.dumps(spec,indent=2));(OUT/'build-script.py').write_text(Path(__file__).read_text())
# Export just the fitted assembly.
for o in bpy.context.scene.objects:o.select_set(False)
for o in owned+list(roots.values()):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Panda_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Panda_Assembly.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.object.select_all(action='DESELECT')
# Reproducible review cameras with source and rebuilt model on identical coordinates.
sc.world=bpy.data.worlds.new('Panda Studio');sc.world.color=(.17,.17,.17);sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';sh.show_specular_highlight=True
camd=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',camd);cols['Studio'].objects.link(cam);sc.camera=cam;camd.type='ORTHO'
center=Vector((0,0,.268))*S
views=[('side',(3,0,.268),1.20),('front',(0,-3,.268),.86),('rear',(0,3,.268),.86),('top',(0,0,3),1.22),('quarter',(1.7,-2.7,1.6),1.28),('rear-quarter',(1.8,2.6,1.3),1.28),('underside',(1.2,1.4,-2),1.25),('wheel-off',(2,-.1,.16),1.2)]
for name,pos,scale in views:
 cols['Wheels'].hide_render=name=='wheel-off';cam.location=Vector(pos)*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=scale*S;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cols['Wheels'].hide_render=False
cam.location=Vector((1.7,-2.7,1.6))*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=1.28*S
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.clip_end=1000;area.spaces.active.region_3d.view_distance=5;area.spaces.active.region_3d.view_location=center;area.spaces.active.shading.color_type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda_Assembly.blend'))
report={'objects':len(owned),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in owned),'quads':sum(sum(len(p.vertices)==4 for p in o.data.polygons) for o in owned),'materials':len(M),'wheels':wheel_data}
(OUT/'build-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
