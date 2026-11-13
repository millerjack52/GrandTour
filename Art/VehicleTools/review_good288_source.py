import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-source-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_LowPoly_Source.blend'))
sc=bpy.context.scene;ob=next(o for o in sc.objects if o.type=='MESH');bm=bmesh.new();bm.from_mesh(ob.data)
before=len(bm.verts);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bm.normal_update();todo=set(bm.verts);parts=[]
while todo:
 v=todo.pop();vs={v};stack=[v]
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in todo:todo.remove(w);vs.add(w);stack.append(w)
 fs={f for v in vs for f in v.link_faces};parts.append({'vertices':len(vs),'faces':len(fs)})
audit={'raw_vertices':before,'position_welded_vertices':len(bm.verts),'welded_islands':sorted(parts,key=lambda p:-p['faces']),'welded_boundary_edges':sum(e.is_boundary for e in bm.edges),'welded_nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'note':'Read-only diagnostic weld. Imported mesh, UV seams, and custom normals are unchanged.'};bm.free();(P/'connectivity-audit.json').write_text(json.dumps(audit,indent=2));print({k:v for k,v in audit.items() if k!='welded_islands'});print('islands',len(parts))
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.world.use_nodes=True;sc.world.node_tree.nodes.get('Background').inputs[0].default_value=(.23,.26,.3,1);sc.world.node_tree.nodes.get('Background').inputs[1].default_value=.5
for name,pos,power,size in [('Key',(1,-1.5,2),85,1.5),('Fill',(-1,-.2,1),45,1),('Rim',(0,1.5,2),60,1)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size;obj=bpy.data.objects.new(name,data);sc.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((0,0,.18))-obj.location).to_track_quat('-Z','Y').to_euler()
sc.render.resolution_x=1400;sc.render.resolution_y=950
sc.render.filepath=str(P/'textured-quarter.png');bpy.ops.render.render(write_still=True)
c=Vector((0,0,.19));cam=sc.camera;cam.location=c+Vector((-2,3,1.3));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/'textured-rear.png');bpy.ops.render.render(write_still=True)
