"""Export approved study 07 unchanged at LOD0, with whole-blade authored LODs."""
import bpy, json, math, random, ast
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'Art/Export/TussockStyle'; OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Art/Export/TussockStyleStudy/07/TussockStyleStudy.blend'))
scene=bpy.context.scene
names=['Arching','Wind-combed','Upright','Fine undergrass']
models=[]
for kind,source_name in enumerate(names):
    source=bpy.data.objects[source_name]; src=source.data
    per_blade=16 if kind<3 else 10
    assert len(src.vertices)%per_blade==0
    # Source corner colour is shared by all corners of each vertex.
    vc={loop.vertex_index:tuple(src.color_attributes['Color'].data[loop.index].color) for loop in src.loops}
    for lod,stride in enumerate([1,3,8]):
        verts=[]; faces=[]; colors=[]; uv=[]
        if lod==0:
            me=src.copy()
        else:
            for first in range(0,len(src.vertices),per_blade*stride):
                offset=len(verts)
                for j in range(per_blade):
                    pair=first+(j//2)*2
                    mid=(src.vertices[pair].co+src.vertices[pair+1].co)*.5
                    v=mid+(src.vertices[first+j].co-mid)*[1,1.45,2.15][lod]
                    verts.append(tuple(v)); colors.append(vc[first+j])
                for j in range(per_blade//2-1):
                    a=offset+j*2; faces.extend([(a,a+3,a+1),(a,a+2,a+3)])
            me=bpy.data.meshes.new('Authored LOD'); me.from_pydata(verts,[],faces); me.update()
            col=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
            for p in me.polygons:
                p.use_smooth=True
                for li in p.loop_indices: col.data[li].color=colors[me.loops[li].vertex_index]
            me.normals_split_custom_set_from_vertices([Vector((v[0]*.48,v[1]*.48,.8)).normalized() for v in verts])
        # Keep the same simple material slot across all LODs; UE supplies its surface shader.
        me.materials.clear(); me.materials.append(src.materials[0])
        if not me.uv_layers:
            layer=me.uv_layers.new(name='UVMap')
            for loop in me.loops: layer.data[loop.index].uv=me.vertices[loop.vertex_index].co.xy
        name='SM_TS_'+['Straw','Rust','Weathered','Fine'][kind]+'_LOD'+str(lod)
        ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob)
        dims=[max(v.co[i] for v in me.vertices)-min(v.co[i] for v in me.vertices) for i in range(3)]
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
        for v in me.vertices:v.co*=100
        scene.unit_settings.scale_length=.01
        bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
        scene.unit_settings.scale_length=1
        me.calc_loop_triangles()
        models.append(dict(name=name,kind=kind,lod=lod,triangles=len(me.loop_triangles),size_m=dims))
        bpy.data.objects.remove(ob,do_unlink=True)

tree=ast.parse((ROOT/'Art/Blender/build_road_ford_style.py').read_text())
funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['center','channel','smooth','noise','edge','h']]
exec(compile(ast.Module(body=funcs,type_ignores=[]),'terrain-functions','exec'))
placements=[]
for layer,step in [('crown',.9),('fine',.60)]:
    rng=random.Random(73281 if layer=='crown' else 2739)
    for ix in range(int(94/step)):
        for iy in range(int(62/step)):
            s=.5+(ix+rng.uniform(-.34,.34))*step; t=-31+(iy+rng.uniform(-.34,.34))*step
            shoulder=abs(t)-edge(s,t)-(.25 if layer=='crown' else .12)
            shore=abs(s-channel(t))-(4 if layer=='crown' else 3.9)
            if min(shoulder,shore)<0 or (s>72 and abs(t)<3):continue
            feather=min(1,shoulder/.85,shore/.8)
            if rng.random()>.45+.55*feather:continue
            grouping=math.sin(s*.30+t*.15)+math.sin(t*.36-s*.085)+rng.uniform(-.55,.55)
            kind=3 if layer=='fine' else (2 if rng.random()<.13 else (0 if grouping>-.1 else 1))
            scale=rng.uniform(.78,1.06)*(.75+.25*feather)
            eps=.1; gy=(h(s,t+eps)-h(s,t-eps))/(2*eps)
            gx=(h(s+eps,t)-h(s-eps,t))/(2*eps)-gy*(center(s+eps)-center(s-eps))/(2*eps)
            normal=Vector((-gx,-gy,1)).normalized()
            rotation=Vector((0,0,1)).rotation_difference(normal) @ Quaternion(Vector((0,0,1)),rng.uniform(-math.pi,math.pi))
            placements.append(dict(kind=kind,location_m=[s,center(s)+t,h(s,t)],rotation_deg=[math.degrees(v) for v in rotation.to_euler('XYZ')],scale=scale))
(OUT/'manifest.json').write_text(json.dumps(dict(source='TussockStyleStudy/07',models=models,placements=placements),indent=2))
print('TUSSOCK_STYLE_EXPORT_OK '+json.dumps(dict(models=len(models),instances=len(placements))))
