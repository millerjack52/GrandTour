"""Repack bark independently of foliage; retain authored colour and leaf UVs."""
import bpy,bmesh,json,math,sys
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraPath');D=O/'BarkFix';D.mkdir(exist_ok=True)
manifest=json.loads((O/'scene-manifest.json').read_text());bpy.ops.wm.open_mainfile(filepath=manifest['source'],load_ui=False,use_scripts=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.render.bake.target='IMAGE_TEXTURES';s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
mat=bpy.data.materials['Wood_material'].copy();copies={}
def convert(t):
 for n in list(t.nodes):
  if n.type=='GROUP' and n.node_tree:
   name=n.node_tree.name
   if name not in copies:copies[name]=n.node_tree.copy();convert(copies[name])
   n.node_tree=copies[name]
  elif n.type in ('BSDF_DIFFUSE','BSDF_PRINCIPLED'):
   e=t.nodes.new('ShaderNodeEmission');c=n.inputs.get('Color') or n.inputs.get('Base Color');e.inputs['Color'].default_value=c.default_value
   if c.is_linked:t.links.new(c.links[0].from_socket,e.inputs['Color'])
   for l in list(n.outputs[0].links):t.links.new(e.outputs[0],l.to_socket)
   t.nodes.remove(n)
convert(mat.node_tree)
uvnode=mat.node_tree.nodes.new('ShaderNodeUVMap');uvnode.uv_map='UVMap'
for n in list(mat.node_tree.nodes):
 if n.type=='TEX_COORD':
  for l in list(n.outputs['UV'].links):mat.node_tree.links.new(uvnode.outputs[0],l.to_socket)
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
report={'ok':False,'meshes':[],'resolution':2048}
for row in manifest['meshes']:
 if not row['source'].startswith('FP_Tree'):continue
 if '--repair-only' in sys.argv and row['source'] not in ('FP_Tree_B_002','FP_Tree_B_003'):continue
 bpy.ops.import_scene.fbx(filepath=str(O/(row['name']+'.fbx')),use_custom_normals=True)
 o=next(o for o in bpy.context.selected_objects if o.type=='MESH');mesh=o.data;bpy.context.view_layer.objects.active=o
 before={'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'bounds':[list(o.bound_box[0]),list(o.bound_box[6])]}
 oldmats=list(mesh.materials);wood=next(i for i,m in enumerate(oldmats) if m.name.startswith('Wood_material'))
 original_leaf={li:tuple(mesh.uv_layers[1].data[li].uv) for p in mesh.polygons if p.material_index!=wood for li in p.loop_indices}
 mesh.uv_layers.active_index=1
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
 for p in mesh.polygons:p.select=p.material_index==wood
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
 assert all((mesh.uv_layers[1].data[li].uv-v).length<1e-7 for li,v in [(li,__import__('mathutils').Vector(v)) for li,v in original_leaf.items()])
 clone=o.copy();clone.data=mesh.copy();s.collection.objects.link(clone);bm=bmesh.new();bm.from_mesh(clone.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=wood],context='FACES');bm.to_mesh(clone.data);bm.free()
 clone.data.materials.clear();clone.data.materials.append(mat)
 for p in clone.data.polygons:p.material_index=0
 # Two source variants have collapsed/extreme source UVs. Repair colour-bake
 # coordinates only; exported geometry and original foliage UVs stay intact.
 repaired=row['source'] in ('FP_Tree_B_002','FP_Tree_B_003')
 if repaired:
  uv=clone.data.uv_layers.get('UVMap') or clone.data.uv_layers[0]
  for polygon in clone.data.polygons:
   angles=[]
   for li in polygon.loop_indices:
    v=clone.data.vertices[clone.data.loops[li].vertex_index].co
    angles.append((math.atan2(v.y,v.x)/math.tau)%1.)
   cross=max(angles)-min(angles)>.5
   for li,a in zip(polygon.loop_indices,angles):
    v=clone.data.vertices[clone.data.loops[li].vertex_index].co
    uv.data[li].uv=((a+1 if cross and a<.5 else a)*3.,v.z*1.8)

 bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone
 image=bpy.data.images.new('Bark_'+row['source'],width=2048,height=2048,alpha=False,float_buffer=True);imnode=mat.node_tree.nodes.new('ShaderNodeTexImage');imnode.image=image;mat.node_tree.nodes.active=imnode
 assert bpy.ops.object.bake(type='EMIT',margin=12,uv_layer=clone.data.uv_layers[1].name)=={'FINISHED'}
 image.save_render(str(D/(row['source']+'_bark.png')),scene=s)
 bpy.data.objects.remove(clone,do_unlink=True);mat.node_tree.nodes.remove(imnode)
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 bpy.ops.export_scene.fbx(filepath=str(D/(row['name']+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='SRGB',bake_anim=False,path_mode='STRIP')
 report['meshes'].append(dict(name=row['name'],source=row['source'],bark_slot=wood,before=before,leaf_uv_unchanged=True))
 print('BARK_BAKED',row['name'],flush=True);bpy.data.objects.remove(o,do_unlink=True)
report['ok']=True;(D/('repair-export-report.json' if '--repair-only' in sys.argv else 'export-report.json')).write_text(json.dumps(report,indent=2))
