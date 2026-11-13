"""Bake approved mud 03 and export the art-map terrain without touching simulation."""
import bpy,ast,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/MudStyleUE';OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'Art/Export/MudStyleStudy/03/MudStyleStudy.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.render.threads_mode='FIXED';scene.render.threads=4
with bpy.data.libraries.load(str(SRC)) as (src,dst):dst.materials=['M_MS_PaintedMud']
mat=dst.materials[0]
bpy.ops.mesh.primitive_plane_add(size=6);plane=bpy.context.object;plane.data.materials.append(mat)
plane.data.uv_layers[0].name='UVMap'
for loop in plane.data.loops:
    v=plane.data.vertices[loop.vertex_index].co;plane.data.uv_layers[0].data[loop.index].uv=((v.x+3)/3,(v.y+3)/3)
surface=plane.data.uv_layers.new(name='SurfaceMasks')
for d in surface.data:d.uv=(0,0)
bake=plane.data.uv_layers.new(name='BakeUV')
for loop in plane.data.loops:
    v=plane.data.vertices[loop.vertex_index].co;bake.data[loop.index].uv=((v.x+3)/6,(v.y+3)/6)
plane.data.uv_layers.active_index=2;bake.active_render=True
vc=plane.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for d in vc.data:d.color=(1,1,1,1)
masks=plane.data.color_attributes.new(name='MudMasks',type='FLOAT_COLOR',domain='CORNER')
ns=mat.node_tree.nodes;ls=mat.node_tree.links;p=next(n for n in ns if n.type=='BSDF_PRINCIPLED');out=next(n for n in ns if n.type=='OUTPUT_MATERIAL')
em=ns.new('ShaderNodeEmission');ls.new(p.inputs['Base Color'].links[0].from_socket,em.inputs[0]);target=ns.new('ShaderNodeTexImage')
scene.render.bake.margin=8;scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_g='NEG_Y'
textures=[]
for kind,rut in [('Clay',0),('Worked',1)]:
    for d in masks.data:d.color=(1,0,rut,1)
    for channel in ['Color','Normal']:
        name='T_MS_'+kind+channel;im=bpy.data.images.new(name,2048,2048,alpha=False);im.colorspace_settings.name='sRGB' if channel=='Color' else 'Non-Color'
        target.image=im;ns.active=target;ls.new(em.outputs[0] if channel=='Color' else p.outputs[0],out.inputs[0]);bpy.ops.object.bake(type='EMIT' if channel=='Color' else 'NORMAL')
        im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save();textures.append(name);print('MUD_BAKED '+name,flush=True)
bpy.data.objects.remove(plane,do_unlink=True)
def functions(path,names):
    tree=ast.parse((ROOT/path).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),path,'exec'),globals())
functions('Art/Blender/build_road_ford_style.py',['center','channel','smooth','noise','edge','h'])
functions('Art/Blender/build_gravel_road_study.py',['gravel_relief'])
original_gravel_relief=gravel_relief
def gravel_relief(s,t):return original_gravel_relief(s,t)*(1-smooth(24,26,s)+smooth(47,49,s))
functions('Art/Blender/build_mud_style_study.py',['lanes','masks','delta','height'])
def export(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
    original=ob.data;ob.data=original.copy()
    for v in ob.data.vertices:v.co*=100
    scene.unit_settings.scale_length=.01
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
    copy=ob.data;ob.data=original;bpy.data.meshes.remove(copy);scene.unit_settings.scale_length=1
terrain=[];models=[];placements=[]
names=['SM_RF_DryRoad','SM_RF_ExitRoad','SM_RF_MudApproach','SM_RF_FordBed','SM_RF_GravelVergeL','SM_RF_GravelVergeR','SM_RF_BankL','SM_RF_BankR']
with bpy.data.libraries.load(str(ROOT/'Art/Export/RoadFordStyle/RoadFordStyle.blend')) as (src,dst):dst.objects=names
for ob in dst.objects:
    scene.collection.objects.link(ob);old=ob.name.replace('SM_RF_','SM_GR_');ob.name=ob.name.replace('SM_RF_','SM_MS_')
    if ob.name=='SM_MS_DryRoad':
        import bmesh
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True);bm.to_mesh(ob.data);bm.free()
    for v in ob.data.vertices:v.co.z=height(v.co.x,v.co.y-center(v.co.x))
    a=ob.data.uv_layers.new(name='MudCoverageWet');b=ob.data.uv_layers.new(name='MudRut')
    for loop in ob.data.loops:
        v=ob.data.vertices[loop.vertex_index].co;mud,wet,rut=masks(v.x,v.y-center(v.x));a.data[loop.index].uv=(mud,wet);b.data[loop.index].uv=(rut,0)
    normals=[];eps=.01
    for v in ob.data.vertices:
        s=v.co.x;t=v.co.y-center(s);ds=(height(s+eps,t)-height(s-eps,t))/(2*eps);dt=(height(s,t+eps)-height(s,t-eps))/(2*eps);bend=(center(s+eps)-center(s-eps))/(2*eps)
        normals.append(Vector((-ds+bend*dt,-dt,1)).normalized())
    ob.data.normals_split_custom_set_from_vertices(normals)
    terrain.append(dict(name=ob.name,replaces=old,triangles=sum(len(p.vertices)-2 for p in ob.data.polygons)));export(ob)
with bpy.data.libraries.load(str(SRC)) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(('Displaced mud clod','Shallow rut pool','Loose gravel'))]
exported={};pools=[]
for ob in dst.objects:
    scene.collection.objects.link(ob)
    if ob.hide_render:continue
    if ob.name.startswith('Loose gravel') and 'clay coated' not in ob.data.name:continue
    pool=ob.name.startswith('Shallow rut pool');key=ob.data.name
    if key not in exported:
        name=('SM_MS_Pool' if pool else 'SM_MS_Detail')+str(len(exported));exported[key]=name
        proxy=bpy.data.objects.new(name,ob.data.copy());scene.collection.objects.link(proxy)
        if not pool and 'Color' not in proxy.data.color_attributes:
            color=proxy.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value
            vc=proxy.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
            for d in vc.data:d.color=color
        export(proxy);models.append(dict(name=name,triangles=sum(len(p.vertices)-2 for p in proxy.data.polygons),pool=pool));bpy.data.objects.remove(proxy,do_unlink=True)
    row=dict(mesh=exported[key],location_m=list(ob.location),rotation_deg=[math.degrees(v) for v in ob.rotation_euler],scale=list(ob.scale))
    placements.append(row)
# Keep the full approved gravel distribution except where the mud covers it.
gravel=json.loads((ROOT/'Art/Export/GravelRoadUE/manifest.json').read_text())
for row in gravel['placements']:
    s,y,z=row['location_m'];t=y-center(s)
    if masks(s,t)[0]>.2:continue
    placements.append(row)
report=dict(source='MudStyleStudy/03',textures=textures,tile_m=6,terrain=terrain,models=models,placements=placements,status='Static art-map import; runtime deformation unchanged')
(OUT/'manifest.json').write_text(json.dumps(report,indent=2));print('MUD_EXPORT_OK',flush=True)
