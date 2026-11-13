import bpy,sys,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04/Porsche_Safari_Review.blend')
body=bpy.data.objects['Porsche original body - locally repaired'];me=body.data;me.calc_loop_triangles();bt=BVHTree.FromPolygons([v.co for v in me.vertices],[t.vertices for t in me.loop_triangles],all_triangles=True)
for n,ax in [('Windscreen',1),('Rear glass',1),('Door glass L',0),('Vent glass L',0),('Quarter glass L',0)]:
 ps=[v.co for v in bpy.data.objects[n].data.vertices];other=[i for i in range(3) if i!=ax];a=np.array([[1,p[other[0]],p[other[1]],p[other[0]]**2,p[other[0]]*p[other[1]],p[other[1]]**2] for p in ps]);co=np.linalg.lstsq(a,[p[ax] for p in ps],rcond=None)[0]
 print(n,'bounds',[[round(fn(p[k] for p in ps),4) for k in range(3)] for fn in (min,max)],'fit',co.tolist(),flush=True)
for y in [-.4,-.2,0,.3,.6,.9,1.1]:
 vals=[]
 for x in [0,.3,.5,.6,.65,.7,.75]:
  h=bt.ray_cast(Vector((x,y,2)),Vector((0,0,-1)),1.2)[0];vals.append(round(h.z,4) if h else None)
 print('ROOF',y,vals,flush=True)
