"""Install/reload whole-water interaction and capture several review views."""
import unreal as u
import sys,json,time,traceback,array,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_domain_material import make,DEST
from benmore_river_life_materials import props
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeWaterDetail'
eal=u.EditorAssetLibrary;act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'images':[],'driving_tested':False,'timings_collected':False};phase='load';last=time.monotonic();started=last;index=0
u.EditorPythonScripting.set_keep_python_script_alive(True)

def signature():
    h=hashlib.sha256();count=0
    for a in sorted(act.get_all_level_actors(),key=lambda a:a.get_actor_label()):
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);h.update(array.array('d',[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()]).tobytes());count+=1
    return {'count':count,'sha256':h.hexdigest()}

def install():
    global sheet,camera,views
    assert les.load_level(LEVEL)
    if not eal.does_asset_exist(BACKUP):assert eal.duplicate_asset(LEVEL,BACKUP)
    report['backup']=BACKUP;report['instances_before']=signature()
    assettools=u.AssetToolsHelpers.get_asset_tools()
    for name in ['T_RS_DomainFlow','T_RS_DomainMask']:
        task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        assettools.import_asset_tasks([task]);tex=u.load_asset(DEST+'/'+name);assert tex
        props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True);assert eal.save_loaded_asset(tex)
    ref=u.load_asset(DEST+'/DA_RS_WaterDomain')
    if not ref:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.GTWaterDomain)
        ref=assettools.create_asset('DA_RS_WaterDomain',DEST,u.GTWaterDomain,factory)
    assert ref.import_bake(str(OUT/'water-domain.bin'));assert eal.save_loaded_asset(ref)
    for kind in ['River','Lake']:
        source=DEST+'/M_RS_Domain'+kind;backup=source+'_BeforeDetail'
        if not eal.does_asset_exist(backup):assert eal.duplicate_asset(source,backup)
    river=make('River');lake=make('Lake')
    bylabel={a.get_actor_label():a for a in act.get_all_level_actors()}
    surfaces=[]
    for label,name in [('Benmore_RL_Stream','SM_RS_RiverSurface'),('Benmore_RL_Outlet','SM_RS_OutletSurface')]:
        a=bylabel[label]
        task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
        props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        task.options=opt;assettools.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
        mesh.set_material(0,river);assert eal.save_loaded_asset(mesh);a.static_mesh_component.set_static_mesh(mesh);a.static_mesh_component.set_material(0,river);surfaces.append(a)
    a=bylabel['Benmore_Vista_Lake'];a.static_mesh_component.set_material(0,lake);surfaces.append(a)
    pilot=bylabel.get('Benmore_RS_LiveFord')
    if pilot:act.destroy_actor(pilot)
    sheet=bylabel.get('Benmore_RS_WaterDomain')
    if not sheet:sheet=act.spawn_actor_from_class(u.GTWaterSheet,u.Vector(-66125,17750,1585));sheet.set_actor_label('Benmore_RS_WaterDomain')
    props(sheet,river_reference=None,river_surface=None,water_domain=ref,domain_surfaces=surfaces,base_level_cm=1585,field_cell_cm=62.5,max_sim_cells=9216,wind_ripple_cm=5,rain_drop_cm=.12,surface_material_path=river.get_path_name(),surface_range_cm=2000,dry_cut_cm=1)
    sheet.set_folder_path('Benmore/RiverScale')
    assert signature()==report['instances_before']
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    sheet=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RS_WaterDomain')
    assert sheet.get_editor_property('water_domain');assert len(sheet.get_editor_property('domain_surfaces'))==3
    assert signature()==report['instances_before'];report['saved_and_reloaded']=True
    # Queries work before building a local window, including the bridge hundreds of metres away.
    report['queries']=[]
    for name,xy in [('Ford',(-66125,17750)),('Footbridge',(-40625,43875)),('Mouth',(-142875,5625)),('Lake',(-166800,-2700))]:
        report['queries'].append({'name':name,'covers':sheet.covers(u.Vector2D(*xy)),'surface_cm':sheet.surface_cm_at(u.Vector2D(*xy)),'flow_cmps':sheet.flow_cm_per_s_at(u.Vector2D(*xy)).to_tuple()})
    assert all(q['covers'] for q in report['queries'])
    sheet.preview_water_at(u.Vector2D(-66125,17750),0,True)
    before=sheet.surface_cm_at(u.Vector2D(-66125,17750));added=sheet.add_impulse(u.Vector2D(-66125,17750),150,5)
    sheet.preview_water_at(u.Vector2D(-66125,17750),.3,False)
    disturbed=sheet.surface_cm_at(u.Vector2D(-66125,17750))
    sheet.preview_water_at(u.Vector2D(-65000,17750),0,False)
    retained=sheet.surface_cm_at(u.Vector2D(-66125,17750))
    report['handoff_preview']={'initial_cm':before,'disturbed_cm':disturbed,'retained_cm':retained,'added_m3':added}
    assert abs(disturbed-before)>.03 and abs(retained-disturbed)<.01
    camera=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RL_Camera_Ford')
    views=[
        ('Ford',(-65550,17800,1780),(-66125,17750,1585),(-66125,17750)),
        ('Ford_Wake',(-65550,17800,1780),(-66125,17750,1585),(-66125,17750)),
        ('Ford_Wake4s',(-65550,17800,1780),(-66125,17750,1585),(-66125,17750)),
        ('Upstream',(-39425,42375,5296),(-40625,43875,4955),(-40625,43875)),
        ('Reach',(-55625,11250,6375),(-58125,25750,2375),(-59000,25000)),
        ('Mouth',(-138000,0,1500),(-142875,5625,90),(-142875,5625)),
    ]

def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'domain-install-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global phase,last,index,task
    try:
        now=time.monotonic()
        if now-started>1000:raise RuntimeError('Water domain setup timeout')
        if phase=='load':phase='installing';install();phase='view'
        elif phase=='view':
            phase='moving';name,pos,target,focus=views[index]
            sheet.preview_water_at(u.Vector2D(*focus),0,True)
            if 'Wake' in name:
                sheet.preview_water_wake(u.Vector2D(focus[0]-300,focus[1]),u.Vector2D(focus[0]+300,focus[1]),3)
                if name.endswith('4s'):sheet.preview_water_at(u.Vector2D(*focus),4,False)
            camera.set_actor_location(u.Vector(*pos),False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
            u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation());phase='warm';last=now
        elif phase=='warm' and now-last>25:
            phase='capturing';path=OUT/('Domain_'+views[index][0]+'.png');task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera);report['images'].append(str(path));phase='shot';last=now
        elif phase=='shot' and now-last>4:
            assert Path(report['images'][-1]).exists();index+=1
            if index<len(views):phase='view'
            else:finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
