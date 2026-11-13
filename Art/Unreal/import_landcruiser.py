"""Import the reviewed LC80 package into its own folder and inspection map.
Run only with the interactive editor closed. Does not replace the current car.
"""
import unreal as u,json,traceback,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();SRC=ROOT/'Art/Export/LandCruiser/Package_v03'
DEST='/Game/GrandTour/Vehicles/Bodies/LandCruiser80';MAP='/Game/GrandTour/ArtTests/LandCruiser80/L_LandCruiserReview'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);V=u.GTVehicleSetupLibrary
report={'status':'STARTED','source':'Package_v03','mesh':DEST+'/SK_LandCruiser80','review_level':MAP,'checks':{},'limitations':['Art import and inspection scene; not wired into the selectable/drivable vehicle system.','Root box is initial collision only; compound fitting and driving validation remain pending.']}
def prop(obj,**kw):
    for k,v in kw.items():obj.set_editor_property(k,v)
    return obj
def log(msg):u.log('LC_IMPORT '+msg)
def material(name):
    path=DEST+'/Materials/'+name;m=E.load_asset(path) if E.does_asset_exist(path) else None
    if m:M.delete_all_material_expressions(m)
    else:m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    M.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
    return m
def expr(m,c,**props):return prop(M.create_material_expression(m,c),**props)
def pin(node,out,target):
    assert M.connect_material_property(node,out,target)
def scalar(m,value,target):pin(expr(m,u.MaterialExpressionConstant,r=value),'',target)
def compile_mat(m):
    errors=M.recompile_material(m)
    assert not errors,(m.get_name(),errors)
    E.save_loaded_asset(m)
def texture(name,orm):
    task=prop(u.AssetImportTask(),filename=str(SRC/(name+'.png')),destination_path=DEST+'/Textures',destination_name=name,automated=True,replace_existing=True,save=False)
    A.import_asset_tasks([task]);tex=E.load_asset(DEST+'/Textures/'+name);assert tex
    prop(tex,srgb=not orm,compression_settings=u.TextureCompressionSettings.TC_MASKS if orm else u.TextureCompressionSettings.TC_DEFAULT,compression_no_alpha=True)
    assert tex.blueprint_get_size_x()==2048 and tex.blueprint_get_size_y()==2048
    E.save_loaded_asset(tex);return tex
def spawn(world,cls,label,pos=(0,0,0),rot=(0,0,0)):
    a=V.spawn_actor_of_class(world,cls,u.Transform(u.Vector(*pos),u.Rotator(*rot),u.Vector(1,1,1)),label);assert a;return a
try:
    checks=json.loads((SRC/'validation_report.json').read_text())
    assert hashlib.sha256((SRC/'SK_LandCruiser80.fbx').read_bytes()).hexdigest()==checks['roundtrip_LOD0']['fbx_sha256']
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    task=prop(u.AssetImportTask(),filename=str(SRC/'SK_LandCruiser80.fbx'),destination_path=DEST,automated=True,replace_existing=True,save=True)
    ui=prop(u.FbxImportUI(),import_mesh=True,import_as_skeletal=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=True,mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH)
    prop(ui.skeletal_mesh_import_data,import_uniform_scale=1.,convert_scene=True,force_front_x_axis=False,convert_scene_unit=True,import_morph_targets=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE)
    task.options=ui;A.import_asset_tasks([task]);sk=E.load_asset(DEST+'/SK_LandCruiser80');assert sk,'Mesh import failed'
    for lod in [1,2]:assert S.import_lod(sk,lod,str(SRC/('SK_LandCruiser80_LOD'+str(lod)+'.fbx')))==lod
    assert S.get_lod_count(sk)==3
    mats={}
    for name in ['Exterior','Interior']:
        m=material('M_LC80_'+name);c=texture('T_LC80_'+name+'_BaseColor',False);orm=texture('T_LC80_'+name+'_ORM',True)
        cs=expr(m,u.MaterialExpressionTextureSample,texture=c,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        os=expr(m,u.MaterialExpressionTextureSample,texture=orm,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        pin(cs,'RGB',u.MaterialProperty.MP_BASE_COLOR);pin(os,'G',u.MaterialProperty.MP_ROUGHNESS);pin(os,'B',u.MaterialProperty.MP_METALLIC)
        compile_mat(m);mats[name]=m
    m=material('M_LC80_Markings');pin(expr(m,u.MaterialExpressionVertexColor),'',u.MaterialProperty.MP_BASE_COLOR);scalar(m,.6,u.MaterialProperty.MP_ROUGHNESS);compile_mat(m);mats['Markings']=m
    m=material('M_LC80_Glass');prop(m,blend_mode=u.BlendMode.BLEND_TRANSLUCENT,two_sided=True,translucency_lighting_mode=u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    pin(expr(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.34,.46,.52,1)),'',u.MaterialProperty.MP_BASE_COLOR)
    scalar(m,.13,u.MaterialProperty.MP_OPACITY);scalar(m,.10,u.MaterialProperty.MP_ROUGHNESS);scalar(m,.8,u.MaterialProperty.MP_SPECULAR);compile_mat(m);mats['Glass']=m
    slots=list(sk.get_editor_property('materials'));assert len(slots)==4,len(slots)
    slot_report=[]
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        key=next((k for k in mats if k in name),None);assert key,name
        slot.material_interface=mats[key];slot_report.append({'slot':name,'material':mats[key].get_path_name()})
    sk.set_editor_property('materials',slots)
    pa=sk.get_editor_property('physics_asset')
    if not pa:pa=S.create_physics_asset(sk,True,0)
    assert pa,'Explicit physics asset creation failed'
    for prefix in ['Wheel_','Door_','Hood','Tailgate','Steering','Needle_']:V.remove_bodies_by_bone_prefix(pa,prefix)
    assert V.set_box_body(pa,sk,'Root',u.Vector(-8,0,115),u.Vector(445,170,120))
    V.enable_hit_events(pa);bodies=[str(x) for x in V.describe_bodies(pa)];body_lines=[x for x in bodies if 'physicsType=' in x];assert len(body_lines)==1 and body_lines[0].startswith('Root ') and 'constraints=0' in bodies,bodies
    E.save_loaded_asset(pa);E.save_loaded_asset(sk);E.save_loaded_asset(sk.get_editor_property('skeleton'))
    # Own level: default game mode provides a spectator for asset inspection.
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if E.does_asset_exist(MAP):assert les.load_level(MAP)
    else:assert les.new_level(MAP)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    V.destroy_actors_with_label_prefix(world,'LC80_')
    world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
    actor=spawn(world,u.SkeletalMeshActor,'LC80_Imported',pos=(0,0,0))
    comp=actor.get_component_by_class(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(sk);comp.set_simulate_physics(False);comp.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
    names=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())];expected=json.loads((SRC/'asset_report.json').read_text())['bones'];assert set(names)==set(expected),(names,expected)
    coords={}
    for n in ['Root','Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']:
        t=comp.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT);v=t.translation;coords[n]=[v.x,v.y,v.z]
    assert abs(coords['Wheel_FL'][0]-coords['Wheel_RL'][0]-285)<.1,coords
    assert abs(coords['Wheel_FR'][1]-coords['Wheel_FL'][1]-160)<.1,coords
    assert abs(coords['Wheel_FL'][2]-41.5)<.1,coords
    b=sk.get_bounds();dims=[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2];assert 480<dims[0]<495 and 220<dims[1]<235 and 185<dims[2]<195,dims
    cube=E.load_asset('/Engine/BasicShapes/Cube');floor=V.spawn_static_mesh_actor(world,cube,u.Transform(u.Vector(0,0,-10),u.Rotator(),u.Vector(200,200,.2)),'LC80_Floor')
    fm=material('M_LC80_ReviewFloor');pin(expr(fm,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.12,.14,.16,1)),'',u.MaterialProperty.MP_BASE_COLOR);scalar(fm,.8,u.MaterialProperty.MP_ROUGHNESS);compile_mat(fm);floor.get_component_by_class(u.StaticMeshComponent).set_material(0,fm)
    sun=spawn(world,u.DirectionalLight,'LC80_Sun',pos=(0,0,600),rot=(-35,-35,0));sun.get_component_by_class(u.DirectionalLightComponent).set_intensity(4.)
    sky=spawn(world,u.SkyLight,'LC80_Sky',pos=(0,0,500));prop(sky.get_component_by_class(u.SkyLightComponent),real_time_capture=True,intensity=.8)
    spawn(world,u.SkyAtmosphere,'LC80_Atmosphere')
    pp=spawn(world,u.PostProcessVolume,'LC80_Exposure');prop(pp,unbound=True);settings=pp.get_editor_property('settings');prop(settings,override_auto_exposure_min_brightness=True,override_auto_exposure_max_brightness=True,auto_exposure_min_brightness=.25,auto_exposure_max_brightness=.25,override_motion_blur_amount=True,motion_blur_amount=0.);pp.set_editor_property('settings',settings)
    for name,pos,target in [('Front',(620,-600,300),(0,0,98)),('Rear',(-660,590,300),(-25,0,100)),('Cockpit',(-64,45.5,157),(70,22,112))]:
        camera=spawn(world,u.CameraActor,'LC80_Camera_'+name,pos=pos)
        rotation=u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target));camera.set_actor_rotation(rotation,False)
        cc=camera.get_component_by_class(u.CameraComponent);cc.set_field_of_view(90 if name=='Cockpit' else 40)
    start=spawn(world,u.PlayerStart,'LC80_PlayerStart',pos=(620,-600,300));start.set_actor_rotation(u.MathLibrary.find_look_at_rotation(start.get_actor_location(),u.Vector(0,0,98)),False)
    assert les.save_current_level()
    report['checks']={'bounds_cm':dims,'bone_count':len(names),'reference_bones_cm':coords,'material_slots':slot_report,'lod_count':S.get_lod_count(sk),'lod_sections':[S.get_num_sections(sk,i) for i in range(3)],'lod_vertices':[S.get_num_verts(sk,i) for i in range(3)],'physics_bodies':bodies,'material_graph_compilation':'PASS','textures':'four 2048px maps; albedo sRGB, ORM linear; markings vertex colour'}
    report['status']='IMPORTED';log('SUCCESS '+MAP)
except Exception:
    report['status']='FAILED';report['error']=traceback.format_exc();u.log_error(report['error']);raise
finally:(SRC/'unreal_import_report.json').write_text(json.dumps(report,indent=2))
