"""Fresh-process verification of persisted imports, Blueprint defaults and map copies."""
import unreal as u
import json, traceback, hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve(); OUT=ROOT/'Art/Export/SpecialsTrio'
E=u.EditorAssetLibrary; V=u.GTVehicleSetupLibrary
report={'ok':False,'cars':{}}
try:
    for car in ['KadettA','E39Touring','SJ413']:
        src=OUT/car/'Package_v01'; data=json.loads((src/'asset_report.json').read_text()); spec=data['spec']
        dest='/Game/GrandTour/Vehicles/Bodies/'+car
        sk=E.load_asset(dest+'/SK_'+car); assert sk
        bp=E.load_asset(dest+'/BP_'+car); pawn=u.get_default_object(bp.generated_class())
        mesh=pawn.get_component_by_class(u.SkeletalMeshComponent)
        assert mesh.get_editor_property('skeletal_mesh_asset')==sk,car+' mesh default did not persist'
        assert not pawn.get_body().get_editor_property('build_windscreen')
        assert pawn.get_body().get_editor_property('panel_folder')==dest
        assert not pawn.get_dashboard().get_editor_property('build_greybox')
        assert not pawn.get_component_by_class(u.GTPartSlotsComponent).get_editor_property('show_greybox_visuals')
        assert any('boxes=2' in str(x) for x in V.describe_bodies(sk.get_editor_property('physics_asset')))
        move=pawn.get_chaos_movement(); radii=[]
        for setup in move.get_editor_property('wheel_setups'):
            wheel=u.get_default_object(setup.get_editor_property('wheel_class'))
            r=wheel.get_editor_property('wheel_radius'); assert abs(r-spec['r']*100)<.01,(car,r); radii.append(r)
        worlds=[]
        for suffix in ['Test','Mud']:
            level='/Game/GrandTour/Test/SpecialsTrio/L_'+car+'_'+suffix
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(level)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            gm=world.get_world_settings().get_editor_property('default_game_mode')
            assert u.get_default_object(gm).get_editor_property('default_pawn_class')==bp.generated_class()
            starts=u.GameplayStatics.get_all_actors_of_class(world,u.PlayerStart); assert len(starts)==1
            worlds.append({'map':level,'actors':len(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()),'start':str(starts[0].get_actor_location())})
        actor=V.spawn_actor_of_class(world,u.SkeletalMeshActor,u.Transform(),car+'_Verify')
        comp=actor.get_component_by_class(u.SkeletalMeshComponent); comp.set_skeletal_mesh_asset(sk)
        bones=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]; assert set(bones)==set(data['bones'])
        coords={}
        for n in ['Root','Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']:
            v=comp.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT).translation; coords[n]=[v.x,v.y,v.z]
        assert abs(coords['Wheel_FL'][0]-coords['Wheel_RL'][0]-spec['wb']*100)<.1
        assert abs(coords['Wheel_FR'][1]-coords['Wheel_FL'][1]-spec['track']*100)<.1
        assert abs(coords['Wheel_FL'][2]-spec['r']*100)<.1
        bounds=sk.get_bounds(); dims=[bounds.box_extent.x*2,bounds.box_extent.y*2,bounds.box_extent.z*2]
        expected=json.loads((src/'validation_report.json').read_text())['roundtrip_LOD0']['bounds_cm']
        assert max(abs(a-b) for a,b in zip(dims,expected))<1.,(dims,expected)
        S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem); assert S.get_lod_count(sk)==3
        report['cars'][car]={'status':'PASS','maps':worlds,'bones':len(bones),'dimensions_cm':dims,'wheel_bones_cm':coords,'wheel_radii_cm':radii,'mass_kg':move.get_editor_property('mass'),'legacy_overlays_disabled':True,'lod_count':3}
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error']); raise
finally:
    (OUT/'unreal_asset_check.json').write_text(json.dumps(report,indent=2))
