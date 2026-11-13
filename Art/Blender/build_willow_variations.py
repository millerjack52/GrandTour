"""Build four reusable willow variants, individual scenes and a scale-matched lineup."""
import bpy
import json
import math
import shutil
import sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from willow_reference_v5 import build,PRESETS
label=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'willow-family-01'
OUT=ROOT/'Art/Export/WillowFamily'/label
if (OUT/'WillowFamily.blend').exists(): raise RuntimeError('Existing family preserved; use a new label.')
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
library=bpy.context.scene; library.name='Willow Family'
originals=bpy.data.collections.new('Reusable assets at origin'); library.collection.children.link(originals)
originals.hide_render=True; originals.hide_viewport=True
world=bpy.data.worlds.new('Willow studio'); world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.55,.63,.78,1); bg.inputs['Strength'].default_value=.35

def material(name,color,roughness=.88,vertex=False):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=roughness
    return m

def mesh(name,verts,faces,mat,smooth=False):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); library.collection.objects.link(ob); me.materials.append(mat)
    ca=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for v in ca.data: v.color=(1,1,1,1)
    return ob

def configure(scene,width=1400,height=1200):
    scene.world=world; scene.render.engine='CYCLES'; scene.cycles.samples=24; scene.cycles.use_denoising=True
    scene.render.resolution_x=width; scene.render.resolution_y=height; scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=0
    scene.render.image_settings.file_format='PNG'

def camera(scene,name,loc,target,scale):
    data=bpy.data.cameras.new(name); data.type='ORTHO'; data.ortho_scale=scale
    ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob); ob.location=loc
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler(); scene.camera=ob
    return ob

def area(scene,name,loc,target,energy,size):
    data=bpy.data.lights.new(name,'AREA'); ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob)
    ob.location=loc; ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    data.energy=energy; data.shape='DISK'; data.size=size

floor_mat=material('ReviewFloor',(.30,.31,.32))
def floor(scene,z):
    me=bpy.data.meshes.new('FloorMesh'); me.from_pydata([(-200,-200,z),(200,-200,z),(200,200,z),(-200,200,z)],[],[(0,1,2,3)]); me.materials.append(floor_mat)
    ob=bpy.data.objects.new('Review Floor',me); scene.collection.objects.link(ob)

assets=[]; metrics=[]
for preset in ['young','broad','windswept','weathered']:
    print('BUILDING_WILLOW '+preset,flush=True)
    objects,hull_dict=build(mesh,material,preset); tree=objects[0]; hulls=hull_dict[tree.name]
    for ob in [tree]+hulls:
        for collection in list(ob.users_collection): collection.objects.unlink(ob)
        originals.objects.link(ob)
    item=bpy.data.scenes.new(preset.title()+' Willow'); configure(item)
    item.collection.objects.link(tree)
    for hull in hulls: item.collection.objects.link(hull)
    low=Vector(tuple(min(v.co[i] for v in tree.data.vertices) for i in range(3)))
    high=Vector(tuple(max(v.co[i] for v in tree.data.vertices) for i in range(3)))
    center=(low+high)*.5
    floor(item,low.z)
    for name,loc,energy,size in [('Key',(-5,-7,11),2100,7),('Fill',(6,-1,6),750,6),('Rim',(1,5,10),1400,5)]:
        area(item,name,loc,(0,0,3),energy,size)
    scale=max(8.6,(high.x-low.x)*1.3,(high.z-low.z)*1.45)
    camera(item,preset+' review',center+Vector((11,-18,3.2)),center,scale)
    item.render.filepath=str(OUT/(preset+'.png')); bpy.ops.render.render(write_still=True,scene=item.name)
    bpy.data.libraries.write(str(OUT/(preset+'.blend')),{item},fake_user=True,compress=True)
    record=dict(preset=preset,name=tree.name,dimensions_m=list(high-low),
                triangles=sum(len(p.vertices)-2 for p in tree.data.polygons),
                leaf_count=tree['leaf_count'],pendant_shoot_count=tree['pendant_shoot_count'],
                collision_hulls=len(hulls),zero_area_faces=sum(p.area<1e-10 for p in tree.data.polygons),
                finite_vertices=all(math.isfinite(x) for v in tree.data.vertices for x in v.co))
    assert record['zero_area_faces']==0 and record['finite_vertices'] and len(hulls)==3
    metrics.append(record); assets.append((preset,tree,low,high))
    (OUT/'metrics.json').write_text(json.dumps(metrics,indent=2))
    print('VARIANT_READY '+json.dumps(record),flush=True)

configure(library,3600,1100); floor(library,0)
widths=[high.x-low.x for _,_,low,high in assets]; total=sum(widths)+3*(len(assets)-1)
cursor=-total/2
labelmat=material('Label',(.035,.045,.055))
for (preset,tree,low,high),width in zip(assets,widths):
    display=tree.copy(); display.data=tree.data; display.name=preset.title()+' display'; library.collection.objects.link(display)
    display.location=(cursor-low.x,0,-low.z)
    data=bpy.data.curves.new(preset+' label','FONT'); data.body=preset.upper(); data.align_x='CENTER'; data.size=.46; data.materials.append(labelmat)
    text=bpy.data.objects.new(preset+' label',data); library.collection.objects.link(text)
    text.location=(cursor+width/2,-7,.12); text.rotation_euler=(math.pi/2,0,0)
    cursor+=width+3
area(library,'Family key',(-10,-17,22),(0,0,3),10000,22)
area(library,'Family fill',(18,-3,14),(0,0,3),4500,20)
area(library,'Family rim',(0,10,18),(0,0,3),9000,25)
camera(library,'Family lineup',(0,-38,8),(0,0,4.1),total*1.08)
library.render.filepath=str(OUT/'Willow_family.png'); bpy.ops.render.render(write_still=True,scene=library.name)
bpy.context.window.scene=library
for screen in bpy.data.screens:
    for area_ui in screen.areas:
        if area_ui.type=='VIEW_3D':
            area_ui.spaces.active.region_3d.view_perspective='CAMERA'; area_ui.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'WillowFamily.blend'))
for filename in ['willow_reference_v5.py','willow_bark.py','build_willow_variations.py']:
    shutil.copyfile(Path(__file__).parent/filename,OUT/filename)
(OUT/'presets.json').write_text(json.dumps(PRESETS,indent=2))
print('WILLOW_FAMILY_OK '+str(OUT),flush=True)
