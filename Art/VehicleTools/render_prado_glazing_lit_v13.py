import bpy
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-v13')
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Corrected.blend'));sc=bpy.context.scene;cam=sc.camera
with bpy.data.libraries.load('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v08/Prado_Studio_Review.blend',link=False) as (src,dst):
 dst.objects=[n for n in src.objects if n in ['STUDIO ground','Key softbox','Fill softbox','Rear softbox']]
for ob in dst.objects:sc.collection.objects.link(ob)
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.62,.7,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.5
sc.render.engine='CYCLES';sc.cycles.samples=40;sc.cycles.use_denoising=True;sc.cycles.max_bounces=10;sc.cycles.transmission_bounces=8;sc.render.resolution_x=1400;sc.render.resolution_y=1000
def render(n,c,d,scale):
 target=Vector(c)*5;cam.data.type='ORTHO';cam.location=target+Vector(d)*5;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*5;sc.render.filepath=str(P/(n+'.png'));bpy.ops.render.render(write_still=True)
render('lit-windscreen',(0,-.11,.35),(2,-3,.4),.51)

cam.data.type='PERSP';cam.data.lens=20;cam.data.clip_start=.015;cam.location=Vector((.085,-.020,.387))*5;target=Vector((.04,-.17,.285))*5;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/'driver-view.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Prado_Studio_Review.blend'))

