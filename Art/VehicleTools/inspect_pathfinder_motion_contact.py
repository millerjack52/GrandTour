import bpy,json
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/pathfinder-articulation-v06/Pathfinder_Articulation.blend');sc=bpy.context.scene;r=bpy.data.objects['GT | Pathfinder controls']
for pos,angle in [('front',1.5),('rear',2)]:
 r['left_front_door']=0.;r['left_rear_door']=0.;r['left_'+pos+'_door']=angle;r.update_tag();sc.frame_set(1);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();shapes=[]
 for name in ['Left '+pos+' | moving window frame','Left | continuous cabin frame']:
  ob=bpy.data.objects[name];eo=ob.evaluated_get(dg);me=eo.to_mesh();me.calc_loop_triangles();vs=[ob.matrix_world@v.co for v in me.vertices];fs=[tuple(t.vertices) for t in me.loop_triangles];shapes.append((vs,fs,BVHTree.FromPolygons(vs,fs,all_triangles=True)));eo.to_mesh_clear()
 hits=shapes[0][2].overlap(shapes[1][2]);vv=[shapes[0][0][i] for a,b in hits for i in shapes[0][1][a]];print('CONTACT '+pos,json.dumps([[min(v[i] for v in vv),max(v[i] for v in vv)] for i in range(3)]))
