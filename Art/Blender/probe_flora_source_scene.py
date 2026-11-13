import bpy,json
from pathlib import Path
src=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Assets_Library_v1_3_PRO/Main_Library/FloraPaint_v1_3_Library.blend')
out=Path('C:/GrandTour/Art/Export/LidarStudy/FloraMatch');out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(src),load_ui=False,use_scripts=False)
s=bpy.context.scene
r={'scene':s.name,'engine':s.render.engine,'view':s.view_settings.view_transform,'look':s.view_settings.look,'exposure':s.view_settings.exposure,'gamma':s.view_settings.gamma,
   'camera':s.camera.name if s.camera else None,'world':s.world.name if s.world else None,'world_nodes':[(n.name,n.bl_idname,[(i.name, list(i.default_value) if hasattr(i.default_value,'__len__') else i.default_value) for i in n.inputs if hasattr(i,'default_value')]) for n in s.world.node_tree.nodes] if s.world and s.world.node_tree else [],'lights':[], 'cameras':[], 'material_settings':[]}
for o in bpy.data.objects:
 if o.type=='LIGHT':r['lights'].append({'name':o.name,'type':o.data.type,'energy':o.data.energy,'angle':o.data.angle if o.data.type=='SUN' else None,'color':list(o.data.color),'location':list(o.location),'rotation':list(o.rotation_euler)})
 if o.type=='CAMERA':r['cameras'].append({'name':o.name,'location':list(o.location),'rotation':list(o.rotation_euler),'lens':o.data.lens,'type':o.data.type,'ortho_scale':o.data.ortho_scale})
for n in ['Leaf_0','Shrubbery','Grass.003','Plant_0.001']:
 m=bpy.data.materials.get(n)
 if m:r['material_settings'].append({'name':n,'surface_render_method':m.surface_render_method,'outputs':[(x.name,x.target,x.is_active_output) for x in m.node_tree.nodes if x.type=='OUTPUT_MATERIAL']})
(out/'source-scene.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
