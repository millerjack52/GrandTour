"""Blender-only shape/palette study. Leaves the rendering benchmark untouched."""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
rev=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else '07'
OUT=ROOT/'Art/Export/TussockStyleStudy'/rev
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.device='CPU'
scene.render.threads_mode='FIXED'; scene.render.threads=4
scene.cycles.samples=32; scene.cycles.use_denoising=True
scene.render.resolution_x=1500; scene.render.resolution_y=1050; scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Cool daylight'); scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.42,.53,.65,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.65
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=0

def material(name,color=None,leaf=False):
    m=bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; n.clear(); link=m.node_tree.links
    out=n.new('ShaderNodeOutputMaterial'); d=n.new('ShaderNodeBsdfDiffuse'); d.inputs['Roughness'].default_value=.85
    if color: d.inputs['Color'].default_value=(*color,1)
    else:
        vc=n.new('ShaderNodeVertexColor'); vc.layer_name='Color'; link.new(vc.outputs['Color'],d.inputs['Color'])
    if leaf:
        tr=n.new('ShaderNodeBsdfTranslucent'); link.new(vc.outputs['Color'],tr.inputs['Color'])
        mix=n.new('ShaderNodeMixShader'); mix.inputs[0].default_value=.45
        link.new(d.outputs[0],mix.inputs[1]); link.new(tr.outputs[0],mix.inputs[2]); link.new(mix.outputs[0],out.inputs[0])
    else: link.new(d.outputs[0],out.inputs[0])
    return m

foliage=material('Dry tussock - painted vertex palette',leaf=True)
soilmat=material('Umber soil and grey gravel')
# Linear RGB, deliberately separate straw, tobacco, weathered grey and subdued olive.
palettes=[[(.32,.205,.095),(.27,.165,.080),(.39,.285,.15),(.30,.21,.12)],
          [(.22,.12,.070),(.31,.175,.09),(.255,.14,.075),(.28,.16,.105)],
          [(.21,.19,.14),(.27,.24,.18),(.17,.155,.12),(.24,.21,.16)],
          [(.125,.125,.084),(.19,.16,.105),(.215,.18,.115),(.145,.12,.087)]]

def mix(a,b,t):return tuple(x*(1-t)+y*t for x,y in zip(a,b))
def mesh(name,verts,faces,colors,mat):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob); me.materials.append(mat)
    attr=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for p in me.polygons:
        p.use_smooth=True
        for li in p.loop_indices: attr.data[li].color=(*colors[me.loops[li].vertex_index],1)
    return ob

prototypes=[]; counts=[]
for kind in range(4):
    rng=random.Random(7091+kind*113)
    verts=[]; faces=[]; cols=[]
    count=190 if kind<3 else 75
    lobes=[(rng.uniform(-.13,.13),rng.uniform(-.13,.13),rng.uniform(.72,1.18),rng.uniform(0,math.tau)) for _ in range(5)]
    for b in range(count):
        lx,ly,strength,lean=lobes[b%5]
        ang=rng.uniform(0,math.tau); d=Vector((math.cos(ang),math.sin(ang),0))
        side=Vector((-d.y,d.x,0)); r=rng.uniform(.04,.25) if kind<3 else rng.uniform(.01,.16)
        root=Vector((lx+d.x*r,ly+d.y*r,-.015))
        upright=b%4==0 if kind==2 else b%13==0
        height=rng.uniform(.62,1.05)*strength*[.85,.48,1.10,.24][kind]
        reach=rng.uniform(.43,.76)*[1.10,1.4,.90,.52][kind]
        tip=rng.uniform(.035,.15)
        if upright: reach*=.62; tip=height*rng.uniform(.48,.68)
        if kind==3:tip=rng.uniform(.09,.24)
        wind=Vector((.36 if kind==1 else .025,-.22 if kind==1 else .015,0))
        p0=root
        p1=root+d*(reach*rng.uniform(.18,.30))+Vector((0,0,height*.48))
        p2=root+d*(reach*.64)+Vector((0,0,height))+wind
        p3=root+d*reach+Vector((0,0,tip))+wind*1.6
        width=rng.uniform(.007,.015)*(1 if kind<3 else .40)
        if b%8==0: width*=.35
        tone=palettes[kind][(b%5)%4]
        variation=rng.uniform(.90,1.08); tone=tuple(c*variation for c in tone)
        base=mix(tone,(.075,.060,.045),.40)
        n=len(verts); steps=7 if kind<3 else 4
        for j in range(steps+1):
            t=j/steps; pos=p0*(1-t)**3+p1*(3*t*(1-t)**2)+p2*(3*t*t*(1-t))+p3*t**3
            taper=(.45+.55*math.sin(math.pi*t))*(1-t**3)
            w=width*max(.015,taper)
            # Broad, restrained colour changes along the leaf; no luminous tip outlines.
            color=mix(base,tone,min(1,t*2))
            for sign in [-1,1]: verts.append(tuple(pos+side*w*sign)); cols.append(color)
        for j in range(steps):
            a=n+j*2; faces.extend([(a,a+3,a+1),(a,a+2,a+3)])
    ob=mesh(['Arching','Wind-combed','Upright','Fine undergrass'][kind],verts,faces,cols,foliage)
    # Artist normals favour the crown's volume over alternating ribbon faces.
    normals=[Vector((v[0]*.48,v[1]*.48,.80)).normalized() for v in verts]
    ob.data.normals_split_custom_set_from_vertices(normals)
    ob.hide_render=True; prototypes.append(ob)
    counts.append(dict(name=ob.name,triangles=len(faces),blades=count))
    print('STYLE_MODEL '+ob.name,flush=True)

def instance(proto,name,pos,scale=1,angle=0):
    ob=bpy.data.objects.new(name,proto.data); scene.collection.objects.link(ob)
    ob.location=pos; ob.rotation_euler[2]=angle; ob.scale=(scale,scale,scale)
    if proto.data.materials and proto.data.materials[0]==foliage: ob.visible_shadow=False
    return ob

def height(x,y):return .10*math.sin(x*.7)+.09*math.sin(y*.8)+.16*max(0,abs(y)-1.2)
def road(x):return .22*math.sin(x*.42)
rng=random.Random(9012)
verts=[]; faces=[]; cols=[]; nx=140; ny=90
for ix in range(nx+1):
    x=-9+ix*18/nx
    for iy in range(ny+1):
        y=-5+iy*10/ny; verts.append((x,y,height(x,y)))
        shoulder=abs(y-road(x)); grit=rng.uniform(.92,1.08)
        if shoulder<1.04+.08*math.sin(x*2+y*4):
            track=math.exp(-((shoulder-.55)/.24)**2)
            c=mix((.16,.165,.15),(.265,.245,.195),track)
        else:
            c=mix((.085,.084,.058),(.15,.14,.095),.5+.5*math.sin(x*.8+y*1.6))
        cols.append(tuple(v*grit for v in c))
for ix in range(nx):
    for iy in range(ny):
        a=ix*(ny+1)+iy; faces.append((a,a+ny+1,a+ny+2,a+1))
ground=mesh('Roadside study ground',verts,faces,cols,soilmat)
print('STYLE_GROUND_READY',flush=True)
patch=[]
# Irregular clustered planting, with taller crowns gathered behind the short verge.
for ix in range(29):
    for iy in range(17):
        x=-8.7+(ix+rng.random()*.8)*.60; y=-4.8+(iy+rng.random()*.8)*.56
        shoulder=abs(y-road(x))
        if shoulder<1.18 or rng.random()<.07:continue
        grouping=math.sin(x*.75+y*.35)+math.sin(y*.85-x*.2)+rng.uniform(-.55,.55)
        k=2 if rng.random()<.13 else (0 if grouping>-.1 else 1)
        scale=rng.uniform(.57,.95)*( .74 if shoulder<1.8 else 1)
        patch.append(instance(prototypes[k],'Patch crown',(x,y,height(x,y)),scale,rng.random()*math.tau))
for _ in range(950):
    x=rng.uniform(-8.8,8.8); y=rng.uniform(-4.8,4.8)
    if abs(y-road(x))<1.06:continue
    patch.append(instance(prototypes[3],'Fine grass',(x,y,height(x,y)),rng.uniform(.6,1.15),rng.random()*math.tau))
stones=[]
print('STYLE_PLANTING_READY '+str(len(patch)),flush=True)
stone_mats=[material('Slate '+str(i),c) for i,c in enumerate([(.15,.175,.18),(.25,.26,.235),(.20,.18,.15)])]
stone_sources=[]
for sm in stone_mats:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1)
    source=bpy.context.object; source.data.materials.append(sm); source.hide_render=True; stone_sources.append(source)
for _ in range(200):
    x=rng.uniform(-8.7,8.7); y=road(x)+rng.uniform(-1.45,1.45)
    ob=instance(rng.choice(stone_sources),'Road gravel',(x,y,height(x,y)+.012))
    s=rng.uniform(.014,.058); ob.scale=(s*1.6,s,s*.65); stones.append(ob)

bpy.ops.object.light_add(type='AREA',location=(-3,-4,8)); key=bpy.context.object
key.name='Large soft daylight'; key.data.energy=1400; key.data.shape='DISK'; key.data.size=6
key.rotation_euler=(Vector((0,0,0))-key.location).to_track_quat('-Z','Y').to_euler()
def camera(name,pos,target,lens=48):
    bpy.ops.object.camera_add(location=pos); cam=bpy.context.object; cam.name=name
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=lens
    scene.camera=cam; return cam
cam=camera('Roadside shape study',(8,-7,4.0),(0,0,.35),46)
scene.render.filepath=str(OUT/'Roadside.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TussockStyleStudy.blend'))
if 'shapes-only' not in sys.argv:bpy.ops.render.render(write_still=True)
# Separate neutral lineup exposes the actual crown shapes, without ground clutter.
for ob in patch+stones+[ground]: ob.hide_render=True
lineup=[]
for kind in range(4):lineup.append(instance(prototypes[kind],'Lineup '+str(kind),(-2.6+kind*1.75,0,0)))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025)); plane=bpy.context.object
plane.data.materials.append(material('Neutral warm slate',(.19,.205,.20)))
cam=camera('Shape lineup',(0,-9,4.2),(0,0,.3),48)
cam.data.type='ORTHO'; cam.data.ortho_scale=7.8
scene.render.resolution_y=800
labelmat=material('Study lettering',(.065,.080,.085))
for kind,label in enumerate(['ARCHING STRAW','WIND-COMBED RUST','TALL WEATHERED','FINE UNDERGRASS']):
    curve=bpy.data.curves.new(label,'FONT'); curve.body=label; curve.align_x='CENTER'; curve.size=.11
    ob=bpy.data.objects.new(label,curve); scene.collection.objects.link(ob)
    ob.location=(-2.6+kind*1.75,-1,.025); ob.data.materials.append(labelmat)
    for i,c in enumerate(palettes[kind]):
        bpy.ops.mesh.primitive_plane_add(size=1,location=(-2.98+kind*1.75+i*.24,-1.34,.01))
        swatch=bpy.context.object; swatch.scale=(.19,.14,1); swatch.data.materials.append(material('Palette '+str(kind)+' '+str(i),c))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TussockShapes.blend'))
scene.render.filepath=str(OUT/'Shapes.png'); bpy.ops.render.render(write_still=True)
(OUT/'manifest.json').write_text(json.dumps(dict(revision=rev,models=counts,patch_instances=len(patch),status='Blender art study; not imported or performance tested'),indent=2))
print('TUSSOCK_STYLE_STUDY_SAVED '+str(OUT))
