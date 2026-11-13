import bpy,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04/Porsche_Safari_Review.blend')
s=bpy.context.scene;c=s.camera;c.data.type='ORTHO';c.data.ortho_scale=5.5;c.location=(4.7,7,3.4);c.rotation_euler=(Vector((0,0,.9))-c.location).to_track_quat('-Z','Y').to_euler();s.render.resolution_x=1500;s.render.resolution_y=1050;bpy.context.view_layer.update();frame=c.data.view_frame(scene=s);rx=max(v.x for v in frame);ty=max(v.y for v in frame)
out=[]
for px,py in [(1017,470),(1036,479),(991,458),(826,510),(818,524),(984,462)]:
 q=c.matrix_world@Vector(((2*px/1500-1)*rx,(1-2*py/1050)*ty,0));d=c.matrix_world.to_quaternion()@Vector((0,0,-1));hits=[]
 for j in range(6):
  hit,p,n,i,ob,m=s.ray_cast(bpy.context.evaluated_depsgraph_get(),q,d)
  if not hit:break
  hits.append({'ob':ob.name,'point':list(p),'face':i});q=p+d*.0005
 out.append({'pixel':[px,py],'hits':hits})
print(json.dumps(out))
