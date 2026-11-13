import bpy,json
from mathutils import Vector
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04/Porsche_Safari_Review.blend')
s=bpy.context.scene;c=s.camera;c.data.type='PERSP';c.data.lens=24;c.location=(.395,.15,1.25);c.rotation_euler=(Vector((.18,-.50,.985))-c.location).to_track_quat('-Z','Y').to_euler();s.render.resolution_x=1500;s.render.resolution_y=1050;bpy.context.view_layer.update()
frame=c.data.view_frame(scene=s);right=max(v.x for v in frame);top=max(v.y for v in frame);z=frame[0].z
out=[]
for px,py in [(713,440),(723,437),(695,446),(717,452),(706,428),(700,450)]:
 d=c.matrix_world.to_quaternion()@Vector(((2*px/1500-1)*right,(1-2*py/1050)*top,z));d.normalize()
 hit,loc,normal,index,obj,m=s.ray_cast(bpy.context.evaluated_depsgraph_get(),c.location,d)
 out.append({'pixel':[px,py],'object':obj.name if obj else None,'point':list(loc),'index':index})
print(json.dumps(out))
