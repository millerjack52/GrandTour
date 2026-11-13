"""Selective rounding of the saved, fitted Range Rover including its cockpit."""
import bpy,bmesh,json,math,hashlib,shutil
from pathlib import Path
from mathutils import Vector
BASE=Path('C:/GrandTour/Art/Export/VehicleTools')
SRC=BASE/'graphic-adventure-interior-v01/GraphicAdventure_Interior.blend'
OUT=BASE/'graphic-adventure-rounded-v01';OUT.mkdir(exist_ok=True)
if (OUT/'delivery-manifest.json').exists():raise RuntimeError('Delivered revision protected')
bpy.ops.wm.open_mainfile(filepath=str(SRC));sc=bpy.context.scene
def current():return [o for o in sc.objects if o.type=='MESH' and o.name.startswith('RET |')]
def fingerprint(o):
 return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],list(map(tuple,o.matrix_world)),[(m.name,m.type,str(getattr(m,'width','')),str(getattr(m,'segments',''))) for m in o.modifiers])).encode()).hexdigest()
before={o.name:fingerprint(o) for o in current()};changed=set();boundary_checks=[]
def mark(o):changed.add(o.name);return o
def mesh_replace(o,verts,faces):
 mark(o);old=o.data;me=bpy.data.meshes.new(old.name+' rounded');me.from_pydata(verts,[],faces);me.update()
 for m in old.materials:me.materials.append(m)
 o.data=me
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
def smooth(o):
 for p in o.data.polygons:p.use_smooth=True
 o.data.set_sharp_from_angle(angle=.65)

# Refine only large crowns and flare faces. Full crease on boundary vertices
# preserves the exact shared panel seating edges; interior loops may relax.
for name in ['Bonnet main pressing','Roof crown']:
 o=mark(bpy.data.objects['RET | '+name]);me=o.data
 bm=bmesh.new();bm.from_mesh(me);bm.edges.ensure_lookup_table();bm.verts.ensure_lookup_table()
 edgeids=[e.index for e in bm.edges if e.is_boundary];vertids={v.index for e in bm.edges if e.is_boundary for v in e.verts};bm.free()
 ce=me.attributes.get('crease_edge') or me.attributes.new('crease_edge','FLOAT','EDGE')
 cv=me.attributes.get('crease_vert') or me.attributes.new('crease_vert','FLOAT','POINT')
 for i in edgeids:ce.data[i].value=1
 for i in vertids:cv.data[i].value=1
 original=[me.vertices[i].co.copy() for i in vertids]
 sub=o.modifiers.new('Rounded form with fixed mating perimeter','SUBSURF');sub.levels=2;sub.render_levels=2
 bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_move_up(modifier=sub.name)
 while list(o.modifiers).index(sub)>0:bpy.ops.object.modifier_move_up(modifier=sub.name)
 # Check the subdivided surface before thickness: shared boundary anchors exact.
 others=[(m,m.show_viewport) for m in o.modifiers if m!=sub]
 for m,_ in others:m.show_viewport=False
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
 error=max(min((v.co-p).length for v in em.vertices) for p in original);ev.to_mesh_clear()
 for m,value in others:m.show_viewport=value
 boundary_checks.append({'part':o.name,'anchor_error_m':error});assert error<1e-5,(o.name,error)
 smooth(o)
 for m in o.modifiers:
  if m.type=='BEVEL':m.segments=4

# Round across each flare's raised section, retaining its designed angular
# arch outline. A 2-D subdivision here can pull the skin through its liner.
for side in ['L','R']:
 for axle in ['Front','Rear']:
  o=bpy.data.objects['RET | '+side+' '+axle+' arch flare']
  controls=[v.co.copy() for v in o.data.vertices];rows=[]
  for seg in range(3):
   for j in range(6):
    t=j/6;row=[]
    for k in range(6):
     p0=controls[max(0,seg-1)*6+k];p1=controls[seg*6+k];p2=controls[(seg+1)*6+k];p3=controls[min(3,seg+2)*6+k]
     # Low-tension Hermite interpolation softens the ridge without overshoot.
     m1=(p2-p0)*.25;m2=(p3-p1)*.25
     row.append((2*t**3-3*t*t+1)*p1+(t**3-2*t*t+t)*m1+(-2*t**3+3*t*t)*p2+(t**3-t*t)*m2)
    rows.append(row)
  rows.append(controls[-6:]);verts=[p for row in rows for p in row]
  faces=[(r*6+k,r*6+k+1,(r+1)*6+k+1,(r+1)*6+k) for r in range(len(rows)-1) for k in range(5)]
  mesh_replace(o,verts,faces);smooth(o)
  for m in list(o.modifiers):
   if m.type in ['BEVEL','WEIGHTED_NORMAL']:o.modifiers.remove(m)

# Derive each frame, seal and glass from its actual saved loops; no whole-car
# recipe is rerun. Exterior frame boundaries are sampled but remain unchanged.
def rounded_ring_pair(outer,inner,trim=.030):
 out=[];inn=[];n=len(inner)
 for i in range(n):
  p=Vector(inner[i]);a=Vector(inner[i-1]);b=Vector(inner[(i+1)%n]);va=a-p;vb=b-p
  angle=va.normalized().dot(vb.normalized())
  if angle<-.99:out.append(Vector(outer[i]));inn.append(p);continue
  d=min(trim,va.length*.28,vb.length*.28);t1=d/va.length;t2=d/vb.length
  st=p+va*t1;en=p+vb*t2;op=Vector(outer[i]);oa=Vector(outer[i-1]);ob=Vector(outer[(i+1)%n])
  for k in range(7):
   t=k/6;inn.append((1-t)**2*st+2*t*(1-t)*p+t*t*en)
   out.append(op.lerp(oa,t1*(1-2*t)) if t<=.5 else op.lerp(ob,t2*(2*t-1)))
 return out,inn
windows=[s+' '+a+' window' for s in ['L','R'] for a in ['Front','Rear']]+[s+' cargo window' for s in ['L','R']]+['Rear glazing','Windscreen']
for name in windows:
 frame=bpy.data.objects['RET | '+name+' frame'];gasket=bpy.data.objects['RET | '+name+' gasket'];glass=bpy.data.objects['RET | '+name+' glass']
 n=len(frame.data.vertices)//2;outer=[v.co.copy() for v in frame.data.vertices[:n]];inner=[v.co.copy() for v in frame.data.vertices[n:]]
 out,inn=rounded_ring_pair(outer,inner,.032);count=len(out)
 faces=[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
 gn=len(gasket.data.vertices)//2;gouter=[v.co.copy() for v in gasket.data.vertices[:gn]];ginner=[v.co.copy() for v in gasket.data.vertices[gn:]]
 _,gout=rounded_ring_pair(gouter,gouter,.032);_,gin=rounded_ring_pair(ginner,ginner,.031)
 assert len(gout)==len(gin)==count
 mesh_replace(frame,out+inn,faces);mesh_replace(gasket,gout+gin,faces)
 # Use saved front glass plane offset and retain a modest centre crown.
 oldcenter=sum((v.co for v in glass.data.vertices),Vector())/len(glass.data.vertices)
 center=sum(gin,Vector())/len(gin)
 normal=Vector((1 if name.startswith('L') else -1,0,0)) if name[0] in ['L','R'] and name!='Rear glazing' else Vector((0,-1 if name=='Windscreen' else 1,0))
 pane=[p-normal*.0009 for p in gin]
 if name=='Windscreen':center.y=oldcenter.y
 else:center-=normal*.0009
 mesh_replace(glass,pane+[center],[(i,(i+1)%count,count) for i in range(count)])
 if name=='Windscreen':
  def uv_from(p):
   x,z=p.x/4.6,p.z/4.6;t=(z-.301)/.125
   for _ in range(8):u=x/(.203-.0346*t);t=(z-.301)/(.128-.005*u*u)
   return Vector((u,t))
  def mapped(uv):
   u,t=uv;return Vector((u*(.203-.0346*t),-.185+(.069+.018*u**4)*t,.301+(.128-.005*u*u)*t))*4.6
  uvs=[uv_from(p) for p in gin];mid=sum(uvs,Vector((0,0)))/len(uvs)
  verts=[mapped(mid)];faces=[]
  for r in range(1,9):verts.extend(mapped(mid.lerp(uv,r/8)) for uv in uvs)
  faces.extend((0,1+i,1+(i+1)%count) for i in range(count))
  for r in range(7):
   a=1+r*count;b=a+count
   faces.extend((a+i,b+i,b+(i+1)%count,a+(i+1)%count) for i in range(count))
  mesh_replace(glass,verts,faces)
 for m in list(frame.modifiers):
  if m.type in ['BEVEL','WEIGHTED_NORMAL']:frame.modifiers.remove(m)
 if name=='Windscreen':smooth(glass)

# True multi-segment geometry on thicker exposed components. Keep the repaired
# rear bumper caps and the exact lamp/corner seating objects.
for o in current():
 if any(k in o.name for k in ['Front recovery bumper','Rear bumper','mirror casing','mirror glass','Bumper fog']):
  for m in o.modifiers:
   if m.type=='BEVEL':
    mark(o);m.segments=6
    if 'bumper' in o.name.lower():m.width=max(m.width,.016)
  if o.name in changed:smooth(o)

# UVs only on locally replaced/refined meshes. Preserve all cockpit geometry,
# parts, materials, wheel sizes and transforms from the saved assembly.
for o in current():
 if o.name not in changed:continue
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
unexpected=[o.name for o in current() if o.name not in changed and before[o.name]!=fingerprint(o)]
assert not unexpected,unexpected
manifest={'source':str(SRC),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'changed':sorted(changed),'preserved_meshes_and_transforms':len(before)-len(changed),'unexpected':unexpected,'fixed_perimeter_checks':boundary_checks,'notes':['Finished cockpit retained exactly.','Wheel sizes, pivot transforms, panel repairs and mating perimeter anchors retained.','Rounding is selective; major body profile unchanged.','Existing Unreal assets have not been replaced by this style revision.']}
(OUT/'repair-manifest.json').write_text(json.dumps(manifest,indent=2))
shutil.copy2(BASE/'graphic-adventure-assembly-v05/vehicle-spec.json',OUT/'vehicle-spec.json')
bpy.ops.object.select_all(action='DESELECT')
for o in sc.objects:
 if o.name.startswith('RET |') and o.type=='MESH' or o.name.startswith('GA |') and o.type=='EMPTY':o.hide_set(False);o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'GraphicAdventure_Rounded.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'GraphicAdventure_Rounded.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.object.select_all(action='DESELECT')
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True
sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
cam=sc.camera;cam.data.type='ORTHO';S=4.6
views=[('side',(2,0,.28),(0,0,.28),6.1),('front',(0,-2,.28),(0,0,.28),4.5),('top',(0,0,2),(0,0,.28),7.7),('quarter',(1.5,-1.9,.95),(0,0,.28),6.4),('rear-quarter',(1.5,1.9,.80),(0,0,.28),6.4),('window-close',(1,.05,.38),(.2,.05,.36),1.5),('front-corner',(.8,-1,.52),(.191,-.432,.263),1.3),('rear-door',(1,.40,.35),(.214,.251,.272),.75),('arch-close',(1,-.4,.3),(.22,-.30,.19),1.55)]
for name,pos,target,scale in views:
 cam.location=Vector(pos)*S;cam.rotation_euler=(Vector(target)*S-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=Vector((1.5,-1.9,.95))*S;cam.rotation_euler=(Vector((0,0,.28))*S-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=6.4
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GraphicAdventure_Rounded.blend'));print('ROUNDING_COMPLETE',json.dumps(manifest),flush=True)
