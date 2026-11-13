import bpy,bmesh,json,time
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-source-v01');OUT=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-work-v01');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Analysed.blend'));sc=bpy.context.scene
source=next(o for o in sc.objects if o.type=='MESH');source.hide_render=True;source.hide_set(True)
me=source.data.copy();body=bpy.data.objects.new('Body retopology',me);sc.collection.objects.link(body)
bm=bmesh.new();bm.from_mesh(me);il=bm.faces.layers.int.get('source_island');bmesh.ops.delete(bm,geom=[f for f in bm.faces if f[il]!=0],context='FACES')
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-6)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(me);bm.free()
ref=body.copy();ref.data=body.data.copy();sc.collection.objects.link(ref);ref.name='Body reference';ref.hide_render=True;ref.hide_set(True)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
md=body.modifiers.new('Repair fused topology','REMESH');md.mode='VOXEL';md.voxel_size=.0018;md.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=md.name)
print('VOXEL',len(body.data.vertices),len(body.data.polygons),flush=True)
bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=True,use_preserve_sharp=False,use_preserve_boundary=True,target_faces=7500,seed=17)
print('QUADS',len(body.data.vertices),len(body.data.polygons),flush=True)
# Light surface relaxation, then return the surface to the measured donor envelope.
md=body.modifiers.new('Relax flow','SMOOTH');md.factor=.25;md.iterations=2;bpy.ops.object.modifier_apply(modifier=md.name)
md=body.modifiers.new('Fit measured donor','SHRINKWRAP');md.target=ref;md.wrap_method='NEAREST_SURFACEPOINT';md.wrap_mode='ON_SURFACE';bpy.ops.object.modifier_apply(modifier=md.name)
mat=bpy.data.materials.new('Retopo clay');mat.diffuse_color=(.5,.54,.52,1);body.data.materials.clear();body.data.materials.append(mat)
for p in body.data.polygons:p.use_smooth=True
body.data.set_sharp_from_angle(angle=.65)
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.render.resolution_x=1200;sc.render.resolution_y=850
cam=sc.camera;cam.data.ortho_scale=1.2
for n,pos in [('quarter',(1.2,-1.6,.95)),('side',(1.2,0,.2)),('rear',(1.1,1.5,.9)),('top',(0,0,2))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.19))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Body_Retopology.blend'))
