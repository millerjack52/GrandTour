"""Assemble repaired donor body with measured wheel components; bake original appearance."""
import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-cleanup-v01');R=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-work-v04');OUT=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-prepared-v01');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Assembly.blend'))
sc=bpy.context.scene;parts=bpy.data.collections['Porsche - separated assembly'];old=bpy.data.objects['Body_and_cabin']
with bpy.data.libraries.load(str(R/'Body_Retopology.blend'),link=False) as (available,requested):requested.objects=['Body retopology']
body=requested.objects[0];parts.objects.link(body);body.name='Porsche_Body_Repaired'
for v in body.data.vertices:v.co*=4.5
body.hide_render=False;body.hide_set(False)
# The original body is the bake donor, never a hidden cover for missing target faces.
src=bpy.data.objects['REFERENCE_Porsche_Tripo'];ref=src.copy();ref.data=src.data.copy();sc.collection.objects.link(ref);ref.name='BAKE_DONOR'
bm=bmesh.new();bm.from_mesh(ref.data);layer=bm.faces.layers.int.get('source_island');bmesh.ops.delete(bm,geom=[f for f in bm.faces if f[layer]!=0],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ref.data);bm.free()
ref.hide_render=False;ref.hide_set(False);old.hide_render=True;old.hide_set(True)
for o in sc.objects:o.select_set(False)
body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.12,island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
mat=bpy.data.materials.new('Porsche - transferred body finish');mat.use_nodes=True;body.data.materials.clear();body.data.materials.append(mat)
for f in body.data.polygons:f.material_index=0;f.use_smooth=True
tex=bpy.data.images.new('Porsche_Body_BaseColor',4096,4096,alpha=False);node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=tex;mat.node_tree.nodes.active=node
shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.38;shader.inputs['Metallic'].default_value=.12
sc.render.engine='CYCLES';sc.cycles.samples=8;sc.render.bake.use_selected_to_active=True;sc.render.bake.cage_extrusion=.025;sc.render.bake.max_ray_distance=.08;sc.render.bake.margin=12
ref.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
tex.filepath_raw=str(OUT/'Porsche_Body_BaseColor.png');tex.file_format='PNG';tex.save();tex.pack();mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
bpy.data.objects.remove(ref,do_unlink=True);bpy.data.objects.remove(old,do_unlink=True)
# Keep the bake-only source hidden and out of every export.
src.hide_render=True;src.hide_set(True)
sc.render.bake.use_selected_to_active=False
cam=sc.camera;cam.data.ortho_scale=5.8;sc.cycles.samples=32
for name,pos,target in [('quarter',(5.4,-7.2,4.5),(0,0,.85)),('side',(5.4,0,.95),(0,0,.95)),('rear',(5,7,3.6),(0,0,.85)),('front',(0,-7.5,1),(0,0,1))]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='SINGLE';sc.display.shading.single_color=(.56,.59,.58)
for name,pos,target in [('clay',(5.4,-7.2,4.5),(0,0,.85)),('underside',(4,-5,-5),(0,0,.6)),('wheel-off',(4,-5,2),(0,0,.85))]:
 if name=='wheel-off':
  for o in parts.objects:
   if o.name.startswith('Wheel_') and o.type=='MESH':o.hide_render=True
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
for o in parts.objects:o.hide_render=False
sc.render.engine='CYCLES';cam.location=(5.4,-7.2,4.5);cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
for o in sc.objects:o.select_set(False)
body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Porsche_Assembly.blend'))
for o in sc.objects:o.select_set(False)
for o in parts.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Porsche_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True)
print('ASSEMBLY_SAVED',flush=True)
