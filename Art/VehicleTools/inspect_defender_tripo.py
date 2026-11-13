import bpy,bmesh,json,hashlib,math
from pathlib import Path
from mathutils import Vector
SRC=Path('C:/Users/mille/Downloads/defender110tripo.glb')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/defender-tripo-v01')
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'objects':[]}
for o in objects:
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 pts=[o.matrix_world@v.co for v in o.data.vertices]
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
 todo=set(bm.verts);islands=[]
 while todo:
  seed=todo.pop();seen={seed};q=[seed]
  while q:
   v=q.pop()
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in todo:todo.remove(w);seen.add(w);q.append(w)
  islands.append({'vertices':len(seen),'min':[min(v.co[i] for v in seen) for i in range(3)],'max':[max(v.co[i] for v in seen) for i in range(3)]})
 report['objects'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'bounds':[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]],'islands':sorted(islands,key=lambda x:-x['vertices']),'boundary_edges':sum(e.is_boundary for e in bm.edges)})
 bm.free()
 o.name='Tripo_Defender_Source'
 for p in o.data.polygons:p.use_smooth=True
 m=bpy.data.materials.new('Inspection clay');m.diffuse_color=(.38,.43,.47,1);m.use_nodes=True;m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=m.diffuse_color;o.data.materials.clear();o.data.materials.append(m)
(OUT/'source-inspection.json').write_text(json.dumps(report,indent=2))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24
sc.render.resolution_x=1100;sc.render.resolution_y=800;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Studio');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.3,.3,.3,1)
sc.world.node_tree.nodes['Background'].inputs[1].default_value=.7
for name,pos,power,size in [('Key',(1,-1,2),90,2),('Fill',(-1,0,1),60,2),('Rim',(0,1,2),70,1.5)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.25))-o.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',camd);sc.collection.objects.link(cam);sc.camera=cam;camd.type='ORTHO'
for name,pos,scale in [('side',(2,0,.25),1.35),('front',(0,-2,.25),.92),('rear',(0,2,.25),.92),('quarter',(1.6,-2,1),1.45),('top',(0,0,2),1.35),('underside',(1,-1,-1),1.4)]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.25))-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=scale
 sc.render.filepath=str(OUT/('source-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Defender_Source_Inspection.blend'))
print(json.dumps(report))
