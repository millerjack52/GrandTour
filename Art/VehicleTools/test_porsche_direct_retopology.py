import bpy,bmesh,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
R=Path('C:/GrandTour/Art/Export/VehicleTools');O=R/'porsche-direct-retopo-study-v02';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'porsche-source-repair-v01/Porsche_Source_Repaired.blend'));sc=bpy.context.scene
old=bpy.data.objects['Body_original_repaired'];ref=bpy.data.objects['WORKING - original shape unchanged']
me=ref.data.copy();ob=bpy.data.objects.new('Direct source topology study',me);old.users_collection[0].objects.link(ob);old.hide_render=True;old.hide_set(True)
bm=bmesh.new();bm.from_mesh(me);il=bm.faces.layers.int.get('source_island');bmesh.ops.delete(bm,geom=[f for f in bm.faces if f[il]!=0],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00065)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000002)
for _ in range(16):
 bad=[e for e in bm.edges if len(e.link_faces)>2]
 if not bad:break
 bmesh.ops.delete(bm,geom=list({min(e.link_faces,key=lambda f:f.calc_area()) for e in bad}),context='FACES_ONLY')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
# Split disconnected fans at exactly the original position (no voxel conversion).
verts=[];corner={};splits=0
for v in bm.verts:
 todo=set(v.link_faces)
 while todo:
  seed=todo.pop();group={seed};q=[seed]
  while q:
   f=q.pop()
   for e in f.edges:
    if v not in e.verts:continue
    for g in e.link_faces:
     if g in todo:todo.remove(g);group.add(g);q.append(g)
  k=len(verts);verts.append(tuple(v.co*4.5))
  for f in group:corner[(v,f)]=k
faces=[[corner[(v,f)] for v in f.verts] for f in bm.faces];bm.free()
new=bpy.data.meshes.new('Manifold source patches');new.from_pydata(verts,[],faces);new.update();ob.data=new
bb=bmesh.new();bb.from_mesh(new);bmesh.ops.recalc_face_normals(bb,faces=list(bb.faces))
print('TOPOLOGY',len(bb.verts),len(bb.edges),len(bb.faces),'boundary',sum(e.is_boundary for e in bb.edges),'overconnected',sum(len(e.link_faces)>2 for e in bb.edges),'inconsistent',sum(e.is_manifold and not e.is_contiguous for e in bb.edges),'badverts',sum(not v.is_manifold for v in bb.verts),flush=True)
bad=[e for e in bb.edges if e.is_manifold and not e.is_contiguous]
if bad:bmesh.ops.delete(bb,geom=list({min(e.link_faces,key=lambda f:f.calc_area()) for e in bad}),context='FACES')
edges={e for e in bb.edges if e.is_boundary}
while edges:
 e=edges.pop();group={e};q=list(e.verts);vs=set(e.verts)
 while q:
  v=q.pop()
  for ee in v.link_edges:
   if ee in edges:edges.remove(ee);group.add(ee);vs.update(ee.verts);q.extend(ee.verts)
 ext=max(max(v.co[k] for v in vs)-min(v.co[k] for v in vs) for k in range(3))
 if ext<.08:bmesh.ops.holes_fill(bb,edges=list(group),sides=0)
bmesh.ops.delete(bb,geom=[v for v in bb.verts if not v.link_faces],context='VERTS');bmesh.ops.recalc_face_normals(bb,faces=list(bb.faces));bb.to_mesh(new);bb.free()
for x in sc.objects:x.select_set(False)
ob.select_set(True);bpy.context.view_layer.objects.active=ob
print('BEGIN_QF',len(new.polygons),flush=True)
try:bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=False,use_preserve_sharp=False,use_preserve_boundary=True,target_faces=11000,seed=33)
except Exception as ex:print('FAILED',ex,flush=True);raise
print('AFTER_QF',len(ob.data.polygons),flush=True)
for f in ob.data.polygons:f.use_smooth=True
ob.data.set_sharp_from_angle(angle=1.1);ob.color=(.52,.56,.58,1)
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='OBJECT';sc.display.shading.show_cavity=False
cam=sc.camera;cam.data.ortho_scale=5.65
for name,pos in [('quarter',(5.4,-7.2,3.7)),('side',(7,0,.92)),('rear',(5.4,7.2,3.8))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.92))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Direct_Source_Study.blend'))
