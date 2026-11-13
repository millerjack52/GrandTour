"""Convert the six fleet art actors to Chaos pawns without changing source art."""
import unreal as u,json,hashlib,shutil,traceback,datetime
from pathlib import Path
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/BenmoreFleet/Driving'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);V=u.GTVehicleSetupLibrary
LES=u.get_editor_subsystem(u.LevelEditorSubsystem);ACT=u.get_editor_subsystem(u.EditorActorSubsystem)
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
report={'ok':False,'cars':{},'tuning':'Initial AWD driving setups fitted to the existing art; not factory handling claims.'}
TUNES={'Panda1990':(1050,160,[-19.44,-34.56,147.6]),'Prado':(2350,340,[10,-42.5,193.5]),'CraftedUtility':(2050,300,[0,-43,159]),'Pathfinder2002':(1900,300,[0,40,146]),'Impreza2003':(1450,280,[0,-41,136]),'LandCruiser80':(2300,300,[-10,-43,162])}
def prop(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def save(o):assert E.save_loaded_asset(o,False)
def blueprint(name,parent):
    path=DEST+'/'+name
    asset=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST,u.Blueprint,prop(u.BlueprintFactory(),parent_class=parent))
    u.BlueprintEditorLibrary.compile_blueprint(asset);return asset
try:
    assert LES.load_level(MAP)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    sourcefile=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'
    backup=OUT/('before-driving-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.umap');shutil.copy2(sourcefile,backup);report['backup']=str(backup)
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    classes={}
    for car,(mass,torque,eye) in TUNES.items():
        DEST='/Game/GrandTour/Vehicles/FleetDriving/'+car
        if car=='LandCruiser80':
            skpath=DEST+'/SK_LandCruiser80_Fleet'
            sk=E.load_asset(skpath) if E.does_asset_exist(skpath) else E.duplicate_asset('/Game/GrandTour/Vehicles/Bodies/LandCruiser80/SK_LandCruiser80',skpath)
            oldpa=sk.get_editor_property('physics_asset');papath=DEST+'/PA_LandCruiser80_Fleet'
            pa=E.load_asset(papath) if E.does_asset_exist(papath) else E.duplicate_asset(oldpa.get_path_name().split('.')[0],papath)
            sk.set_editor_property('physics_asset',pa)
            wheels={b:{'center':[142.5 if '_F' in b else -142.5,-80 if b.endswith('L') else 80,41.5],'radius':41.5,'width':31.1} for b in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']}
            data={'wheels':wheels,'body_bounds':[[-240,-100,48],[240,100,189]],'bones':{'Root':[0,0,0],**{b:w['center'] for b,w in wheels.items()}}}
            probe=V.spawn_actor_of_class(world,u.SkeletalMeshActor,u.Transform(),'FleetRigProbe');c=probe.get_component_by_class(u.SkeletalMeshComponent);c.set_skeletal_mesh_asset(sk)
            for b in wheels:wheels[b]['center']=list(c.get_socket_transform(b,u.RelativeTransformSpace.RTS_COMPONENT).translation.to_tuple());data['bones'][b]=wheels[b]['center']
            for i in range(c.get_num_bones()):
                b=str(c.get_bone_name(i))
                if b!='Root':V.remove_bodies_by_bone_prefix(pa,b)
            ACT.destroy_actor(probe)
        else:
            data=json.loads((OUT/car/'rig-report.json').read_text());manifest=json.loads(Path(data['source_manifest']).read_text())
            task=prop(u.AssetImportTask(),filename=data['lods'][0]['file'],destination_path=DEST,automated=True,replace_existing=True,save=False)
            ui=prop(u.FbxImportUI(),import_mesh=True,import_as_skeletal=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=True,mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH)
            prop(ui.skeletal_mesh_import_data,import_uniform_scale=1.,convert_scene=True,force_front_x_axis=False,convert_scene_unit=True,import_morph_targets=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,normal_generation_method=u.FBXNormalGenerationMethod.BUILT_IN)
            task.options=ui;A.import_asset_tasks([task]);sk=E.load_asset(DEST+'/SK_'+car+'_Fleet');assert sk,car
            for lod in [1,2]:assert S.import_lod(sk,lod,data['lods'][lod]['file'])==lod
            sourcefolder=('/Game/GrandTour/Vehicles/Panda/Panda1990' if car=='Panda1990' else '/Game/GrandTour/Vehicles/Prado/Prado' if car=='Prado' else '/Game/GrandTour/Vehicles/ModelStudies/'+car)
            slots=list(sk.get_editor_property('materials'))
            for slot in slots:
                name=str(slot.get_editor_property('imported_material_slot_name'));assert name in manifest['materials'],name
                dest=DEST+'/Materials/'+name
                mat=E.load_asset(dest) if E.does_asset_exist(dest) else E.duplicate_asset(sourcefolder+'/Materials/'+name,dest)
                assert mat,name
                M.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True);M.recompile_material(mat);save(mat);slot.material_interface=mat
            sk.set_editor_property('materials',slots)
            pa=sk.get_editor_property('physics_asset') or S.create_physics_asset(sk,True,0)
            for b in data['bones']:
                if b!='Root':V.remove_bodies_by_bone_prefix(pa,b)
        bb=data['body_bounds'];zmin=max(26,bb[0][2]);roof=bb[1][2];belt=zmin+(roof-zmin)*.49
        xmin,xmax=bb[0][0],bb[1][0];width=(bb[1][1]-bb[0][1])*.86
        centers=[u.Vector((xmin+xmax)/2,0,(zmin+belt)/2),u.Vector((xmin+75)/2,0,(belt+roof-4)/2)]
        sizes=[u.Vector(xmax-xmin-12,width,belt-zmin),u.Vector(75-xmin-15,width*.88,roof-4-belt)]
        assert V.set_compound_box_body(pa,sk,'Root',centers,sizes)
        V.enable_hit_events(pa)
        for o in [pa,sk,sk.get_editor_property('skeleton')]:save(o)
        wheelclasses=[]
        for b in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']:
            wdata=data['wheels'][b];front=b.startswith('Wheel_F')
            bp=blueprint('BP_'+car+'_'+b,u.GTVehicleWheelFront if front else u.GTVehicleWheelRear)
            w=u.get_default_object(bp.generated_class())
            prop(w,wheel_radius=wdata['radius'],wheel_width=wdata['width'],wheel_mass=20.,suspension_max_raise=7.,suspension_max_drop=11.,spring_rate=mass*.24,suspension_damping_ratio=.72,max_brake_torque=mass*.8,max_steer_angle=30. if front else 0.)
            save(bp);wheelclasses.append(bp.generated_class())
        bp=blueprint('BP_'+car+'_Fleet',u.GTCarPawn);pawn=u.get_default_object(bp.generated_class())
        mesh=pawn.get_component_by_class(u.SkeletalMeshComponent);mesh.set_skeletal_mesh_asset(sk);mesh.set_anim_instance_class(u.GTVehicleAnimInstance)
        prop(pawn,driver_eye_offset=u.Vector(*eye),enter_needs_open_door=False,chase_arm_length=780.,chase_pivot_height=130.)
        prop(pawn.get_body(),panel_folder=DEST,panel_prefix='NO_LEGACY_PANELS_',paint_folder=DEST,build_windscreen=False)
        prop(pawn.get_dashboard(),build_greybox=False);prop(pawn.get_component_by_class(u.GTPartSlotsComponent),show_greybox_visuals=False)
        for camera in pawn.get_components_by_class(u.CameraComponent):
            if camera.get_name()=='DriverCamera':camera.set_field_of_view(95.)
        move=pawn.get_chaos_movement();prop(move,mass=mass,chassis_width=width,chassis_height=roof,center_of_mass_override=u.Vector((data['wheels']['Wheel_FL']['center'][0]+data['wheels']['Wheel_RL']['center'][0])/2,0,52 if car!='Prado' else 65))
        setups=list(move.get_editor_property('wheel_setups'))
        for setup,wc,b in zip(setups,wheelclasses,['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']):prop(setup,wheel_class=wc,bone_name=b,additional_offset=u.Vector())
        move.set_editor_property('wheel_setups',setups)
        eng=move.get_editor_property('engine_setup');eng.set_editor_property('max_torque',torque);move.set_editor_property('engine_setup',eng)
        prop(pawn.get_drivetrain(),centre_split_front=.5,low_range_ratio=2.,centre_lock_when_on=1.)
        save(bp);classes[car]=bp.generated_class()
        probe=V.spawn_actor_of_class(world,classes[car],u.Transform(),'FleetRigProbe');c=probe.get_component_by_class(u.SkeletalMeshComponent)
        bone_errors={}
        for b,expected in data['bones'].items():
            got=c.get_socket_transform(b,u.RelativeTransformSpace.RTS_COMPONENT).translation.to_tuple();error=max(abs(x-y) for x,y in zip(got,expected));assert error<.2,(car,b,got,expected);bone_errors[b]=error
        ACT.destroy_actor(probe)
        report['cars'][car]={'blueprint':bp.get_path_name(),'skeletal_mesh':sk.get_path_name(),'mass_kg':mass,'wheel_bone_errors_cm':bone_errors,'lods':S.get_lod_count(sk),'driver_eye_cm':eye,'wheels':data['wheels'],'physics_bodies':[str(x) for x in V.describe_bodies(pa)]}
        (OUT/'import-report.json').write_text(json.dumps(report,indent=2))
        u.log('FLEET_DRIVING_IMPORTED '+car)
    actors={a.get_actor_label():a for a in ACT.get_all_level_actors()}
    for car,cls in classes.items():
        old=actors['Benmore_Fleet_'+car];transform=old.get_actor_transform();tags=old.tags;folder=old.get_folder_path()
        # Preserve the actor's exact art transform; no terrain or scene dressing edits.
        assert ACT.destroy_actor(old)
        a=V.spawn_actor_of_class(world,cls,transform,'Benmore_Fleet_'+car);assert a
        a.tags=tags;a.set_folder_path(folder);prop(a,auto_possess_player=u.AutoReceiveInput.DISABLED,auto_possess_ai=u.AutoPossessAI.DISABLED)
        # Explicit instance values avoid native defaults surviving the first generated-class spawn.
        prop(a,driver_eye_offset=u.Vector(*TUNES[car][2]),enter_needs_open_door=False,chase_arm_length=780.,chase_pivot_height=130.)
        report['cars'][car]['placed_transform']=str(transform)
    fleet=[a for a in ACT.get_all_level_actors() if a.get_actor_label().startswith('Benmore_Fleet_') and isinstance(a,u.GTCarPawn)]
    assert len(fleet)==12,len(fleet)
    assert LES.save_current_level()
    report['ok']=True;report['fleet_driving_pawns']=len(fleet)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'import-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
