import bpy, json
from pathlib import Path
ROOT = Path('C:/GrandTour/Art/Export/VehicleTools')
FILES = {
 'CraftedUtility': ROOT/'crafted-character-detailed-v06/Crafted_Utility_Detailed.blend',
 'Pathfinder2002': ROOT/'pathfinder-articulation-v08/Pathfinder_Articulation.blend',
 'Impreza2003': ROOT/'impreza-ortho-full-v08/Impreza_Orthographic_Rebuild.blend',
}
out = {}
for name, path in FILES.items():
 bpy.ops.wm.open_mainfile(filepath=str(path))
 out[name] = dict(path=str(path), frame=bpy.context.scene.frame_current,
  collections=[dict(name=c.name, count=len(c.objects), hide_render=c.hide_render) for c in bpy.data.collections],
  objects=[dict(name=o.name,type=o.type,collections=[c.name for c in o.users_collection],hide_render=o.hide_render,props={k:str(o[k]) for k in o.keys()},location=list(o.matrix_world.translation)) for o in bpy.data.objects],
  materials=[dict(name=m.name, nodes=[n.type for n in m.node_tree.nodes] if m.node_tree else []) for m in bpy.data.materials])
p=ROOT/'new-cars-unreal-v01'
p.mkdir(exist_ok=True)
(p/'source-inspection.json').write_text(json.dumps(out,indent=2))
for name,v in out.items():
 print(name, 'collections:',v['collections'], 'objects:',len(v['objects']), 'materials:',v['materials'])
