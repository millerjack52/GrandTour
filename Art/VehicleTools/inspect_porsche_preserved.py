import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('C:/GrandTour/Art/Export/VehicleTools');O=R/'porsche-preserved-study';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'porsche-source-v01/Porsche_Analysed.blend'))
sc=bpy.context.scene;o=next(o for o in sc.objects if o.type=='MESH')
for p in o.data.polygons:p.use_smooth=True
o.data.set_sharp_from_angle(angle=1.05)
bm=bmesh.new();bm.from_mesh(o.data);layer=bm.faces.layers.int.get('source_island');uv=bm.loops.layers.uv.active
im=next(n.image for n in o.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');pix=np.array(im.pixels[:]).reshape(im.size[1],im.size[0],4)
rows=[]
for f in bm.faces:
 if f[layer]!=0:continue
 c=f.calc_center_median();x,y,z=c
 if z<.235:continue
 rgb=[]
 for l in f.loops:
  q=l[uv].uv;rgb.append(pix[min(im.size[1]-1,max(0,int(q.y*im.size[1]))),min(im.size[0]-1,max(0,int(q.x*im.size[0])))][:3])
 rows.append({'id':f.index,'c':list(c),'n':list(f.normal),'a':f.calc_area(),'rgb':np.mean(rgb,axis=0).tolist(),'vs':[list(v.co) for v in f.verts]})
(O/'upper-face-data.json').write_text(json.dumps(rows))
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='SINGLE';sc.display.shading.single_color=(.5,.55,.57);sc.display.shading.light='STUDIO';sc.display.shading.show_cavity=False;sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world.color=(.11,.12,.13)
sc.render.resolution_x=1500;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
cam=sc.camera;cam.data.type='ORTHO';cam.data.ortho_scale=1.18
for name,pos in [('smooth-quarter',(1.3,-1.8,.95)),('smooth-side',(1.5,0,.20)),('smooth-rear',(1.3,1.8,.8)),('smooth-top',(0,0,2))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.19))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('DIAGNOSED',len(rows),flush=True)
