import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-cleanup-v02');OUT=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-review-v01');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Assembly.blend'))
sc=bpy.context.scene;body=bpy.data.objects['Body_and_cabin'];parts=body.users_collection[0];paint=bpy.data.materials['Porsche - satin ivory paint'];glass=bpy.data.materials['Porsche - clear glazing'];black=bpy.data.materials['Porsche - underbody']
def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=.3;return m
red=mat('Porsche - rear red lens',(.38,.025,.015));amber=mat('Porsche - amber lens',(.8,.25,.018))
body.data.materials.clear()
for m in [paint,black,red,amber,glass]:body.data.materials.append(m)
extra=0
for f in body.data.polygons:
 c=f.center/4.5;x,y,z=c;f.material_index=0
 if z<.11 or (y>.44 and z<.145) or (y<-.42 and z<.137):f.material_index=1
 if y>.44 and abs(x)>.135 and .146<z<.195:f.material_index=2
 if y<-.437 and abs(x)>.10 and .112<z<.14:f.material_index=3
 # Remaining thin donor windshield fragments must transmit as well.
 if abs(x)<.154 and -.169<y<-.045 and .238<z<.328 and abs(z-(.244+.77*(y+.165)-.035*(x/.14)**2))<.011 and f.area/(4.5**2)>.000025:
  f.material_index=4;extra+=1
for n in ['Mirror_L','Mirror_R']:
 o=bpy.data.objects.get(n)
 if o:
  o.data.materials.clear();o.data.materials.append(paint)
  for f in o.data.polygons:f.material_index=0
# Fair glazing normals using the original pane points, removing the baked reflections.
for name in ['Windscreen','Rear_window','Quarter_window_L','Quarter_window_R']:
 o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0025)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 data=np.array([tuple(v.co/4.5) for v in o.data.vertices]);x,y,z=data.T
 if name in ('Windscreen','Rear_window'):
  A=np.column_stack([np.ones(len(x)),y,x*x,y*y]);coeff=np.linalg.lstsq(A,z,rcond=None)[0]
  for v,zz in zip(o.data.vertices,A@coeff):v.co.z=float(zz)*4.5
 else:
  A=np.column_stack([np.ones(len(x)),y,z]);coeff=np.linalg.lstsq(A,x,rcond=None)[0]
  for v,xx in zip(o.data.vertices,A@coeff):v.co.x=float(xx)*4.5
 for p in o.data.polygons:p.use_smooth=True
 # A thin pane uses mostly straight-through light; its reflection remains angle dependent.
nt=glass.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');mix=nt.nodes.new('ShaderNodeMixShader');tr=nt.nodes.new('ShaderNodeBsdfTransparent');gl=nt.nodes.new('ShaderNodeBsdfGlossy');gl.inputs['Color'].default_value=(.76,.87,.91,1);gl.inputs['Roughness'].default_value=.075;fr=nt.nodes.new('ShaderNodeFresnel');fr.inputs['IOR'].default_value=1.45
nt.links.new(fr.outputs[0],mix.inputs[0]);nt.links.new(tr.outputs[0],mix.inputs[1]);nt.links.new(gl.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],out.inputs['Surface'])
sc.render.engine='CYCLES';sc.cycles.samples=40;cam=sc.camera;cam.data.ortho_scale=5.8
for name,pos in [('quarter',(5.4,-7.2,4.5)),('side',(5.4,0,1)),('rear',(5,7,4)),('front',(0,-7.5,1))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(5.4,-7.2,4.5);cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Porsche_Assembly.blend'))
print('SAVED_REVIEW',extra,flush=True)
