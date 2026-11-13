import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-benmore-paint/Ferrari288_GT_Painted.blend')
bpy.ops.wm.open_mainfile(filepath=str(p))
o=bpy.data.objects['Body | original textured shell'];verts=[o.matrix_world@v.co for v in o.data.vertices];bvh=BVHTree.FromPolygons(verts,[p.vertices[:] for p in o.data.polygons])
samples=[]
for x in [-.65,-.55,0,.55,.65]:
 for y in [-.4,-.2,0,.2,.4,.6,.8,1.]:
  hit,n,i,d=bvh.ray_cast(Vector((x,y,3)),Vector((0,0,-1)),3)
  samples.append({'x':x,'y':y,'z':hit.z if hit else None,'normal':list(n) if n else None})
w=[]
for o in bpy.data.objects:
 if o.name.startswith('Wheel_'):
  vv=[o.matrix_world@v.co for v in o.data.vertices];w.append({'name':o.name,'pivot':list(o.get('pivot',[])),'bounds':[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]],'materials':[m.name for m in o.data.materials]})
Path('C:/GrandTour/Art/VehicleTools/ferrari-roof-survey.json').write_text(json.dumps({'roof':samples,'wheels':w},indent=2))
