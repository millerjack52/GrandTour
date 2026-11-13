"""Freeze the replacement GLB without modifying its geometry or imported normals."""
import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector
SRC=Path('C:/Users/mille/Downloads/good288.glb')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-source-v01');OUT.mkdir(exist_ok=True)
assert not (OUT/'Ferrari288_LowPoly_Source.blend').exists(),'Preserve baseline'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(SRC))
sc=bpy.context.scene;objects=[o for o in sc.objects if o.type=='MESH'];report={'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'objects':[]}
for o in objects:
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();islands=[]
 for seed in bm.verts:
  if seed in seen:continue
  seen.add(seed);vs={seed};stack=[seed]
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    w=e.other_vert(v)
    if w not in seen:seen.add(w);vs.add(w);stack.append(w)
  fs={f for v in vs for f in v.link_faces};islands.append({'vertices':len(vs),'faces':len(fs)})
 report['objects'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'uv_layers':len(o.data.uv_layers),'materials':[m.name for m in o.data.materials if m],'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'islands':sorted(islands,key=lambda a:-a['faces'])});bm.free();o.color=(.55,.57,.58,1)
report['images']=[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in bpy.data.images]
sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1500;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Neutral inspection');sc.world.color=(.11,.12,.14);sh=sc.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
bpy.ops.object.camera_add();cam=bpy.context.object;sc.camera=cam;cam.data.type='ORTHO'
pts=[o.matrix_world@v.co for o in objects for v in o.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);center=(lo+hi)/2;size=max(hi-lo)
report['world_bounds']=[list(lo),list(hi)]
for name,d in [('quarter',(2,-3,1.3)),('side',(3,0,0)),('front',(0,-3,0)),('rear',(0,3,0)),('top',(0,0,3))]:
 cam.location=center+Vector(d)*size;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=size*1.22;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=center+Vector((2,-3,1.3))*size;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.overlay.show_overlays=False;a.spaces.active.region_3d.view_location=center;a.spaces.active.region_3d.view_distance=size*1.8;a.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_LowPoly_Source.blend'));(OUT/'inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
