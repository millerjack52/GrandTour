import bpy,bmesh,json,math
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Source.blend'))
o=bpy.data.objects['Prado Tripo source'];bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for f in bm.faces:f.smooth=True
for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle()<math.radians(35)
bm.to_mesh(o.data);bm.free();o.data.update()
mod=o.modifiers.new('Area weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=30
sc=bpy.context.scene
from mathutils import Vector
center=Vector((0,0,.27))
for name,d in [('diagnostic-normals-side',(3,0,0)),('diagnostic-normals-quarter',(2,-3,1.6))]:
 sc.camera.location=center+Vector(d);sc.camera.rotation_euler=(center-sc.camera.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Prado_Normal_Diagnostic.blend'))
