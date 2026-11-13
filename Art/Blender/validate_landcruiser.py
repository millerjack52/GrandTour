"""Offline LC80 roundtrip, reduction and collision-template validation."""
import bpy,bmesh,math,json,hashlib,sys,argparse
from pathlib import Path
from mathutils import Vector,Matrix
parser=argparse.ArgumentParser();parser.add_argument('--package',default='Package_v03');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/LandCruiser'/args.package
report=json.loads((OUT/'asset_report.json').read_text());results={}
T=Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z')
opts=dict(use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,path_mode='COPY',embed_textures=False)
for lod,ratio in [(1,.58),(2,.30)]:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'LandCruiser80_Rigged.blend'))
    objects=[o for o in bpy.data.collections['GAME_ASSET'].objects if o.type=='MESH'];arm=bpy.data.objects['Armature']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        bpy.context.view_layer.objects.active=o;o.select_set(True)
        if 'Glass' not in o.name and 'Markings' not in o.name:
            target=o
            if 'Exterior' in o.name:
                # Keep manufactured body surfaces exactly: a global collapse
                # damaged the door/bonnet highlights despite valid topology.
                prior=set(bpy.context.scene.objects)
                wheel_ids={g.index for g in o.vertex_groups if g.name.startswith('Wheel_')}
                bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT')
                bm=bmesh.from_edit_mesh(o.data);deform=bm.verts.layers.deform.active
                for face in bm.faces:
                    face.select_set(all(any(i in wheel_ids and w>.99 for i,w in v[deform].items()) for v in face.verts))
                bmesh.update_edit_mesh(o.data);bpy.ops.mesh.separate(type='SELECTED');bpy.ops.object.mode_set(mode='OBJECT')
                created=set(bpy.context.scene.objects)-prior;assert len(created)==1
                target=created.pop();bpy.context.view_layer.objects.active=target
            dec=target.modifiers.new('Distance reduction','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=dec.name)
            if target!=o:
                bpy.ops.object.select_all(action='DESELECT');o.select_set(True);target.select_set(True)
                bpy.context.view_layer.objects.active=o;bpy.ops.object.join()
        tri_mod=o.modifiers.new('Final LOD triangles','TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier=tri_mod.name)
        o.data.validate(verbose=True,clean_customdata=False)
        # Reduction must retain one rigid influence per vertex and valid triangles.
        assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-4 for v in o.data.vertices)
        assert all(p.area>1e-12 for p in o.data.polygons)
        o.select_set(False)
    tris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects)
    assert tris<report['triangles'];results['LOD'+str(lod)]={'triangles':tris,'ratio_requested':ratio,'weights':'PASS'}
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('LandCruiser80_LOD'+str(lod)+'.blend')))
    for o in objects:o.data.transform(T);o.select_set(True)
    arm.data.transform(T);arm.select_set(True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
    bpy.ops.export_scene.fbx(filepath=str(OUT/('SK_LandCruiser80_LOD'+str(lod)+'.fbx')),**opts)
# Fresh scene roundtrips. Validate import scale against source bounds and bone distances.
for lod in [0,1,2]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
    name='SK_LandCruiser80'+('_LOD'+str(lod) if lod else '')+'.fbx'
    bpy.ops.import_scene.fbx(filepath=str(OUT/name),use_anim=False)
    arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(arms)==1
    arm=arms[0];bones=arm.data.bones;assert set(report['bones'])==set(bones.keys())
    pts={n:arm.matrix_world@bones[n].head_local for n in bones.keys()}
    # Blender's FBX reader returns cm coordinates in this cm scene.
    wb=(pts['Wheel_FL']-pts['Wheel_RL']).length;track=(pts['Wheel_FL']-pts['Wheel_FR']).length
    assert abs(wb-285)<.03,(name,wb)
    assert abs(track-160)<.03,(name,track)
    assert pts['Wheel_FL'].x>pts['Wheel_RL'].x and pts['Wheel_FL'].y>pts['Wheel_FR'].y
    assert abs(pts['Wheel_FL'].z-41.5)<.03
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==4,len(meshes)
    assert sum(len(o.data.materials) for o in meshes)==4
    for o in meshes:
        assert len(o.data.uv_layers)==1
        if 'Markings' in o.name:assert len(o.data.color_attributes)>0
        assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-4 for v in o.data.vertices)
        assert all(math.isfinite(x) for v in o.data.vertices for x in v.co)
    tri=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
    expected=report['triangles'] if not lod else results['LOD'+str(lod)]['triangles']
    assert tri==expected,(name,tri,expected,[(o.name,len(o.data.polygons)) for o in meshes])
    allp=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
    bounds=[max(p[i] for p in allp)-min(p[i] for p in allp) for i in range(3)]
    assert 470<bounds[0]<500 and 200<bounds[1]<240 and 185<bounds[2]<200,bounds
    results['roundtrip_LOD'+str(lod)]={'status':'PASS','triangles':tri,'meshes':len(meshes),'material_slots':4,'wheelbase_cm':wb,'track_cm':track,'bounds_cm':bounds,'bones':len(bones)}
    results['roundtrip_LOD'+str(lod)]['fbx_sha256']=hashlib.sha256((OUT/name).read_bytes()).hexdigest()
    if not lod:bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LandCruiser80_FBX_Roundtrip.blend'))
# Editable compound convex body collision template; NOT a validated UE PhysicsAsset.
bpy.ops.wm.open_mainfile(filepath=str(OUT/'LandCruiser80_Rigged.blend'))
scene=bpy.context.scene;collision=bpy.data.collections.new('PhysicsProxies');scene.collection.children.link(collision)
collision.hide_viewport=True
spec=[('Root',(.0,-.0,.84),(1.69,4.20,.54)),('Root',(0,.55,1.44),(1.48,2.82,.78)),('Root',(0,-1.42,1.02),(1.62,1.58,.38))]
proxy_report=[]
for i,(bone,centre,size) in enumerate(spec):
    bpy.ops.mesh.primitive_cube_add(size=1,location=centre);o=bpy.context.object;o.name='UCX_LandCruiser80_'+str(i).zfill(2);o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection):c.objects.unlink(o)
    collision.objects.link(o);o.display_type='WIRE';o.hide_render=True;o['PhysicsBone']=bone
    proxy_report.append({'bone':bone,'centre_cm':list(T@Vector(centre)),'size_cm':[size[1]*100,size[0]*100,size[2]*100]})
scene['Status']='Offline asset checked; Unreal material/PhysicsAsset/Chaos/camera validation pending'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LandCruiser80_Rigged.blend'))
results['collision_template']={'body_boxes':proxy_report,'status':'Blender template only; fit and suspension contact require Unreal'}
(OUT/'validation_report.json').write_text(json.dumps(results,indent=2))
print('LC_VALIDATE_OK '+json.dumps(results),flush=True)
