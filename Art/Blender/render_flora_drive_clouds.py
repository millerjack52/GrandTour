"""Render purchased Cloud Paint geometry in its documented Eevee engine."""
import bpy,json,math
from mathutils import Vector
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/FloraDrive');SRC='D:/GrandTourAssets/FlippedNormals/stylized_cloud_paint/Assets/Library_assets/Clouds_Assets.blend'
bpy.ops.wm.open_mainfile(filepath=SRC,load_ui=False,use_scripts=False);s=bpy.context.scene
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1536;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8';s.use_nodes=False
s.eevee.use_raytracing=True;s.eevee.taa_render_samples=64
# Keep the creator's world, sun and cloud shader settings. Only isolate a cloud and frame it.
for o in bpy.data.objects:
 if o.name.startswith(('Cloud_Assets_','test_mesh_')):o.hide_render=True
camera_data=bpy.data.cameras.new('DriveCloudBakeCamera');camera=bpy.data.objects.new('DriveCloudBakeCamera',camera_data);s.collection.objects.link(camera);s.camera=camera;camera_data.type='ORTHO';camera_data.clip_end=10000
r={'ok':False,'source':SRC,'engine':s.render.engine,'raytracing':True,'clouds':[],'runtime_representation':'distant translucent cards with creator-rendered RGBA; not native volumetrics','attribution':'Cloud Paint by Casey Sheep and MeiU'}
for name in ['Cloud_Assets_003','Cloud_Assets_007','Cloud_Assets_015']:
 o=bpy.data.objects[name];o.hide_render=False
 if o.name not in s.collection.objects:s.collection.objects.link(o)
 s.view_layers[0].update();dg=bpy.context.evaluated_depsgraph_get();eo=o.evaluated_get(dg);corners=[eo.matrix_world@Vector(v) for v in eo.bound_box];centre=sum(corners,Vector())/8
 width=max(v.x for v in corners)-min(v.x for v in corners);height=max(v.z for v in corners)-min(v.z for v in corners)
 camera.location=centre+Vector((0,-300,15));camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.ortho_scale=max(width*1.2,height*1.5*1.2)
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
 r['clouds'].append({'name':name,'file':name+'.png','world_dimensions':list(o.dimensions),'render_size':[1536,1024],'camera_scale':camera_data.ortho_scale});o.hide_render=True
# A dedicated 2m x 2m card; shader and UVs remain simple at runtime.
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
m=bpy.data.meshes.new('CloudCard');m.from_pydata([(0,1,-1),(0,-1,-1),(0,-1,1),(0,1,1)],[],[(0,1,2,3)]);uv=m.uv_layers.new(name='UVMap')
for p in m.polygons:
 for i,li in enumerate(p.loop_indices):uv.data[li].uv=[(0,0),(1,0),(1,1),(0,1)][i]
o=bpy.data.objects.new('SM_DriveCloudCard',m);s.collection.objects.link(o);bpy.context.view_layer.objects.active=o;o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(O/'SM_DriveCloudCard.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_anim=False)
r['ok']=True;(O/'cloud-render-report.json').write_text(json.dumps(r,indent=2))
