import bpy,math,json
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import barycentric_transform
from mathutils.bvhtree import BVHTree
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v06')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v07');OUT.mkdir(exist_ok=True)
assert not (OUT/'Prado_Cabin.blend').exists(),'Saved revision protected'
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Prado_Cabin.blend'));sc=bpy.context.scene
with bpy.data.libraries.load('C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04/Prado_Exterior.blend',link=False) as (src,dst):dst.objects=['Prado | source-fitted body']
ref=dst.objects[0];sc.collection.objects.link(ref);ref.parent=None;ref.hide_render=True
dg=bpy.context.evaluated_depsgraph_get();ev=ref.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles()
verts=[v.co.copy() for v in me.vertices];tris=[list(t.vertices) for t in me.loop_triangles];loops=[list(t.loops) for t in me.loop_triangles]
normals=[n.vector.copy() for n in me.corner_normals];tree=BVHTree.FromPolygons(verts,tris,all_triangles=True)
checks=[]
for ob in [o for o in sc.objects if o.name.startswith('Door |') or o.name in ['Prado | fixed shell and underbody','Bonnet | original surface']]:
 for mod in list(ob.modifiers):
  if mod.type in ['DATA_TRANSFER','WEIGHTED_NORMAL']:ob.modifiers.remove(mod)
 result=[Vector((0,0,1))]*len(ob.data.loops);distances=[]
 for p in ob.data.polygons:
  for li in p.loop_indices:
   pos=ob.data.vertices[ob.data.loops[li].vertex_index].co
   q=pos.lerp(p.center,.0001);nearest,_,ti,dist=tree.find_nearest(q);ids=tris[ti];ns=loops[ti]
   result[li]=barycentric_transform(nearest,*(verts[i] for i in ids),*(normals[i] for i in ns)).normalized()
   distances.append(dist)
 ob.data.normals_split_custom_set(result);ob.data.update()
 checks.append({'object':ob.name,'max_source_surface_distance_m':max(distances)})
ev.to_mesh_clear();bpy.data.objects.remove(ref,do_unlink=True)
for ob in list(bpy.data.objects):
 if ob.name=='REFERENCE | exterior normals only':bpy.data.objects.remove(ob,do_unlink=True)
(OUT/'surface-preservation.json').write_text(json.dumps(checks,indent=2))

# Keep material roughness in the stylized range; glass remains physically transparent.
glass=bpy.data.materials['Prado | Glass'];p=glass.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value=(.93,.97,.98,1);p.inputs['Transmission Weight'].default_value=1;p.inputs['Roughness'].default_value=.055;p.inputs['IOR'].default_value=1.45
sc.render.engine='BLENDER_WORKBENCH';cam=sc.camera
def render(n,c,d,scale=1.2):
 center=Vector(c)*5;cam.data.type='ORTHO';cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*5;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for n,d in [('side',(3,0,0)),('opposite-side',(-3,0,0)),('quarter',(2,-3,1.1)),('rear-quarter',(-2,3,1)),('underside',(1,-1,-2))]:render(n,(0,0,.27),d)
hidden=[]
for ob in sc.objects:
 if ob.type=='MESH' and all(c.name not in ['12 Cabin structure','13 Seats','14 Dashboard','15 Controls','16 Cabin trim'] for c in ob.users_collection) and not ob.hide_render:hidden.append(ob);ob.hide_render=True
head=bpy.data.objects['CAB | Headliner'];head.hide_render=True
rooftrim=[o for o in sc.objects if any(k in o.name for k in ['Sun visor','Visor hinge','Interior lamp','Rear mirror stalk','Interior mirror'])]
for ob in rooftrim:ob.hide_render=True
render('interior-cutaway',(0,.065,.255),(2,1.6,2),.76)
seats=list(bpy.data.collections['13 Seats'].objects)
for ob in seats:ob.hide_render=True
render('dashboard',(0,-.11,.282),(.3,3,1.6),.37)
for ob in seats+hidden+rooftrim:ob.hide_render=False
head.hide_render=False
# Save working scene before studio lighting and ground are added.
render('quarter',(0,0,.27),(2,-3,1.1))
for area in bpy.context.screen.areas if bpy.context.screen else []:
 if area.type=='VIEW_3D':area.spaces.active.shading.type='SOLID'
sc['asset_status']='Fitted four-seat interior and separated door/bonnet skins; source surface preserved; static review, not game ready'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Cabin.blend'))

# A separate saved review scene keeps studio objects out of the vehicle asset.
studio=bpy.data.collections.new('STUDIO - review only');sc.collection.children.link(studio)
def area(n,loc,power,size):
 dat=bpy.data.lights.new(n,'AREA');dat.energy=power;dat.shape='DISK';dat.size=size
 ob=bpy.data.objects.new(n,dat);studio.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,1.2))-ob.location).to_track_quat('-Z','Y').to_euler()
area('Key softbox',(4,-5,7),1800,5);area('Fill softbox',(-4,-1,5),1600,5);area('Rear softbox',(1,5,6),2000,4)
world=bpy.data.worlds.new('Studio world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.62,.7,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;sc.world=world
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.035));ground=bpy.context.object;ground.name='STUDIO ground'
for col in list(ground.users_collection):col.objects.unlink(ground)
studio.objects.link(ground);m=bpy.data.materials.new('Studio ground');m.diffuse_color=(.16,.18,.19,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color;ground.data.materials.append(m)
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.cycles.max_bounces=10;sc.cycles.transmission_bounces=8
sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
render('lit-exterior',(0,0,.27),(2,-3,1.1))
render('glass-cabin-close',(.045,-.055,.347),(2,-3,1.0),.53)
# Driver eye view must show the actual installed dashboard with all panels present.
cam.data.type='PERSP';cam.data.lens=21;cam.location=Vector((.085,.035,.382))*5;target=Vector((.06,-.18,.29))*5;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/'driver-view.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Studio_Review.blend'))
