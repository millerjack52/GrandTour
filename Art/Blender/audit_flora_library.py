"""Read-only inspection; run with factory startup and disabled auto-execution."""
import bpy
import json
from pathlib import Path

SOURCE=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Assets_Library_v1_3_PRO/Main_Library/FloraPaint_v1_3_Library.blend')
OUT=Path('C:/GrandTour/Saved/LidarAuthoringQA/AssetIntake')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
objects=[]
for o in bpy.data.objects:
    if o.type not in {'MESH','CURVE'}: continue
    row={'name':o.name,'type':o.type,'asset':bool(o.asset_data),'dimensions':list(o.dimensions),
         'materials':[m.name if m else None for m in o.data.materials],
         'modifiers':[{'name':m.name,'type':m.type,'group':m.node_group.name if m.type=='NODES' and m.node_group else None} for m in o.modifiers]}
    if o.type=='MESH':
        row.update(vertices=len(o.data.vertices),polygons=len(o.data.polygons),uvs=[a.name for a in o.data.uv_layers],attributes=[a.name for a in o.data.attributes])
    objects.append(row)
materials=[]
for m in bpy.data.materials:
    if not m.node_tree: continue
    materials.append({'name':m.name,'nodes':[{'name':n.name,'type':n.bl_idname,'group':n.node_tree.name if n.type=='GROUP' and n.node_tree else None,'image':n.image.name if n.type=='TEX_IMAGE' and n.image else None} for n in m.node_tree.nodes]})
images=[{'name':i.name,'path':i.filepath,'packed':bool(i.packed_file),'size':list(i.size)} for i in bpy.data.images]
result={'source':str(SOURCE),'objects':objects,'materials':materials,'images':images,
        'collections':[{'name':c.name,'asset':bool(c.asset_data),'objects':[o.name for o in c.objects]} for c in bpy.data.collections]}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'flora-audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('FLORA_AUDIT_OK',len(objects),len(materials),len(images),flush=True)
