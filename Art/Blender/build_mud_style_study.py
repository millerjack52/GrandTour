"""Mud art study using approved road/grass. Does not change Unreal deformation."""
import bpy,math,random,ast,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/MudStyleStudy/03';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Art/Export/GravelRoadStudy/04/GravelRoadStudy.blend'))
scene=bpy.context.scene;R=random.Random(300929)
tree=ast.parse((ROOT/'Art/Blender/build_road_ford_style.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['center','channel','smooth','noise','edge','h']],type_ignores=[]),'terrain','exec'))
tree=ast.parse((ROOT/'Art/Blender/build_gravel_road_study.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='gravel_relief'],type_ignores=[]),'relief','exec'))
def lanes(s):return [.79+.075*math.sin(s*.6),-.79+.10*math.sin(s*.48+.6)]
def masks(s,t):
    mud=smooth(5.5,9,s)*(1-smooth(23,26,s))*(1-smooth(1.75,2.85,abs(t)+.16*noise(s,t,1.2)))
    rut=max(math.exp(-((t-lane)/.25)**4) for lane in lanes(s))
    wet=rut*(.45+.45*smooth(-.5,.7,noise(s,t,1.6)))*mud
    return mud,wet,rut
def delta(s,t):
    mud,wet,rut=masks(s,t)
    cut=sum(-(.085+.018*noise(s,0,1.3))*math.exp(-((t-lane)/.25)**4) for lane in lanes(s))
    banks=sum(.055*(.65+.35*noise(s,t,.6))*math.exp(-((abs(t-lane)-.40)/.20)**2) for lane in lanes(s))
    clumps=.014*noise(s,t,.26)+.01*noise(s,t,.65)
    return mud*(cut+banks+clumps*(1-rut*.7))
def height(s,t):
    basins=sum(-.045*math.exp(-3*((s-s0)/length)**4-3*((t-lanes(s)[index])/.22)**4) for s0,index,length in [(12.3,0,.78),(17.1,1,1.05),(21.6,0,.72)])
    return h(s,t)+gravel_relief(s,t)+delta(s,t)+basins

original=bpy.data.materials['M_GR_PaintedGravel'];mat=original.copy();mat.name='M_MS_PaintedMud'
ns=mat.node_tree.nodes;ls=mat.node_tree.links;p=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
old_color=p.inputs['Base Color'].links[0].from_socket;old_normal=p.inputs['Normal'].links[0].from_socket
def node(kind,label):
    n=ns.new(kind);n.label=label;return n
def wire(value,socket):
    if isinstance(value,(int,float,tuple,list)):socket.default_value=value
    else:ls.new(value,socket)
def mathop(op,a,b=0):
    n=node('ShaderNodeMath',op);n.operation=op;wire(a,n.inputs[0]);wire(b,n.inputs[1]);return n.outputs[0]
def mix(a,b,f):
    n=node('ShaderNodeMixRGB','Paint blend');wire(f,n.inputs[0]);wire(a,n.inputs[1]);wire(b,n.inputs[2]);return n.outputs[0]
def vec(op,a,b):
    n=node('ShaderNodeVectorMath',op);n.operation=op;wire(a,n.inputs[0]);wire(b,n.inputs['Scale'] if op=='SCALE' else n.inputs[1]);return n.outputs[0]
def ramp(value,colors):
    n=node('ShaderNodeValToRGB','Earth palette');n.color_ramp.interpolation='EASE'
    for i,(pos,col) in enumerate(colors):
        e=n.color_ramp.elements[i] if i<2 else n.color_ramp.elements.new(pos);e.position=pos;e.color=(*col,1)
    wire(value,n.inputs[0]);return n.outputs[0]
attr=node('ShaderNodeVertexColor','Mud / wetness / worked-floor masks');attr.layer_name='MudMasks'
sep=node('ShaderNodeSeparateColor','Surface zones');wire(attr.outputs['Color'],sep.inputs[0]);mud,wet,rut=sep.outputs[:3]
uv=node('ShaderNodeUVMap','World continuous ground');uv.uv_map='UVMap';metres=vec('SCALE',uv.outputs[0],3)
wash=node('ShaderNodeTexNoise','Broad umber and clay patches');wash.inputs['Scale'].default_value=2.2;wash.inputs['Detail'].default_value=1;wire(metres,wash.inputs['Vector'])
earth=ramp(wash.outputs['Fac'],[(.18,(.115,.067,.037)),(.50,(.18,.109,.061)),(.8,(.255,.164,.095))])
dab=node('ShaderNodeTexNoise','Broken clay paint shapes');dab.inputs['Scale'].default_value=9;dab.inputs['Detail'].default_value=1;wire(vec('MULTIPLY',metres,(.7,1.3,1)),dab.inputs['Vector'])
clay=ramp(dab.outputs['Fac'],[(.27,(.085,.065,.047)),(.43,(.12,.087,.057)),(.57,(.19,.139,.082)),(.72,(.15,.116,.076))])
earth=mix(earth,clay,.12)
# Irregular shallow clay plates: broken, softened seams instead of cloudy speckles.
warp=node('ShaderNodeTexNoise','Small chipped deviations in clay edges');warp.inputs['Scale'].default_value=11;warp.inputs['Detail'].default_value=1;wire(metres,warp.inputs['Vector'])
warped=vec('ADD',metres,vec('SCALE',vec('SUBTRACT',warp.outputs['Color'],(.5,.5,.5)),.055))
plates=node('ShaderNodeTexVoronoi','Broad overlapping clay faces');plates.voronoi_dimensions='2D';plates.feature='F1';plates.inputs['Scale'].default_value=3.8;wire(warped,plates.inputs['Vector'])
seams=node('ShaderNodeTexVoronoi','Shallow broken plate edges');seams.voronoi_dimensions='2D';seams.feature='DISTANCE_TO_EDGE';seams.inputs['Scale'].default_value=3.8;wire(warped,seams.inputs['Vector'])
plate_colors=ramp(plates.outputs['Color'],[(.15,(.135,.078,.041)),(.48,(.195,.117,.064)),(.82,(.245,.157,.093))])
earth=mix(earth,plate_colors,.47)
ledge=ramp(seams.outputs['Distance'],[(.0,(.12,.12,.12)),(.026,(.25,.25,.25)),(.072,(.85,.85,.85)),(.19,(.96,.96,.96))])
breakup=ramp(dab.outputs['Fac'],[(.34,(0,0,0)),(.48,(.12,.12,.12)),(.65,(1,1,1))])
broken=mathop('MULTIPLY',mix((1,1,1,1),ledge,breakup),mathop('ADD',.85,mathop('MULTIPLY',dab.outputs['Fac'],.15)))
# Most of each face remains quiet; only interrupted edges catch the light.
edge_shade=mix((.82,.79,.75,1),(1.02,1.01,1,1),mix((1,1,1,1),ledge,breakup))
plate_tint=node('ShaderNodeMixRGB','Clay edge depth');plate_tint.blend_type='MULTIPLY';plate_tint.inputs[0].default_value=.35;wire(earth,plate_tint.inputs[1]);wire(edge_shade,plate_tint.inputs[2]);earth=plate_tint.outputs[0]
smear=node('ShaderNodeTexNoise','Dragged paint and compressed streaks');smear.inputs['Scale'].default_value=1;smear.inputs['Detail'].default_value=1;wire(vec('MULTIPLY',metres,(3.8,34,1)),smear.inputs['Vector'])
worked=ramp(smear.outputs['Fac'],[(.2,(.057,.047,.037)),(.8,(.105,.083,.06))])
earth=mix(earth,worked,mathop('MULTIPLY',rut,.8))
grain=node('ShaderNodeTexNoise','Small clay clumps');grain.inputs['Scale'].default_value=22;grain.inputs['Detail'].default_value=0;wire(metres,grain.inputs['Vector'])
paint=mix((.88,.9,.92,1),(1.08,1.055,1.015,1),grain.outputs['Fac'])
mult=node('ShaderNodeMixRGB','Broken paint coverage');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=.75;wire(earth,mult.inputs[1]);wire(paint,mult.inputs[2])
wire(mix(old_color,mult.outputs[0],mud),p.inputs['Base Color'])
wire(mathop('SUBTRACT',.88,mathop('MULTIPLY',wet,.40)),p.inputs['Roughness'])
bump=node('ShaderNodeBump','Subtle clay grain');bump.inputs['Distance'].default_value=.003;bump.inputs['Strength'].default_value=.22
wire(mix(grain.outputs['Fac'],smear.outputs['Fac'],rut),bump.inputs['Height'])
relief=node('ShaderNodeBump','Shallow chipped clay ledges');relief.inputs['Distance'].default_value=.017;relief.inputs['Strength'].default_value=.6
wire(mathop('MULTIPLY',broken,mathop('SUBTRACT',1,mathop('MULTIPLY',rut,.93))),relief.inputs['Height']);wire(bump.outputs[0],relief.inputs['Normal'])
wire(mix(old_normal,relief.outputs[0],mud),p.inputs['Normal'])
p.inputs['Specular IOR Level'].default_value=.27

grounds=[];coated_meshes={};embedded_stones=0
for ob in list(scene.objects):
    if ob.type!='MESH':continue
    if ob.name.startswith('Loose gravel'):
        s=ob.location.x;t=ob.location.y-center(s)
        if masks(s,t)[0]>.2:
            # Retain sparse embedded aggregate, separate from displaced clay clods.
            keep=(math.sin(s*137.2+t*91.7)*43758.5453)%1<.12 and masks(s,t)[2]<.25
            ob.hide_render=not keep
            if keep:
                ob.location.z=height(s,t)-.012;embedded_stones+=1
                key=ob.data.name
                if key not in coated_meshes:
                    mesh=ob.data.copy();mesh.name=key+' clay coated'
                    for color in mesh.color_attributes['Color'].data:
                        r,g,b,a=color.color;color.color=(r*.70,g*.52,b*.36,a)
                    coated_meshes[key]=mesh
                ob.data=coated_meshes[key]
        continue
    if not ob.name.startswith(('SM_RF_DryRoad','SM_RF_GravelVerge','SM_RF_Bank')):continue
    grounds.append(ob);ob.data.materials.clear();ob.data.materials.append(mat)
    if ob.name.startswith('SM_RF_DryRoad'):
        import bmesh
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True);bm.to_mesh(ob.data);bm.free()
    ca=ob.data.color_attributes.new(name='MudMasks',type='FLOAT_COLOR',domain='CORNER')
    for v in ob.data.vertices:v.co.z=height(v.co.x,v.co.y-center(v.co.x))
    for loop in ob.data.loops:
        v=ob.data.vertices[loop.vertex_index].co;ca.data[loop.index].color=(*masks(v.x,v.y-center(v.x)),1)
    normals=[];eps=.01
    for v in ob.data.vertices:
        s=v.co.x;t=v.co.y-center(s);ds=(height(s+eps,t)-height(s-eps,t))/(2*eps);dt=(height(s,t+eps)-height(s,t-eps))/(2*eps);bend=(center(s+eps)-center(s-eps))/(2*eps)
        normals.append(Vector((-ds+bend*dt,-dt,1)).normalized())
    ob.data.normals_split_custom_set_from_vertices(normals)

def simple(name,color,rough=.9):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;return m
clod_mats=[simple('Mud clod '+str(i),c) for i,c in enumerate([(.17,.099,.052),(.215,.13,.075),(.12,.078,.047)])]
sources=[]
for kind in range(3):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1);ob=bpy.context.object;ob.name='SM_MS_SoftClod'+str(kind)
    for v in ob.data.vertices:v.co*=R.uniform(.83,1.1);v.co.z*=.46
    for poly in ob.data.polygons:poly.use_smooth=False
    ob.data.materials.append(clod_mats[kind]);ob.hide_render=True;sources.append(ob)
clods=0
for _ in range(250):
    s=R.uniform(8.5,24);lane=R.choice(lanes(s));t=lane+R.choice([-1,1])*R.uniform(.27,.55)
    if R.random()>.55+.3*noise(s,t,.6):continue
    ob=bpy.data.objects.new('Displaced mud clod',R.choice(sources).data);scene.collection.objects.link(ob)
    size=R.uniform(.045,.13);ob.location=(s,center(s)+t,height(s,t)-size*.19);ob.scale=(size*R.uniform(1.3,2.4),size*.85,size*.65);ob.rotation_euler.z=R.uniform(-.6,.6);clods+=1

# Clip flat water triangles against terrain height and pool extents for natural shores.
water=simple('M_MS_ShallowRutWater',(.042,.055,.058),.22)
water.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.333
pools=[]
for s0,index,length in [(12.3,0,.78),(17.1,1,1.05),(21.6,0,.72)]:
    t0=lanes(s0)[index]
    rim=[]
    for k in range(64):
        angle=k*math.tau/64;s=s0+length*.98*math.cos(angle);t=lanes(s)[index]+.29*.98*math.sin(angle);rim.append(height(s,t))
    level=min(height(s0,t0)+.026,min(rim)-.006);verts=[];faces=[];step=.035
    nx=int(length*2/step);ny=16
    def point(i,j):
        s=s0-length+i*2*length/nx;t=lanes(s)[index]+(j/ny-.5)*.6
        value=min(level-height(s,t),(.98-((s-s0)/length)**2-((t-lanes(s)[index])/.29)**2)*.05)
        return (Vector((s,center(s)+t,level)),value)
    for i in range(nx):
        for j in range(ny):
            a,b,c,d=point(i,j),point(i+1,j),point(i+1,j+1),point(i,j+1)
            for tri in [(a,b,c),(a,c,d)]:
                poly=[]
                for k,current in enumerate(tri):
                    previous=tri[k-1];inside=current[1]>=0;was=previous[1]>=0
                    if inside!=was:
                        f=previous[1]/(previous[1]-current[1]);poly.append(previous[0].lerp(current[0],f))
                    if inside:poly.append(current[0])
                if len(poly)>=3:
                    first=len(verts);verts.extend(poly);faces.append(tuple(range(first,first+len(poly))))
    me=bpy.data.meshes.new('Clipped shallow water');me.from_pydata(verts,[],faces);me.materials.append(water);ob=bpy.data.objects.new('Shallow rut pool',me);scene.collection.objects.link(ob);pools.append(len(faces))

scene.cycles.device='CPU';scene.cycles.samples=40;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.camera=bpy.data.objects['Driver'];scene.render.filepath=str(OUT/'Driver.png')
for im in bpy.data.images:
    if im.source=='FILE' and not im.packed_file:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MudStyleStudy.blend'))
(OUT/'source').mkdir(exist_ok=True);(OUT/'source'/Path(__file__).name).write_text(Path(__file__).read_text())
(OUT/'manifest.json').write_text(json.dumps(dict(status='Static Blender art study; no Unreal or deformation tuning',source='Approved gravel 04 and tussock 07',clod_instances=clods,embedded_stones=embedded_stones,pool_polygons=pools,mask_channels=['mud coverage','wetness','rut coverage']),indent=2))
for name in ['Driver','SurfaceDetail']:
    scene.camera=bpy.data.objects[name];scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('MUD_STYLE_REVIEW_OK',flush=True)
