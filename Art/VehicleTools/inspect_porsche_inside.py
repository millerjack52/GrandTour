import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-window-repair-v05/Porsche_Window_Repair.blend')
s=bpy.context.scene;c=s.camera;c.location=(4,-3,2.4);c.rotation_euler=(Vector((.68,.05,1.25))-c.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();q=c.rotation_euler.to_quaternion();right=q@Vector((1,0,0));up=q@Vector((0,1,0));fwd=q@Vector((0,0,-1));dg=bpy.context.evaluated_depsgraph_get()
for px,py in [(925,402),(925,410),(980,410),(685,464),(665,505),(1160,429),(1180,432)]:
 p=c.location+right*((px/1400-.5)*2)+up*((.5-py/1000)*2*1000/1400)
 hits=[]
 for i in range(12):
  h=s.ray_cast(dg,p,fwd,distance=20)
  if not h[0]:break
  hits.append((h[4].name,[round(v,4) for v in h[1]]));p=h[1]+fwd*.0003
 print('RAY',px,py,hits,flush=True)
