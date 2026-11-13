import bpy,json
from pathlib import Path
p=Path('C:/GrandTour/Art/Export/RoadFordStyle/RoadFordStyle.blend')
bpy.ops.wm.open_mainfile(filepath=str(p))
s=bpy.context.scene
print('PALETTE_SCENE '+json.dumps(dict(objects=len(s.objects),camera=s.camera.name if s.camera else None,cameras=[o.name for o in s.objects if o.type=='CAMERA'],world=s.world.name,exposure=s.view_settings.exposure)))
for m in bpy.data.materials:
 if m.users:
  print('PALETTE_MATERIAL '+json.dumps(dict(name=m.name,nodes=[dict(name=n.name,type=n.type,colour=list(n.inputs['Base Color'].default_value) if n.type=='BSDF_PRINCIPLED' else None) for n in m.node_tree.nodes] if m.use_nodes else [])))
print('PALETTE_OBJECTS '+json.dumps([dict(name=o.name,loc=list(o.location),data=o.data.name if o.data else None) for o in s.objects if any(v in o.name.lower() for v in ('willow','mountain','ridge','water','camera'))][:35]))
