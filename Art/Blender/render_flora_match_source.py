"""Render the purchased original material, without changing the source library."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
SRC=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Assets_Library_v1_3_PRO/Main_Library/FloraPaint_v1_3_Library.blend')
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FloraMatch');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(SRC),link=False) as (src,dst):dst.objects=['FP_Tree_E_001']
o=dst.objects[0];bpy.context.scene.collection.objects.link(o)
o.hide_render=False;o.hide_set(False);o.location=(0,0,0)
bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.context.view_layer.update()
if o.modifiers:
 deps=bpy.context.evaluated_depsgraph_get();mesh=bpy.data.meshes.new_from_object(o.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
 for m in list(o.modifiers):o.modifiers.remove(m)
 o.data=mesh
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
minz=min(v.co.z for v in o.data.vertices)
for v in o.data.vertices:v.co.z-=minz
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=128
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.5,.6,.75,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
bpy.ops.object.camera_add(location=(13.5,20,8.5));cam=bpy.context.object
direction=Vector((math.cos(math.radians(124))*math.cos(math.radians(-9.8)),-math.sin(math.radians(124))*math.cos(math.radians(-9.8)),math.sin(math.radians(-9.8))))
cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();cam.data.lens=36/(2*math.tan(math.radians(54/2)));scene.camera=cam
bpy.ops.object.light_add(type='SUN',location=(0,0,15));sun=bpy.context.object;sun.data.energy=3;sun.data.angle=math.radians(1.5)
lightdir=Vector((math.cos(math.radians(115))*math.cos(math.radians(-38)),-math.sin(math.radians(115))*math.cos(math.radians(-38)),math.sin(math.radians(-38))))
sun.rotation_euler=lightdir.to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=100,location=(0,0,-.02));plane=bpy.context.object
m=bpy.data.materials.new('MatchFloor');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.10,.115,.08,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=1;plane.data.materials.append(m)
for image in bpy.data.images:
 if image.source=='FILE' and not Path(bpy.path.abspath(image.filepath)).exists():
  candidate=SRC.parent/'textures'/Path(image.filepath).name
  if candidate.exists():image.filepath=str(candidate);image.reload()
if '--preview-grid' in sys.argv:
 with bpy.data.libraries.load(str(SRC),link=False) as (src,dst):dst.worlds=['World']
 scene.world=dst.worlds[0];sun.data.energy=18;sun.rotation_euler=(.676684916,.854503572,6.10810566)
 scene.render.resolution_x=1024 if '--final' in sys.argv else 512;scene.render.resolution_y=scene.render.resolution_x;scene.eevee.taa_render_samples=128 if '--final' in sys.argv else 32
 cam.data.type='ORTHO';cam.data.ortho_scale=13;plane.hide_render=True
 if '--calibration' in sys.argv:
  o.hide_render=True;bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,20));cube=bpy.context.object
  mat=bpy.data.materials.new('CalibrationGrey');mat.use_nodes=True;mat.node_tree.nodes.clear()
  diffuse=mat.node_tree.nodes.new('ShaderNodeBsdfDiffuse');diffuse.inputs['Color'].default_value=(.18,.18,.18,1)
  output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(diffuse.outputs[0],output.inputs['Surface']);cube.data.materials.append(mat)
  cam.location=(15,20,27);cam.rotation_euler=(Vector((0,0,20))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=4
  scene.render.filepath=str(OUT/'calibration-source.png');bpy.ops.render.render(write_still=True)
  print('SOURCE_CALIBRATION_RENDERED',flush=True);raise SystemExit
 for i,xy in enumerate([(15,20)] if '--final' in sys.argv else [(15,20),(-15,20),(-15,-20),(15,-20)]):
  cam.location=(*xy,12);cam.rotation_euler=(Vector((0,0,5))-cam.location).to_track_quat('-Z','Y').to_euler()
  scene.render.filepath=str(OUT/('author-reference.png' if '--final' in sys.argv else f'author-rig-angle-{i}.png'));bpy.ops.render.render(write_still=True)
 print('AUTHOR_RIG_ANGLES_RENDERED',flush=True);raise SystemExit
(OUT/'source-rig.json').write_text(json.dumps({'camera_blender':list(cam.location),'camera_rotation':list(cam.rotation_euler),'fov':54,'sun_rotation':list(sun.rotation_euler),'sun_energy':3,'world_strength':.35,'view_transform':'Standard','source_materials_unmodified':True},indent=2))
if '--legacy' in sys.argv:
 g=bpy.data.node_groups['Flora_Shader_v4_2'];g.links.new(g.nodes['Mix Shader'].outputs[0],g.nodes['Mix Shader.003'].inputs[1])
 scene.render.resolution_percentage=50;scene.eevee.taa_render_samples=32
 scene.render.filepath=str(OUT/'source-legacy-eevee.png');bpy.ops.render.render(write_still=True)
 raise SystemExit
else:
 scene.render.filepath=str(OUT/'source-eevee.png');bpy.ops.render.render(write_still=True)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.cycles.device='GPU'
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type!='CPU'
except:scene.cycles.device='CPU'
scene.render.filepath=str(OUT/'source-cycles.png');bpy.ops.render.render(write_still=True)
print('FLORA_SOURCE_RENDERED',flush=True)
