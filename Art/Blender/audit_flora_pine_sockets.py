"""Read exact socket identities; the purchased group repeats the name Soft."""
import bpy,json,hashlib
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/PineMatch'
source=Path(json.loads((R/'Art/Export/FloraTrail/PineTrial/export-report.json').read_text())['source']);before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
m=bpy.data.materials['Leaf_0.002'];group=next(n for n in m.node_tree.nodes if n.type=='GROUP' and n.node_tree.name.startswith('Flora_Shader'))
g=group.node_tree
data={'links':[[l.from_node.name,list(l.from_node.outputs).index(l.from_socket),l.from_socket.name,l.to_node.name,list(l.to_node.inputs).index(l.to_socket),l.to_socket.name] for l in g.links],
 'inputs':[[i,x.name,list(x.default_value) if hasattr(x.default_value,'__len__') else x.default_value] for i,x in enumerate(group.inputs) if hasattr(x,'default_value')],
 'images':[{ 'node':n.name,'image':n.image.name if n.image else None,'size':list(n.image.size) if n.image else None,'interpolation':n.interpolation} for n in m.node_tree.nodes if n.type=='TEX_IMAGE'],
 'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before}
(O/'socket-audit.json').write_text(json.dumps(data,indent=2));print(json.dumps({'soft_links':[l for l in data['links'] if l[0]=='Group Input' and l[2]=='Soft'],'images':data['images']}))
