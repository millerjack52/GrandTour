"""Derive rigid five-bone driving rigs from the exact installed static FBXs.
Source blends, component FBXs and their materials remain untouched.
"""
import bpy,json,hashlib,math,re
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/Driving');OUT.mkdir(exist_ok=True)
SOURCES={'Panda1990':'panda-unreal-v01','Prado':'prado-unreal-v01','CraftedUtility':'new-cars-unreal-v01','Pathfinder2002':'new-cars-unreal-v01','Impreza2003':'new-cars-unreal-v01'}
def bounds(vs):return [[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]]
for car,folder in SOURCES.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    out=OUT/car;out.mkdir(exist_ok=True)
    d=json.loads((ROOT/folder/car/'manifest.json').read_text())
    parts=[];mats={};wheels={};boneparts={};errors=[]
    for part in d['parts']:
        assert hashlib.sha256(Path(part['file']).read_bytes()).hexdigest()==part['sha256']
        bpy.ops.import_scene.fbx(filepath=part['file'])
        obs=[o for o in bpy.context.selected_objects if o.type=='MESH'];assert obs
        verts=[o.matrix_world@v.co*100 for o in obs for v in o.data.vertices]
        got=bounds([(v.x,-v.y,v.z) for v in verts])
        error=max(abs(got[j][i]-part['bounds_local_cm'][j][i]) for j in range(2) for i in range(3));assert error<.2,(car,part['group'],error)
        errors.append(error)
        pivot=part['pivot_cm'];local=part['bounds_local_cm']
        center=[pivot[i]+(local[0][i]+local[1][i])/2 for i in range(3)]
        wheel='wheel' in part['group'].lower() and 'spare' not in part['group'].lower()
        bone=('Wheel_'+('F' if center[0]>0 else 'R')+('L' if center[1]<0 else 'R')) if wheel else 'Root'
        if wheel:
            assert bone not in wheels
            wheels[bone]={'center':center,'radius':(local[1][2]-local[0][2])/2,'width':local[1][1]-local[0][1]}
        boneparts[part['group']]=bone
        for ob in obs:
            ob.data.transform(Matrix.Scale(100,4)@ob.matrix_world)
            ob.matrix_world=Matrix.Identity(4)
            ob.data.transform(Matrix.Translation(Vector((pivot[0],-pivot[1],pivot[2]))))
            for i,m in enumerate(list(ob.data.materials)):
                name=m.name if m.name in d['materials'] else re.sub(r'\.\d+$','',m.name)
                assert name in d['materials'],name
                if name not in mats:m.name=name;mats[name]=m
                ob.data.materials[i]=mats[name]
            ob.vertex_groups.clear();g=ob.vertex_groups.new(name=bone);g.add(list(range(len(ob.data.vertices))),1,'REPLACE')
            parts.append(ob)
    assert set(wheels)=={'Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR'}
    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:ob.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SK_'+car+'_Fleet'
    tri=mesh.modifiers.new('Export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    ad=bpy.data.armatures.new(car+'_FleetSkeleton');arm=bpy.data.objects.new('Armature',ad);bpy.context.scene.collection.objects.link(arm)
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
    bones={'Root':[0,0,0],**{b:w['center'] for b,w in wheels.items()}}
    for name,head in bones.items():
        b=ad.edit_bones.new(name);b.head=(head[0],-head[1],head[2]);b.tail=b.head+Vector((0,15,0))
        if name!='Root':b.parent=ad.edit_bones['Root']
    bpy.ops.object.mode_set(mode='OBJECT');mod=mesh.modifiers.new('Rigid vehicle rig','ARMATURE');mod.object=arm
    assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-6 for v in mesh.data.vertices)
    poses={}
    for name in wheels:
        pb=arm.pose.bones[name];p=pb.bone.head_local;delta=Matrix.Translation(p)@Matrix.Rotation(.4,4,'Y')@Matrix.Translation(-p)
        pb.matrix=delta@pb.bone.matrix_local;bpy.context.view_layer.update()
        ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();gid=mesh.vertex_groups[name].index
        errs=[(me.vertices[v.index].co-(delta@v.co if v.groups[0].group==gid else v.co)).length for v in mesh.data.vertices]
        assert max(errs)<.002,(car,name,max(errs));poses[name]=max(errs)
        ev.to_mesh_clear();pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update();sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.01
    def export(ob,path):
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False)
    lods=[]
    for lod,ratio in [(0,1),(1,.6),(2,.3)]:
        if lod==0:ob=mesh
        else:
            ob=mesh.copy();ob.data=mesh.data.copy();sc.collection.objects.link(ob)
            for m in list(ob.modifiers):ob.modifiers.remove(m)
            bpy.context.view_layer.objects.active=ob
            dec=ob.modifiers.new('Distance reduction','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
            mod=ob.modifiers.new('Rigid vehicle rig','ARMATURE');mod.object=arm
        path=out/(mesh.name+('' if lod==0 else '_LOD'+str(lod))+'.fbx');export(ob,path)
        lods.append({'file':str(path),'triangles':len(ob.data.polygons),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        if lod:ob.hide_set(True);ob.hide_render=True
    report={'car':car,'source_manifest':str(ROOT/folder/car/'manifest.json'),'bones':bones,'wheels':wheels,'body_bounds':next(p['bounds_local_cm'] for p in d['parts'] if p['group']=='Body'),'bounds_cm':d['bounds_cm'],'lods':lods,'material_names':[m.name for m in mesh.data.materials],'component_bones':boneparts,'geometry_max_error_cm':max(errors),'pose_max_error_cm':poses}
    (out/'rig-report.json').write_text(json.dumps(report,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(car+'_DrivingRig.blend')))
    print('FLEET_RIG_READY',car,flush=True)
