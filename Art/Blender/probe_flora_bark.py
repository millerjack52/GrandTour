import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend',load_ui=False,use_scripts=False)
g=bpy.data.node_groups['FP_Wood_material_01'];r={'nodes':[],'links':[],'uv':[]}
for n in g.nodes:
 d={'name':n.name,'type':n.type,'group':n.node_tree.name if n.type=='GROUP' else '', 'inputs':{}}
 for i in n.inputs:
  if hasattr(i,'default_value'):
   v=i.default_value
   try:v=list(v)
   except:pass
   if isinstance(v,(str,int,float,list)):d['inputs'][i.name]=v
 if n.type=='VALTORGB':d['ramp']=[(e.position,list(e.color)) for e in n.color_ramp.elements]
 r['nodes'].append(d)
r['links']=[[l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name] for l in g.links]
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.startswith('FP_Tree') and '.' not in o.name:
  m=o.data;uv=m.uv_layers.get('UVMap') or m.uv_layers.active
  vals=[uv.data[i].uv[:] for p in m.polygons if p.material_index==0 for i in p.loop_indices]
  r['uv'].append({'name':o.name,'min':[min(v[a] for v in vals) for a in (0,1)],'max':[max(v[a] for v in vals) for a in (0,1)]})
Path('C:/GrandTour/Art/Export/LidarStudy/FloraPath/bark-source.json').write_text(json.dumps(r,indent=2))
