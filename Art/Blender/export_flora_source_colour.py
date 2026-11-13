"""Bake the actual author colour graph, with no light/shadow baked into foliage."""
import bpy,json,math,numpy as np
from pathlib import Path
SRC=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Assets_Library_v1_3_PRO/Main_Library/FloraPaint_v1_3_Library.blend')
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FloraMatch');OUT.mkdir(parents=True,exist_ok=True)
names=['FP_Tree_E_001','FP_Shrubbery_003','FP_Small_Plants_002','FP_Grass_003']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(SRC),link=False) as (src,dst):dst.objects=list(names)
for o in dst.objects:bpy.context.scene.collection.objects.link(o)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=1;s.cycles.device='CPU';s.render.bake.target='VERTEX_COLORS'
rows=[]
for name in names:
 o=bpy.data.objects[name]
 for other in bpy.context.view_layer.objects:other.select_set(False)
 o.hide_render=False;o.hide_select=False;o.hide_viewport=False;o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 o.location=(0,0,0);bpy.context.view_layer.update()
 if o.modifiers:
  dg=bpy.context.evaluated_depsgraph_get();data=bpy.data.meshes.new_from_object(o.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
  for mod in list(o.modifiers):o.modifiers.remove(mod)
  o.data=data
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 minz=min(v.co.z for v in o.data.vertices)
 for v in o.data.vertices:v.co.z-=minz
 uvdata=[tuple(v.uv) for v in o.data.uv_layers['UVMap'].data]
 for uv in list(o.data.uv_layers):o.data.uv_layers.remove(uv)
 uv=o.data.uv_layers.new(name='UVMap')
 for v,coords in zip(uv.data,uvdata):v.uv=coords
 for a in list(o.data.color_attributes):o.data.color_attributes.remove(a)
 ca=o.data.color_attributes.new(name='SourceColour',type='FLOAT_COLOR',domain='CORNER');o.data.color_attributes.active_color=ca
 original_mats=list(o.data.materials)
 for mat in original_mats:
  if mat.name=='Wood_material':
   tree=mat.node_tree;uvnode=tree.nodes.new('ShaderNodeUVMap');uvnode.uv_map='UVMap'
   for texcoord in [n for n in tree.nodes if n.type=='TEX_COORD']:
    for link in list(texcoord.outputs['UV'].links):tree.links.new(uvnode.outputs[0],link.to_socket)
 # Preserve the existing diffuse-only bark extraction for wood slots.
 if any(m.name=='Wood_material' for m in original_mats):
  assert bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})=={'FINISHED'}
 wood={li:tuple(ca.data[li].color) for p in o.data.polygons if original_mats[p.material_index].name=='Wood_material' for li in p.loop_indices}
 for idx,m in enumerate(original_mats):
  if m.name=='Wood_material':continue
  clone=m.copy();o.data.materials[idx]=clone;tree=clone.node_tree
  group=next(n for n in tree.nodes if n.type=='GROUP' and n.node_tree.name.startswith('Flora_Shader'))
  for n in list(tree.nodes):
   if n.type=='OUTPUT_MATERIAL':tree.nodes.remove(n)
  emit=tree.nodes.new('ShaderNodeEmission');emit.inputs['Strength'].default_value=1
  out=tree.nodes.new('ShaderNodeOutputMaterial');tree.links.new(group.outputs['Color'],emit.inputs['Color']);tree.links.new(emit.outputs[0],out.inputs['Surface'])
 assert bpy.ops.object.bake(type='EMIT')=={'FINISHED'}
 for li,col in wood.items():ca.data[li].color=col
 stats={}
 height=max(v.co.z for v in o.data.vertices)
 for p in o.data.polygons:
  mat=original_mats[p.material_index].name;values=stats.setdefault(mat,[])
  for li in p.loop_indices:
   c=list(ca.data[li].color);z=o.data.vertices[o.data.loops[li].vertex_index].co.z/height
   values.append(c[:3]);c[3]=max(0,z-.45)*.12 if mat=='Wood_material' else max(0,z-.08)**1.4;ca.data[li].color=c
 # Preserve the full procedural leaf colour in a separate, non-overlapping UV
 # atlas. Vertex-only baking cannot retain the shrub's authored fine variation.
 atlas_uv=o.data.uv_layers.new(name='SourceColourUV');o.data.uv_layers.active=atlas_uv
 for p in o.data.polygons:p.select=True
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.001);bpy.ops.object.mode_set(mode='OBJECT')
 size=2048 if name=='FP_Tree_E_001' else (1024 if name=='FP_Shrubbery_003' else 512)
 im=bpy.data.images.new(name+'_Colour',width=size,height=size,alpha=False,float_buffer=True);im.colorspace_settings.name='sRGB'
 for mat in o.data.materials:
  tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;mat.node_tree.nodes.active=tex
 s.render.bake.target='IMAGE_TEXTURES';s.render.bake.margin=8
 assert bpy.ops.object.bake(type='EMIT',margin=8,margin_type='EXTEND',uv_layer='SourceColourUV')=={'FINISHED'}
 if wood:
  leaf_pixels=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(leaf_pixels)
  assert bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'},margin=0,uv_layer='SourceColourUV')=={'FINISHED'}
  wood_pixels=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(wood_pixels)
  # Occupied wood and leaf UV islands are disjoint; fill gutters after export.
  combined=leaf_pixels.reshape(-1,4).copy();wood_values=wood_pixels.reshape(-1,4)
  wood_occupied=np.any(wood_values[:,:3]>0,axis=1)
  combined[wood_occupied]=wood_values[wood_occupied];im.pixels.foreach_set(combined.reshape(-1))
 s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
 im.save_render(str(OUT/(name+'_Colour.png')),scene=s)
 s.render.bake.target='VERTEX_COLORS';o.data.uv_layers.active=o.data.uv_layers['UVMap']
 # A constant per-card seed decorrelates temporal coverage of overlapping cards.
 # Leaf colour comes from the atlas; wood keeps its baked RGB. Alpha retains wind.
 ca=o.data.color_attributes['SourceColour']
 for p in o.data.polygons:
  if original_mats[p.material_index].name!='Wood_material':
   h=p.index+1;h=((h^(h>>16))*0x7feb352d)&0xffffffff;h=((h^(h>>15))*0x846ca68b)&0xffffffff;h^=h>>16;seed=h/4294967295
   for li in p.loop_indices:
    c=list(ca.data[li].color);c[0]=seed;ca.data[li].color=c
 for idx,m in enumerate(original_mats):o.data.materials[idx]=m
 o.data.calc_loop_triangles();bounds=[[min(v.co[k] for v in o.data.vertices),max(v.co[k] for v in o.data.vertices)] for k in range(3)]
 row={'source':name,'triangles':len(o.data.loop_triangles),'bounds':bounds,'materials':[m.name for m in original_mats],
      'colour_atlas':name+'_Colour.png','colour_atlas_size':size,'colour_uv_channel':1,
      'colours':{mat:{'mean':[sum(v[k] for v in a)/len(a) for k in range(3)],'min':[min(v[k] for v in a) for k in range(3)],'max':[max(v[k] for v in a) for k in range(3)]} for mat,a in stats.items()}}
 o.name='SM_Match_'+name.removeprefix('FP_');row['mesh']=o.name
 bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='SRGB',bake_anim=False,path_mode='STRIP')
 rows.append(row);print('SOURCE_COLOUR_BAKED',json.dumps(row),flush=True)
(OUT/'source-colour-manifest.json').write_text(json.dumps(rows,indent=2))
