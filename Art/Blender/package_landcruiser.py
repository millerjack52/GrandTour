"""Build portable LC80 atlases and a rigid articulated skeletal FBX.
Run in Blender, CPU only. Does not launch Unreal or replace the existing car.
"""
import bpy,bmesh,math,json,sys,argparse
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--source',default='R7');parser.add_argument('--package',default='Package_v03')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=ROOT/'Art/Export/LandCruiser'/args.package;OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Art/Export/LandCruiser'/args.source/'LandCruiser80.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.bake.margin=12;scene.render.bake.use_clear=True
SKIP={'Studio','Reference','Pivots'}
MOVING=['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR','Door_FL','Door_FR','Door_RL','Door_RR','Hood','TailgateUpper','TailgateLower','Steering']
MOVING+=['Needle_'+n for n in ['Speedometer','Tachometer','Fuel','Voltage','Coolant','Oil']]
heads={'Root':Vector((0,0,0))}
for n in MOVING:
    ob=bpy.data.objects.get(n+'_Pivot') or bpy.data.objects.get(n)
    if ob:heads[n]=ob.matrix_world.translation.copy()
assert set(MOVING)<=set(heads),str(set(MOVING)-set(heads))
src=[o for o in scene.objects if o.type in {'MESH','CURVE','FONT'} and not ({c.name for c in o.users_collection}&SKIP)]
dest=bpy.data.collections.new('GAME_ASSET');scene.collection.children.link(dest)
buckets={'Exterior':[],'Interior':[],'Glass':[],'Markings':[]};wheel_bounds={}
deps=bpy.context.evaluated_depsgraph_get()
for old in src:
    groups={c.name for c in old.users_collection}
    bone=next((n for n in MOVING if n in groups),'Root')
    interior=bool(groups&{'Interior','Instruments','Steering'}) or bone.startswith('Needle_') or old.name.startswith(('DoorCard','DoorInsert','Armrest','InnerHandle','Speaker'))
    ev=old.evaluated_get(deps);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
    me.transform(old.matrix_world)
    colours=me.color_attributes.new(name='LC_Colour',type='FLOAT_COLOR',domain='CORNER')
    for poly in me.polygons:
        ma=me.materials[poly.material_index];bs=next(n for n in ma.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        for li in poly.loop_indices:colours.data[li].color=bs.inputs['Base Color'].default_value
    if old.name in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']:
        wheel_bounds[old.name]={'min':[min(v.co[i] for v in me.vertices) for i in range(3)],'max':[max(v.co[i] for v in me.vertices) for i in range(3)]}
    glass_ids={i for i,m in enumerate(me.materials) if m and m.name=='LC_Glass'}
    marking_ids={i for i,m in enumerate(me.materials) if m and (m.name=='LC_Markings' or old.type=='FONT')}
    kinds=(['Glass'] if glass_ids else [])+(['Markings'] if marking_ids else [])+[('Interior' if interior else 'Exterior')]
    for kind in kinds:
        part=me.copy();bm=bmesh.new();bm.from_mesh(part)
        keep_ids=glass_ids if kind=='Glass' else marking_ids if kind=='Markings' else set(range(len(me.materials)))-glass_ids-marking_ids
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in keep_ids],context='FACES')
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
        bm.to_mesh(part);bm.free()
        if not part.polygons:bpy.data.meshes.remove(part);continue
        o=bpy.data.objects.new(old.name+'_Game',part);dest.objects.link(o)
        vg=o.vertex_groups.new(name=bone);vg.add(list(range(len(part.vertices))),1,'REPLACE')
        buckets[kind].append(o)
    bpy.data.meshes.remove(me)
for old in src:bpy.data.objects.remove(old,do_unlink=True)
meshes=[];report={'source_revision':args.source,'wheel_bounds_metres':wheel_bounds,'bones':list(heads),'materials':{},'validation':{}}
for name,items in buckets.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in items:o.select_set(True)
    bpy.context.view_layer.objects.active=items[0];bpy.ops.object.join();o=bpy.context.object;o.name='LC80_'+name;meshes.append(o)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008,area_weight=.5,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    if name in {'Glass','Markings'}:
        mat=bpy.data.materials['LC_Glass' if name=='Glass' else 'LC_Markings']
        if name=='Markings':
            mat=mat.copy();mat.name='M_LC80_Markings';nt=mat.node_tree
            colour=nt.nodes.new('ShaderNodeVertexColor');colour.layer_name='LC_Colour'
            nt.links.new(colour.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Base Color'])
        o.data.materials.clear();o.data.materials.append(mat)
        for p in o.data.polygons:p.material_index=0
        continue
    # Unique bake materials avoid sharing active image targets with the next atlas.
    for i,m in enumerate(o.data.materials):o.data.materials[i]=m.copy()
    maps={}
    for channel in ['BaseColor','ORM']:
        im=bpy.data.images.new('T_LC80_'+name+'_'+channel,2048,2048,alpha=False)
        if channel=='ORM':im.colorspace_settings.name='Non-Color'
        restore=[]
        for ma in o.data.materials:
            nt=ma.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
            original=output.inputs['Surface'].links[0].from_socket
            em=nt.nodes.new('ShaderNodeEmission')
            if channel=='BaseColor':
                inp=bs.inputs['Base Color']
                if inp.is_linked:nt.links.new(inp.links[0].from_socket,em.inputs['Color'])
                else:em.inputs['Color'].default_value=inp.default_value
            else:em.inputs['Color'].default_value=(1,bs.inputs['Roughness'].default_value,bs.inputs['Metallic'].default_value,1)
            nt.links.new(em.outputs[0],output.inputs['Surface'])
            target=nt.nodes.new('ShaderNodeTexImage');target.image=im;nt.nodes.active=target
            restore.append((nt,output,original,em,target))
        print('LC_PACKAGE_BAKE '+name+' '+channel,flush=True)
        bpy.ops.object.bake(type='EMIT')
        im.filepath_raw=str(OUT/(im.name+'.png'));im.file_format='PNG';im.save();maps[channel]=im
        for nt,output,original,em,target in restore:
            nt.links.new(original,output.inputs['Surface']);nt.nodes.remove(em);nt.nodes.remove(target)
    ma=bpy.data.materials.new('M_LC80_'+name);ma.use_nodes=True;nt=ma.node_tree;bs=nt.nodes.get('Principled BSDF')
    al=nt.nodes.new('ShaderNodeTexImage');al.image=maps['BaseColor'];nt.links.new(al.outputs['Color'],bs.inputs['Base Color'])
    orm=nt.nodes.new('ShaderNodeTexImage');orm.image=maps['ORM'];sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(orm.outputs['Color'],sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    o.data.materials.clear();o.data.materials.append(ma)
    for p in o.data.polygons:p.material_index=0
    report['materials'][name]=[im.name+'.png' for im in maps.values()]
# Clean glass to one portable slot; UE needs its own translucent material.
glass=next(o for o in meshes if o.name=='LC80_Glass');gm=bpy.data.materials.get('LC_Glass');glass.data.materials.clear();glass.data.materials.append(gm)
for p in glass.data.polygons:p.material_index=0
armdata=bpy.data.armatures.new('LC80_Skeleton');arm=bpy.data.objects.new('Armature',armdata);dest.objects.link(arm)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for n,head in heads.items():
    b=armdata.edit_bones.new(n);b.head=head;b.tail=head+Vector((.15,0,0))
    if n!='Root':b.parent=armdata.edit_bones['Root']
bpy.ops.object.mode_set(mode='OBJECT')
for o in meshes:
    mod=o.modifiers.new('Rigid vehicle skeleton','ARMATURE');mod.object=arm
    # All construction is finished: triangulate explicitly for stable import.
    tri=o.modifiers.new('Export triangulation','TRIANGULATE');tri.keep_custom_normals=True
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=tri.name)
    assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-6 for v in o.data.vertices),o.name+' invalid weights'
    assert len(o.data.uv_layers)>0
    assert all(math.isfinite(x) for v in o.data.vertices for x in v.co)
    assert all(p.area>1e-12 for p in o.data.polygons),o.name+' degenerate face'
report['triangles']=sum(len(o.data.polygons) for o in meshes)
report['vertices']=sum(len(o.data.vertices) for o in meshes)
report['validation']['rigid_weights_uv_finite_nonzero_faces']='PASS'
# Test every articulated group: rotate it around its bone pivot and compare evaluated vertices.
pose_errors={}
for name in MOVING:
    pb=arm.pose.bones[name];rest=pb.bone.matrix_local.copy();p=heads[name]
    axis='X' if name.startswith('Wheel') else 'Y' if name.startswith('Needle') else 'Z'
    delta=Matrix.Translation(p)@Matrix.Rotation(.31,4,axis)@Matrix.Translation(-p)
    pb.matrix=delta@rest;bpy.context.view_layer.update();maxerr=0.;tested=0
    for o in meshes:
        vg=o.vertex_groups.get(name)
        if not vg:continue
        ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
        for v in o.data.vertices:
            if v.groups[0].group==vg.index:maxerr=max(maxerr,(em.vertices[v.index].co-delta@v.co).length);tested+=1
        ev.to_mesh_clear()
    pb.matrix_basis=Matrix.Identity(4);bpy.context.view_layer.update()
    assert tested and maxerr<1e-4,(name,tested,maxerr)
    pose_errors[name]={'vertices':tested,'max_error_m':maxerr}
report['validation']['articulation']=pose_errors
scene['Status']='Textured rigid rig; FBX roundtrip required; Unreal validation pending'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LandCruiser80_Rigged.blend'))
# Render the baked asset, not the procedural source.
def P(v):return Vector((v[1],-v[0],v[2]))
views={'front':((6.2,6,3),(-.05,0,.98),57),'rear':((-6.6,-5.9,3),(-.25,0,1),57),'cockpit':((-.64,-.455,1.57),(.7,-.22,1.12),18)}
scene.cycles.samples=24
for name,(pos,target,lens) in views.items():
    cam=scene.camera;cam.location=P(pos);cam.rotation_euler=(P(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens;cam.data.type='PERSP'
    bpy.data.objects['CabinReviewFill'].hide_render=name!='cockpit';scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('LC_PACKAGE_RENDER '+name,flush=True)
# Copy and transform geometry and bind pose into centimetres/+X front.
T=Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z')
for o in meshes:o.data.transform(T)
armdata.transform(T)
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01;scene.unit_settings.length_unit='CENTIMETERS'
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True)
for o in meshes:o.select_set(True)
opts=dict(use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,path_mode='COPY',embed_textures=False)
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_LandCruiser80.fbx'),**opts)
(OUT/'asset_report.json').write_text(json.dumps(report,indent=2))
print('LC_PACKAGE_OK '+str(OUT),flush=True)
