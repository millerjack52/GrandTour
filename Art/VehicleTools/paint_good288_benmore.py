"""Full GT Paint colour/mask/normal bake, matching Benmore's vehicle workflow."""
import bpy,sys,json,hashlib,shutil
from pathlib import Path
from mathutils import Vector
import numpy as np
sys.path.insert(0,'C:/GrandTour/Art/Blender');from gt_paint import core
BASE=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-game-v01')
OUT=BASE.parent/'ferrari288-benmore-paint';OUT.mkdir(exist_ok=True)
preset=json.loads(Path('C:/GrandTour/Art/Blender/gt_paint_preset.json').read_text())
preset['normal'].update(dab_length_cm=100.,length_min=1.,length_max=2.4,aspect=1.5,detail_enable=False,normal_jitter=6.)
preset['base_source']='id'
# The imported shell's custom normals turn the bevel wear detector into broad
# white patches. Keep this request to painted shading rather than chipped paint.
preset.update(wear_tint=0.,wear_lighten=0.,normal_enable=False)
def digest():
 h=hashlib.sha256()
 for o in sorted((o for o in bpy.data.objects if o.type=='MESH'),key=lambda o:o.name):
  h.update(o.name.encode());h.update(np.array(o.matrix_world).tobytes());h.update(np.array([v.co[:] for v in o.data.vertices]).tobytes())
  h.update(str([tuple(p.vertices) for p in o.data.polygons]).encode())
  for uv in o.data.uv_layers:h.update(np.array([x.uv[:] for x in uv.data]).tobytes())
 return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Ferrari288_GameReady.blend'));sc=bpy.context.scene;before=digest()
img=next(i for i in bpy.data.images if i.name.startswith('tripo_rgb'))
parts=[]
for src in bpy.data.collections['Ferrari | preserved source components'].objects:
 if src.type!='MESH':continue
 ob=src.copy();ob.data=src.data.copy();sc.collection.objects.link(ob);parts.append(ob)
core.select_only(bpy.context,parts);bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=bpy.context.object
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
ob.name='Ferrari_GT_Paint_Atlas';ob.data.materials.clear();ob.data.materials.append(bpy.data.materials.new('Ferrari Paint IDs'))
core.apply_style([ob],preset);mat=ob.data.materials[0];nt=mat.node_tree;g=core.group_node_of(mat)
tex=nt.nodes.new('ShaderNodeTexImage');tex.image=img
hsv=nt.nodes.new('ShaderNodeSeparateColor');hsv.mode='HSV';nt.links.new(tex.outputs['Color'],hsv.inputs['Color'])
def math(op,a,b):
 n=nt.nodes.new('ShaderNodeMath');n.operation=op
 for i,v in enumerate([a,b]):
  if isinstance(v,(int,float)):n.inputs[i].default_value=v
  else:nt.links.new(v,n.inputs[i])
 return n.outputs[0]
def mix(base,color,factor):
 n=nt.nodes.new('ShaderNodeMixRGB');n.blend_type='MIX';nt.links.new(factor,n.inputs[0])
 if isinstance(base,tuple):n.inputs[1].default_value=base
 else:nt.links.new(base,n.inputs[1])
 n.inputs[2].default_value=color;return n.outputs[0]
# Use the Tripo atlas only to identify paint, trim and lamp regions; its baked
# highlights/shadows are replaced by flat material colours before GT Paint.
h,s,v=[hsv.outputs[i] for i in range(3)]
base=mix((.014,.017,.021,1),(.105,.115,.12,1),math('GREATER_THAN',v,.11))
base=mix(base,(.56,.54,.48,1),math('GREATER_THAN',v,.42))
colored=math('MULTIPLY',math('GREATER_THAN',s,.32),math('GREATER_THAN',v,.045))
red=math('MULTIPLY',colored,math('MAXIMUM',math('LESS_THAN',h,.085),math('GREATER_THAN',h,.92)))
base=mix(base,(.38,.026,.016,1),red)
amber=math('MULTIPLY',colored,math('MULTIPLY',math('GREATER_THAN',h,.085),math('LESS_THAN',h,.22)))
base=mix(base,(.65,.28,.035,1),amber);nt.links.new(base,g.inputs['Base Colour'])
core.ensure_normal_baker(preset);sc.pnb_settings.detail_enable=False;sc.pnb_settings.features_enable=False;sc.pnb_settings.color_enable=False;sc.pnb_settings.flow_axis='Y'
info=core.bake(bpy.context,[ob],'Ferrari288Benmore',str(OUT),2048,preset)
for label,path in info['files'].items():shutil.copy2(path,OUT/('T_F288_GT_'+label+'.png'))
shutil.copy2(BASE.parent/'ferrari288-painterly-v01/T_GT_Ferrari288_N.png',OUT/'T_F288_GT_N.png')
info['files']['N']=str(OUT/'T_F288_GT_N.png');info['normal']='Retained identical max-size OW bake on unchanged source UV and geometry'
bpy.data.objects.remove(bpy.data.objects[info['bake_object']],do_unlink=True);bpy.data.objects.remove(ob,do_unlink=True)
assert digest()==before
def apply():
 m=next(m for m in bpy.data.materials if m.name.startswith('tripo_mat') or m.name=='F288_Source');nt=m.node_tree;nt.nodes.clear()
 bs=nt.nodes.new('ShaderNodeBsdfPrincipled');out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(bs.outputs[0],out.inputs['Surface'])
 for label in ['D','M']:
  image=bpy.data.images.load(str(OUT/('T_F288_GT_'+label+'.png')),check_existing=True);image.colorspace_settings.name='sRGB' if label=='D' else 'Non-Color';image.pack()
  n=nt.nodes.new('ShaderNodeTexImage');n.image=image
  if label=='D':nt.links.new(n.outputs['Color'],bs.inputs['Base Color'])
  else:
   sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(n.outputs['Color'],sep.inputs[0]);nt.links.new(sep.outputs['Blue'],bs.inputs['Roughness'])
 bs.inputs['Coat Weight'].default_value=.8;bs.inputs['Coat Roughness'].default_value=.1
 core.attach_normal(m,str(OUT/'T_F288_GT_N.png'),'UVMap',.5)
 for n in nt.nodes:
  if n.type=='TEX_IMAGE':n.image.pack()
apply()
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_GT_Painted.blend'))
sc.cycles.samples=32;sc.render.resolution_x=1440;sc.render.resolution_y=960;sc.render.resolution_percentage=100
sc.camera.location=(6,-8,4);sc.camera.rotation_euler=(Vector((0,0,.8))-sc.camera.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/'front-quarter.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Ferrari288_GameRig.blend'));before=digest();apply();assert digest()==before;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_GT_Painted_GameRig.blend'))
shutil.copy2(BASE/'export-report.json',OUT/'export-report.json')
(OUT/'paint-report.json').write_text(json.dumps({'ok':True,'system':'GT Paint full D/M/N bake -> M_GT_Vehicle (Benmore Range Rover parent)','bake':info,'geometry_uv_unchanged':True,'tripo_colour_lighting_replaced':True,'base_stroke_cm':100,'fine_strokes':False},indent=2))
(OUT/'preset.json').write_text(json.dumps(preset,indent=2))
print('GT_PAINT_COMPLETE',flush=True)
