exec(open('C:/GrandTour/Art/VehicleTools/inspect_porsche_dashboard_shard.py').read().split('out=[]')[0])
c.data.type='ORTHO';c.data.ortho_scale=4.4;c.location=(4,-3,.9);c.rotation_euler=(Vector((.5,-.4,.7))-c.location).to_track_quat('-Z','Y').to_euler();s.render.resolution_x=1600;s.render.resolution_y=1100
for o in bpy.data.collections['04 Wheels and running gear'].objects:
 if o.name.startswith('Wheel_'):o.hide_set(True)
bpy.context.view_layer.update();frame=c.data.view_frame(scene=s);right=max(v.x for v in frame);top=max(v.y for v in frame);out=[]
for px,py in [(717,590),(719,620),(646,558),(556,666),(1464,575),(1450,596),(739,588)]:
 q=c.matrix_world@Vector(((2*px/1600-1)*right,(1-2*py/1100)*top,0));d=c.matrix_world.to_quaternion()@Vector((0,0,-1))
 hit,loc,normal,index,obj,m=s.ray_cast(bpy.context.evaluated_depsgraph_get(),q,d)
 out.append({'pixel':[px,py],'object':obj.name if obj else None,'point':list(loc),'index':index})
print(json.dumps(out))
