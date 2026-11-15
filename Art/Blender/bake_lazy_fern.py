"""Bake the owned fern's authored pigment, coverage and bump for Unreal."""
import bpy, json, hashlib
from pathlib import Path
O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/LazyFern')
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(O/'Fern02-source.blend'),link=False) as (src,dst):dst.objects=['Fern_02']
obj=dst.objects[0];bpy.context.scene.collection.objects.link(obj)
mat=obj.data.materials[0];original=mat.copy();tree=mat.node_tree
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.render.bake.margin=16;scene.render.bake.use_clear=True
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
output=next(n for n in tree.nodes if n.type=='OUTPUT_MATERIAL')
normal=tree.nodes['Bump'].outputs['Normal']
# Normal bake on the actual source geometry, retaining original UVs.
image=bpy.data.images.new('LazyFernNormal',4096,4096,alpha=False)
image.colorspace_settings.name='Non-Color';image.generated_color=(.5,.5,1,1)
target=tree.nodes.new('ShaderNodeTexImage');target.image=image;tree.nodes.active=target
scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_g='NEG_Y'
bpy.ops.object.bake(type='NORMAL')
image.filepath_raw=str(O/'T_LazyFern_Normal.png');image.file_format='PNG';image.save()
# Full atlas plane avoids UV-overlap seams in the authored colour/coverage maps.
obj.select_set(False);obj.hide_render=True
bpy.ops.mesh.primitive_plane_add(size=1)
plane=bpy.context.object;plane.data.materials.append(mat)
emission=tree.nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
tree.links.new(emission.outputs[0],output.inputs['Surface'])
for role,socket,srgb in [('Colour',tree.nodes['Reroute.001'].outputs[0],True),
                         ('Coverage',tree.nodes['Image Texture'].outputs['Alpha'],False),
                         ('Transmission',tree.nodes['Mix'].outputs['Result'],False)]:
    image=bpy.data.images.new('LazyFern'+role,4096,4096,alpha=False)
    image.colorspace_settings.name='sRGB' if srgb else 'Non-Color'
    target.image=image;tree.nodes.active=target
    tree.links.new(socket,emission.inputs['Color'])
    bpy.ops.object.bake(type='EMIT')
    image.filepath_raw=str(O/('T_LazyFern_'+role+'.png'));image.file_format='PNG';image.save()
report={'ok':True,'blender':bpy.app.version_string,'size':4096,'normal_convention':'DirectX',
        'lighting_baked':False,'source_colour':'Authored mixes, RGB curves and one frozen object variation',
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.glob('T_LazyFern_*.png')}}
(O/'bake-report.json').write_text(json.dumps(report,indent=2))
print('LAZY_FERN_BAKE_OK',flush=True)
