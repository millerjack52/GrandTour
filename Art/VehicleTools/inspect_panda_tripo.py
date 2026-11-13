import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector
SRC=Path('C:/Users/mille/Downloads/pandatripo.glb')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/panda-source-v01');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'objects':[]}
for o in objects:
 bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);o.select_set(False)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bm.verts.ensure_lookup_table();bm.verts.index_update();bm.faces.ensure_lookup_table();bm.faces.index_update()
 todo=set(bm.verts);islands=[]
 while todo:
  seed=todo.pop();seen={seed};q=[seed]
  while q:
   v=q.pop()
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in todo:todo.remove(w);seen.add(w);q.append(w)
  faces={f for v in seen for f in v.link_faces};vs=sorted(seen,key=lambda v:v.index);idx={v:i for i,v in enumerate(vs)}
  islands.append({'vertices':len(vs),'faces':len(faces),'min':[min(v.co[i] for v in seen) for i in range(3)],'max':[max(v.co[i] for v in seen) for i in range(3)],'verts':[list(v.co) for v in vs],'polys':[[idx[v] for v in f.verts] for f in sorted(faces,key=lambda f:f.index)]})
 islands.sort(key=lambda x:-x['vertices']);(OUT/'islands.json').write_text(json.dumps(islands))
 report['objects'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'materials':[m.name for m in o.data.materials if m],'uv_layers':len(o.data.uv_layers),'bounds':[[min(v.co[i] for v in bm.verts) for i in range(3)],[max(v.co[i] for v in bm.verts) for i in range(3)]],'islands':[{k:v for k,v in a.items() if k not in ['verts','polys']} for a in islands],'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)})
 bm.free()
 o.name='Panda Tripo source';o.color=(.48,.53,.48,1)
 for p in o.data.polygons:p.use_smooth=False
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1200;sc.render.resolution_y=850;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Studio');sc.display.shading.light='STUDIO';sc.display.shading.color_type='OBJECT';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.background_type='WORLD';sc.world.color=(.13,.13,.13)
bpy.ops.object.camera_add();cam=bpy.context.object;sc.camera=cam;cam.data.type='ORTHO'
pts=[o.matrix_world@v.co for o in objects for v in o.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);center=(lo+hi)/2;size=max(hi-lo)
for name,d in [('side',(3,0,0)),('front',(0,-3,0)),('rear',(0,3,0)),('quarter',(2,-3,1.6)),('top',(0,0,3)),('underside',(1,-1,-2))]:
 cam.location=center+Vector(d)*size;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=size*1.25;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda_Source.blend'));(OUT/'inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
