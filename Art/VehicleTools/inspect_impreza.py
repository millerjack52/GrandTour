import bpy,sys,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index('--')+1]);rows=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or o.hide_render:continue
 pts=[o.matrix_world@Vector(p) for p in o.bound_box];lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
 if lo[1]<-2.25 or o.name.startswith('Front |') or 'Hinge' in o.name:rows.append([o.name,lo,hi,len(o.data.vertices),len(o.data.polygons)])
print(json.dumps(rows,indent=2))
