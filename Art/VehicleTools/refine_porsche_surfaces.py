import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-cleanup-v01');OUT=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-cleanup-v02');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Assembly.blend'))
sc=bpy.context.scene;cam=sc.camera;body=bpy.data.objects['Body_and_cabin'];parts=body.users_collection[0]
paint=bpy.data.materials.new('Porsche - satin ivory paint');paint.diffuse_color=(.59,.62,.60,1);paint.use_nodes=True
p=paint.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.59,.62,.60,1);p.inputs['Roughness'].default_value=.32;p.inputs['Metallic'].default_value=.16
glass=bpy.data.materials.new('Porsche - clear glazing');glass.use_nodes=True;glass.diffuse_color=(.13,.19,.21,.16)
gp=glass.node_tree.nodes.get('Principled BSDF');gp.inputs['Base Color'].default_value=(.8,.91,.95,1);gp.inputs['Roughness'].default_value=.04;gp.inputs['Transmission Weight'].default_value=1;gp.inputs['IOR'].default_value=1.45
body.data.materials.append(paint);paintid=len(body.data.materials)-1;body.data.materials.append(glass);glassid=len(body.data.materials)-1
image=next(n.image for n in body.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');pixels=np.array(image.pixels[:],dtype=np.float32).reshape(image.size[1],image.size[0],4)
bm=bmesh.new();bm.from_mesh(body.data);uv=bm.loops.layers.uv.active
groups={'Windscreen':[],'Rear_window':[],'Quarter_window_L':[],'Quarter_window_R':[]};paintfaces=0
for f in bm.faces:
 c=f.calc_center_median()/4.5;x,y,z=c;n=f.normal;area=f.calc_area()/4.5**2
 wind=abs(x)<.153 and -.174<y<-.044 and .240<z<.329 and abs(z-(.244+.77*(y+.165)-.035*(x/.14)**2))<.008 and area>.000035
 rear=abs(x)<.13 and .267<y<.350 and .250<z<.315 and abs(n.dot(Vector((0,.6,.8))))>.78 and area>.000045
 quarter=abs(x)>.152 and .133<y<.232 and .246<z<.308 and abs(n.x)>.6 and area>.00006
 if wind or rear or quarter:
  name='Windscreen' if wind else 'Rear_window' if rear else ('Quarter_window_L' if x>0 else 'Quarter_window_R')
  f.material_index=glassid;groups[name].append(f.index);continue
 samples=[]
 for l in f.loops:
  q=l[uv].uv;xx=min(image.size[0]-1,max(0,int(q.x*image.size[0])));yy=min(image.size[1]-1,max(0,int(q.y*image.size[1])));samples.append(pixels[yy,xx,:3])
 rgb=np.mean(samples,axis=0);v=float(np.mean(rgb));sat=float(max(rgb)-min(rgb))
 if v>.34 and sat<.16 and z>.11:
  f.material_index=paintid;paintfaces+=1
# Locally fair broad door pressings, fading to unchanged perimeter landmarks.
moves=[]
for sign in (-1,1):
 vs=[v for v in bm.verts if sign*v.co.x/4.5>.165 and -.135<v.co.y/4.5<.15 and .117<v.co.z/4.5<.242 and any(f.material_index==paintid for f in v.link_faces)]
 data=np.array([tuple(v.co/4.5) for v in vs]);y=data[:,1];z=data[:,2];A=np.column_stack([np.ones(len(vs)),y,z,y*y,y*z,z*z]);values=np.abs(data[:,0]);coef=np.linalg.lstsq(A,values,rcond=None)[0]
 for _ in range(3):
  residual=values-A@coef;keep=np.abs(residual)<.008
  coef=np.linalg.lstsq(A[keep],values[keep],rcond=None)[0]
 for v,row in zip(vs,A):
  x,y,z=v.co/4.5;fade=min(1,(y+.135)/.03,(.15-y)/.03,(z-.117)/.025,(.242-z)/.025);fade=max(0,fade)
  target=sign*float(row@coef);delta=max(-.006,min(.006,target-x))*fade
  v.co.x+=delta*4.5;moves.append(abs(delta)*4.5)
bm.to_mesh(body.data);bm.free()
# Split donor glazing at exactly its original surface boundaries, retaining the body surrounds.
for name,ids in groups.items():
 if not ids:continue
 me=body.data.copy();o=bpy.data.objects.new(name,me);parts.objects.link(o)
 b=bmesh.new();b.from_mesh(me);b.faces.ensure_lookup_table();keep=set(ids);bmesh.ops.delete(b,geom=[f for f in b.faces if f.index not in keep],context='FACES');bmesh.ops.delete(b,geom=[v for v in b.verts if not v.link_faces],context='VERTS')
 b.to_mesh(me);b.free();me.materials.clear();me.materials.append(glass)
 for f in me.polygons:f.material_index=0;f.use_smooth=True
b=bmesh.new();b.from_mesh(body.data);b.faces.ensure_lookup_table();removed=set(i for ids in groups.values() for i in ids);bmesh.ops.delete(b,geom=[f for f in b.faces if f.index in removed],context='FACES');bmesh.ops.delete(b,geom=[v for v in b.verts if not v.link_faces],context='VERTS');b.to_mesh(body.data);b.free()
report={'glass_faces':{n:len(ids) for n,ids in groups.items()},'satin_paint_faces':paintfaces,'door_fairing_max_m':max(moves),'body':'UVs and source silhouette retained; selective cleanup rather than full quad retopology'}
(OUT/'refinement-report.json').write_text(json.dumps(report,indent=2))
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.transparent_max_bounces=12;sc.cycles.transmission_bounces=12;cam.data.ortho_scale=5.8
for name,pos in [('quarter',(5.4,-7.2,4.5)),('side',(5.4,0,1)),('rear',(5,7,4))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Porsche_Assembly.blend'))
print('REFINED',report,flush=True)
