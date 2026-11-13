"""Rigid game rig from the immutable v05 model. No source-file writes."""
import bpy,bmesh,json,math,hashlib,sys,argparse
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
parser=argparse.ArgumentParser();parser.add_argument('--source',default=str(ROOT/'graphic-adventure-assembly-v05/GraphicAdventure_Assembly.blend'));parser.add_argument('--output',default=str(ROOT/'graphic-adventure-unreal-v01'));parser.add_argument('--finish',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=Path(args.source);OUT=Path(args.output);OUT.mkdir(exist_ok=True)
digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));sc=bpy.context.scene
sources=[o for o in sc.objects if o.type=='MESH' and o.name.startswith('RET |')]
mapping={'Wheel LF':'Wheel_FL','Wheel RF':'Wheel_FR','Wheel LR':'Wheel_RL','Wheel RR':'Wheel_RR','L Front door':'Door_FL','R Front door':'Door_FR','L Rear door':'Door_RL','R Rear door':'Door_RR','Bonnet':'Hood','Lower tailgate':'TailgateLower','Upper tailgate':'TailgateUpper'}
heads={'Root':Vector((0,0,0))}
for name,bone in mapping.items():heads[bone]=bpy.data.objects['GA | '+name].matrix_world.translation.copy()
dest=bpy.data.collections.new('UNREAL_EXPORT');sc.collection.children.link(dest)
dg=bpy.context.evaluated_depsgraph_get();parts=[];membership={};mats={}
for old in sources:
 par=old.parent;bone='Root'
 while par:
  name=par.name.removeprefix('GA | ')
  if name in mapping:bone=mapping[name];break
  par=par.parent
 ev=old.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg);me.transform(old.matrix_world)
 ob=bpy.data.objects.new('GAME '+old.name,me);dest.objects.link(ob);parts.append(ob);membership[old.name]=bone
 vg=ob.vertex_groups.new(name=bone);vg.add(list(range(len(me.vertices))),1.,'REPLACE')
 for m in me.materials:
  if not m or m.name in mats:continue
  bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  mats[m.name]={'color':list(bs.inputs['Base Color'].default_value),'roughness':float(bs.inputs['Roughness'].default_value),'metallic':float(bs.inputs['Metallic'].default_value)}
atlas_report=None
if args.finish:
 sys.path.insert(0,str(Path(__file__).resolve().parent))
 import graphic_adventure_texture_atlas as atlas
 atlas_report=atlas.pack(parts,mats,OUT)
for o in bpy.context.view_layer.objects:o.select_set(False)
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SK_GraphicAdventure'
tri=mesh.modifiers.new('Stable export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
removed_degenerate=0
if args.finish:
 bm=bmesh.new();bm.from_mesh(mesh.data);bad=[f for f in bm.faces if f.calc_area()<=1e-12];removed_degenerate=len(bad)
 bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
 loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bm.to_mesh(mesh.data);bm.free();mesh.data.update()
assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-6 for v in mesh.data.vertices)
assert all(p.area>1e-12 for p in mesh.data.polygons)
# Compact repeated source slots into the nine flat review materials.
old=list(mesh.data.materials);unique=[]
for m in old:
 if m not in unique:unique.append(m)
ids=[unique.index(old[p.material_index]) for p in mesh.data.polygons]
mesh.data.materials.clear()
for m in unique:mesh.data.materials.append(m)
for p,i in zip(mesh.data.polygons,ids):p.material_index=i
if not mesh.data.uv_layers:mesh.data.uv_layers.new(name='UVMap')
ad=bpy.data.armatures.new('GraphicAdventureSkeleton');arm=bpy.data.objects.new('Armature',ad);dest.objects.link(arm)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for n,head in heads.items():
 b=ad.edit_bones.new(n);b.head=head;b.tail=head+Vector((.15,0,0))
 if n!='Root':b.parent=ad.edit_bones['Root']
bpy.ops.object.mode_set(mode='OBJECT');mod=mesh.modifiers.new('Rigid vehicle skeleton','ARMATURE');mod.object=arm
checks={}
for n in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']:
 pb=arm.pose.bones[n];p=heads[n];delta=Matrix.Translation(p)@Matrix.Rotation(.3,4,'X')@Matrix.Translation(-p);pb.matrix=delta@pb.bone.matrix_local
 bpy.context.view_layer.update();ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();vg=mesh.vertex_groups[n];err=0.;count=0
 for v in mesh.data.vertices:
  if v.groups[0].group==vg.index:err=max(err,(me.vertices[v.index].co-delta@v.co).length);count+=1
 assert count>0 and err<1e-5,(n,err)
 checks[n]={'vertices':count,'max_error_m':err};ev.to_mesh_clear();pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
T=Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z');mesh.data.transform(T);ad.transform(T)
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.01
bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);arm.select_set(True)
filename=OUT/'SK_GraphicAdventure.fbx'
bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,path_mode='AUTO',embed_textures=False)
coords=[(v.co.x,-v.co.y,v.co.z) for v in mesh.data.vertices]
report={'source':str(SOURCE),'source_sha256':digest,'fbx_sha256':hashlib.sha256(filename.read_bytes()).hexdigest(),'triangles':len(mesh.data.polygons),'materials':mats,'source_objects':len(sources),'bone_membership':membership,'bones':{n:[-p.y*100,-p.x*100,p.z*100] for n,p in heads.items()},'bounds_cm':[[min(p[i] for p in coords) for i in range(3)],[max(p[i] for p in coords) for i in range(3)]],'wheel_pose_checks':checks,'limits':['Flat review materials; placeholder UVs, no texture unwrap or LODs.','Rigid body/doors with four animated Chaos wheel bones; doors are not wired to gameplay.']}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==digest
(OUT/'export-report.json').write_text(json.dumps(report,indent=2))
print('EXPORT_OK',len(sources),len(mesh.data.polygons),len(unique))
if args.finish:
 lods=[{'level':0,'triangles':len(mesh.data.polygons),'file':str(filename)}]
 for level,ratio in [(1,.50),(2,.22)]:
  bpy.ops.object.select_all(action='DESELECT')
  low=mesh.copy();low.data=mesh.data.copy();dest.objects.link(low);low.name='SK_GraphicAdventure_LOD'+str(level)
  for md in list(low.modifiers):low.modifiers.remove(md)
  low.select_set(True);bpy.context.view_layer.objects.active=low
  dec=low.modifiers.new('Distance reduction','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True
  bpy.ops.object.modifier_apply(modifier=dec.name)
  bm=bmesh.new();bm.from_mesh(low.data)
  bmesh.ops.dissolve_degenerate(bm,dist=.0001,edges=list(bm.edges))
  bad=[f for f in bm.faces if f.calc_area()<=1e-8]
  if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
  bmesh.ops.triangulate(bm,faces=list(bm.faces))
  loose=[v for v in bm.verts if not v.link_faces]
  if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
  bm.to_mesh(low.data);bm.free();low.data.update()
  low.data.validate(verbose=True,clean_customdata=False)
  md=low.modifiers.new('Rigid skeleton','ARMATURE');md.object=arm
  arm.select_set(True)
  path=OUT/(low.name+'.fbx')
  bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,path_mode='AUTO')
  count=sum(len(p.vertices)-2 for p in low.data.polygons);assert count<lods[-1]['triangles']
  lods.append({'level':level,'triangles':count,'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()});low.hide_render=True;low.hide_set(True)
 report['atlas']=atlas_report;report['lods']=lods;report['export_degenerate_faces_removed']=removed_degenerate
 report['limits']=['Static cockpit controls and mirror material; no functional mirror capture or animated dashboard needles.','Rigid wheel rig tested; opening-door gameplay is separate.']
 (OUT/'export-report.json').write_text(json.dumps(report,indent=2))
 # Save a rigged, textured game asset in addition to the separate-part authoring file.
 for o in sources:o.hide_render=True;o.hide_set(True)
 bpy.ops.object.select_all(action='DESELECT');mesh.hide_set(False);mesh.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=mesh
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GraphicAdventure_GameRig.blend'))
 print('FINISHED_EXPORT',json.dumps(lods),flush=True)
