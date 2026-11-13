import bpy,sys,json,math,hashlib,shutil
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0,'C:/GrandTour/Art/Blender');from gt_paint import core
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-expedition-v01');src=OUT/'Ferrari288_Expedition.blend'
bpy.ops.wm.open_mainfile(filepath=str(src));sc=bpy.context.scene
parts=[o for o in bpy.data.collections['CUSTOM | Expedition equipment'].all_objects if o.type=='MESH']
spare=next(o for o in parts if o.name.startswith('Spare | matching'))
kit=[o for o in parts if o!=spare]
preset=json.loads((OUT.parent/'ferrari288-benmore-paint/preset.json').read_text());preset['normal_enable']=True
core.ensure_normal_baker(preset);sc.pnb_settings.detail_enable=False;sc.pnb_settings.features_enable=False;sc.pnb_settings.color_enable=False
info=core.bake(bpy.context,kit,'F288Expedition',str(OUT),2048,preset)
for label,path in info['files'].items():shutil.copy2(path,OUT/('T_F288_Expedition_'+label+'.png'))
ob=bpy.data.objects[info['bake_object']];ob.hide_set(False);ob.hide_render=False
mat=bpy.data.materials.new('F288_Expedition');mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/'T_F288_Expedition_D.png'));tex.image.pack();mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.7
ob.data.materials.clear();ob.data.materials.append(mat)
for p in ob.data.polygons:p.material_index=0
# Spare retains exactly the accepted car UV and painterly material.
dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(spare.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg);me.transform(spare.matrix_world)
sp=bpy.data.objects.new('Export matching spare',me);sc.collection.objects.link(sp);me.materials[0].name='F288_Source'
# Rename active UV consistently before joining; the two materials use separate atlases.
ob.data.uv_layers[0].name='UVMap';sp.data.uv_layers[0].name='UVMap'
core.select_only(bpy.context,[ob,sp]);bpy.context.view_layer.objects.active=ob;bpy.ops.object.join();ob.name='SM_Ferrari288_Expedition'
tri=ob.modifiers.new('Triangulate export','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
T=Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z');ob.data.transform(T);sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.01
core.select_only(bpy.context,[ob]);path=OUT/'SM_Ferrari288_Expedition.fbx'
bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='AUTO')
coords=[(v.co.x,-v.co.y,v.co.z) for v in ob.data.vertices]
report={'source':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'fbx_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':len(ob.data.polygons),'bounds_cm':[[min(v[i] for v in coords) for i in range(3)],[max(v[i] for v in coords) for i in range(3)]],'materials':[m.name for m in ob.data.materials],'paint':info,'attachment':'Vehicle mesh, identity relative transform, +X forward, centimetres'}
(OUT/'equipment-export-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_Expedition_Export.blend'))
print('EXPEDITION_EXPORT_COMPLETE',json.dumps(report),flush=True)
