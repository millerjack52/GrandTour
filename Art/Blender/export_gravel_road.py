"""Bake the approved painted surface and export full-size road geometry for UE."""
import bpy,ast,json,math,shutil
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'Art/Export/GravelRoadStudy/04';OUT=ROOT/'Art/Export/GravelRoadUE';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.render.threads_mode='FIXED';scene.render.threads=4
with bpy.data.libraries.load(str(SRC/'GravelRoadStudy.blend')) as (src,dst):dst.materials=['M_GR_PaintedGravel']
mat=dst.materials[0];assert mat
bpy.ops.mesh.primitive_plane_add(size=6,location=(3,3,0));plane=bpy.context.object;plane.data.materials.append(mat)
plane.data.uv_layers[0].name='UVMap'
for loop in plane.data.loops:
    v=plane.data.vertices[loop.vertex_index].co
    plane.data.uv_layers[0].data[loop.index].uv=((v.x+3)/3,(v.y+3)/3)
masks=plane.data.uv_layers.new(name='SurfaceMasks')
for d in masks.data:d.uv=(0,0)
bake=plane.data.uv_layers.new(name='BakeUV')
for loop in plane.data.loops:
    v=plane.data.vertices[loop.vertex_index].co;bake.data[loop.index].uv=((v.x+3)/6,(v.y+3)/6)
plane.data.uv_layers.active_index=2;bake.active_render=True
vc=plane.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
ns=mat.node_tree.nodes;ls=mat.node_tree.links
p=next(n for n in ns if n.type=='BSDF_PRINCIPLED');out=next(n for n in ns if n.type=='OUTPUT_MATERIAL')
em=ns.new('ShaderNodeEmission');ls.new(p.inputs['Base Color'].links[0].from_socket,em.inputs[0])
target=ns.new('ShaderNodeTexImage');ns.active=target
scene.render.bake.use_clear=True;scene.render.bake.margin=8;scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_g='NEG_Y'
textures=[]
for kind,alpha in [('Loose',1.0),('Compact',.32)]:
    for d in vc.data:d.color=(1,1,1,alpha)
    for channel in ['Color','Normal']:
        name='T_GR_'+kind+channel;im=bpy.data.images.new(name,2048,2048,alpha=False)
        im.colorspace_settings.name='sRGB' if channel=='Color' else 'Non-Color';target.image=im;ns.active=target
        ls.new(em.outputs[0] if channel=='Color' else p.outputs[0],out.inputs[0])
        bpy.ops.object.bake(type='EMIT' if channel=='Color' else 'NORMAL')
        im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save();textures.append(name)
        print('GRAVEL_BAKED '+name,flush=True)
bpy.data.objects.remove(plane,do_unlink=True)

tree=ast.parse((ROOT/'Art/Blender/build_road_ford_style.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['center','channel','smooth','noise','edge','h']],type_ignores=[]),'terrain','exec'))
tree=ast.parse((ROOT/'Art/Blender/build_gravel_road_study.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='gravel_relief'],type_ignores=[]),'gravel','exec'))
def relief(s,t):return gravel_relief(s,t)*(1-smooth(24,26,s)+smooth(47,49,s))
names=['SM_RF_DryRoad','SM_RF_ExitRoad','SM_RF_MudApproach','SM_RF_FordBed','SM_RF_GravelVergeL','SM_RF_GravelVergeR','SM_RF_BankL','SM_RF_BankR']
with bpy.data.libraries.load(str(ROOT/'Art/Export/RoadFordStyle/RoadFordStyle.blend')) as (src,dst):dst.objects=names
meshes=[]
for ob in dst.objects:
    scene.collection.objects.link(ob);original_name=ob.name;ob.name=ob.name.replace('SM_RF_','SM_GR_')
    for v in ob.data.vertices:v.co.z+=relief(v.co.x,v.co.y-center(v.co.x))
    eps=.01;normals=[]
    for v in ob.data.vertices:
        s=v.co.x;t=v.co.y-center(s)
        def height(a,b):return h(a,b)+relief(a,b)
        ds=(height(s+eps,t)-height(s-eps,t))/(2*eps);dt=(height(s,t+eps)-height(s,t-eps))/(2*eps)
        bend=(center(s+eps)-center(s-eps))/(2*eps);normals.append(Vector((-ds+bend*dt,-dt,1)).normalized())
    ob.data.normals_split_custom_set_from_vertices(normals)
    meshes.append(dict(name=ob.name,replaces=original_name,triangles=sum(len(p.vertices)-2 for p in ob.data.polygons)))
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
    for v in ob.data.vertices:v.co*=100
    scene.unit_settings.scale_length=.01
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
    scene.unit_settings.scale_length=1;bpy.data.objects.remove(ob,do_unlink=True)
data=json.loads((SRC/'manifest.json').read_text())
for row in data['models']:shutil.copy2(SRC/(row['name']+'.fbx'),OUT/(row['name']+'.fbx'))
# Reconcile pebbles with the blend into the unchanged wet approach.
for row in data['placements']:
    s,y,z=row['location_m'];t=y-center(s);row['location_m'][2]=z-gravel_relief(s,t)+relief(s,t)
data.update(textures=textures,tile_m=6,terrain=meshes,source='GravelRoadStudy/04',status='Exported for Unreal import')
(OUT/'manifest.json').write_text(json.dumps(data,indent=2));print('GRAVEL_EXPORT_OK',flush=True)
