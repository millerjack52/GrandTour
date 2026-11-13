import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-source-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Source.blend'))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
print('MATERIALS',[(m.name,[(n.name,n.type,n.image.name if n.type=='TEX_IMAGE' and n.image else '') for n in m.node_tree.nodes]) for m in ob.data.materials])
for im in bpy.data.images:
 if im.size[0]>0 and im.name!='Render Result':
  im.filepath_raw=str(P/(im.name.replace('/','_')+'.png'));im.file_format='PNG';im.save();print('IMAGE',im.name,list(im.size))
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);layer=bm.faces.layers.int.new('source_island')
todo=set(bm.verts);parts=[]
while todo:
 seed=todo.pop();seen={seed};q=[seed]
 while q:
  v=q.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in todo:todo.remove(w);seen.add(w);q.append(w)
 parts.append((seen,{f for v in seen for f in v.link_faces}))
parts.sort(key=lambda p:-len(p[0]))
# Tag original connected components while retaining their UVs.
for i,(vs,fs) in enumerate(parts):
 for f in fs:f[layer]=i
bm.to_mesh(ob.data);bm.free()
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=10
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.7,.8,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.7
for pos,power,size in [((1,-1,2),70,1),((-1,0,1),40,1)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.rotation_euler=(Vector((0,0,.2))-o.location).to_track_quat('-Z','Y').to_euler()
cam=sc.camera;cam.data.ortho_scale=1.25;cam.location=(1.2,-1.6,1);cam.rotation_euler=(Vector((0,0,.19))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/'textured-quarter.png');bpy.ops.render.render(write_still=True)
cam.data.ortho_scale=1.25;cam.location=(1.2,0,.22);cam.rotation_euler=(Vector((0,0,.22))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/'textured-side.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Porsche_Analysed.blend'))
print('ANALYSIS_COMPLETE',flush=True)
