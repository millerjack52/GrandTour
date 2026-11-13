"""Local saved-assembly repair: arch-conforming jambs and coherent rear interfaces."""
import bpy,bmesh,math,json,hashlib,ast,shutil,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from graphic_adventure_coverage_v02 import tree
BASE=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-assembly-v02')
OUT=BASE.parent/'graphic-adventure-assembly-v03';OUT.mkdir(exist_ok=True)
SOURCE=BASE/'GraphicAdventure_Assembly.blend'
sourcehash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));S=4.6
root=bpy.data.objects['GA | Assembly'];active=[]
cols={n:bpy.data.collections[n] for n in ['Panels','Cabin frames','Glazing','Front module','Rear module','Hardware','Underbody','Wheels','Roof equipment']}
M={n:bpy.data.materials.get(n) or bpy.data.materials['Body'] for n in ['Body','Panel','Glass','Rubber','Metal','Light','Inner','Cargo','Strap']}
for file,names in [(BASE.parent/'defender-retopology-v01/retopologize_defender.py',{'interp','make','grid','box','tube'}),(Path(__file__).with_name('build_graphic_adventure_v02.py'),{'sx','tail','orient','panel'})]:
 for node in ast.parse(file.read_text()).body:
  if isinstance(node,ast.FunctionDef) and node.name in names:exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'))
def current():return [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('RET |')]
def fingerprint(o):
 return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],tuple(tuple(r) for r in o.matrix_world))).encode()).hexdigest()
original={o.name:fingerprint(o) for o in current()};removed=[]
def remove(name):
 o=bpy.data.objects['RET | '+name];removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
ARCH=[(.155,.134),(.180,.200),(.199,.219),(.316,.219),(.346,.191),(.371,.136)]

def intrusion():
 # Rays target the empty space immediately inside the arch lip, not the inner tub.
 result={}
 for side,sign in [('L',1),('R',-1)]:
  t=tree([bpy.data.objects['RET | '+side+' Rear door jamb'],bpy.data.objects['RET | '+side+' rocker']]);hits=[]
  for i in range(70):
   y=.160+i*(.253-.160)/69;top=interp(y,ARCH)-.002
   for j in range(30):
    z=.140+j*(top-.140)/29
    if top<.14:continue
    p=t.ray_cast(Vector((sign*.24,y,z))*S,Vector((-sign,0,0)),.040*S)[0]
    if p is not None:hits.append([y,z])
  result[side]={'samples':2100,'intrusions':len(hits),'positions':hits}
 return result

def rear_interface_report():
 # Compare the actual mesh edges, not a duplicate of the profile equation.
 errors={}
 for side in ['L','R']:
  q=bpy.data.objects['RET | '+side+' rear quarter']
  pts=[q.matrix_world@v.co/S for v in q.data.vertices]
  errors[side]=[]
  for z in [.187,.190,.22,.25,.26,.27,.29]:
   vv=[p for p in pts if abs(p.z-z)<1e-6];qy=max(p.y for p in vv)
   sections=[]
   for name in ['bottom','outer','top']:
    o=bpy.data.objects['RET | '+side+' rear lamp aperture '+name]
    verts=[o.matrix_world@v.co/S for v in o.data.vertices]
    # Every patch is a grid of two vertices per height; select exterior edge.
    edge=sorted([(verts[i].z,verts[i].y) for i in range(1,len(verts),2)])
    if edge[0][0]-1e-7<=z<=edge[-1][0]+1e-7:sections.append(abs(interp(z,edge)-qy)*S)
   errors[side].append({'z':z,'gap_m':max(sections,default=0)})
 return errors

def rear_overlap():
 # Projected base faces of the apron and lamp-bottom patches must not overlap.
 a=bpy.data.objects['RET | Rear lower apron'];zs=[(a.matrix_world@v.co).z/S for v in a.data.vertices]
 result={}
 for side in ['L','R']:
  o=bpy.data.objects['RET | '+side+' rear lamp aperture bottom']
  zv=[(o.matrix_world@v.co).z/S for v in o.data.vertices]
  result[side]=max(0,min(max(zs),max(zv))-max(min(zs),min(zv)))*S
 return result

before={'jamb_intrusion':intrusion(),'rear_corner_gaps':rear_interface_report(),'apron_overlap_height_m':rear_overlap()}
assert sum(r['intrusions'] for r in before['jamb_intrusion'].values())>0
assert max(r['gap_m'] for rs in before['rear_corner_gaps'].values() for r in rs)>.01
assert min(before['apron_overlap_height_m'].values())>.1

# Actual rear-door perimeter, including EACH arch shoulder; inset strips stay on the door side.
poly=[(.036,.139),(.138,.139),(.162,.221),(.188,.239),(.254,.239),(.254,.301),(.208,.424),(.036,.424),(.036,.301)]
stations=[.139,.15,.18,.187,.190,.191,.202,.205,.22,.238,.25,.251,.26,.265,.27,.286,.29,.301,.424]
def offset_loop(points,d):
 out=[]
 for i,p in enumerate(points):
  p=Vector(p);a=(p-Vector(points[i-1])).normalized();b=(Vector(points[(i+1)%len(points)])-p).normalized()
  na=Vector((-a.y,a.x));nb=Vector((-b.y,b.x));bis=na+nb
  out.append(p+bis*(d/max(1e-6,bis.dot(na))))
 return out
for side,sign in [('L',1),('R',-1)]:
 remove(side+' rocker')
 box(side+' rocker',(sign*.207,(-.1785+.138)/2,.134),(.023,.138+.1785,.019),'Underbody','Inner',.005)
 remove(side+' Rear door jamb')
 outside=offset_loop(poly,-.001);inside=offset_loop(poly,.008)
 oa=[];ia=[]
 for i in range(len(poly)):
  a,b=outside[i],outside[(i+1)%len(poly)];c,d=inside[i],inside[(i+1)%len(poly)]
  ts={0,.25,.5,.75}
  for p,q in [(a,b),(c,d)]:
   if abs(q.y-p.y)>1e-8:ts.update((z-p.y)/(q.y-p.y) for z in stations if 0<(z-p.y)/(q.y-p.y)<1)
  # Offset edges can cross a height station at numerically identical parameters.
  # Quantize the sampling parameter to avoid zero-area slivers after float32 storage.
  for t in sorted({round(t,5) for t in ts if t<.99999}):oa.append(a.lerp(b,t));ia.append(c.lerp(d,t))
 rows=[[(sign*(sx(z)-dep),y,z) for y,z in pts+pts[:1]] for pts,dep in [(oa,.0035),(ia,.0035),(ia,.014)]]
 o=panel(side+' Rear door jamb',rows,(sign,0,0),group='Cabin frames',mat='Inner',thick=.008)
 o['interface']='Bottom edge follows rear arch shoulder; mitered offsets into door material, checked against arch aperture keep-out.'

# Rear skins partition one surface. Apron owns all the area below .190;
# lamp corners own only the area beside the tailgate above .190.
for side,sign in [('L',1),('R',-1)]:
 for name,lo,hi,xrange in [('bottom',.190,.191,None),('top',.251,.301,None),('inner',.191,.251,(.167,.174)),('outer',.191,.251,(.214,None))]:
  remove(side+' rear lamp aperture '+name)
  zs=sorted(set([lo,hi]+[z for z in stations if lo<z<hi]));rows=[]
  for z in zs:
   a,b=(.167,sx(z)) if xrange is None else (xrange[0],xrange[1] if xrange[1] is not None else sx(z))
   rows.append([(sign*x,tail(z),z) for x in [a,b]])
  o=panel(side+' rear lamp aperture '+name,rows,(0,1,0),group='Rear module',thick=.012)
  o['interface']='Rear quarter and lamp surround share width and depth breakpoints; no apron overlap.'
remove('Rear lower apron')
panel('Rear lower apron',[[(x,tail(z),z) for x in [-sx(z),-.167,0,.167,sx(z)]] for z in [.139,.15,.18,.187,.190]],(0,1,0),group='Rear module',thick=.012)
remove('Lower tailgate')
panel('Lower tailgate',[[(x,tail(z),z) for x in [-.167,-.1,0,.1,.167]] for z in [.190,.22,.25,.26,.27,.286,.29,.301]],(0,1,0),group='Rear module',thick=.016,parent=bpy.data.objects['GA | Lower tailgate'])

# Planar top/caps and a continuous tucked underside. The old warped cap/ngon
# produced a pinched outer tip; the new top covers the lower-body transition.
remove('Rear bumper')
plan=[(-.224,.459),(-.224,.491),(-.218,.499),(-.170,.501),(.170,.501),(.218,.499),(.224,.491),(.224,.459),(.215,.450),(-.215,.450)]
n=len(plan)
vv=[(x,y-.006,.143) for x,y in plan]+[(x,y,.1905) for x,y in plan]
o=make('Rear bumper',vv,[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'Rear module','Inner',bevel=.007)
o['interface']='Level top covers rear body return; restrained end chamfers, planar caps, continuous lower tuck.'
bpy.context.view_layer.update()
after={'jamb_intrusion':intrusion(),'rear_corner_gaps':rear_interface_report(),'apron_overlap_height_m':rear_overlap()}
assert sum(r['intrusions'] for r in after['jamb_intrusion'].values())==0,after['jamb_intrusion']
assert max(r['gap_m'] for rs in after['rear_corner_gaps'].values() for r in rs)<.00001,after['rear_corner_gaps']
assert max(after['apron_overlap_height_m'].values())<.000001
manifest={'base':str(SOURCE),'base_sha256':sourcehash,'removed_and_replaced':removed,'added':[o.name for o in active],'unchanged':[],'changed_existing':[],'regressions_before':before,'regressions_after':after}
for o in current():
 if o.name in original:manifest['unchanged' if fingerprint(o)==original[o.name] else 'changed_existing'].append(o.name)
assert set(manifest['changed_existing']).issubset(removed)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sourcehash
(OUT/'repair-manifest.json').write_text(json.dumps(manifest,indent=2))
shutil.copy2(BASE/'vehicle-spec.json',OUT/'vehicle-spec.json')

sc=bpy.context.scene;cam=sc.camera
sc.render.resolution_x=1400;sc.render.resolution_y=1050
def render(name,pos,target,scale):
 cam.location=Vector(pos)*S;cam.rotation_euler=(Vector(target)*S-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('rear-arch-left',(1,.29,.11),(.20,.235,.235),1.7)
render('rear-arch-right',(-1,.29,.11),(-.20,.235,.235),1.7)
render('rear-bumper-profile',(1,.44,.23),(.20,.44,.23),1.3)
render('rear-corner',(.9,1,.17),(.14,.40,.25),2.2)
render('rear',(0,2,.25),(0,.40,.25),2.8)
render('rear-quarter',(-1,1.3,.60),(0,.12,.27),6.1)
render('side',(2,0,.26),(0,0,.26),6.1)
render('front',(0,-2,.28),(0,0,.28),4.0)
render('top',(0,0,2),(0,0,.25),7.4)
for o in cols['Wheels'].objects:o.hide_render=True
render('rear-arch-wheel-off',(1,.29,.11),(.20,.235,.235),1.7)
for o in cols['Wheels'].objects:o.hide_render=False
render('quarter',(1.5,-1.9,.87),(0,0,.27),6.7)
for o in bpy.context.selected_objects:o.select_set(False)
for o in current():o.hide_set(False);o.select_set(True)
for o in bpy.data.objects:
 if o.type=='EMPTY' and o.name.startswith('GA |'):o.hide_set(False);o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'GraphicAdventure_Assembly.glb'),use_selection=True,export_format='GLB',export_apply=True,export_animations=False,export_extras=True)
for o in bpy.context.selected_objects:o.select_set(False)
for o in bpy.data.objects:
 if o.type in {'EMPTY','CAMERA'}:o.hide_set(True)
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':
   a.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion();a.spaces.active.region_3d.view_distance=7.0;a.spaces.active.region_3d.view_location=(0,0,1.25)
   a.spaces.active.overlay.show_extras=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GraphicAdventure_Assembly.blend'))
print('LOCAL_REPAIR_COMPLETE',len(removed),len(manifest['unchanged']))
