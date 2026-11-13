import bpy,json
from pathlib import Path
S=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend')
bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False)
def audit(m):
 g=next((n for n in m.node_tree.nodes if n.type=='GROUP' and n.node_tree and n.node_tree.name.startswith('Flora_Shader')),None)
 return {'name':m.name,'full_name':m.name_full,'library':m.library.filepath if m.library else None,'blend':getattr(m,'blend_method',None),'shadow':getattr(m,'shadow_method',None),'inputs':[(i,x.name,list(x.default_value) if hasattr(x.default_value,'__len__') else x.default_value) for i,x in enumerate(g.inputs) if hasattr(x,'default_value')] if g else []}
r={'materials':[audit(m) for m in bpy.data.materials if m.name.startswith('Leaf_0')],'objects':[{'name':o.name,'library':o.library.filepath if o.library else None,'materials':[audit(m) for m in o.data.materials]} for o in bpy.data.objects if o.type=='MESH' and o.name=='FP_Tree_B_001']}
Path('C:/GrandTour/Art/Export/FloraTreeLightBench/source-identities.json').write_text(json.dumps(r,indent=2))
