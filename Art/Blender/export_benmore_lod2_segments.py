"""Reduce distant ribbon curvature segments, retaining every LOD2 blade.

Exports candidates only. Uses the approved study and the original LOD2 stride,
width and palette. LOD0/1 and every Unreal asset remain untouched.
"""
import bpy,json,hashlib,datetime
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Art/Export/TussockStyleStudy/07/TussockStyleStudy.blend'
OUT=ROOT/'Art/Export/BenmoreGaea'/('TussockSegments_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
report={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'scope':'LOD2 only: same complete blades, stride 8, width multiplier 2.15; fewer curvature segments',
        'installed':False,'models':[]}


def triangle_area(vertices,faces):
    return sum((vertices[b]-vertices[a]).cross(vertices[c]-vertices[a]).length*.5 for a,b,c in faces)


for variant,source_name,pairs in (
    ('Straw','Arching',8),('Rust','Wind-combed',8),('Weathered','Upright',8),('Fine','Fine undergrass',5)):
    source=bpy.data.objects[source_name].data
    stride=pairs*2
    assert len(source.vertices)%stride==0
    colour={loop.vertex_index:tuple(source.color_attributes['Color'].data[loop.index].color) for loop in source.loops}
    keep=[0,2,5,7] if pairs==8 else [0,2,4]
    vertices=[];faces=[];colours=[];reference=[];reference_faces=[];errors=[]
    blades=0
    for first in range(0,len(source.vertices),stride*8):
        blades+=1
        old=[]
        for j in range(stride):
            pair=first+(j//2)*2
            middle=(source.vertices[pair].co+source.vertices[pair+1].co)*.5
            old.append(middle+(source.vertices[first+j].co-middle)*2.15)
        offset=len(reference)
        reference.extend(old)
        for j in range(pairs-1):
            a=offset+j*2
            reference_faces.extend([(a,a+3,a+1),(a,a+2,a+3)])
        for left,right in zip(keep,keep[1:]):
            for pair in range(left,right+1):
                t=(pair-left)/(right-left)
                for edge in (0,1):
                    approximation=old[left*2+edge].lerp(old[right*2+edge],t)
                    errors.append((old[pair*2+edge]-approximation).length)
        offset=len(vertices)
        for pair in keep:
            for edge in (0,1):
                vertices.append(old[pair*2+edge])
                colours.append(colour[first+pair*2+edge])
        for j in range(len(keep)-1):
            a=offset+j*2
            faces.extend([(a,a+3,a+1),(a,a+2,a+3)])
    ratio=triangle_area(vertices,faces)/triangle_area(reference,reference_faces)
    assert ratio>.90, 'Excessive ribbon area loss'
    mesh=bpy.data.meshes.new('LOD2 reduced curvature '+variant)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    mesh.materials.append(source.materials[0])
    attr=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    uv=mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        polygon.use_smooth=True
        for index in polygon.loop_indices:
            vertex=mesh.loops[index].vertex_index
            attr.data[index].color=colours[vertex]
            uv.data[index].uv=vertices[vertex].xy
    mesh.normals_split_custom_set_from_vertices([Vector((v.x*.48,v.y*.48,.8)).normalized() for v in vertices])
    obj=bpy.data.objects.new('SM_TS_'+variant+'_LOD2_Segments',mesh)
    scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    for vertex in mesh.vertices:vertex.co*=100
    scene.unit_settings.scale_length=.01
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',
        global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
    scene.unit_settings.scale_length=1
    report['models'].append(dict(variant=variant,fbx=str(path),fbx_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        lod=2,blades=blades,reference_triangles=len(reference_faces),triangles=len(faces),
        triangle_reduction=1-len(faces)/len(reference_faces),area_ratio=ratio,max_edge_deviation_cm=max(errors)*100,
        retained_pairs=keep,near_lods_changed=False))
    bpy.data.objects.remove(obj,do_unlink=True)
(OUT/'manifest.json').write_text(json.dumps(report,indent=2))
print('TUSSOCK_SEGMENTS_CANDIDATES '+str(OUT),flush=True)
