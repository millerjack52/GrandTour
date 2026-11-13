"""Extend the accepted road vocabulary into an isolated, static ford art assembly."""
import bpy, json, math, random, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/RoadFordStyle'
OUT.mkdir(parents=True, exist_ok=True)
R = random.Random(2909)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
with bpy.data.libraries.load(str(ROOT/'Art/Export/RoadBenchmark/RoadBenchmark.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith(('SM_GT_RoadStone_', 'SM_GT_Tussock_'))]
prototypes = []
for ob in dst.objects:
    scene.collection.objects.link(ob)
    ob.name = ob.name.replace('SM_GT_', 'SM_RF_')
    ob.hide_render = True
    ob.hide_set(True)
    prototypes.append(ob)
stones = [o for o in prototypes if 'RoadStone' in o.name]
grasses = [o for o in prototypes if 'Tussock' in o.name]
with bpy.data.libraries.load(str(ROOT/'Art/Export/RoadBenchmark/RoadBenchmark.blend'), link=False) as (src,dst):
    dst.materials = ['M_RB_Dirt']
dirt = dst.materials[0]
specs = []

# Keep the same meshes while giving stones and dry tussocks distinct colour families.
for family, palette in [('Stone',[(.16,.215,.28),(.34,.265,.15),(.075,.115,.17)]),
                        ('Grass',[(.30,.23,.12),(.38,.30,.17),(.22,.155,.075)])]:
    for i,color in enumerate(palette):
        mat=bpy.data.materials.get('M_RB_'+family+str(i))
        mat.diffuse_color=(*color,1)
        next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(*color,1)
        specs.append(dict(name=mat.name,color=color,roughness=.9,vertex=False,textured=False))

def simple(name, color, roughness=.9, vertex=False):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.diffuse_color=(*color,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=roughness
    if vertex:
        vc=m.node_tree.nodes.new('ShaderNodeVertexColor'); vc.layer_name='Color'
        mix=m.node_tree.nodes.new('ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=1
        mix.inputs[1].default_value=(*color,1)
        m.node_tree.links.new(vc.outputs['Color'],mix.inputs[2]); m.node_tree.links.new(mix.outputs[0],p.inputs['Base Color'])
    specs.append(dict(name=name,color=color,roughness=roughness,vertex=vertex,textured=False))
    return m

# Shared material; explicit gravel/meadow and wetness masks are in UV channel 1.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ground_material_v2 import build as build_ground_material
dirt=build_ground_material(dirt,ROOT)
mud=bankmat=dirt
specs.append(dict(name=dirt.name,color=[1,1,1],roughness=.9,vertex=False,textured=True,surface_blend=True))
water=simple('M_RF_WaterPreview',(.028,.19,.23),.26)
waterlight=simple('M_RF_WaterStroke',(.18,.42,.45),.36)
wood=simple('M_RF_WeatheredPost',(.28,.22,.14))
marker=simple('M_RF_Marker',(.73,.62,.39))
wetstone=simple('M_RF_WetStone',(.075,.13,.17),.65)
hillmat=simple('M_RF_DistantHill',(.075,.14,.23),vertex=True)

def center(s): return 1.8*math.sin(s/17)
def channel(t): return 43+.65*math.sin(t/6)
def smooth(a,b,x):
    v=max(0,min(1,(x-a)/(b-a))); return v*v*(3-2*v)
def noise(s,t,scale=1):
    x=s/scale; y=t/scale; ix=math.floor(x); iy=math.floor(y)
    fx=smooth(0,1,x-ix); fy=smooth(0,1,y-iy)
    def value(a,b):
        v=math.sin(a*127.1+b*311.7+29.09)*43758.5453
        return (v-math.floor(v))*2-1
    return (value(ix,iy)*(1-fx)+value(ix+1,iy)*fx)*(1-fy)+(value(ix,iy+1)*(1-fx)+value(ix+1,iy+1)*fx)*fy
def edge(s,t): return 2.15+.55*noise(s,5 if t>0 else -5,3.1)+.23*noise(s,t,.8)
def blend_color(a,b,w): return tuple(x*(1-w)+y*w for x,y in zip(a,b))
spills=[(8,-1.8,1.5,.7),(15,1.4,1.7,.65),(22,-.1,1.3,.5),(28,1.8,1.1,.6),(37,-1.7,.9,.55),(51,1.3,1.7,.8),(59,-1.5,1.6,.65),(65,.2,1.1,.45)]
def surface_masks(s,t):
    n=noise(s,t,.55)
    ground=smooth(edge(s,t)-.4,edge(s,t)+1.05,abs(t)+.25*n)
    moisture=math.exp(-((s-34+.4*math.sin(t*4))/6)**4)*math.exp(-(abs(t)/2.05)**6)
    return ground,moisture

def surface(s,t):
    # Neutral broad tint preserves the authored colour contrast within each texture.
    ground,moisture=surface_masks(s,t)
    lane=max(math.exp(-((t-.784-.12*math.sin(s*.29))/.30)**2),math.exp(-((t+.784-.12*math.sin(s*.29))/.34)**2))
    value=.84+.12*noise(s,t,2.7)+.055*noise(s,t,.55)
    for ps,pt,rs,rt in spills:
        value+=.10*math.exp(-(((s-ps)/rs)**2+((t-pt)/rt)**2)*1.6)
    value=max(.63,min(1,value))
    return (value,value,value,1-.68*lane)
def h(s,t):
    c=math.exp(-((s-channel(t))/3.9)**4)
    side=max(0,abs(t)-2.3)
    relief=(.035*side + .006*side*side)*(1-c)
    relief*=.7+.3*math.sin(s*.13+t*.07)**2
    crown=.045*math.exp(-(t/1.6)**2)
    moist=math.exp(-((s-34)/7)**4)
    rut=-(.03+.095*moist)*(math.exp(-((t-.784)/.24)**2)+math.exp(-((t+.784)/.24)**2))
    wear=1-smooth(1.7,3.8,abs(t))
    undulation=.045*noise(s,t,1.8)+.018*noise(s,t,.4)
    potholes=sum(-depth*math.exp(-(((s-ps)/rs)**2+((t-pt)/rt)**2)*2) for ps,pt,rs,rt,depth in [(17,-.5,.65,.42,.10),(23,1.0,.85,.45,.085),(55,-1.1,.8,.5,.11)])
    erosion=-.10*math.exp(-((t-(edge(s,t)+.2)*(1 if t>0 else -1))/.28)**2)*( .5+.5*noise(s,0,2))
    return .72-1.02*c+relief+crown+rut+(undulation+potholes)*wear*(1-c)+erosion*(1-c)

def mesh(name,verts,faces,mat,colors=None,uvs=None,smooth=True):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob); me.materials.append(mat)
    ca=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    layer=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        p.use_smooth=smooth
        for li in p.loop_indices:
            vi=me.loops[li].vertex_index
            ca.data[li].color=colors[vi] if colors else (1,1,1,1)
            layer.data[li].uv=uvs[vi] if uvs else (verts[vi][0]/10,verts[vi][1]/10)
    return ob

def grid(name,start,end,ts,count,mat):
    verts=[]; colors=[]; faces=[]; uv=[]
    for i in range(count+1):
        s=start+(end-start)*i/count
        for t in ts:
            verts.append((s,center(s)+t,h(s,t)))
            colors.append(surface(s,t))
            uv.append((s/3,t/3))
    w=len(ts)
    for i in range(count):
        for j in range(w-1):
            a=i*w+j
            if abs((ts[j]+ts[j+1])*.5)>2.8:
                if (i+j)%2: faces.extend([(a,a+w,a+1),(a+1,a+w,a+w+1)])
                else: faces.extend([(a,a+w,a+w+1),(a,a+w+1,a+1)])
            else: faces.append((a,a+w,a+w+1,a+1))
    ob=mesh(name,verts,faces,mat,colors,uv)
    masks=ob.data.uv_layers.new(name='SurfaceMasks')
    for loop in ob.data.loops:
        vi=loop.vertex_index; ps=verts[vi][0]; pt=verts[vi][1]-center(ps)
        masks.data[loop.index].uv=surface_masks(ps,pt)
    # Continuous tint and analytic height-field normals conceal the terrain grid.
    # Adjacent chunks evaluate identical normals at their shared boundary.
    normals=[]
    step=.01
    for ps,py,pz in verts:
        pt=py-center(ps)
        ds=(h(ps+step,pt)-h(ps-step,pt))/(2*step)
        dt=(h(ps,pt+step)-h(ps,pt-step))/(2*step)
        bend=(center(ps+step)-center(ps-step))/(2*step)
        normals.append(Vector((-ds+bend*dt,-dt,1)).normalized())
    ob.data.normals_split_custom_set_from_vertices(normals)
    return ob

assets=[]; physical={}; static=[]
ts=[-2.3+i*4.6/24 for i in range(25)]
for title,start,end,mat,phys in [('DryRoad',0,26,dirt,'Dirt'),('MudApproach',26,39,mud,'Mud'),('FordBed',39,47,dirt,'Dirt'),('ExitRoad',47,72,dirt,'Dirt')]:
    ob=grid('SM_RF_'+title,start,end,ts,int((end-start)*4),mat)
    assets.append(ob); static.append(ob); physical[ob.name]=phys
for suffix,side in [('L',-1),('R',1)]:
    # Narrow gravel shoulders share the exact road-edge vertices.
    t=[side*(2.3+i*1.7/8) for i in range(9)]
    if side<0: t.reverse()
    ob=grid('SM_RF_GravelVerge'+suffix,0,72,t,288,dirt)
    assets.append(ob); static.append(ob); physical[ob.name]='Dirt'
    t=[side*x for x in ([4+i*.25 for i in range(17)]+[9+i for i in range(24)])]
    if side<0: t.reverse()
    ob=grid('SM_RF_Bank'+suffix,0,72,t,288,bankmat)
    assets.append(ob); static.append(ob); physical[ob.name]='Dirt'

# A deliberately static surface: it communicates water composition without claiming simulation.
verts=[]; faces=[]
for j in range(161):
    t=-32+j*.4
    for i in range(13):
        s=channel(t)-3.4+i*6.8/12
        verts.append((s,center(s)+t,.14+.007*math.sin(t*2.5+s*3)))
for j in range(160):
    for i in range(12):
        a=j*13+i; faces.append((a,a+1,a+14,a+13))
ob=mesh('SM_RF_Water_STATIC_PREVIEW',verts,faces,water)
assets.append(ob); static.append(ob); physical[ob.name]=None
verts=[]; faces=[]
for _ in range(85):
    t=R.uniform(-31,31); s=channel(t)+R.uniform(-2.65,2.65)
    length=R.uniform(.15,.65); width=R.uniform(.025,.065)
    y=center(s)+t; n=len(verts)
    verts.extend([(s-width,y-length,.157),(s+width,y-length*.7,.157),(s+width*.5,y+length,.157),(s-width*.6,y+length*.8,.157)])
    faces.append((n,n+1,n+2,n+3))
ob=mesh('SM_RF_WaterBrushStrokes',verts,faces,waterlight,smooth=False)
assets.append(ob); static.append(ob); physical[ob.name]=None

# Elongated river stones, a squat bank boulder and simple weathered crossing markers.
for i in range(3):
    ob=stones[i].copy(); ob.data=stones[i].data.copy(); ob.name='SM_RF_FordRock'+str(i+1)
    scene.collection.objects.link(ob)
    for v in ob.data.vertices: v.co.x*=1.35; v.co.y*=.8; v.co.z*=.8
    ob.data.materials.clear(); ob.data.materials.append(wetstone)
    prototypes.append(ob)
verts=[(-.075,-.06,0),(.075,-.06,0),(.075,.06,0),(-.075,.06,0),(-.055,-.045,1.02),(.068,-.05,1.04),(.061,.047,1.05),(-.062,.056,1.01)]
faces=[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
post=mesh('SM_RF_FordMarkerPost',verts,faces,wood,smooth=False)
post.data.materials.append(marker); post.data.polygons[-1].material_index=1
prototypes.append(post)

placements=[]
def place(proto,s,t,scale,solid=False,z=None):
    ob=bpy.data.objects.new('Placed_'+proto.name,proto.data); scene.collection.objects.link(ob)
    ob.location=(s,center(s)+t,h(s,t)-.035 if z is None else z)
    ob.rotation_euler.z=R.uniform(-math.pi,math.pi); ob.scale=(scale,scale,scale)
    placements.append(dict(mesh=proto.name,location_m=list(ob.location),yaw_deg=math.degrees(ob.rotation_euler.z),scale=scale,collision=solid))

for _ in range(1200):
    s=R.uniform(.2,71.8)
    t=R.choice([-1,1])*R.uniform(1.15,4.2) if R.random()<.8 else R.uniform(-.35,.35)
    if 27<s<39 and abs(t)<1.8: continue
    place(R.choice(stones),s,t,R.uniform(.022,.075))
for ps,pt,rs,rt in spills:
    for _ in range(55):
        s=ps+R.gauss(0,rs*.55); t=pt+R.gauss(0,rt*.6)
        place(R.choice(stones),s,t,R.uniform(.025,.095))
# Small verge clusters intrude into gravel, following the irregular material boundary.
for _ in range(340):
    s=R.uniform(.3,71.7); sign=R.choice([-1,1]); t=sign*(edge(s,sign)+R.uniform(.1,1.25))
    if abs(s-channel(t))<4.8 or noise(s,t,2)<-.25: continue
    place(R.choice(grasses),s,t,R.uniform(.32,.85))
for s in [5,12.5,20,53,62,68]:
    for _ in range(4): place(R.choice(grasses),s+R.uniform(-.3,.3),R.uniform(-.2,.2),R.uniform(.22,.4))
for _ in range(240):
    t=R.uniform(-29,29); s=channel(t)+R.choice([-1,1])*R.uniform(2.8,5.2)
    if abs(t)<2.1: continue
    place(R.choice(prototypes[6:9]),s,t,R.uniform(.12,.46),True)
# Leave the central 3 m of the ford open; the edge boulders give the crossing a readable width.
for s,t,sc in [(40.5,-2.7,.65),(45.4,2.8,.6),(42.1,3.7,.82),(44.6,-3.8,.58)]:
    place(prototypes[6],s,t,sc,True)
for _ in range(1000):
    s=R.uniform(.2,71.8); t=R.choice([-1,1])*R.uniform(3,30)
    if abs(s-channel(t))<4.8: continue
    # Cluster vegetation rather than spacing it at a constant density.
    if R.random()>(.62+.32*math.sin(s*.5+t*.43)): continue
    place(R.choice(grasses),s,t,R.uniform(.65,1.5))
for s in [39,47.7]:
    for t in [-3.2,3.2]: place(post,s,t,1,True)

# Close the far end beneath the overlapping backdrop rather than leaving a sky gap.
ob=grid('SM_RF_FarGround',72,95,[-32+i for i in range(65)],46,bankmat)
assets.append(ob); static.append(ob); physical[ob.name]=None
# Smooth distant landform beyond the small playable art patch.
verts=[]; faces=[]; colors=[]
for i in range(13):
    x=88+i*6
    for j in range(25):
        y=-110+j*9
        z=-2+(i/12)*18+12*math.sin(j*.59+i*.17)**2*math.sin(min(1,i/4)*math.pi/2)
        R.random()  # Preserve subsequent dressing's deterministic random sequence.
        verts.append((x,y,z)); k=.90+.10*noise(x,y,25); colors.append((k,k,k,1))
for i in range(12):
    for j in range(24):
        a=i*25+j; faces.extend([(a,a+25,a+1),(a+1,a+25,a+26)])
ob=mesh('SM_RF_BackdropRidge',verts,faces,hillmat,colors,smooth=True)
assets.append(ob); static.append(ob); physical[ob.name]=None
# Add the vegetation last so the approved ground, palette and existing dressing
# retain their exact deterministic values.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from riverbank_vegetation_v2 import build as build_vegetation
vegetation,collisions=build_vegetation(mesh,simple)
prototypes+=vegetation
for index,s,t,scale in [(0,38,-7.5,1),(1,47,7,.95),(0,47.7,16,.86),(1,38,-19,1.1),(1,48,-12,1.05),(0,38,23,.8)]:
    place(vegetation[index],s,t,scale,True)
vr=random.Random(940)
for _ in range(62):
    t=vr.choice([-1,1])*vr.uniform(5.2,27)
    s=channel(t)+vr.choice([-1,1])*vr.uniform(4.8,8)
    place(vegetation[vr.choice([2,3])],s,t,vr.uniform(.75,1.3))
from grass_coverage import build as build_grass
grass_assets,grass_placements=build_grass(mesh,simple,center,channel,edge,h,noise,scene)
prototypes+=grass_assets; placements+=grass_placements
assets+=prototypes
for ob in prototypes: ob.hide_render=True; ob.hide_set(True)

def camera(name,loc,target,lens):
    bpy.ops.object.camera_add(location=loc); ob=bpy.context.object; ob.name=name
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler(); ob.data.lens=lens
    ob.data.clip_end=1000; return ob
cams=[camera('Ford_driver_view',(30,center(30)-.4,h(30,0)+1.35),(47,center(47),.8),28),
      camera('Ford_overview',(21,-28,23),(43,0,.7),39),
      camera('Mud_approach_detail',(28,-4.2,3.4),(36,0,.5),42)]
cams.append(camera('Dry_road_driver_view',(7,center(7)-.4,h(7,0)+1.35),(25,center(25),.8),28))
cams.append(camera('Road_verge_detail',(13,-4.6,3.9),(18,center(18),.7),39))
bpy.ops.object.light_add(type='SUN',location=(10,-20,30))
sun=bpy.context.object; sun.rotation_euler=(.4,-.55,-.7); sun.data.energy=2.5; sun.data.angle=.12
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.42,.52,.70,1); bg.inputs['Strength'].default_value=.5
# Camera sky is independent of ambient fill so blue sky doesn't wash out surfaces.
world_nodes=scene.world.node_tree.nodes; world_links=scene.world.node_tree.links
sky=world_nodes.new('ShaderNodeBackground'); sky.inputs['Color'].default_value=(.10,.28,.58,1); sky.inputs['Strength'].default_value=.8
path=world_nodes.new('ShaderNodeLightPath'); mix=world_nodes.new('ShaderNodeMixShader')
world_links.new(path.outputs['Is Camera Ray'],mix.inputs[0])
world_links.new(bg.outputs[0],mix.inputs[1]); world_links.new(sky.outputs[0],mix.inputs[2])
world_links.new(mix.outputs[0],next(n for n in world_nodes if n.type=='OUTPUT_WORLD').inputs[0])
scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.render.resolution_x=1440; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'; scene.view_settings.exposure=0
looks=[v.identifier for v in scene.view_settings.bl_rna.properties['look'].enum_items]
for look in looks:
    if 'Medium High Contrast' in look: scene.view_settings.look=look; break
scene.render.image_settings.file_format='PNG'; scene.camera=cams[0]
for im in bpy.data.images:
    if im.source=='FILE': im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RoadFordStyle.blend'))
exports=[]
scene.unit_settings.scale_length=.01
for ob in assets:
    bpy.ops.object.select_all(action='DESELECT'); ob.hide_set(False); ob.select_set(True)
    bpy.context.view_layer.objects.active=ob
    original=ob.data; copied=original.copy(); ob.data=copied
    for v in copied.vertices: v.co*=100
    hull_copies=[]
    for hull in collisions.get(ob.name,[]):
        hull.hide_set(False); hull.select_set(True)
        source=hull.data; scaled=source.copy(); hull.data=scaled
        for vertex in scaled.vertices: vertex.co*=100
        hull_copies.append((hull,source,scaled))
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
    ob.data=original; bpy.data.meshes.remove(copied)
    for hull,source,scaled in hull_copies:
        hull.data=source; bpy.data.meshes.remove(scaled); hull.hide_set(True)
    exports.append(dict(name=ob.name,triangles=sum(len(p.vertices)-2 for p in original.polygons),materials=[m.name for m in original.materials],static=ob in static,physical=physical.get(ob.name),collision_hulls=len(collisions.get(ob.name,[]))))
    if ob in prototypes: ob.hide_set(True)
scene.unit_settings.scale_length=1
manifest=dict(revision='meadow-variety-04',vertex_color_encoding='LINEAR',seed=2909,length_m=72,width_m=64,assets=exports,placements=placements,materials=specs,water='STATIC ART PREVIEW',mud='STATIC ART PREVIEW')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
for cam in cams:
    scene.camera=cam; scene.render.filepath=str(OUT/(cam.name+'.png')); bpy.ops.render.render(write_still=True)

# A separate reusable library and neutral asset-review scene, at real metre scale.
review=bpy.data.scenes.new('Riverbank Vegetation Review')
review.world=bpy.data.worlds.new('Vegetation Review World'); review.world.use_nodes=True
review_bg=next(n for n in review.world.node_tree.nodes if n.type=='BACKGROUND')
review_bg.inputs['Color'].default_value=(.40,.45,.55,1); review_bg.inputs['Strength'].default_value=.35
review.unit_settings.system='METRIC'; review.unit_settings.scale_length=1
for ob,x,y in zip(vegetation,[-5,4.4,-1.4,2],[0,0,-3,-3]):
    display=bpy.data.objects.new(ob.name,ob.data); review.collection.objects.link(display)
    display.location=(x,y,-.10 if 'Scrub' in ob.name else 0)
for hulls in collisions.values():
    for hull in hulls: review.collection.objects.link(hull)
me=bpy.data.meshes.new('ReviewFloor'); me.from_pydata([(-18,-14,-.13),(18,-14,-.13),(18,14,-.13),(-18,14,-.13)],[],[(0,1,2,3)])
floor=bpy.data.objects.new('ReviewFloor',me); review.collection.objects.link(floor)
fm=bpy.data.materials.new('ReviewFloor'); fm.diffuse_color=(.18,.19,.17,1); fm.use_nodes=True
next(n for n in fm.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.18,.19,.17,1)
me.materials.append(fm)
for name,loc,energy,size in [('Key',(-6,-7,12),2700,8),('Fill',(7,-3,7),1000,7),('Rim',(0,5,11),1800,7)]:
    lightdata=bpy.data.lights.new(name,'AREA'); lamp=bpy.data.objects.new(name,lightdata); review.collection.objects.link(lamp)
    lamp.location=loc; lamp.rotation_euler=(Vector((0,0,3))-lamp.location).to_track_quat('-Z','Y').to_euler()
    lightdata.energy=energy; lightdata.shape='DISK'; lightdata.size=size
data=bpy.data.cameras.new('AssetReview'); view=bpy.data.objects.new('AssetReview',data); review.collection.objects.link(view)
view.location=(11,-23,10); view.rotation_euler=(Vector((0,0,3))-view.location).to_track_quat('-Z','Y').to_euler(); data.lens=46
review.camera=view; review.render.engine='CYCLES'; review.cycles.samples=32
review.render.resolution_x=1600; review.render.resolution_y=1000; review.render.resolution_percentage=100
review.view_settings.view_transform=scene.view_settings.view_transform; review.view_settings.look=scene.view_settings.look
review.view_settings.exposure=scene.view_settings.exposure
review.render.image_settings.file_format='PNG'; review.render.filepath=str(OUT/'Riverbank_asset_review.png')
bpy.data.libraries.write(str(OUT/'RiverbankVegetation.blend'),{review,*vegetation,*[h for group in collisions.values() for h in group]})
bpy.ops.render.render(write_still=True,scene=review.name)
print('ROAD_FORD_STYLE_OK '+json.dumps(dict(assets=len(exports),instances=len(placements),triangles=sum(e['triangles'] for e in exports))))
