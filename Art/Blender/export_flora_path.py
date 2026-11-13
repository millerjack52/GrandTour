"""Convert the purchased learning scene into an isolated, instanced Unreal study.
Original scene/artwork: Casey Sheep. Never overwrite or redistribute the source.
"""
import bpy,json,math,re,hashlib,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
SRC=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend')
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FloraPath');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SRC),load_ui=False,use_scripts=False)
s=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get()
audit=json.loads((OUT/'source-audit.json').read_text());probe=json.loads((OUT/'source-materials.json').read_text())
groups={};placements=[]
for i in dg.object_instances:
 o=i.object;original=o.original
 if o.type!='MESH' or original.name=='FOG' or original.hide_render:continue
 if not i.is_instance and not original.visible_get():continue
 key=(original.name.split('.')[0] if original.name.startswith('FP_Tree') else original.data.name)+'|'+','.join(m.name for m in original.data.materials if m)
 if key not in groups:
  mesh=bpy.data.meshes.new_from_object(o,preserve_all_data_layers=True,depsgraph=dg)
  groups[key]={'mesh':mesh,'source':original.name.split('.')[0] if original.name.startswith('FP_Tree') else original.name,'materials':[m.name for m in mesh.materials], 'matrix':o.matrix_world.copy()}
 placements.append({'key':key,'matrix':[list(r) for r in i.matrix_world]})
print('PATH_GROUPS',len(groups),'INSTANCES',len(placements),flush=True)
# Remove the live scene graph after freezing geometry and instance transforms.
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=1;s.cycles.device='CPU';s.render.bake.target='VERTEX_COLORS'
s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
for im in bpy.data.images:
 if im.source=='FILE':
  filename=Path(im.filepath.replace('\\','/')).name;p=SRC.parent/'textures'/filename
  if p.is_file():im.filepath=str(p);im.reload()
converted={};groupcopies={};settings={}
def convert_tree(tree):
 for n in list(tree.nodes):
  if n.type=='GROUP' and n.node_tree:
   key=n.node_tree.name
   if key not in groupcopies:
    g=n.node_tree.copy();groupcopies[key]=g;convert_tree(g)
   n.node_tree=groupcopies[key]
  elif n.type in ('BSDF_DIFFUSE','BSDF_PRINCIPLED'):
   emit=tree.nodes.new('ShaderNodeEmission');inp=n.inputs.get('Color') or n.inputs.get('Base Color')
   emit.inputs['Color'].default_value=inp.default_value
   if inp.is_linked:tree.links.new(inp.links[0].from_socket,emit.inputs['Color'])
   for link in list(n.outputs[0].links):tree.links.new(emit.outputs[0],link.to_socket)
   tree.nodes.remove(n)
def convert_material(mat):
 if mat.name in converted:return converted[mat.name]
 name=mat.name;m=mat.copy();m.name='PathBake_'+name;tree=m.node_tree
 flora=next((n for n in tree.nodes if n.type=='GROUP' and n.node_tree and n.node_tree.name.startswith('Flora_Shader')),None)
 if flora:
  masktex=next((n.image for n in tree.nodes if n.type=='TEX_IMAGE' and n.image and not n.image.name.startswith('Gradient')),None)
  ramp=next((n for n in tree.nodes if n.type=='VALTORGB' and any(l.to_node==flora and l.to_socket.name=='Alpha Mask' for l in n.outputs[0].links)),None)
  maskname=(Path(masktex.filepath.replace('\\','/')).name or re.match(r'.+?\.(?:png|jpg)',masktex.name).group(0)) if masktex else None
  settings[name]={'foliage':True,'mask':maskname,'soft':float(flora.inputs['Soft'].default_value),'ramp':[[float(e.position),float(e.color[0])] for e in ramp.color_ramp.elements] if ramp else [[0,0],[1,1]],'emission':float(flora.inputs['Emission Strength'].default_value),'emission_colour':list(flora.inputs['Emission Color'].default_value)}
  for n in list(tree.nodes):
   if n.type=='OUTPUT_MATERIAL':tree.nodes.remove(n)
  emit=tree.nodes.new('ShaderNodeEmission');out=tree.nodes.new('ShaderNodeOutputMaterial');tree.links.new(flora.outputs['Color'],emit.inputs['Color']);tree.links.new(emit.outputs[0],out.inputs['Surface'])
 else:
  settings[name]={'foliage':False};convert_tree(tree)
 converted[name]=m;return m
rows=[]
for idx,(key,g) in enumerate(groups.items()):
 mesh=g['mesh'];o=bpy.data.objects.new('Path_'+str(idx),mesh);s.collection.objects.link(o)
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 mats=list(mesh.materials)
 for n,m in enumerate(mats):mesh.materials[n]=convert_material(m)
 if '--metadata-only' in sys.argv:
  name='SM_Path_'+re.sub('[^a-zA-Z0-9_]','_',g['source']);atlas='Colour_'+str(idx)+'.png' if g['source'].startswith('FP_Tree') or g['source']=='Ground1' else None
  assert (OUT/(name+'.fbx')).is_file()
  mesh.calc_loop_triangles();rows.append({'key':key,'name':name,'source':g['source'],'materials':g['materials'],'triangles':len(mesh.loop_triangles),'atlas':atlas,'uv_channels':2 if atlas else 1})
  bpy.data.objects.remove(o,do_unlink=True);continue
 # Keep original colour attributes because the authored terrain reads them.
 ca=mesh.color_attributes.new(name='PathColour',type='FLOAT_COLOR',domain='CORNER');mesh.color_attributes.active_color=ca
 for m in mesh.materials:
  for n in m.node_tree.nodes:
   if n.type=='VERTEX_COLOR' and not n.layer_name:
    n.layer_name=next((a.name for a in mesh.color_attributes if a.name!='PathColour'),'')
 if not mesh.uv_layers:mesh.uv_layers.new(name='UVMap')
 preferred=mesh.uv_layers.get('UVMap') or mesh.uv_layers[0];mesh.uv_layers.active=preferred
 assert bpy.ops.object.bake(type='EMIT')=={'FINISHED'}
 atlas=None
 if g['source'].startswith('FP_Tree') or g['source']=='Ground1':
  # Preserve original UV evaluation while adding a uniquely packed colour atlas.
  for m in mesh.materials:
   uvnode=m.node_tree.nodes.new('ShaderNodeUVMap');uvnode.uv_map=preferred.name
   for n in list(m.node_tree.nodes):
    if n.type=='TEX_COORD':
     for l in list(n.outputs['UV'].links):m.node_tree.links.new(uvnode.outputs[0],l.to_socket)
  preferred_name=preferred.name
  uv=mesh.uv_layers.new(name='PathAtlas');mesh.uv_layers.active=uv
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.002);bpy.ops.object.mode_set(mode='OBJECT')
  image=bpy.data.images.new('PathAtlas_'+str(idx),width=2048,height=2048,alpha=False,float_buffer=True)
  for m in mesh.materials:
   n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=image;m.node_tree.nodes.active=n
  s.render.bake.target='IMAGE_TEXTURES';assert bpy.ops.object.bake(type='EMIT',margin=12,uv_layer='PathAtlas')=={'FINISHED'}
  atlas='Colour_'+str(idx)+'.png';image.save_render(str(OUT/atlas),scene=s);s.render.bake.target='VERTEX_COLORS'
  # Export exactly UV0 authored mask mapping and UV1 colour atlas.
  original_uv=[tuple(x.uv) for x in mesh.uv_layers[preferred_name].data];atlas_uv=[tuple(x.uv) for x in mesh.uv_layers['PathAtlas'].data]
  for layer in list(mesh.uv_layers):mesh.uv_layers.remove(layer)
  for name,values in [('UVMap',original_uv),('PathAtlas',atlas_uv)]:
   layer=mesh.uv_layers.new(name=name)
   for e,v in zip(layer.data,values):e.uv=v
 else:
  original_uv=[tuple(x.uv) for x in preferred.data]
  for layer in list(mesh.uv_layers):mesh.uv_layers.remove(layer)
  layer=mesh.uv_layers.new(name='UVMap')
  for e,v in zip(layer.data,original_uv):e.uv=v
 # Use RGB for baked colour and A for deterministic per-card coverage seeds.
 ca=mesh.color_attributes['PathColour'];mesh.color_attributes.active_color=ca
 for p in mesh.polygons:
  seed=((p.index*1664525+1013904223)&0xffffffff)/4294967295
  for li in p.loop_indices:
   c=list(ca.data[li].color);c[3]=seed;ca.data[li].color=c
 for a in list(mesh.color_attributes):
  if a.name!='PathColour':mesh.color_attributes.remove(a)
 for n,m in enumerate(mats):mesh.materials[n]=m
 name='SM_Path_'+re.sub('[^a-zA-Z0-9_]','_',g['source']);o.name=name;mesh.calc_loop_triangles()
 bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='SRGB',bake_anim=False,path_mode='STRIP')
 rows.append({'key':key,'name':name,'source':g['source'],'materials':g['materials'],'triangles':len(mesh.loop_triangles),'atlas':atlas,'uv_channels':len(mesh.uv_layers)})
 print('PATH_EXPORT',idx+1,len(groups),name,len(mesh.loop_triangles),flush=True)
 bpy.data.objects.remove(o,do_unlink=True)
for p in placements:
 key=p.pop('key');p['mesh']=next(r['name'] for r in rows if r['key']==key)
 loc,q,sc=Matrix(p['matrix']).decompose();p['location_cm']=[loc.x*100,-loc.y*100,loc.z*100];p['quat']=[-q.x,q.y,-q.z,q.w];p['scale']=list(sc)
out={'source':str(SRC),'attribution':'Original scene and assets by Casey Sheep / Flora Paint. Unreal conversion is an isolated purchaser study.','meshes':rows,'instances':placements,'materials':settings,'camera':audit['camera'],'light':next(x for x in audit['lights'] if x['name']=='Sun.001')}
(OUT/'scene-manifest.json').write_text(json.dumps(out,indent=2));print('PATH_EXPORT_DONE',flush=True)
