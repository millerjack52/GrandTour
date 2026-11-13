"""First authored road geometry study. New source/export files only; deterministic seed.
CC0 Poly Haven gravel, recoloured in the material; original source maps are untouched.
"""
import bpy, math, random, json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/RoadBenchmark'
OUT.mkdir(parents=True, exist_ok=True)
R = random.Random(2809)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

def material(name, color, texture=None):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    n = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    n.inputs['Base Color'].default_value = (*color, 1)
    n.inputs['Roughness'].default_value = .9
    if texture:
        im = m.node_tree.nodes.new('ShaderNodeTexImage')
        im.image = bpy.data.images.load(str(texture))
        ramp = m.node_tree.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.025
        ramp.color_ramp.elements[0].color=(*[c*.48 for c in color],1)
        ramp.color_ramp.elements[1].position=.48
        ramp.color_ramp.elements[1].color=(*[min(1,c*1.45) for c in color],1)
        for pos,mul in [(.12,.72),(.24,1.02)]:
            el=ramp.color_ramp.elements.new(pos); el.color=(*[c*mul for c in color],1)
        vc = m.node_tree.nodes.new('ShaderNodeVertexColor')
        vc.layer_name = 'Color'
        coarse=m.node_tree.nodes.new('ShaderNodeTexImage')
        coarse.image=bpy.data.images.load(str(ROOT/'Art/Textures/RoadBenchmark/gravel_floor_02_diff_2k.jpg'))
        remap=m.node_tree.nodes.new('ShaderNodeMapRange')
        remap.inputs['From Min'].default_value=.7; remap.inputs['From Max'].default_value=.97
        split=m.node_tree.nodes.new('ShaderNodeSeparateColor')
        m.node_tree.links.new(vc.outputs['Color'],split.inputs[0])
        m.node_tree.links.new(split.outputs['Red'],remap.inputs['Value'])
        layers=m.node_tree.nodes.new('ShaderNodeMixRGB')
        m.node_tree.links.new(remap.outputs['Result'],layers.inputs[0])
        m.node_tree.links.new(coarse.outputs['Color'],layers.inputs[1])
        m.node_tree.links.new(im.outputs['Color'],layers.inputs[2])
        m.node_tree.links.new(layers.outputs[0],ramp.inputs[0])
        mix = m.node_tree.nodes.new('ShaderNodeMixRGB')
        mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1
        m.node_tree.links.new(ramp.outputs['Color'], mix.inputs[1])
        m.node_tree.links.new(vc.outputs['Color'], mix.inputs[2])
        m.node_tree.links.new(mix.outputs[0], n.inputs['Base Color'])
        normal=m.node_tree.nodes.new('ShaderNodeTexImage')
        normal.image=bpy.data.images.load(str(ROOT/'Art/Textures/RoadBenchmark/gravel_floor_02_nor_gl_2k.jpg'))
        normal.image.colorspace_settings.name='Non-Color'
        nm=m.node_tree.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value=.4
        m.node_tree.links.new(normal.outputs['Color'],nm.inputs['Color'])
        m.node_tree.links.new(nm.outputs['Normal'],n.inputs['Normal'])
    return m

dirt = material('M_RB_Dirt', (.55,.45,.31), ROOT/'Art/Textures/RoadBenchmark/gravel_floor_04_diff_2k.jpg')
ground = dirt
stones = [material('M_RB_Stone'+str(i), c) for i,c in enumerate([(.30,.32,.32),(.41,.39,.33),(.22,.25,.27)])]
grasses = [material('M_RB_Grass'+str(i), c) for i,c in enumerate([(.40,.29,.10),(.57,.43,.17),(.29,.27,.11)])]

def center(s): return .012*s*s
def xy(s,t):
    a = math.atan(.024*s)
    return s-t*math.sin(a), center(s)+t*math.cos(a)
def height(s,t):
    crown = .045*math.exp(-(t/1.5)**2)
    rut = -.035*(math.exp(-((t-.784)/.24)**2)+math.exp(-((t+.784)/.24)**2))
    corr = .009*math.sin(s*math.tau/.48)*math.exp(-((s-14)/4)**2)*math.exp(-(t/1.65)**6)
    bank = max(0,abs(t)-2.3)*.06
    return .018*s + crown + rut + corr + bank + .007*math.sin(s*2+t*3)

def grid(name, ts, count, mat):
    verts, faces, colors, uv = [],[],[],[]
    for i in range(count+1):
        s = 24*i/count
        for t in ts:
            offset=math.sin(s*2.2)*.055+math.sin(s*.7)*.08
            adjusted=t+offset*min(1,abs(t)/2.3)**3
            x,y = xy(s,adjusted)
            verts.append((x,y,height(s,t)))
            lane = max(math.exp(-((t-.784)/.33)**2),math.exp(-((t+.784)/.33)**2))
            k=.70+.27*lane+.035*math.sin(s*1.8+t*6)
            w=max(0,min(1,(abs(t)-1.65)/1.8)); w=w*w*(3-2*w)
            colors.append((k*(1-w)+.66*w,k*.97*(1-w)+.70*w,k*.89*(1-w)+.41*w,1))
            uv.append((s/10,t/10))
    w=len(ts)
    for i in range(count):
        for j in range(w-1):
            a=i*w+j
            faces.append((a,a+w,a+w+1,a+1))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    ca=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    uv_layer=mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            vi=mesh.loops[li].vertex_index
            ca.data[li].color=colors[vi]
            uv_layer.data[li].uv=uv[vi]
    return obj

road=grid('SM_GT_RoadBenchmark_Bend',[(-2.3+i*4.6/46) for i in range(47)],120,dirt)
left=grid('SM_GT_RoadBenchmark_ShoulderL',[-7+i*4.7/16 for i in range(17)],120,ground)
right=grid('SM_GT_RoadBenchmark_ShoulderR',[2.3+i*4.7/16 for i in range(17)],120,ground)
prototypes=[]
for i in range(3):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1)
    obj=bpy.context.object; obj.name='SM_GT_RoadStone_'+str(i+1)
    for v in obj.data.vertices:
        v.co.x*=R.uniform(.75,1.2); v.co.y*=R.uniform(.7,1.15)
        v.co.z=v.co.z*R.uniform(.35,.6)+.3
    obj.data.materials.append(stones[i]); prototypes.append(obj)
for i in range(3):
    verts, faces=[],[]
    for k in range(24+i*6):
        a=R.uniform(0,math.tau); h=R.uniform(.16,.40)*(1+i*.2)
        rad=R.uniform(.015,.09); wide=R.uniform(.012,.035)
        base=Vector((math.cos(a)*rad,math.sin(a)*rad,0))
        tip=base+Vector((math.cos(a)*h*.65,math.sin(a)*h*.65,h))
        mid=base.lerp(tip,.55)+Vector((0,0,h*.1))
        side=Vector((-math.sin(a)*wide,math.cos(a)*wide,0))
        n=len(verts); verts.extend([tuple(base-side),tuple(base+side),tuple(mid+side*.65),tuple(mid-side*.65),tuple(tip)])
        faces.extend([(n,n+1,n+2,n+3),(n+3,n+2,n+4)])
    me=bpy.data.meshes.new('Tuft'); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new('SM_GT_Tussock_'+str(i+1),me); scene.collection.objects.link(ob)
    for m in grasses: me.materials.append(m)
    for p in me.polygons: p.material_index=R.randrange(3)
    prototypes.append(ob)

placements=[]
def place(proto,s,t,scale,solid=False):
    x,y=xy(s,t); z=height(s,t)-.006
    yaw=R.uniform(-math.pi,math.pi)
    ob=bpy.data.objects.new('Placed_'+proto.name,proto.data); scene.collection.objects.link(ob)
    ob.location=(x,y,z); ob.rotation_euler.z=yaw; ob.scale=(scale,scale,scale)
    placements.append(dict(mesh=proto.name,location_m=[x,y,z],yaw_deg=math.degrees(yaw),scale=scale,collision=solid))

for _ in range(320):
    s=R.uniform(.2,23.8)
    t=R.uniform(-.42,.42) if R.random()<.5 else R.choice([-1,1])*R.uniform(1.18,2.65)
    place(R.choice(prototypes[:3]),s,t,R.uniform(.025,.085))
for _ in range(12):
    place(R.choice(prototypes[:3]),R.uniform(4,23),R.choice([-1,1])*R.uniform(1.55,3.0),R.uniform(.15,.32),True)
for _ in range(100):
    place(R.choice(prototypes[3:]),R.uniform(.1,23.9),R.choice([-1,1])*R.uniform(2.1,6.7),R.uniform(.7,1.6))
for s in [3.2,9.4,16.2,20.1]: place(prototypes[3],s,R.uniform(-.2,.2),.52)

for ob in prototypes: ob.hide_render=True; ob.hide_set(True)

def camera(name, loc, target, lens):
    bpy.ops.object.camera_add(location=loc)
    ob=bpy.context.object; ob.name=name
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    ob.data.lens=lens; ob.data.clip_end=1000
    return ob
driver=camera('Driver_height_135cm',(-.8,-.4,1.4),(14,center(14),.65),24)
overview=camera('Road_geometry_review',(6,-13,12),(12,2,.2),35)
closeup=camera('Surface_detail',(9,center(9)-3,2.3),(13,center(13),.2),45)
bpy.ops.object.light_add(type='SUN',location=(4,-4,8))
sun=bpy.context.object; sun.rotation_euler=(.45,-.55,-.5); sun.data.energy=2.1; sun.data.angle=.05
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.25,.35,.50,1); bg.inputs['Strength'].default_value=.6
try: scene.render.engine='CYCLES'
except TypeError: pass
scene.cycles.samples=24
scene.render.resolution_x=1440; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=.65
scene.render.image_settings.file_format='PNG'
for im in bpy.data.images:
    if im.source=='FILE': im.pack()
scene.camera=driver
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RoadBenchmark.blend'))

export=[]
scene.unit_settings.scale_length=.01
for ob in [road,left,right]+prototypes:
    bpy.ops.object.select_all(action='DESELECT')
    ob.hide_set(False); ob.select_set(True); bpy.context.view_layer.objects.active=ob
    # Match the established export's centimetre geometry and FBX axis contract.
    meshcopy=ob.data.copy(); original=ob.data; ob.data=meshcopy
    for v in meshcopy.vertices: v.co*=100
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
        bake_space_transform=False,mesh_smooth_type='FACE',bake_anim=False)
    ob.data=original; bpy.data.meshes.remove(meshcopy)
    export.append(dict(name=ob.name,vertices=len(ob.data.vertices),triangles=sum(len(p.vertices)-2 for p in ob.data.polygons),materials=[m.name for m in ob.data.materials]))
    if ob in prototypes: ob.hide_set(True)

scene.unit_settings.scale_length=1.0
(OUT/'manifest.json').write_text(json.dumps(dict(seed=2809,length_m=24,road_width_m=4.6,wheel_track_m=1.568,assets=export,placements=placements),indent=2))
for cam in [driver,overview,closeup]:
    scene.camera=cam; scene.render.filepath=str(OUT/(cam.name+'.png')); bpy.ops.render.render(write_still=True)
print('ROAD_BENCHMARK_OK',json.dumps(dict(assets=len(export),placements=len(placements),triangles=sum(x['triangles'] for x in export))))
