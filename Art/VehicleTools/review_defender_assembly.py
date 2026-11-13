import bpy,sys,json
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/defender-assembly-v02')
bpy.ops.wm.open_mainfile(filepath=str(P/'Defender_Assembly.blend'))
sc=bpy.context.scene;cam=sc.camera;sh=sc.display.shading
sh.color_type='SINGLE';sh.single_color=(.75,.75,.75);sh.light='STUDIO';sh.show_shadows=False
sh.show_cavity=True;sh.background_type='WORLD';sc.world.color=(.065,.095,.13)
sc.render.resolution_x=1600;sc.render.resolution_y=1100
def render(name,pos,scale,target):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
render('review-quarter',(7,-9,3),6.2,(0,0,1.1))
render('review-rear-corner',(-7,8,1.1),2.7,(-.7,1.8,1.3))
render('review-roof-joins',(8,0,2),4.4,(.8,.1,1.9))
render('review-front',(0,-9,1.1),4,(0,0,1.1))
render('review-rear',(0,9,1.1),4,(0,0,1.1))
render('review-bottom',(0,0,-9),6.2,(0,0,0))
for o in bpy.data.objects:
 if o.name.startswith('Rebuilt'):o.hide_render=True
render('review-wheel-off',(8,-2,1.0),6.0,(0,0,1.1))
# Do not save diagnostic visibility into the deliverable.
print('DIAGNOSTICS_DONE')
