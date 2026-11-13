import bpy,json
from pathlib import Path
SOURCE=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Assets_Library_v1_3_PRO/Main_Library/FloraPaint_v1_3_Library.blend')
OUT=Path('C:/GrandTour/Saved/LidarAuthoringQA/AssetIntake')
names=['FP_Tree_E_001','FP_Shrubbery_003','FP_Small_Plants_002','FP_Grass_003']
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):dst.objects=names
for o in dst.objects:bpy.context.scene.collection.objects.link(o)
def value(s):
    try:
        v=s.default_value
        if isinstance(v,(float,int,str,bool)):return v
        return list(v)
    except:return None
def nodes(tree):
    return {'nodes':[{'name':n.name,'type':n.bl_idname,'inputs':[{ 'name':s.name,'value':value(s),'links':[(l.from_node.name,l.from_socket.name) for l in s.links]} for s in n.inputs],
    'image':{'name':n.image.name,'path':bpy.path.abspath(n.image.filepath),'colorspace':n.image.colorspace_settings.name} if n.type=='TEX_IMAGE' and n.image else None,
    'uv_map':n.uv_map if n.type=='UVMAP' else None,
    'ramp':[(e.position,list(e.color)) for e in n.color_ramp.elements] if n.type=='VALTORGB' else None,
    'group':n.node_tree.name if n.type=='GROUP' and n.node_tree else None} for n in tree.nodes]}
materials={m.name:nodes(m.node_tree) for m in bpy.data.materials if m.node_tree}
groups={g.name:nodes(g) for g in bpy.data.node_groups}
objects=[]
for o in dst.objects:
    o.data.calc_loop_triangles()
    counts={}
    for t in o.data.loop_triangles:counts[t.material_index]=counts.get(t.material_index,0)+1
    objects.append({'name':o.name,'triangles':len(o.data.loop_triangles),'by_material':counts,'dimensions':list(o.dimensions),'scale':list(o.scale),'location':list(o.location),'custom_normals':o.data.has_custom_normals,'uv_active':o.data.uv_layers.active.name})
(OUT/'pilot-source-detail.json').write_text(json.dumps({'materials':materials,'groups':groups,'objects':objects},indent=2))
print('PILOT_SOURCE_OK',json.dumps(objects),flush=True)
