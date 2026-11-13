import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-assembly-v02/GraphicAdventure_Assembly.blend')
for y in [-.183,-.181,-.1805,-.1795,-.1785,-.1775,-.1765]:
 hits=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or not o.name.startswith('RET |'):continue
  m=o.matrix_world.inverted();orig=m@(Vector((.25,y,.23))*4.6);d=m.to_3x3()@Vector((-1,0,0));yes,loc,n,idx=o.ray_cast(orig,d,distance=.2)
  if yes:hits.append((round((o.matrix_world@loc).x/4.6,6),o.name,list(n)))
 print(y,sorted(hits,reverse=True))
