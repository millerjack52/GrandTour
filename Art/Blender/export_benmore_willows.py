"""Export approved willow family without changing the Blender originals."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'Art/Export/WillowFamily/willow-family-01';OUT=ROOT/'Art/Export/BenmoreScenery';OUT.mkdir(exist_ok=True)
rows=[]
for variant in ['young','broad','windswept','weathered']:
    bpy.ops.wm.open_mainfile(filepath=str(SRC/(variant+'.blend')))
    tree=next(o for o in bpy.data.objects if o.type=='MESH' and o.name=='SM_Willow_'+variant.title())
    hulls=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('UCX_'+tree.name)]
    assert len(hulls)==3,(variant,[o.name for o in hulls])
    bpy.ops.object.select_all(action='DESELECT')
    for c in tree.users_collection:c.hide_viewport=False
    for o in [tree]+hulls:
        o.hide_set(False);o.hide_viewport=False;o.select_set(True)
    bpy.context.view_layer.objects.active=tree
    # FBX carries one colour layer: preserve the fork blend used by painted bark.
    for a in list(tree.data.color_attributes):
        if a.name!='BarkBlend':tree.data.color_attributes.remove(a)
    tree.data.color_attributes.active_color_index=0
    materials=[]
    for i,m in enumerate(tree.data.materials):
        shader=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        materials.append({'slot':i,'name':m.name,'bark':i==0,'color':list(shader.inputs['Base Color'].default_value)[:3]})
    bpy.ops.export_scene.fbx(filepath=str(OUT/(tree.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='LINEAR',bake_anim=False)
    rows.append({'variant':variant,'name':tree.name,'materials':materials,'hulls':len(hulls),'dimensions_m':list(tree.dimensions),'uv_layers':[x.name for x in tree.data.uv_layers]})
(OUT/'willow-manifest.json').write_text(json.dumps({'ok':True,'source':str(SRC),'meshes':rows},indent=2))
