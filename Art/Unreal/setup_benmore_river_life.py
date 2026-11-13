"""Install native riverbed, baked flow, grounded ecology and crossing profiles."""
import unreal as u
from pathlib import Path
import array,hashlib,json,sys,time,traceback
ROOT=Path(u.Paths.project_dir()).resolve();BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'RiverLife';sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_river_life_materials as mats
DEST=mats.DEST;LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview';BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaBeforeRiverLife'
data=json.loads((OUT/'assets.json').read_text());flow_report=json.loads((OUT/'flow-report.json').read_text());assert data['ok'] and flow_report['ok']
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
grid=array.array('f');grid.frombytes((OUT/'height_local_south_up.f32').read_bytes());old=array.array('f');old.frombytes((BASE/'candidate/height_local_south_up.f32').read_bytes())
shore=array.array('f');shore.frombytes((OUT/'shore_distance.f32').read_bytes());trail=array.array('f');trail.frombytes((OUT/'path_mask.f32').read_bytes())
N=2017;phase='load';started=time.monotonic();last=started;cache={};support=[];report={'ok':False,'level':LEVEL,'stages':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
props=mats.props

def height(a,x,y):
    fx=max(0,min(2015.999999,(x+1250)/2500*2016));fy=max(0,min(2015.999999,(y+1250)/2500*2016));i=int(fx);j=int(fy);s=fx-i;t=fy-j;k=j*N+i;q,r,v,w=a[k],a[k+1],a[k+N],a[k+N+1]
    return q+(r-q)*s+(w-r)*t if s>=t else q+(w-v)*s+(v-q)*t

def texture(name,exact=False):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True);assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS if exact else u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP,filter=u.TextureFilter.TF_NEAREST if exact else u.TextureFilter.TF_BILINEAR,never_stream=True)
    assert eal.save_loaded_asset(t);return t

def digest(a):
    h=hashlib.sha256();count=0
    for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,True);h.update(array.array('d',[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()]).tobytes());count+=1
    return [count,h.hexdigest()]

def seat(tr,mesh,sink=7,record=False):
    key=mesh.get_path_name()
    if key not in cache:
        desc=mesh.get_static_mesh_description(0);b=mesh.get_bounds();cut=b.origin.z-b.box_extent.z+b.box_extent.z*.50
        cache[key]=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count()) if desc.get_vertex_position(u.VertexID(i)).z<=cut]
    pts=[];oz=tr.translation.z
    for p in cache[key]:
        v=u.MathLibrary.transform_location(tr,p);z=height(grid,v.x/100,v.y/100)*100;pts.append((z-(v.z-oz),v.x,v.y,z))
    limit,x,y,z=min(pts);tr.translation=u.Vector(tr.translation.x,tr.translation.y,limit-sink)
    if record:support.append([x,y,z,-sink])
    return tr

def import_mesh(name,mat,solid=False):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh;mesh.set_material(0,mat)
    if solid:mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    assert eal.save_loaded_asset(mesh)
    a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label('Benmore_RL_'+name.removeprefix('SM_RL_'));a.static_mesh_component.set_static_mesh(mesh);a.static_mesh_component.set_material(0,mat);a.static_mesh_component.set_collision_profile_name('BlockAll' if solid else 'NoCollision');a.set_actor_enable_collision(solid)
    props(a.static_mesh_component,cast_shadow=solid,affect_distance_field_lighting=solid,receives_decals=solid)
    return a

def dressing():
    cleared={};shifted=0
    for a in list(act.get_all_level_actors()):
        label=a.get_actor_label()
        if label.startswith('Benmore_RL_') or label.startswith('Benmore_Gaea_Art_') or label in ['Benmore_Gaea_CreekSurface','Benmore_Gaea_GravelBars']:
            act.destroy_actor(a);continue
        if isinstance(a,u.LandscapeProxy):continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if not mesh:continue
            remove=[];nature=any(w in label.lower() for w in ['scrub','tussock','grass','willow','scenery','shrub'])
            for i in range(c.get_instance_count()):
                tr=c.get_instance_transform(i,True);p=tr.translation;x=p.x/100;y=p.y/100
                if abs(x)>1249 or abs(y)>1249:continue
                if nature and (height(shore,x,y)<1.15 or height(trail,x,y)>.25):remove.append(i);continue
                dz=height(grid,x,y)-height(old,x,y)
                if abs(dz)<.02:continue
                tr=seat(tr,mesh,6,shifted%30==0);assert c.update_instance_transform(i,tr,True,True,True);shifted+=1
            for i in reversed(remove):assert c.remove_instance(i)
            if remove:cleared[label]=cleared.get(label,0)+len(remove)
        if isinstance(a,u.StaticMeshActor) and label.startswith(('Benmore_Scenery_','Benmore_Composition_SchistExposure_')):
            tr=a.get_actor_transform();p=tr.translation
            if abs(height(grid,p.x/100,p.y/100)-height(old,p.x/100,p.y/100))>.02:a.set_actor_transform(seat(tr,a.static_mesh_component.static_mesh,8,True),False,True)
    groups={}
    for row in json.loads((OUT/'placements.json').read_text()):
        key=(row['kind'],row['mesh'],tuple(row.get('materials',[])))
        groups.setdefault(key,[]).append(row)
    counts={}
    for (kind,path,materials),rows in groups.items():
        mesh=u.load_asset(path);assert mesh,path
        a=act.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label('Benmore_RL_'+kind+'_'+mesh.get_name());transforms=[]
        for i,row in enumerate(rows):
            x,y=row['xy_m'];tr=u.Transform(u.Vector(x*100,y*100,0),u.Rotator(yaw=row['yaw_deg']),u.Vector(*row['scale']));transforms.append(seat(tr,mesh,row['sink_cm'],i%27==0))
        solid=kind in ['tree','rock'];c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,transforms,'BenmoreRiverLife','BlockAll' if solid else 'NoCollision',solid)
        for i,path in enumerate(materials):
            if path:c.set_material(i,u.load_asset(path))
        c.set_cull_distances(45000 if kind=='tree' else 17000,90000 if kind=='tree' else 33000);props(c,affect_distance_field_lighting=solid,receives_decals=False)
        counts[kind]=counts.get(kind,0)+len(rows)
    assert counts==data['counts'];report.update(counts=counts,cleared_instances=cleared,regrounded_instances=shifted)

def profiles(field):
    ford=next(c for c in data['crossings'] if c['name']=='Ford');p=ford['center_m'];n=ford['cross_direction']
    spec=props(u.GTTerrainSpec(),route_m=[u.Vector2D(p[0]-n[0]*30,p[1]-n[1]*30),u.Vector2D(p[0]+n[0]*30,p[1]+n[1]*30)],road_half_width_m=2.1,shoulder_m=1.,alt_routes=[],planes=[],stations=[],features=[],biomes=[],spans=[])
    sections=[]
    for start,end,medium,cap,rate in [(20.,24.,u.GTDeformMedium.MUD,.075,.006),(25.,35.,u.GTDeformMedium.GRAVEL,.035,.005)]:
        profile=props(u.GTDeformProfile(),mode=u.GTDeformProfileMode.ON,medium=medium,surface_material_path=field.get_path_name(),max_sinkage_m=cap,sinkage_rate=rate,cell_cm=12.5,ridge_width_cm=45.,max_ridge_cm=3.5,ridge_blend=1.,ridge_smooth=0.,ridge_foot_cm=18.,ridge_noise=.35,floor_noise_cm=.15,ridge_return=.78,rut_shoulder_cm=14.,rut_shoulder_min_cells=1.,rut_depth_variation=.12,ridge_slump=.08,ridge_slump_floor=.12,ridge_slump_rise_max_cm=.15,ridge_fill_share=.12,repose_deg=37.,slump_rate=3.,ooze_rate=0.,recover_share=0.,creep_cm_per_cm=.15,smear_cm_per_cm=0.,set_seconds=.7,lump_share=0.,lump_max_cm=.7,lump_radius_cells=.8,throw_max=0.,clod_chance=0.,clod_bank_per_cm=0.,clod_throw_chance=0.)
        sections.append(props(u.GTRouteSection(),start_m=start,end_m=end,kind=u.GTRouteSectionKind.ROAD,water_table_cm=-200.,deform=profile))
    spec.sections=sections
    asset=u.load_asset(DEST+'/DA_RL_CrossingProfiles') or assets.create_asset('DA_RL_CrossingProfiles',DEST,u.GTTerrainSpecAsset,u.DataAssetFactory());props(asset,display_name='River crossing deformation only — keep imported Landscape',spec=spec);assert eal.save_loaded_asset(asset)
    assert not any(isinstance(a,u.GTTerrainBuilder) for a in act.get_all_level_actors()),'Another terrain profile provider exists; do not replace it'
    a=act.spawn_actor_from_class(u.GTTerrainBuilder,u.Vector());a.set_actor_label('Benmore_RL_CrossingProfiles');a.set_editor_property('spec_asset',asset)
    report['deformation']={'profiles':2,'existing_subsystem':True,'native_ground_collision':True,'mud_sink_cap_cm':7.5,'gravel_sink_cap_cm':3.5,'runtime_checked':False,'vehicle_water_coupling':False,'warning':'This builder provides runtime profiles only. Never call Rebuild Landscape on this imported heightfield.'}

def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global phase,last,world,land,rt,transfer,watermat,timbermat,road_before
    now=time.monotonic()
    try:
        if now-started>1500:raise RuntimeError('River setup timed out')
        if phase=='load':
            phase='loading';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            if not eal.does_asset_exist(BACKUP):assert u.EditorLoadingAndSavingUtils.save_map(world,BACKUP);assert les.load_level(LEVEL)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
            road_before={label:digest(next(a for a in act.get_all_level_actors() if a.get_actor_label()==label)) for label in ['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail']}
            # Retire our prior install before recreating profiles/actors on a retry.
            for a in list(act.get_all_level_actors()):
                if a.get_actor_label().startswith('Benmore_RL_'):act.destroy_actor(a)
            textures={name:texture(name,name=='T_RL_HeightRG') for name in ['T_RL_HeightRG','T_RL_Flow','T_RL_WaterMask','T_RL_Ecology','T_RL_Vegetation']}
            transfer=mats.fresh('M_RL_HeightTransfer');props(transfer,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=mats.Graph(transfer);n=g.node(u.MaterialExpressionTextureSample,texture=textures['T_RL_HeightRG'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);g.output(n,u.MaterialProperty.MP_EMISSIVE_COLOR,'RGB');assert not mel.recompile_material(transfer);assert eal.save_loaded_asset(transfer)
            terrain=mats.ground(u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/M_Gaea_Terrain'),textures['T_RL_Ecology'],textures['T_RL_Vegetation']);field=mats.deformation(terrain);land.set_editor_property('landscape_material',terrain)
            watermat=mats.water(textures['T_RL_Flow'],textures['T_RL_WaterMask']);timbermat=mats.timber()
            for a in act.get_all_level_actors():
                if a.get_actor_label()=='Benmore_Vista_Lake':a.static_mesh_component.set_material(0,mats.lake(u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/M_Gaea_Lake'),textures['T_RL_WaterMask']))
            rt=u.RenderingLibrary.create_render_target2d(world,N,N,u.TextureRenderTargetFormat.RTF_RGBA8);phase='warm';last=now
        elif phase=='warm' and now-last>20:
            phase='drawing';u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);phase='import';last=now
        elif phase=='import' and now-last>10:
            phase='importing';u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);assert land.landscape_import_heightmap_from_render_target(rt,True,0);phase='settle';last=now
        elif phase=='settle' and now-last>25:
            phase='exporting';assert land.landscape_export_heightmap_to_render_target(rt,True,True);phase='verify';last=now
        elif phase=='verify' and now-last>10:
            phase='verifying';assert land.landscape_export_heightmap_to_render_target(rt,True,True);pixels=u.RenderingLibrary.read_render_target(world,rt,False);values=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
            checksum=hashlib.sha256(values.tobytes()).hexdigest();assert checksum==data['height_sha256'];report['height_sha256']=checksum
            dressing();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
            for row in data['meshes']:import_mesh(row['name'],watermat)
            bridge=import_mesh('SM_RL_Footbridge',timbermat,True);report['bridge_actor']=bridge.get_actor_label()
            profiles(u.load_asset(DEST+'/M_RL_DeformField'))
            for row in data['cameras']:
                a=act.spawn_actor_from_class(u.CameraActor,u.Vector(*(v*100 for v in row['position_m'])));a.set_actor_label('Benmore_RL_Camera_'+row['name']);a.set_actor_rotation(u.MathLibrary.find_look_at_rotation(a.get_actor_location(),u.Vector(*(v*100 for v in row['target_m']))),False);a.camera_component.set_field_of_view(row['fov']);a.camera_component.set_editor_property('constrain_aspect_ratio',False)
                if row['name']=='Ford':u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(a.get_actor_location(),a.get_actor_rotation())
            road_after={label:digest(next(a for a in act.get_all_level_actors() if a.get_actor_label()==label)) for label in road_before};assert road_after==road_before
            report['roads_unchanged']=True;report['road_hashes']=road_after;(OUT/'support-samples.json').write_text(json.dumps(support))
            u.SystemLibrary.execute_console_command(world,'grass.FlushCache');phase='save';last=time.monotonic()
        elif phase=='save' and now-last>15:
            phase='saving';ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)];errors=[]
            for x,y,z,gap in support:
                hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,z+20000),u.Vector(x,y,z-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit is not None
                actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z;errors.append(abs(actual-z)/100)
            assert errors and max(errors)<.05;report['grounding']={'native_samples':len(errors),'max_error_m':max(errors),'maximum_basal_gap_cm':max(p[3] for p in support)}
            assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL);report['stages']=['native riverbed','baked-flow material','grounded bank ecology','ford and footbridge','two existing deformation profiles'];finish()
    except Exception:finish(traceback.format_exc())

handle=u.register_slate_post_tick_callback(tick)
