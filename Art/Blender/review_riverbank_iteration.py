"""Fast repeatable model-only review; saves source snapshot and three camera views."""
import bpy,sys,json,shutil
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
label=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'pass-01'
OUT=ROOT/'Art/Export/RoadFordStyle/Iterations'/label; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from riverbank_vegetation_v2 import build
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
def material(name,color,roughness=.9,vertex=False):
    m=bpy.data.materials.new(name); m.use_nodes=True; p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=roughness
    if vertex:
        vc=m.node_tree.nodes.new('ShaderNodeVertexColor'); vc.layer_name='Color'
        mul=m.node_tree.nodes.new('ShaderNodeMixRGB'); mul.blend_type='MULTIPLY'; mul.inputs[0].default_value=1; mul.inputs[1].default_value=(*color,1)
        m.node_tree.links.new(vc.outputs['Color'],mul.inputs[2]); m.node_tree.links.new(mul.outputs[0],p.inputs['Base Color'])
    return m
def mesh(name,verts,faces,mat,smooth=False):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob); me.materials.append(mat)
    ca=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for v in ca.data: v.color=(1,1,1,1)
    return ob
assets,hulls=build(mesh,material)
for ob in assets[1:]: ob.hide_render=True
floor=mesh('Floor',[(-200,-200,-.16),(200,-200,-.16),(200,200,-.16),(-200,200,-.16)],[(0,1,2,3)],material('Floor',(.25,.26,.25)))
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs['Color'].default_value=(.40,.45,.55,1); bg.inputs['Strength'].default_value=.35
def area(name,loc,energy,size):
    data=bpy.data.lights.new(name,'AREA'); ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob)
    ob.location=loc; ob.rotation_euler=(Vector((0,0,3))-ob.location).to_track_quat('-Z','Y').to_euler(); data.energy=energy; data.shape='DISK'; data.size=size
area('Key',(-5,-7,11),2100,7); area('Fill',(6,-1,6),750,6); area('Rim',(1,5,10),1400,5)
scene.render.engine='CYCLES'; scene.cycles.samples=32
scene.render.resolution_x=1440; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'; scene.view_settings.exposure=0
scene.render.image_settings.file_format='PNG'
views=[('front',(0,-19,5),(0,0,3.8),46),('three-quarter',(11,-17,8),(0,0,3.8),48),('branch-detail',(3,-8,4),(-.2,0,2.3),58)]
for name,loc,target,lens in views:
    data=bpy.data.cameras.new(name); ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob)
    ob.location=loc; ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler(); data.lens=lens
    scene.camera=ob; scene.render.filepath=str(OUT/(name+'.png')); bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['three-quarter']
if label!='pass-01' and label!='pass-02':
    assets[0].hide_render=True; assets[1].hide_render=False
    scene.render.filepath=str(OUT/'sparse.png'); bpy.ops.render.render(write_still=True)
    assets[1].hide_render=True
    floor.location.z=.12
    for ob,x in zip(assets[2:],[-1.2,1.2]): ob.hide_render=False; ob.location.x=x
    scene.camera=bpy.data.objects['branch-detail']; scene.camera.location=(4,-7,3)
    scene.camera.rotation_euler=(Vector((0,0,.7))-scene.camera.location).to_track_quat('-Z','Y').to_euler(); scene.camera.data.lens=48
    scene.render.filepath=str(OUT/'scrub.png'); bpy.ops.render.render(write_still=True)
    for ob in assets[2:]: ob.hide_render=True; ob.location.x=0
    floor.location.z=0
    assets[0].hide_render=False; scene.camera=bpy.data.objects['three-quarter']
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TreeReview.blend'))
shutil.copyfile(Path(__file__).parent/'riverbank_vegetation_v2.py',OUT/'source.py')
(OUT/'metrics.json').write_text(json.dumps([dict(name=o.name,triangles=sum(len(p.vertices)-2 for p in o.data.polygons)) for o in assets],indent=2))
print('TREE_REVIEW_OK '+label)
