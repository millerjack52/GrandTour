"""Prado-specific panel separation and fitted cabin; retains source exterior surfaces."""
import bpy,bmesh,math,json,sys,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon
from shapely.ops import triangulate
S=5.;SRC=Path('C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v05');OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'Prado_Cabin.blend').exists(),'Saved revision protected'
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Prado_Exterior.blend'))
sc=bpy.context.scene;root=bpy.data.objects['PRADO | working assembly'];cols={c.name:c for c in bpy.data.collections}
for n in ['10 Doors and closures','11 Panel returns','12 Cabin structure','13 Seats','14 Dashboard','15 Controls','16 Cabin trim']:
 c=bpy.data.collections.new(n);sc.collection.children.link(c);cols[n]=c
M={m.name.split(' | ')[-1]:m for m in bpy.data.materials if m.name.startswith('Prado |')}
for n,c in {'Cabin':(.085,.10,.092,1),'Fabric':(.32,.29,.22,1),'Insert':(.51,.45,.32,1),'Carpet':(.055,.060,.049,1),'Marking':(.80,.82,.72,1),'Buckle':(.52,.04,.025,1)}.items():
 m=bpy.data.materials.new('Prado | '+n);m.diffuse_color=c;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=c;p.inputs['Roughness'].default_value=.78;M[n]=m
made=[];preservation={o.name:hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],list(map(tuple,o.matrix_world)))).encode()).hexdigest() for o in sc.objects if o.type=='MESH' and not o.name.startswith('REFERENCE')}
body=bpy.data.objects['Prado | source-fitted body'];rawv=[v.co/S for v in body.data.vertices];rawf=[list(p.vertices) for p in body.data.polygons]
source_tree=BVHTree.FromPolygons(rawv,rawf)
def make(n,v,f,col='12 Cabin structure',mat='Cabin',thick=0,bevel=0,smooth=True):
 me=bpy.data.meshes.new(n);me.from_pydata([Vector(p)*S for p in v],[],f);me.update();bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=smooth
 for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle()<.65
 bm.to_mesh(me);bm.free();me.materials.append(M[mat]);o=bpy.data.objects.new(n,me);cols[col].objects.link(o);o.parent=root;o.color=M[mat].diffuse_color
 if thick:mod=o.modifiers.new('Fitted inward thickness','SOLIDIFY');mod.thickness=thick*S;mod.offset=-1
 if bevel:mod=o.modifiers.new('Rounded manufactured edges','BEVEL');mod.width=bevel*S;mod.segments=3
 if smooth:mod=o.modifiers.new('Face-weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True
 made.append(o);return o
def box(n,c,d,col='12 Cabin structure',mat='Cabin',bevel=.001):
 v=[(c[0]+x*d[0]/2,c[1]+y*d[1]/2,c[2]+z*d[2]/2) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 return make(n,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],col,mat,bevel=bevel)
def tube(n,pts,r,col='15 Controls',mat='Metal',closed=False,segments=12):
 pp=[Vector(p) for p in pts];v=[]
 for i,p in enumerate(pp):
  t=(pp[(i+1)%len(pp)]-pp[i-1]) if closed else (pp[min(i+1,len(pp)-1)]-pp[max(0,i-1)])
  t.normalize();a=t.cross(Vector((0,0,1)))
  if a.length<.01:a=t.cross(Vector((0,1,0)))
  a.normalize();b=t.cross(a);v.extend(p+r*(a*math.cos(j*math.tau/segments)+b*math.sin(j*math.tau/segments)) for j in range(segments))
 f=[(i*segments+j,i*segments+(j+1)%segments,((i+1)%len(pp))*segments+(j+1)%segments,((i+1)%len(pp))*segments+j) for i in range(len(pp) if closed else len(pp)-1) for j in range(segments)]
 if not closed:f += [tuple(reversed(range(segments))),tuple((len(pp)-1)*segments+j for j in range(segments))]
 return make(n,v,f,col,mat)
def interp(t,pts):
 if t<=pts[0][0]:return pts[0][1]
 for (a,b),(c,d) in zip(pts,pts[1:]):
  if t<=c:return b+(d-b)*(t-a)/(c-a)
 return pts[-1][1]

# Split only surfaces inside measured projected door outlines. New cut vertices
# lie on the original triangles. The fixed shell is the exact complementary cut.
DOORS={
 'Front':Polygon([(-.178,.142),(.030,.142),(.030,.418),(-.042,.414),(-.075,.406),(-.099,.389),(-.159,.305),(-.178,.291)]),
 'Rear':Polygon([(.033,.142),(.129,.142),(.143,.177),(.158,.207),(.181,.237),(.199,.253),(.191,.422),(.033,.418)])}
bins={k:[] for k in ['Fixed','Front_L','Rear_L','Front_R','Rear_R']};backs={k:[] for k in bins if k!='Fixed'}
def geometries(p):
 if p.is_empty:return []
 if p.geom_type=='Polygon':return [p]
 return [g for g in getattr(p,'geoms',[]) if g.geom_type=='Polygon']
def projected_clip(points,poly):
 # Barycentric interpolation on the original triangle preserves its surface.
 p0,p1,p2=points;u=p1-p0;v=p2-p0;det=u.y*v.z-u.z*v.y
 if abs(det)<1e-14:return []
 pieces=[]
 for part in geometries(poly):
  for t in triangulate(part):
   if not part.covers(t.representative_point()):continue
   xyz=[]
   for y,z in list(t.exterior.coords)[:3]:
    dy,dz=y-p0.y,z-p0.z;a=(dy*v.z-dz*v.y)/det;b=(u.y*dz-u.z*dy)/det;xyz.append(p0+u*a+v*b)
   if (xyz[1]-xyz[0]).cross(xyz[2]-xyz[0]).dot(u.cross(v))<0:xyz.reverse()
   pieces.append(xyz)
 return pieces
for f in rawf:
 # Source body is triangulated except the two microscopic repair caps.
 triangles=[f] if len(f)==3 else [(f[0],f[j],f[j+1]) for j in range(1,len(f)-1)]
 for tri in triangles:
  pts=[rawv[i] for i in tri];center=sum(pts,Vector())/3;proj=Polygon([(p.y,p.z) for p in pts])
  if min(abs(p.x) for p in pts)<.137 or center.z<.139 or center.z>.427 or not proj.is_valid or proj.area<1e-12:
   bins['Fixed'].append(pts);continue
  side='_L' if center.x>0 else '_R';remaining=proj
  for label,cut in DOORS.items():
   hit=remaining.intersection(cut)
   if hit.area<1e-12:continue
   key=label+side
   # 1.25 mm reveal on the door side; recessed backing covers the reveal.
   doorhit=proj.intersection(cut.buffer(-.00025,join_style=2))
   bins[key]+=projected_clip(pts,doorhit)
   ring=proj.intersection(cut.boundary.buffer(.0015,join_style=2))
   backs[key]+=[[p-Vector((math.copysign(.0018,center.x),0,0)) for p in tr] for tr in projected_clip(pts,ring)]
   remaining=remaining.difference(cut)
  bins['Fixed']+=projected_clip(pts,remaining)
def triangles_object(n,tris,col,mat,thick=0):
 verts=[p for tri in tris for p in tri];return make(n,verts,[(i,i+1,i+2) for i in range(0,len(verts),3)],col,mat,thick=thick)
fixed=triangles_object('Prado | fixed shell and underbody',bins['Fixed'],'01 Body','Paint')
door_objects=[]
for name in backs:
 o=triangles_object('Door | '+name,bins[name],'10 Doors and closures','Paint',thick=.0015);o['separation']='Source-surface clipping; closed pose only, not an opening rig';door_objects.append(o)
 triangles_object('Jamb backing | '+name,backs[name],'11 Panel returns','Rubber',thick=.001)
bpy.data.objects.remove(body,do_unlink=True)

# Bonnet is extracted as its existing upper sheet, preserving all source facets.
# Keep the fixed wings / nose / scuttle in place. Region is inside the hood creases.
me=fixed.data;hoodids=[]
for p in me.polygons:
 c=p.center/S
 if -.406<c.y<-.195 and abs(c.x)<.132 and c.z>.267 and p.normal.z>.65:hoodids.append(p.index)
if hoodids:
 def extract_faces(ob,ids,name,col):
  ids=set(ids);v=[p.co/S for p in ob.data.vertices];f=[list(p.vertices) for p in ob.data.polygons]
  result=make(name,v,[p for i,p in enumerate(f) if i in ids],col,'Paint',thick=.0015)
  new=make(ob.name+' remainder',v,[p for i,p in enumerate(f) if i not in ids],ob.users_collection[0].name,'Paint')
  oldname=ob.name;made.remove(ob);bpy.data.objects.remove(ob,do_unlink=True);new.name=oldname
  return new,result
 fixed,hood=extract_faces(fixed,hoodids,'Bonnet | original surface','10 Doors and closures')

# Continuous passenger/cargo pan; the central tunnel rises over the original
# driveline. Rear side bays rise over, rather than fill, the tyre volume.
FLOOR='12 Cabin structure';TUB=[(.145,.149),(.17,.191),(.20,.234),(.235,.247),(.292,.247),(.323,.226),(.35,.184),(.42,.184)]
YS=[-.180,-.15,-.10,-.05,0,.05,.10,.14,.145,.17,.20,.235,.275,.292,.323,.35,.38,.419]
def basez(y):return interp(y,[(-.18,.144),(.14,.149),(.17,.184),(.419,.184)])
def outerx(y,z):
 hit=source_tree.ray_cast(Vector((.27,y,z)),Vector((-1,0,0)),.16)[0]
 return hit.x+.0004 if hit and hit.x>.14 else .179
def tunnel(y,x):
 if abs(x)>.033 or y>.145:return basez(y)
 return max(basez(y),interp(y,[(-.18,.170),(-.10,.184),(0,.196),(.06,.180),(.145,.170)]))
fv=[];ff=[]
# Central pan ends at the inner wheelhouse wall (same coordinates for both bays).
xs=[-.111,-.038,-.033,0,.033,.038,.111]
for y in YS:
 for x in xs:fv.append((x,y,tunnel(y,x)))
for j in range(len(YS)-1):
 for i in range(len(xs)-1):a=j*len(xs)+i;ff.append((a,a+1,a+1+len(xs),a+len(xs)))
pan=make('Cabin | continuous central floor and tunnel',fv,ff,FLOOR,'Carpet',thick=.002,smooth=False)
for sign in [-1,1]:
 v=[];f=[]
 for y in YS:
  z=max(basez(y),interp(y,TUB)) if y>=.145 else basez(y)
  w=outerx(y,z)
  v.extend([(sign*.111,y,basez(y)),(sign*.111,y,z),(sign*w,y,z)])
 for j in range(len(YS)-1):
  a=j*3
  f += [(a,a+3,a+4,a+1),(a+1,a+4,a+5,a+2)]
 make('Cabin | '+('left' if sign>0 else 'right')+' floor wing and rear wheelhouse',v,f,FLOOR,'Carpet',thick=.002,smooth=False)
# Firewall closes the footwell to the engine, rising behind the source scuttle.
make('Cabin | firewall',[(-.177,-.180,.144),(.177,-.180,.144),(.174,-.180,.294),(-.174,-.180,.294)],[(0,1,2,3)],FLOOR,'Cabin',thick=.003,smooth=False)
make('Cabin | cargo rear upstand',[(-.178,.419,.184),(.178,.419,.184),(.177,.419,.268),(-.177,.419,.268)],[(0,3,2,1)],FLOOR,'Cabin',thick=.002,smooth=False)

SEAT='13 Seats';DASH='14 Dashboard';CTRL='15 Controls';TRIM='16 Cabin trim'
def cb(n,c,d,mat='Cabin',bevel=.002,col=SEAT):return box('CAB | '+n,c,d,col,mat,bevel)
def seat(x,y,label,rear=False):
 floor=basez(y);width=.098 if not rear else .116;cy=y;z=.222 if not rear else .258;backy=y+.060
 for dx in [-width*.33,width*.33]:
  cb(label+' rail',(x+dx,y,floor+.008),(.008,.11,.008),'Metal',.001)
  for dy in [-.042,.042]:cb(label+' attached floor foot',(x+dx,y+dy,floor+.003),(.016,.014,.006),'Metal',.0006)
  cb(label+' riser',(x+dx,y,(floor+.012+z-.019)/2),(.008,.085,z-.019-floor-.012),'Cabin',.001)
 cb(label+' cushion',(x,y,z),(width,.118,.032),'Fabric',.007)
 cb(label+' cushion insert',(x,y-.002,z+.017),(width*.70,.094,.006),'Insert',.003)
 for k in [-1,0,1]:cb(label+' cushion stitched rib',(x+k*width*.19,y-.002,z+.0205),(.0014,.083,.0007),'Fabric',.0002)
 back=cb(label+' backrest',(x,backy,z+.069),(width,.027,.124),'Fabric',.007);center=Vector((x,backy,z+.069))*S;back.data.transform(Matrix.Translation(center)@Matrix.Rotation(-.10,4,'X')@Matrix.Translation(-center))
 cb(label+' backrest insert',(x,backy-.016,z+.070),(width*.69,.004,.094),'Insert',.003)
 for dx in [-.019,.019]:tube(label+' headrest post',[(x+dx,backy+.005,z+.125),(x+dx,backy+.005,z+.153)],.0015,SEAT,'Metal')
 cb(label+' headrest',(x,backy+.005,z+.159),(width*.69,.029,.039),'Fabric',.006)
 # Shoulder straps and buckles are separate parts with anchored endpoints.
 bx=x-math.copysign(width*.56,x)
 tube(label+' buckle stalk',[(bx,y+.035,floor+.01),(bx,y+.035,z+.025)],.0013,SEAT,'Rubber')
 cb(label+' buckle',(bx,y+.035,z+.028),(.008,.012,.014),'Cabin',.001)
 cb(label+' release',(bx,y+.0412,z+.032),(.006,.001,.004),'Buckle',.0003)
seat(.085,-.038,'Driver');seat(-.085,-.038,'Passenger')
# Rear row is in front of the wheel tubs; rear-seat backs stay ahead of y=.20.
seat(.065,.120,'Rear left',True);seat(-.065,.120,'Rear right',True)

# Door cards follow the body taper and remain entirely below the glazing.
for s in [-1,1]:
 for label,ya,yb in [('Front',-.169,.023),('Rear',.038,.141)]:
  y=(ya+yb)/2
  v=[(s*.174,ya,.159),(s*.174,yb,.159),(s*.171,yb,.292),(s*.171,ya,.292)]
  make('CAB | '+label+' door card '+str(s),v,[(0,1,2,3)],TRIM,'Fabric',thick=.002,bevel=.001)
  cb(label+' padded armrest '+str(s),(s*.161,y,.240),(.026,(yb-ya)*.65,.018),'Cabin',.004,TRIM)
  cb(label+' release bezel '+str(s),(s*.169,y-.02,.270),(.004,.025,.013),'Cabin',.001,TRIM)
  cb(label+' release grip '+str(s),(s*.166,y-.02,.270),(.004,.016,.003),'Metal',.0005,TRIM)
  cb(label+' door pocket '+str(s),(s*.166,y,.189),(.012,(yb-ya)*.65,.034),'Cabin',.002,TRIM)
  if label=='Front':
   tube('Speaker rim '+str(s),[(s*.160,y-.044+.017*math.cos(a*math.tau/24),.199+.017*math.sin(a*math.tau/24)) for a in range(24)],.001,TRIM,'Metal',True)
   for k in range(-3,4):tube('Speaker grille '+str(s),[(s*.159,y-.056,.199+k*.0035),(s*.159,y-.032,.199+k*.0035)],.0006,TRIM,'Rubber')

# Compact 1990s utility dashboard: source windscreen lower boundary is z~.31.
cb('Dashboard upper',(0,-.143,.294),(.331,.072,.025),'Cabin',.007,DASH)
cb('Dashboard fascia',(0,-.118,.270),(.322,.018,.044),'Cabin',.004,DASH)
cb('Passenger glovebox',(-.096,-.106,.267),(.104,.004,.029),'Fabric',.002,DASH)
cb('Glovebox latch',(-.096,-.103,.273),(.017,.003,.005),'Metal',.0005,DASH)
for x in [-.145,-.035,.025,.145]:
 cb('Vent recessed face',(x,-.107,.283),(.027,.003,.011),'Rubber',.001,DASH)
 for k in range(4):cb('Vent vane',(x-.009+k*.006,-.1047,.283),(.0013,.001,.008),'Metal',.0002,DASH)
cb('Centre radio recess',(0,-.105,.264),(.047,.004,.018),'Rubber',.001,DASH)
cb('Radio display',(0,-.1025,.267),(.025,.001,.007),'Glass',.0003,DASH)
for x in [-.018,.018]:tube('Radio knob',[(x,-.102,.263),(x,-.098,.263)],.003,DASH,'Metal')
for x in [-.015,0,.015]:tube('Heater dial',[(x,-.105,.248),(x,-.100,.248)],.0035,DASH,'Metal')
for x in [-.14,.14]:
 cb('Demister slot',(x,-.158,.307),(.065,.005,.001),'Rubber',.0003,DASH)
# Gauges are recessed in a separate hood with real rims and needles.
cb('Instrument hood',(.085,-.128,.309),(.091,.044,.040),'Cabin',.005,DASH)
cb('Instrument face',(.085,-.104,.308),(.080,.003,.031),'Rubber',.001,DASH)
for x,r,label in [(.064,.012,'tachometer'),(.098,.013,'speedometer')]:
 tube(label+' bezel',[(x+r*math.cos(k*math.tau/40),-.101,.308+r*math.sin(k*math.tau/40)) for k in range(40)],.001,DASH,'Metal',True)
 for k in range(11):
  a=math.radians(-40+k*26)
  tube(label+' tick',[(x+r*.69*math.cos(a),-.100,.308+r*.69*math.sin(a)),(x+r*.84*math.cos(a),-.100,.308+r*.84*math.sin(a))],.00025,DASH,'Marking',segments=6)
 tube(label+' needle',[(x,-.0995,.308),(x-r*.53,-.0995,.308+r*.31)],.00035,DASH,'Buckle',segments=6)
# Driver at +X is a working-layout choice; no real-vehicle exactness claimed.
sx=.085;steercenter=Vector((sx,-.067,.297));axis=Vector((0,1,.40)).normalized();right=Vector((1,0,0));up=axis.cross(right)
tube('Steering column',[(sx,-.133,.258),tuple(steercenter)],.005,CTRL,'Cabin')
points=[steercenter+.034*(right*math.cos(k*math.tau/48)+up*math.sin(k*math.tau/48)) for k in range(48)]
tube('Steering rim',points,.0031,CTRL,'Rubber',True)
for ang in [.15,math.pi-.15,math.pi*1.5]:tube('Steering spoke',[steercenter,steercenter+.031*(right*math.cos(ang)+up*math.sin(ang))],.0025,CTRL,'Metal')
cb('Steering centre',tuple(steercenter),(.024,.011,.017),'Cabin',.003,CTRL)
for x in [.066,.092,.117]:
 tube('Pedal arm',[(x,-.174,.210),(x,-.156,.177)],.0018,CTRL,'Metal')
 cb('Pedal pad',(x,-.154,.176),(.012,.006,.019),'Rubber',.001,CTRL)
cb('Console housing',(0,-.025,.209),(.057,.131,.032),'Cabin',.004,CTRL)
cb('Gear lever boot',(0,-.046,.226),(.023,.023,.011),'Rubber',.002,CTRL)
tube('Gear lever',[(0,-.046,.227),(0,-.04,.261)],.0018,CTRL,'Metal');cb('Gear knob',(0,-.04,.264),(.011,.014,.013),'Cabin',.004,CTRL)
tube('Transfer lever',[(.018,-.022,.225),(.018,-.018,.247)],.0015,CTRL,'Metal');cb('Transfer knob',(.018,-.018,.249),(.009,.011,.009),'Rubber',.003,CTRL)
tube('Handbrake',[(.026,.018,.218),(.026,-.012,.230)],.0022,CTRL,'Rubber')
for x in [-.012,.012]:tube('Cup holder',[(x+.007*math.cos(k*math.tau/20),.015+.007*math.sin(k*math.tau/20),.226) for k in range(20)],.001,CTRL,'Rubber',True)

# Rear cargo tray between the wheelhouses, tied down to the raised floor.
cb('Cargo tray',(0,.313,.190),(.212,.177,.010),'Cabin',.002,TRIM)
for x in [-.09,.09]:
 for y in [.245,.383]:tube('Cargo tie-down',[(x+.004*math.cos(k*math.tau/16),y+.004*math.sin(k*math.tau/16),.196) for k in range(16)],.0008,TRIM,'Metal',True)
# Thin headliner, offset from measured roof underside; kept above headrests.
box('CAB | Headliner',(0,.136,.424),(.267,.438,.003),TRIM,'Insert',.008)
cb('Interior lamp',(0,.073,.419),(.021,.032,.008),'Lens',.002,TRIM)
for x in [-.085,.085]:cb('Sun visor',(x,-.086,.408),(.077,.028,.006),'Fabric',.002,TRIM)
tube('Rear mirror stalk',[(0,-.098,.409),(0,-.114,.392)],.0015,TRIM,'Cabin')
cb('Interior mirror housing',(0,-.114,.388),(.049,.005,.017),'Cabin',.002,TRIM)
cb('Interior mirror face',(0,-.111,.388),(.043,.001,.012),'Wheel',.001,TRIM)

# Use a thin-sheet transmission shader for game-style glazing; preview is still
# Workbench until the lit exterior render verifies cabin visibility.
glass=M['Glass'];p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.72,.82,.86,1);p.inputs['Transmission Weight'].default_value=1;p.inputs['Roughness'].default_value=.08
for name in ['FrontDoor_L','FrontDoor_R','RearDoor_L','RearDoor_R']:
 bpy.data.objects['Glass | '+name]['assembly_role']='Pane fitted to original opening; retain with corresponding door'

sc['asset_status']='Separated door skins and bonnet, fitted cabin; static model, engine preparation not complete'
report={'source':str(SRC/'Prado_Exterior.blend'),'source_sha256':hashlib.sha256((SRC/'Prado_Exterior.blend').read_bytes()).hexdigest(),'new_objects':[o.name for o in made if o.name in bpy.data.objects],'prior_fingerprints':preservation,'body_method':'Original surfaces partitioned by projected door boundaries; complementary fixed shell retained. No exterior displacement.','door_profiles':{n:list(p.exterior.coords) for n,p in DOORS.items()},'floor_y_stations':YS,'rear_tub_profile':TUB,'remaining':['Full fixed-shell retopology and residual source seam audit','Tailgate and bumper separation','Opening and driving rig','UVs, LODs, collision and Unreal validation']}
(OUT/'build-report.json').write_text(json.dumps(report,indent=2))
cam=sc.camera
def render(n,c,d,scale=1.2):
 center=Vector(c)*S;cam.location=center+Vector(d)*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*S;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for n,d in [('side',(3,0,0)),('opposite-side',(-3,0,0)),('quarter',(2,-3,1.1)),('rear-quarter',(-2,3,1)),('underside',(1,-1,-2))]:render(n,(0,0,.27),d)
# Cutaway review isolates the actual interior meshes, not an illustrative image.
hidden=[]
for o in sc.objects:
 if o.type=='MESH' and all(c.name not in ['12 Cabin structure','13 Seats','14 Dashboard','15 Controls','16 Cabin trim'] for c in o.users_collection) and not o.hide_render:hidden.append(o);o.hide_render=True
head=bpy.data.objects['CAB | Headliner'];head.hide_render=True
render('cabin-cutaway',(0,.08,.26),(2,1.6,2),.77)
render('dashboard',(0,-.115,.283),(.3,3,1.6),.41)
render('seating',(0,.08,.26),(2,-1,1.4),.57)
for o in hidden:o.hide_render=False
head.hide_render=False
render('quarter',(0,0,.27),(2,-3,1.1))
bpy.ops.object.select_all(action='DESELECT');fixed.select_set(True);bpy.context.view_layer.objects.active=fixed
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Cabin.blend'))
print('SAVED',OUT,'new objects',len(made))
