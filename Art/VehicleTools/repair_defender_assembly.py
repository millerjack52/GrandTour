"""Repair the saved retopology assembly without rebuilding its approved external panels."""
import bpy,bmesh,math,json,hashlib,ast,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from defender_coverage import inspect,FRONT,REAR
BASE=Path('C:/GrandTour/Art/Export/VehicleTools/defender-retopology-v01')
OUT=BASE.parent/'defender-assembly-v02';OUT.mkdir(exist_ok=True)
SOURCE=BASE/'Defender_Retopology.blend';sourcehash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));S=4.6
def current():return [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('RET |','Rebuilt')) and not o.hide_render]
before=inspect(current());(OUT/'coverage-before.json').write_text(json.dumps(before,indent=2))
root=bpy.data.objects['DEFENDER | assembly'];active=[];cols={}
for n in ['Panels','Cabin frames','Glazing','Front module','Rear module','Hardware','Underbody']:
 c=bpy.data.collections.new('FIT | '+n);bpy.context.scene.collection.children.link(c);cols[n]=c
M={k:bpy.data.materials['Review | '+k] for k in ['Body','Panel','Glass','Rubber','Metal','Light','Inner']}
# Reuse frozen construction helpers only, never execute the earlier generator.
tree=ast.parse((BASE/'retopologize_defender.py').read_text())
for node in tree.body:
 if isinstance(node,ast.FunctionDef):exec(compile(ast.Module(body=[node],type_ignores=[]),'helpers','exec'))
changed=[];removed=[]
def remove(name):
 o=bpy.data.objects.get('RET | '+name)
 if o:removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
def outward(o,direction):
 bm=bmesh.new();bm.from_mesh(o.data)
 n=sum((f.normal*f.calc_area() for f in bm.faces),Vector())
 if n.dot(Vector(direction))<0:
  bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(o.data);changed.append(o.name+' normals')
 bm.free()
def fingerprint(o):
 return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],tuple(tuple(r) for r in o.matrix_world))).encode()).hexdigest()
original={o.name:fingerprint(o) for o in current()}

# Orient the sheet skins into the exterior so inward thickness does not drift outward.
for o in current():
 if any(m.type=='SOLIDIFY' for m in o.modifiers):
  if o.name.startswith('RET | L '):outward(o,(1,0,0))
  elif o.name.startswith('RET | R '):outward(o,(-1,0,0))
  elif 'Rear door' in o.name:outward(o,(0,1,0))

for side,sign in [('L',1),('R',-1)]:
 # Make the rear face and side terminate on one tapered rear boundary.
 for label in ['rear corner return','rear lower corner return']:remove(side+' '+label)
 for label in ['rear quarter','D pillar','rear fixed face','rear upper corner']:remove(side+' '+label)
 stations=[.144,.145,.147,.162,.18,.203,.226,.235,.246,.262,.263,.272,.274,.294,.295,.30,.307]
 arch=[(.181,.235),(.198,.226),(.225,.246),(.321,.246),(.355,.220),(.378,.144),(.438,.144)]
 ys=[.181,.198,.225,.27,.321,.355,.378,.410,.438]
 verts=[];indices=[];keys={}
 for h in stations:
  row=[]
  for y in ys:
   z=max(h,interp(y,arch));p=(sign*side_x(z),rear_y(z) if y==.438 else y,z)
   key=tuple(round(c,8) for c in p)
   if key not in keys:keys[key]=len(verts);verts.append(p)
   row.append(keys[key])
  indices.append(row)
 faces=[]
 for j in range(len(indices)-1):
  for i in range(len(ys)-1):
   face=list(dict.fromkeys([indices[j][i],indices[j][i+1],indices[j+1][i+1],indices[j+1][i]]))
   if len(face)>=3:faces.append(face)
 o=make(side+' rear quarter',verts,faces,thick=.012,bevel=.002);outward(o,(sign,0,0))
 o=grid(side+' D pillar',[[(sign*side_x(z),y,z) for y in [.422,rear_y(z)]] for z in [.307,.32,.43,.44]],group='Cabin frames',thick=.025,bevel=.003);outward(o,(sign,0,0))
 for label,zs in [('rear fixed face',stations[:-1]+[.30]),('rear upper corner',[.30,.302,.307,.32,.33,.40,.43,.44])]:
  zs=sorted(set(zs))
  o=grid(side+' '+label,[[(sign*x,rear_y(z),z) for x in [.124,.16,side_x(z)]] for z in zs],group='Rear module',thick=.012,bevel=.002);outward(o,(0,1,0))
 # Replace floating half-cylinder liners and detached returns with one connected tub.
 for label,curve,cy,ends in [('Front',FRONT,-.345,(-.480,-.230)),('Rear',REAR,.266,(.150,.390))]:
  remove(side+' '+label+' arch return')
  remove('Wheelhouse roof '+str(sign)+' '+str(cy));remove('Wheelhouse inner wall '+str(sign)+' '+str(cy))
  contour=curve
  # Lip stays fixed; the inboard liner expands around the tyre envelope.
  inner=[(cy+(y-cy)*1.10,.098+(z-.098)*1.10) for y,z in contour]
  rows=[[(sign*.231,y,z) for y,z in contour],[(sign*.216,y,z) for y,z in inner],[(sign*.15,y,z) for y,z in inner]]
  rows.append([(sign*.15,y,.137) for y,z in inner])
  tub=grid(side+' '+label+' connected wheelhouse',rows,group='Underbody',mat='Inner',thick=.007)
  outward(tub,(sign,0,0))
  tub['interface']='Arch lip contour shared by flare, throat and closed inner wall; bottom open for wheel travel'
 # Connect the door skins to their window frames with fitted painted waist rails.
 for label,a,b in [('Front',-.195,.007),('Rear',.026,.180)]:
  par=bpy.data.objects['Hinge | '+side+' '+label+' door']
  rail=grid(side+' '+label+' door waist closure',[[(sign*side_x(z),y,z) for y in [a,a+.003,b-.003,b]] for z in [.307,.309]],mat='Panel',thick=.012,parent=par)
  outward(rail,(sign,0,0))
  for y,s in [(a,1),(b,-1)]:
   patch=make(side+' '+label+' window corner '+str(s),[(sign*side_x(z),yy,z) for yy,z in [(y,.309),(y+s*.003,.309),(y,.312)]],[(0,1,2)],mat='Panel',thick=.012,parent=par)
   outward(patch,(sign,0,0))
  # Fixed aperture jamb: recessed band follows the actual sloping door perimeter.
  poly=[(a,.149),(b,.149 if label=='Front' else .234),(b,.440),(-.135 if label=='Front' else a,.440),(a,.309)]
  if label=='Rear':poly=[(a,.149),(.108,.149),(b,.234),(b,.440),(a,.440)]
  centroid=sum((Vector(p) for p in poly),Vector((0,0)))/len(poly)
  outer=[Vector(p)+(Vector(p)-centroid).normalized()*.004 for p in poly]
  inner=[Vector(p)-(Vector(p)-centroid).normalized()*.006 for p in poly]
  rows=[]
  for contour,depth in [(outer,.0035),(inner,.0035),(inner,.012)]:
   rows.append([(sign*(side_x(z)-depth),y,z) for y,z in contour+contour[:1]])
  jamb=grid(side+' '+label+' aperture jamb',rows,group='Cabin frames',mat='Inner',thick=.006)
  outward(jamb,(sign,0,0))
 # The fixed cargo window and upper pillars have actual rebates behind the joints.
 for a,b,z0,z1,label in [(.199,.438,.306,.311,'cargo waist'),(-.135,.438,.438,.446,'header')]:
  r=grid(side+' '+label+' rebate',[[(sign*(side_x(z)-.0015),y,z) for y in [a,b]] for z in [z0,z1]],group='Cabin frames',thick=.012)
  outward(r,(sign,0,0))
 for y in [.181,.199,.422,.438]:
  r=grid(side+' pillar rebate '+str(y),[[(sign*(side_x(z)-.002),yy,z) for yy in [y-.004,y+.004]] for z in [.306,.32,.43,.443]],group='Cabin frames',thick=.012)
  outward(r,(sign,0,0))
 # Side scuttle closes the wedge between wing, cowl and door leading edge.
 r=grid(side+' scuttle cheek',[[(sign*side_x(z),y,z) for y in [-.205,-.196]] for z in [.146,.262,.272,.280,.294,.307,.313]],thick=.012)
 outward(r,(sign,0,0))
 # Sill upstand physically meets the floor edge and the door's lower reveal.
 r=grid(side+' sill inner upstand',[[(sign*x,y,z) for y in [-.207,.15]] for x,z in [(.214,.140),(.214,.148),(.206,.149)]],group='Underbody',mat='Inner',thick=.006)
 outward(r,(sign,0,0))

# Continuous floor with wheelhouse-sized cutouts; the old tapered notch cut into tyre space.
remove('Full width inner floor')
outline=[(-.207,-.206),(.207,-.206),(.207,.1758),(.150,.1758),(.150,.3661),(.207,.3661),(.207,rear_y(.149)),(-.207,rear_y(.149)),(-.207,.3661),(-.150,.3661),(-.150,.1758),(-.207,.1758)]
make('Full width fitted floor',[(x,y,.149) for x,y in outline],[tuple(range(len(outline)))],group='Underbody',mat='Inner',thick=.025)
# Bulkhead joins front footwell to cowl, avoiding views through the engine/cabin gap.
grid('Fitted firewall',[[(x,y,z) for x in [-.207,-.15,0,.15,.207]] for y,z in [(-.206,.149),(-.206,.28),(-.200,.311)]],group='Underbody',mat='Inner',thick=.012)
# Real roof/header returns, including the strip behind each end of the roof cap.
for end,y,z0,z1 in [('Front',-.14,.437,.447),('Rear',.429,.436,.446)]:
 grid(end+' roof header return',[[(x,y,z) for x in [-.194,-.1,0,.1,.194]] for z in [z0,z1]],group='Cabin frames',thick=.012)
# Rear fixed-body and rear-door horizontal seams receive matching backing returns.
for a,b,par,label in [(-.121,.121,bpy.data.objects['Hinge | Rear door'],'Rear door'),(-.207,-.124,None,'R rear fixed'),(.124,.207,None,'L rear fixed')]:
 for z0,z1 in ([(.309,.310)] if label=='Rear door' else [[.298,.304]]):
  o=grid(label+' waist closure',[[(x,rear_y(z),z) for x in [a,b]] for z in [z0,z1]],group='Rear module',thick=.012,parent=par);outward(o,(0,1,0))
for x in [-.123,.123]:
 o=grid('Rear aperture jamb '+str(x),[[(xx,rear_y(z)-.004,z) for xx in [x-.005,x+.005]] for z in [.154,.18,.30,.44]],group='Rear module',mat='Inner',thick=.008);outward(o,(0,1,0))
grid('Rear sill return',[[(x,rear_y(z),z) for x in [-.207,-.121,0,.121,.207]] for z in [.144,.149,.162]],group='Rear module',mat='Inner',thick=.012)

# Restore a deliberate seam colour for inspection rather than using a white single-colour render.
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sh=sc.display.shading
sh.color_type='MATERIAL';sh.light='STUDIO';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH'
sh.background_type='WORLD';sc.world.color=(.13,.18,.23)
for key in ['Body','Panel','Metal']:M[key].diffuse_color=(.48,.51,.53,1)
M['Inner'].diffuse_color=(.10,.12,.14,1);M['Rubber'].diffuse_color=(.065,.075,.085,1)
sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
cam=sc.camera
def render(name,pos,scale=6.7,target=(0,0,1.1)):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
after=inspect(current());(OUT/'coverage-after.json').write_text(json.dumps(after,indent=2))
manifest={'source':str(SOURCE),'source_sha256':sourcehash,'removed':removed,'normals_corrected':changed,'added':[o.name for o in active],'unchanged':[],'changed_existing':[],'coverage_before':before['uncovered'],'coverage_after':after['uncovered']}
for o in current():
 if o.name in original:manifest['unchanged' if fingerprint(o)==original[o.name] else 'changed_existing'].append(o.name)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sourcehash
(OUT/'repair-manifest.json').write_text(json.dumps(manifest,indent=2))
render('quarter',(7,-9,3.5));render('opposite',(-7,-9,3.5));render('rear-quarter',(-7,9,3.0))
render('side',(9,0,1.15),6.4);render('underside',(5,-7,-4),6.7)
for o in current():
 if o.name.startswith('Rebuilt'):o.hide_render=True
render('wheel-off-left',(9,-3,1.1),6.3);render('wheel-off-right',(-9,3,1.1),6.3)
render('front-wheelhouse',(8,-2.2,1),2.4,target=(.85,-1.58,.70))
render('rear-wheelhouse',(-8,2,1),2.4,target=(-.85,1.22,.70))
for o in bpy.data.objects:
 if o.name.startswith('Rebuilt'):o.hide_render=False
render('scuttle-close',(-7,-5,2.8),2.6,target=(-.8,-.8,1.40))
render('door-seams',(7,1,2.2),3.7,target=(.9,.10,1.4))
render('quarter',(7,-9,3.5))
for o in bpy.context.selected_objects:o.select_set(False)
for o in current():o.hide_set(False);o.select_set(True)
for o in bpy.data.objects:
 if o.type=='EMPTY':o.hide_set(False);o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Defender_Assembly.glb'),use_selection=True,export_format='GLB',export_apply=True,export_animations=False,export_extras=True)
for o in bpy.context.selected_objects:o.select_set(False)
for o in bpy.data.objects:
 if o.type in {'EMPTY','LIGHT','CAMERA'}:o.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Defender_Assembly.blend'))
print('ASSEMBLY_REPAIRED',before['uncovered'],after['uncovered'],len(current()))
