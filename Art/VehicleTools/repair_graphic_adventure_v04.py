"""Repair rear-door reveal backing locally; preserve the saved v03 exterior."""
import bpy,bmesh,math,json,hashlib,ast,shutil,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from graphic_adventure_coverage_v03 import tree
BASE=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-assembly-v03')
OUT=BASE.parent/'graphic-adventure-assembly-v04';OUT.mkdir(exist_ok=True)
SOURCE=BASE/'GraphicAdventure_Assembly.blend';sourcehash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));S=4.6
root=bpy.data.objects['GA | Assembly'];active=[];cols={n:bpy.data.collections[n] for n in ['Cabin frames']}
M={n:bpy.data.materials[n] for n in ['Body','Inner']}
for file,names in [(BASE.parent/'defender-retopology-v01/retopologize_defender.py',{'interp','make','grid'}),(Path(__file__).with_name('build_graphic_adventure_v02.py'),{'sx','orient','panel'}),(Path(__file__).with_name('repair_graphic_adventure_v03.py'),{'current','fingerprint','offset_loop','intrusion'})]:
 for node in ast.parse(file.read_text()).body:
  if isinstance(node,ast.FunctionDef) and node.name in names:exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'))
ARCH=[(.155,.134),(.180,.200),(.199,.219),(.316,.219),(.346,.191),(.371,.136)]

def seam_coverage():
 t=tree(current());misses=[];samples=0
 for side,sign in [('L',1),('R',-1)]:
  for j in range(70):
   z=.2395+j*(.3005-.2395)/69
   for y in [.25425,.2545,.255,.2555,.25575]:
    for dy in [-.7,0,.7]:
     for dz in [-.4,0,.4]:
      samples+=1;origin=Vector((sign*(sx(z)+.010),y-.010*dy,z-.010*dz))*S
      d=Vector((-sign,dy,dz)).normalized()
      if t.ray_cast(origin,d,.035*S)[0] is None:misses.append({'side':side,'y':y,'z':z,'dy':dy,'dz':dz})
 return {'samples':samples,'uncovered':len(misses),'misses':misses}

original={o.name:fingerprint(o) for o in current()}
before=seam_coverage();assert before['uncovered']>0,'Negative control must detect reported v03 gap'
sc=bpy.context.scene;cam=sc.camera;sc.render.resolution_x=1400;sc.render.resolution_y=1050
def render(name,pos,target,scale):
 cam.location=Vector(pos)*S;cam.rotation_euler=(Vector(target)*S-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('door-before',(1,.40,.35),(.214,.251,.272),.58)

poly=[(.036,.139),(.138,.139),(.162,.221),(.188,.239),(.254,.239),(.254,.301),(.208,.424),(.036,.424),(.036,.301)]
stations=[.139,.15,.18,.187,.190,.191,.202,.205,.22,.238,.25,.251,.26,.265,.27,.286,.29,.301,.424]
replaced=[]
for side,sign in [('L',1),('R',-1)]:
 name=side+' Rear door jamb';old=bpy.data.objects['RET | '+name];replaced.append(old.name);bpy.data.objects.remove(old,do_unlink=True)
 # Wider hidden flange bridges the full reveal and extends under the fixed quarter.
 # Keep the arch-following contour and inboard wall from v03.
 outside=offset_loop(poly,-.005);inside=offset_loop(poly,.008);oa=[];ia=[]
 for i in range(len(poly)):
  a,b=outside[i],outside[(i+1)%len(poly)];c,d=inside[i],inside[(i+1)%len(poly)];ts={0,.25,.5,.75}
  for p,q in [(a,b),(c,d)]:
   if abs(q.y-p.y)>1e-8:ts.update((z-p.y)/(q.y-p.y) for z in stations if 0<(z-p.y)/(q.y-p.y)<1)
  for t in sorted({round(t,5) for t in ts if t<.99999}):oa.append(a.lerp(b,t));ia.append(c.lerp(d,t))
 rows=[[(sign*(sx(z)-dep),y,z) for y,z in pts+pts[:1]] for pts,dep in [(oa,.0035),(ia,.0035),(ia,.014)]]
 o=panel(name,rows,(sign,0,0),group='Cabin frames',mat='Inner',thick=.008)
 o['interface']='Arch-conforming jamb; outer hidden flange overlaps fixed quarter behind complete door reveal, with multi-angle coverage check.'
bpy.context.view_layer.update();after=seam_coverage();arch=intrusion()
(OUT/'door-seam-check.json').write_text(json.dumps({'before':before,'after':after,'arch_keepout':arch},indent=2))
assert after['uncovered']==0,after['misses'][:10]
assert sum(v['intrusions'] for v in arch.values())==0
unchanged=[o.name for o in current() if o.name in original and fingerprint(o)==original[o.name]]
changed=[o.name for o in current() if o.name in original and fingerprint(o)!=original[o.name]]
assert set(changed)==set(replaced)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sourcehash
(OUT/'repair-manifest.json').write_text(json.dumps({'base':str(SOURCE),'base_sha256':sourcehash,'replaced':replaced,'unchanged':unchanged,'before_seam_misses':before['uncovered'],'after_seam_misses':after['uncovered']},indent=2))
shutil.copy2(BASE/'vehicle-spec.json',OUT/'vehicle-spec.json')
render('door-after',(1,.40,.35),(.214,.251,.272),.58)
render('door-opposite',(-1,.40,.35),(-.214,.251,.272),.58)
render('door-forward-angle',(1,.02,.22),(.214,.251,.272),.68)
render('rear-arch-left',(1,.29,.11),(.20,.235,.235),1.7)
render('side',(2,0,.26),(0,0,.26),6.1)
render('quarter',(1.5,-1.9,.87),(0,0,.27),6.7)
for o in bpy.context.selected_objects:o.select_set(False)
for o in current():o.hide_set(False);o.select_set(True)
for o in bpy.data.objects:
 if o.type=='EMPTY' and o.name.startswith('GA |'):o.hide_set(False);o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'GraphicAdventure_Assembly.glb'),use_selection=True,export_format='GLB',export_apply=True,export_animations=False,export_extras=True)
for o in bpy.context.selected_objects:o.select_set(False)
for o in bpy.data.objects:
 if o.type in {'EMPTY','CAMERA'}:o.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GraphicAdventure_Assembly.blend'))
print('REPAIR',len(changed),len(unchanged),'SEAM',before['uncovered'],after['uncovered'])
