import bpy, json, hashlib, struct, shutil
from pathlib import Path
from mathutils import Vector
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/panda-interior-v01')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/panda-interior-v02')
OUT.mkdir(exist_ok=True)
if (OUT/'delivery-manifest.json').exists(): raise RuntimeError('Protected delivery')
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Panda_Assembly.blend'))
sc=bpy.context.scene
def geometry():
 result={}
 for o in sc.objects:
  if o.type!='MESH':continue
  h=hashlib.sha256()
  for row in o.matrix_world:h.update(struct.pack('4f',*row))
  for v in o.data.vertices:h.update(struct.pack('3f',*v.co))
  for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
  result[o.name]=h.hexdigest()
 return result
before=geometry()
m=bpy.data.materials['Panda | Glass'];p=m.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value=(.94,.98,1,1)
p.inputs['Roughness'].default_value=.018
p.inputs['Transmission Weight'].default_value=1
p.inputs['IOR'].default_value=1.45
p.inputs['Alpha'].default_value=1
m.diffuse_color=(.94,.98,1,1)
m.use_raytrace_refraction=True
sc.eevee.use_raytracing=True
sc.render.engine='CYCLES';sc.cycles.preview_samples=16;sc.cycles.use_preview_denoising=True
sc.cycles.max_bounces=12;sc.cycles.transmission_bounces=8
sc.world.use_nodes=True
sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.6,.68,1)
sc.world.node_tree.nodes['Background'].inputs[1].default_value=.4
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.shading.type='RENDERED'
bpy.ops.object.select_all(action='DESELECT')
for o in sc.objects:
 if o.type in ['MESH','EMPTY'] and not o.name.startswith('SOURCE'):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Panda_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Panda_Assembly.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.object.select_all(action='DESELECT')
assert before==geometry(),'Unexpected geometry change'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda_Assembly.blend'))
data=(OUT/'Panda_Assembly.glb').read_bytes();ln,typ=struct.unpack_from('<II',data,12);gltf=json.loads(data[20:20+ln])
gm=next(x for x in gltf['materials'] if x['name']=='Panda | Glass')
assert gm['extensions']['KHR_materials_transmission']['transmissionFactor']==1
report={'source':str(SRC),'unchanged_meshes_and_transforms':len(before),'changed_material':'Panda | Glass','glass_objects':[o.name for o in sc.objects if o.type=='MESH' and m.name in o.data.materials],'glb_glass_material':gm,'geometry_unchanged':True,'validation_scope':'Material correction only; geometry checks inherited from unchanged v01 assembly. Unreal glass material not tested.'}
(OUT/'glazing-verification.json').write_text(json.dumps(report,indent=2))
shutil.copy2(SRC/'vehicle-spec.json',OUT/'vehicle-spec.json')
shutil.copy2(__file__,OUT/'fix_panda_glazing.py')
(OUT/'README.txt').write_text('Panda interior v02: clear glazing. Full transmission, near-neutral tint, roughness 0.018. Opens in Cycles Rendered viewport because Solid mode is opaque. Geometry and transforms unchanged from v01. GLB transmission extension checked. FBX material translation and Unreal translucency still require engine-side setup. Review props are render-only and are not in the model.\n')
# Review-only lighting and striped posts beyond the windscreen demonstrate actual visibility.
sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.threads_mode='FIXED';sc.render.threads=10
sc.render.resolution_x=1200;sc.render.resolution_y=860;sc.render.resolution_percentage=100
for name,pos,e,size in [('Key',(3,-4,6),1300,4),('Fill',(-3,0,4),850,3),('Back',(1,4,5),1200,3),('Cabin',(0,.35,1.54),18,1)]:
 d=bpy.data.lights.new('Review '+name,'AREA');d.energy=e;d.shape='DISK';d.size=size;o=bpy.data.objects.new(d.name,d);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.7))-o.location).to_track_quat('-Z','Y').to_euler()
def mat(name,c):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1);return m
orange=mat('Review orange',(.85,.17,.025));white=mat('Review white',(.8,.8,.8));grey=mat('Review floor',(.16,.18,.2))
props=[]
for x in [-1.15,0,1.15]:
 for k in range(8):
  bpy.ops.mesh.primitive_cube_add(size=1,location=(x,-4.8,.1+k*.2));o=bpy.context.object;o.scale=(.18,.18,.2);o.data.materials.append(orange if k%2 else white);props.append(o)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));bpy.context.object.data.materials.append(grey);props.append(bpy.context.object)
cam=sc.camera;cam.data.clip_start=.008
def render(name,pos,target,lens=23,ortho=None):
 cam.location=Vector(pos)*3.6;cam.rotation_euler=(Vector(target)*3.6-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO' if ortho else 'PERSP';cam.data.lens=lens
 if ortho:cam.data.ortho_scale=ortho*3.6
 sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('windscreen-inside',(.096,.054,.410),(.03,-.5,.34),lens=22)
for o in props:o.hide_render=True
render('windscreen-outside',(.55,-1.0,.65),(0,-.06,.34),lens=48)
render('exterior',(1.7,-2.7,1.30),(0,0,.26),ortho=1.3)
print('GLAZING_COMPLETE',flush=True)
