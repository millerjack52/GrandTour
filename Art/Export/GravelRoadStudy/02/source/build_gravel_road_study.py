"""Non-destructive Blender-only gravel study. CPU review; does not touch UE assets."""
import ast,bpy,json,math,random,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/GravelRoadStudy/02';OUT.mkdir(parents=True,exist_ok=True)
R=random.Random(290929)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
sys.path.insert(0,str(Path(__file__).parent))
from gravel_road_material import build
tree=ast.parse((ROOT/'Art/Blender/build_road_ford_style.py').read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['center','channel','smooth','noise','edge','h']]
exec(compile(ast.Module(body=functions,type_ignores=[]),'existing-road-height','exec'))
def gravel_relief(s,t):
    # Shallow displaced gravel ridges, intermittent rather than perfectly straight berms.
    centre=math.exp(-((t-.1*math.sin(s*.5))/.44)**2)
    shoulders=math.exp(-((abs(t)-1.9-.12*math.sin(s*.8))/.42)**2)
    edge_fade=1-smooth(2.5,3.5,abs(t))
    return edge_fade*(.036*centre+.025*shoulders)*(.65+.35*noise(s,t,1.4))
ground_names=['SM_RF_DryRoad','SM_RF_GravelVergeL','SM_RF_GravelVergeR','SM_RF_BankL','SM_RF_BankR']
with bpy.data.libraries.load(str(ROOT/'Art/Export/RoadFordStyle/RoadFordStyle.blend')) as (src,dst):dst.objects=ground_names
ground=[];material=None
for ob in dst.objects:
    scene.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False
    if material is None:material=build(ob.data.materials[0],ROOT)
    ob.data.materials.clear();ob.data.materials.append(material);ground.append(ob)
    # The review is the first 26m only. Trim banks beyond it without changing source assets.
    import bmesh
    bm=bmesh.new();bm.from_mesh(ob.data)
    doomed=[v for v in bm.verts if v.co.x>26.001 or abs(v.co.y-center(v.co.x))>12.01]
    bmesh.ops.delete(bm,geom=doomed,context='VERTS');bm.to_mesh(ob.data);bm.free()
    for v in ob.data.vertices:
        s=v.co.x;t=v.co.y-center(s);v.co.z+=gravel_relief(s,t)
    # Smooth analytic normals keep shallow road relief free of visible tessellation.
    normals=[];eps=.01
    for v in ob.data.vertices:
        s=v.co.x;t=v.co.y-center(s)
        def height(a,b):return h(a,b)+gravel_relief(a,b)
        ds=(height(s+eps,t)-height(s-eps,t))/(2*eps)
        dt=(height(s,t+eps)-height(s,t-eps))/(2*eps)
        bend=(center(s+eps)-center(s-eps))/(2*eps)
        normals.append(Vector((-ds+bend*dt,-dt,1)).normalized())
    ob.data.normals_split_custom_set_from_vertices(normals)

def simple(name,color,vertex=False):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.9;p.inputs['Specular IOR Level'].default_value=.15
    if vertex:
        c=m.node_tree.nodes.new('ShaderNodeVertexColor');c.layer_name='Color';m.node_tree.links.new(c.outputs['Color'],p.inputs['Base Color'])
    return m

stone_mat=simple('M_GR_Stone',(.28,.29,.27),True)
palette=[(.23,.25,.245),(.39,.38,.33),(.13,.145,.145),(.30,.275,.225)]
prototypes=[];models=[]
for kind in range(4):
    # Irregular angular, flattened stones, with bevel-like rim rather than round spheres.
    count=7+kind%2;verts=[]
    angles=[i*math.tau/count+R.uniform(-.12,.12) for i in range(count)]
    radii=[R.uniform(.40,.52) for _ in angles]
    for level,z in enumerate([-.13,.07,.36]):
        for a,rad in zip(angles,radii):
            size=rad*[.82,1,.58][level]
            verts.append((math.cos(a)*size,math.sin(a)*size*R.uniform(.72,.96),z+R.uniform(-.03,.03)))
    faces=[]
    for ring in range(2):
        for i in range(count):
            a=ring*count+i;b=ring*count+(i+1)%count
            faces.extend([(a,b,b+count),(a,b+count,a+count)])
    for i in range(1,count-1):faces.append((2*count,2*count+i,2*count+i+1))
    me=bpy.data.meshes.new('Gravel '+str(kind));me.from_pydata(verts,[],faces);me.materials.append(stone_mat);me.update()
    color=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for p in me.polygons:
        c=palette[kind];shade=R.uniform(.92,1.06)
        for li in p.loop_indices:color.data[li].color=(*[v*shade for v in c],1)
    ob=bpy.data.objects.new('SM_GR_Stone'+str(kind+1),me);scene.collection.objects.link(ob);ob.hide_render=True;ob.hide_set(True)
    prototypes.append(ob);models.append(dict(name=ob.name,triangles=len(faces),width_m=1))

placements=[]
for _ in range(78000):
    s=R.uniform(.1,71.9);t=R.uniform(-3.25,3.25)
    if 26<s<47:continue
    lane=max(math.exp(-((t-.784-.12*math.sin(s*.29))/.33)**2),math.exp(-((t+.784-.12*math.sin(s*.29))/.35)**2))
    shoulder=smooth(1.1,2.6,abs(t));middle=math.exp(-(t/.45)**2)
    patch=.5+.5*noise(s,t,1.1)
    chance=(.075+.42*shoulder+.42*middle)*(.35+1.0*patch)*(1-.86*lane)
    if R.random()>chance or abs(t)>edge(s,t)+.48:continue
    width=R.uniform(.032,.087)
    if R.random()<.09 and shoulder>.5:width=R.uniform(.09,.13)
    kind=R.randrange(4);yaw=R.uniform(-math.pi,math.pi);sx=width*R.uniform(.9,1.35);sy=width
    location=(s,center(s)+t,h(s,t)+gravel_relief(s,t)+.001)
    row=dict(mesh=prototypes[kind].name,location_m=location,rotation_deg=[R.uniform(-8,8),R.uniform(-8,8),math.degrees(yaw)],scale=[sx,sy,width*R.uniform(.7,1.1)])
    placements.append(row)
    if s>26:continue
    ob=bpy.data.objects.new('Loose gravel',prototypes[kind].data);scene.collection.objects.link(ob);ob.location=location;ob.rotation_euler=[math.radians(v) for v in row['rotation_deg']];ob.scale=row['scale']

# Accepted grass shapes and palette, using the already-exported planting positions.
with bpy.data.libraries.load(str(ROOT/'Art/Export/TussockStyleStudy/07/TussockStyleStudy.blend')) as (src,dst):dst.objects=['Arching','Wind-combed','Upright','Fine undergrass']
grass_sources=dst.objects
grass_count=0
for row in json.loads((ROOT/'Art/Export/TussockStyle/manifest.json').read_text())['placements']:
    x,y,z=row['location_m']
    if x>26 or abs(y-center(x))>11:continue
    ob=bpy.data.objects.new('Accepted tussock',grass_sources[row['kind']].data);scene.collection.objects.link(ob)
    ob.location=(x,y,z);ob.rotation_euler=[math.radians(v) for v in row['rotation_deg']];ob.scale=(row['scale'],)*3;grass_count+=1

world=bpy.data.worlds.new('Soft cool daylight');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.47,.55,.65,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5
bpy.ops.object.light_add(type='SUN',location=(10,-10,14));sun=bpy.context.object;sun.name='Directional daylight';sun.data.energy=2.4;sun.data.angle=math.radians(4)
sun.rotation_euler=Vector((.55,.6,-.6)).to_track_quat('-Z','Y').to_euler()
def camera(name,pos,target,lens):
    bpy.ops.object.camera_add(location=pos);ob=bpy.context.object;ob.name=name;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.lens=lens;return ob
cameras=[camera('Driver',(5,center(5)-.32,h(5,0)+1.35),(24,center(24),.65),30),camera('SurfaceDetail',(11,center(11)-2.6,3.4),(14,center(14)+.1,.72),48)]
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4
scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
scene.render.image_settings.file_format='PNG';scene.camera=cameras[0]
for im in bpy.data.images:
    if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GravelRoadStudy.blend'))

# Export tiny stone meshes for later instancing; no collision or per-pebble actors intended.
for ob in prototypes:
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
    original=ob.data;ob.data=original.copy()
    for v in ob.data.vertices:v.co*=100
    scene.unit_settings.scale_length=.01
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
    copy=ob.data;ob.data=original;bpy.data.meshes.remove(copy);ob.hide_set(True)
scene.unit_settings.scale_length=1
report=dict(status='Blender study only; not imported or GPU benchmarked',models=models,placements=placements,grass_review_instances=grass_count,road_width_m=4.6,review_length_m=26,texture_tile_m=dict(coarse=5.4,fine=2.4),max_added_road_relief_m=.036,seed=290929)
(OUT/'manifest.json').write_text(json.dumps(report,indent=2))
print('GRAVEL_STUDY_SAVED',flush=True)
for cam in cameras:
    scene.camera=cam;scene.render.filepath=str(OUT/(cam.name+'.png'));bpy.ops.render.render(write_still=True)
print('GRAVEL_STUDY_REVIEW_OK',flush=True)
