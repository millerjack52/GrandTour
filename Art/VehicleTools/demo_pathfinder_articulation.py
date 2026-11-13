import bpy,sys,json,math,hashlib
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1]);source=out/'Pathfinder_Articulation.blend';sha=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene;r=bpy.data.objects['GT | Pathfinder controls']
doors=['left_front_door','right_front_door','left_rear_door','right_rear_door'];props=doors+['steer','roll']
for frame,opening,steer,roll in [(1,0,0,0),(8,0,0,0),(35,55,0,0),(48,55,0,0),(73,0,0,0),(88,0,25,110),(104,0,-25,240),(120,0,0,360)]:
 for key in props:
  r[key]=float(opening if key in doors else steer if key=='steer' else roll);r.keyframe_insert(data_path='["'+key+'"]',frame=frame)
sc.frame_start=1;sc.frame_end=120;sc.render.fps=24;sc.frame_set(1);sc.camera=bpy.data.objects['Review | front quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];sc['stage']='Separate in-place articulation demo; use manual file for controls'
demo=out/'Pathfinder_Movement_Demo.blend';bpy.ops.wm.save_as_mainfile(filepath=str(demo));bpy.ops.wm.open_mainfile(filepath=str(demo));sc=bpy.context.scene;sc.frame_set(35);bpy.context.view_layer.update()
checks={'door_animation_reopened':abs(bpy.data.objects['Hinge | left_front_door'].rotation_euler.z+math.radians(55))<1e-6}
sc.frame_set(120);bpy.context.view_layer.update();checks['roll_animation_reopened']=abs(bpy.data.objects['Roll | front_1_wheel'].rotation_euler.x-math.tau)<1e-6;checks['manual_blend_unchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==sha
(out/'demo-reopen-checks.json').write_text(json.dumps(checks,indent=2));assert all(checks.values())
sc.render.resolution_x=640;sc.render.resolution_y=460;sc.render.resolution_percentage=100;sc.cycles.samples=12;sc.cycles.use_denoising=True;folder=out/'demo-frames';folder.mkdir(exist_ok=True)
for frame in range(1,121,5):
 sc.frame_set(frame);sc.render.filepath=str(folder/('%03d.png'%frame));bpy.ops.render.render(write_still=True)
print('DEMO_RENDERED',flush=True)
