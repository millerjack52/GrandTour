import bpy,sys
from pathlib import Path
from mathutils import Vector
OUT=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path('C:/GrandTour/Art/Export/VehicleTools/panda-assembly-v02');S=3.6
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Panda_Assembly.blend'));sc=bpy.context.scene;cam=sc.camera;sc.render.engine='BLENDER_WORKBENCH'
views=[('front',(0,-3,.268),(0,0,.268),.86),('rear',(0,3,.268),(0,0,.268),.86),('top',(0,0,3),(0,0,.268),1.62),('underside',(1.2,1.4,-2),(0,0,.268),1.25),('review-front-arch',(1,-.45,.25),(.19,-.25,.18),.40),('review-door-seam',(1,.18,.31),(.2,.13,.29),.38),('review-rear-corner',(1,1,.4),(.17,.44,.32),.37)]
for name,pos,target,scale in views:
 cam.location=Vector(pos)*S;cam.rotation_euler=(Vector(target)*S-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*S;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)

