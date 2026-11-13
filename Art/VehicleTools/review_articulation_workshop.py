"""Native pose renders and a separate animated inspection copy."""
import bpy,sys,json,argparse,shutil
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));import articulation_workshop as ar
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--top-only',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Articulation_Workshop.blend'))
sc=bpy.context.scene;cam=sc.camera;sc.cycles.samples=48;sc.render.threads_mode='FIXED';sc.render.threads=10;sc.render.resolution_x=1200;sc.render.resolution_y=900
views={'whole':((5,-7,3.5),(0,.04,.88),6.05,'ORTHO'),'rear':((4.8,6,3.7),(0,.10,.95),6.05,'ORTHO'),'top':((0,.10,7),(0,.10,0),6.70,'ORTHO'),'wheel':((3.7,-4.5,1.45),(.70,-1.25,.58),2.75,'ORTHO'),'driver':((-.410,.260,1.485),(-.410,-.90,1.080),20,'PERSP')}
def render(name,key):
    loc,target,size,typ=views[key];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type=typ
    if typ=='ORTHO':cam.data.ortho_scale=size
    else:cam.data.lens=size
    bpy.data.objects['Cockpit review fill'].hide_render=key!='driver';sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True);bpy.data.objects['Cockpit review fill'].hide_render=True
if a.top_only:
    ar.neutral();ar.set_controls(**{k:60. for k in ar.DOORS});render('04-open-top','top');ar.neutral();ar.set_controls(steer=30.);render('06-steering-top','top');shutil.copy2(__file__,out/Path(__file__).name);print('TOP_REVIEWS_SAVED',flush=True);sys.exit(0)
ar.neutral();render('01-neutral','whole')
ar.set_controls(**{k:60. for k in ar.DOORS});render('02-open-doors','whole');render('03-open-rear','rear');render('04-open-top','top')
ar.neutral();ar.set_controls(steer=30.);render('05-steering-left','wheel');render('06-steering-top','top');render('07-linked-steering-wheel','driver')
# A saved demo is a derivative; the manual-control file stays neutral and action-free.
ar.neutral();r=ar.root();sc.frame_start=1;sc.frame_end=180;sc.render.fps=24
poses=[(1,{}),(25,{k:60. for k in ar.DOORS}),(55,{k:60. for k in ar.DOORS}),(80,{}),(105,dict(steer=25.,roll=90.)),(130,dict(steer=-25.,roll=180.)),(160,dict(roll=360.)),(180,dict(roll=360.))]
for frame,values in poses:
    for k in ar.PROPS:r[k]=values.get(k,0.);r.keyframe_insert(data_path='["'+k+'"]',frame=frame)
action=r.animation_data.action;action.name='GT inspection | doors steer and roll'
for layer in action.layers:
    for strip in layer.strips:
        if hasattr(strip,'channelbags'):
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for kp in fc.keyframe_points:kp.interpolation='LINEAR'
sc.frame_set(1);loc,target,size,typ=views['whole'];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type=typ;cam.data.ortho_scale=size
sc['inspection_demo']='Frames 1–80 doors; 80–160 steering and wheel rotation; 160–180 neutral. In-place kinematic inspection, no driving physics.'
for o in bpy.context.selected_objects:o.select_set(False)
r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RangeRover_Movement_Demo.blend'))
# Reopen and evaluate animation rather than assuming the saved action works.
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Movement_Demo.blend'));sc=bpy.context.scene;sc.frame_set(25)
door=bpy.data.objects['Hinge | left_front_door'].rotation_euler.z;assert abs(door+1.04719755)<1e-5
sc.frame_set(105);spin=bpy.data.objects['Roll pivot | left_front_wheel'].rotation_euler.x;assert abs(spin-1.57079633)<1e-5
(out/'demo-reopen-check.json').write_text(json.dumps(dict(door_60_degrees_at_frame_25=True,wheel_roll_90_degrees_at_frame_105=True,animated_properties=len(ar.PROPS)),indent=2))
shutil.copy2(__file__,out/Path(__file__).name);print('MOVEMENT_REVIEW_AND_DEMO_SAVED',flush=True)
