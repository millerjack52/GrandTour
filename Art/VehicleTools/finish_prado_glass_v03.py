import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v02')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v03');OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'Prado_Exterior.blend').exists(),'Preserve saved revision'
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Prado_Exterior.blend'))
sc=bpy.context.scene
for o in bpy.data.collections['02 Glass'].objects:
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
 bm=bmesh.new();bm.from_mesh(o.data)
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle()<math.radians(30)
 bm.to_mesh(o.data);bm.free()
 # Glass faces and their thin edge walls must not share smoothing normals.
 o.data.update()
cam=sc.camera
for name,c,d,scale in [('quarter',(0,0,.27),(2,-3,1.1),1.2),('side',(0,0,.27),(3,0,0),1.2),('window-close',(0,-.1,.355),(2,-3,.7),.53)]:
 center=Vector(c)*5;cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*5;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Exterior.blend'))
