import bpy,bmesh,json,time
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-source-v01');OUT=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-work-v03');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Analysed.blend'));sc=bpy.context.scene
source=next(o for o in sc.objects if o.type=='MESH');source.hide_render=True;source.hide_set(True)
me=source.data.copy();body=bpy.data.objects.new('Body retopology',me);sc.collection.objects.link(body)
bm=bmesh.new();bm.from_mesh(me);il=bm.faces.layers.int.get('source_island');bmesh.ops.delete(bm,geom=[f for f in bm.faces if f[il]!=0],context='FACES')
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-6)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(me);bm.free()
ref=body.copy();ref.data=body.data.copy();sc.collection.objects.link(ref);ref.name='Body reference';ref.hide_render=True;ref.hide_set(True)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
print('VOXEL',len(body.data.vertices),len(body.data.polygons),flush=True)
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
for repair in range(5):
 bad=[e for e in bm.edges if len(e.link_faces)>2]
 print('REPAIR',repair,len(bad),sum(e.is_boundary for e in bm.edges),flush=True)
 if bad:bmesh.ops.delete(bm,geom=list({min(e.link_faces,key=lambda f:f.calc_area()) for e in bad}),context='FACES')
 loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 boundary=[e for e in bm.edges if e.is_boundary]
 if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=8)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if all(e.is_manifold for e in bm.edges):break
print('REPAIRED',len(bm.verts),len(bm.faces),sum(not e.is_manifold for e in bm.edges),flush=True)
# Voxel surfaces can have multiple disconnected face fans meeting at one vertex.
# Split those fans, retaining the exact surface positions.
bmesh.ops.triangulate(bm,faces=list(bm.faces))
coords=[]; corner={}; splits=0
for v in bm.verts:
 todo=set(v.link_faces)
 groups=[]
 while todo:
  seed=todo.pop();seen={seed};q=[seed]
  while q:
   f=q.pop()
   for e in f.edges:
    if v not in e.verts:continue
    for g in e.link_faces:
     if g in todo:todo.remove(g);seen.add(g);q.append(g)
  groups.append(seen)
 for group in groups:
  idx=len(coords);coords.append(tuple(v.co))
  for f in group:corner[(v,f)]=idx
 splits+=max(0,len(groups)-1)
faces=[[corner[(v,f)] for v in f.verts] for f in bm.faces]
new=bpy.data.meshes.new('Manifold remesh');new.from_pydata(coords,[],faces);new.update();body.data=new
print('SPLIT_FANS',splits,flush=True)
bm.free()
for ob in sc.objects:ob.select_set(False)
body.hide_set(False);body.hide_viewport=False;body.select_set(True);bpy.context.view_layer.objects.active=body
print('ACTIVE',bpy.context.active_object.name,[o.name for o in bpy.context.selected_objects],flush=True)
for v in body.data.vertices:v.co*=100
bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=False,use_preserve_sharp=False,use_preserve_boundary=True,target_faces=8500,seed=17)
for v in body.data.vertices:v.co/=100
assert len(body.data.polygons)<20000,'Quadriflow failed'
print('QUADS',len(body.data.vertices),len(body.data.polygons),flush=True)
# Light surface relaxation, then return the surface to the measured donor envelope.
md=body.modifiers.new('Relax flow','SMOOTH');md.factor=.25;md.iterations=2;bpy.ops.object.modifier_apply(modifier=md.name)
md=body.modifiers.new('Fit measured donor','SHRINKWRAP');md.target=ref;md.wrap_method='NEAREST_SURFACEPOINT';md.wrap_mode='ON_SURFACE';bpy.ops.object.modifier_apply(modifier=md.name)
mat=bpy.data.materials.new('Retopo clay');mat.diffuse_color=(.5,.54,.52,1);body.data.materials.clear();body.data.materials.append(mat)
for p in body.data.polygons:p.use_smooth=True
body.data.set_sharp_from_angle(angle=.65)
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.render.resolution_x=1200;sc.render.resolution_y=850
cam=sc.camera;cam.data.ortho_scale=1.2
for n,pos in [('quarter',(1.2,-1.6,.95)),('side',(1.2,0,.2)),('rear',(1.1,1.5,.9)),('top',(0,0,2))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.19))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Body_Retopology.blend'))








