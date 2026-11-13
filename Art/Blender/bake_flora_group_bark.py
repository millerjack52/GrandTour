"""Dedicated bark UV1/colour from ACTIVE source graph; foliage coordinates intact."""
import bpy,bmesh,sys,json,math,hashlib,traceback
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraGroup';B=R/'Art/Export/LidarStudy/FloraParity/AssetMatch';D=O/'Bark';D.mkdir(exist_ok=True)
S=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend')
sys.path.insert(0,str(R/'Art/Blender'))
from flora_pigment_check import emission_material
report={'ok':False,'meshes':[],'active_source_bark':'procedural FP_Wood_material_01 through Moss_Shader_v1','source_bark_normal_texture':None,'normal_policy':'Preserve authored geometry/custom normals; active source has no normal-map or bump input','resolution':4096}
before=hashlib.sha256(S.read_bytes()).hexdigest()
try:
 bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False);s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=4;s.render.bake.target='IMAGE_TEXTURES'
 s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_depth='8';s.render.image_settings.color_mode='RGB'
 source=bpy.data.materials['Wood_material'];source.use_fake_user=True
 for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
 for key,folder in [('tree',B),('pine',O)]:
  bpy.ops.object.select_all(action='DESELECT');bpy.ops.import_scene.fbx(filepath=str(folder/'meshes'/('SM_Exact_'+key+'.fbx')),use_anim=False)
  ob=next(o for o in bpy.context.selected_objects if o.type=='MESH');mesh=ob.data;bpy.context.view_layer.objects.active=ob
  index=next(i for i,m in enumerate(mesh.materials) if m.name.startswith('Wood_material'))
  def fingerprint():
   return {'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'positions':hashlib.sha256(repr([tuple(v.co) for v in mesh.vertices]).encode()).hexdigest(),'uv0':hashlib.sha256(repr([tuple(x.uv) for x in mesh.uv_layers[0].data]).encode()).hexdigest(),'leaf_uv1':hashlib.sha256(repr([(li,tuple(mesh.uv_layers[1].data[li].uv)) for p in mesh.polygons if p.material_index!=index for li in p.loop_indices]).encode()).hexdigest()}
  original=fingerprint();mesh.uv_layers.active_index=1
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
  for p in mesh.polygons:p.select=p.material_index==index
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
  assert fingerprint()==original,'Geometry or leaf UV changed during bark-only unwrap'
  clone=ob.copy();clone.data=mesh.copy();s.collection.objects.link(clone)
  bm=bmesh.new();bm.from_mesh(clone.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=index],context='FACES');bm.to_mesh(clone.data);bm.free()
  material=emission_material(source,mesh.uv_layers[0].name);clone.data.materials.clear();clone.data.materials.append(material)
  for p in clone.data.polygons:p.material_index=0
  bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone
  image=bpy.data.images.new('SourceBark_'+key,width=4096,height=4096,alpha=False,float_buffer=True);image.colorspace_settings.name='Linear Rec.709'
  n=material.node_tree.nodes.new('ShaderNodeTexImage');n.image=image;material.node_tree.nodes.active=n
  assert bpy.ops.object.bake(type='EMIT',margin=24,uv_layer=clone.data.uv_layers[1].name)=={'FINISHED'}
  texture=D/('T_SourceBark_'+key+'.png');image.save_render(str(texture),scene=s)
  bpy.data.objects.remove(clone,do_unlink=True);bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
  fbx=D/('SM_Exact_'+key+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='SRGB',bake_anim=False,path_mode='STRIP')
  report['meshes'].append({'key':key,'fbx':str(fbx),'colour':str(texture),'before':original,'after':fingerprint(),'source_material':'Wood_material','source_bake':'active procedural wood + moss, emission-only, no illumination'})
  bpy.data.objects.remove(ob,do_unlink=True);print('DEDICATED_BARK',key,flush=True)
 report.update(ok=True,source_unchanged=hashlib.sha256(S.read_bytes()).hexdigest()==before)
except Exception:report['error']=traceback.format_exc();raise
finally:(O/'bark-report.json').write_text(json.dumps(report,indent=2))
