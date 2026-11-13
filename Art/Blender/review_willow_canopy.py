"""Isolated versioned willow study. Does not rebuild/import the driving level."""
import bpy
import importlib
import json
import shutil
import sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
args=sys.argv[sys.argv.index('--')+1:]
label=args[0]
module=args[1] if len(args)>1 else 'riverbank_vegetation_v3'
OUT=ROOT/'Art/Export/RoadFordStyle/Iterations'/label
OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'TreeReview.blend').exists():
    raise RuntimeError('Choose a new study label; existing review is preserved.')
sys.path.insert(0,str(Path(__file__).parent))
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene

def material(name,color,roughness=.88,vertex=False):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=roughness
    if vertex:
        vc=m.node_tree.nodes.new('ShaderNodeVertexColor'); vc.layer_name='Color'
        mul=m.node_tree.nodes.new('ShaderNodeMixRGB'); mul.blend_type='MULTIPLY'
        mul.inputs[0].default_value=1; mul.inputs[1].default_value=(*color,1)
        m.node_tree.links.new(vc.outputs['Color'],mul.inputs[2]); m.node_tree.links.new(mul.outputs[0],p.inputs['Base Color'])
    return m

def mesh(name,verts,faces,mat,smooth=False):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob); me.materials.append(mat)
    ca=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for v in ca.data: v.color=(1,1,1,1)
    return ob

assets,hulls=importlib.import_module(module).build(mesh,material)
for ob in assets[1:]: ob.hide_render=True; ob.hide_set(True)
floor=mesh('ReviewFloor',[(-200,-200,-.14),(200,-200,-.14),(200,200,-.14),(-200,200,-.14)],[(0,1,2,3)],material('ReviewFloor',(.30,.31,.32)))
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.55,.63,.78,1); bg.inputs['Strength'].default_value=.35
for name,loc,energy,size in [('Key',(-5,-7,11),2100,7),('Fill',(6,-1,6),750,6),('Rim',(1,5,10),1400,5)]:
    data=bpy.data.lights.new(name,'AREA'); ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob)
    ob.location=loc; ob.rotation_euler=(Vector((0,0,3))-ob.location).to_track_quat('-Z','Y').to_euler()
    data.energy=energy; data.shape='DISK'; data.size=size
scene.render.engine='CYCLES'; scene.cycles.samples=24; scene.cycles.use_denoising=True
scene.render.resolution_x=1400; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=0
scene.render.image_settings.file_format='PNG'
views=[('branch-detail',(3,-9,4),(-.2,0,2.4),4.8),('three-quarter',(11,-18,7),(0,0,3.6),11.6),('front',(0,-20,5),(0,0,3.6),11.6)]
if module=='willow_reference_v5':
    views=[('three-quarter',(11,-18,7),(0,0,3.8),12.5),('front',(0,-20,5),(0,0,3.8),12.5),('branch-detail',(3,-9,3),(.1,0,1.5),4.0)]
for name,loc,target,scale in views:
    data=bpy.data.cameras.new(name); ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob)
    ob.location=loc; ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO'; data.ortho_scale=scale
    scene.camera=ob; scene.render.filepath=str(OUT/(name+'.png')); bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['three-quarter']
bpy.ops.object.select_all(action='DESELECT'); assets[0].select_set(True); bpy.context.view_layer.objects.active=assets[0]
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TreeReview.blend'))
shutil.copyfile(Path(__file__).parent/(module+'.py'),OUT/'source.py')
if module in ('riverbank_vegetation_v3','willow_reference_v5'):
    shutil.copyfile(Path(__file__).parent/'willow_bark.py',OUT/'willow_bark.py')
metrics=[]
for o in assets:
    metrics.append(dict(name=o.name,triangles=sum(len(p.vertices)-2 for p in o.data.polygons),
                        dimensions=list(o.dimensions),collision_hulls=len(hulls.get(o.name,[])),
                        zero_area_faces=sum(p.area<1e-10 for p in o.data.polygons)))
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2))
print('WILLOW_REVIEW_OK '+label,flush=True)
