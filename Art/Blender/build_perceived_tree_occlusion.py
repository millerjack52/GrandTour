"""Bake bounded canopy cavity shading into existing colours, preserving geometry."""
import bpy,sys,math,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import build_lidar_forest as F
L=F.L;B=F.B;OUT=HERE.parent/'Export/LidarStudy/FirstSection/PerceivedDetail'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
D,n=F.design('Mature');s=F.SPECS['Mature'];g,_=B.emit(D,0,s['budget'][0]);scale=s['height']/max(v.z for v in g.v)
objects=[]
for lod in range(3):
 g,_=B.emit(D,lod,s['budget'][lod]);g.v=[v*scale for v in g.v]
 ob,_=L.to_object(g,'SM_PD_CanopyAO_LOD'+str(lod),L.plant_materials(),[0,1]);objects.append(ob)
source=objects[0].data;tree=BVHTree.FromPolygons([v.co for v in source.vertices],[list(p.vertices) for p in source.polygons]);rows=[]
for lod,ob in enumerate(objects):
 mesh=ob.data;ao=[]
 for vert in mesh.vertices:
  normal=vert.normal.normalized();side=normal.cross(Vector((.23,.71,.37))).normalized();up=normal.cross(side);hits=0
  for k in range(16):
   z=math.sqrt((k+.5)/16);radius=math.sqrt(1-z*z);angle=k*2.399963
   direction=(normal*z+side*(math.cos(angle)*radius)+up*(math.sin(angle)*radius)).normalized()
   hit=tree.ray_cast(vert.co+normal*.025,direction,5.)
   if hit[0] is not None:hits+=1
  # Limited cavity tint: no painted sun direction; retain 65% even in deep overlap.
  ao.append(1-.35*hits/16)
 colours=mesh.color_attributes.active_color
 assert colours.domain=='CORNER'
 for poly in mesh.polygons:
  if poly.material_index!=1:continue
  for index in poly.loop_indices:
   c=colours.data[index].color;factor=ao[mesh.loops[index].vertex_index]
   colours.data[index].color=(c[0]*factor,c[1]*factor,c[2]*factor,c[3])
 rows.append(dict(lod=lod,vertices=len(mesh.vertices),min_factor=min(ao),mean_factor=sum(ao)/len(ao),position_hash=hashlib.sha256(str([list(v.co) for v in mesh.vertices]).encode()).hexdigest()))
 L.export(ob,out=OUT);ob.hide_set(True);ob.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'canopy-occlusion.blend'))
(OUT/'canopy-occlusion.json').write_text(json.dumps(dict(method='16 cosine-weighted hemisphere rays, 5m maximum, 2.5cm origin bias, 35% maximum cavity tint; LOD0 occluder for all LODs; bark and vertex alpha unchanged',lods=rows),indent=2))
print('PD_CANOPY_OCCLUSION_COMPLETE')
