"""Local nose-corner wrap and bonnet/header interface repair from saved v04."""
import bpy,bmesh,math,json,hashlib,ast,shutil,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from graphic_adventure_coverage_v04 import tree
BASE=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-assembly-v04')
OUT=BASE.parent/'graphic-adventure-assembly-v05';OUT.mkdir(exist_ok=True)
SOURCE=BASE/'GraphicAdventure_Assembly.blend';sourcehash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));S=4.6
root=bpy.data.objects['GA | Assembly'];active=[]
cols={n:bpy.data.collections[n] for n in ['Front module','Panels','Hardware']}
M={n:bpy.data.materials[n] for n in ['Body','Inner','Metal']}
for file,names in [(BASE.parent/'defender-retopology-v01/retopologize_defender.py',{'interp','make','grid','box'}),(Path(__file__).with_name('build_graphic_adventure_v02.py'),{'sx','orient','panel'}),(Path(__file__).with_name('repair_graphic_adventure_v03.py'),{'current','fingerprint'})]:
 for node in ast.parse(file.read_text()).body:
  if isinstance(node,ast.FunctionDef) and node.name in names:exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'))
def nose(x):return -.451+.010*(abs(x)/.220)**4
def corner_coverage():
 t=tree(current());miss=[];count=0
 for side,sign in [('L',1),('R',-1)]:
  for i in range(60):
   z=.189+i*(.257-.189)/59;x=sx(z);a=nose(x)
   for j in range(1,10):
    y=a+(-.438-a)*j/10;count+=1
    if t.ray_cast(Vector((sign*(x+.012),y,z))*S,Vector((-sign,0,0)),.018*S)[0] is None:miss.append({'side':side,'y':y,'z':z})
 return {'samples':count,'uncovered':len(miss),'misses':miss}
original={o.name:fingerprint(o) for o in current()};removed=[]
def remove(n):
 o=bpy.data.objects['RET | '+n];removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
before=corner_coverage()
sc=bpy.context.scene;cam=sc.camera;sc.render.resolution_x=1400;sc.render.resolution_y=1050
def render(name,pos,target,scale):
 cam.location=Vector(pos)*S;cam.rotation_euler=(Vector(target)*S-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('corner-before',(.8,-1,.52),(.191,-.432,.263),1.0)
render('corner-low-before',(.65,-1,.10),(.173,-.434,.245),1.25)

# One folded skin per corner: shared nose/wing contact, no exposed box ends.
for side,sign in [('L',1),('R',-1)]:
 remove(side+' nose corner')
 rows=[]
 for z in [.187,.190,.202,.22,.25,.258]:
  xs=[.187,.195,.212,sx(z)]
  rows.append([(sign*x,nose(x),z) for x in xs]+[(sign*sx(z),-.438,z)])
 o=panel(side+' nose corner',rows,(sign,-1,0),group='Front module',thick=.010)
 o['interface']='Front sheet matches headlamp edge; folded return reaches exact front-wing boundary at y=-.438.'

# Replace the floating straight box trim with a continuous folded header.
# Its lower face seats on the lamp panel; upper flange extends beneath the bonnet return.
remove('Grille edge 0.259')
us=[-1,-.98,-.95,-.88,-.64,-.35,0,.35,.64,.88,.95,.98,1]
xs=sorted(set([u*.220 for u in us]+[-.212,-.195,-.187,-.126,.126,.187,.195,.212]))
rows=[[(x,nose(x)-.0003,.258) for x in xs],[(x,nose(x)-.0003,.259) for x in xs],[(x,nose(x)+.003,.259) for x in xs]]
panel('Grille edge 0.259',rows,(0,-1,1),group='Front module',thick=.004)
# Vertical grille edging previously projected 27 mm above the upper trim.
# Reuse its exact swept nose surface, shortening only the projecting vertices.
for label in ['Grille border -0.125','Grille border 0.125']:
 o=bpy.data.objects['RET | '+label]
 for v in o.data.vertices:
  if v.co.z/S>.259:v.co.z=.259*S
 o.data.update();removed.append(o.name)
# The box behind the grille must also end beneath the shared header.
o=bpy.data.objects['RET | Grille recess']
for v in o.data.vertices:
 if v.co.z/S>.259:v.co.z=.259*S
o.data.update();removed.append(o.name)
# Seat the inboard bonnet flanges below the actual bonnet surface. At the low
# front corner the previous constant-height flange emerged through the pressing.
hood_tree=tree([bpy.data.objects['RET | Bonnet main pressing']])
for sign in [-1,1]:
 o=bpy.data.objects['RET | Bonnet seating flange '+str(sign)]
 for v in o.data.vertices:
  p=o.matrix_world@v.co
  if p.z/S<.260:continue
  hit=hood_tree.ray_cast(Vector((p.x,p.y,.4*S)),Vector((0,0,-1)),.20*S)[0]
  assert hit is not None,tuple(p/S)
  p.z=min(p.z,hit.z-.003*S);v.co=o.matrix_world.inverted()@p
 o.data.update();removed.append(o.name)
bpy.context.view_layer.update();after=corner_coverage()
(OUT/'front-corner-check.json').write_text(json.dumps({'before':before,'after':after},indent=2))
assert before['uncovered']>0,'Corner check must detect previous open return'
assert after['uncovered']==0,after['misses'][:8]
unchanged=[o.name for o in current() if o.name in original and fingerprint(o)==original[o.name]]
changed=[o.name for o in current() if o.name in original and fingerprint(o)!=original[o.name]]
assert set(changed)==set(removed)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sourcehash
(OUT/'repair-manifest.json').write_text(json.dumps({'base':str(SOURCE),'base_sha256':sourcehash,'changed':changed,'unchanged':unchanged,'before_corner_misses':before['uncovered'],'after_corner_misses':after['uncovered']},indent=2))
shutil.copy2(BASE/'vehicle-spec.json',OUT/'vehicle-spec.json')
render('corner-after',(.8,-1,.52),(.191,-.432,.263),1.0)
render('corner-low-after',(.65,-1,.10),(.173,-.434,.245),1.25)
render('corner-opposite',(-.8,-1,.52),(-.191,-.432,.263),1.0)
render('corner-side',(1,-.420,.275),(.215,-.420,.255),.8)
render('front',(0,-2,.28),(0,0,.28),4)
render('side',(2,0,.26),(0,0,.26),6.1)
render('top',(0,0,2),(0,0,.25),7.4)
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
print('REPAIR',len(changed),len(unchanged),'CORNER',before['uncovered'],after['uncovered'])
