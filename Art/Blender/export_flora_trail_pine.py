"""Freeze and bake one licensed conifer using the author's Blender generation."""
import bpy,bmesh,json,sys,math,hashlib,traceback
from pathlib import Path
from mathutils import Vector
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/PineTrial';O.mkdir(parents=True,exist_ok=True)
S=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/002/Forest_20240121.blend')
sys.path.insert(0,str(R/'Art/Blender'))
from bake_flora_exact import bake_assets
from flora_pigment_check import emission_material
report={'ok':False,'source':str(S),'source_hash':hashlib.sha256(S.read_bytes()).hexdigest(),'version':bpy.app.version_string,'tree':'FP_Tree_F_002'}
def save():(O/'export-report.json').write_text(json.dumps(report,indent=2))
try:
 assert bpy.app.version[:2]==(3,4)
 bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False)
 s=bpy.context.scene;s.frame_set(1)
 source=bpy.data.objects['FP_Tree_F_002'];dg=bpy.context.evaluated_depsgraph_get()
 mesh=bpy.data.meshes.new_from_object(source.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
 for m in mesh.materials:m.use_fake_user=True
 for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
 ob=bpy.data.objects.new('Pine_F002',mesh);s.collection.objects.link(ob)
 # Local asset coordinates, centred on the root, no scene placement/animation.
 lo=Vector(tuple(min(v.co[j] for v in mesh.vertices) for j in range(3)))
 hi=Vector(tuple(max(v.co[j] for v in mesh.vertices) for j in range(3)))
 offset=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 for v in mesh.vertices:v.co-=offset
 for im in bpy.data.images:
  if im.source=='FILE':
   p=S.parent/'textures'/Path(im.filepath.replace('\\','/')).name
   if p.is_file():im.filepath=str(p);im.reload()
 mesh.uv_layers.active_index=0
 for m in mesh.materials:
  for n in m.node_tree.nodes:
   if n.type=='UVMAP':n.uv_map=mesh.uv_layers[0].name
 ca=mesh.color_attributes.new(name='PathColour',type='FLOAT_COLOR',domain='CORNER');mesh.color_attributes.active_color=ca
 for p in mesh.polygons:
  seed=((p.index*1664525+1013904223)&0xffffffff)/4294967295
  for li in p.loop_indices:ca.data[li].color=(1,1,1,seed)
 for a in list(mesh.color_attributes):
  if a!=ca:mesh.color_attributes.remove(a)
 s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
 recipe={'assets':[{'key':'pine_f002','source':'FP_Tree_F_002'}]}
 bake_assets(s,[ob],recipe,O)
 report['recipe']=recipe
 # Repack only bark UV1 into its own 4K atlas, keeping all foliage coordinates.
 ob.hide_render=False;bpy.context.view_layer.objects.active=ob;ob.select_set(True)
 index=next(i for i,m in enumerate(mesh.materials) if m.name.startswith('Wood_material'))
 def leaf_uv():return hashlib.sha256(repr([(li,tuple(mesh.uv_layers[1].data[li].uv)) for p in mesh.polygons if p.material_index!=index for li in p.loop_indices]).encode()).hexdigest()
 before=leaf_uv();mesh.uv_layers.active_index=1
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
 for p in mesh.polygons:p.select=p.material_index==index
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
 assert before==leaf_uv()
 clone=ob.copy();clone.data=mesh.copy();s.collection.objects.link(clone)
 bm=bmesh.new();bm.from_mesh(clone.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=index],context='FACES');bm.to_mesh(clone.data);bm.free()
 mat=emission_material(mesh.materials[index],mesh.uv_layers[0].name);clone.data.materials.clear();clone.data.materials.append(mat)
 for p in clone.data.polygons:p.material_index=0
 bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone
 im=bpy.data.images.new('PineBark',width=4096,height=4096,alpha=False,float_buffer=True);im.colorspace_settings.name='Linear'
 n=mat.node_tree.nodes.new('ShaderNodeTexImage');n.image=im;mat.node_tree.nodes.active=n
 s.render.engine='CYCLES';s.cycles.samples=4;s.render.bake.target='IMAGE_TEXTURES'
 assert bpy.ops.object.bake(type='EMIT',margin=24,uv_layer=clone.data.uv_layers[1].name)=={'FINISHED'}
 bark=O/'textures/T_SourceBark_pine_f002.png';im.save_render(str(bark),scene=s)
 bpy.data.objects.remove(clone,do_unlink=True);bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;mesh.uv_layers.active_index=0
 fbx=O/'meshes/SM_Exact_pine_f002.fbx'
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='SRGB',bake_anim=False,path_mode='STRIP')
 mesh.calc_loop_triangles();report.update(triangles=len(mesh.loop_triangles),height=hi.z-lo.z,bark=str(bark),leaf_uv_preserved=before==leaf_uv())
 # Source beauty: authored shader, Standard, fixed sun/sky. Not an asset-preview match claim.
 s.render.engine='BLENDER_EEVEE';s.use_nodes=False;s.eevee.taa_render_samples=128;s.eevee.use_bloom=False
 s.render.resolution_x=768;s.render.resolution_y=768;s.render.resolution_percentage=100
 s.render.film_transparent=False
 h=hi.z-lo.z
 w=bpy.data.worlds.new('PineWorld');w.use_nodes=True;s.world=w
 w.node_tree.nodes['Background'].inputs['Color'].default_value=(.58,.74,1,1);w.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
 d=bpy.data.lights.new('PineSun','SUN');d.energy=16;d.color=(1,.814,.539);d.angle=math.radians(.5)
 sun=bpy.data.objects.new('PineSun',d);s.collection.objects.link(sun);sun.rotation_euler=Vector((-.233908564,.810244143,-.537392974)).to_track_quat('-Z','Y').to_euler()
 c=bpy.data.cameras.new('PineCamera');cam=bpy.data.objects.new('PineCamera',c);s.collection.objects.link(cam);s.camera=cam;c.lens=45
 cam.location=(0,-h*1.65,h*.6);target=Vector((0,0,h*.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 report['source_camera']={'position':list(cam.location),'target':list(target),'horizontal_fov':math.degrees(c.angle_x)}
 for ao in (False,True):
  s.eevee.use_gtao=ao;s.eevee.gtao_distance=1;s.eevee.gtao_factor=1.5
  s.render.filepath=str(O/('source_ao_on.png' if ao else 'source_ao_off.png'));bpy.ops.render.render(write_still=True)
 report.update(ok=True,source_unchanged=hashlib.sha256(S.read_bytes()).hexdigest()==report['source_hash']);save()
except Exception:report['error']=traceback.format_exc();save();raise
