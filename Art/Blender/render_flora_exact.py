"""Original Eevee materials on the exact existing imported FBXs; no source save."""
import bpy,json,math,hashlib,traceback,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraParity/AssetMatch';P=R/'Art/Export/LidarStudy/FloraPath'
S=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend')
(O/'blender').mkdir(parents=True,exist_ok=True)
import sys
sys.path.insert(0,str(R/'Art/Blender'))
from bake_flora_exact import bake_assets
report={'ok':False,'images':[],'assets':[]};recipe={'schema':1,'size':512,'fov':50,'assets':[],'cases':[],'space':'Blender metres; UE=(x,-y,z)*100'}
def save():(O/'reference-report.json').write_text(json.dumps(report,indent=2))
def material(name,c):
 m=bpy.data.materials.new(name);m.use_nodes=True;t=m.node_tree;t.nodes.clear();d=t.nodes.new('ShaderNodeBsdfDiffuse');d.inputs['Color'].default_value=(*c,1);d.inputs['Roughness'].default_value=0
 out=t.nodes.new('ShaderNodeOutputMaterial');t.links.new(d.outputs[0],out.inputs['Surface']);return m
def render(name):
 s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_depth='32';s.render.filepath=str(O/'blender'/(name+'.exr'))
 bpy.ops.render.render(write_still=True)
 im=bpy.data.images.load(s.render.filepath,check_existing=False);px=np.empty(512*512*4,dtype=np.float32);im.pixels.foreach_get(px);px.reshape(512,512,4)[::-1].tofile(str(O/'blender'/(name+'.f32')));bpy.data.images.remove(im)
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8';bpy.data.images['Render Result'].save_render(str(O/'blender'/(name+'.png')),scene=s)
 report['images'].append(name);save();print('PARITY_REFERENCE',name,flush=True)
try:
 bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False);s=bpy.context.scene
 source_mats={m.name:m for m in bpy.data.materials}
 for m in source_mats.values():m.use_fake_user=True
 for im in bpy.data.images:
  if im.source=='FILE':
   p=S.parent/'textures'/Path(im.filepath.replace('\\','/')).name
   if p.is_file():im.filepath=str(p);im.reload()
 for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
 s.use_nodes=False;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=s.render.resolution_y=512;s.render.resolution_percentage=100
 s.render.film_transparent=False;s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8'
 s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
 if hasattr(s,'eevee'):s.eevee.taa_render_samples=64
 w=bpy.data.worlds.new('ParityWorld');w.use_nodes=True;s.world=w;bg=w.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(1,1,1,1);bg.inputs['Strength'].default_value=0
 objs=[];data=json.loads((P/'scene-manifest.json').read_text())
 for key,meshname in [('fern','SM_Path_FP_Ferns_021'),('shrub','SM_Path_FP_Blooming_Shrubbery_006'),('tree','SM_Path_FP_Tree_B_001')]:
  row=next(x for x in data['meshes'] if x['name']==meshname)
  bpy.ops.object.select_all(action='DESELECT');bpy.ops.import_scene.fbx(filepath=str(P/(meshname+'.fbx')),use_anim=False)
  ob=next(o for o in bpy.context.selected_objects if o.type=='MESH');ob.name='Parity_'+key
  imported_slots=[m.name if m else '' for m in ob.data.materials]
  polygon_slots=[p.material_index for p in ob.data.polygons]
  slot_names=[]
  for name in imported_slots:
   match=next((n for n in sorted(row['materials'],key=len,reverse=True) if name==n or name.startswith(n+'.')),None)
   assert match,(meshname,name,row['materials']);slot_names.append(match)
  # FBX importers may reorder material slots. Match actual slot names, not index.
  ob.data.materials.clear()
  for n in slot_names:ob.data.materials.append(source_mats[n])
  for polygon,index in zip(ob.data.polygons,polygon_slots):polygon.material_index=index
  # The frozen export intentionally names its source mask UV channel UVMap.
  for m in ob.data.materials:
   for n in m.node_tree.nodes:
    if n.type=='UVMAP':n.uv_map=ob.data.uv_layers[0].name
  # Apply only the FBX axis transform; then normalize all objects to a 2m height.
  bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
  lo=Vector(tuple(min(v.co[j] for v in ob.data.vertices) for j in range(3)));hi=Vector(tuple(max(v.co[j] for v in ob.data.vertices) for j in range(3)))
  scale=2/max(hi.x-lo.x,hi.y-lo.y,hi.z-lo.z);location=Vector((-(lo.x+hi.x)*.5*scale,-(lo.y+hi.y)*.5*scale,-lo.z*scale))
  ob.scale=(scale,)*3;ob.location=location;ob.hide_render=True;objs.append(ob)
  asset=dict(key=key,mesh=meshname,location=list(location),scale=scale,source_bounds=[list(lo),list(hi)],materials=row['materials'],blender_imported_slots=imported_slots,blender_source_slots=slot_names,fbx_sha256=hashlib.sha256((P/(meshname+'.fbx')).read_bytes()).hexdigest(),vertices=len(ob.data.vertices),polygons=len(ob.data.polygons))
  recipe['assets'].append(asset);report['assets'].append(asset)
 bake_assets(s,objs,recipe,O)
 bpy.ops.mesh.primitive_plane_add(size=20);floor=bpy.context.object;floor.name='ParityReceiver';floor.data.materials.append(material('ParityGrey',(.18,.18,.18)))
 light=bpy.data.lights.new('ParitySun','SUN');light.energy=1;light.angle=math.radians(.5);sun=bpy.data.objects.new('ParitySun',light);s.collection.objects.link(sun)
 c=bpy.data.cameras.new('ParityCamera');camera=bpy.data.objects.new('ParityCamera',c);s.collection.objects.link(camera);s.camera=camera;c.lens=36/(2*math.tan(math.radians(25)));c.sensor_width=36;c.clip_start=.01;c.clip_end=100
 target=Vector((0,0,1.0))
 # A diffuse neutral chart object calibrates light/display separately from leaves.
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.65,location=(0,0,.75));chart=bpy.context.object;chart.name='ParityGreySphere';chart.data.materials.append(material('ParityChart',(.18,.18,.18)));chart.hide_render=True
 lights={'front':[-.3,-.8,1.0],'side':[1,0,.65],'back':[.3,.8,.7],'shade':[0,0,1],'warm':[-.8,.2,.35],'coolshade':[0,0,1]}
 for kind,vec in lights.items():
  ray=-Vector(vec).normalized();sun.rotation_euler=ray.to_track_quat('-Z','Y').to_euler();light.energy=0 if kind in ['shade','coolshade'] else 3
  light.color=(1,.72,.42) if kind=='warm' else (1,1,1)
  sky_colour=(.48,.67,1) if kind in ['warm','coolshade'] else (1,1,1)
  bg.inputs['Color'].default_value=(*sky_colour,1)
  bg.inputs['Strength'].default_value=.8
  for angle,deg in [('face',0),('grazing',70)]:
   a=math.radians(deg);pos=Vector((math.sin(a)*3.6,-math.cos(a)*3.6,1.65));camera.location=pos;camera.rotation_euler=(target-pos).to_track_quat('-Z','Y').to_euler()
   for asset,ob in zip(recipe['assets'],objs):
    name=asset['key']+'_'+kind+'_'+angle;recipe['cases'].append(dict(name=name,asset=asset['key'],light=kind,angle=angle,camera=list(pos),target=list(target),sun_ray=list(ray),sun_energy=light.energy,sun_colour=list(light.color),sky_colour=list(sky_colour),sky_strength=bg.inputs['Strength'].default_value))
    ob.hide_render=False;render(name);ob.hide_render=True
   if angle=='face':
    chart.hide_render=False;render('chart_'+kind);chart.hide_render=True
 # Separate lobe response from shadow-map behaviour; original shaders unchanged.
 camera.location=Vector(recipe['cases'][0]['camera']);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 sun.rotation_euler=Vector(recipe['cases'][0]['sun_ray']).to_track_quat('-Z','Y').to_euler();light.energy=3;light.use_shadow=False;bg.inputs['Strength'].default_value=0
 for asset,ob in zip(recipe['assets'],objs):
  ob.hide_render=False;render(asset['key']+'_noshadow_face');ob.hide_render=True
 report['test_light_properties']={k:getattr(light,k,None) for k in ['diffuse_factor','specular_factor','transmission_factor','use_shadow']}
 # An unconnected Thickness socket is not necessarily an explicit zero in Eevee.
 # Diagnose the renderer default separately; never alter the reference materials.
 for asset,ob in zip(recipe['assets'],objs):
  original=list(ob.data.materials)
  for index,m in enumerate(original):
   copy=m.copy();t=copy.node_tree
   zero=t.nodes.new('ShaderNodeValue');zero.outputs[0].default_value=0
   for n in list(t.nodes):
    if n.type=='OUTPUT_MATERIAL':t.links.new(zero.outputs[0],n.inputs['Thickness'])
   ob.data.materials[index]=copy
  ob.hide_render=False;render(asset['key']+'_thinzero_face');ob.hide_render=True
  for index,m in enumerate(original):ob.data.materials[index]=m
 from flora_pigment_check import render_pigment
 render_pigment(s,objs,recipe,render)
 render_pigment(s,objs,recipe,render,white=True)
 (O/'recipe.json').write_text(json.dumps(recipe,indent=2));report.update(ok=True,engine=s.render.engine,view='Standard',source_geometry='Same purchased frozen geometry; source shader outputs baked into new isolated UV atlases; original shader used for reference renders',source_frame=16,limitations=['Diagnostic normalized asset bench, not the full source composition','Per-object random seed differs from original forest placement; the same bench identity is retained for all lighting cases'])
 save()
except Exception:
 report['error']=traceback.format_exc();save();raise

