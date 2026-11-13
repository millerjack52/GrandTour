"""Install a reversible bed/surface pilot and capture identical Unreal views."""
import unreal as u
import sys,json,time,traceback,array,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'ChannelPilot'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
import benmore_channel_pilot_materials as mats
DEST=mats.DEST;LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeChannelPilot'
eal=u.EditorAssetLibrary;act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);assets=u.AssetToolsHelpers.get_asset_tools()
grid=array.array('f');grid.frombytes((BASE/'RiverLife/height_local_south_up.f32').read_bytes())
report={'ok':False,'images':[],'driving_tested':False,'timings_collected':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
busy=False;cache={}

def height(x,y):
    fx=max(0,min(2015.999999,(x+1250)/2500*2016));fy=max(0,min(2015.999999,(y+1250)/2500*2016));i=int(fx);j=int(fy);s=fx-i;t=fy-j;k=j*2017+i;q,r,v,w=grid[k],grid[k+1],grid[k+2017],grid[k+2018]
    return q+(r-q)*s+(w-r)*t if s>=t else q+(w-v)*s+(v-q)*t

def signature():
    h=hashlib.sha256();count=0
    for a in sorted(act.get_all_level_actors(),key=lambda a:a.get_actor_label()):
        if a.get_actor_label().startswith('Benmore_CP_'):continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);h.update(array.array('d',[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()]).tobytes());count+=1
    return {'count':count,'sha256':h.hexdigest()}

def refs():return {a.get_actor_label():a for a in act.get_all_level_actors()}

def queries():
    sheet=refs()['Benmore_RS_WaterDomain']
    return [{'name':name,'covers':sheet.covers(u.Vector2D(*p)),'surface_cm':sheet.surface_cm_at(u.Vector2D(*p)),'flow_cmps':sheet.flow_cm_per_s_at(u.Vector2D(*p)).to_tuple()} for name,p in [('Ford',(-66125,17750)),('Bed',(-60500,23000)),('Bridge',(-40625,43875)),('Lake',(-166800,-2700))]]

def native_support():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)]
    results=[]
    for x,y in [(-661.25,177.5),(-660,179),(-666,177),(-605,230),(-609,227),(-601,234),(-690,145),(-570,263)]:
        z=height(x,y)*100
        hit=u.SystemLibrary.line_trace_single(world,u.Vector(x*100,y*100,z+20000),u.Vector(x*100,y*100,z-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
        assert hit is not None
        actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z
        assert abs(actual-z)<5,(x,y,z,actual)
        results.append({'xy_m':[x,y],'collision_z_cm':actual})
    return results

def texture(name,path,mode='data'):
    task=props(u.AssetImportTask(),filename=str(path),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
    if mode=='data':props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_BILINEAR,never_stream=True)
    elif mode=='normal':props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_NORMALMAP)
    elif mode=='rough':props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE)
    else:props(t,srgb=True,compression_settings=u.TextureCompressionSettings.TC_DEFAULT)
    assert eal.save_loaded_asset(t)

def stones():
    for a in list(act.get_all_level_actors()):
        if a.get_actor_label().startswith('Benmore_CP_'):act.destroy_actor(a)
    rows=json.loads((OUT/'stones.json').read_text());gaps=[];groups={}
    for row in rows:groups.setdefault(row['mesh'],[]).append(row)
    for index,rows in groups.items():
        mesh=u.load_asset('/Game/GrandTour/ArtTests/GravelRoad/SM_GR_Stone'+str(index));assert mesh
        b=mesh.get_bounds();diameter=max(b.box_extent.x,b.box_extent.y)*2
        desc=mesh.get_static_mesh_description(0)
        points=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count())]
        bottom=[p for p in points if p.z<=b.origin.z-b.box_extent.z*.5]
        transforms=[]
        for row in rows:
            x,y=row['xy_m'];s=row['diameter_cm']/diameter
            tr=u.Transform(u.Vector(x*100,y*100,0),u.Rotator(yaw=row['yaw']),u.Vector(s,s,s*row['flatten']))
            limits=[]
            for p in bottom:
                v=u.MathLibrary.transform_location(tr,p);limits.append(height(v.x/100,v.y/100)*100-v.z)
            sink=max(.7,row['diameter_cm']*.09)
            tr.translation=u.Vector(x*100,y*100,min(limits)-sink)
            # Every sampled bottom vertex is embedded, even on a sloping bank.
            gap=max(u.MathLibrary.transform_location(tr,p).z-height(u.MathLibrary.transform_location(tr,p).x/100,u.MathLibrary.transform_location(tr,p).y/100)*100 for p in bottom)
            gaps.append(gap);transforms.append(tr)
        a=act.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label('Benmore_CP_Aggregate'+str(index));a.set_folder_path('Benmore/ChannelPilot')
        c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,transforms,'BenmoreChannelPilot','NoCollision',False)
        c.set_material(0,u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/M_Benmore_VergeStone'))
        c.set_cull_distances(5000,11000);props(c,cast_shadow=False,affect_distance_field_lighting=False,receives_decals=False)
    assert max(gaps)<0
    report['aggregate']={'count':len(gaps),'max_bottom_gap_cm':max(gaps),'cull_start_end_m':[50,110],'collision':False,'crossing_excluded':True}

def install():
    for name in ['T_CP_BedZones','T_CP_Shore']:texture(name,OUT/(name+'.png'))
    source=ROOT/'Art/Textures/RiverBed'
    for name,file,mode in [('T_CP_RiverColor','river_small_rocks_diff_2k.jpg','color'),('T_CP_RiverNormal','river_small_rocks_nor_dx_2k.jpg','normal'),('T_CP_RiverRough','river_small_rocks_rough_2k.jpg','rough')]:texture(name,source/file,mode)
    terrain,field,water=mats.make();bylabel=refs()
    land=next(a for a in bylabel.values() if isinstance(a,u.Landscape));land.set_editor_property('landscape_material',terrain)
    provider=bylabel['Benmore_RL_CrossingProfiles'];old=provider.get_editor_property('spec_asset')
    profile=u.load_asset(DEST+'/DA_CP_CrossingProfiles') or eal.duplicate_asset(old.get_path_name().split('.')[0],DEST+'/DA_CP_CrossingProfiles')
    # Copy current authored settings before changing only their material reference.
    spec=old.get_editor_property('spec');sections=list(spec.get_editor_property('sections'))
    for section in sections:
        deform=section.get_editor_property('deform');deform.set_editor_property('surface_material_path',field.get_path_name());section.set_editor_property('deform',deform)
    spec.set_editor_property('sections',sections);profile.set_editor_property('spec',spec);assert eal.save_loaded_asset(profile)
    provider.set_editor_property('spec_asset',profile)
    task=props(u.AssetImportTask(),filename=str(OUT/'SM_CP_RiverSurface.fbx'),destination_path=DEST,destination_name='SM_CP_RiverSurface',automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/SM_CP_RiverSurface');assert mesh
    mesh.set_material(0,water);assert eal.save_loaded_asset(mesh)
    stream=bylabel['Benmore_RL_Stream'];stream.static_mesh_component.set_static_mesh(mesh);stream.static_mesh_component.set_material(0,water)
    bylabel['Benmore_RL_Outlet'].static_mesh_component.set_material(0,water)
    bylabel['Benmore_RS_WaterDomain'].set_editor_property('surface_material_path',water.get_path_name())
    stones()
    assert signature()==report['instances_before']
    assert queries()==report['queries_before']
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    report['saved_and_reloaded']=True;report['instances_after']=signature();report['queries_after']=queries()
    assert report['instances_before']==report['instances_after'];assert report['queries_before']==report['queries_after']
    report['native_support_after']=native_support();assert report['native_support_before']==report['native_support_after']
    bylabel=refs();provider=bylabel['Benmore_RL_CrossingProfiles']
    report['deformation_materials']=[s.get_editor_property('deform').get_editor_property('surface_material_path') for s in provider.get_editor_property('spec_asset').get_editor_property('spec').get_editor_property('sections')]
    assert all('M_CP_DeformField' in p for p in report['deformation_materials'])

def views():
    z=height(-605,230)*100
    return [('Ford',(-65550,17800,1780),(-66125,17750,1585),(-66125,17750)),
            ('Bed',(-60000,23120,z+260),(-60600,23000,z+20),(-60500,23000)),
            ('Reach',(-64000,16000,4500),(-62500,21300,2000),(-62500,21300))]

def capture(suffix):
    bylabel=refs();sheet=bylabel['Benmore_RS_WaterDomain'];camera=bylabel['Benmore_RL_Camera_Ford']
    for name,pos,target,focus in views():
        sheet.preview_water_at(u.Vector2D(*focus),0,True)
        components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
        for c in components:
            m=c.get_material(0)
            if isinstance(m,u.MaterialInstanceDynamic):m.set_scalar_parameter_value('WaterTimeOverride',12)
        camera.set_actor_location(u.Vector(*pos),False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
        u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
        yield 30 if name=='Ford' else 12
        path=OUT/(name+'_'+suffix+'.png');requested=time.time()
        u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera);yield 2
        while not path.exists() or path.stat().st_mtime<requested:
            if time.time()-requested>45:raise RuntimeError('Screenshot timeout: '+str(path))
            yield 1
        report['images'].append(str(path))
        if name=='Bed':
            # A diagnostic bed view isolates aggregate scale/grounding from optics.
            for c in components:c.set_visibility(False,True)
            yield 1
            path=OUT/('Bed_Bare_'+suffix+'.png');requested=time.time()
            u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera);yield 2
            while not path.exists() or path.stat().st_mtime<requested:
                if time.time()-requested>45:raise RuntimeError('Bare-bed screenshot timeout')
                yield 1
            report['images'].append(str(path))
            for c in components:c.set_visibility(True,True)

def run():
    assert les.load_level(LEVEL)
    if not eal.does_asset_exist(BACKUP):
        # Duplicating an already loaded World leaves a standalone duplicate that
        # UE 5.8 refuses to collect on map load. Save a map copy through the editor.
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),BACKUP)
        assert les.load_level(LEVEL)
    report['backup']=BACKUP
    # Always compare against the preserved baseline, including retries.
    assert les.load_level(BACKUP);report['instances_before']=signature();report['queries_before']=queries();report['native_support_before']=native_support()
    report['drive_map_hash_before']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest()
    yield from capture('Before')
    assert les.load_level(LEVEL)
    u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    install();yield 20
    yield from capture('After')
    prepare=json.loads((OUT/'prepare-report.json').read_text())
    for path,value in prepare['source_hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==value
    report['drive_map_hash_after']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest()
    assert report['drive_map_hash_before']==report['drive_map_hash_after']
    report.update(terrain_heights_changed=False,water_query_data_changed=False,prepare=prepare)
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    assert signature()==report['instances_before'];report['ok']=True

def finish(error=None):
    global gen
    gen=None
    if error:report['ok']=False;report['error']=error;u.log_error(error)
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

gen=run();next_at=time.monotonic();started=next_at
def tick(dt):
    global next_at,busy
    if busy:return
    try:
        if time.monotonic()-started>720:raise RuntimeError('Channel pilot install timeout')
        if time.monotonic()<next_at:return
        busy=True;next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
