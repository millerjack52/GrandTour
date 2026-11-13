"""Deterministic, texture-free Grand Tour shrub kit. Run with Blender --background --python."""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/ShrubLibrary/v01'
OUT.mkdir(parents=True, exist_ok=True)
RENDER_ONLY = '--render-only' in sys.argv
SPECS = [
    dict(key='SageCushion', label='SAGE CUSHION', height=.55, width=1.25, stems=8, nodes=7, leaf=.095, broad=.42, lift=.22, color=(.23,.31,.19)),
    dict(key='Broadleaf', label='BROADLEAF BUSH', height=1.15, width=1.5, stems=7, nodes=8, leaf=.145, broad=.48, lift=.64, color=(.115,.235,.085)),
    dict(key='RiverLance', label='RIVER SCRUB', height=1.9, width=1.4, stems=7, nodes=8, leaf=.16, broad=.15, lift=.8, color=(.25,.32,.115)),
    dict(key='GoldenBloom', label='GOLDEN FLOWER', height=.95, width=1.35, stems=8, nodes=7, leaf=.09, broad=.20, lift=.55, color=(.16,.24,.075), flower=True),
    dict(key='RustThicket', label='RUST THICKET', height=1.35, width=1.7, stems=7, nodes=8, leaf=.12, broad=.36, lift=.56, color=(.36,.19,.065)),
    dict(key='DryScrub', label='DRY SCRUB', height=1.05, width=1.3, stems=7, nodes=7, leaf=.07, broad=.17, lift=.62, color=(.32,.29,.16), sparse=True),
]

def material(name, color, vertex=False):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.87; p.inputs['Specular IOR Level'].default_value=.19
    if vertex:
        v=m.node_tree.nodes.new('ShaderNodeVertexColor'); v.layer_name='Color'
        m.node_tree.links.new(v.outputs['Color'],p.inputs['Base Color'])
    return m

def build(spec, variant, lod, mat):
    rng=random.Random(15410+SPECS.index(spec)*327+variant*83)
    verts=[]; faces=[]; colors=[]; uvs=[]
    leaf_count=0; stem_count=0
    def add(vs, fs, color, uv):
        start=len(verts); verts.extend([tuple(v) for v in vs]); uvs.extend(uv)
        for f in fs: faces.append(tuple(start+i for i in f)); colors.append((*color,1))
    def tube(points, r0, r1, color, sides=5):
        nonlocal stem_count
        vs=[]; uv=[]; fs=[]
        for j,p in enumerate(points):
            d=(points[min(j+1,len(points)-1)]-points[max(0,j-1)]).normalized()
            axis=d.cross(Vector((0,1,.13))).normalized(); other=d.cross(axis).normalized()
            r=r0+(r1-r0)*j/(len(points)-1)
            for k in range(sides):
                a=k*math.tau/sides; vs.append(p+r*(axis*math.cos(a)+other*math.sin(a))); uv.append((k/sides,j/(len(points)-1)))
        for j in range(len(points)-1):
            for k in range(sides):
                a=j*sides+k; b=j*sides+(k+1)%sides
                fs.append((a,b,b+sides,a+sides))
        fs.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+k for k in range(sides))])
        add(vs,fs,color,uv); stem_count+=1
    def leaf(anchor, direction, size, color, broad):
        nonlocal leaf_count
        d=direction.normalized(); side=d.cross(Vector((.13,.21,1))).normalized(); n=side.cross(d).normalized()
        roll=rng.uniform(-.6,.6); side=side*math.cos(roll)+n*math.sin(roll); n=side.cross(d).normalized()
        w=size*broad
        vs=[anchor,anchor+d*size*.30-side*w*.8,anchor+d*size*.67-side*w,
            anchor+d*size+Vector((0,0,-size*.09)),anchor+d*size*.67+side*w,anchor+d*size*.30+side*w*.8,
            anchor+d*size*.49+n*size*.09]
        add(vs,[(i,(i+1)%6,6) for i in range(6)],color,[(0,.5),(.3,0),(.67,0),(1,.5),(.67,1),(.3,1),(.49,.5)])
        leaf_count+=1
    def flower(p, size, colour):
        # Solid petal silhouettes; no alpha cards, every flower terminates a twig.
        for k in range(5):
            a=math.tau*k/5; d=Vector((math.cos(a),math.sin(a),.24)); s=Vector((-d.y,d.x,0))*size*.40
            add([p,p+d*size*.65-s,p+d*size,p+d*size*.65+s],[(0,1,2),(0,2,3)],colour,[(.5,0),(0,.6),(.5,1),(1,.6)])
    h=spec['height']*(1 if variant==0 else .81); width=spec['width']*(1 if variant==0 else 1.12)
    bark=(.16,.115,.069) if not spec.get('sparse') else (.27,.225,.16)
    for s in range(spec['stems']):
        a=math.tau*s/spec['stems']+rng.uniform(-.28,.28)
        radial=Vector((math.cos(a),math.sin(a),0)); tangent=Vector((-radial.y,radial.x,0))
        reach=width*rng.uniform(.25,.48); top=h*rng.uniform(.73,1.03)
        if s==0: reach*=.25; top=h
        lean=Vector((.20*top,0,0)) if variant else Vector((0,0,0))
        base=radial*rng.uniform(.015,.075); base.z=-.055
        points=[]
        for j in range(6):
            t=j/5; points.append(base+radial*reach*(t**1.2)+lean*t*t+Vector((0,0,top*(t*(1.2-.2*t)))))
        tube(points,.020*h+.004,.0018,bark,5 if lod<2 else 4)
        for j in range(2,6):
            for side in [-1,1]:
                anchor=points[j-1].lerp(points[j],rng.uniform(.35,.95))
                direction=(radial*.40+tangent*side*.78+Vector((0,0,spec['lift']))).normalized()
                length=width*rng.uniform(.18,.30)*(1-.36*j/6)
                end=anchor+direction*length
                mid=anchor.lerp(end,.5)+Vector((0,0,.035))
                tube([anchor,mid,end],.0048*h,.0009,bark,4 if lod<2 else 3)
                for n in range(spec['nodes']):
                    t=(n+.5)/spec['nodes']; p=anchor.lerp(mid,t*2) if t<.5 else mid.lerp(end,(t-.5)*2)
                    shoot_side=1 if n%2 else -1
                    sd=(radial*.45+tangent*shoot_side*.55+Vector((0,0,rng.uniform(.15,.6)))).normalized()
                    sl=spec['leaf']*rng.uniform(1.2,2.0); tip=p+sd*sl
                    # RNG is consumed identically at each LOD, retaining exact branches and a distributed subset of foliage.
                    retain=(n%[1,2,3][lod]==0)
                    if retain: tube([p,tip],.0018,.00045,bark,3)
                    tint=rng.uniform(.78,1.15); colour=tuple(min(.8,c*tint) for c in spec['color'])
                    for q in range(3):
                        lp=p.lerp(tip,(q+1)/3)
                        for ls in [-1,1]:
                            ld=(sd*.55+tangent*ls*.8+Vector((0,0,rng.uniform(-.15,.40))))
                            size=spec['leaf']*rng.uniform(.72,1.10)*(1-.18*q)
                            keep=not spec.get('sparse') or rng.random()<.23
                            # Always consume leaf orientation randomness, including omitted LOD leaves.
                            if retain and keep: leaf(lp,ld,size*[1,1.30,1.53][lod],colour,spec['broad'])
                            else: rng.uniform(-.6,.6)
                    if spec.get('flower') and retain and n%2==0:
                        flower(tip,.028*[1,1.2,1.4][lod],(.78,.48,.055))
    name='SM_SH_'+spec['key']+'_'+('A' if variant==0 else 'B')+'_LOD'+str(lod)
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update(); mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='UVMap')
    mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    col=mesh.color_attributes['Color']; uv=mesh.uv_layers['UVMap']
    for poly,c in zip(mesh.polygons,colors):
        for li in poly.loop_indices: col.data[li].color=c; uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
    mesh.calc_loop_triangles()
    assert all((mesh.vertices[t.vertices[1]].co-mesh.vertices[t.vertices[0]].co).cross(mesh.vertices[t.vertices[2]].co-mesh.vertices[t.vertices[0]].co).length>1e-12 for t in mesh.loop_triangles)
    ob=bpy.data.objects.new(name,mesh); bpy.context.scene.collection.objects.link(ob)
    ob['kit']='Grand Tour Shrub Library v01'; ob['lod']=lod; ob['seed']=15410+SPECS.index(spec)*327+variant*83
    ob['placement']='Ground pivot; roots extend 5.5 cm below ground. No blocking collision.'
    if lod==0:
        ob.asset_mark(); ob.asset_data.description=spec['label']+' / '+('upright' if variant==0 else 'spreading')+' / opaque vertex-colour foliage'
        ob.asset_data.tags.new('Shrub'); ob.asset_data.tags.new('Grand Tour')
    row=dict(name=name,asset=name.rsplit('_LOD',1)[0],family=spec['key'],variant='AB'[variant],lod=lod,triangles=len(mesh.loop_triangles),leaves=leaf_count,branches=stem_count,size_m=[round(max(v[i] for v in verts)-min(v[i] for v in verts),4) for i in range(3)],ground_pivot=True)
    return ob,row

def export(ob):
    bpy.ops.object.select_all(action='DESELECT'); ob.hide_set(False); ob.select_set(True); bpy.context.view_layer.objects.active=ob
    bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.export_scene.gltf(filepath=str(OUT/(ob.name+'.glb')),export_format='GLB',use_selection=True,export_materials='EXPORT')
    # Match the project's proven centimetre FBX pipeline.
    for v in ob.data.vertices: v.co*=100
    bpy.context.scene.unit_settings.scale_length=.01
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
    for v in ob.data.vertices: v.co/=100
    bpy.context.scene.unit_settings.scale_length=1

def text_obj(body, location, size, mat):
    c=bpy.data.curves.new(body,'FONT'); c.body=body; c.size=size; c.align_x='CENTER'; c.extrude=0
    o=bpy.data.objects.new(body,c); bpy.context.scene.collection.objects.link(o); o.location=location; o.rotation_euler=(math.pi/4,0,0); c.materials.append(mat)
    return o

def review(objects):
    scene=bpy.data.scenes.new('Shrub Library Review'); bpy.context.window.scene=scene
    scene.render.engine='CYCLES'; scene.cycles.samples=24; scene.cycles.use_denoising=True
    scene.world=bpy.data.worlds.new('ReviewWorld'); scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.38,.44,1); scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
    scene.view_settings.view_transform='AgX'
    ground=material('Review | Chalk',(.19,.225,.21)); ink=material('Review | Ink',(.70,.78,.70)); muted=material('Review | Secondary',(.44,.53,.47))
    for m,c in [(ink,(.70,.78,.70,1)),(muted,(.44,.53,.47,1))]:
        p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Emission Color'].default_value=c; p.inputs['Emission Strength'].default_value=.8
    for i,original in enumerate([4,5,8,9,2,3,6,7,0,1,10,11]):
        ob=objects[original]
        col=i%4; row=i//4; x=(col-1.5)*3.05; y=(1-row)*3.6
        copy=bpy.data.objects.new(ob.name.replace('SM_SH_','Display_'),ob.data); scene.collection.objects.link(copy); copy.location=(x,y,0)
        spec=SPECS[original//2]; text_obj(spec['label']+' / '+'AB'[original%2],(x,y-1.23,.09),.145,ink)
        text_obj(f'{max(v.co.z for v in ob.data.vertices):.2f} m',(x,y-1.50,.09),.11,muted)
    text_obj('GRAND TOUR / SHRUB LIBRARY',(0,7.1,.1),.35,ink)
    text_obj('12 VARIANTS     /     MODELED FOLIAGE     /     THREE LODS',(0,6.65,.1),.15,muted)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.07)); bpy.context.object.data.materials.append(ground)
    for loc,energy,size in [((-5,-5,11),1900,8),((7,3,9),1400,7)]:
        bpy.ops.object.light_add(type='AREA',location=loc); light=bpy.context.object; light.data.energy=energy; light.data.shape='DISK'; light.data.size=size; light.rotation_euler=(Vector((0,0,0))-light.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(0,-18,17)); cam=bpy.context.object; cam.rotation_euler=(Vector((0,0,.3))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=13.6; scene.camera=cam
    scene.render.resolution_x=2000; scene.render.resolution_y=1700; scene.render.resolution_percentage=100
    scene.render.filepath=str(OUT/'Shrub_Library_Overview.png')
    return scene

if '--review-layout-only' in sys.argv:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'GrandTour_ShrubLibrary.blend'))
    bpy.data.scenes.remove(bpy.data.scenes['Shrub Library Review'])
    objects=[bpy.data.objects['SM_SH_'+s['key']+'_'+v+'_LOD0'] for s in SPECS for v in 'AB']
    scene=review(objects)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GrandTour_ShrubLibrary.blend'))
elif RENDER_ONLY:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'GrandTour_ShrubLibrary.blend'))
    scene=bpy.data.scenes['Shrub Library Review']; bpy.context.window.scene=scene
else:
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.scene.name='Shrub Assets - metres'
    mat=material('M_SH_VertexFoliage',(.2,.3,.1),True); mat.use_backface_culling=False
    objects=[]; rows=[]
    for spec in SPECS:
        for variant in range(2):
            for lod in range(3):
                ob,row=build(spec,variant,lod,mat); export(ob); rows.append(row)
                if lod==0:
                    objects.append(ob)
                    ob.location=((len(objects)-1)%4*3.05,(len(objects)-1)//4*3.6,0)
                ob.hide_set(lod>0); ob.hide_render=lod>0
    (OUT/'manifest.json').write_text(json.dumps(dict(version=1,units='metres; FBX centimetres',collision='none',textures='none; linear vertex Color',models=rows),indent=2))
    scene=review(objects)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GrandTour_ShrubLibrary.blend'))
    print('SHRUB_BUILD_OK',len(rows))
bpy.ops.render.render(write_still=True)
# A second angle checks exposed stems and foliage from driver height.
scene.camera.location=(9,-17,9); scene.camera.rotation_euler=(Vector((0,0,.65))-scene.camera.location).to_track_quat('-Z','Y').to_euler(); scene.camera.data.ortho_scale=15.8
scene.render.filepath=str(OUT/'Shrub_Library_Angle.png'); bpy.ops.render.render(write_still=True)
print('SHRUB_REVIEW_OK')
