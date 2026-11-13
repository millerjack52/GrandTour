"""Ferrari material-only revision through the installed GT Paint normal baker."""
import bpy,sys,json,hashlib,shutil,time
from pathlib import Path
from mathutils import Vector
import numpy as np
sys.path.insert(0,'C:/GrandTour/Art/Blender')
from gt_paint import core
BASE=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-game-v01')
OUT=BASE.parent/'ferrari288-painterly-v01';OUT.mkdir(exist_ok=True)
preset=json.loads(Path('C:/GrandTour/Art/Blender/gt_paint_preset.json').read_text())
preset['normal'].update(dab_length_cm=100.,length_min=1.,length_max=2.4,aspect=1.5,coverage=2.,normal_jitter=6.,rot_jitter=20.,detail_enable=False,seed=7)
preset['normal_strength']=.5
(OUT/'painterly-preset.json').write_text(json.dumps(preset,indent=2))
def geometry_digest():
 h=hashlib.sha256()
 for o in sorted((o for o in bpy.data.objects if o.type=='MESH'),key=lambda o:o.name):
  h.update(o.name.encode());h.update(np.array(o.matrix_world,dtype=np.float64).tobytes())
  h.update(np.array([v.co[:] for v in o.data.vertices],dtype=np.float32).tobytes())
  h.update(str([tuple(p.vertices) for p in o.data.polygons]).encode())
  for uv in o.data.uv_layers:h.update(np.array([v.uv[:] for v in uv.data],dtype=np.float32).tobytes())
 return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Ferrari288_GameReady.blend'))
sc=bpy.context.scene;before=geometry_digest();copies=[]
for src in bpy.data.collections['Ferrari | preserved source components'].objects:
 if src.type!='MESH':continue
 o=src.copy();o.data=src.data.copy();sc.collection.objects.link(o);o.hide_set(False);o.hide_render=False;copies.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in copies:o.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='Ferrari288_PainterlyBake'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
core.ensure_normal_baker(preset)
s=sc.pnb_settings;s.features_enable=False;s.color_enable=False;s.flow_axis='Y'
assert s.bl_rna.properties['dab_length_cm'].hard_max==100
print('BAKING_MAXIMUM_BASE_STROKE_100CM',flush=True)
info=core.bake_normal(bpy.context,ob,'Ferrari288',str(OUT),2048,preset)
bpy.data.objects.remove(ob,do_unlink=True)
assert geometry_digest()==before
normal=info['file']
def attach():
 mat=next(m for m in bpy.data.materials if m.name.startswith('tripo_mat') or m.name=='F288_Source')
 assert core.attach_normal(mat,normal,'UVMap',.5)
 bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=.78
 bpy.data.images.load(normal,check_existing=True).pack()
 return mat
attach();sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=1440;sc.render.resolution_y=960;sc.render.resolution_percentage=100
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_Painterly.blend'))
def view(name,pos,target):
 cam=sc.camera;cam.data.lens=48;cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
 sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
view('front-quarter',(6,-8,4),(0,0,.8))
view('rear-quarter',(-6,8,3.6),(0,0,.8))
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Ferrari288_GameRig.blend'));rig_before=geometry_digest();attach();assert geometry_digest()==rig_before
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_Painterly_GameRig.blend'))
for name in ['SK_Ferrari288.fbx','SK_Ferrari288_LOD1.fbx','SK_Ferrari288_LOD2.fbx','T_F288_Source.png','T_F288_Palette.png','export-report.json']:
 shutil.copy2(BASE/name,OUT/name)
report={'ok':True,'baker':info,'normal_strength':.5,'roughness':.78,'authoring_geometry_uv_unchanged':True,'game_rig_geometry_uv_unchanged':True,'base_stroke_is_baker_maximum':True,'stroke_length_range_cm':[100,240],'fine_detail_pass':False,'source_albedo_preserved':True,'glass_preserved':True,'fbx_sha256':hashlib.sha256((OUT/'SK_Ferrari288.fbx').read_bytes()).hexdigest()}
(OUT/'painterly-report.json').write_text(json.dumps(report,indent=2));print('PAINTERLY_COMPLETE',json.dumps(report),flush=True)
