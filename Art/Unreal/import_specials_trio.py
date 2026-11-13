"""Import the approved R6 packages and make independent drivable test-map copies."""
import unreal as u
import json, hashlib, traceback
from pathlib import Path

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT/'Art/Export/SpecialsTrio'
BASE_MAP = '/Game/GrandTour/Test/L_TestTrack'
MUD_MAP = '/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive'
TEST_FOLDER = '/Game/GrandTour/Test/SpecialsTrio'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
M = u.MaterialEditingLibrary
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
V = u.GTVehicleSetupLibrary
LES = u.get_editor_subsystem(u.LevelEditorSubsystem)
report = {'ok': False, 'base_map': BASE_MAP, 'cars': {}}

def prop(obj, **kw):
    for k,v in kw.items(): obj.set_editor_property(k,v)
    return obj

def material(name):
    path=DEST+'/Materials/'+name
    m=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    M.delete_all_material_expressions(m)
    M.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
    return m

def expr(m,c,**kw): return prop(M.create_material_expression(m,c),**kw)
def pin(n,out,p): assert M.connect_material_property(n,out,p)
def scalar(m,value,p): pin(expr(m,u.MaterialExpressionConstant,r=value),'',p)
def compile_mat(m):
    assert not M.recompile_material(m)
    assert E.save_loaded_asset(m)

def texture(name,orm):
    t=prop(u.AssetImportTask(),filename=str(SRC/(name+'.png')),destination_path=DEST+'/Textures',automated=True,replace_existing=True,save=False)
    A.import_asset_tasks([t]); tex=E.load_asset(DEST+'/Textures/'+name); assert tex
    prop(tex,srgb=not orm,compression_settings=u.TextureCompressionSettings.TC_MASKS if orm else u.TextureCompressionSettings.TC_DEFAULT,compression_no_alpha=True)
    assert E.save_loaded_asset(tex)
    return tex

def blueprint(name,parent):
    path=DEST+'/'+name
    if E.does_asset_exist(path): return E.load_asset(path)
    factory=prop(u.BlueprintFactory(),parent_class=parent)
    bp=A.create_asset(name,DEST,u.Blueprint,factory); assert bp
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    return bp

def save_bp(bp):
    # CDO edits must be saved after compilation: recompilation recreates inherited component templates.
    assert E.save_loaded_asset(bp,False)

try:
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for car,mass,torque in [('KadettA',800.,95.),('E39Touring',1650.,245.),('SJ413',1000.,110.)]:
        SRC=OUT/car/'Package_v01'; DEST='/Game/GrandTour/Vehicles/Bodies/'+car
        data=json.loads((SRC/'asset_report.json').read_text()); spec=data['spec']
        checks=json.loads((SRC/'validation_report.json').read_text())
        for lod in range(3):
            f=SRC/('SK_'+car+('' if lod==0 else '_LOD'+str(lod))+'.fbx')
            assert hashlib.sha256(f.read_bytes()).hexdigest()==checks['roundtrip_LOD'+str(lod)]['fbx_sha256']
        task=prop(u.AssetImportTask(),filename=str(SRC/('SK_'+car+'.fbx')),destination_path=DEST,automated=True,replace_existing=True,save=True)
        ui=prop(u.FbxImportUI(),import_mesh=True,import_as_skeletal=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=True,mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH)
        prop(ui.skeletal_mesh_import_data,import_uniform_scale=1.,convert_scene=True,force_front_x_axis=False,convert_scene_unit=True,import_morph_targets=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE)
        task.options=ui; A.import_asset_tasks([task]); sk=E.load_asset(DEST+'/SK_'+car); assert sk
        for lod in [1,2]: assert S.import_lod(sk,lod,str(SRC/('SK_'+car+'_LOD'+str(lod)+'.fbx')))==lod
        mats={}
        for kind in ['Exterior','Interior']:
            m=material('M_'+car+'_'+kind)
            cs=expr(m,u.MaterialExpressionTextureSample,texture=texture('T_'+car+'_'+kind+'_BaseColor',False),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            os=expr(m,u.MaterialExpressionTextureSample,texture=texture('T_'+car+'_'+kind+'_ORM',True),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            pin(cs,'RGB',u.MaterialProperty.MP_BASE_COLOR); pin(os,'G',u.MaterialProperty.MP_ROUGHNESS); pin(os,'B',u.MaterialProperty.MP_METALLIC)
            compile_mat(m); mats[kind]=m
        m=material('M_'+car+'_Markings'); pin(expr(m,u.MaterialExpressionVertexColor),'',u.MaterialProperty.MP_BASE_COLOR); scalar(m,.6,u.MaterialProperty.MP_ROUGHNESS); compile_mat(m); mats['Markings']=m
        m=material('M_'+car+'_Glass'); prop(m,blend_mode=u.BlendMode.BLEND_TRANSLUCENT,two_sided=True,translucency_lighting_mode=u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        pin(expr(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.34,.46,.52,1)),'',u.MaterialProperty.MP_BASE_COLOR)
        scalar(m,.13,u.MaterialProperty.MP_OPACITY); scalar(m,.10,u.MaterialProperty.MP_ROUGHNESS); scalar(m,.8,u.MaterialProperty.MP_SPECULAR); compile_mat(m); mats['Glass']=m
        slots=list(sk.get_editor_property('materials')); assert len(slots)==4
        for slot in slots:
            name=str(slot.get_editor_property('imported_material_slot_name')); key=next(k for k in mats if k in name); slot.material_interface=mats[key]
        sk.set_editor_property('materials',slots)
        pa=sk.get_editor_property('physics_asset') or S.create_physics_asset(sk,True,0); assert pa
        for name in data['bones']:
            if name!='Root': V.remove_bodies_by_bone_prefix(pa,name)
        # Separate lower body and cabin collision; no invisible roof-height box over the bonnet.
        boxes=checks['collision_template']['body_boxes']
        centres=[u.Vector(b['centre_cm'][0],-b['centre_cm'][1],b['centre_cm'][2]) for b in boxes]
        sizes=[u.Vector(*b['size_cm']) for b in boxes]
        assert V.set_compound_box_body(pa,sk,'Root',centres,sizes)
        V.enable_hit_events(pa)
        bodies=[str(x) for x in V.describe_bodies(pa)]; assert len([x for x in bodies if 'physicsType=' in x])==1
        for asset in [pa,sk,sk.get_editor_property('skeleton')]: assert E.save_loaded_asset(asset)

        wheel_classes=[]
        for axle,parent in [('Front',u.GTVehicleWheelFront),('Rear',u.GTVehicleWheelRear)]:
            bp=blueprint('BP_'+car+'_Wheel'+axle,parent)
            wheel=u.get_default_object(bp.generated_class())
            prop(wheel,wheel_radius=spec['r']*100,wheel_width=spec['tw']*100,wheel_mass=20.,suspension_max_raise=7.,suspension_max_drop=11.,spring_rate=mass*.24,suspension_damping_ratio=.68,max_brake_torque=mass*.65)
            save_bp(bp); wheel_classes.append(bp.generated_class())
        bp=blueprint('BP_'+car,u.GTCarPawn); pawn=u.get_default_object(bp.generated_class())
        mesh=pawn.get_component_by_class(u.SkeletalMeshComponent); mesh.set_skeletal_mesh_asset(sk); mesh.set_anim_instance_class(u.GTVehicleAnimInstance)
        eye=u.Vector((spec['fb']-1.05)*100,-spec['drive']*spec['w']*.51*100,(spec['roof']-.22)*100)
        prop(pawn,driver_eye_offset=eye,enter_needs_open_door=False)
        body=pawn.get_body(); prop(body,panel_folder=DEST,panel_prefix='NO_LEGACY_PANELS_',paint_folder=DEST+'/Textures',build_windscreen=False)
        prop(pawn.get_dashboard(),build_greybox=False)
        prop(pawn.get_component_by_class(u.GTPartSlotsComponent),show_greybox_visuals=False)
        move=pawn.get_chaos_movement()
        prop(move,mass=mass,chassis_width=spec['w']*200,chassis_height=spec['roof']*100,center_of_mass_override=u.Vector(0,0,45 if car!='SJ413' else 60))
        setups=list(move.get_editor_property('wheel_setups'))
        for i,setup in enumerate(setups): setup.set_editor_property('wheel_class',wheel_classes[0 if i<2 else 1])
        move.set_editor_property('wheel_setups',setups)
        engine=move.get_editor_property('engine_setup'); engine.set_editor_property('max_torque',torque); move.set_editor_property('engine_setup',engine)
        prop(pawn.get_drivetrain(),centre_split_front=.5 if car=='SJ413' else 0.,low_range_ratio=2.5 if car=='SJ413' else 1.,centre_lock_when_on=1. if car=='SJ413' else 0.)
        save_bp(bp)
        gm=blueprint('BP_'+car+'_TestGameMode',u.GTRunGameMode)
        prop(u.get_default_object(gm.generated_class()),default_pawn_class=bp.generated_class()); save_bp(gm)

        level=TEST_FOLDER+'/L_'+car+'_Test'
        for source,target in [(BASE_MAP,level),(MUD_MAP,TEST_FOLDER+'/L_'+car+'_Mud')]:
            if not E.does_asset_exist(target): assert E.duplicate_asset(source,target)
            assert LES.load_level(target)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            world.get_world_settings().set_editor_property('default_game_mode',gm.generated_class())
            assert LES.save_current_level()
        report['cars'][car]={'mesh':sk.get_path_name(),'pawn':bp.get_path_name(),'map':level,'lod_count':S.get_lod_count(sk),'physics_bodies':bodies,'driver_eye_cm':[eye.x,eye.y,eye.z],'wheel_radius_cm':spec['r']*100,'test_mass_kg':mass,'test_torque_nm':torque,'status':'IMPORTED_RUNTIME_CHECK_PENDING'}
        (OUT/'unreal_import_report.json').write_text(json.dumps(report,indent=2))
        u.log('SPECIALS_IMPORTED '+car+' '+level)
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error']); raise
finally:
    (OUT/'unreal_import_report.json').write_text(json.dumps(report,indent=2))
