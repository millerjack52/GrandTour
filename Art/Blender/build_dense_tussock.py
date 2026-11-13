"""Isolated dense foliage experiment. Never saves over RoadFordStyle.blend."""
import bpy, math, random, json, ast
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/DenseTussock'; OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Art/Export/RoadFordStyle/RoadFordStyle.blend'))
scene=bpy.context.scene
for ob in list(bpy.data.objects):
    if 'GrassCarpet' in ob.name or ob.name.startswith('Coverage_') or 'Tussock' in ob.name:
        bpy.data.objects.remove(ob,do_unlink=True)
# Reuse the reviewed terrain equations without executing its build/export script.
tree=ast.parse((ROOT/'Art/Blender/build_road_ford_style.py').read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['center','channel','smooth','noise','edge','h']]
exec(compile(ast.Module(body=functions,type_ignores=[]),'terrain-functions','exec'))
mat=bpy.data.materials.new('M_DT_Foliage'); mat.use_nodes=True
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
p.inputs['Roughness'].default_value=.9; p.inputs['Specular IOR Level'].default_value=.1
vc=mat.node_tree.nodes.new('ShaderNodeVertexColor'); vc.layer_name='Color'
mat.node_tree.links.new(vc.outputs['Color'],p.inputs['Base Color'])
models={}; report=[]
for kind in range(4):
    fine=kind==3
    rng=random.Random(6140+kind*89)
    blades=[]
    for b in range(48 if fine else 160):
        angle=b*2.399963+rng.uniform(-.2,.2)
        if fine:
            radius=.42*math.sqrt(rng.random()); rx=radius*math.cos(angle); ry=radius*math.sin(angle)
            height=rng.uniform(.12,.26); reach=rng.uniform(.08,.20); width=rng.uniform(.012,.024)
        else:
            radius=rng.uniform(.02,.17); rx=radius*math.cos(angle); ry=radius*math.sin(angle)
            outer=b%5!=0
            height=rng.uniform(.43,.70)*(1 if kind==0 else (.84 if kind==1 else 1.15))
            reach=rng.uniform(.43,.72) if outer else rng.uniform(.15,.38)
            width=rng.uniform(.018,.037)
        blades.append((angle,rx,ry,height,reach,width,rng.random()))
    for lod,stride in enumerate([1,3,10]):
        verts=[]; faces=[]; colors=[]
        for angle,rx,ry,height,reach,width,tint in blades[::stride]:
            dx,dy=math.cos(angle),math.sin(angle); sx,sy=-dy,dx
            width*=math.sqrt(stride)*(.95 if lod else 1)
            base=(.16,.095,.044)
            tip=[(.36,.25,.12),(.29,.195,.092),(.41,.30,.15),(.28,.19,.087)][kind]
            shade=.78+.40*tint
            n=len(verts); segments=2 if fine else 4
            for j in range(segments+1):
                t=j/segments
                forward=reach*(t**.85)
                z=height*(math.sin(t*math.pi*(.86+.12*tint)) if not fine else t)-.035
                w=width*(1-.999*t)
                for sign in [-1,1]:
                    verts.append((rx+dx*forward+sx*w*sign,ry+dy*forward+sy*w*sign,z))
                    f=min(1,t*1.8)
                    colors.append(tuple((base[k]*(1-f)+tip[k]*f)*shade for k in range(3))+(1,))
            for j in range(segments):
                a=n+j*2; faces.extend([(a,a+1,a+3),(a,a+3,a+2)])
        name='SM_DT_'+['Crown','Shaggy','Tall','Underfelt'][kind]+'_LOD'+str(lod)
        me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
        ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob); me.materials.append(mat)
        ca=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
        uv=me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            poly.use_smooth=True
            for li in poly.loop_indices:
                vi=me.loops[li].vertex_index; ca.data[li].color=colors[vi]; uv.data[li].uv=(verts[vi][0],verts[vi][1])
        ob.hide_render=True; ob.hide_set(True); models[kind,lod]=ob
        report.append(dict(name=name,kind=kind,lod=lod,triangles=len(faces),vertices=len(verts)))
placements=[]
for layer,step in [('crown',1.08),('underfelt',.64)]:
    rng=random.Random(90231 if layer=='crown' else 27412)
    for ix in range(int(94/step)):
        for iy in range(int(62/step)):
            s=.5+(ix+rng.uniform(-.34,.34))*step; t=-31+(iy+rng.uniform(-.34,.34))*step
            shoulder=abs(t)-edge(s,t)-(.25 if layer=='crown' else .12)
            shore=abs(s-channel(t))-(4.0 if layer=='crown' else 3.9)
            if min(shoulder,shore)<0 or (s>72 and abs(t)<3): continue
            feather=min(1,shoulder/.85,shore/.8)
            if rng.random()>(.45+.55*feather): continue
            kind=3 if layer=='underfelt' else rng.choices([0,1,2],[.50,.35,.15])[0]
            scale=rng.uniform(.80,1.15)*(.75+.25*feather)
            eps=.1; gy=(h(s,t+eps)-h(s,t-eps))/(2*eps)
            gx=(h(s+eps,t)-h(s-eps,t))/(2*eps)-gy*(center(s+eps)-center(s-eps))/(2*eps)
            normal=Vector((-gx,-gy,1)).normalized()
            rotation=Vector((0,0,1)).rotation_difference(normal) @ Quaternion(Vector((0,0,1)),rng.uniform(-math.pi,math.pi))
            ob=bpy.data.objects.new('Dense_'+str(len(placements)),models[kind,0].data); scene.collection.objects.link(ob)
            ob.location=(s,center(s)+t,h(s,t)); ob.rotation_mode='QUATERNION'; ob.rotation_quaternion=rotation; ob.scale=(scale,)*3
            ob.visible_shadow=False
            e=rotation.to_euler('XYZ')
            placements.append(dict(kind=kind,location_m=list(ob.location),rotation_deg=[math.degrees(v) for v in e],scale=scale))
# Preserve the original review cameras and lighting. Add an overview of the whole field.
bpy.ops.object.camera_add(location=(9,-24,12)); cam=bpy.context.object; cam.name='Dense_overview'
cam.rotation_euler=(Vector((54,0,2))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=33
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DenseTussock.blend'))
scene.unit_settings.scale_length=.01
for (kind,lod),ob in models.items():
    bpy.ops.object.select_all(action='DESELECT'); ob.hide_set(False); ob.select_set(True); bpy.context.view_layer.objects.active=ob
    original=ob.data; ob.data=original.copy()
    for v in ob.data.vertices: v.co*=100
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
    copy=ob.data; ob.data=original; bpy.data.meshes.remove(copy); ob.hide_set(True)
scene.unit_settings.scale_length=1
manifest=dict(revision='dense-tussock-02',models=report,placements=placements,material='M_DT_Foliage',vertex_color_encoding='LINEAR')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
for name in ['Road_verge_detail','Dry_road_driver_view','Dense_overview']:
    scene.camera=bpy.data.objects[name]; scene.render.filepath=str(OUT/(name+'.png')); bpy.ops.render.render(write_still=True)
print('DENSE_TUSSOCK_BUILT '+json.dumps(dict(models=len(report),instances=len(placements))))
