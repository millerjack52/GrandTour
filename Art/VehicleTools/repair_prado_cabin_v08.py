import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v07');O=P.parent/'prado-cabin-v08';O.mkdir(exist_ok=True)
assert not (O/'Prado_Cabin.blend').exists(),'Protected revision'
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Cabin.blend'));sc=bpy.context.scene
with bpy.data.libraries.load('C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04/Prado_Exterior.blend',link=False) as (src,dst):dst.objects=['Prado | source-fitted body']
source=dst.objects[0];source.data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co for v in source.data.vertices],[list(t.vertices) for t in source.data.loop_triangles],all_triangles=True)
repairs=[]
for ob in [o for o in sc.objects if o.name.startswith('Door |') or o.name=='Prado | fixed shell and underbody']:
 used={i for p in ob.data.polygons for i in p.vertices}
 for i in used:
  v=ob.data.vertices[i];p,_,_,dist=tree.find_nearest(v.co)
  if dist>.00001:
   repairs.append({'object':ob.name,'vertex':i,'correction_m':dist,'reason':'Clipped non-planar source cap interpolation; returned to original surface'})
   v.co=p
 ob.data.update()
def mesh(n,v,f,col,mat,thickness):
 me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(n,me);bpy.data.collections[col].objects.link(ob);ob.parent=bpy.data.objects['PRADO | working assembly'];me.materials.append(bpy.data.materials['Prado | '+mat]);ob.color=me.materials[0].diffuse_color
 mod=ob.modifiers.new('Fitted return thickness','SOLIDIFY');mod.thickness=thickness;mod.offset=-1
 return ob
for sign in [-1,1]:
 verts=[];faces=[]
 for i in range(25):
  y=.034+i/24*.100
  for z in [.138,.147]:
   p=tree.ray_cast(Vector((sign*1.4,y*5,z*5)),Vector((-sign,0,0)),.8)[0]
   assert p is not None,(sign,y,z)
   verts.append((p.x-sign*.010,y*5,z*5))
 for i in range(24):a=i*2;faces.append((a,a+2,a+3,a+1))
 mesh('Rear door sill return | '+str(sign),verts,faces,'11 Panel returns','Rubber',.002)
# Actual windscreen aperture boundary, from the unchanged body edge loops.
bm=bmesh.new();bm.from_mesh(source.data);todo={e for e in bm.edges if e.is_boundary};candidates=[]
while todo:
 e=todo.pop();es={e};vs=set(e.verts);queue=list(vs)
 while queue:
  v=queue.pop()
  for e in v.link_edges:
   if e in todo:todo.remove(e);es.add(e);w=e.other_vert(v);vs.add(w);queue.append(w)
 co=[v.co.copy() for v in vs]
 if len(co)>10 and max(v.y for v in co)<-.45 and min(v.z for v in co)>1.49 and max(v.z for v in co)>2.:candidates.append(co)
assert len(candidates)==1,len(candidates)
lower=sorted([v for v in candidates[0] if v.z<1.60],key=lambda v:v.x)
bm.free();assert len(lower)>=4
v=[];f=[]
for p in lower:
 v.extend([(p.x,p.y+.004,p.z-.0025),(p.x,-.155*5,.3058*5)])
for i in range(len(lower)-1):a=i*2;f.append((a,a+2,a+3,a+1))
cowl=mesh('CAB | aperture-fitted dashboard cowl',v,f,'14 Dashboard','Cabin',.003)
(O/'local-repairs.json').write_text(json.dumps({'surface_corrections':repairs,'sill_returns':'9 mm tall fitted return at 10 mm recess, both rear sills','cowl_boundary':[[*p] for p in lower]},indent=2))
bpy.data.objects.remove(source,do_unlink=True)
root=bpy.data.objects['PRADO | working assembly'];root['status']='Fitted cabin and separated closed door/bonnet skins. Source body still needs final topology and engine preparation.'
sc.render.engine='BLENDER_WORKBENCH';cam=sc.camera
def render(n,c,d,scale):
 center=Vector(c)*5;cam.data.type='ORTHO';cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*5;sc.render.filepath=str(O/(n+'.png'));bpy.ops.render.render(write_still=True)
for n,d in [('quarter',(2,-3,1.1)),('side',(3,0,0)),('rear-quarter',(-2,3,1)),('underside',(1,-1,-2))]:render(n,(0,0,.27),d,1.2)
render('door-sill-close',(.175,.07,.153),(3,-.2,-.3),.24)
for name in ['START HERE — Prado status','Prado cabin build notes']:
 if name in bpy.data.texts:bpy.data.texts.remove(bpy.data.texts[name])
readme='''PRADO — FITTED CABIN REVIEW v08

Source: C:/Users/mille/Downloads/pradotripo.glb, unchanged.
Working scale: 5x normalized source, not verified factory dimensions.

Added four upholstered seats with rails, risers, headrests and buckles;
dashboard, gauges, vents, pedals, steering wheel, radio and cabin controls;
door cards, headliner, sun visors, interior mirror, cargo tray and tie-downs.
Continuous floor, central tunnel and raised rear wheelhouses fitted to body.
Door skins and bonnet separated from existing surface with recessed seam backing.
Glass transmission checked in a real lit render, from outside and the driver seat.
Earlier failed preview revisions are retained as negative controls.

This is a static review asset, NOT a finished game-ready vehicle.
Door skins are separated; opening door interiors, hinges and motion are not rigged.
Fixed body retains source topology defects; full retopology and final seam audit,
tailgate/bumper separation, belts, UVs, LODs, collisions, driving rig and Unreal
validation remain. Inspection materials are not a finished texture set.

Actual reviewed renders and scoped geometry checks accompany this file.
The cabin cutaway intentionally hides body, glass and overhead trim for visibility.
Workbench preview does not display glass transmission; use Material/Rendered view.
Preserve the source shape. Do not replace it with a generic vehicle generator.
'''
(O/'README.txt').write_text(readme);bpy.data.texts.new('START HERE — Prado status').write(readme)
render('quarter',(0,0,.27),(2,-3,1.1),1.2)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Prado_Cabin.blend'))
