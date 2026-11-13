import bpy,json
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/panda-interior-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Panda_Assembly.blend'))
r={'engine':bpy.context.scene.render.engine,'glass':[]}
for o in bpy.context.scene.objects:
 if o.type!='MESH' or 'glass' not in o.name.lower():continue
 mats=[]
 for m in o.data.materials:
  p=m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
  mats.append({'name':m.name,'diffuse':list(m.diffuse_color),'principled':{k:list(p.inputs[k].default_value) if k=='Base Color' else p.inputs[k].default_value for k in ['Base Color','Roughness','Transmission Weight','IOR','Alpha']} if p else None})
 r['glass'].append({'name':o.name,'dimensions':list(o.dimensions),'materials':mats,'modifiers':[(m.name,m.type) for m in o.modifiers]})
print(json.dumps(r,indent=2))
