import bpy,json
from pathlib import Path
S='D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend'
O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraPath')
bpy.ops.wm.open_mainfile(filepath=S,load_ui=False,use_scripts=False)
def val(v):
 try:return list(v)
 except:return v if isinstance(v,(str,int,float,bool)) else str(v)
def graph(t):return {'nodes':[{'name':n.name,'type':n.type,'group':n.node_tree.name if n.type=='GROUP' and n.node_tree else '', 'image':n.image.name if n.type=='TEX_IMAGE' and n.image else '', 'inputs':{i.name:val(i.default_value) for i in n.inputs if hasattr(i,'default_value')},'ramp':[[e.position,list(e.color)] for e in n.color_ramp.elements] if n.type=='VALTORGB' else None} for n in t.nodes], 'links':[[l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name] for l in t.links]}
out={'materials':{m.name:graph(m.node_tree) for m in bpy.data.materials if m.node_tree},'world':graph(bpy.context.scene.world.node_tree),'curves':[],'groups':{g.name:graph(g) for g in bpy.data.node_groups if 'Shader' in g.name}}
dg=bpy.context.evaluated_depsgraph_get()
for o in bpy.context.scene.objects:
 if o.type=='CURVE':
  e=o.evaluated_get(dg);mesh=e.to_mesh();
  if mesh is None:continue
  out['curves'].append({'name':o.name,'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'materials':[m.name for m in mesh.materials],'matrix':[list(r) for r in o.matrix_world]});e.to_mesh_clear()
out['visible_lights']=[o.name for o in bpy.context.scene.objects if o.type=='LIGHT' and o.visible_get() and not o.hide_render]
(O/'source-materials.json').write_text(json.dumps(out,indent=2))
print('CURVES',out['curves'],flush=True)

