"""Read-only original shader audit and FBX-roundtrip reference in Blender 3.4.1."""
import bpy,json,sys,math,hashlib,traceback
from pathlib import Path
from mathutils import Vector
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/PineMatch';O.mkdir(parents=True,exist_ok=True)
P=R/'Art/Export/FloraTrail/PineTrial';data=json.loads((P/'export-report.json').read_text());S=Path(data['source'])
sys.path.insert(0,str(R/'Art/Blender'))
report={'ok':False,'images':[],'source_hash':hashlib.sha256(S.read_bytes()).hexdigest(),'version':bpy.app.version_string}
def save():(O/'source-report.json').write_text(json.dumps(report,indent=2))
def render(name):
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True);report['images'].append(name);save()
def val(v):
 try:return list(v)
 except TypeError:return v
try:
 assert bpy.app.version[:2]==(3,4)
 bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False);s=bpy.context.scene
 source=bpy.data.objects['FP_Tree_F_002'];mats=list(source.data.materials)
 for m in mats:m.use_fake_user=True
 graphs={}
 def graph(t,root=None):
  key=root or t.name
  if key in graphs:return
  graphs[key]={'nodes':[{'name':n.name,'type':n.type,'operation':getattr(n,'operation',None),'inputs':[{'name':x.name,'index':i,'value':val(x.default_value) if hasattr(x,'default_value') else None,'linked':x.is_linked} for i,x in enumerate(n.inputs)],'group':n.node_tree.name if n.type=='GROUP' and n.node_tree else None} for n in t.nodes],'links':[[l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name] for l in t.links]}
  for n in t.nodes:
   if n.type=='GROUP' and n.node_tree:graph(n.node_tree)
 for m in mats:graph(m.node_tree,m.name)
 (O/'source-graphs.json').write_text(json.dumps(graphs,indent=2))
 for im in bpy.data.images:
  if im.source=='FILE':
   p=S.parent/'textures'/Path(im.filepath.replace('\\','/')).name
   if p.is_file():im.filepath=str(p);im.reload()
 for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
 bpy.ops.import_scene.fbx(filepath=str(P/'meshes/SM_Exact_pine_f002.fbx'),use_anim=False)
 ob=next(x for x in bpy.context.selected_objects if x.type=='MESH');bpy.context.view_layer.objects.active=ob
 report['fbx_material_names']=[m.name for m in ob.data.materials]
 for i,m in enumerate(ob.data.materials):
  family=next(k for k in ('Wood_material','Leaf_0') if m.name.startswith(k))
  matches=[x for x in mats if x.name.startswith(family)];assert len(matches)==1
  ob.data.materials[i]=matches[0]
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);ob.location=(0,0,0)
 ob.data.uv_layers.active_index=0
 for m in mats:
  for n in m.node_tree.nodes:
   if n.type=='UVMAP':n.uv_map=ob.data.uv_layers[0].name
 s.render.engine='BLENDER_EEVEE';s.use_nodes=False;s.render.resolution_x=768;s.render.resolution_y=768;s.render.resolution_percentage=100
 s.eevee.taa_render_samples=128;s.eevee.use_gtao=False;s.eevee.use_bloom=False
 s.render.film_transparent=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='8'
 world=bpy.data.worlds.new('MatchWorld');world.use_nodes=True;s.world=world;bg=world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.58,.74,1,1);bg.inputs['Strength'].default_value=.8
 d=bpy.data.lights.new('MatchSun','SUN');d.energy=16;d.color=(1,.814,.539);d.angle=math.radians(.5)
 sun=bpy.data.objects.new('MatchSun',d);s.collection.objects.link(sun)
 cd=bpy.data.cameras.new('MatchCamera');cam=bpy.data.objects.new('MatchCamera',cd);s.collection.objects.link(cam);s.camera=cam
 src=data['source_camera'];cd.lens=45;cam.location=src['position'];cam.rotation_euler=(Vector(src['target'])-cam.location).to_track_quat('-Z','Y').to_euler()
 recipe={'size':768,'camera':src,'cases':[{'name':'warm','ray':[-.233908564,.810244143,-.537392974]},{'name':'side','ray':list(Vector((-.85,0,-.53)).normalized())},{'name':'back','ray':[.233908564,-.810244143,-.537392974]}]}
 for case in recipe['cases']:
  sun.rotation_euler=Vector(case['ray']).to_track_quat('-Z','Y').to_euler();render('source_'+case['name'])
 # Same view, native source transparency; remove illumination only diagnostically.
 from flora_pigment_check import render_pigment
 r={'cases':[{'camera':src['position'],'target':src['target']}],'assets':[{'key':'source'}]}
 render_pigment(s,[ob],r,render);render_pigment(s,[ob],r,render,white=True)
 recipe['bounds']=[[min(v.co[j] for v in ob.data.vertices) for j in range(3)],[max(v.co[j] for v in ob.data.vertices) for j in range(3)]]
 (O/'recipe.json').write_text(json.dumps(recipe,indent=2))
 report.update(ok=True,source_unchanged=hashlib.sha256(S.read_bytes()).hexdigest()==report['source_hash']);save()
except Exception:report['error']=traceback.format_exc();save();raise
