import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04');bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Safari_Review.blend'));body=bpy.data.objects['Porsche original body - locally repaired'];me=body.data;me.calc_loop_triangles()
r={'corner':[],'nose':[]}
for t in me.loop_triangles:
 ps=[me.vertices[i].co for i in t.vertices];c=sum(ps,Vector())/3;n=(ps[1]-ps[0]).cross(ps[2]-ps[0]).normalized()
 if c.x>.70 and -1.90<c.y<-1.12 and .575<c.z<.725:r['corner'].append({'c':list(c),'n':list(n),'p':[list(p) for p in ps]})
 if abs(c.x)<.76 and c.y<-1.78 and .55<c.z<.74:r['nose'].append({'c':list(c),'n':list(n)})
print(json.dumps(r));(O/'local-diagnosis.json').write_text(json.dumps(r))
