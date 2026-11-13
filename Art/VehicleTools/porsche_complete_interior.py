"""Fitted cockpit, executed by complete_porsche_v04.py in metres."""
# Continuous shaped carpet pan fitted inside the original shell.
foot=[(-.51,-.97),(.51,-.97),(.69,-.67),(.765,-.30),(.765,.52),(.62,.77),(.49,1.15),(-.49,1.15),(-.62,.77),(-.765,.52),(-.765,-.30),(-.69,-.67)]
floor=mesh('Cabin | continuous carpet pan',[(x,y,.478) for x,y in foot],[tuple(range(len(foot)))],carpet,INT);thick(floor,.015)
# Replacement inner rear tub walls close the source interior removal at the
# wheelhouses. They stay outboard of the narrow 2+2 seats and inboard of tyres.
for side in [-1,1]:
 arc=[(1.204+.435*cos(pi*j/40),.383+.435*sin(pi*j/40)) for j in range(41)]
 wall=mesh('Cabin | rear wheelhouse inner wall '+str(side),[(side*.655,y,z) for y,z in arc],[tuple(range(41))],carpet,INT);thick(wall,.009)
 vs=[(side*x,y,z) for x in [.655,.74] for y,z in arc]
 tub=mesh('Cabin | rear wheelhouse crown '+str(side),vs,[(i,i+1,41+i+1,41+i) for i in range(40)],carpet,INT);thick(tub,.006)
box('Cabin | tunnel',(0,-.01,.515),(.22,1.49,.11),carpet,INT,.035)
box('Cabin | rear footwell riser',(0,.75,.53),(1.08,.18,.13),carpet,INT,.020)
box('Cabin | rear parcel shelf',(0,1.135,1.064),(1.09,.29,.034),dashmat,INT,.018)
rearwall=mesh('Cabin | engine bulkhead',[(-.53,1.12,.48),(.53,1.12,.48),(.56,1.25,1.07),(-.56,1.25,1.07)],[(0,1,2,3)],carpet,INT);thick(rearwall,.015)
firewall=mesh('Cabin | front footwell bulkhead',[(-.54,-.93,.46),(.54,-.93,.46),(.69,-.70,1.02),(-.69,-.70,1.02)],[(0,1,2,3)],carpet,INT);thick(firewall,.012)
for side in [-1,1]:
 kick=mesh('Cabin | front kick panel '+str(side),[(side*.54,-.93,.475),(side*.77,-.36,.478),(side*.79,-.35,.94),(side*.69,-.70,1.015)],[(0,1,2,3)],carpet,INT);thick(kick,.008)
# Curved dashboard shell: a continuous cross-section follows the windscreen base.
xs=np.linspace(-.70,.70,25);sections=[(-.69,1.033),(-.48,1.055),(-.355,1.01),(-.347,.916),(-.55,.885),(-.69,.935)]
vs=[]
for x in xs:
 for y,z in sections:vs.append((float(x),y+.055*(abs(x)/.7)**2,z-.030*(abs(x)/.7)**2))
n=len(sections);fs=[(i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j) for i in range(len(xs)-1) for j in range(n)];fs+=[tuple(reversed(range(n))),tuple((len(xs)-1)*n+j for j in range(n))]
dashboard=mesh('Dashboard | continuous padded shell',vs,fs,dashmat,INT);bevel(dashboard,.007,3)
# The scuttle pad shares its upper border with the real windscreen aperture.
gt=tree(bpy.data.objects['Windscreen']);front=[]
for x in np.linspace(-.67,.67,65):
 for y in np.arange(-.83,-.30,.002):
  hit=gt.ray_cast(Vector((float(x),float(y),1.8)),Vector((0,0,-1)),.85)
  if hit[0] is not None:break
 if hit[0] is not None:front.append(hit[0]+Vector((0,.008,-.008)))
vs=front+[Vector((p.x,-.477,1.052-.03*(abs(p.x)/.7)**2)) for p in front];n=len(front)
scuttle=mesh('Dashboard | windscreen-fitted scuttle pad',vs,[(i,i+1,n+i+1,n+i) for i in range(n-1)],dashmat,INT);thick(scuttle,.012)
st=tree(scuttle);dt=tree(dashboard)
bm=bmesh.new();bm.from_mesh(body.data);es=[]
for e in bm.edges:
 p=(e.verts[0].co+e.verts[1].co)/2
 if abs(p.x)<.70 and -.82<p.y<-.32 and .99<p.z<1.19 and e.calc_length()>.025:es.append(e)
if es:bmesh.ops.subdivide_edges(bm,edges=es,cuts=3,use_grid_fill=True)
bm.to_mesh(body.data);bm.free()
for vert in body.data.vertices:
 p=vert.co
 if abs(p.x)<.67 and -.81<p.y<-.34 and 1.0<p.z<1.16:
  hits=[t.ray_cast(p+Vector((0,0,.12)),Vector((0,0,-1)),.24) for t in [st,dt]]
  heights=[h[0].z for h in hits if h[0] is not None]
  if heights and 0<p.z-max(heights)<.090:p.z=max(heights)-.009
body.data.update()
for x in [-.51,0,.51]:
 box('Dash | demister recess',(x,-.625,1.041),(.19,.027,.008),rubber,INT,.004)
 for j in range(6):box('Dash | demister vane',(x-.078+j*.031,-.625,1.046),(.005,.023,.004),steel,INT,.001)
# Five instrument pods with inset faces, ticks, labels and needles.
gauges=[(.10,.032,'FUEL'),(.24,.041,'OIL'),(.405,.053,'RPM'),(.563,.042,'KM/H'),(.675,.030,'TEMP')]
for idx,(x,r,label) in enumerate(gauges):
 z=1.015-.025*(abs(x)/.7)**2;y=-.331+.055*(abs(x)/.7)**2
 cyl('Gauge | '+label+' housing',(x,y-.012,z),r+.006,.052,rubber,INT,(0,1,0))
 cyl('Gauge | '+label+' bezel',(x,y+.016,z),r+.003,.007,silver,INT,(0,1,0))
 cyl('Gauge | '+label+' face',(x,y+.021,z),r,.004,dashmat,INT,(0,1,0))
 for j in range(25):
  a=math.radians(-135+j*270/24);q1=Vector((x+(r*.78)*sin(a),y+.024,z+(r*.78)*cos(a)));q2=Vector((x+(r*(.95 if j%3==0 else .87))*sin(a),y+.024,z+(r*(.95 if j%3==0 else .87))*cos(a)))
  tube('Gauge | tick',[q1,q2],.0006,ivory,INT)
 a=math.radians(-75+idx*21);tube('Gauge | needle',[(x,y+.028,z),(x+r*.70*sin(a),y+.028,z+r*.70*cos(a))],.0011,red,INT)
 cyl('Gauge | needle cap',(x,y+.030,z),.0035,.003,steel,INT,(0,1,0),16)
 text('Gauge | legend',label,(x,y+.026,z-r*.40),r*.19,ivory,INT)
# Radio and passenger glovebox deliberately below the windscreen.
box('Dash | radio surround',(-.06,-.345,.944),(.245,.022,.062),rubber,INT,.009)
box('Dash | radio face',(-.06,-.331,.944),(.185,.006,.039),steel,INT,.004)
text('Dash | radio display','88.4',(-.06,-.326,.933),.019,ivory,INT)
for x in [-.170,.051]:cyl('Dash | radio rotary knob',(x,-.322,.944),.012,.016,rubber,INT,(0,1,0),24)
box('Dash | glovebox inset',(-.442,-.323,.946),(.42,.008,.074),steel,INT,.012)
box('Dash | glovebox latch',(-.442,-.314,.953),(.058,.014,.016),silver,INT,.004)
for x in [-.665,.01]:
 box('Dash | vent bezel',(x,-.332,.998),(.055,.018,.034),rubber,INT,.006)
 for j in range(4):box('Dash | vent louvre',(x,-.321,.987+j*.006),(.044,.004,.002),steel,INT,.0007)
# Steering column / wheel aligned to the preserved driver side (+X).
wheel_center=Vector((.405,-.125,.983));axis=Vector((0,1,.32)).normalized();u=Vector((1,0,0));v=axis.cross(u).normalized()
tube('Steering | column',[(.405,-.65,.77),wheel_center],.022,steel,INT)
box('Steering | column shroud',(.405,-.26,.91),(.102,.17,.082),dashmat,INT,.019)
steerpieces=[]
steerpieces.append(tube('Steering | leather rim',[wheel_center+u*.150*cos(2*pi*j/64)+v*.150*sin(2*pi*j/64) for j in range(64)],.013,dashmat,INT,True))
steerpieces.append(cyl('Steering | horn hub',wheel_center,.042,.044,dashmat,INT,axis,32))
for a in [15,165,270]:
 t=math.radians(a);p=wheel_center+(u*cos(t)+v*sin(t))*.14
 steerpieces.append(tube('Steering | spoke',[wheel_center,p],.012,silver,INT))
for s in [-1,1]:tube('Steering | stalk',[(.405+s*.04,-.28,.94),(.405+s*.16,-.24,.961)],.007,steel,INT)
# Sculpted seat volumes with coherent curved cross-sections, not donor lumps.
seat_sets={}
for side in [-1,1]:
 cx=side*.405;tag='Driver' if side>0 else 'Passenger';start=set(INT.objects)
 for dx in [-.145,.145]:
  box(tag+' | seat rail',(cx+dx,.08,.482),(.038,.60,.025),steel,INT,.006)
  for y in [-.16,.32]:box(tag+' | bolted rail foot',(cx+dx,y,.471),(.064,.075,.022),steel,INT,.005)
 box(tag+' | seat base',(cx,.07,.532),(.465,.54,.075),dashmat,INT,.030)
 cushion=box(tag+' | cushion',(cx,.045,.608),(.445,.56,.14),cloth,INT,.052)
 box(tag+' | cushion centre',(cx,.01,.681),(.278,.40,.024),insert,INT,.018)
 for dx in [-.188,.188]:box(tag+' | cushion bolster',(cx+dx,.04,.670),(.092,.51,.13),cloth,INT,.039)
 # Backrest and bolsters share the same recline transform.
 back=box(tag+' | backrest',(cx,.385,.959),(.465,.13,.58),cloth,INT,.052);back.rotation_euler.x=math.radians(-12)
 ins=box(tag+' | backrest centre',(cx,.306,.958),(.278,.031,.455),insert,INT,.023);ins.rotation_euler.x=math.radians(-12)
 for dx in [-.193,.193]:
  b=box(tag+' | backrest bolster',(cx+dx,.327,.958),(.085,.145,.51),cloth,INT,.038);b.rotation_euler.x=math.radians(-12)
 for dx in [-.067,.067]:cyl(tag+' | headrest post',(cx+dx,.453,1.269),.008,.11,silver,INT)
 box(tag+' | padded headrest',(cx,.47,1.323),(.285,.144,.15),cloth,INT,.046)
 for j in range(7):
  yy=-.16+j*.057;tube(tag+' | cushion stitched channel',[(cx-.12,yy,.696),(cx+.12,yy,.696)],.0014,cloth,INT)
 for j in range(7):
  zz=.78+j*.055;yy=.306+math.tan(math.radians(12))*(zz-.958)-.019
  tube(tag+' | back stitched channel',[(cx-.12,yy,zz),(cx+.12,yy,zz)],.0014,cloth,INT)
 seat_sets[tag]=[o.name for o in set(INT.objects)-start]
 # Belt follows seat contours and terminates on visible floor anchors.
 anchor=(cx+side*.23,.44,1.18);tube(tag+' | shoulder belt',[anchor,(cx+side*.16,.28,1.13),(cx-side*.15,-.015,.70),(cx-side*.225,.05,.58)],.014,ochre,INT)
 box(tag+' | belt buckle',(cx-side*.233,.06,.59),(.041,.057,.072),rubber,INT,.008)
 box(tag+' | buckle release',(cx-side*.233,.052,.628),(.029,.037,.008),red,INT,.003)
 box(tag+' | belt anchor',(cx+side*.238,.46,.52),(.036,.059,.085),steel,INT,.006)
# Rear 2+2 seats fit between the actual rear wheelhouse volume.
for cx in [-.285,.285]:
 box('Rear cabin | small seat squab',(cx,.853,.674),(.41,.34,.10),cloth,INT,.040)
 box('Rear cabin | squab insert',(cx,.83,.726),(.29,.24,.017),insert,INT,.012)
 back=box('Rear cabin | folding backrest',(cx,1.092,.885),(.415,.088,.30),cloth,INT,.035);back.rotation_euler.x=math.radians(-16)
 ins=box('Rear cabin | backrest inset',(cx,1.043,.885),(.29,.014,.205),insert,INT,.010);ins.rotation_euler.x=math.radians(-16)
 box('Rear cabin | belt buckle',(cx+(.16 if cx<0 else -.16),.83,.745),(.027,.043,.033),rubber,INT,.006)
# Door cards derive depth from the actual exterior at every panel vertex.
for side in [-1,1]:
 contour=[(-.45,.53),(.51,.53),(.62,.68),(.59,1.025),(-.38,1.026),(-.51,.82)]
 points=[]
 for y,z in contour:
  h=bt.ray_cast(Vector((side*1.25,y,z)),Vector((-side,0,0)),.65)
  assert h[0] is not None,('Door card support missing',side,y,z)
  points.append(h[0]-Vector((side*.040,0,0)))
 panel=mesh('Door card | '+str(side),points,[tuple(range(len(points)))],dashmat,INT);thick(panel,.012);bevel(panel,.007,3)
 # A fitted inset and armrest stay inside the narrowest card section.
 x=side*.77
 box('Door card | fabric inset',(x,.09,.82),(.024,.64,.20),insert,INT,.012)
 tube('Door card | padded pull',[(side*.735,-.12,.86),(side*.695,-.075,.86),(side*.695,.105,.86),(side*.735,.15,.86)],.015,dashmat,INT)
 box('Door card | release bezel',(side*.738,-.28,.958),(.019,.087,.037),rubber,INT,.007)
 box('Door card | release lever',(side*.723,-.28,.958),(.012,.06,.014),silver,INT,.004)
 cyl('Door card | speaker',(side*.756,-.30,.657),.063,.014,steel,INT,(-side,0,0),32)
 for j in range(9):
  z=.613+j*.010;half=math.sqrt(max(0,.050**2-(z-.657)**2));tube('Door card | speaker grille',[(side*.746,-.30-half,z),(side*.746,-.30+half,z)],.002,dashmat,INT)
# Console, shifter, handbrake and pedal set.
box('Console | boot surround',(0,-.23,.59),(.16,.20,.043),dashmat,INT,.018)
for k in range(4):box('Console | gaiter fold',(0,-.23,.62+k*.013),(.12-k*.018,.15-k*.022,.020),rubber,INT,.006)
tube('Console | gear lever',[(0,-.23,.662),(0,-.17,.775)],.010,silver,INT)
knob=cyl('Console | shift knob',(0,-.17,.789),.026,.038,dashmat,INT);text('Console | shift diagram','H',(0,-.17,.810),.023,ivory,INT,(0,0,0))
tube('Console | handbrake',[(.065,.13,.568),(.065,-.018,.677)],.014,dashmat,INT)
for j in range(3):
 x=.31+j*.093
 tube('Pedals | arm',[(x,-.82,.485),(x,-.75,.65)],.009,steel,INT)
 p=box('Pedals | rubber pad',(x,-.733,.65),(.062,.019,.089 if j<2 else .13),rubber,INT,.008);p.rotation_euler.x=math.radians(-15)
 for k in range(5):box('Pedals | grip rib',(x,-.721,.623+k*.012),(.052,.004,.003),steel,INT,.001)
for side in [-1,1]:box('Cabin | floor mat',(side*.395,-.54,.486),(.39,.49,.008),rubber,INT,.017)
# Headliner follows the actual roof skin; inner window returns share seal geometry.
vs=[];fs=[];samples=[]
for y in np.linspace(-.05,1.02,19):
 for x in np.linspace(-.55,.55,19):
  h=bt.ray_cast(Vector((float(x),float(y),1.8)),Vector((0,0,-1)),.6)
  if h[0] is not None:samples.append(h[0])
a=np.array([[1,p.x,p.y,p.x*p.x,p.x*p.y,p.y*p.y] for p in samples]);coef=np.linalg.lstsq(a,np.array([p.z for p in samples]),rcond=None)[0]
for y in np.linspace(-.05,1.02,19):
 for x in np.linspace(-.55,.55,19):
  z=float(np.array([1,x,y,x*x,x*y,y*y])@coef)-.025;vs.append((float(x),float(y),z))
for j in range(18):
 for i in range(18):k=j*19+i;fs.append((k,k+19,k+20,k+1))
liner=mesh('Cabin | fitted headliner',vs,fs,insert,INT);thick(liner,.004)
for w in spec['windows']:
 rim=bpy.data.objects[w['name']+' fitted surround'];N=w['outer_ring_vertices'];outer=[rim.data.vertices[i].co.copy() for i in range(N)];inner=[]
 for p in outer:
  if w['name']=='Windscreen':d=Vector((0,.013,-.007))
  elif w['name']=='Rear glass':d=Vector((0,-.012,-.008))
  else:d=Vector((-.014 if p.x>0 else .014,0,0))
  inner.append(p+d)
 o=mesh('Cabin | '+w['name']+' aperture return',outer+inner,[(j,(j+1)%N,N+(j+1)%N,N+j) for j in range(N)],dashmat,INT);thick(o,.002)
for cx in [-.34,.34]:
 visor=box('Cabin | sun visor',(cx,-.14,1.424),(.37,.12,.022),dashmat,INT,.012);visor.rotation_euler.x=math.radians(18)
 tube('Cabin | visor bracket',[(cx-.13,-.115,1.44),(cx-.13,-.165,1.46)],.007,silver,INT)
tube('Cabin | mirror stem',[(0,-.13,1.447),(0,-.08,1.352)],.009,steel,INT)
box('Cabin | rearview mirror case',(0,-.07,1.341),(.213,.032,.066),dashmat,INT,.014)
box('Cabin | rearview mirror',(0,-.05,1.341),(.188,.005,.047),silver,INT,.008)
report['interior']={'layout':'Left driver (+X), five gauges, two front seats and compact 2+2 rear seats','seat_components':seat_sets,'floor_footprint':foot,'floor_top_z':.478,'glass':'Fitted transparent panes and inward-facing aperture returns; rear pane notch corrected locally'}
