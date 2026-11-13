import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-working-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_LowPoly_Working.blend'))
body=bpy.data.objects['Body | original textured shell'];me=body.data;mat=body.matrix_world
vs=[list(mat@v.co) for v in me.vertices];fs=[list(p.vertices) for p in me.polygons]
(P/'body-data.json').write_text(json.dumps({'verts':vs,'polys':fs}))
large=[]
for p in me.polygons:
 coords=[Vector(vs[i]) for i in p.vertices];c=sum(coords,Vector())/len(coords)
 if c.z>.265 and -.24<c.y<.39 and p.area>.0003:large.append({'i':p.index,'c':list(c),'area':p.area,'v':[list(p) for p in coords]})
(P/'window-faces.json').write_text(json.dumps(large,indent=2))
for o in bpy.context.scene.objects:
 if o.type=='MESH' and o!=body:o.hide_render=True
body.show_wire=True;body.show_all_edges=True
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1800;sc.render.resolution_y=1200
wire=body.copy();wire.data=body.data.copy();sc.collection.objects.link(wire);wire.color=(.01,.01,.01,1);m=wire.modifiers.new('Survey wire','WIREFRAME');m.thickness=.00016;m.use_replace=True
cam=sc.camera
for name,d in [('body-side',(3,0,0)),('body-front',(0,-3,.1)),('body-rear',(0,3,.2)),('body-quarter',(2,-3,1.3))]:
 c=Vector((0,-.01,.29));cam.location=c+Vector(d);cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.98;sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
print('LARGE WINDOW FACES',len(large))
