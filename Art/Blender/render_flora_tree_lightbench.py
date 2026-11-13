"""Author-version source tree and neutral receivers. Never save the purchased file."""
import bpy,json,math,hashlib,traceback,sys,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTreeLightBench'
S=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend')
F=R/'Art/Export/LidarStudy/FloraGroup/Bark/SM_Exact_tree.fbx'
version='blender34' if bpy.app.version<(4,0,0) else 'blender51'
out=O/version;out.mkdir(parents=True,exist_ok=True)
report={'ok':False,'version':bpy.app.version_string,'images':[],'source_hash':hashlib.sha256(S.read_bytes()).hexdigest(),'fbx_hash':hashlib.sha256(F.read_bytes()).hexdigest()}
recipe={'size':768,'fov':40,'space':'Blender metres; Unreal (x,-y,z)*100','cases':[]}
def save():(out/'report.json').write_text(json.dumps(report,indent=2))
def diffuse(name):
 m=bpy.data.materials.new(name);m.use_nodes=True;t=m.node_tree;t.nodes.clear();n=t.nodes.new('ShaderNodeBsdfDiffuse');n.inputs['Color'].default_value=(.18,.18,.18,1);n.inputs['Roughness'].default_value=0
 t.links.new(n.outputs[0],t.nodes.new('ShaderNodeOutputMaterial').inputs['Surface']);return m
def render(name):
 s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32';s.render.filepath=str(out/(name+'.exr'));bpy.ops.render.render(write_still=True)
 im=bpy.data.images.load(s.render.filepath,check_existing=False);px=np.empty(768*768*4,dtype=np.float32);im.pixels.foreach_get(px);px.reshape(768,768,4)[::-1].tofile(str(out/(name+'.f32')));bpy.data.images.remove(im)
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_depth='8';s.render.image_settings.color_mode='RGBA';bpy.data.images['Render Result'].save_render(str(out/(name+'.png')),scene=s)
 report['images'].append(name);save();print('TREE_BENCH',version,name,flush=True)
try:
 bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False);s=bpy.context.scene
 report['source_display']={k:getattr(s.view_settings,k) for k in ['view_transform','look','exposure','gamma']}
 mats={k:bpy.data.materials[k] for k in ['Wood_material','Leaf_0']}
 for m in mats.values():m.use_fake_user=True
 for im in bpy.data.images:
  if im.source=='FILE':
   p=S.parent/'textures'/Path(im.filepath.replace('\\','/')).name
   if p.is_file():im.filepath=str(p);im.reload()
 for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
 bpy.ops.import_scene.fbx(filepath=str(F),use_anim=False)
 ob=next(o for o in bpy.context.selected_objects if o.type=='MESH');ob.name='Parity_tree';bpy.context.view_layer.objects.active=ob
 indices=[p.material_index for p in ob.data.polygons];slots=[next(k for k in mats if m.name==k or m.name.startswith(k+'.') or m.name.startswith(k+'_')) for m in ob.data.materials]
 ob.data.materials.clear()
 for k in slots:ob.data.materials.append(mats[k])
 for p,i in zip(ob.data.polygons,indices):p.material_index=i
 ob.data.uv_layers.active_index=0
 for m in mats.values():
  for n in m.node_tree.nodes:
   if n.type=='UVMAP':n.uv_map=ob.data.uv_layers[0].name
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 lo=Vector(tuple(min(v.co[j] for v in ob.data.vertices) for j in range(3)));hi=Vector(tuple(max(v.co[j] for v in ob.data.vertices) for j in range(3)))
 scale=2/(hi.z-lo.z);location=Vector((-(lo.x+hi.x)*.5*scale,-(lo.y+hi.y)*.5*scale,-lo.z*scale));ob.scale=(scale,)*3;ob.location=location
 recipe.update(scale=scale,location=list(location),bounds=[list(lo),list(hi)],fbx=str(F),materials=slots)
 leaf=mats['Leaf_0'];group=next(n for n in leaf.node_tree.nodes if n.type=='GROUP' and n.node_tree.name.startswith('Flora_Shader'))
 # The source group has three sockets named Soft; preserve identities by index.
 report['leaf_inputs']=[{'index':i,'name':x.name,'value':list(x.default_value) if hasattr(x.default_value,'__len__') else x.default_value} for i,x in enumerate(group.inputs) if hasattr(x,'default_value')]
 report['mesh']={'vertices':len(ob.data.vertices),'polygons':len(ob.data.polygons),'uv_channels':len(ob.data.uv_layers)}
 s.use_nodes=False;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.film_transparent=False
 s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1;s.eevee.taa_render_samples=128
 if hasattr(s.eevee,'use_gtao'):s.eevee.use_gtao=False
 if hasattr(s.eevee,'use_bloom'):s.eevee.use_bloom=False
 w=bpy.data.worlds.new('TreeBenchWorld');w.use_nodes=True;s.world=w;bg=w.node_tree.nodes.get('Background')
 grey=diffuse('TreeBenchGrey');bpy.ops.mesh.primitive_plane_add(size=20);floor=bpy.context.object;floor.data.materials.append(grey)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=.65,location=(0,0,.75));chart=bpy.context.object;chart.data.materials.append(grey);chart.hide_render=True
 data=bpy.data.lights.new('TreeBenchSun','SUN');data.angle=math.radians(.5);sun=bpy.data.objects.new('TreeBenchSun',data);s.collection.objects.link(sun)
 c=bpy.data.cameras.new('TreeBenchCamera');camera=bpy.data.objects.new('TreeBenchCamera',c);s.collection.objects.link(camera);s.camera=camera;c.sensor_width=36;c.lens=36/(2*math.tan(math.radians(20)));c.clip_start=.01;c.clip_end=100
 pos=Vector((0,-3.6,1.55));target=Vector((0,0,1.05));camera.location=pos;camera.rotation_euler=(target-pos).to_track_quat('-Z','Y').to_euler()
 cases=[('front',[-.3,-.8,1],3,[1,1,1],[1,1,1],.8),('side',[1,0,.65],3,[1,1,1],[1,1,1],.8),('back',[.3,.8,.7],3,[1,1,1],[1,1,1],.8),('sky',[0,0,1],0,[1,1,1],[.58,.74,1],.8),('warm',[-.3,-.8,.65],3,[1,.814,.539],[.58,.74,1],.8),('sun_only',[-.3,-.8,1],3,[1,1,1],[1,1,1],0)]
 for name,direction,energy,colour,sky,ambient in cases:
  ray=-Vector(direction).normalized();sun.rotation_euler=ray.to_track_quat('-Z','Y').to_euler();data.energy=energy;data.color=colour;bg.inputs['Color'].default_value=(*sky,1);bg.inputs['Strength'].default_value=ambient
  recipe['cases'].append(dict(name=name,camera=list(pos),target=list(target),sun_ray=list(ray),sun_energy=energy,sun_colour=colour,sky_colour=sky,sky_strength=ambient))
  ob.hide_render=False;chart.hide_render=True;render('tree_'+name)
  ob.hide_render=True;chart.hide_render=False;render('chart_'+name)
 # Isolate the light lobe from the two renderers' shadow-map behaviour.
 data.use_shadow=False;ob.hide_render=False;chart.hide_render=True;render('tree_sun_unshadowed');data.use_shadow=True
 # Retain a source diagnostic for coverage/pigment, not used as beauty imagery.
 ob.hide_render=False;chart.hide_render=True;floor.hide_render=True;data.energy=0;bg.inputs['Strength'].default_value=0
 sys.path.insert(0,str(R/'Art/Blender'));from flora_pigment_check import render_pigment
 oldrecipe={'cases':recipe['cases'],'assets':[{'key':'tree'}]}
 render_pigment(s,[ob],oldrecipe,render);render_pigment(s,[ob],oldrecipe,render,white=True)
 if version=='blender34':(O/'recipe.json').write_text(json.dumps(recipe,indent=2))
 assert hashlib.sha256(S.read_bytes()).hexdigest()==report['source_hash']
 report.update(ok=True,source_unchanged=True,display='Standard / None / exposure 0 / gamma 1',source_materials_unchanged=True);save()
except Exception:report['error']=traceback.format_exc();save();raise
