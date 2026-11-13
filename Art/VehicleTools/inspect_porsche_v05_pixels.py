import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-window-repair-v05/Porsche_Window_Repair.blend')
s=bpy.context.scene;c=s.camera;c.location=(4,-3,2.4);c.rotation_euler=(Vector((.68,.05,1.25))-c.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();q=c.rotation_euler.to_quaternion();right=q@Vector((1,0,0));up=q@Vector((0,1,0));fwd=q@Vector((0,0,-1));dg=bpy.context.evaluated_depsgraph_get()
for px,py in [(350,835),(360,835),(365,837),(330,828),(358,846),(1450,439),(1130,455)]:
 p=c.location+right*((px/1600-.5)*2)+up*((.5-py/1100)*2*1100/1600)
 h=s.ray_cast(dg,p,fwd,distance=20);print('PIXEL',px,py, h[4].name if h[0] else None,list(h[1]) if h[0] else None,flush=True)
for o in s.objects:
 if o.type=='MESH' and o.name!='Porsche original body - locally repaired' and '| fitted pane' not in o.name and '| clean gasket' not in o.name:o.hide_render=True
s.render.filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-window-repair-v05/isolated-cabin.png';c.data.ortho_scale=2;bpy.ops.render.render(write_still=True)
