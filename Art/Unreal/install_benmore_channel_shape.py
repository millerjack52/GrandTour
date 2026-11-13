"""Install native continuous banks, matched water and regrounded supports."""
import unreal as u
import sys,json,time,traceback,array,hashlib,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'ChannelShape'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props,Graph
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ChannelShape'
PILOT='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ChannelPilot'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeChannelShape'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);assets=u.AssetToolsHelpers.get_asset_tools()
before=array.array('f');before.frombytes((BASE/'RiverLife/height_local_south_up.f32').read_bytes())
after=array.array('f');after.frombytes((OUT/'height_local_south_up.f32').read_bytes())
BASELINE_ONLY='-GTChannelBaseline' in u.SystemLibrary.get_command_line()
VERIFY_ONLY='-GTChannelVerifyOnly' in u.SystemLibrary.get_command_line()
prepare=None if BASELINE_ONLY else json.loads((OUT/'prepare-report.json').read_text())
if prepare:assert prepare['ok']
report=dict(ok=False,images=[],driving_tested=False,timings_collected=False)
grid=before;cache={};busy=False
if VERIFY_ONLY:
    report=json.loads((OUT/'install-report.json').read_text());assert report['saved_and_reloaded']
    report.pop('error',None);report['ok']=False;grid=after
u.EditorPythonScripting.set_keep_python_script_alive(True)

def height(a,x,y):
    fx=max(0,min(2015.999999,(x+1250)*2016/2500));fy=max(0,min(2015.999999,(y+1250)*2016/2500));i=int(fx);j=int(fy);s=fx-i;t=fy-j;k=j*2017+i;q,r,v,w=a[k],a[k+1],a[k+2017],a[k+2018]
    return q+(r-q)*s+(w-r)*t if s>=t else q+(w-v)*s+(v-q)*t

def refs():return {a.get_actor_label():a for a in act.get_all_level_actors()}

def signature(xy_only=False,labels=None):
    h=hashlib.sha256();count=0
    for a in sorted(act.get_all_level_actors(),key=lambda a:a.get_actor_label()):
        if labels and a.get_actor_label() not in labels:continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
            h.update((a.get_actor_label()+'|'+c.get_name()).encode())
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);p=t.translation
                values=[p.x,p.y] if xy_only else [p.x,p.y,p.z]
                h.update(array.array('d',values if xy_only else values+list(t.rotation.to_tuple())+list(t.scale3d.to_tuple())).tobytes());count+=1
    return dict(count=count,sha256=h.hexdigest())

def queries():
    sheet=refs()['Benmore_RS_WaterDomain']
    return [dict(name=name,covers=sheet.covers(u.Vector2D(*p)),surface_cm=sheet.surface_cm_at(u.Vector2D(*p)),flow_cmps=sheet.flow_cm_per_s_at(u.Vector2D(*p)).to_tuple()) for name,p in [('Ford',(-66125,17750)),('Bed',(-60500,23000)),('Bridge',(-40625,43875)),('Lake',(-166800,-2700))]]

def profiles():
    provider=refs()['Benmore_RL_CrossingProfiles'];sections=provider.get_editor_property('spec_asset').get_editor_property('spec').get_editor_property('sections')
    return [dict(start_m=s.get_editor_property('start_m'),end_m=s.get_editor_property('end_m'),deform={k:s.get_editor_property('deform').get_editor_property(k) for k in ['max_sinkage_m','sinkage_rate','cell_cm','ridge_width_cm','max_ridge_cm','repose_deg','slump_rate']}) for s in sections]

def native_support():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)];results=[]
    points=[(-661.25,177.5),(-660,179),(-666,177),(-605,230),(-609,227),(-601,234),(-690,145),(-570,263),(-406.25,438.75)]
    if (OUT/'support-checks.json').exists():points+=json.loads((OUT/'support-checks.json').read_text())
    for x,y in points:
        z=height(grid,x,y)*100
        hit=u.SystemLibrary.line_trace_single(world,u.Vector(x*100,y*100,z+20000),u.Vector(x*100,y*100,z-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit
        actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z
        assert abs(actual-z)<5,(x,y,z,actual)
        results.append(dict(xy_m=[x,y],expected_z_cm=z,collision_z_cm=actual,error_cm=abs(actual-z)))
    return results

def texture(name,exact=False):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST if exact else u.TextureFilter.TF_BILINEAR,never_stream=True)
    assert eal.save_loaded_asset(t);return t

def clone_material(source,name,textures):
    m=u.load_asset(DEST+'/'+name) or eal.duplicate_asset(source,DEST+'/'+name);assert m
    for n in mel.get_material_expressions(m):
        if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter)):
            t=n.get_editor_property('texture')
            if t and t.get_name() in textures:n.set_editor_property('texture',textures[t.get_name()])
    errors=mel.recompile_material(m);assert not errors,list(errors)
    assert eal.save_loaded_asset(m);return m

def import_mesh(name,water):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
    mesh.set_material(0,water);assert eal.save_loaded_asset(mesh);return mesh

def reground():
    # Integral image makes the changed-ground support test inexpensive over 90k
    # authored instances. Only changed footprints require vertex-level seating.
    prefix=array.array('I');prefix.frombytes((OUT/'changed-prefix.u32').read_bytes());side=2018
    def touched(tr,mesh):
        p=tr.translation;b=mesh.get_bounds();scale=tr.scale3d
        radius=math.sqrt(b.box_extent.x**2+b.box_extent.y**2+b.box_extent.z**2)*max(abs(scale.x),abs(scale.y),abs(scale.z))
        radius+=math.sqrt(b.origin.x**2+b.origin.y**2+b.origin.z**2)*max(abs(scale.x),abs(scale.y),abs(scale.z))
        lo=[int(math.floor((v-radius+125000)/250000*2016)) for v in [p.x,p.y]];hi=[int(math.ceil((v+radius+125000)/250000*2016))+1 for v in [p.x,p.y]]
        if hi[0]<0 or hi[1]<0 or lo[0]>2017 or lo[1]>2017:return False
        x0,y0=[max(0,min(2017,v)) for v in lo];x1,y1=[max(0,min(2017,v)) for v in hi]
        return prefix[y1*side+x1]-prefix[y1*side+x0]-prefix[y0*side+x1]+prefix[y0*side+x0]>0
    def seat(tr,mesh,label):
        key=mesh.get_path_name()
        if key not in cache:
            b=mesh.get_bounds();desc=mesh.get_static_mesh_description(0);cut=b.origin.z-b.box_extent.z*.5
            cache[key]=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count()) if desc.get_vertex_position(u.VertexID(i)).z<=cut]
        points=cache[key];assert points,key
        oldlimits=[];newlimits=[];oz=tr.translation.z
        for point in points:
            v=u.MathLibrary.transform_location(tr,point);relative=v.z-oz
            oldlimits.append(height(before,v.x/100,v.y/100)*100-relative);newlimits.append(height(after,v.x/100,v.y/100)*100-relative)
        sink=.7 if label.startswith('Benmore_CP_') else 6
        nz=min(oz+min(newlimits)-min(oldlimits),min(newlimits)-sink)
        tr.translation=u.Vector(tr.translation.x,tr.translation.y,nz)
        return tr,nz-oz,nz-min(newlimits)
    shifted=[];basal=[];max_rotation=0.;max_scale=0.;max_xy=0.
    for a in act.get_all_level_actors():
        label=a.get_actor_label()
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
            mesh=c.get_editor_property('static_mesh')
            if not mesh:continue
            for i in range(c.get_instance_count()):
                tr=c.get_instance_transform(i,True)
                if not touched(tr,mesh):continue
                oldxy=(tr.translation.x,tr.translation.y);oldrotation=tr.rotation.to_tuple();oldscale=tr.scale3d.to_tuple()
                tr,dz,gap=seat(tr,mesh,label)
                if abs(dz)<.01:continue
                assert c.update_instance_transform(i,tr,True,True,True)
                actual=c.get_instance_transform(i,True)
                max_xy=max(max_xy,abs(actual.translation.x-oldxy[0]),abs(actual.translation.y-oldxy[1]))
                # ISM stores matrices; decomposing/recomposing them can round
                # rotation and scale despite preserving the supplied transform.
                max_rotation=max(max_rotation,max(abs(v-w) for v,w in zip(actual.rotation.to_tuple(),oldrotation)))
                max_scale=max(max_scale,max(abs(v-w) for v,w in zip(actual.scale3d.to_tuple(),oldscale)))
                shifted.append(dict(actor=label,index=i,shift_cm=dz));basal.append(gap)
        if isinstance(a,u.StaticMeshActor) and label.startswith(('Benmore_Scenery_','Benmore_Composition_SchistExposure_')):
            tr=a.get_actor_transform();mesh=a.static_mesh_component.static_mesh
            if mesh and touched(tr,mesh):
                tr,dz,gap=seat(tr,mesh,label);a.set_actor_transform(tr,False,True);shifted.append(dict(actor=label,index=-1,shift_cm=dz));basal.append(gap)
    assert basal and max(basal)<=-.69
    (OUT/'regrounded-supports.json').write_text(json.dumps(shifted,indent=2))
    report['regrounding']=dict(count=len(shifted),maximum_basal_gap_cm=max(basal),z_shift_range_cm=[min(p['shift_cm'] for p in shifted),max(p['shift_cm'] for p in shifted)],maximum_xy_change_cm=max_xy,maximum_quaternion_component_change=max_rotation,maximum_scale_component_change=max_scale)
    assert max_xy==0 and max_rotation<1e-5 and max_scale<1e-5,report['regrounding']

def install_assets():
    bylabel=refs();land=next(a for a in bylabel.values() if isinstance(a,u.Landscape))
    textures={name:texture(name) for name in ['T_CP_BedZones','T_CP_Shore','T_RL_Ecology','T_RL_Vegetation','T_RL_WaterMask','T_RS_DomainFlow','T_RS_DomainMask']}
    terrain=clone_material(PILOT+'/M_CP_Terrain','M_CS_Terrain',textures)
    field=clone_material(PILOT+'/M_CP_DeformField','M_CS_DeformField',textures)
    water=clone_material(PILOT+'/M_CP_DomainRiver','M_CS_DomainRiver',textures)
    lake=clone_material('/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale/M_RS_DomainLake','M_CS_DomainLake',textures)
    land.set_editor_property('landscape_material',terrain)
    provider=bylabel['Benmore_RL_CrossingProfiles'];old=provider.get_editor_property('spec_asset')
    profile=u.load_asset(DEST+'/DA_CS_CrossingProfiles') or eal.duplicate_asset(old.get_path_name().split('.')[0],DEST+'/DA_CS_CrossingProfiles')
    spec=old.get_editor_property('spec');sections=list(spec.get_editor_property('sections'))
    for section in sections:
        deform=section.get_editor_property('deform');deform.set_editor_property('surface_material_path',field.get_path_name());section.set_editor_property('deform',deform)
    spec.set_editor_property('sections',sections);profile.set_editor_property('spec',spec);assert eal.save_loaded_asset(profile);provider.set_editor_property('spec_asset',profile)
    ref=u.load_asset(DEST+'/DA_CS_WaterDomain') or eal.duplicate_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale/DA_RS_WaterDomain',DEST+'/DA_CS_WaterDomain')
    assert ref.import_bake(str(OUT/'water-domain.bin'));assert eal.save_loaded_asset(ref)
    for label,name in [('Benmore_RL_Stream','SM_CS_RiverSurface'),('Benmore_RL_Outlet','SM_CS_OutletSurface')]:
        mesh=import_mesh(name,water);bylabel[label].static_mesh_component.set_static_mesh(mesh);bylabel[label].static_mesh_component.set_material(0,water)
    bylabel['Benmore_Vista_Lake'].static_mesh_component.set_material(0,lake)
    sheet=bylabel['Benmore_RS_WaterDomain'];sheet.set_editor_property('water_domain',ref);sheet.set_editor_property('surface_material_path',water.get_path_name())
    reground()
    assert signature(True)==report['placement_before'];assert signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail'])==report['roads_before']
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    report['saved_and_reloaded']=True;report['placement_after']=signature(True);report['roads_after']=signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail'])
    report['queries_after']=queries();report['native_support_after']=native_support()
    assert report['placement_before']==report['placement_after'];assert report['roads_before']==report['roads_after']
    assert all(q['covers'] for q in report['queries_after'])
    for q in report['queries_after']:
        if q['name'] in prepare['queries']:assert abs(q['surface_cm']-prepare['queries'][q['name']]['surface_m']*100)<.01
    assert abs(report['queries_after'][0]['surface_cm']-report['queries_before'][0]['surface_cm'])<6
    provider=refs()['Benmore_RL_CrossingProfiles'];report['deformation_materials']=[s.get_editor_property('deform').get_editor_property('surface_material_path') for s in provider.get_editor_property('spec_asset').get_editor_property('spec').get_editor_property('sections')]
    assert all('M_CS_DeformField' in p for p in report['deformation_materials'])
    report['profiles_after']=profiles();assert report['profiles_after']==report['profiles_before']
    assert mel.get_material_property_input_node(u.load_asset(DEST+'/M_CS_DeformField'),u.MaterialProperty.MP_WORLD_POSITION_OFFSET)

def views():
    z=height(before,-605,230)*100
    return [('Ford',(-65550,17800,1780),(-66125,17750,1585),(-66125,17750)),
            ('Bed',(-60000,23120,z+260),(-60600,23000,z+20),(-60500,23000)),
            ('Reach',(-64000,16000,4500),(-62500,21300,2000),(-62500,21300)),
            ('Plan',(-62500,21000,6400),(-62500,21200,2050),(-62500,21300))]

def capture(suffix):
    bylabel=refs();sheet=bylabel['Benmore_RS_WaterDomain'];camera=bylabel['Benmore_RL_Camera_Ford']
    for name,pos,target,focus in views():
        sheet.preview_water_at(u.Vector2D(*focus),0,True)
        components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
        for c in components:
            m=c.get_material(0)
            if isinstance(m,u.MaterialInstanceDynamic):m.set_scalar_parameter_value('WaterTimeOverride',12)
        camera.set_actor_location(u.Vector(*pos),False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
        u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation());yield 35 if name=='Ford' else 15
        for bare in [False,True] if name in ['Bed','Plan'] else [False]:
            if bare:
                for c in components:c.set_visibility(False,True)
                yield 2
            path=OUT/(name+('_Bare' if bare else '')+'_'+suffix+'.png');requested=time.time()
            u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera);yield 3
            while not path.exists() or path.stat().st_mtime<requested:
                if time.time()-requested>60:raise RuntimeError('Screenshot timeout: '+str(path))
                yield 1
            report['images'].append(str(path))
            if bare:
                for c in components:c.set_visibility(True,True)

def verify_saved_height():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
    rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);yield 10
    assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 10
    assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 5
    pixels=u.RenderingLibrary.read_render_target(world,rt,False);values=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
    (OUT/'reloaded-native-height.r16').write_bytes(values.tobytes())
    report['reloaded_native_height_sha256']=hashlib.sha256(values.tobytes()).hexdigest();assert report['reloaded_native_height_sha256']==prepare['terrain_height_sha256']

def run():
    global grid
    assert les.load_level(LEVEL)
    if VERIFY_ONLY:
        assert signature(True)==report['placement_before']
        assert signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail'])==report['roads_before']
        assert profiles()==report['profiles_before']
        assert json.loads(json.dumps(queries()))==report['queries_after']
        report['native_support_after']=native_support()
        yield from verify_saved_height()
        yield from capture('After')
        assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
        report['drive_map_hash']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest();assert report['drive_map_hash']==prepare['source_original_drive_sha256']
        report['prepare']=prepare;report['ok']=True;return
    if not eal.does_asset_exist(BACKUP):
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),BACKUP);assert les.load_level(LEVEL)
    assert les.load_level(BACKUP);report['backup']=BACKUP;grid=before
    report['placement_before']=signature(True);report['roads_before']=signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail']);report['queries_before']=queries();report['native_support_before']=native_support();report['profiles_before']=profiles()
    baselinepath=OUT/'baseline-report.json'
    if not BASELINE_ONLY and baselinepath.exists():
        baseline=json.loads(baselinepath.read_text());assert baseline['ok']
        # Legacy baseline signatures included decomposed rotation/scale; that
        # hash cannot be compared with the XY-only signature after re-seating.
        assert baseline['placement_before']['count']==report['placement_before']['count'];assert baseline['queries_before']==json.loads(json.dumps(report['queries_before']))
        assert all(Path(p).exists() for p in baseline['images']);report['images']=baseline['images'];report['reused_baseline_capture']=True
    else:yield from capture('Before')
    if BASELINE_ONLY:
        assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL);report['ok']=True;return
    # Rebuild from the preserved baseline on retries, avoiding a second seating
    # offset if an earlier install saved successfully but failed during capture.
    assert les.load_level(BACKUP)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
    tex=texture('T_CS_HeightRG',True)
    transfer=u.load_asset(DEST+'/M_CS_HeightTransfer') or assets.create_asset('M_CS_HeightTransfer',DEST,u.Material,u.MaterialFactoryNew())
    for n in list(mel.get_material_expressions(transfer)):mel.delete_material_expression(transfer,n)
    props(transfer,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=Graph(transfer);n=g.node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);g.output(n,u.MaterialProperty.MP_EMISSIVE_COLOR,'RGB')
    assert not mel.recompile_material(transfer);assert eal.save_loaded_asset(transfer)
    rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);yield 20
    u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);yield 10
    u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);assert land.landscape_import_heightmap_from_render_target(rt,True,0);yield 25
    assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 10
    assert land.landscape_export_heightmap_to_render_target(rt,True,True)
    pixels=u.RenderingLibrary.read_render_target(world,rt,False);values=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
    checksum=hashlib.sha256(values.tobytes()).hexdigest();assert checksum==prepare['terrain_height_sha256'];report['native_height_sha256']=checksum;grid=after
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0');install_assets()
    # Verify the serialized native bed again after the provider/material changes.
    yield from verify_saved_height()
    u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'grass.FlushCache');yield 20
    yield from capture('After')
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    assert signature(True)==report['placement_before']
    report['drive_map_hash']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest();assert report['drive_map_hash']==prepare['source_original_drive_sha256']
    report['prepare']=json.loads((OUT/'prepare-report.json').read_text());report['ok']=True

def finish(error=None):
    global gen
    gen=None
    if error:report['ok']=False;report['error']=error;u.log_error(error)
    (OUT/('baseline-report.json' if BASELINE_ONLY else 'install-report.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

gen=run();next_at=time.monotonic();started=next_at
def tick(dt):
    global next_at,busy
    if busy:return
    try:
        if time.monotonic()-started>1500:raise RuntimeError('Channel shape install timeout')
        if time.monotonic()<next_at:return
        busy=True;delay=next(gen);next_at=time.monotonic()+delay
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
