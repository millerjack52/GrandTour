import bpy,math
from pathlib import Path
from mathutils import Vector
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/panda-assembly-v02');S=3.6
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Panda_Assembly.blend'));sc=bpy.context.scene
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.72,.76,.82,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.45
for name,p,e,size in [('Key',(4,-5,7),1500,5),('Fill',(-4,-1,4),1000,4),('Rear',(1,5,6),1800,4)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=e;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.data.collections['Studio'].objects.link(o);o.location=p;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.029));ground=bpy.context.object;ground.name='REVIEW ONLY | ground'
m=bpy.data.materials.new('Review ground');m.diffuse_color=(.65,.63,.57,1);ground.data.materials.append(m)
cam=sc.camera;cam.location=Vector((1.7,-2.7,1.30))*S;target=Vector((0,0,.26))*S;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.30*S;sc.render.filepath=str(OUT/'studio-quarter.png');bpy.ops.render.render(write_still=True)
# Diagnostic interior cutaway only; never saved with exterior hidden.
for name in ['Body','Doors','Bonnet','Tailgate','Glazing','Roof and snorkel','Front equipment']:bpy.data.collections[name].hide_render=True
cam.location=Vector((1.4,-1.5,1.6))*S;target=Vector((0,.08,.25))*S;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.98*S;sc.render.filepath=str(OUT/'interior-cutaway.png');bpy.ops.render.render(write_still=True)
print('Review renders complete',flush=True)
