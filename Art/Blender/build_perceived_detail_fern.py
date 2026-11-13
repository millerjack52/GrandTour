"""Preserve Cascade_0 geometry, add leaflet UVs and ray-tested vertex AO in UV1."""
import bpy,sys,math,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
# Load definitions only; the normal full-library generation stays untouched.
source=(HERE/'build_lidar_bank_section.py').read_text().split("for kind,label in enumerate")[0]
source=source.replace("[(0,0)]*6","[(0,0),(.48,.115),(1,.5),(.48,.885),(0,1),(.48,.5)]")
ns={'__file__':str(HERE/'build_lidar_bank_section.py')};exec(compile(source,'bank-definitions','exec'),ns)
L=ns['L'];out=Path('C:/GrandTour/Art/Export/LidarStudy/FirstSection/PerceivedDetail');out.mkdir(exist_ok=True)
rows=[]
for lod in range(3):
 g,probes=ns['build'](ns['design'](0,0),0,lod);ob,_=L.to_object(g,'SM_RS7_Cascade_0_LOD'+str(lod),ns['mats'],[0,1])
 mesh=ob.data;uv=mesh.uv_layers.new(name='SelfOcclusion');tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
 ao=[]
 for vert in mesh.vertices:
  normal=vert.normal.normalized();side=normal.cross(Vector((.23,.71,.37))).normalized();up=normal.cross(side);hits=0
  for k in range(12):
   z=(k+.5)/12;radius=math.sqrt(1-z*z);angle=k*2.399963
   direction=(normal*z+side*(math.cos(angle)*radius)+up*(math.sin(angle)*radius)).normalized()
   hit=tree.ray_cast(vert.co+normal*.003,direction,.36)
   if hit[0] is not None:hits+=1
  ao.append(1-.45*hits/12)
 for loop in mesh.loops:uv.data[loop.index].uv=(ao[loop.vertex_index],.5)
 L.export(ob,out=out);rows.append(dict(lod=lod,vertices=len(mesh.vertices),min_ao=min(ao),mean_ao=sum(ao)/len(ao),positions_sha256=hashlib.sha256(str([list(v.co) for v in mesh.vertices]).encode()).hexdigest()))
 ob.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fern-detail.blend'))
(out/'fern-detail.json').write_text(json.dumps(rows,indent=2))
print('PD_FERN_BUILT')
