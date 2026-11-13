"""Local radius pass over the saved Panda v02. Keeps unrelated meshes unchanged."""
import bpy,bmesh,ast,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/panda-assembly-v02')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/panda-rounded-v03');OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'delivery-manifest.json').exists():raise RuntimeError('Delivered revision exists; choose a fresh output folder.')
S=3.6
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Panda_Assembly.blend'));sc=bpy.context.scene
def fingerprint(o):
 return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],list(map(list,o.matrix_world)))).encode()).hexdigest()
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
spec=json.loads((SRC/'vehicle-spec.json').read_text());WIDTH=spec['width_profile'];TAIL=spec['tail_profile'];Z=[.135,.15,.19,.22,.27,.303,.322]
cols={c.name:c for c in bpy.data.collections};M={m.name.split(' | ')[-1]:m for m in bpy.data.materials if m.name.startswith('Panda | ')};root=bpy.data.objects['PANDA | assembly'];owned=[];changed=set()
code=ast.parse(Path('C:/GrandTour/Art/VehicleTools/build_panda_assembly.py').read_text())
for node in code.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['parent_keep','make','orient','grid','ring','sidep','interp','sx','tail','hood','strip','aperture','side_surface','box','tube','frontmap']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'panda_helpers','exec'))
base_make=make
def make(name,*args,**kw):
 old=bpy.data.objects.get(name)
 if old:bpy.data.objects.remove(old,do_unlink=True)
 changed.add(name);return base_make(name,*args,**kw)
def rounded(points,trim,closed=False,steps=6):
 pts=[Vector(p) for p in points];result=[]
 for i,p in enumerate(pts):
  if not closed and i in [0,len(pts)-1]:result.append(p);continue
  prev=pts[i-1];nxt=pts[(i+1)%len(pts)];a=p-prev;b=nxt-p
  d=min(trim,a.length*.32,b.length*.32);start=p-a.normalized()*d;end=p+b.normalized()*d
  for j in range(steps+1):
   t=j/steps;result.append((1-t)**2*start+2*t*(1-t)*p+t*t*end)
 return [tuple(p) for p in result]
ARCH={n:rounded(ar,.018,steps=5) for n,ar in spec['arches'].items()}
doorpoly=[(-.184,aperture(-.184))]+[(y,z) for y,z in ARCH['F'] if y>-.184]+[(.13,.135),(.13,.455),(-.041,.455),(-.184,.322)]
def smooth(o,angle=.65):
 for f in o.data.polygons:f.use_smooth=True
 o.data.set_sharp_from_angle(angle=angle)
def window_round(name,outer,inner,normal,parent=None,group='Glazing'):
 # Equal vertex counts retain corner correspondence; outer fixed frame envelope
 # is sampled along original straight edges, inner aperture gets real curvature.
 outer_samples=[]
 for i,p in enumerate(outer):
  p=Vector(p);a=Vector(outer[i-1]);b=Vector(outer[(i+1)%len(outer)])
  for j in range(7):
   t=j/6
   outer_samples.append(tuple(a.lerp(p,.86+t*.28) if t<=.5 else p.lerp(b,(t-.5)*.28)))
 inner_round=rounded(inner,.009,closed=True,steps=6)
 normal=Vector(normal).normalized()
 ring(name+' metal surround',outer_samples,inner_round,group=group,normal=normal,thick=.003,parent=parent)
 center=sum((Vector(p) for p in inner_round),Vector())/len(inner_round)
 glass=[center+(Vector(p)-center)*.966-normal*.0008 for p in inner_round]
 ring(name+' gasket',[Vector(p)-normal*.0007 for p in inner_round],glass,mat='Rubber',normal=normal,thick=.002,parent=parent)
 o=make(name+' glass',glass,[tuple(range(len(glass)))],group='Glazing',mat='Glass',thick=.001,parent=parent);orient(o,normal)

for label,sign in [('L',1),('R',-1)]:
 dp=bpy.data.objects[label+' door hinge']
 for name,a,b,par,top in [(label+' front wing',-.438,-.184,None,hood),(label+' door skin',-.1828,.1288,dp,None),(label+' rear quarter',.1312,.488,None,None)]:
  o=side_surface(name,a,b,sign,par,top);smooth(o,.60)
 strip(label+' full door reveal backing',doorpoly,sign)
 for which,ar in ARCH.items():
  lip=[(sign*(sx(z)+.0003),y,z) for y,z in ar]
  # Rounded bead section rather than one angular chamfer strip.
  bead=[]
  for a in [0,.25,.5,.75,1]:
   bead.append([(sign*(sx(z)+.0003+.0057*math.sin(a*math.pi/2)),y,z+.003*(1-math.cos(a*math.pi/2))) for y,z in ar])
  o=grid(label+which+' arch bead',bead,(sign,0,0),thick=.002);smooth(o)
  outer=bead[-1];inner=[(sign*.142,y,z+.003) for y,z in ar]
  o=grid(label+which+' wheelhouse roof',[outer,inner],(0,0,-1),group='Underbody',mat='Inner',thick=.002);smooth(o)
  cap=inner+[(sign*.142,ar[-1][0],.132),(sign*.142,ar[0][0],.132)]
  o=make(label+which+' inner wheelhouse wall',cap,[tuple(range(len(cap)))],group='Underbody',mat='Inner',thick=.002);orient(o,(sign,0,0))
 window_round(label+' door',sidep(sign,[(-.1828,.322),(-.040,.455),(.1288,.455),(.1288,.322)]),sidep(sign,[(-.163,.335),(-.032,.444),(.115,.444),(.115,.335)]),(sign,0,0),dp,'Doors')
 window_round(label+' quarter',sidep(sign,[(.1312,.322),(.1312,.455),(.394,.455),(.474,.322)]),sidep(sign,[(.149,.335),(.149,.443),(.382,.443),(.450,.335)]),(sign,0,0))
window_round('Windscreen',[frontmap(x,z) for x,z in [(-.213,.322),(.213,.322),(.179,.455),(-.179,.455)]],[frontmap(x,z) for x,z in [(-.197,.334),(.197,.334),(.166,.444),(-.166,.444)]],(0,-.68,.73))
tp=bpy.data.objects['Tailgate upper hinge']
window_round('Tailgate upper',[(-.1818,tail(.322),.322),(.1818,tail(.322),.322),(.179,tail(.455),.455),(-.179,tail(.455),.455)],[(-.166,tail(.335),.335),(.166,tail(.335),.335),(.163,tail(.443),.443),(-.163,tail(.443),.443)],(0,.85,.52),tp,'Tailgate')

# Crown sampled densely enough to form smooth rolled shoulders, with the entire
# original mating perimeter retained. This does not subdivide/shrink the whole car.
bp=bpy.data.objects['Bonnet hinge'];ys=sorted(set([-.438,-.435,-.39,-.32,-.26,-.197]+[-.438+i*.241/24 for i in range(25)]));ts=[-1+i/16 for i in range(33)]
def hp(t,y):
 z=hood(y);u=(y+.438)/.241
 crown=.0075*max(0,math.sin(math.pi*u))**.55*max(0,1-abs(t)**6)**.55
 return(t*(sx(z)-.0012),y,z+crown)
o=grid('Bonnet pressing',[[hp(t,y) for t in ts] for y in ys],(0,0,1),group='Bonnet',thick=.003,parent=bp);smooth(o)
# Refitted vent positions follow new bonnet curvature, keeping them seated.
for o in list(sc.objects):
 if o.name.startswith('Bonnet vent '):
  changed.add(o.name)
  for v in o.data.vertices:
   w=o.matrix_world@v.co;p=w/S;t=p.x/(sx(hood(p.y))-.0012)
   old=.005*math.sin(math.pi*(p.y+.438)/.243)*max(0,1-t*t)
   new=hp(t,p.y)[2]-hood(p.y);w.z+=(new-old)*S;v.co=o.matrix_world.inverted()@w
roofys=[-.041+i*.435/24 for i in range(25)]
o=grid('Roof cap',[[ (t*.179,y,.455+.016*max(0,1-abs(t)**6)**.6*max(0,math.sin(math.pi*(y+.041)/.435))**.65) for t in ts] for y in roofys],(0,0,1),thick=.003);smooth(o)

# Rebuild thick bumper corner radii with six segments, retaining their mounting
# envelope and nominal width; unlike thin panel bevels these alter the silhouette.
for name,y in [('Front',-.450),('Rear',.486)]:
 for suffix,c,d,r in [(' bumper',(0,y,.181),(.487,.051,.048),.011),(' lower valance',(0,y-.001 if name=='Front' else y+.001,.147),(.456,.043,.033),.007)]:
  o=box(name+suffix,c,d,mat='Rubber',bevel=r)
  o.modifiers[-1].segments=6;smooth(o)
  m=o.modifiers.new('Weighted broad faces','WEIGHTED_NORMAL');m.keep_sharp=True
# Rounded accessory tubes use the same mounting endpoints, with bends softened.
for name,points,r,group in [('Bull bar hoop',[(-.12,-.485,.16),(-.12,-.489,.222),(-.108,-.489,.235),(.108,-.489,.235),(.12,-.489,.222),(.12,-.485,.16)],.008,'Front equipment'),('Left snorkel',[(.226,-.207,.315),(.237,-.193,.320),(.235,-.169,.337),(.192,-.047,.452),(.191,-.031,.475)],.009,'Roof and snorkel')]:
 tube(name,rounded(points,.013,steps=5),r,group=group,segments=16)

print('Local rounded modules built',flush=True)
bpy.ops.object.select_all(action='DESELECT')
for o in owned:
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.validate();o['component_group']=o.users_collection[0].name
 o.select_set(False)
for o in owned:o.select_set(True)
bpy.context.view_layer.objects.active=owned[0];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT');bpy.ops.object.select_all(action='DESELECT')
# Shared analytic surface normals keep separate side panels visually continuous.
# The solidified returns retain their own face normals, rather than pulling the
# exterior highlights around every panel seam.
for label,sign in [('L',1),('R',-1)]:
 for part in [' front wing',' door skin',' rear quarter']:
  o=bpy.data.objects[label+part];me=o.data;normals=[None]*len(me.loops)
  for face in me.polygons:
   exterior=face.normal.x*sign>.5 and all(abs(abs(me.vertices[i].co.x)/S-sx(me.vertices[i].co.z/S))<.00001 for i in face.vertices)
   face.use_smooth=exterior
   for li in face.loop_indices:
    z=me.vertices[me.loops[li].vertex_index].co.z/S
    slope=(sx(z+.004)-sx(z-.004))/.008
    normals[li]=tuple(Vector((sign,0,-slope)).normalized()) if exterior else tuple(face.normal)
  me.normals_split_custom_set(normals)
preserved=[];unexpected=[]
for n,h in before.items():
 if n not in changed:
  o=bpy.data.objects.get(n)
  (preserved if o and fingerprint(o)==h else unexpected).append(n)
assert not unexpected,unexpected
spec['arches']=ARCH;spec['door_outline']=doorpoly;spec['style_revision']='Selective rounded form transitions: aperture radii, rolled arch section, crown surfaces and bumper corners.'
(OUT/'vehicle-spec.json').write_text(json.dumps(spec,indent=2))
(OUT/'repair-manifest.json').write_text(json.dumps({'source':str(SRC/'Panda_Assembly.blend'),'source_sha256':hashlib.sha256((SRC/'Panda_Assembly.blend').read_bytes()).hexdigest(),'changed':sorted(changed),'preserved_geometry_and_transforms':len(preserved),'unexpected_changes':unexpected,'notes':['Wheels, centres and diameter retained exactly.','Outer window frame envelope retained, aperture corners rounded geometrically.','Body/arch/bead/liner/jamb share the same new rounded aperture.','Bonnet and roof mating perimeters retained; broad crowns receive more samples and curved shoulders.','No global subdivision, mesh smoothing or scale adjustment.']},indent=2))
for o in sc.objects:o.select_set(False)
for o in sc.objects:
 if o.type in ['MESH','EMPTY'] and not o.name.startswith('SOURCE'):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Panda_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Panda_Assembly.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.object.select_all(action='DESELECT')
cam=sc.camera;center=Vector((0,0,.268))*S
for name,pos,scale in [('side',(3,0,.268),1.20),('front',(0,-3,.268),.86),('top',(0,0,3),1.22),('quarter',(1.7,-2.7,1.35),1.28),('rear-quarter',(1.8,2.6,1.1),1.28)]:
 cam.location=Vector(pos)*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*S;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=Vector((1.7,-2.7,1.35))*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.28*S
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda_Assembly.blend'))
print('Preserved',len(preserved),'changed',len(changed),flush=True)
