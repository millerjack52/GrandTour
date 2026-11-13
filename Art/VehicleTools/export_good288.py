import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-game-v01');SOURCE=P/'Ferrari288_GameReady.blend'
def clean_mesh(ob,threshold):
 old=ob.data;groupnames=[g.name for g in ob.vertex_groups];polys=[p for p in old.polygons if p.area>threshold];ids=sorted({v for p in polys for v in p.vertices});remap={v:i for i,v in enumerate(ids)}
 weights=[[(g.group,g.weight) for g in old.vertices[i].groups] for i in ids];normal=[n.vector.copy() for n in old.corner_normals]
 me=bpy.data.meshes.new(old.name+'_validated');me.from_pydata([old.vertices[i].co for i in ids],[],[[remap[v] for v in p.vertices] for p in polys]);me.update()
 for mat in old.materials:me.materials.append(mat)
 uv=me.uv_layers.new(name='UVMap');nn=[]
 for p,q in zip(polys,me.polygons):
  q.material_index=p.material_index;q.use_smooth=p.use_smooth
  for a,b in zip(p.loop_indices,q.loop_indices):
   uv.data[b].uv=old.uv_layers[0].data[a].uv;nn.append(normal[a] if normal[a].length>.5 else p.normal)
 me.normals_split_custom_set(nn);ob.data=me
 for name in groupnames:ob.vertex_groups.new(name=name)
 for i,gs in enumerate(weights):
  for group,w in gs:ob.vertex_groups[group].add([i],w,'REPLACE')
 return len(old.polygons)-len(me.polygons)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));sc=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get()
parts=list(bpy.data.collections['Ferrari | preserved source components'].objects)+list(bpy.data.collections['GAME | fitted additions'].objects)
build=json.loads((P/'build-report.json').read_text());heads={'Root':Vector((0,0,0))}
for tag,d in build['wheels'].items():heads['Wheel_'+tag]=Vector(d['centre'])*4.5
outcol=bpy.data.collections.new('EXPORT | Unreal rig');sc.collection.children.link(outcol)
palette_names=['F288_Rubber','F288_Cabin','F288_Seats','F288_Metal','F288_Dials'];palette=bpy.data.materials.new('F288_Palette');palette.use_nodes=True
pixels=[];colors=[]
for n in palette_names:colors.append(list(bpy.data.materials[n].diffuse_color))
# Palette image stores sRGB encoded values through Blender's image saving.
img=bpy.data.images.new('T_F288_Palette',width=80,height=16,alpha=False)
for y in range(16):
 for x in range(80):pixels.extend(colors[x//16])
img.pixels.foreach_set(pixels);img.filepath_raw=str(P/'T_F288_Palette.png');img.file_format='PNG';img.save();img.pack()
tex=palette.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img;bs=palette.node_tree.nodes.get('Principled BSDF');palette.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.65
source_mat=next(m for m in bpy.data.materials if m.name.startswith('tripo_mat'));source_mat.name='F288_Source'
exportparts=[];membership={}
for src in parts:
 if src.type!='MESH':continue
 ev=src.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg);me.transform(src.matrix_world)
 ob=bpy.data.objects.new('GAME '+src.name,me);outcol.objects.link(ob);exportparts.append(ob);bone=src.get('bone','Root');membership[src.name]=bone
 group=ob.vertex_groups.new(name=bone);group.add(list(range(len(me.vertices))),1,'REPLACE')
 for slot,m in enumerate(list(me.materials)):
  if m.name not in palette_names:continue
  x=(palette_names.index(m.name)+.5)/5
  for p in me.polygons:
   if p.material_index==slot:
    for j,li in enumerate(p.loop_indices):
     angle=2*math.pi*j/len(p.loop_indices);me.uv_layers[0].data[li].uv=(x+.015*math.cos(angle),.5+.075*math.sin(angle))
  me.materials[slot]=palette
bpy.ops.object.select_all(action='DESELECT')
for ob in exportparts:ob.select_set(True)
bpy.context.view_layer.objects.active=exportparts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SK_Ferrari288'
tri=mesh.modifiers.new('Export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
# Remove only zero-area source triangles; protect UVs and valid source normals.
mesh.data.validate(verbose=True,clean_customdata=False)
removed=clean_mesh(mesh,1e-12)
slots=list(mesh.data.materials);unique=[]
for m in slots:
 if m not in unique:unique.append(m)
ids=[unique.index(slots[p.material_index]) for p in mesh.data.polygons];mesh.data.materials.clear()
for m in unique:mesh.data.materials.append(m)
for p,i in zip(mesh.data.polygons,ids):p.material_index=i
assert len(unique)==3,[m.name for m in unique]
ad=bpy.data.armatures.new('Ferrari288Skeleton');arm=bpy.data.objects.new('Armature',ad);outcol.objects.link(arm)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for name,head in heads.items():
 b=ad.edit_bones.new(name);b.head=head;b.tail=head+Vector((.15,0,0))
 if name!='Root':b.parent=ad.edit_bones['Root']
bpy.ops.object.mode_set(mode='OBJECT');md=mesh.modifiers.new('Vehicle skeleton','ARMATURE');md.object=arm
assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-6 for v in mesh.data.vertices)
checks={}
for name,p in heads.items():
 if name=='Root':continue
 pb=arm.pose.bones[name];delta=Matrix.Translation(p)@Matrix.Rotation(.4,4,'X')@Matrix.Translation(-p);pb.matrix=delta@pb.bone.matrix_local;bpy.context.view_layer.update()
 ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();group=mesh.vertex_groups[name].index
 errors=[(m.vertices[v.index].co-delta@v.co).length for v in mesh.data.vertices if v.groups[0].group==group];assert errors and max(errors)<1e-5
 checks[name]={'vertices':len(errors),'max_error_m':max(errors)};ev.to_mesh_clear();pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();T=Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z');mesh.data.transform(T);ad.transform(T);sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.01
def fbx(ob,path):
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,path_mode='AUTO')
filename=P/'SK_Ferrari288.fbx';fbx(mesh,filename);lods=[{'level':0,'triangles':len(mesh.data.polygons),'file':str(filename)}]
for level,ratio in [(1,.60),(2,.30)]:
 low=mesh.copy();low.data=mesh.data.copy();outcol.objects.link(low);low.name='SK_Ferrari288_LOD'+str(level)
 for md in list(low.modifiers):low.modifiers.remove(md)
 bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
 # The source splits vertices at UV/normal seams. Weld positions before reducing
 # so adjacent sides cannot collapse independently and open visible cracks.
 bm=bmesh.new();bm.from_mesh(low.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bm.to_mesh(low.data);bm.free();low.data.update()
 if low.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
 dec=low.modifiers.new('Distance reduction','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
 clean_mesh(low,1e-8)
 md=low.modifiers.new('Vehicle skeleton','ARMATURE');md.object=arm
 path=P/(low.name+'.fbx');fbx(low,path);lods.append({'level':level,'triangles':len(low.data.polygons),'file':str(path)});low.hide_render=True;low.hide_set(True)
coords=[(v.co.x,-v.co.y,v.co.z) for v in mesh.data.vertices]
report={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'fbx_sha256':hashlib.sha256(filename.read_bytes()).hexdigest(),'triangles':len(mesh.data.polygons),'degenerate_faces_removed':removed,'lods':lods,'materials':[m.name for m in unique],'bone_membership':membership,'bones':{n:[-p.y*100,-p.x*100,p.z*100] for n,p in heads.items()},'bounds_cm':[[min(v[i] for v in coords) for i in range(3)],[max(v[i] for v in coords) for i in range(3)]],'wheel_pose_checks':checks,'limits':build['limits']}
(P/'export-report.json').write_text(json.dumps(report,indent=2))
for o in parts:o.hide_render=True;o.hide_set(True)
cam=sc.camera;cam.location=(800,600,400);cam.rotation_euler=(Vector((0,0,80))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=48
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   space=area.spaces.active;space.region_3d.view_location=(0,0,80);space.region_3d.view_distance=680;space.region_3d.view_rotation=cam.rotation_euler.to_quaternion();space.shading.color_type='TEXTURE';space.overlay.show_extras=False
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Ferrari288_GameRig.blend'));print('EXPORTED',json.dumps(report))
