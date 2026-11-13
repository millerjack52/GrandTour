import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04/Prado_Exterior.blend')
o=bpy.data.objects['Prado | source-fitted body'];tree=BVHTree.FromPolygons([v.co/5 for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
for y in [-.10,-.086,-.06,-.04,0,.07,.14,.19,.25,.32,.35,.38,.419]:
 print('ROOF',y,[(x,tuple(p) if (p:=tree.ray_cast(Vector((x,y,.48)),Vector((0,0,-1)),.15)[0]) else None) for x in [0,.085,.123,.14]])
for o in bpy.context.scene.objects:
 if o.name.startswith('Glass'):
  vs=[o.matrix_world@v.co/5 for v in o.data.vertices]
  print(o.name,[(min(v[i] for v in vs),max(v[i] for v in vs)) for i in range(3)])
print('ROOT',bpy.data.objects['PRADO | working assembly'].matrix_world)
