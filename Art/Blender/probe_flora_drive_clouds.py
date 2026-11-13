import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/GrandTourAssets/FlippedNormals/stylized_cloud_paint/Assets/Library_assets/Clouds_Assets.blend',load_ui=False,use_scripts=False)
r={'world':bpy.context.scene.world.name if bpy.context.scene.world else None,'engine':bpy.context.scene.render.engine,'objects':[]}
for name in ['Cloud_Assets_003','Cloud_Assets_007','Sun','Sun.001','Camera']:
 o=bpy.data.objects.get(name)
 if o:
  r['objects'].append({'name':name,'type':o.type,'location':list(o.location),'dimensions':list(o.dimensions),'rotation':list(o.rotation_euler),'modifiers':[(m.name,m.type) for m in o.modifiers],'hide_render':o.hide_render})
Path('C:/GrandTour/Art/Export/FloraDrive/cloud-source-settings.json').write_text(json.dumps(r,indent=2))
