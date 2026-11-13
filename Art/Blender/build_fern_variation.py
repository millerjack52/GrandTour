"""Sixteen isolated fern candidates and CPU patch review; no live asset mutation."""
import bpy, hashlib, json, math, random, sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import build_fern_revision as R
L=R.L
OUT=R.OUT/'Variation';OUT.mkdir(parents=True,exist_ok=True)
FORMS=['Cascade','Fine','Crevice','Crown']


def design(kind,variant):
    rng=random.Random(96023+kind*977+variant*191)
    count=([10,11,9,10],[9,10,8,9],[7,9,8,7],[11,10,9,12])[kind][variant]
    lengths=[(1.35,2.2),(1.15,1.85),(.45,.95),(.85,1.6)][kind]
    pairs=[23,15,19,21][kind]
    palette=[(.075,.18,.078),(.07,.165,.095),(.11,.19,.065),(.08,.18,.065)]
    plant_tint=rng.uniform(.88,1.10)
    fs=[]
    for i in range(count):
        young=i>=count-3
        old=(i==1 and variant in (1,3))
        # Different crown architectures, not just randomly rotated copies.
        az=rng.uniform(-1.5,1.5) if kind in (0,2) else rng.uniform(-2.6,2.6)
        length=rng.uniform(*lengths)*([.9,1.05,.82,1.1][variant])
        el=rng.uniform(.65,1.15);droop=rng.uniform(2.05,2.8)
        if kind==1:el=rng.uniform(.55,.95);droop=rng.uniform(1.2,2.05)
        if kind==3:el=rng.uniform(1.0,1.42);droop=rng.uniform(1.3,2.0)
        if young:length*=rng.uniform(.55,.8);el=rng.uniform(1.25,1.5);droop=rng.uniform(.35,.85)
        if old:el-=.2;droop+=.25
        colour=palette[kind]
        if young:colour=L.mix(colour,(.17,.245,.075),.42)
        if old:colour=L.mix(colour,(.19,.11,.045),.65)
        colour=tuple(c*plant_tint*rng.uniform(.96,1.04) for c in colour)
        fs.append(dict(az=az,length=length,el=el,droop=droop,colour=colour,
                       width=rng.uniform(.17,.24)*([1,1.15,.58,.82][kind]),
                       curl=rng.uniform(-.21,.21),roll=rng.uniform(-.8,.8),
                       seed=rng.randrange(999999),phase=rng.uniform(0,math.tau),
                       pairs=pairs+rng.randrange(-2,2),fine=kind==1,old=old,
                       anchor=[rng.uniform(-.035,.035),rng.uniform(-.035,.035),rng.uniform(.03,.10)]))
    return fs


def divided(g,a,d,cross,up,length,colour,phase,lod):
    # Actual secondary divisions: small leaves branch off each primary pinna.
    R.pinna(g,a,d,cross,up,length,length*.018,colour,phase,1)
    for k in range(5):
        u=.15+k*.16
        if lod==2 and k%2:continue
        q=a+d*length*u+up*length*.035*math.sin(u*math.pi)
        for sign in (-1,1):
            dd=(cross*sign+d*.38).normalized()
            ln=length*.36*math.sin(math.pi*(u+.05))**.6
            R.pinna(g,q,dd,d,up,ln,ln*.26,colour,phase+k,1)


def build(fs,lod):
    g=L.Geo();skeleton=[]
    L.tube(g,[(0,0,-.14),(.01,0,-.01),(.02,0,.065)],[.065,.048,.023],6,(.08,.06,.025),mi=0)
    for f in fs:
        direction=Vector((math.cos(f['az'])*math.cos(f['el']),math.sin(f['az'])*math.cos(f['el']),math.sin(f['el'])))
        pts,tans,sides,ups=L.frond_path(Vector(f['anchor']),direction,f['length'],f['droop'],16,1.25,f['curl'],f['roll'])
        skeleton.append([list(p) for p in pts])
        L.tube(g,pts[::2],[.0045*(1-j/11) for j in range(9)],3,(.085,.11,.035),mi=1)
        rng=random.Random(f['seed']);pairs=f['pairs']
        for j in range(pairs):
            jitter=rng.uniform(-.22,.22);scale=rng.uniform(.9,1.08)
            for sign in (-1,1):
                asym=rng.uniform(.87,1.08);twist=rng.uniform(-.22,.22)
                nick=rng.random()<(.07 if f['old'] else .012)
                if nick:continue
                if lod==1 and j%4==1:continue
                if lod==2 and j%2:continue
                t=.14+.82*(j+.5+jitter+(.23 if sign<0 else 0))/pairs
                seg=min(15,int(t*16));v=t*16-seg
                a=pts[seg].lerp(pts[seg+1],v);T=tans[seg].lerp(tans[seg+1],v).normalized()
                S=sides[seg];U=ups[seg]
                length=f['width']*math.sin(math.pi*(t-.05)/.95)**.8*scale*asym
                d=(S*sign+T*(.22+.2*t)+U*twist).normalized()
                cross=(T-d*T.dot(d)).normalized()
                width=min(f['length']*.82/pairs*.65*(1-.35*t),length*.17)
                if lod:width*=1.18 if lod==1 else 1.6
                col=tuple(c*(.94+.08*math.sin(t*4+f['phase'])) for c in f['colour'])
                if f['old'] and t>.7:col=L.mix(col,(.17,.105,.04),(t-.7)*.75)
                if f['fine']:divided(g,a,d,cross,U,length,col,f['phase'],lod)
                else:R.pinna(g,a,d,cross,U,length,width,col,f['phase'],lod)
    # Keep the established radial wind convention and a fixed root region.
    g.a=[max(0.,min(1.,(math.hypot(v.x,v.y)-.12)/1.2)) for v in g.v]
    return g,skeleton


def camera(scene,position,target,scale):
    c=scene.camera;c.location=position
    c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler()
    c.data.ortho_scale=scale


def render(scene,name):
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)


def support_height(x,y):
    return -.45*x-.13+.035*math.sin(x*2)+.025*math.cos(y*1.7)


def main():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mats=L.plant_materials();mats[1]=R.material()
    # Older brown pigments are rougher; all variants share this texture-free graph.
    nodes=mats[1].node_tree.nodes;links=mats[1].node_tree.links
    colour=next(n for n in nodes if n.type=='VERTEX_COLOR')
    p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    split=nodes.new('ShaderNodeSeparateColor');links.new(colour.outputs['Color'],split.inputs['Color'])
    age=nodes.new('ShaderNodeMath');age.operation='SUBTRACT'
    links.new(split.outputs['Red'],age.inputs[0]);links.new(split.outputs['Green'],age.inputs[1])
    rough=nodes.new('ShaderNodeMapRange');rough.clamp=True
    rough.inputs['From Min'].default_value=-.11;rough.inputs['From Max'].default_value=.05
    rough.inputs['To Min'].default_value=.65;rough.inputs['To Max'].default_value=.84
    links.new(age.outputs[0],rough.inputs['Value']);links.new(rough.outputs['Result'],p.inputs['Roughness'])
    originals=R.old_definitions();records=[];display=[]
    for kind,form in enumerate(FORMS):
        for variant in range(4):
            fs=design(kind,variant);counts=[];hashes=[];bounds=[]
            assert fs==design(kind,variant),'Non-deterministic design'
            for lod in range(3):
                g,sk=build(fs,lod)
                ob,dropped=L.to_object(g,f'SM_FernVar_{form}_{variant}_LOD{lod}',mats,[0,1])
                for p in ob.data.polygons:p.use_smooth=True
                assert dropped==0,(ob.name,dropped)
                ob.data.calc_loop_triangles();counts.append(len(ob.data.loop_triangles))
                hashes.append(hashlib.sha256(json.dumps(sk).encode()).hexdigest())
                bounds.append([[min(v[i] for v in g.v),max(v[i] for v in g.v)] for i in range(3)])
                L.export(ob,out=OUT);ob.hide_render=True
                if lod==0:display.append(ob)
            oldg,_=originals['build'](originals['design'](kind,variant%3),kind,0)
            # Original buffer has triangles and quads.
            original=sum(len(face)-2 for face in oldg.f)
            assert counts[0]<=original,(form,variant,counts,original)
            assert counts[0]>counts[1]>counts[2]
            assert len(set(hashes))==1
            records.append(dict(form=form,variant=variant,fronds=len(fs),triangles=counts,
                                original_lod0_triangles=original,skeleton_sha256=hashes[0],
                                bounds_m=bounds,design=fs,dropped_faces=0))
    assert len({r['skeleton_sha256'] for r in records})==16
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.cycles.max_bounces=4;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.world.use_nodes=True;bg=scene.world.node_tree.nodes['Background']
    bg.inputs[0].default_value=(.23,.27,.30,1);bg.inputs[1].default_value=.6
    bpy.ops.object.light_add(type='AREA',location=(0,-4,10));key=bpy.context.object;key.data.energy=2200;key.data.size=9
    bpy.ops.object.light_add(type='AREA',location=(1,6,6));fill=bpy.context.object;fill.data.energy=1600;fill.data.size=8
    bpy.ops.object.camera_add();scene.camera=bpy.context.object;scene.camera.data.type='ORTHO'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    (OUT/'manifest.json').write_text(json.dumps(dict(status='Isolated candidate; Unreal visual and performance validation pending',
        forms=FORMS,variants=records,shared_materials=2,alpha_cards=False,
        checks='16 unique deterministic skeletons; skeleton stable across LODs; decreasing triangles; no degenerate faces; each LOD0 within original form budget',
        source='Art/Blender/build_fern_variation.py',reference='Owner Waimeamea photos 04/08',
        review='CPU Blender preview, not game capture',live_assets_changed=False),indent=2))
    camera(scene,(5,-8,5),(0,0,0),13.5)
    rotation=scene.camera.rotation_euler.to_quaternion()
    right=rotation@Vector((1,0,0));up=rotation@Vector((0,1,0))
    labels=[]
    for i,ob in enumerate(display):
        centre=right*((i%4-1.5)*3.2)+up*((1.5-i//4)*2.4)
        ob.location=centre;ob.hide_render=False
        bpy.ops.object.text_add(location=centre-up*1.12)
        label=bpy.context.object;label.name='Review_label_'+str(i)
        label.data.body=FORMS[i//4]+' '+str(i%4+1);label.data.align_x='CENTER';label.data.size=.17
        label.rotation_euler=scene.camera.rotation_euler;labels.append(label)
    scene.render.resolution_x=1800;scene.render.resolution_y=1500
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'fern-variation-library.blend'))
    render(scene,'variation-library')
    for label in labels:label.hide_render=True
    for ob in display:ob.hide_render=True;ob.location=(0,0,0)
    # Uneven colony sizes and uncovered pockets, not equal species proportions.
    patch=[(0,(-1.3,.5,.08),-.2,1),(2,(.1,.65,.17),.35,.9),(1,(1.45,1.1,.2),.7,.86),
           (3,(-.4,1.9,.2),-.5,.93),(12,(-1.5,2.8,.12),.1,.9),(13,(.7,2.9,.15),-.3,1),
           (4,(2.25,2.4,.12),-.5,.9),(6,(-2.65,1.9,.12),.2,.9),
           (8,(-2.4,-.35,.02),.2,.9),(10,(1.8,-.1,.02),.5,1),
           (9,(2.9,.9,.02),-.5,.8)]
    patch_records=[]
    for idx,pos,angle,scale in patch:
        x,y=pos[0]*.8,pos[1]*.8
        grounded=(x,y,support_height(x,y)-.04*scale)
        ob=display[idx];ob.location=grounded;ob.rotation_euler.z=angle;ob.scale=(scale,)*3;ob.hide_render=False
        patch_records.append(dict(asset=ob.name,position=grounded,rotation_z=angle,scale=scale))
    # Neutral sloping support: bury root collars and let outer fronds hang downhill.
    # This is a constructed asset study, not the surveyed bank or a placement test.
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=100,y_subdivisions=100,size=30,location=(0,0,0))
    ground=bpy.context.object;ground.name='Preview_ground_only'
    for v in ground.data.vertices:v.co.z=support_height(v.co.x,v.co.y)
    ground.data.materials.append(L.material('Preview_damp_earth',(.05,.045,.028),vertex=False))
    # Keep a quiet floor and light contact cues so silhouette issues remain visible.
    key.location=(0,-3,7);key.data.energy=1050;key.data.size=6
    fill.location=(1,5,5);fill.data.energy=850;fill.data.size=5
    camera(scene,(7,-10,7),(0,.9,.15),7.6)
    scene.render.resolution_x=1600;scene.render.resolution_y=1200
    (OUT/'patch-layout.json').write_text(json.dumps(patch_records,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'fern-variation-patch.blend'))
    render(scene,'variation-patch')
    print('FERN_VARIATION_COMPLETE',len(records),flush=True)


if __name__=='__main__':main()
