"""R50-specific cockpit fitted to the current saved exterior; no body regeneration."""
import bpy,bmesh,math,json,hashlib,sys,argparse,ast,shutil
from pathlib import Path
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Choose a new empty revision.')
out.mkdir(parents=True,exist_ok=True)
src=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-bonnet-wheels-v05');source=src/'Pathfinder_Bonnet_Wheels.blend';source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene
S=json.loads((src/'approved-target-shape-spec.json').read_text());P=S['registration']['pixels_per_metre']
trimcol=None
helpers=ast.parse(Path('C:/GrandTour/Art/VehicleTools/dress_pathfinder_exterior.py').read_text());names={'interp','mesh','curve','box','rr','prism','cut'}
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<shared primitives>','exec'))
def col(n):c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
cab=col('15 | Pathfinder fitted cockpit');seatcol=col('16 | Pathfinder mounted seats');lining=col('17 | Pathfinder cabin lining');fitcol=col('18 | Pathfinder remaining fittings');trimcol=cab
def mat(n,c,rough=.6,metal=0):
 m=bpy.data.materials.new('R50 cockpit | '+n);m.diffuse_color=(*c,1);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;return m
dark=mat('charcoal',(.032,.038,.039));pad=mat('warm graphite',(.095,.101,.098),.8);cloth=mat('stone fabric',(.29,.27,.225),.92);bolster=mat('warm grey bolsters',(.18,.17,.145),.78);seam=mat('upholstery seam',(.10,.095,.08),.9);carpet=mat('carpet',(.053,.055,.05),1);ivory=mat('instrument markings',(.76,.8,.72),.6);dial=mat('recess shadow',(.008,.012,.012));orange=mat('needle',(.8,.20,.045));red=mat('belt release',(.44,.025,.02));metal=mat('satin hardware',(.30,.32,.30),.35,.6);head=mat('headlining',(.36,.35,.30),.95)
black=dark
def Y(u):return -1.35+(u-208)/P
def U(y):return 208+(y+1.35)*P
def Z(v):return .369+(891-v)/P
def width(y,z):return interp(z,S['body_section_z_width'])*interp(U(y),S['longitudinal_width'])
def top(y):return Z(interp(U(y),S['side_top_uv']))
def cabwidth(y,z):
 gutter=Z(interp(U(y),S['roof_gutter_uv']));t=max(0,min(1,(z-top(y))/(gutter-top(y))));return width(y,top(y))*(1-t)+.730*t
def geomhash(o):
 h=hashlib.sha256()
 for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
 for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
 h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode());return h.hexdigest()
protected={o.name:geomhash(o) for o in sc.objects if o.type=='MESH'}
def rod(n,a,b,r,m,c=cab,N=16):
 a=Vector(a);d=Vector(b)-a;w=d.normalized();u=w.cross(Vector((0,0,1)))
 if u.length<.01:u=w.cross(Vector((0,1,0)))
 u.normalize();v=w.cross(u);pts=[a+u*r*math.cos(i*math.tau/N)+v*r*math.sin(i*math.tau/N) for i in range(N)];vs=[tuple(q+t*d) for t in [0,1] for q in pts];fs=[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)];return mesh(n,vs,fs,m,c,0,True)
def text(n,s,loc,size,m=ivory):
 cu=bpy.data.curves.new(n,'FONT');cu.body=s;cu.size=size;cu.align_x='CENTER';cu.align_y='CENTER';cu.extrude=.0001;ob=bpy.data.objects.new(n,cu);cab.objects.link(ob);ob.location=loc;ob.rotation_euler=(math.pi/2,0,math.pi);cu.materials.append(m);return ob
def ring_y(n,x,y,z,w,h,depth,m):
 rad=.028 if n.startswith('Cluster') else .01
 outer=rr(x,z,w,h,rad);inner=rr(x,z,w-.016,h-.016,rad-.005);N=len(outer);vs=[(xx,yy,zz) for yy in [y,y-depth] for loop in [outer,inner] for xx,zz in loop];fs=[]
 for i in range(N):j=(i+1)%N;fs.extend([(i,j,N+j,N+i),(i,2*N+i,2*N+j,j),(N+i,N+j,3*N+j,3*N+i),(2*N+i,3*N+i,3*N+j,2*N+j)])
 return mesh(n,vs,fs,m,cab)
def panel_x(n,poly,x0,x1,m,c=cab):return mesh(n,[(x,y,z) for x in [x0,x1] for y,z in poly],[tuple(range(len(poly)-1,-1,-1)),tuple(range(len(poly),2*len(poly)))]+[(i,(i+1)%len(poly),(i+1)%len(poly)+len(poly),i+len(poly)) for i in range(len(poly))],m,c)

# Fitted front closure above the original inclined footwell; mounting edge seats
# into that existing closure, with the top hidden inside the dashboard shell.
panel_x('Cockpit | firewall',[(-.710,.88),(-.772,1.145),(-.748,1.152),(-.687,.89)],-.77,.77,dark,lining)
dash=panel_x('Dash | contoured carrier',[(-.786,1.138),(-.767,1.169),(-.612,1.163),(-.518,1.126),(-.505,1.025),(-.560,.978),(-.687,.987)],-.778,.778,pad)
bev=dash.modifiers.new('Soft moulded corners','BEVEL');bev.width=.012;bev.segments=3
def vent(x,z,w=.13,h=.075):
 cut(dash,prism('Temporary vent aperture',rr(x,z,w-.01,h-.008,.008),1,-.80,-.45,cab))
 ring_y('Dash vent | return',x,-.496,z,w,h,.040,dark);box('Dash vent | back',(x,-.530,z),(w-.015,.008,h-.015),dial,cab,.003)
 for dz in [-.023,-.011,0,.011,.023]:box('Dash vent | louvre',(x,-.501,z+dz),(w-.025,.022,.004),pad,cab,.001)
 box('Dash vent | tab',(x,-.484,z),(.019,.007,.009),metal,cab,.001)
for x,w in [(-.67,.13),(.66,.15),(-.097,.14),(.097,.14)]:vent(x,1.083,w)
for x in [-.56,.54]:
 for i in range(9):box('Dash | demister',(x+(i-4)*.018,-.723,1.172),(.008,.036,.002),dial,cab)
box('Dash | glovebox seam',(.415,-.499,1.018),(.385,.014,.11),dark,cab,.014);box('Dash | glovebox lid',(.415,-.488,1.018),(.370,.014,.096),pad,cab,.01);box('Dash | glovebox latch',(.415,-.478,1.044),(.068,.012,.019),dark,cab,.004)

# Recessed analog cassette and readable driver-facing details.
cut(dash,prism('Temporary instrument aperture',rr(-.407,1.172,.39,.176,.02),1,-.79,-.43,cab))
ring_y('Cluster | deep cowl',-.407,-.468,1.17,.414,.195,.19,dark);box('Cluster | instrument plate',(-.407,-.494,1.17),(.392,.014,.171),dial,cab,.013)
box('Cluster | closed rear shell',(-.407,-.655,1.17),(.409,.014,.19),dark,cab,.026)
for x,r,kind in [(-.49,.068,'km/h'),(-.327,.062,'x1000')]:
 rod('Gauge | bezel',(x,-.499,1.178),(x,-.479,1.178),r,metal);rod('Gauge | face',(x,-.477,1.178),(x,-.475,1.178),r-.004,dial)
 for i in range(25):
  ang=math.radians(220-260*i/24);r0=r*(.69 if i%3==0 else .78);r1=r*.87
  rod('Gauge | tick',(x-r0*math.cos(ang),-.472,1.178+r0*math.sin(ang)),(x-r1*math.cos(ang),-.472,1.178+r1*math.sin(ang)),.0009,ivory,N=6)
 for i,lab in enumerate(['0','40','80','120','160'] if kind=='km/h' else ['0','2','4','6','8']):
  ang=math.radians(220-260*i/4);text('Gauge | number',lab,(x-r*.52*math.cos(ang),-.470,1.178+r*.52*math.sin(ang)),.009)
 rod('Gauge | needle',(x,-.468,1.178),(x+r*.53,-.468,1.178+r*.18),.0016,orange,N=6);text('Gauge | label',kind,(x,-.469,1.150),.008)
text('Cluster | odometer','124 082',(-.407,-.467,1.114),.010)
box('Console | radio housing',(0,-.500,.979),(.302,.062,.105),dark,cab,.010);box('Console | radio display',(0,-.462,.996),(.184,.009,.031),dial,cab,.004);text('Console | display','FM  101.7',(0,-.455,.996),.011)
for x in [-.123,.123]:rod('Console | radio knob',(x,-.478,.99),(x,-.447,.99),.016,metal)
for i in range(6):box('Console | preset',(-.091+i*.036,-.453,.961),(.026,.012,.01),pad,cab,.002)
box('Console | climate carrier',(0,-.522,.868),(.303,.102,.107),pad,cab,.013)
for x in [-.095,0,.095]:
 rod('Console | HVAC dial',(x,-.477,.877),(x,-.450,.877),.029,dark);box('Console | dial pointer',(x,-.445,.893),(.003,.003,.012),ivory,cab)
text('Console | legend','TEMP       FAN       AIR',(0,-.447,.837),.010)
console=panel_x('Console | floor tunnel',[(-.55,.441),(-.55,.816),(-.38,.79),(-.22,.62),(.22,.603),(.31,.583),(.31,.441)],-.125,.125,dark)
box('Console | selector surround',(-.04,-.13,.625),(.115,.20,.015),metal,cab,.012);box('Console | selector gate',(-.04,-.13,.634),(.037,.152,.011),dial,cab,.005);rod('Console | selector stem',(-.04,-.17,.636),(-.04,-.145,.77),.011,dark);box('Console | selector grip',(-.04,-.142,.783),(.076,.043,.037),pad,cab,.013)
for yy in [.085,.205]:
 rod('Console | cup socket',(0,yy,.585),(0,yy,.601),.045,dial);curve('Console | cup lip',[(.047*math.cos(i*math.tau/48),yy+.047*math.sin(i*math.tau/48),.605) for i in range(49)],.004,pad,cab)
rod('Console | handbrake',(.104,.015,.63),(.104,.167,.697),.013,pad)

# Steering is independent of seats; driver on -X as in the existing workflow.
wc=Vector((-.407,-.257,1.032));wn=Vector((0,.94,.34)).normalized();wu=Vector((1,0,0));wv=wn.cross(wu);vs=[];fs=[]
for i in range(56):
 d=wu*math.cos(i*math.tau/56)+wv*math.sin(i*math.tau/56)
 for j in range(10):ang=j*math.tau/10;vs.append(tuple(wc+d*(.168+.014*math.cos(ang))+wn*.014*math.sin(ang)))
for i in range(56):
 for j in range(10):fs.append((i*10+j,((i+1)%56)*10+j,((i+1)%56)*10+(j+1)%10,i*10+(j+1)%10))
mesh('Steering | padded rim',vs,fs,dark,cab,0,True)
rod('Steering | column',(-.407,-.56,.91),wc,.026,metal);rod('Steering | shroud',wc-wn*.16,wc-wn*.025,.044,dark);rod('Steering | horn boss',wc-wn*.017,wc+wn*.034,.070,pad)
for ang in [25,155,270]:
 d=wu*math.cos(math.radians(ang))+wv*math.sin(math.radians(ang));rod('Steering | spoke',wc+d*.047,wc+d*.166,.018,dark)
for side in [-1,1]:rod('Steering | stalk',wc-wn*.10+wu*side*.04,wc-wn*.10+wu*side*.14,.008,dark)
for x,w in [(-.49,.085),(-.33,.038)]:
 rod('Pedal | arm',(x,-.645,.9),(x,-.585,.62),.010,metal);box('Pedal | pad',(x,-.570,.613),(w,.03,.085),dark,cab,.006)
 for dz in [-.026,-.012,.012,.026]:box('Pedal | tread',(x,-.552,.613+dz),(w-.012,.003,.003),pad,cab)

# Shaped upholstered grids keep the bolsters and stitched lines on the surface.
seat_specs=[];mounts=[]
def upholstery(n,front,nu,nv,back,m):
 N=len(front);fs=[]
 for j in range(nv-1):
  for i in range(nu-1):k=j*nu+i;fs.extend([(k,k+1,k+1+nu,k+nu),(k+N,k+N+nu,k+N+nu+1,k+N+1)])
 edge=list(range(nu))+[j*nu+nu-1 for j in range(1,nv)]+list(range(N-2,N-nu-1,-1))+[j*nu for j in range(nv-2,0,-1)]
 fs.extend((a,b,b+N,a+N) for a,b in zip(edge,edge[1:]+edge[:1]));ob=mesh(n,front+back,fs,m,seatcol,0,True);return ob
def seat(n,xc,yc,w,rear=False):
 hw=w/2;xs=[-hw,-hw*.82,-hw*.60,0,hw*.60,hw*.82,hw];bumps=[-.02,.025,.009,0,.009,.025,-.02];ys=[(-.25,.635),(-.205,.70),(.13,.688),(.20,.642)];front=[]
 for yy,zz in ys:
  for xx,dz in zip(xs,bumps):front.append((xc+xx,yc+yy,zz+dz))
 ob=upholstery(n+' | cushion',front,7,4,[(x,y,.595) for x,y,z in front],bolster)
 for f in ob.data.polygons:
  if f.index%2==0 and f.index//2%6 in [2,3]:f.material_index=1
 ob.data.materials.append(cloth)
 for xx in [-hw*.60,hw*.60]:curve(n+' | cushion piping',[(xc+xx,yc+y,z+.012) for y,z in ys],.0016,seam,seatcol)
 levels=[(.63,.175),(.71,.175),(1.05,.245),(1.21,.28),(1.245,.275)];fv=[]
 for z,y in levels:
  for xx,bump in zip(xs,[.015,-.025,-.010,0,-.010,-.025,.015]):fv.append((xc+xx*.95,yc+y+bump,z))
 ob=upholstery(n+' | shaped backrest',fv,7,5,[(x,y+.075,z) for x,y,z in fv],bolster);ob.data.materials.append(cloth)
 for f in ob.data.polygons:
  if f.index%2==0 and f.index//2%6 in [2,3]:f.material_index=1
 for xx in [-hw*.57,hw*.57]:curve(n+' | backrest piping',[(xc+xx,yc+y-.011,z) for z,y in levels],.0015,seam,seatcol)
 for dx in [-.075,.075]:rod(n+' | headrest post',(xc+dx,yc+.295,1.21),(xc+dx,yc+.295,1.34),.008,metal,seatcol)
 box(n+' | headrest',(xc,yc+.294,1.36),(.25 if not rear else .235,.102,.155),bolster,seatcol,.028)
 box(n+' | base frame',(xc,yc-.015,.567),(w-.055,.385,.057),dark,seatcol,.009)
 for dx in [-hw*.62,hw*.62]:
  box(n+' | rail',(xc+dx,yc-.020,.511),(.034,.425,.054),metal,seatcol,.004)
  for yy in [-.18,.14]:
   foot=box(n+' | floor foot',(xc+dx,yc+yy,.461),(.057,.078,.060),dark,seatcol,.003);mounts.append(foot.name)
   rod(n+' | mounting bolt',(xc+dx,yc+yy,.488),(xc+dx,yc+yy,.496),.009,metal,seatcol,N=6)
 seat_specs.append({'name':n,'x':xc,'y':yc,'width':w,'rear':rear,'footprint':[xc-hw,xc+hw,yc-.25,yc+.36]})
for side in [-1,1]:
 seat('Front seat '+str(side),side*.410,-.015,.485)
 box('Belt | front buckle '+str(side),(side*.144,.08,.708),(.034,.04,.061),dark,seatcol,.008);box('Belt | release '+str(side),(side*.144,.08,.74),(.027,.025,.006),red,seatcol,.002)
for side in [-1,1]:seat('Rear bench '+str(side),side*.2725,.815,.525,True)

# Carpet uses the exact floor footprint; no invented narrow central rectangle.
floor=bpy.data.objects['Floor | fitted passenger and cargo pan'];cp=floor.copy();cp.data=floor.data.copy();cp.name='Lining | fitted carpet';lining.objects.link(cp);cp.location.z+=.009;cp.data.materials.clear();cp.data.materials.append(carpet)
for mod in cp.modifiers:
 if mod.type=='SOLIDIFY':mod.thickness=.007
# Cargo deck fits inside the rear tubs, leaving their occupied volumes untouched.
box('Cargo | raised load deck',(0,1.659,.603),(1.13,.825,.035),carpet,lining,.004)
for y in [1.30,2.02]:
 for x in [-.51,.51]:box('Cargo | deck support',(x,y,.51),(.060,.060,.162),dark,lining,.003)
for side in [-1,1]:
 for position,ya,yb in [('Front',-.64,.26),('Rear',.36,1.16)]:
  vs=[];fs=[];N=25
  for j in range(N):
   y=ya+(yb-ya)*j/(N-1);low=.49
   for pts in S['arches_uv'].values():
    if pts[0][0]<=U(y)<=pts[-1][0]:low=max(low,Z(interp(U(y),pts))+.045)
   for t in [0,.18,.65,1]:z=low+(1.089-low)*t;vs.append((side*(width(y,z)-.038),y,z))
  for j in range(N-1):
   for k in range(3):i=j*4+k;fs.append((i,i+1,i+5,i+4))
  mesh(position+' door '+str(side)+' | inner card',vs,fs,pad,lining,.012,True)
  ym=(ya+yb)/2
  box(position+' door '+str(side)+' | armrest',(side*.763,ym,.995),(.088,.32,.052),bolster,lining,.013)
  box(position+' door '+str(side)+' | pull recess',(side*.712,ym+.04,1.003),(.015,.11,.025),dial,lining,.006)
  box(position+' door '+str(side)+' | latch',(side*.771,ym-.12,1.062),(.030,.068,.028),metal,lining,.005)
  if position=='Front':
   for i in range(4):box('Door | window switch',(side*.706,ym-.05+i*.025,1.023),(.019,.015,.008),dark,lining,.002)
 # Shoulder belt upper anchor is on the real pillar's inner face.
 y=.28;z=1.39;x=side*(cabwidth(y,z)-.028)
 box('Belt | upper anchor '+str(side),(x-side*.030,y,z),(.082,.063,.06),dark,lining,.006)
 pts=[(x-side*.062,y,1.38),(side*.625,.22,1.08),(side*.58,.18,.715)];vs=[]
 for xx,yy,zz in pts:
  vs.extend([(xx-.021,yy-.002,zz),(xx+.021,yy-.002,zz),(xx-.021,yy+.002,zz),(xx+.021,yy+.002,zz)])
 fs=[(0,1,3,2),(8,10,11,9)]
 for j in range(2):
  k=4*j;fs.extend([(k,k+4,k+5,k+1),(k+2,k+3,k+7,k+6),(k,k+2,k+6,k+4),(k+1,k+5,k+7,k+3)])
 mesh('Belt | flat webbing '+str(side),vs,fs,dark,seatcol)
 box('Belt | lower anchor '+str(side),(side*.59,.195,.687),(.048,.055,.062),dark,seatcol,.008)
roof=bpy.data.objects['Roof | shallow transverse and longitudinal crown'];hl=roof.copy();hl.data=roof.data.copy();hl.name='Lining | fitted headliner';lining.objects.link(hl);hl.location.z-=.029;hl.data.materials.clear();hl.data.materials.append(head)
for mod in hl.modifiers:
 if mod.type=='SOLIDIFY':mod.thickness=.009
for x in [-.43,.43]:box('Lining | sun visor',(x,-.315,1.521),(.34,.125,.026),head,lining,.011)
box('Lining | dome lamp',(0,.42,1.596),(.15,.17,.025),pad,lining,.01);box('Lining | dome diffuser',(0,.42,1.581),(.104,.12,.009),ivory,lining,.007)
rod('Mirror | interior stem',(0,-.438,1.519),(0,-.380,1.431),.011,dark,lining);box('Mirror | interior housing',(0,-.367,1.418),(.245,.032,.083),dark,lining,.012);box('Mirror | interior silver',(0,-.347,1.418),(.224,.005,.062),metal,lining,.007)

# Replace only the glazing material assignment, preserving the original surfaces.
glass=mat('clear smoked glazing',(.84,.89,.86),.065);bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=1;bs.inputs['IOR'].default_value=1.45
glassnames=[]
for ob in sc.objects:
 if ob.type=='MESH' and any(m and m.name=='R50 | shape-study glazing' for m in ob.data.materials):
  ob.data.materials.clear();ob.data.materials.append(glass);glassnames.append(ob.name)

# Existing roof rails receive matching crossbars, seated on their actual rail height.
for y in [.05,1.41]:
 z=1.717;box('Roof | removable crossbar',(0,y,z),(1.33,.07,.039),bpy.data.materials['R50 | charcoal'],fitcol,.012)
 for side in [-1,1]:box('Roof | crossbar clamp',(side*.65,y,z-.015),(.085,.105,.065),dark,fitcol,.008)

for name,h in protected.items():assert geomhash(bpy.data.objects[name])==h,name
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
manifest={'source':str(source),'source_sha256':source_sha,'protected_hashes':protected,'protected_raw_meshes':len(protected),'glazing_material_changes':glassnames,'seat_specs':seat_specs,'mount_feet':mounts,'interior_authority':'Stylized interpretation fitted to the accepted exterior, not a factory-measured cabin. Driver retained on -X.','scope':'Static cockpit, transparent glazing and crossbars. No operating rig, ergonomics or game export certification.'}
(out/'cockpit-manifest.json').write_text(json.dumps(manifest,indent=2));shutil.copy2(Path(__file__),out/Path(__file__).name)
for filename in ['approved-target-shape-spec.json','parent-component-manifest.json','refinement-manifest.json']:shutil.copy2(src/filename,out/filename)

def camera(n,loc,target,ortho,res=(1400,1000)):
 data=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,data);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=ortho;o['resolution']=res;return o
reviews=[camera('Cockpit review | dashboard',(-1.36,.64,1.78),(-.01,-.36,1.01),2.03),camera('Cockpit review | seats',(2.9,-2.3,3.3),(0,.57,.86),3.45),camera('Cockpit review | underside',(3,-3,-3),(0,.35,.5),4.6)]
def render(cam,filename):sc.camera=cam;sc.render.resolution_x,sc.render.resolution_y=cam['resolution'];sc.render.filepath=str(out/(filename+'.png'));bpy.ops.render.render(write_still=True)
# Cycles handles the real glass consistently across outside and cutaway views.
sc.render.engine='CYCLES';sc.cycles.samples=48;sc.cycles.use_denoising=True
for name in ['front quarter','rear quarter','side']:render(bpy.data.objects['Review | '+name],name.replace(' ','-'))
hidden={o:o.hide_render for o in sc.objects}
for o in sc.objects:
 if o.type in ['MESH','CURVE'] and o not in cab.objects.values() and o not in seatcol.objects.values() and o not in lining.objects.values() and not o.name.startswith('Floor |') and not any('Studio' in c.name for c in o.users_collection):o.hide_render=True
hl.hide_render=True
for o in lining.objects:
 if any(s in o.name for s in ['sun visor','dome','Mirror | interior']):o.hide_render=True
render(reviews[0],'dashboard');render(reviews[1],'seating-cutaway')
for o,state in hidden.items():o.hide_render=state
for o in sc.objects:
 if o.type=='MESH' and any('Studio' in c.name for c in o.users_collection):o.hide_render=True
render(reviews[2],'underside')
for o,state in hidden.items():o.hide_render=state
sc.camera=bpy.data.objects['Review | front quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];sc['stage']='Pathfinder static cockpit and fittings; awaiting visual review; no rig/export'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Pathfinder_Cockpit.blend'));print('COCKPIT_READY '+str(out),flush=True)
