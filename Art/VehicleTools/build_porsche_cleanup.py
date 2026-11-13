"""Non-destructive Porsche Tripo preparation. Preserves donor UVs and body shape.
No whole-body voxel remesh: it destroys the thin pillars on this donor.
"""
import bpy,bmesh,math,json,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from math import sin,cos,pi
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-source-v01')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-cleanup-v01');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Porsche_Analysed.blend'))
sc=bpy.context.scene;donor=next(o for o in sc.objects if o.type=='MESH')
parts=bpy.data.collections.new('Porsche - separated assembly');sc.collection.children.link(parts)
reference=bpy.data.collections.new('REFERENCE - untouched Tripo');sc.collection.children.link(reference)
for c in list(donor.users_collection):c.objects.unlink(donor)
reference.objects.link(donor);donor.hide_render=True;donor.hide_set(True);donor.name='REFERENCE_Porsche_Tripo'
report={'source':'C:/Users/mille/Downloads/porshceoffroadtripo.glb','scale_m_per_donor_unit':4.5,'body_method':'UV-preserving cleanup; original silhouette retained. Not a complete quad retopology.','parts':[]}
def active(o):
 for x in bpy.context.selected_objects:x.select_set(False)
 o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def mat(n,c,metal=0,rough=.4):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
rubber=mat('Porsche - tyre rubber',(.023,.027,.029),0,.72)
steel=mat('Porsche - graphite steel',(.095,.109,.112),.65,.3)
silver=mat('Porsche - fasteners',(.37,.40,.41),.8,.22)
black=mat('Porsche - underbody',(.018,.022,.024),.15,.6)
glass=mat('Porsche - clear glazing',(.8,.91,.95),0,.045)
gp=glass.node_tree.nodes.get('Principled BSDF');gp.inputs['Transmission Weight'].default_value=1;gp.inputs['IOR'].default_value=1.45
def object_mesh(n,verts,faces,m):
 me=bpy.data.meshes.new(n);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(n,me);parts.objects.link(o)
 if m:me.materials.append(m)
 return o
def finish(o,smooth=True):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 for p in o.data.polygons:p.use_smooth=smooth
 o.data.set_sharp_from_angle(angle=.7)
def bevel(o,w=.0006):
 active(o);m=o.modifiers.new('Rounded edges','BEVEL');m.width=w;m.segments=2;bpy.ops.object.modifier_apply(modifier=m.name);finish(o)
def box(n,loc,size,m,edge=.001):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=n;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for c in list(o.users_collection):c.objects.unlink(o)
 parts.objects.link(o);o.data.materials.append(m)
 if edge:bevel(o,edge)
 return o
def lathe(n,profile,center,m,segments=64):
 vs=[(center[0]+x,center[1]+r*cos(2*pi*j/segments),center[2]+r*sin(2*pi*j/segments)) for x,r in profile for j in range(segments)]
 fs=[(i*segments+j,i*segments+(j+1)%segments,((i+1)%len(profile))*segments+(j+1)%segments,((i+1)%len(profile))*segments+j) for i in range(len(profile)) for j in range(segments)]
 o=object_mesh(n,vs,fs,m);finish(o);return o
names={0:'Body_and_cabin',1:'Rear_axle',2:'Front_bullbar_and_carrier',3:'Suspension_FR',4:'Suspension_FL',5:'Rack_mounts',6:'Wiper_mount_A',7:'Cockpit_controls',8:'Seat_R',9:'Seat_L',10:'Rack_lower_rail',11:'Rack_upper_rail',12:'Wiper_mount_B',13:'Door_handle_R',14:'Mirror_R',15:'Mirror_L',16:'Door_handle_L',17:'Console',18:'Rack_rear_mount',19:'Roof_spare',20:'Exhaust_R',21:'Exhaust_L',22:'Skid_plate',23:'Rack_crossbar_front',24:'Auxiliary_light_R',25:'Auxiliary_light_L',26:'Rack_crossbar_rear',27:'Console_trim',28:'Door_card_R',29:'Door_card_L',30:'Rack_crossbar_middle',31:'Tailpipe_R',32:'Tailpipe_L',33:'Driveshaft',34:'Front_lightbar',35:'Gearlever',36:'Front_undertray',37:'Rear_carrier',38:'Roof_toolcase',49:'Headlamp_R',50:'Headlamp_L'}
for i in range(112):
 me=donor.data.copy();o=bpy.data.objects.new(names.get(i,'Trim_%03d'%i),me);parts.objects.link(o)
 bm=bmesh.new();bm.from_mesh(me);il=bm.faces.layers.int.get('source_island')
 remove=[f for f in bm.faces if f[il]!=i or (i in (1,3,4) and abs(f.calc_center_median().x)>.145)]
 bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 if not bm.faces:bm.free();bpy.data.objects.remove(o,do_unlink=True);continue
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
 # Remove smallest overlapping sliver at over-connected edges; retain UVs.
 removed=0
 for _ in range(8):
  bad=[e for e in bm.edges if len(e.link_faces)>2]
  if not bad:break
  fs={min(e.link_faces,key=lambda f:f.calc_area()) for e in bad};removed+=len(fs)
  bmesh.ops.delete(bm,geom=list(fs),context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 # Close only small unintended boundary loops, not windows or broad openings.
 edges={e for e in bm.edges if e.is_boundary};closed=0
 while edges:
  seed=edges.pop();group={seed};todo=list(seed.verts);vs=set(seed.verts)
  while todo:
   v=todo.pop()
   for e in v.link_edges:
    if e in edges:edges.remove(e);group.add(e);vs.update(e.verts);todo.extend(e.verts)
  ext=max(max(v.co[k] for v in vs)-min(v.co[k] for v in vs) for k in range(3))
  if len(group)<=14 and ext<.024:
   bmesh.ops.holes_fill(bm,edges=list(group),sides=14);closed+=1
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 # Join compatible triangles without moving any body landmarks or UV seams.
 bmesh.ops.join_triangles(bm,faces=list(bm.faces),angle_face_threshold=.16,angle_shape_threshold=.45,cmp_uvs=True)
 bm.to_mesh(me);bm.free();finish(o)
 if i in (1,3,4):o.data.materials.clear();o.data.materials.append(black)
 report['parts'].append({'name':o.name,'source_island':i,'overlap_slivers_removed':removed,'small_loops_closed':closed})
body=bpy.data.objects['Body_and_cabin']
# Retain all the curved source body points. New wheels use a measured shared axle datum.
wheel_roots=[]
for axle,y in [('F',-.29126),('R',.26758)]:
 for side,s in [('L',1),('R',-1)]:
  c=(s*.2,y,.085205);prefix='Wheel_'+axle+side
  root=bpy.data.objects.new(prefix,None);parts.objects.link(root);root.location=c;root.empty_display_size=.05;root['spin_axis']='local X';wheel_roots.append(root)
  built=[]
  profile=[(-.027,.051),(-.031,.058),(-.032,.067),(-.029,.076),(-.024,.082),(-.018,.084),(.018,.084),(.024,.082),(.029,.076),(.032,.067),(.031,.058),(.027,.051)]
  built.append(lathe(prefix+'_Tyre',profile,c,rubber))
  rim=[(-.027,.0495),(-.026,.053),(-.023,.054),(-.021,.051),(.020,.051),(.023,.054),(.027,.054),(.028,.050),(.024,.046),(-.024,.046)]
  built.append(lathe(prefix+'_Rim_barrel',rim,c,steel))
  # A dished steel web with twelve genuine ventilation holes.
  web=[(s*.020,.012),(s*.018,.022),(s*.020,.037),(s*.024,.047),(s*.021,.048),(s*.017,.037),(s*.015,.022),(s*.017,.012)]
  o=lathe(prefix+'_Vented_web',web,c,steel);active(o)
  for j in range(12):
   a=j*2*pi/12
   bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0058,depth=.04,location=(c[0]+s*.02,y+.035*cos(a),c[2]+.035*sin(a)),rotation=(0,pi/2,0));cut=bpy.context.object
   active(o);md=o.modifiers.new('Vent','BOOLEAN');md.operation='DIFFERENCE';md.solver='EXACT';md.object=cut;bpy.ops.object.modifier_apply(modifier=md.name);bpy.data.objects.remove(cut,do_unlink=True)
  bevel(o,.00045);built.append(o)
  built.append(lathe(prefix+'_Hub',[(s*.017,.0001),(s*.027,.0001),(s*.029,.011),(s*.026,.013),(s*.017,.013)],c,steel,32))
  for j in range(5):
   a=j*2*pi/5;cc=(c[0],y+.018*cos(a),c[2]+.018*sin(a))
   built.append(lathe(prefix+'_Lug_%d'%j,[(s*.020,.0001),(s*.027,.0001),(s*.027,.0027),(s*.020,.0027)],cc,silver,6))
  # Chamfered tread blocks, combined into a single editable mesh per wheel.
  vs=[];fs=[]
  for row in range(3):
   for j in range(36):
    a=(j+(row%2)*.5)*2*pi/36;shift=(row-1)*.014
    # octagonal block section around its radial axis
    outline=[(-.005,-.005),(-.004,-.006),(.004,-.006),(.005,-.005),(.005,.005),(.004,.006),(-.004,.006),(-.005,.005)]
    base=len(vs)
    for r,shrink in [(.0828,1),(.0860,.86)]:
     for dx,t in outline:vs.append((c[0]+shift+dx*shrink,y+r*cos(a)-t*shrink*sin(a),c[2]+r*sin(a)+t*shrink*cos(a)))
    fs.extend([tuple(base+k for k in reversed(range(8))),tuple(base+8+k for k in range(8))])
    fs.extend([(base+k,base+(k+1)%8,base+8+(k+1)%8,base+8+k) for k in range(8)])
  o=object_mesh(prefix+'_Tread',vs,fs,rubber);finish(o,False);built.append(o)
  for o in built:
   for v in o.data.vertices:v.co-=Vector(c)
   o.parent=root;o.matrix_parent_inverse=Matrix.Identity(4);o.location=(0,0,0)
  report.setdefault('wheels',[]).append({'name':prefix,'centre_donor':list(c),'tyre_section_width':.064,'rim_outer_width':.056,'tread_radius':.086,'vents':12})
# A minimally processed source-body comparison remains available in the reference collection.
# Set real-world scale once, with all child wheel geometry following its axle root.
for o in list(parts.objects):
 if o.type=='MESH':
  for v in o.data.vertices:v.co*=4.5
  o.location*=4.5
 elif o.type=='EMPTY':
  o.location*=4.5
donor.scale=(4.5,4.5,4.5)
for o in list(parts.objects):
 if o.type=='MESH' and o.parent:
  active(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
# All materials/textures are packed and all edited parts retain or receive a UV map.
for o in parts.objects:
 if o.type!='MESH':continue
 if not o.data.uv_layers:
  active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
for im in bpy.data.images:
 if im.type=='IMAGE' and im.size[0]>0:im.pack()
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
for o in sc.objects:
 if o.type=='LIGHT':o.location*=4.5;o.data.energy*=4.5**2;o.data.size*=4.5
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
cam=sc.camera;cam.data.ortho_scale=5.8
def render(n,pos,target=(0,0,.85)):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
render('quarter',(5.4,-7.2,4.5));render('side',(5.4,0,.95),(0,0,.95));render('rear',(5,7,3.6));render('front',(0,-7.5,1),(0,0,1))
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='SINGLE';sc.display.shading.single_color=(.56,.59,.58)
render('underside',(4,-5,-5), (0,0,.6))
sc.render.engine='CYCLES';cam.data.ortho_scale=1.4;render('wheel-close',(2.5,-1.65,.65),(.9,-1.31,.38))
cam.data.ortho_scale=5.8;cam.location=(5.4,-7.2,4.5);cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
for o in sc.objects:o.select_set(False)
body.select_set(True);bpy.context.view_layer.objects.active=body
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':a.spaces.active.region_3d.view_distance=6;a.spaces.active.region_3d.view_location=(0,0,.8);a.spaces.active.shading.type='MATERIAL'
tris=0
for o in parts.objects:
 if o.type=='MESH':o.data.calc_loop_triangles();tris+=len(o.data.loop_triangles)
report['triangles']=tris;report['mesh_objects']=sum(o.type=='MESH' for o in parts.objects)
report['not_completed']=['Complete body retopology','Opening panel rig','Clear-glass conversion and fitted cabin finishing','Suspension/steering sweep','LOD/collision/Unreal validation']
(OUT/'build-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Porsche_Assembly.blend'))
for o in sc.objects:o.select_set(False)
for o in parts.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Porsche_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True)
print('PORSCHE_CLEANUP_SAVED',report['triangles'],flush=True)
