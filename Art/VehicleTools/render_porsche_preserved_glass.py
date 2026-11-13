import bpy,math,json
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02')
bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Preserved_Repair.blend'));s=bpy.context.scene
for o in list(bpy.data.objects):
 if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.cycles.max_bounces=10;s.cycles.transmission_bounces=8
s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100
w=bpy.data.worlds.new('Glass review studio');s.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.35,.4,.48,1);w.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,pos,power,size in [('Key',(3,-4,6),1500,5),('Fill',(-4,-2,4),1000,4),('Rim',(0,5,5),1600,4)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
c=s.camera;c.location=(4,-6,3.2);c.rotation_euler=(Vector((0,-.5,1.1))-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=3.6
s.render.filepath=str(O/'glass-review.png');bpy.ops.render.render(write_still=True)
