"""Blender preparation and review setup. Intentionally performs no asset export."""
# Discard hidden historical source objects from the delivery scene; source files remain intact.
owned=set(o for c in COL.values() for o in c.objects)
bpy.context.view_layer.update()
saved_world={o:o.matrix_world.copy() for o in owned}
for o,mw in saved_world.items():o.parent=None;o.matrix_world=mw
bpy.context.view_layer.update()
for o in list(bpy.data.objects):
 if o not in owned and o.type not in {'CAMERA','LIGHT'}:delete(o)
for o in list(sc.objects):
 if o.type in {'CAMERA','LIGHT'}:move(o,STUDIO)
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1.0
def empty(n,p=(0,0,0),c=RIG):
 o=bpy.data.objects.new(n,None);c.objects.link(o);o.location=p;o.empty_display_size=.11;o.empty_display_type='PLAIN_AXES';return o
root=empty('Porsche | ROOT');root['steering_degrees']=0.;root['wheel_roll_degrees']=0.;root['suspension_m']=0.;root['headlamps']=0.
root.id_properties_ui('steering_degrees').update(min=-22,max=22);root.id_properties_ui('wheel_roll_degrees').update(min=-360,max=360);root.id_properties_ui('suspension_m').update(min=-.025,max=.015);root.id_properties_ui('headlamps').update(min=0,max=1)
emission=lampemit.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'];d=emission.driver_add('default_value').driver;v=d.variables.new();v.name='lights';v.targets[0].id=root;v.targets[0].data_path='["headlamps"]';d.expression='lights*4'
def parent(o,p):
 bpy.context.view_layer.update();mw=o.matrix_world.copy();o.parent=p;o.matrix_parent_inverse=p.matrix_world.inverted();o.matrix_world=mw;bpy.context.view_layer.update()
wheel_centres={}
for tag in ['FL','FR','RL','RR']:
 obs=[o for o in GEAR.objects if o.name.startswith('Wheel_'+tag)];pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices];center=Vector([(max(p[k] for p in pts)+min(p[k] for p in pts))/2 for k in range(3)]);wheel_centres[tag]=list(center)
 sus=empty('Suspension | '+tag,center);parent(sus,root);steer=empty('Steer | '+tag,center);parent(steer,sus);roll=empty('Roll | '+tag,center);parent(roll,steer)
 for ob in obs:parent(ob,roll)
 for ob,prop,index,expression in [(sus,'location',2,str(center.z)+'+s'),(steer,'rotation_euler',2,'s*pi/180' if tag.startswith('F') else '0*s'),(roll,'rotation_euler',0,'s*pi/180')]:
  d=ob.driver_add(prop,index).driver;d.type='SCRIPTED';v=d.variables.new();v.name='s';v.type='SINGLE_PROP';v.targets[0].id=root;v.targets[0].data_path='["'+('suspension_m' if ob==sus else 'steering_degrees' if ob==steer else 'wheel_roll_degrees')+'"]';d.expression=expression
for c in [EXT,GLASS,INT,KIT,GEAR]:
 for o in c.objects:
  if o.parent is None:parent(o,root)
# Local steering-wheel control follows the vehicle control, independently editable.
sw=empty('Steering wheel | pivot',wheel_center);parent(sw,root)
for o in steerpieces:parent(o,sw)
sw.rotation_mode='AXIS_ANGLE';sw.rotation_axis_angle=(0,*axis)
d=sw.driver_add('rotation_axis_angle',0).driver;v=d.variables.new();v.name='steer';v.targets[0].id=root;v.targets[0].data_path='["steering_degrees"]';d.expression='-steer*pi/180*12'
report['wheel_centres_m']=wheel_centres
# Simple convex vehicle collision pieces, separate and disabled in beauty views.
for n,p,size in [('Lower body',(0,.03,.60),(1.42,3.72,.38)),('Cabin',(0,.28,1.10),(1.30,1.56,.68)),('Front protection',(0,-2.17,.46),(1.67,.12,.26)),('Rear bumper',(0,2.08,.56),(1.66,.14,.19))]:
 o=box('UCX_Porsche_'+n.replace(' ','_'),p,size,rubber,COLL,.035);o.display_type='WIRE';o.hide_render=True;parent(o,root)
COLL.hide_viewport=True;COLL.hide_render=True
# UV0 exists on all visible meshes. Generate charts only where UVs were absent.
uvmade=[];bad=[]
for c in [EXT,GLASS,INT,GEAR,KIT]:
 for o in list(c.objects):
  if o.type!='MESH':continue
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0000002);loose=[v for v in bm.verts if not v.link_faces]
  if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
  over=[e for e in bm.edges if len(e.link_faces)>2]
  if over:bmesh.ops.split_edges(bm,edges=over)
  bm.to_mesh(o.data);bm.free()
  if not o.data.polygons:bad.append(o.name);continue
  if not o.data.uv_layers:
   active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.05,island_margin=.02,area_weight=.25,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT');uvmade.append(o.name)
  o['asset_part']=c.name;o['review_revision']='completion-v04'
active(body);md=body.modifiers.new('Balanced body-panel shading','WEIGHTED_NORMAL');md.keep_sharp=True;md.weight=35;bpy.ops.object.modifier_apply(modifier=md.name)
report['new_uv_charts']=len(uvmade)
for n in bad:delete(bpy.data.objects[n])
# Low-detail variants are separate hidden collections, never overlaid on LOD0.
for level,ratio in [(1,.48),(2,.20)]:
 col=bpy.data.collections.new('LOD'+str(level)+' | preview');sc.collection.children.link(col)
 for src in [o for c in [EXT,GLASS,INT,GEAR,KIT] for o in c.objects if o.type=='MESH']:
  lo,hi=bounds(src)
  if level==2 and (hi-lo).length<.10:continue
  if level==1 and len(src.data.polygons)<80:continue
  ob=src.copy();ob.data=src.data.copy();col.objects.link(ob);ob.name='LOD'+str(level)+' | '+src.name
  if len(ob.data.polygons)>100:
   active(ob);md=ob.modifiers.new('LOD simplification','DECIMATE');md.ratio=ratio;md.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=md.name)
 col.hide_render=True;col.hide_viewport=True
# Review cameras and non-exported studio lighting.
for o in list(STUDIO.objects):
 if o.type=='LIGHT':delete(o)
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.26,.31,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.45
for n,p,power,size in [('Key',(3,-4,6),1300,5),('Fill',(-4,-2,4),1000,4),('Rim',(0,5,5),1500,4)]:
 d=bpy.data.lights.new(n,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(n,d);STUDIO.objects.link(o);o.location=p;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
cam=sc.camera;cam.data.type='ORTHO';sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_cavity=False;sc.display.shading.show_shadows=True;sc.display.shading.show_specular_highlight=True;sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
def render(n,p,target,scale):
 cam.location=p;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for n,p,t,scale in [('quarter',(5,-7,3.5),(0,0,.90),5.5),('rear',(5,7,3.5),(0,0,.90),5.5),('side',(7,0,.9),(0,0,.9),5.5),('front',(0,-7,.9),(0,0,.9),3.2),('top',(0,0,8),(0,0,.9),5.5),('front-detail',(3,-4,1.65),(.45,-1.78,.72),1.9),('rear-detail',(3,4,1.7),(0,1.68,.8),2.8)]:render(n,p,t,scale)
# Interior presentation explicitly hides the shell and exterior only for cutaway views.
hidden=[]
for c in [EXT,GLASS,KIT,GEAR]:
 for o in c.objects:
  if not o.hide_render:hidden.append(o);o.hide_render=True
for o in INT.objects:
 if 'headliner' in o.name or 'aperture return' in o.name or 'sun visor' in o.name or 'visor bracket' in o.name:
  hidden.append(o);o.hide_render=True
render('interior-cutaway',(3,2,3),(0,.08,.83),2.55)
render('dashboard',(.15,.075,1.32),(.10,-.42,.98),1.65)
render('seats',(-2,-2,2.6),(0,.34,.85),2.45)
for o in hidden:o.hide_render=False
for o in GEAR.objects:
 if o.name.startswith('Wheel_'):o.hide_render=True
render('wheelhouses',(4,-3,.9),(.5,-.4,.7),4.4)
render('underside',(3,-4,-4),(0,0,.55),5.5)
for o in GEAR.objects:o.hide_render=False
cam.location=(5,-7,3.5);cam.rotation_euler=(Vector((0,0,.90))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5.5
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':
   sp=a.spaces.active;sp.overlay.show_overlays=False;sp.shading.type='SOLID';sp.shading.color_type='MATERIAL';sp.region_3d.view_location=Vector((0,0,.90));sp.region_3d.view_distance=6;sp.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
active(root);bpy.ops.wm.save_as_mainfile(filepath=str(DEST));report['blend_sha256']=hashlib.sha256(DEST.read_bytes()).hexdigest();report['status']='Built; independent fit/movement and visual review in progress';MAN.write_text(json.dumps(report,indent=2));print('SAVED',str(DEST),flush=True)
