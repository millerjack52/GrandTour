import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v08')
assert not (P/'Prado_Interior.blend').exists(),'Protect final review revision'
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Cabin.blend'));sc=bpy.context.scene
# A small header mounting plate connects the mirror stalk to the fitted headliner.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,-.051*5,.429*5));mount=bpy.context.object;mount.name='CAB | interior mirror header mount';mount.dimensions=(.015*5,.012*5,.006*5)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for col in list(mount.users_collection):col.objects.unlink(mount)
bpy.data.collections['16 Cabin trim'].objects.link(mount);mount.parent=bpy.data.objects['PRADO | working assembly'];mount.data.materials.append(bpy.data.materials['Prado | Cabin']);mount.color=bpy.data.materials['Prado | Cabin'].diffuse_color
mod=mount.modifiers.new('Soft moulded corners','BEVEL');mod.width=.003;mod.segments=2
for col in list(bpy.data.collections):
 if not col.objects and not col.children and col.name.startswith('99 Source normals'):bpy.data.collections.remove(col)
cam=sc.camera
hidden=[]
for o in sc.objects:
 if o.type=='MESH' and all(c.name not in ['12 Cabin structure','13 Seats','14 Dashboard','15 Controls','16 Cabin trim'] for c in o.users_collection) and not o.hide_render:hidden.append(o);o.hide_render=True
overhead=[o for o in sc.objects if any(k in o.name for k in ['Headliner','Sun visor','Visor hinge','Interior lamp','Rear mirror stalk','Interior mirror','interior mirror header mount'])]
for o in overhead:o.hide_render=True
def render(n,c,d,scale):
 center=Vector(c)*5;cam.data.type='ORTHO';cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*5;sc.render.filepath=str(P/(n+'.png'));bpy.ops.render.render(write_still=True)
render('interior-cutaway',(0,.065,.255),(2,1.6,2),.76)
seats=list(bpy.data.collections['13 Seats'].objects)
for o in seats:o.hide_render=True
render('dashboard',(0,-.11,.282),(.3,3,1.6),.37)
for o in seats+hidden+overhead:o.hide_render=False
render('quarter',(0,0,.27),(2,-3,1.1),1.2)
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
# Material preview in the saved viewport displays the actual transmissive glass.
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.shading.type='MATERIAL';sp.overlay.show_overlays=False
   sp.region_3d.view_location=(0,0,1.35);sp.region_3d.view_distance=7.;sp.region_3d.view_rotation=cam.rotation_euler.to_quaternion();sp.region_3d.view_perspective='PERSP'
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Prado_Interior.blend'))
# Load only the studio lighting/ground objects from the previous review scene.
with bpy.data.libraries.load('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v07/Prado_Studio_Review.blend',link=False) as (src,dst):
 dst.objects=[n for n in src.objects if n in ['STUDIO ground','Key softbox','Fill softbox','Rear softbox']]
for o in dst.objects:sc.collection.objects.link(o)
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.62,.7,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.5
sc.cycles.max_bounces=10;sc.cycles.transmission_bounces=8
sc.render.resolution_x=1400;sc.render.resolution_y=1000
render('lit-exterior',(0,0,.27),(2,-3,1.1),1.2)
render('glass-cabin-close',(.045,-.055,.347),(2,-3,1),.53)
cam.data.type='PERSP';cam.data.lens=20;cam.data.clip_start=.015;cam.location=Vector((.085,-.020,.387))*5;target=Vector((.04,-.17,.285))*5;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/'driver-view.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Prado_Studio_Review.blend'))
print('PACKAGED',P)
