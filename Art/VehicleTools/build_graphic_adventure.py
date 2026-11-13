"""Graphic Adventure: measured Tripo shape, shared body interfaces, separated components."""
import bpy,bmesh,math,json,hashlib,ast
from pathlib import Path
from mathutils import Vector
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools');OUT=ROOT/'graphic-adventure-assembly-v01';OUT.mkdir(exist_ok=True)
SRC=Path('C:/Users/mille/Downloads/graphicAdventureRangeRoverTripo.glb');S=4.6
bpy.ops.wm.read_factory_settings(use_empty=True)
cols={};active=[]
for n in ['Panels','Cabin frames','Glazing','Front module','Rear module','Hardware','Underbody','Wheels','Roof equipment']:
 c=bpy.data.collections.new(n);bpy.context.scene.collection.children.link(c);cols[n]=c
def pivot(name,pos=(0,0,0),parent=None):
 o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.location=Vector(pos)*S
 bpy.context.view_layer.update()
 if parent:w=o.matrix_world.copy();o.parent=parent;o.matrix_world=w
 return o
root=pivot('GA | Assembly');M={}
for n,c in {'Body':(.38,.42,.32),'Panel':(.38,.42,.32),'Glass':(.12,.17,.19),'Rubber':(.07,.08,.085),'Metal':(.36,.37,.33),'Light':(.72,.73,.66),'Inner':(.10,.12,.13),'Cargo':(.36,.33,.25),'Strap':(.065,.068,.07)}.items():
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.7;M[n]=m
helpers=ast.parse((ROOT/'defender-retopology-v01/retopologize_defender.py').read_text())
for node in helpers.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['interp','make','grid','box','tube','chamfer','ring_lamp']:exec(compile(ast.Module(body=[node],type_ignores=[]),'shared_helpers','exec'))
_tube=tube
def tube(*args,**kwargs):
 o=_tube(*args,**kwargs);o.data.set_sharp_from_angle(angle=.8);return o
def sx(z):return interp(z,[(.13,.209),(.15,.216),(.18,.2185),(.25,.2185),(.27,.2192),(.286,.2165),(.308,.200),(.424,.1675),(.43,.1675)])
def tail(z):return interp(z,[(.139,.446),(.15,.4525),(.18,.463),(.25,.4908),(.27,.491),(.29,.4862),(.308,.471),(.424,.407)])
Z=[.139,.15,.18,.22,.25,.27,.286,.29,.308]
WHEELS={'LF':(.1897,-.31226,.09619),'RF':(-.1897,-.31226,.09619),'LR':(.1897,.26343,.09619),'RR':(-.1897,.26343,.09619)}
ARCH={
 'Front':{'inner':[(-.420,.136),(-.388,.195),(-.367,.219),(-.260,.219),(-.235,.185),(-.210,.133)],'outer':[(-.437,.138),(-.400,.220),(-.380,.238),(-.247,.238),(-.217,.202),(-.190,.133)],'cy':-.31226},
 'Rear':{'inner':[(.155,.134),(.180,.200),(.199,.219),(.316,.219),(.346,.191),(.371,.136)],'outer':[(.138,.135),(.162,.220),(.188,.238),(.329,.238),(.369,.205),(.392,.139)],'cy':.26343}}
spec={'source':str(SRC),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'uniform_scale':S,'units':'raw coordinates scaled uniformly to metres','shape_authority':'Tripo source and Graphic Adventure reference set; exterior cleaned without transplanting Defender proportions','wheel_centres':WHEELS,'arches':ARCH,'side_stations':[(z,sx(z)) for z in Z+[.424]],'rear_stations':[(z,tail(z)) for z in Z+[.424]],'observations':['Long broad sloping bonnet, single raked windscreen, strong cabin taper.','Shoulder rolls inward above z=.27; rocker and lower rear body tuck inward.','Roof basket and three cases retain measured source bounds.','Triangular side graphics in Tripo became unwanted raised wedges; remove those mesh distortions, defer livery.','Source lacks a complete windscreen; reconstruct glazing in its actual opening.']}
(OUT/'vehicle-spec.json').write_text(json.dumps(spec,indent=2))
def orient(o,n):
 bm=bmesh.new();bm.from_mesh(o.data)
 normal=sum((f.normal*f.calc_area() for f in bm.faces),Vector())
 if normal.dot(Vector(n))<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bm.to_mesh(o.data);bm.free()
def panel(name,rows,n,**kw):
 o=grid(name,rows,**kw);orient(o,n);return o
def surface(name,ys,low,upper,sign,parent=None,rear=False):
 # All height breakpoints are shared, eliminating different chord approximations at joins.
 v=[];keys={};idx=[]
 for z0 in sorted(set(Z+[.133,.135,.136,.138,.162,.202,.205,.220,.238,.265])):
  row=[]
  for y in ys:
   z=min(max(z0,low(y)),upper);yy=tail(z) if rear and y==ys[-1] else y
   p=(sign*sx(z),yy,z);key=tuple(round(c,8) for c in p)
   if key not in keys:keys[key]=len(v);v.append(p)
   row.append(keys[key])
  idx.append(row)
 fs=[]
 for a,b in zip(idx,idx[1:]):
  for i in range(len(ys)-1):
   f=list(dict.fromkeys([a[i],a[i+1],b[i+1],b[i]]))
   if len(f)>=3:fs.append(f)
 o=make(name,v,fs,thick=.012,bevel=.001,parent=parent);orient(o,(sign,0,0));return o
def window(name,outer,inner,mapper,normal,parent=None):
 # Exact unchamfered perimeter, fitted glass and gasket: no detached frame-corner slits.
 n=len(outer);v=[mapper(*p) for p in outer+inner];fs=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 o=make(name+' frame',v,fs,'Cabin frames',thick=.012,bevel=.001,parent=parent);orient(o,normal)
 centre=sum((Vector(p) for p in inner),Vector((0,0)))/n
 inside=[tuple(centre+(Vector(p)-centre)*.98) for p in inner]
 vv=[Vector(mapper(*p))-Vector(normal)*.0007 for p in inner+inside]
 o=make(name+' gasket',vv,fs,'Glazing','Rubber',thick=.005,parent=parent);orient(o,normal)
 vv=[Vector(mapper(*p))-Vector(normal)*.0009 for p in inside]
 o=make(name+' glass',vv,[tuple(range(n))],'Glazing','Glass',thick=.006,parent=parent);orient(o,normal)
def jamb(name,poly,sign,parent=None):
 centre=sum((Vector(p) for p in poly),Vector((0,0)))/len(poly)
 outside=[Vector(p)+(Vector(p)-centre).normalized()*.004 for p in poly];inside=[Vector(p)-(Vector(p)-centre).normalized()*.006 for p in poly]
 rows=[[(sign*(sx(z)-dep),y,z) for y,z in pts+pts[:1]] for pts,dep in [(outside,.0035),(inside,.0035),(inside,.014)]]
 panel(name,rows,(sign,0,0),group='Cabin frames',mat='Inner',thick=.008,parent=parent)

# Doors and fixed quarter panels derive from one cross-section and arch profile.
for side,sign in [('L',1),('R',-1)]:
 af=ARCH['Front'];ar=ARCH['Rear']
 surface(side+' front wing',[-.448,-.437,-.400,-.380,-.31226,-.247,-.217,-.190,-.180],lambda y:interp(y,af['outer']),.265,sign)
 for label,a,b,ytop in [('Front',-.177,.041,-.102),('Rear',.050,.249,.050)]:
  par=pivot('GA | '+side+' '+label+' door',(sign*sx(.24),a,.24),root)
  low=lambda y:.139 if label=='Front' or y<.138 else interp(y,ar['outer'])+.001
  ys=sorted(set([a,b]+[y for y in [a+.003,-.1,0,.10,.138,.162,.188,.22,b-.003] if a<y<b]))
  surface(side+' '+label+' door skin',ys,low,.308,sign,par)
  outer=[(a,.308),(ytop,.424),(b if label=='Front' else .210,.424),(b,.308)]
  inner=[(a+.017,.324),(ytop+.012,.414),(b-.012 if label=='Front' else .198,.414),(b-.013,.324)]
  window(side+' '+label+' window',outer,inner,lambda y,z:(sign*sx(z),y,z),(sign,0,0),par)
  outline=[(a,low(a)),(b,low(b)),(b,.308),(b if label=='Front' else .210,.424),(ytop,.424),(a,.308)]
  if label=='Rear':outline.insert(1,(.138,.139))
  jamb(side+' '+label+' door jamb',outline,sign)
  hy=b-.037
  box(side+' '+label+' handle cup',(sign*(sx(.282)+.001),hy,.282),(.003,.033,.012),mat='Inner',bevel=.003,parent=par)
  box(side+' '+label+' handle',(sign*(sx(.282)+.004),hy,.283),(.007,.014,.007),bevel=.003,parent=par)
  if label=='Front':
   tube(side+' mirror bracket',(sign*.201,-.160,.308),(sign*.235,-.148,.319),.003,parent=par)
   box(side+' mirror casing',(sign*.236,-.138,.324),(.037,.024,.035),mat='Inner',bevel=.009,parent=par)
   box(side+' mirror glass',(sign*.236,-.124,.324),(.031,.003,.028),mat='Glass',bevel=.005,parent=par)
 surface(side+' rear quarter',[.251,.28,.329,.369,.392,.415,.449,.491],lambda y:interp(y,ar['outer']),.308,sign,rear=True)
 # Recessed fixed pillar strips and full cowl cheek physically back every reveal.
 panel(side+' B pillar',[[(sign*sx(z),y,z) for y in [.041,.050]] for z in Z+[.424]],(sign,0,0),group='Cabin frames',thick=.022)
 panel(side+' C pillar',[[(sign*sx(z),y,z) for y in [interp(z,[(.308,.249),(.424,.210)]),interp(z,[(.308,.260),(.424,.221)])]] for z in [.308,.324,.414,.424]],(sign,0,0),group='Cabin frames',thick=.020)
 window(side+' cargo window',[(.260,.308),(.221,.424),(.386,.424),(.446,.308)],[(.274,.324),(.231,.414),(.377,.414),(.426,.324)],lambda y,z:(sign*sx(z),y,z),(sign,0,0))
 panel(side+' D pillar',[[(sign*sx(z),y,z) for y in [interp(z,[(.308,.446),(.424,.386)]),tail(z)]] for z in [.308,.324,.35,.40,.424]],(sign,0,0),group='Cabin frames',thick=.018)
 panel(side+' scuttle cheek',[[(sign*sx(z),y,z) for y in [-.184,-.177]] for z in Z],(sign,0,0),thick=.012)
 panel(side+' roof rebate',[[(sign*(sx(z)-.001),y,z) for y in [-.102,.10,.386,tail(z)]] for z in [.422,.428]],(sign,0,0),group='Cabin frames',thick=.014)
 # Connected flare, return and wheelhouse; the outer lip is the common interface.
 for label,arch in ARCH.items():
  out,inn=arch['outer'],arch['inner'];rr=[]
  for t,x in [(0,None),(.12,.227),(.85,.237),(1,.234)]:
   rr.append([(sign*(sx(a[1]) if x is None else x),a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t) for a,b in zip(out,inn)])
  panel(side+' '+label+' arch flare',rr,(sign,0,0),thick=.008,bevel=.001)
  if label=='Rear':
   # The opening-door reveal over the arch needs a real backing flange.
   panel(side+' rear arch seating return',[[(sign*(sx(z+dz)-.0035),y,z+dz) for y,z in out] for dz in [-.007,.006]],(sign,0,0),group='Underbody',mat='Inner',thick=.008)
  # Inboard wall is behind the tyre's inside axial envelope.
  expanded=[(arch['cy']+(y-arch['cy'])*1.04,.09619+(z-.09619)*1.04) for y,z in inn]
  rr=[[(sign*.234,y,z) for y,z in inn],[(sign*.218,y,z) for y,z in expanded],[(sign*.139,y,z) for y,z in expanded],[(sign*.139,y,.126) for y,z in expanded]]
  panel(side+' '+label+' enclosed wheelhouse',rr,(sign,0,0),group='Underbody',mat='Inner',thick=.007)
 box(side+' rocker',(sign*.207,.029,.134),(.023,.415,.019),'Underbody','Inner',.005)
 panel(side+' sill return',[[(sign*x,y,z) for y in [-.179,.146]] for x,z in [(.216,.139),(.203,.139),(.203,.131)]],(sign,0,0),group='Underbody',mat='Inner',thick=.008)
 panel(side+' cargo floor return',[[(sign*x,y,z) for y in [.376,tail(.139)]] for x,z in [(sx(.139),.139),(.203,.139),(.203,.131)]],(sign,0,0),group='Underbody',mat='Inner',thick=.008)
 box(side+' front marker',(sign*.219,-.425,.256),(.004,.018,.009),mat='Light',bevel=.002)
 # Rear-pillar louvers, seated on the raked quarter pillar.
 for j in range(4):
  z=.335+j*.0045;y=interp(z,[(.308,.446),(.424,.386)])+.008
  tube(side+' D pillar vent '+str(j),(sign*(sx(z)+.0006),y,z),(sign*(sx(z)+.0006),y+.025,z),.0014,mat='Inner')

# Broad clamshell bonnet, preserving the actual source's shallow forward slope.
par=pivot('GA | Bonnet',(0,-.181,.306),root)
hood=[]
for y,edge,mid in [(-.449,.265,.267),(-.440,.265,.2755),(-.40,.282,.2859),(-.30,.295,.2984),(-.22,.301,.310),(-.181,.3038,.3085)]:
 w=sx(edge)
 hood.append([(u*w,y,edge+(mid-edge)*(1-abs(u)**4)) for u in [-1,-.92,-.75,-.4,0,.4,.75,.92,1]])
panel('Bonnet main pressing',hood,(0,0,1),thick=.014,parent=par,smooth=True)
edge=hood[0]+[r[-1] for r in hood[1:]]+list(reversed(hood[-1][:-1]))+[r[0] for r in reversed(hood[1:-1])]
grid('Bonnet perimeter return',[edge+edge[:1],[(x*sx(.265)/sx(z),y,min(z-.001,.265)) for x,y,z in edge+edge[:1]]],thick=.010,parent=par)
for sign in [-1,1]:
 ys=[-.449,-.440,-.430,-.400,-.300,-.220,-.181]
 outline=[(r[0][1],r[0][2]) for r in hood]
 panel('Bonnet seating flange '+str(sign),[[(sign*.215,y,.260) for y in ys],[(sign*.215,y,min(.270,interp(y,outline)-.0003)) for y in ys]],(sign,0,0),group='Underbody',mat='Inner',thick=.008)
# Bonnet edge touches wing at .265; front/side below it use the same contact curve.
panel('Firewall',[[(x,y,z) for x in [-sx(z),-.139,0,.139,sx(z)]] for y,z in [(-.181,.139),(-.181,.265),(-.181,.308)]],(0,-1,0),group='Underbody',mat='Inner',thick=.018)
box('Bonnet scuttle vent',(0,-.202,.313),(.225,.014,.008),mat='Inner',bevel=.004,parent=par)
for x in [-.075,0,.075]:box('Vent divider '+str(x),(x,-.210,.313),(.003,.003,.008),mat='Body',bevel=.001,parent=par)

# Single windscreen; retain its actual raked opening instead of the source's missing faces.
def wind(x,z):return(x,interp(z,[(.308,-.181),(.424,-.111)]),z)
window('Windscreen',[(-.200,.308),(-.1675,.424),(.1675,.424),(.200,.308)],[(-.183,.320),(-.157,.413),(.157,.413),(.183,.320)],wind,(0,-1,0))
for side,sign in [('L',1),('R',-1)]:
 panel(side+' A pillar return',[[wind(sign*sx(z),z),(sign*sx(z),interp(z,[(.308,-.177),(.424,-.102)]),z)] for z in [.308,.32,.4,.424]],(sign,0,0),group='Cabin frames',thick=.014)
 blade_y=wind(0,.329)[1]
 box(side+' wiper spindle',(sign*.12,-.187,.310),(.009,.013,.007),mat='Inner',bevel=.003)
 tube(side+' wiper',(sign*.12,-.189,.312),(sign*.055,blade_y-.003,.329),.0015)
 tube(side+' wiper blade',(sign*.014,blade_y-.002,.329),(sign*.15,blade_y-.002,.329),.0015)
 box(side+' wiper rubber',(sign*.082,blade_y-.0003,.329),(.136,.003,.0018),mat='Rubber',bevel=.001)
panel('Roof front header',[[wind(x,z) for x in [-sx(z),0,sx(z)]] for z in [.421,.428]],(0,-1,0),group='Cabin frames',thick=.014)

# Crowned roof: shared perimeter and a separate fitted gutter.
roof=[]
for y,z in [(-.13,.428),(-.12,.431),(-.10,.4398),(0,.4462),(.15,.4486),(.30,.4465),(.4,.441),(.414,.428)]:
 roof.append([(u*.183,y,.427+(z-.427)*(1-abs(u)**4)) for u in [-1,-.96,-.87,-.7,-.4,0,.4,.7,.87,.96,1]])
roofpar=pivot('GA | Roof',(0,.15,.427),root)
panel('Roof crown',roof,(0,0,1),thick=.012,parent=roofpar,smooth=True)
for sign in [-1,1]:
 ys=[-.102,-.100,0,.15,.30,.4,.407]
 roofcentre=[(r[0][1],r[5][2]) for r in roof]
 # Match the tessellated crown, including its changing fore/aft camber.
 factor=interp(.1675/.183,[(u,1-u**4) for u in [0,.4,.7,.87,.96,1]])
 rr=[[(sign*.1675,y,.4238) for y in ys],[(sign*.1675,y,.427+(interp(y,roofcentre)-.427)*factor) for y in ys]]
 panel('Roof side closure '+str(sign),rr,(sign,0,0),group='Cabin frames',thick=.012,parent=roofpar)
for s in [-1,1]:box('Roof gutter '+str(s),(s*.182,.143,.427),(.007,.547,.004),'Cabin frames','Body',.004,roofpar)

# Rear end: all side/body returns evaluate the same tail(z), avoiding stepped joins.
rearpar=pivot('GA | Lower tailgate',(0,tail(.177),.177),root)
panel('Lower tailgate',[[(x,tail(z),z) for x in [-.169,-.1,0,.1,.169]] for z in [.177,.18,.22,.25,.27,.286,.29,.308]],(0,1,0),group='Rear module',thick=.016,parent=rearpar)
upperpar=pivot('GA | Upper tailgate',(0,tail(.424),.424),root)
window('Rear glazing',[(-sx(.308),.308),(-sx(.424),.424),(sx(.424),.424),(sx(.308),.308)],[(-.176,.321),(-.150,.410),(.150,.410),(.176,.321)],lambda x,z:(x,tail(z),z),(0,1,0),upperpar)
panel('Rear roof header',[[(x,tail(z),z) for x in [-sx(z),0,sx(z)]] for z in [.421,.428]],(0,1,0),group='Cabin frames',thick=.012)
for side,s in [('L',1),('R',-1)]:
 panel(side+' rear lamp support',[[(s*x,tail(z),z) for x in [.170,sx(z)]] for z in Z],(0,1,0),group='Rear module',thick=.014)
 for j,z in enumerate([.209,.240]):
  box(side+' tail lamp '+str(j),(s*.194,tail(z)+.001,z),(.033,.005,.028),'Rear module','Light',.003)
panel('Rear lower apron',[[(x,tail(z),z) for x in [-sx(z),-.169,0,.169,sx(z)]] for z in [.139,.15,.177]],(0,1,0),group='Rear module',thick=.012)
for x in [-.170,.170]:
 panel('Tailgate jamb '+str(x),[[(xx,tail(z)-.004,z) for xx in [x-.004,x+.004]] for z in [.177,.18,.25,.27,.286,.29,.308]],(0,1,0),group='Rear module',mat='Inner',thick=.012)
box('Tailgate latch',(0,tail(.201)+.004,.201),(.027,.006,.018),'Hardware','Inner',.003,rearpar)
box('Rear wiper spindle',(0,tail(.319)+.003,.319),(.008,.009,.008),mat='Inner',bevel=.002,parent=upperpar)
tube('Rear wiper',(0,tail(.319)+.005,.319),(.075,tail(.332)+.003,.332),.002,parent=upperpar)
tube('Rear wiper carrier',(.02,tail(.332)+.002,.332),(.15,tail(.332)+.002,.332),.0015,parent=upperpar)
box('Rear wiper rubber',(.085,tail(.332)+.0003,.332),(.130,.003,.0018),mat='Rubber',bevel=.001,parent=upperpar)
box('Rear bumper',(0,.475,.159),(.446,.050,.047),'Rear module','Inner',.015)

# Nose and recovery bumper. Rectangular light panel corners are explicitly sampled.
for side,s in [('L',1),('R',-1)]:
 cx=s*.155;cz=.227;r=.025;xmin,xmax=sorted([s*.126,s*.187]);zmin,zmax=.190,.264
 angles=sorted([i*math.tau/32 for i in range(32)]+[math.atan2(z-cz,x-cx)%math.tau for x,z in [(xmin,zmin),(xmax,zmin),(xmax,zmax),(xmin,zmax)]])
 outer=[];inner=[]
 for t in angles:
  dx,dz=math.cos(t),math.sin(t);tx=(xmax-cx)/dx if dx>1e-8 else (xmin-cx)/dx if dx<-1e-8 else 1e5;tz=(zmax-cz)/dz if dz>1e-8 else (zmin-cz)/dz if dz<-1e-8 else 1e5
  d=min(tx,tz);outer.append((cx+dx*d,-.451,cz+dz*d));inner.append((cx+dx*r,-.451,cz+dz*r))
 n=len(angles);o=make(side+' headlamp panel',outer+inner,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'Front module',thick=.010);orient(o,(0,-1,0))
 ring_lamp(side+' headlight',(cx,-.452,cz),r*.92)
 for j,z in enumerate([.205,.245]):box(side+' front indicator '+str(j),(s*.204,-.450,z),(.027,.006,.026),'Front module','Light',.003)
 panel(side+' nose corner',[[(s*x,y,z) for x,y in [(.185,-.449),(sx(z),-.448)]] for z in [.187,.25,.265]],(0,-1,0),group='Front module',thick=.012)
box('Grille recess',(0,-.449,.226),(.249,.012,.077),'Front module','Inner',.007)
for i in range(5):box('Grille slat '+str(i),(0,-.457,.197+i*.013),(.244,.006,.004),'Front module','Metal',.002)
for x in [-.125,.125]:box('Grille border '+str(x),(x,-.456,.227),(.004,.008,.076),'Front module','Body',.002)
for z in [.188,.265]:box('Grille edge '+str(z),(0,-.452,z),(.438,.01,.003),'Front module','Body',.002)
# A single closed bumper volume follows the source's swept-back wing ends.
plan=[(-.231,-.419),(-.231,-.461),(-.120,-.480),(.120,-.480),(.231,-.461),(.231,-.419),(.112,-.449),(-.112,-.449)]
v=[(x,y,z) for z in [.140,.188] for x,y in plan];n=len(plan)
make('Front recovery bumper',v,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'Front module','Inner',bevel=.009)
box('Winch cradle',(0,-.473,.163),(.128,.044,.054),'Front module','Inner',.006)
tube('Winch drum',(-.038,-.487,.17),(.038,-.487,.17),.012,'Front module','Metal',n=32)
for x in [-.049,.049]:box('Winch cheek '+str(x),(x,-.480,.170),(.009,.028,.035),'Front module','Metal',.004)
for x in [-.06,.06]:tube('Fairlead roller '+str(x),(x,-.496,.150),(x,-.496,.185),.003,'Front module','Metal')
for z in [.150,.185]:tube('Fairlead roller '+str(z),(-.06,-.496,z),(.06,-.496,z),.003,'Front module','Metal')
for s in [-1,1]:
 box('Tow mount '+str(s),(s*.092,-.480,.161),(.021,.016,.029),'Front module','Inner',.005)
 # Continuous swept bow, not a chain of overlapping capped cylinders.
 vv=[];ff=[];n=24;m=8
 for j in range(n+1):
  t=math.pi/4+j*(math.tau-math.pi/2)/n
  for k in range(m):
   a=k*math.tau/m;vv.append((s*.092+(.012+.003*math.cos(a))*math.cos(t),-.491+.003*math.sin(a),.141+(.017+.003*math.cos(a))*math.sin(t)))
 for j in range(n):
  for k in range(m):ff.append((j*m+k,j*m+(k+1)%m,(j+1)*m+(k+1)%m,(j+1)*m+k))
 ff.extend([tuple(reversed(range(m))),tuple(range(n*m,(n+1)*m))])
 make('Recovery shackle '+str(s),vv,ff,'Front module','Metal',smooth=True)
 tube('Shackle pin '+str(s),(s*.082,-.491,.153),(s*.102,-.491,.153),.003,'Front module','Metal')
 box('Bumper fog '+str(s),(s*.161,-.472,.164),(.029,.010,.019),'Front module','Light',.004)
box('Recovery strap',(.043,-.498,.127),(.007,.002,.083),'Front module','Strap',.002)
box('Front skid plate',(0,-.432,.122),(.143,.070,.010),'Underbody','Metal',.006)

# Continuous compartment floor, fitted to the inner tubs and rear taper.
outline=[(-.205,-.182),(.205,-.182),(.205,.149),(.139,.149),(.139,.377),(.205,.377),(.205,tail(.139)),(-.205,tail(.139)),(-.205,.377),(-.139,.377),(-.139,.149),(-.205,.149)]
make('Fitted cabin floor',[(x,y,.139) for x,y in outline],[tuple(range(len(outline)))],'Underbody','Inner',thick=.023)
box('Engine bay undertray',(0,-.32,.130),(.278,.28,.007),'Underbody','Inner',.003)
for s in [-1,1]:
 box('Chassis rail '+str(s),(s*.102,.015,.116),(.022,.915,.025),'Underbody','Inner',.005)
 for cy in [-.31226,.26343]:tube('Axle '+str(s)+' '+str(cy),(0,cy,.09619),(s*.19,cy,.09619),.009,'Underbody','Metal')
for y in [-.18,0,.14,.405]:box('Body crossmember '+str(y),(0,y,.125),(.38,.018,.022),'Underbody','Inner',.003)
for y in [-.31226,.26343]:box('Differential '+str(y),(0,y,.09619),(.067,.052,.054),'Underbody','Inner',.035)
box('Transmission',(0,-.1,.113),(.085,.35,.050),'Underbody','Inner',.020)

# Circular wheel interfaces with matched bead/barrel width and geometry tread.
def lathe(name,profile,centre,par,mat,segments=48):
 x,y,z=centre;v=[];f=[]
 for ax,r in profile:
  for i in range(segments):t=math.tau*i/segments;v.append((x+ax,y+r*math.cos(t),z+r*math.sin(t)))
 for j in range(len(profile)):
  for i in range(segments):f.append((j*segments+i,j*segments+(i+1)%segments,((j+1)%len(profile))*segments+(i+1)%segments,((j+1)%len(profile))*segments+i))
 o=make(name,v,f,'Wheels',mat,parent=par,smooth=True);o.data.set_sharp_from_angle(angle=.7);return o
for corner,c in WHEELS.items():
 s=1 if c[0]>0 else -1;par=pivot('GA | Wheel '+corner,c,root);r=.0952;w=.040;bead=.057
 lathe(corner+' tyre',[(-w*.83,bead),(-w,bead*1.15),(-w,r*.88),(-w*.68,r),(w*.68,r),(w,r*.88),(w,bead*1.15),(w*.83,bead)],c,par,'Rubber')
 lathe(corner+' rim barrel',[(-.030,.054),(-.030,.059),(.030,.059),(.030,.054)],c,par,'Metal')
 lathe(corner+' rim face',[(s*.026,.049),(s*.031,.052),(s*.033,.058),(s*.030,.059),(s*.023,.055),(s*.022,.049)],c,par,'Metal')
 x,y,z=c
 tube(corner+' hub',(x+s*.018,y,z),(x+s*.036,y,z),.013,'Wheels','Inner',par,n=24)
 tube(corner+' lug mounting disc',(x+s*.022,y,z),(x+s*.030,y,z),.024,'Wheels','Metal',par,n=32)
 tube(corner+' brake disc',(x-s*.020,y,z),(x-s*.016,y,z),.044,'Wheels','Metal',par,n=32)
 box(corner+' brake caliper',(x-s*.010,y+.037,z),(.018,.016,.029),'Wheels','Inner',.006,par)
 for j in range(6):
  t=j*math.tau/6
  vv=[]
  for ax in [s*.020,s*.031]:
   for r,dt in [(.010,-.37),(.052,-.095),(.052,.095),(.010,.37)]:vv.append((x+ax,y+r*math.cos(t+dt),z+r*math.sin(t+dt)))
  make(corner+' spoke '+str(j),vv,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'Wheels','Metal',bevel=.003,parent=par)
 for j in range(5):
  t=j*math.tau/5
  by=y+.019*math.cos(t);bz=z+.019*math.sin(t)
  tube(corner+' bolt '+str(j),(x+s*.029,by,bz),(x+s*.034,by,bz),.0024,'Wheels','Metal',par,n=6)
 # Tread blocks merged into one separate mesh per tyre, avoiding hundreds of scene objects.
 vv=[];ff=[]
 for lane in [-1,0,1]:
  for j in range(36):
   t=(j+(lane%2)*.42)*math.tau/36;rad=Vector((0,math.cos(t),math.sin(t)));tan=Vector((0,-math.sin(t),math.cos(t)));ax=Vector((1,0,0))
   cen=Vector(c)+ax*(lane*.022)+rad*.0951;off=len(vv)
   for a,b,d in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:vv.append(cen+ax*(a*.009)+tan*(b*.0045)+rad*(d*.0017))
   ff.extend(tuple(off+i for i in face) for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
 make(corner+' tread',vv,ff,'Wheels','Rubber',parent=par)

# Roof equipment fitted to the crown and rebuilt as separable cases, lids, straps and rack.
rack=pivot('GA | Roof rack',(0,.15,.455),root)
for s in [-1,1]:
 for y in [-.035,.345]:box('Rack foot '+str(s)+' '+str(y),(s*.137,y,.449),(.026,.033,.019),'Roof equipment','Inner',.005,rack)
 for z in [.461,.491]:tube('Rack rail '+str(s)+' '+str(z),(s*.147,-.048,z),(s*.147,.365,z),.004,'Roof equipment','Inner',rack)
 for y in [-.048,.045,.15,.26,.365]:tube('Rack upright '+str(s)+' '+str(y),(s*.147,y,.461),(s*.147,y,.491),.003,'Roof equipment','Inner',rack)
for y in [-.048,.365]:
 for z in [.461,.491]:tube('Rack cross rail '+str(y)+' '+str(z),(-.147,y,z),(.147,y,z),.004,'Roof equipment','Inner',rack)
for y in [-.032,.045,.12,.20,.28,.35]:box('Rack deck '+str(y),(0,y,.460),(.291,.019,.006),'Roof equipment','Inner',.002,rack)
for s in [-1,1]:
 tube('Roof lamp mount '+str(s),(s*.087,-.064,.443),(s*.087,-.072,.462),.004,'Roof equipment','Inner',rack)
 tube('Roof lamp housing '+str(s),(s*.087,-.080,.470),(s*.087,-.064,.470),.022,'Roof equipment','Inner',rack,n=24)
 ring_lamp('Roof spot '+str(s),(s*.087,-.080,.470),.021,parent=rack)
for label,bounds in [('Front',[(-.118,-.025,.465),(.063,.120,.538)]),('Right',[(.011,.085,.465),(.139,.255,.538)]),('Rear',[(-.126,.131,.465),(-.004,.291,.536)])]:
 a,b=map(Vector,bounds);c=(a+b)/2;d=b-a;par=pivot('GA | Cargo '+label,tuple(c),rack)
 box(label+' cargo base',tuple(c),tuple(d),'Roof equipment','Cargo',.025,par)
 box(label+' cargo lid',(c.x,c.y,b.z-.003),(d.x+.002,d.y+.002,.009),'Roof equipment','Cargo',.012,par)
 for y in [a.y+d.y*.24,a.y+d.y*.76]:
  # Straps are full wrapped bands supported on the rounded case, not hovering roof ornaments.
  box(label+' strap top '+str(y),(c.x,y,b.z+.002),(d.x+.006,.010,.004),'Roof equipment','Strap',.003,par)
  for s in [-1,1]:
   xx=c.x+s*(d.x/2+.001)
   box(label+' strap side '+str(y)+' '+str(s),(xx,y,c.z+.001),(.004,.010,d.z+.002),'Roof equipment','Strap',.003,par)
   box(label+' buckle '+str(y)+' '+str(s),(xx+s*.003,y,b.z-.025),(.006,.016,.015),'Roof equipment','Metal',.003,par)
 tube(label+' luggage handle',(c.x-.021,c.y,b.z+.007),(c.x+.021,c.y,b.z+.007),.003,'Roof equipment','Inner',par)
 for x in [c.x-.021,c.x+.021]:box(label+' handle mount '+str(x),(x,c.y,b.z+.003),(.007,.009,.007),'Roof equipment','Inner',.002,par)
tube('Aerial base',(.195,.447,.346),(.195,.447,.407),.006,'Hardware','Inner')
box('Aerial mounting foot',(.192,.447,.349),(.018,.017,.009),'Hardware','Inner',.003)
tube('Aerial whip',(.195,.447,.407),(.195,.447,.566),.0015,'Hardware','Inner')

# Hidden immutable source for direct comparison in the delivered Blender file.
for o in bpy.context.selected_objects:o.select_set(False)
bpy.ops.import_scene.gltf(filepath=str(SRC))
ref=bpy.data.collections.new('99 SOURCE - hidden original');bpy.context.scene.collection.children.link(ref)
for o in list(bpy.context.selected_objects):
 for col in list(o.users_collection):col.objects.unlink(o)
 ref.objects.link(o);o.scale*=S;o.name='SOURCE | '+o.name;o.hide_render=True;o.hide_set(True)
ref.hide_render=True;ref.hide_viewport=True
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.world=bpy.data.worlds.new('Review world');sc.world.color=(.10,.14,.18)
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
sc.render.resolution_x=1500;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
cd=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',cd);sc.collection.objects.link(cam);sc.camera=cam;cd.type='ORTHO'
def render(name,pos,scale=6.7,target=(0,0,1.25)):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('quarter',(7,-9,4));render('opposite',(-7,-9,3.5));render('side',(9,0,1.3),6.3);render('rear-quarter',(-7,9,3.3));render('underside',(5,-7,-4))
for o in cols['Wheels'].objects:o.hide_render=True
render('wheel-off',(9,-3,1.1),6.2);render('wheel-off-opposite',(-9,3,1.1),6.2)
for o in cols['Wheels'].objects:o.hide_render=False
render('quarter',(7,-9,4))
for o in bpy.context.selected_objects:o.select_set(False)
for o in active:o.hide_set(False);o.select_set(True)
for o in bpy.data.objects:
 if o.type=='EMPTY' and o.name.startswith('GA |'):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'GraphicAdventure_Assembly.glb'),use_selection=True,export_format='GLB',export_apply=True,export_animations=False,export_extras=True)
for o in bpy.context.selected_objects:o.select_set(False)
for o in bpy.data.objects:
 if o.type in {'EMPTY','CAMERA'}:o.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GraphicAdventure_Assembly.blend'))
print('GRAPHIC_ADVENTURE_BUILT',len(active))
