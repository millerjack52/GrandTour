import bpy,json
from mathutils import Vector
from pathlib import Path
R=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02')
bpy.ops.wm.open_mainfile(filepath=str(R/'Porsche_Preserved_Repair.blend'));sc=bpy.context.scene;cam=sc.camera
cam.location=(5.4,-7.2,3.7);cam.rotation_euler=(Vector((0,0,.92))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5.65;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();rot=cam.rotation_euler.to_matrix()
for px,py in [(640,490),(660,505),(680,480),(695,500),(642,520),(711,462)]:
 origin=cam.location+rot@Vector(((px/1600-.5)*5.65,(.5-py/1100)*5.65*1100/1600,0));direction=rot@Vector((0,0,-1))
 h=sc.ray_cast(dg,origin,direction)
 if h[0]:
  p,n,idx,o,ma=h[1:];print('HIT',px,py,o.name,idx,'point',list(p/4.5),'verts',[list((o.matrix_world@o.data.vertices[k].co)/4.5) for k in o.data.polygons[idx].vertices],flush=True)
