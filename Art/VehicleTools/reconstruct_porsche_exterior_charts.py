"""Source-registered exterior chart study: radial ray sampling, no inferred body profiles.
Charts query only the original main body. No voxel or nearest-sheet projection.
"""
import bpy,bmesh,math,json,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
R=Path('C:/GrandTour/Art/Export/VehicleTools');O=R/'porsche-source-chart-v01';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'porsche-source-repair-v01/Porsche_Source_Repaired.blend'));sc=bpy.context.scene
parts=bpy.data.collections['Porsche - repaired original components'];old=bpy.data.objects['Body_original_repaired'];old.hide_render=True;old.hide_set(True)
src=bpy.data.objects['WORKING - original shape unchanged']
bm=bmesh.new();bm.from_mesh(src.data);il=bm.faces.layers.int.get('source_island');bmesh.ops.delete(bm,geom=[f for f in bm.faces if f[il]!=0],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table();bm.verts.index_update()
def mat(n,c,rough=.45,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
paint=mat('Source fitted ivory',(.56,.6,.58),.34,.15);black=mat('Window gaskets',(.027,.039,.042),.6);glass=mat('Glazing',(.14,.23,.27),.07);glass.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.97;glass.node_tree.nodes.get('Principled BSDF').inputs['IOR'].default_value=1.45
sourceuv=bm.loops.layers.uv.active
img=next(n.image for n in src.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');pix=np.array(img.pixels[:]).reshape(img.size[1],img.size[0],4)
# The thin raised spoiler remains its own original mesh rather than being folded into a hull.
spoiler=[];shell=[]
for f in bm.faces:
 c=f.calc_center_median()
 if c.y>.354 and c.z>.248-.30*(c.y-.354):spoiler.append(f)
 else:shell.append(f)
def source_object(name,fs):
 vs=list({v for f in fs for v in f.verts});ix={v:i for i,v in enumerate(vs)};me=bpy.data.meshes.new(name);me.from_pydata([v.co*4.5 for v in vs],[],[[ix[v] for v in f.verts] for f in fs]);me.update();o=bpy.data.objects.new(name,me);parts.objects.link(o);me.materials.append(paint)
 for f in me.polygons:f.use_smooth=True
 o.color=(.52,.56,.58,1);return o
source_object('Original raised spoiler',spoiler)
tree=BVHTree.FromPolygons([v.co for v in bm.verts],[[v.index for v in f.verts] for f in shell],all_triangles=True)
def ray(y,t):
 direction=Vector((math.sin(t),0,math.cos(t)));origin=Vector((0,y,.062))
 hit=tree.ray_cast(origin+direction*.7,-direction,1.0)
 if hit[0] is None:return None
 p,n,k,d=hit;f=shell[k]
 # Reject inward cabin/body surfaces reached through original open window or wheel hole.
 if abs(p.x)<.140 and abs(t)>1.05:return None
 if p.z<.076:return None
 # Door windows are original open apertures. Keep their negative space.
 if -.12<y<.143 and p.z>.239 and abs(p.x)<(.186-(p.z-.239)*.47) and abs(t)>.48:return None
 return ((p-origin).dot(direction),p,f)
NY=241;NT=161;ys=np.linspace(-.468,.49,NY);ts=np.linspace(-1.63,1.63,NT)
rad=np.full((NY,NT),np.nan);hits={}
for i,y in enumerate(ys):
 for j,t in enumerate(ts):
  h=ray(float(y),float(t))
  if h:rad[i,j]=h[0];hits[i,j]=h
raw=rad.copy()
# Bilateral fairing rejects distant or disconnected sheets and caps displacement at 6.75 mm.
for step in range(4):
 nxt=rad.copy()
 for i in range(1,NY-1):
  for j in range(1,NT-1):
   r=rad[i,j]
   if not np.isfinite(r):continue
   near=rad[i-1:i+2,j-1:j+2];values=near[np.isfinite(near)&(np.abs(near-r)<.012)]
   if len(values)<7:continue
   target=float(np.mean(values));nxt[i,j]=raw[i,j]+max(-.0015,min(.0015,target-raw[i,j]))
 rad=nxt
vs=[];index={};coords={}
for i,y in enumerate(ys):
 for j,t in enumerate(ts):
  if not np.isfinite(rad[i,j]):continue
  p=Vector((math.sin(t)*rad[i,j],y,.062+math.cos(t)*rad[i,j]));index[i,j]=len(vs);coords[len(vs)]=(i,j);vs.append(tuple(p*4.5))
fs=[];mats=[]
def appearance(f,p):
 x,y,z=p;uvs=[Vector((*l[sourceuv].uv,0)) for l in f.loops]
 q=barycentric_transform(p,*[v.co for v in f.verts],*uvs)
 rgb=pix[min(img.size[1]-1,max(0,int(q.y*img.size[1]))),min(img.size[0]-1,max(0,int(q.x*img.size[0])))][:3];value=float(np.mean(rgb))
 wind=abs(x)<.16 and -.17<y<-.026 and z>.24 and abs(z-(.244+.77*(y+.165)-.030*(x/.14)**2))<.014
 rear=abs(x)<.14 and .21<y<.355 and z>.249
 side=abs(x)>.135 and .12<y<.26 and z>.239
 if (wind or rear or side) and value<.34:return 2
 return 0
for i in range(NY-1):
 for j in range(NT-1):
  keys=[(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
  if not all(k in index for k in keys):continue
  # Never bridge a discontinuity across separate original surfaces.
  if max(rad[k] for k in keys)-min(rad[k] for k in keys)>.033:continue
  p=Vector((sum(vs[index[k]][a] for k in keys)/4/4.5 for a in range(3)))
  h=ray((ys[i]+ys[i+1])/2,(ts[j]+ts[j+1])/2)
  if h is None:continue
  fs.append(tuple(index[k] for k in keys));mats.append(appearance(h[2],h[1]))
me=bpy.data.meshes.new('Original exterior structured charts');me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new('Source sampled exterior',me);parts.objects.link(o)
for m in [paint,black,glass]:me.materials.append(m)
for f,mi in zip(me.polygons,mats):f.material_index=mi;f.use_smooth=True
bb=bmesh.new();bb.from_mesh(me);bmesh.ops.recalc_face_normals(bb,faces=list(bb.faces));bb.to_mesh(me);bb.free();o.color=(.52,.56,.58,1)
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_cavity=False
cam=sc.camera;cam.data.ortho_scale=5.65
for name,pos in [('quarter',(5.4,-7.2,3.7)),('side',(7,0,.92)),('rear',(5.4,7.2,3.8)),('front',(0,-8,.92)),('top',(0,0,8))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.92))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Source_Charts.blend'))
print('CHARTS',len(vs),len(fs),flush=True)
