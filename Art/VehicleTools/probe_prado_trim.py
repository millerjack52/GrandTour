import bpy,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v03/Prado_Exterior.blend')
dg=bpy.context.evaluated_depsgraph_get()
for y in [-.045,-.04,-.039,-.038,-.035]:
 for z in [.395,.390,.385,.31,.307,.305]:
  hit,p,n,i,o,m=bpy.context.scene.ray_cast(dg,Vector((2,y*5,z*5)),Vector((-1,0,0)),distance=3)
  if hit and not o.name.startswith('Glass'):print(y,z,o.name,i,list(p/5))
