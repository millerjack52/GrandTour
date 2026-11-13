"""Approved RR rack/bar/snorkel, authored as separate fitted Blender collections."""
import bpy,bmesh,math,json,sys,hashlib,shutil
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));import wheel_fender_workshop as wf
OUT=Path(sys.argv[sys.argv.index('--')+1]).resolve();OUT.mkdir(parents=True,exist_ok=False)
ROOT=Path('C:/GrandTour');SOURCE=ROOT/'Art/rangerover.blend';source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
REF=ROOT/'Art/References/Vehicles/RangeRoverCustomization_2026-10-25_v01/03-bolt-on-equipment.png'
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene
with bpy.data.libraries.load(str(SOURCE)) as (src,dst):dst.objects=[n for n in src.objects if not n.startswith('Ref_')]
for o in dst.objects:
 if o:sc.collection.objects.link(o)
bpy.context.view_layer.update();body=[o for o in dst.objects if o and o.type=='MESH' and not o.name.lower().startswith('wheel')]
def tree(obs):
 vs=[];fs=[];dg=bpy.context.evaluated_depsgraph_get()
 for o in obs:
  e=o.evaluated_get(dg);m=e.to_mesh();n=len(vs);vs += [o.matrix_world@v.co for v in m.vertices];fs += [tuple(n+i for i in f.vertices) for f in m.polygons];e.to_mesh_clear()
 return BVHTree.FromPolygons(vs,fs)
roof=tree([o for o in body if o.name=='Roof']);bumper=tree([o for o in body if o.name=='bumper']);pillar=tree([o for o in body if o.name=='pillars']);wing=tree([o for o in body if o.name=='frontPanel'])
black=wf.material('Equipment | powder steel',(.022,.028,.031),.53,.35)
metal=wf.material('Equipment | plated bolts',(.34,.37,.38),.32,.75)
plastic=wf.material('Equipment | intake polymer',(.018,.023,.026),.66,0)
rubber=wf.material('Equipment | rubber pad',(.012,.015,.018),.84,0)
parts=[];contacts=[]
def collection(name):
 c=bpy.data.collections.new('EQUIPMENT | '+name);sc.collection.children.link(c);c['kind']='equipment';c['axis']='metres; X left, -Y front, Z up; car-origin pivot'
 c.asset_mark();parts.append(c);return c
def box(name,loc,size,mat,c,bevel=.003,mount=False):
 x,y,z=size;v=[(a*x/2,b*y/2,d*z/2) for a,b,d in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 fs=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
 o=wf.mesh(name,[Vector(p)+Vector(loc) for p in v],fs,mat,c,bevel=bevel);o['mount_contact']=mount;return o
def tube(name,points,r,mat,c,closed=False,segments=16,mount=False):
 pts=[]
 for p in points:
  p=Vector(p)
  if not pts or (p-pts[-1]).length>1e-6:pts.append(p)
 vs=[];fs=[];n=len(pts);previous_tangent=previous_a=None
 for i,p in enumerate(pts):
  tangent=(pts[(i+1)%n]-pts[(i-1)%n]).normalized() if closed or 0<i<n-1 else (pts[1]-pts[0]).normalized() if i==0 else (pts[-1]-pts[-2]).normalized()
  if previous_tangent is None:
   axis=min([Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))],key=lambda v:abs(v.dot(tangent)))
   a=tangent.cross(axis).normalized()
  else:
   a=previous_tangent.rotation_difference(tangent)@previous_a
   a=(a-tangent*a.dot(tangent)).normalized()
  b=tangent.cross(a).normalized();previous_tangent=tangent;previous_a=a
  vs.extend(p+r*(a*math.cos(j*math.tau/segments)+b*math.sin(j*math.tau/segments)) for j in range(segments))
 for i in range(n if closed else n-1):
  for j in range(segments):fs.append((i*segments+j,i*segments+(j+1)%segments,((i+1)%n)*segments+(j+1)%segments,((i+1)%n)*segments+j))
 if not closed:fs += [tuple(range(segments-1,-1,-1)),tuple((n-1)*segments+j for j in range(segments))]
 o=wf.mesh(name,vs,fs,mat,c);o['mount_contact']=mount
 for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
 return o
def bolt(name,p,axis,c):
 p=Vector(p);axis=Vector(axis);tube(name,[p-axis*.007,p+axis*.007],.009,metal,c,segments=6,mount=True)
def rounded_rect(x0,x1,y0,y1,z,r):
 pts=[]
 for x,y,start in [(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)]:
  for j in range(9):
   a=math.radians(start+j*90/8);pts.append((x+r*math.cos(a),y+r*math.sin(a),z))
 return pts
c=collection('Roof Rack')
for z in [1.88,2.025]:tube('Rack | continuous perimeter',rounded_rect(-.68,.68,-.46,1.66,z,.065),.016,black,c,True)
for y in [-.39,.15,.7,1.2,1.59]:
 tube('Rack | transverse bearer',[(-.665,y,1.88),(.665,y,1.88)],.013,black,c)
for x in [-.54,-.36,-.18,0,.18,.36,.54]:box('Rack | deck slat',(x,.60,1.897),(.047,2.08,.018),black,c,.004)
for x in [-.68,.68]:
 for y in [-.35,.25,.95,1.55]:tube('Rack | rail upright',[(x,y,1.88),(x,y,2.025)],.012,black,c)
for side in [-1,1]:
 for y in [-.30,.58,1.48]:
  x=side*.675;p=roof.ray_cast(Vector((x,y,2.3)),Vector((0,0,-1)),1)[0];assert p is not None
  # Pad vertices follow the actual roof surface at their four corners.
  corners=[]
  for dx,dy in [(-.027,-.06),(.027,-.06),(.027,.06),(-.027,.06)]:
   hit=roof.ray_cast(Vector((x+dx,y+dy,2.3)),Vector((0,0,-1)),1)[0];assert hit is not None
   corners.append(hit)
  verts=[q+Vector((0,0,h)) for h in [-.001,.009] for q in corners]
  o=wf.mesh('Rack | fitted rubber foot',verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],rubber,c);o['mount_contact']=True
  tube('Rack | load leg',[p+Vector((0,0,.008)),Vector((side*.665,y,1.885))],.019,black,c,mount=True)
  box('Rack | clamp saddle',(x,y,p.z+.015),(.05,.11,.014),black,c,.002,True)
  # Turned-down outer clamp jaw wraps the roof edge; attached via the saddle.
  box('Rack | clamp outer jaw',(side*.708,y,p.z-.009),(.012,.105,.065),black,c,.003,True)
  tube('Rack | clamp shoulder',[(x,y,p.z+.019),(side*.708,y,p.z+.019)],.012,black,c,mount=True)
  bolt('Rack | clamp fastener',(side*.716,y,p.z), (1,0,0),c);contacts.append(dict(part='rack',point=list(p),surface='Roof'))
c=collection('Bull Bar')
# A continuous modest hoop, with rounded top corners, stays below the bonnet sightline.
path=[(-.78,-2.43,.50),(-.78,-2.43,.84)]
for j in range(9):
 a=math.pi-j*math.pi/16;path.append((-.70+.08*math.cos(a),-2.43,.84+.08*math.sin(a)))
path.append((.70,-2.43,.92))
for j in range(1,9):
 a=math.pi/2-j*math.pi/16;path.append((.70+.08*math.cos(a),-2.43,.84+.08*math.sin(a)))
path.append((.78,-2.43,.50));tube('Bull bar | main hoop',path,.029,black,c,segments=24)
tube('Bull bar | lower tie',[(-.78,-2.43,.56),(.78,-2.43,.56)],.025,black,c)
for x in [-.46,.46]:
 p=bumper.ray_cast(Vector((x,-2.7,.52)),Vector((0,1,0)),1)[0];assert p is not None
 box('Bull bar | bumper mount',(x,p.y+.004,.52),(.105,.018,.12),black,c,.004,True)
 box('Bull bar | forward bracket',(x,(p.y-2.43)/2,.51),(.055,abs(p.y+2.43)+.014,.07),black,c,.004,True)
 tube('Bull bar | upright brace',[(x,-2.43,.52),(x,-2.43,.905)],.018,black,c)
 for z in [.48,.56]:bolt('Bull bar | bracket bolt',(x,p.y-.012,z),(0,1,0),c)
 # Recovery eyes are model detail only, not gameplay tow anchors.
 loop=[(x+.045*math.cos(a),-2.478,.495+.055*math.sin(a)) for a in [i*math.tau/32 for i in range(32)]]
 tube('Bull bar | recovery eye',loop,.010,metal,c,True);tube('Bull bar | eye pin',[(x-.04,-2.478,.535),(x+.04,-2.478,.535)],.010,black,c)
 tube('Bull bar | eye hanger',[(x,-2.43,.55),(x,-2.478,.54)],.018,black,c);contacts.append(dict(part='bull_bar',point=list(p),surface='bumper'))
c=collection('Snorkel')
duct=[(.958,-1.34,1.075),(.958,-1.16,1.075),(.955,-1.05,1.09),(.928,-.96,1.18),(.88,-.83,1.41),(.81,-.66,1.71),(.81,-.64,1.84)]
tube('Snorkel | formed duct',duct,.043,plastic,c,segments=12)
p=wing.ray_cast(Vector((1.3,-1.31,1.055)),Vector((-1,0,0)),.7)[0]
if p is None:p=wing.find_nearest(Vector((.91,-1.31,1.055)))[0]
tube('Snorkel | wing adapter',[p,Vector((.958,-1.31,1.075))],.048,plastic,c,mount=True)
contacts.append(dict(part='snorkel',point=list(p),surface='frontPanel'))
for anchor in [Vector(duct[4]),Vector(duct[5])]:
 p=pillar.find_nearest(anchor)[0]
 tube('Snorkel | pillar bracket',[p,anchor],.012,black,c,mount=True)
 box('Snorkel | pillar pad',p,(.023,.045,.065),rubber,c,.003,True)
 bolt('Snorkel | bracket screw',p+Vector((.015,0,0)),(1,0,0),c);contacts.append(dict(part='snorkel',point=list(p),surface='pillars'))
# Intake shell has an open front with real louvres and a recessed rear wall.
for name,p,size in [('top',(.81,-.65,1.936),(.166,.135,.018)),('bottom',(.81,-.65,1.826),(.166,.135,.018)),('left',(.735,-.65,1.881),(.016,.135,.11)),('right',(.885,-.65,1.881),(.016,.135,.11)),('back',(.81,-.59,1.881),(.15,.015,.11))]:box('Snorkel | head '+name,p,size,plastic,c,.008)
for z in [1.85,1.872,1.894,1.916]:box('Snorkel | intake louvre',(.81,-.714,z),(.14,.013,.005),black,c,.001)
for x in [.775,.845]:box('Snorkel | grille brace',(x,-.716,1.881),(.005,.011,.092),black,c,.001)
# Topology + source fit evidence, excluding intentional attachment interfaces.
bpy.context.view_layer.update();bt=tree(body);checks=[]
for c in parts:
 for o in c.objects:
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data)
  checks.append(dict(name=o.name+' closed',passed=all(e.is_manifold for e in bm.edges) and all(f.calc_area()>1e-12 for f in bm.faces)));bm.free()
  if not o.get('mount_contact'):checks.append(dict(name=o.name+' body clearance',passed=not tree([o]).overlap(bt)))
 wf.seal(c)
for c in parts:sc.collection.children.unlink(c);c.use_fake_user=True
bpy.data.libraries.write(str(OUT/'GT_RangeRover_Equipment.blend'),set(parts),fake_user=True)
for c in parts:sc.collection.children.link(c)
# Reuse the already reviewed body and wheels as context; never overwrite either source.
for o in list(sc.objects):
 if o in dst.objects:
  if o.type!='MESH' or o.name.lower().startswith('wheel'):o.hide_render=True;continue
  o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(wf.material('Context | green',(.105,.18,.115),.58) if not any(n in o.name.lower() for n in ['bumper','interior','pillar']) else black)
with bpy.data.libraries.load(str(ROOT/'Art/Export/VehicleTools/rr-wheels-tyres-v04/GT_RangeRover_Wheel_Components.blend')) as (src,wheels):wheels.collections=['RIM | Pressed Steel','TYRE | All Terrain']
spec=json.loads((ROOT/'Art/Export/VehicleTools/rr-wheels-tyres-v04/spec.json').read_text())
for centre in spec['measured_hub_centres_m']:
 for c in wheels.collections:
  o=bpy.data.objects.new('Context wheel',None);sc.collection.objects.link(o);o.instance_type='COLLECTION';o.instance_collection=c;o.location=centre
  if centre[0]<0:o.rotation_euler.z=math.pi
sc.unit_settings.system='METRIC';sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=10
sc.render.resolution_x=1500;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Studio');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.65,.61,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.6
for name,loc,power,size in [('Key',(3,-5,7),1600,5),('Fill',(-4,-2,3),1000,4),('Rim',(2,4,5),1800,4)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.008));bpy.context.object.data.materials.append(wf.material('Studio floor',(.52,.51,.47),.9))
d=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',d);sc.collection.objects.link(cam);sc.camera=cam;d.type='ORTHO'
def render(name,loc,target,scale):
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=scale;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
for args in [('01-fitted-front',(6,-8,4),(0,0,1),5.6),('02-fitted-rear',(6,8,4),(0,0,1),5.6),('03-side',(7,0,1.2),(0,0,1.2),5.4),('04-front',(0,-8,1.15),(0,0,1.15),3),('05-top',(0,0,8),(0,0,0),5.4),('06-roof-mount',(3,-2,3),(.65,.2,1.84),1.35),('07-intake-detail',(3,-3,2.2),(.84,-.85,1.53),1.18),('08-bar-mount',(2,-4,1),(.46,-2.33,.58),1.1)]:render(*args)
cam.location=(6,-8,4);cam.rotation_euler=(Vector((0,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=5.6
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RangeRover_Equipment_Fit.blend'))
shutil.copy2(REF,OUT/'approved-reference.png');shutil.copy2(__file__,OUT/'build_source.py')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
(OUT/'verification.json').write_text(json.dumps(dict(ok=all(r['passed'] for r in checks),checks=checks,contacts=contacts,source_sha256=source_hash,scope='Raw topology and static body clearance of non-mount meshes; deliberate mount contacts recorded. Further wheel/door sweep and runtime validation required.'),indent=2))
print('EQUIPMENT_BUILD',[(r['name']) for r in checks if not r['passed']],flush=True)
