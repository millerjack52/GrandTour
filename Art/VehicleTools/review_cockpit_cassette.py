"""Supplementary isolated instrument review; never overwrites the assembly."""
import bpy,sys,argparse,shutil
from pathlib import Path
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Cockpit_Workshop.blend'))
sc=bpy.context.scene;cam=sc.camera
keep=set(bpy.data.collections['Cabin | instrument cassette'].objects)
for ob in sc.objects:
    if ob.type in ['MESH','FONT','CURVE','SURFACE'] and ob not in keep and ob.name!='Ground':ob.hide_render=True
cam.location=(-.13,.65,1.47);cam.rotation_euler=(Vector((-.41,-.43,1.215))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.69
sc.render.filepath=str(out/'14-instrument-cassette.png');bpy.ops.render.render(write_still=True)
shutil.copy2(__file__,out/Path(__file__).name)
print('CASSETTE_REVIEW_SAVED',flush=True)
