import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-tidy-v03/Porsche_Tidy.blend');s=bpy.context.scene;c=s.camera;c.location=(3,-4,1.65);c.rotation_euler=(Vector((.45,-1.78,.72))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=1.9;bpy.context.view_layer.update();o=bpy.data.objects['Porsche original body - locally repaired'];o.data.calc_loop_triangles();tr=BVHTree.FromPolygons([v.co for v in o.data.vertices],[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
for px,py in [(995,694),(1020,690),(977,709),(1005,705)]:
 org=c.matrix_world@Vector(((px/1600-.5)*1.9,(.5-py/1100)*1.9*1100/1600,-.01));d=c.rotation_euler.to_quaternion()@Vector((0,0,-1));h=tr.ray_cast(org,d,10)
 print('PIXEL',px,py,'HIT',list(h[0]) if h[0] else None,'normal',list(h[1]) if h[1] else None)
