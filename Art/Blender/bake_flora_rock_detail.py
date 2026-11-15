"""Bake licensed rock pigment at texel resolution; never alter the source blend."""
import bpy,json,math,hashlib,time
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/UnderstoryStudy/Rocks';O.mkdir(parents=True,exist_ok=True)
manifest=json.loads((R/'Art/Export/LidarStudy/FloraPath/scene-manifest.json').read_text())
source=Path(manifest['source']);before=hashlib.sha256(source.read_bytes()).hexdigest()
assert bpy.app.version[:3]==(3,4,1),bpy.app.version_string
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
s=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get();frozen=[]
for row in manifest['meshes']:
 if not row['name'].startswith('SM_Path_FP_Rock'):continue
 obj=bpy.data.objects[row['source']]
 mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
 mesh.calc_loop_triangles();assert len(mesh.loop_triangles)==row['triangles'],row
 frozen.append((row,mesh))
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=1;s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=6
s.render.bake.target='IMAGE_TEXTURES';s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8'
copies={}
def convert(tree):
 for n in list(tree.nodes):
  if n.type=='GROUP' and n.node_tree:
   key=n.node_tree.name
   if key not in copies:
    copies[key]=n.node_tree.copy();convert(copies[key])
   n.node_tree=copies[key]
  elif n.type in ('BSDF_DIFFUSE','BSDF_PRINCIPLED'):
   emit=tree.nodes.new('ShaderNodeEmission');inp=n.inputs.get('Color') or n.inputs.get('Base Color')
   emit.inputs['Color'].default_value=inp.default_value
   if inp.is_linked:tree.links.new(inp.links[0].from_socket,emit.inputs['Color'])
   for link in list(n.outputs[0].links):tree.links.new(emit.outputs[0],link.to_socket)
   tree.nodes.remove(n)
rows=[]
for row,mesh in frozen:
 name=row['name'].replace('SM_Path_','SM_Detail_');obj=bpy.data.objects.new(name,mesh);s.collection.objects.link(obj)
 bpy.context.view_layer.objects.active=obj;obj.select_set(True)
 original=list(mesh.materials)
 for i,m in enumerate(original):
  copy=m.copy();convert(copy.node_tree);mesh.materials[i]=copy
 if not mesh.uv_layers:mesh.uv_layers.new(name='UVMap')
 preferred=mesh.uv_layers.get('UVMap') or mesh.uv_layers[0];uv0=[tuple(v.uv) for v in preferred.data]
 for layer in list(mesh.uv_layers):mesh.uv_layers.remove(layer)
 layer=mesh.uv_layers.new(name='UVMap')
 for v,co in zip(layer.data,uv0):v.uv=co
 atlas=mesh.uv_layers.new(name='RockAtlas');mesh.uv_layers.active=atlas
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
 image=bpy.data.images.new(name+'_Pigment',width=2048,height=2048,alpha=False,float_buffer=True)
 for m in mesh.materials:
  n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=image;m.node_tree.nodes.active=n
 assert bpy.ops.object.bake(type='EMIT',margin=12,uv_layer='RockAtlas')=={'FINISHED'}
 image.save_render(str(O/(name+'.png')),scene=s)
 for i,m in enumerate(original):mesh.materials[i]=m
 bpy.ops.export_scene.fbx(filepath=str(O/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='SRGB',bake_anim=False,path_mode='STRIP')
 rows.append(dict(original=row['name'],name=name,source=row['source'],triangles=row['triangles'],uvs=2,pigment=str(O/(name+'.png')),fbx=str(O/(name+'.fbx'))))
 print('ROCK_BAKED',name,flush=True);bpy.data.objects.remove(obj,do_unlink=True);bpy.data.images.remove(image)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(O/'manifest.json').write_text(json.dumps(dict(version=bpy.app.version_string,source_sha256=before,rocks=rows,normal_detail='Source diffuse shader has no connected normal input; no invented bump added.'),indent=2))
print('ROCK_DETAIL_DONE',flush=True)
