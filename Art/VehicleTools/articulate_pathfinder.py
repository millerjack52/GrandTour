"""Explicit articulation derivative of the reviewed Pathfinder cockpit."""
import bpy,bmesh,math,json,sys,argparse,hashlib,shutil
from pathlib import Path
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Use an empty new revision.')
out.mkdir(parents=True,exist_ok=True)
source=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-cockpit-v03/Pathfinder_Cockpit.blend');sha=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene
if bpy.data.objects.get('GT | Pathfinder controls'):raise RuntimeError('Already articulated; preserve manual work.')
def col(n):c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
rig=col('19 | Pathfinder articulation');doors=col('20 | Pathfinder moving doors');jambs=col('21 | Pathfinder door interfaces')
def rawhash(o):
 h=hashlib.sha256()
 for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
 for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
 return h.hexdigest()
oldhash={o.name:rawhash(o) for o in sc.objects if o.type=='MESH'};oldmat={o.name:[list(r) for r in o.matrix_world] for o in sc.objects};edits=[]
def empty(n,loc=(0,0,0),parent=None):
 o=bpy.data.objects.new(n,None);rig.objects.link(o);o.location=loc;o.parent=parent;o.empty_display_type='ARROWS';o.empty_display_size=.12;return o
ctrl=empty('GT | Pathfinder controls');ctrl.empty_display_type='CUBE';ctrl.empty_display_size=.08
props=['left_front_door','right_front_door','left_rear_door','right_rear_door','steer','roll']
for k in props:
 ctrl[k]=0.;lo,hi=(0.,60.) if 'door' in k else ((-30.,30.) if k=='steer' else (-720.,720.));ctrl.id_properties_ui(k).update(min=lo,max=hi,description='Degrees. Static inspection rig; consult sweep-report.json.')
def driver(o,index,key,expression):
 d=o.driver_add('rotation_euler',index).driver;d.type='SCRIPTED';v=d.variables.new();v.name='v';v.type='SINGLE_PROP';v.targets[0].id=ctrl;v.targets[0].data_path='["'+key+'"]';d.expression=expression
def attach(o,p):
 bpy.context.view_layer.update();world=o.matrix_world.copy();o.parent=p;o.matrix_parent_inverse=p.matrix_world.inverted();o.matrix_world=world
def pose(**values):
 for k in props:ctrl[k]=float(values.get(k,0))
 ctrl.update_tag();sc.frame_set(sc.frame_current);bpy.context.view_layer.update()
def make(n,vs,fs,mats,c,indices=None):
 me=bpy.data.meshes.new(n);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(n,me);c.objects.link(o)
 for m in mats:me.materials.append(m)
 if indices:
  for f,i in zip(me.polygons,indices):f.material_index=i
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();return o
def box(n,loc,size,m,c=jambs):
 x,y,z=loc;dx,dy,dz=[v/2 for v in size];vs=[(x+a*dx,y+b*dy,z+d*dz) for a,b,d in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]];o=make(n,vs,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],[m],c);be=o.modifiers.new('Edge radius','BEVEL');be.width=.003;be.segments=2;return o
def clip(poly,A,B,inside=True):
 def value(v):return (B[0]-A[0])*(v.z-A[1])-(B[1]-A[1])*(v.y-A[0])
 result=[]
 for va,vb in zip(poly,poly[1:]+poly[:1]):
  da=value(va)*(1 if inside else -1);db=value(vb)*(1 if inside else -1)
  if da>=-1e-8:result.append(va)
  if (da>=0)!=(db>=0):result.append(va.lerp(vb,da/(da-db)))
 return result
def partition(o,poly,n):
 # Partition original faces directly: open sheet surfaces need no boolean volume.
 iv=[];iff=[];im=[];ov=[];off=[];om=[]
 for f in o.data.polygons:
  remaining=[o.data.vertices[i].co.copy() for i in f.vertices]
  for A,B in zip(poly,poly[1:]+poly[:1]):
   if len(remaining)<3:break
   piece=clip(remaining,A,B,False)
   if len(piece)>=3:k=len(ov);ov.extend(tuple(v) for v in piece);off.append(tuple(range(k,len(ov))));om.append(f.material_index)
   remaining=clip(remaining,A,B,True)
  if len(remaining)>=3:k=len(iv);iv.extend(tuple(v) for v in remaining);iff.append(tuple(range(k,len(iv))));im.append(f.material_index)
 moving=make(n,iv,iff,list(o.data.materials),doors,im);fixed=make(o.name+' replacement',ov,off,list(o.data.materials),o.users_collection[0],om)
 for target in [moving,fixed]:
  for f in target.data.polygons:f.use_smooth=True
  for mod in o.modifiers:
   if mod.type=='SOLIDIFY':m=target.modifiers.new(mod.name,'SOLIDIFY');m.thickness=mod.thickness;m.offset=mod.offset;m.use_rim=mod.use_rim
 name=o.name;bpy.data.objects.remove(o,do_unlink=True);fixed.name=name;return fixed,moving
frontpoly=[(-.810,.474),(.272,.474),(.272,1.564),(-.305,1.539),(-.810,1.178)]
rearpoly=[(.314,.474),(1.307,.474),(1.379,1.098),(1.133,1.575),(.314,1.575)]
# A small reveal is produced by separating the moving panel from the cut boundary.
groups={};door_pivots={};black=bpy.data.materials['R50 | charcoal']
for side,label in [(1,'Left'),(-1,'Right')]:
 skin=bpy.data.objects[label+' | shared body skin'];frame=bpy.data.objects[label+' | continuous cabin frame'];edits.extend([skin.name,frame.name])
 for position,poly in [('front',frontpoly),('rear',rearpoly)]:
  key=label.lower()+'_'+position+'_door';pivot=empty('Hinge | '+key,(side*.913,-.831 if position=='front' else .313,.83),ctrl);driver(pivot,2,key,f'{-side}*min(max(v,0),60)*pi/180');door_pivots[key]=pivot
  skin,part=partition(skin,poly,label+' '+position+' | door pressing');frame,fr=partition(frame,poly,label+' '+position+' | moving window frame');members=[part,fr]
  # Open seams need a small physical gap, not merely a drawn line.
  cy=sum(y for y,z in poly)/len(poly);cz=sum(z for y,z in poly)/len(poly)
  for ob in [part,fr]:
   for v in ob.data.vertices:v.co.y=cy+(v.co.y-cy)*.994;v.co.z=cz+(v.co.z-cz)*.996
  for v in fr.data.vertices:
   if v.co.z>1.46:v.co.z-=.003*min(1,(v.co.z-1.46)/.07)
   if v.co.z>1.40 and v.co.y>(.20 if position=='front' else 1.04):v.co.y-=.012*min(1,(v.co.z-1.40)/.075)
   if position=='rear' and v.co.y>1.04:v.co.y-=.010
  for ob in list(sc.objects):
   if ob in members:continue
   match=(ob.name in [str(side)+' | '+position+' recessed glass',str(side)+' | '+position+' window seal'] or ob.name.startswith(position.capitalize()+' door |') and ob.name.endswith(' '+str(side)) or ob.name.startswith(position.capitalize()+' door '+str(side)+' |'))
   if position=='front' and ob.name in ['Mirror | stalk '+str(side),'Mirror | housing '+str(side),'Mirror | glass '+str(side)]:match=True
   if position=='front' and ob.name=='Front handle | fitted recess '+str(side):match=True
   if position=='rear' and ob.name=='Rear door glass | divider '+str(side):match=True
   if ob.name.startswith('Door moulding '+str(side)+' '):
    yy=sum(v.co.y for v in ob.data.vertices)/len(ob.data.vertices)
    if (position=='front' and -.83<yy<.272) or (position=='rear' and .314<yy<1.31):match=True
   if match:members.append(ob)
  # Door switches were originally generic names; locate them by their geometry.
  if position=='front':
   for ob in sc.objects:
    if ob.name.startswith('Door | window switch'):
     center=sum((v.co for v in ob.data.vertices),Vector())/len(ob.data.vertices)
     if center.x*side>0:members.append(ob)
  for ob in members:attach(ob,pivot)
  groups[key]=[o.name for o in members]
  # Mechanical inspection hinge barrels are seated between fixed body and leaf.
  for z in [.69,1.03]:
   fixed=box('Hinge backing | '+key,(side*.853,pivot.location.y-(.033 if position=='front' else .017),z),(.120,.050 if position=='front' else .022,.080),black)
   moving=box('Hinge leaf | '+key,(side*.887,pivot.location.y+.055,z),(.064,.050,.064),black);attach(moving,pivot);groups[key].append(moving.name)
   for suffix,xx,yy,dx,dy in [('knuckle',.913,.014,.032,.016),('arm',.905,.035,.016,.045)]:
    link=box('Hinge leaf | '+key+' '+suffix,(side*xx,pivot.location.y+yy,z),(dx,dy,.064),black);attach(link,pivot);groups[key].append(link.name)
   vs=[];fs=[]
   for zz in [z-.044,z+.044]:
    for j in range(16):t=j*math.tau/16;vs.append((side*.913+.017*math.cos(t),pivot.location.y+.017*math.sin(t),zz))
   fs=[tuple(range(15,-1,-1)),tuple(range(16,32))]+[(i,(i+1)%16,(i+1)%16+16,i+16) for i in range(16)]
   make('Hinge backing | '+key+' pin',vs,fs,[black],jambs)
 # Decorative seam curves become redundant with real door edges.
 for ob in list(sc.objects):
  if ob.name.startswith('Door boundary '+str(side)+' '):bpy.data.objects.remove(ob,do_unlink=True)
 # Rear wheel arch trim straddles the rear door: keep its liner stationary.
 flare=bpy.data.objects['Rear '+str(side)+' | seated flare and continuous tub'];edits.append(flare.name)
 vs=[tuple(v.co) for v in flare.data.vertices];fixedfaces=[tuple(f.vertices) for f in flare.data.polygons if f.material_index!=0];paintfaces=[tuple(f.vertices) for f in flare.data.polygons if f.material_index==0]
 liner=make('Rear '+str(side)+' | fixed liner',vs,fixedfaces,list(flare.data.materials),flare.users_collection[0],[1]*len(fixedfaces));paint=make('Rear '+str(side)+' | split arch trim',vs,paintfaces,list(flare.data.materials),flare.users_collection[0]);
 for ob in [liner,paint]:
  mod=ob.modifiers.new('Sheet thickness','SOLIDIFY');mod.thickness=.010;mod.offset=-1
  for f in ob.data.polygons:f.use_smooth=True
 for v in liner.data.vertices:
  v.co.x=side*min(abs(v.co.x),.830)
  radial=Vector((v.co.y-1.35,v.co.z-.369)).normalized();v.co.y-=radial.x*.012;v.co.z-=radial.y*.012
 bpy.data.objects.remove(flare,do_unlink=True);fixed,moving=partition(paint,rearpoly,'Rear '+str(side)+' | door arch trim')
 cy=sum(y for y,z in rearpoly)/len(rearpoly);cz=sum(z for y,z in rearpoly)/len(rearpoly)
 for v in moving.data.vertices:v.co.y=cy+(v.co.y-cy)*.988;v.co.z=cz+(v.co.z-cz)*.988
 attach(moving,door_pivots[label.lower()+'_rear_door']);groups[label.lower()+'_rear_door'].append(moving.name)

# Explicit repairs revealed by the first sweep. Keep exterior arch surfaces.
for ob in list(sc.objects):
 if ob.type!='MESH':continue
 changed=False
 if ob.name.startswith('Front ') and 'inner wheelhouse wall' in ob.name:
  for v in ob.data.vertices:v.co.x=math.copysign(.400,v.co.x)
  changed=True
 if ob.name.startswith('Front ') and 'seated flare and continuous tub' in ob.name:
  for v in ob.data.vertices:
   if abs(abs(v.co.x)-.600)<.0001:v.co.x=math.copysign(.400,v.co.x)
  changed=True
 if ob.name.startswith('Rear ') and 'inner wheelhouse wall' in ob.name:
  for v in ob.data.vertices:
   radial=Vector((v.co.y-1.35,v.co.z-.369)).normalized();v.co.y-=radial.x*.012;v.co.z-=radial.y*.012
  changed=True
 if ob.name.startswith('Underbody | shallow sill member'):
  for v in ob.data.vertices:v.co.x=math.copysign(.47+(abs(v.co.x)-.7)*.3,v.co.x)
  changed=True
 if ob.name=='Floor | front footwell closure':
  for v in ob.data.vertices:v.co.x*=.91
  changed=True
 if ob.name=='Lining | fitted headliner':
  for v in ob.data.vertices:v.co.x*=.93
  changed=True
 if ob.name.startswith('Belt | upper anchor'):
  for v in ob.data.vertices:v.co.y=.295+(v.co.y-.280)*.28
  changed=True
 if ob.name.startswith('Belt | flat webbing'):
  for v in ob.data.vertices:
   if v.co.z>1.37:v.co.y+=.015
  changed=True
 if changed:edits.append(ob.name)

for side in [-1,1]:
 poly=[(-.861,.431),(-.700,.903),(-.672,.93),(-.672,.431)]
 ob=make('Footwell | closed side kick panel '+str(side),[(side*.772,y,z) for y,z in poly],[tuple(range(4))],[black],jambs);m=ob.modifiers.new('Kick panel thickness','SOLIDIFY');m.thickness=.014

# Steer around world Z, then roll about the unmirrored world-X axle.
for side in [-1,1]:
 for axle,y,track in [('Front',-1.35,1.54),('Rear',1.35,1.545)]:
  key=axle.lower()+'_'+str(side)+'_wheel';prefix=axle+' '+str(side)+' | ';center=(side*track/2,y,.369);turn=empty('Steer | '+key,center,ctrl)
  if axle=='Front':driver(turn,2,'steer',f'atan(2.7*tan(min(max(v,-30),30)*pi/180)/(2.7-{side}*.77*tan(min(max(v,-30),30)*pi/180)))')
  spin=empty('Roll | '+key,(0,0,0),turn);driver(spin,0,'roll','v*pi/180');members=[]
  for ob in list(bpy.data.collections['14 | Detailed wheels and tyres'].objects):
   if not ob.name.startswith(prefix):continue
   attach(ob,turn if 'caliper' in ob.name else spin);members.append(ob.name)
  groups[key]=members
axis=empty('Cabin steering axis',(-.407,-.257,1.032),ctrl);axis.rotation_euler=Vector((0,0,1)).rotation_difference(Vector((0,.94,.34)).normalized()).to_euler();spin=empty('Cabin steering spin',parent=axis);driver(spin,2,'steer','min(max(v,-30),30)*15*pi/180');groups['cabin_steering']=[]
for ob in list(sc.objects):
 if ob.name.startswith(('Steering | padded rim','Steering | horn boss','Steering | spoke')):attach(ob,spin);groups['cabin_steering'].append(ob.name)
ctrl['groups']=json.dumps(groups);ctrl['scope']='Doors, Ackermann steering, road-wheel roll and linked cabin wheel. No suspension or physics.'
for ob in sc.objects:
 if ob.name.startswith(('Hinge backing |','Hinge leaf |')):
  ob.hide_render=True;ob.hide_set(True);ob['inspection_fixture']=True
for c in [doors,bpy.data.collections['14 | Detailed wheels and tyres'],bpy.data.collections['15 | Pathfinder fitted cockpit']]:c['articulated_do_not_static_rebuild']=True
pose()
changed=[n for n,h in oldhash.items() if n not in bpy.data.objects or rawhash(bpy.data.objects[n])!=h]
assert set(changed)<=set(edits),'Unexpected source geometry changes '+str(set(changed)-set(edits))
manifest={'source':str(source),'source_sha256':sha,'changed_source_meshes':changed,'unchanged_raw_meshes':{n:h for n,h in oldhash.items() if n not in changed},'rest_matrices':{o.name:[list(r) for r in o.matrix_world] for o in sc.objects if o.type in ['MESH','CURVE']},'groups':groups,'door_limits_degrees':60,'steering_limit_degrees':30,'repairs':['Split four door pressings/window frames at existing seam locations; real small edge reveals','Split rear arch paint from stationary liners so door trim can move','Grouped each door with its glazing, card, handle, moulding, switches and front mirror'],'scope':ctrl['scope']}
manifest['repairs']+=['Moved front inner wheelhouse boundaries from 600 to 400 mm half-width for steering, keeping visible flares','Narrowed two underbody bars that already intersected rear tyres','Narrowed the hidden headliner and lowered moving frame top margins','Refitted front footwell closure and added side kick panels','Refitted fixed rear liner, moving arch-trim gaps, belt anchors and hinge interfaces for door motion']
(out/'articulation-manifest.json').write_text(json.dumps(manifest,indent=2));shutil.copy2(Path(__file__),out/Path(__file__).name)
assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
text=bpy.data.texts.new('START HERE - Pathfinder controls.txt');text.write('Select GT | Pathfinder controls and edit Object Custom Properties. Angles are degrees. Doors 0-60; steer -30 to +30; roll spins road wheels in place. Use the neutral manual file for editing. This is an inspection rig, not vehicle physics. Read the delivered sweep report before extending ranges. Preserve the static source for geometry editing.\n')
sc['stage']='Pathfinder articulation candidate; sampled motion checks required';sc.camera=bpy.data.objects['Review | front quarter'];bpy.ops.wm.save_as_mainfile(filepath=str(out/'Pathfinder_Articulation.blend'));print('RIG_READY '+str(out),flush=True)
