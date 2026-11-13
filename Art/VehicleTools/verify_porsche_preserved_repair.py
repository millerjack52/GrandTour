import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path('C:/GrandTour/Art/Export/VehicleTools');O=R/'porsche-preserved-repair-v02'
bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Preserved_Repair.blend'));sc=bpy.context.scene
body=bpy.data.objects['Porsche original body - locally repaired'];parts=bpy.data.collections['Porsche - repaired original components'];src=bpy.data.objects['WORKING - original shape unchanged']
bm=bmesh.new();bm.from_mesh(src.data);il=bm.faces.layers.int.get('source_island');sourceparts={}
for f in bm.faces:
 sourceparts.setdefault(f[il],set()).update(f.verts)
bm.verts.ensure_lookup_table();bm.verts.index_update();ss=[v.co*4.5 for v in bm.verts];ff=[[v.index for v in f.verts] for f in bm.faces if f[il]==0];tree=BVHTree.FromPolygons(ss,ff,all_triangles=True)
def stats(v):
 v=sorted(v);return {'count':len(v),'mean':sum(v)/len(v) if v else 0,'p95':v[min(len(v)-1,int(len(v)*.95))] if v else 0,'max':max(v,default=0)}
r={'status':'Scoped source-fidelity and geometry audit; not engine certification','mesh':{},'accessory_preservation':{},'limitations':['Mixed repaired source topology; not a complete artist-authored quad retopology','Static assembly only; rig, LOD, collision and Unreal not validated']}
r['body_vertex_distance_to_original_m']=stats([tree.find_nearest(v.co)[3] for v in body.data.vertices]);r['body_face_centroid_distance_m']=stats([tree.find_nearest(sum((body.data.vertices[k].co for k in f.vertices),Vector())/len(f.vertices))[3] for f in body.data.polygons])
sourcebody=[v.co*4.5 for v in sourceparts[0]];actual=[v.co for v in body.data.vertices];support=[]
for y in range(0,360,10):
 for e in [-60,-30,0,30,60,90]:
  yaw=math.radians(y);e=math.radians(e);d=Vector((math.cos(yaw)*math.cos(e),math.sin(yaw)*math.cos(e),math.sin(e)))
  support.append(abs(max(p.dot(d) for p in sourcebody)-max(p.dot(d) for p in actual)))
r['body_outer_support_difference_m']=stats(support)
for o in parts.objects:
 if o.type!='MESH':continue
 bb=bmesh.new();bb.from_mesh(o.data);r['mesh'][o.name]={'verts':len(bb.verts),'faces':len(bb.faces),'boundary_edges':sum(e.is_boundary for e in bb.edges),'overconnected_edges':sum(len(e.link_faces)>2 for e in bb.edges),'inconsistent_edges':sum(e.is_manifold and not e.is_contiguous for e in bb.edges),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bb.faces)};bb.free()
 if 'source_island' in o:
  island=o['source_island'];points=[v.co*4.5 for v in sourceparts[island]]
  from mathutils.kdtree import KDTree
  kd=KDTree(len(points))
  for i,p in enumerate(points):kd.insert(p,i)
  kd.balance();r['accessory_preservation'][o.name]=stats([kd.find(o.matrix_world@v.co)[2] for v in o.data.vertices])
(O/'verification.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['mesh','accessory_preservation']},indent=2),flush=True)

# Matching clay comparisons, source above and repaired assembly below.
cam=sc.camera;center=Vector((0,0,.94));sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='SINGLE';sc.display.shading.single_color=(.55,.59,.60);sc.display.shading.show_cavity=False
sc.render.resolution_x=1500;sc.render.resolution_y=1250;sc.render.resolution_percentage=100
src.hide_set(False);src.hide_render=False
meshes=[o for o in parts.objects if o.type=='MESH'];bpy.context.view_layer.update();base={o:o.matrix_world.copy() for o in [src]+meshes}
for o in meshes:o.parent=None;o.matrix_world=base[o]
labels=[]
for text in ['ORIGINAL TRIPO','SOURCE-PRESERVING REPAIR']:
 cu=bpy.data.curves.new(text,'FONT');cu.body=text;cu.size=.11;o=bpy.data.objects.new(text,cu);sc.collection.objects.link(o);labels.append(o)
for name,pos,scale,sep in [('comparison-side',(8,0,.94),6.4,1.3),('comparison-quarter',(5,-7,3.4),7.7,1.55)]:
 cam.location=pos;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;rot=cam.rotation_euler.to_matrix();up=rot@Vector((0,1,0));right=rot@Vector((1,0,0));forward=rot@Vector((0,0,1))
 for o in [src]+meshes:o.matrix_world=base[o].copy();o.matrix_world.translation+=up*(sep if o==src else -sep)
 for label,sgn in zip(labels,[1,-1]):label.rotation_euler=cam.rotation_euler;label.location=center+right*(-scale*.36)+up*(sgn*sep+(1.25 if name.endswith('quarter') else 1.03))+forward*3
 sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('COMPARISONS_AND_AUDIT_SAVED',flush=True)
