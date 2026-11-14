"""Read original Eevee 3.4 environment settings without rendering or saving."""
import bpy
import hashlib
import json
from pathlib import Path

assert bpy.app.version[:2] == (3, 4), 'Read legacy Eevee settings in their native API'
root=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files')
out=Path('C:/GrandTour/Art/Export/TreeInventory/source-environments.json')


def value(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    try:return [value(x) for x in v]
    except TypeError:return str(v)


def fields(obj,names):return {name:value(getattr(obj,name)) for name in names if hasattr(obj,name)}


reports=[]
for relative in ['001/001.blend','002/Forest_20240121.blend']:
    path=root/relative; digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    scene=bpy.context.scene
    world=scene.world
    report={'source':str(path),'reader':bpy.app.version_string,'sha256':digest,
            'eevee':fields(scene.eevee,['use_gtao','gtao_distance','gtao_factor','use_soft_shadows',
                       'use_shadow_high_bitdepth','shadow_cube_size','shadow_cascade_size',
                       'taa_render_samples','use_bloom','use_ssr','use_ssr_refraction']),
            'display':fields(scene.view_settings,['view_transform','look','exposure','gamma']),
            'compositor_enabled':scene.use_nodes,
            'compositor_nodes':[{'name':n.name,'type':n.bl_idname,'muted':n.mute} for n in scene.node_tree.nodes] if scene.node_tree else [],
            'world_nodes':[{'name':n.name,'type':n.bl_idname,'inputs':{s.name:value(s.default_value) for s in n.inputs if hasattr(s,'default_value')}} for n in world.node_tree.nodes] if world and world.node_tree else [],
            'lights':[{'name':o.name,'rotation':list(o.rotation_euler),'hidden_render':o.hide_render,
                       'collections':[c.name for c in o.users_collection],
                       **fields(o.data,['type','energy','color','angle','use_shadow',
                           'use_contact_shadow','contact_shadow_distance','contact_shadow_bias','contact_shadow_thickness'])}
                      for o in bpy.data.objects if o.type=='LIGHT'],
            'leaf_settings':fields(bpy.data.materials['Leaf_0'],['blend_method','shadow_method','use_backface_culling','alpha_threshold','use_screen_refraction'])}
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    report['source_unchanged']=True;reports.append(report)
out.write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2),flush=True)
