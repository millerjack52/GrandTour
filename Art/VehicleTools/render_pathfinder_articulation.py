import bpy,sys,json
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1]);bpy.ops.wm.open_mainfile(filepath=str(out/'Pathfinder_Articulation.blend'));sc=bpy.context.scene;r=bpy.data.objects['GT | Pathfinder controls'];props=['left_front_door','right_front_door','left_rear_door','right_rear_door','steer','roll']
def pose(**values):
 for k in props:r[k]=float(values.get(k,0))
 r.update_tag();sc.frame_set(sc.frame_current);bpy.context.view_layer.update()
sc.cycles.samples=32
for name,cam,values in [('neutral','Review | front quarter',{}),('doors-open','Review | front quarter',dict(left_front_door=55,right_front_door=55,left_rear_door=55,right_rear_door=55)),('open-rear','Review | rear quarter',dict(left_front_door=55,right_front_door=55,left_rear_door=55,right_rear_door=55)),('steering','Detail review | front-module',dict(steer=25)),('open-top','Review | top',dict(left_front_door=55,right_front_door=55,left_rear_door=55,right_rear_door=55))]:
 pose(**values);sc.camera=bpy.data.objects[cam];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
 if name=='open-top':sc.camera.data.ortho_scale*=1.5;sc.render.resolution_x=1200;sc.render.resolution_y=1200
 sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
pose()
