"""Create a small Unreal trial from purchased source assets; never save the originals."""
import bpy,json,math,random,shutil
from pathlib import Path
from mathutils import Vector

ROOT=Path('C:/GrandTour')
SOURCE=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Assets_Library_v1_3_PRO/Main_Library/FloraPaint_v1_3_Library.blend')
OUT=ROOT/'Art/Export/LidarStudy/FloraPilot';OUT.mkdir(parents=True,exist_ok=True)
NAMES=['FP_Tree_E_001','FP_Shrubbery_003','FP_Small_Plants_002','FP_Grass_003']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):dst.objects=list(NAMES)
for o in dst.objects:bpy.context.scene.collection.objects.link(o)
def active(o):
    bpy.context.view_layer.update()
    for other in bpy.context.view_layer.objects:
        if other:other.select_set(False)
    o.hide_viewport=False;o.hide_render=False;o.hide_select=False;o.hide_set(False)
    o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.context.view_layer.update()
    assert list(bpy.context.selected_objects)==[o],('Selection',o.name,[x.name for x in bpy.context.selected_objects])

def bark_colors(o):
    """Bake source procedural diffuse colour, without light/shadow, into vertices."""
    active(o)
    for a in list(o.data.color_attributes):o.data.color_attributes.remove(a)
    ca=o.data.color_attributes.new(name='SourceBark',type='FLOAT_COLOR',domain='CORNER')
    o.data.color_attributes.active_color=ca
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
    scene.render.bake.target='VERTEX_COLORS'
    assert bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})=={'FINISHED'}
    vals=[tuple(c.color) for c in ca.data]
    assert any(max(c[:3])>.01 for c in vals),'Source bark bake is empty'

def material_part(source,slot):
    """Build clean topology instead of retaining source asset/dependency metadata."""
    data=source.data;polys=[p for p in data.polygons if p.material_index==slot]
    used=sorted({i for p in polys for i in p.vertices});remap={v:i for i,v in enumerate(used)}
    mesh=bpy.data.meshes.new('PilotPart');mesh.from_pydata([tuple(data.vertices[i].co) for i in used],[],[[remap[i] for i in p.vertices] for p in polys]);mesh.update()
    mesh.materials.append(data.materials[slot]);uv=mesh.uv_layers.new(name='UVMap');normals=[]
    for target,original in zip(mesh.polygons,polys):
        target.use_smooth=original.use_smooth
        for dst,src in zip(target.loop_indices,original.loop_indices):
            uv.data[dst].uv=data.uv_layers.active.data[src].uv
            normals.append(tuple(data.corner_normals[src].vector))
    if data.has_custom_normals:mesh.normals_split_custom_set(normals)
    part=bpy.data.objects.new('PilotPart',mesh);bpy.context.scene.collection.objects.link(part)
    return part

rows=[]
for src_name in NAMES:
    o=bpy.data.objects[src_name];active(o)
    bpy.context.view_layer.update()
    if o.modifiers:
        deps=bpy.context.evaluated_depsgraph_get()
        evaluated=bpy.data.meshes.new_from_object(o.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
        for m in list(o.modifiers):o.modifiers.remove(m)
        o.data=evaluated # freeze the authored shape at the source frame; wind belongs in Unreal
    o.location=(0,0,0);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    minz=min(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:v.co.z-=minz
    # Shader explicitly reads UVMap. Some sources list a different UV layer first.
    uv_values=[tuple(p.uv) for p in o.data.uv_layers['UVMap'].data]
    for uv in list(o.data.uv_layers):o.data.uv_layers.remove(uv)
    uv=o.data.uv_layers.new(name='UVMap')
    for p,v in zip(uv.data,uv_values):p.uv=v
    o.data.calc_loop_triangles();original_tris=len(o.data.loop_triangles)
    if src_name.startswith('FP_Tree'):
        wood=material_part(o,0);leaves=material_part(o,1)
        bpy.data.objects.remove(o,do_unlink=True)
        def debug_part(p,label):
            used={v for f in p.data.polygons for v in f.vertices}
            print('PART',label,p.name,len(p.data.polygons),len(p.data.vertices),len(used),min(p.data.vertices[i].co.z for i in used),max(p.data.vertices[i].co.z for i in used),flush=True)
        debug_part(wood,'wood_before');debug_part(leaves,'leaves_before')
        bark_colors(wood)
        debug_part(wood,'wood_baked');print('MODS',[(m.name,m.type) for m in wood.modifiers], 'SHAPES',bool(wood.data.shape_keys),flush=True)
        # Preserve source topology in the visual pilot. The first reduction trial
        # failed the bounds gate; optimisation must be validated independently.
        for p in [wood,leaves]:
            ca=p.data.color_attributes.get('SourceBark') or p.data.color_attributes.new(name='SourceBark',type='FLOAT_COLOR',domain='CORNER')
            if p==leaves:
                for c in ca.data:c.color=(1,1,1,1)
            p.data.color_attributes.active_color=ca
        active(wood);leaves.hide_select=False;leaves.hide_viewport=False;leaves.hide_set(False);leaves.select_set(True)
        assert len(bpy.context.selected_objects)==2
        assert bpy.ops.object.join()=={'FINISHED'};o=wood
        debug_part(o,'joined');print('OBJECTS',[(x.name,len(x.data.polygons)) for x in bpy.data.objects if x.type=='MESH'],flush=True)
    else:
        for a in list(o.data.color_attributes):o.data.color_attributes.remove(a)
        o.data.color_attributes.new(name='SourceBark',type='FLOAT_COLOR',domain='CORNER')
    ca=o.data.color_attributes['SourceBark'];o.data.color_attributes.active_color=ca
    height=max(v.co.z for v in o.data.vertices)
    # RGB stores source bark colour or restrained leaf variation; alpha is the wind weight.
    rng=random.Random(371)
    for p in o.data.polygons:
        iswood=o.data.materials[p.material_index].name=='Wood_material'
        for li in p.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co
            z=co.z/height
            if iswood:
                c=list(ca.data[li].color);c[3]=max(0,z-.45)*.12;ca.data[li].color=c
            else:
                variation=.96+.1*math.sin(co.x*1.7+co.y*2.3+co.z*.7)
                shade=variation*(.72+.28*z);ca.data[li].color=(shade,shade,shade,max(0,z-.08)**1.4)
    o.name='SM_Flora_'+src_name.removeprefix('FP_');active(o)
    o.data.calc_loop_triangles()
    bounds=[max(v.co[k] for v in o.data.vertices)-min(v.co[k] for v in o.data.vertices) for k in range(3)]
    row={'name':o.name,'source_object':src_name,'source_triangles':original_tris,'triangles':len(o.data.loop_triangles),'size_m':bounds,
         'materials':[m.name for m in o.data.materials],'custom_normals':o.data.has_custom_normals}
    bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='SRGB',bake_anim=False,path_mode='STRIP')
    rows.append(row)
    print('FLORA_EXPORTED',json.dumps(row),flush=True)
for name in ['plant_0.png','shrubbery_0.png','grass_0.png']:
    shutil.copy2(SOURCE.parent/'textures'/name,OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'flora-pilot-prepared.blend'))
(OUT/'manifest.json').write_text(json.dumps({'ok':True,'source':str(SOURCE),'meshes':rows,'notes':['Source tree topology and custom normals retained. An initial wood reduction failed the geometry gate and was rejected.','Original procedural bark diffuse colour baked to vertices without lighting.','Authored shape frozen at the source frame before export; no live Blender modifiers.','Pilot only: optimisation, distant LODs and wind require Unreal validation.']},indent=2))
