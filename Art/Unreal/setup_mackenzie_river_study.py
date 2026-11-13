"""Build and capture the isolated dry / damp / submerged river study."""
import json,math,random,sys,time,traceback,shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from mackenzie_river_study_shape import height,centre,silt,VIEWS
from mackenzie_river_study_materials import build,props,DEST
import mackenzie_river_study_bridge as bridge
OUT=ROOT/'Art/Export/MackenzieRiverStudy';OUT.mkdir(parents=True,exist_ok=True)
LEVEL=DEST+'/L_MackenzieRiverStudy'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
assets=u.EditorAssetLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
report=dict(ok=False,level=LEVEL,images=[],counts={},performance_measured=False,water_level_cm=0,reference_concept=str(ROOT/'Art/Export/MackenzieRiverConcept/mackenzie-river-concept-v1.png'))
phase='setup';last=started=time.monotonic();index=0;busy=False;world=pc=pace_rt=None

def spawn(cls,label,pos=(0,0,0),rot=None):
    a=actors.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());a.set_actor_label('RiverStudy_'+label);return a

def setup():
    report['benmore_water_reference']=bridge.inspect_reference()
    file=ROOT/'Content/GrandTour/ArtTests/MackenzieRiverStudy/L_MackenzieRiverStudy.umap'
    if file.exists():
        backup=ROOT/'Saved/MackenzieRiverStudy'/str(time.time_ns());backup.mkdir(parents=True)
        shutil.copy2(file,backup/file.name);report['backup']=str(backup/file.name)
        assert les.load_level(LEVEL)
    else:assert les.new_level(LEVEL)
    for a in actors.get_all_level_actors():
        if a.get_actor_label().startswith('RiverStudy_'):actors.destroy_actor(a)
    ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    ew.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    mats=build();bridge.mud_margin(mats['bed']);meshes={}
    mats['water'],domain,ambient=bridge.water()
    u.SystemLibrary.execute_console_command(ew,'Interchange.FeatureFlags.Import.FBX 0')
    for part in json.loads((OUT/'geometry.json').read_text())['parts']:
        name=part['name'];task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
        props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        task.options=opt
        package=ROOT/'Content/GrandTour/ArtTests/MackenzieRiverStudy'/(name+'.uasset')
        if not package.exists() or package.stat().st_mtime<(OUT/(name+'.fbx')).stat().st_mtime:
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=u.load_asset(DEST+'/'+name);assert mesh,name
        meshes[name]=mesh
        key='stone' if 'Cobble' in name else 'water' if 'Water' in name else 'hills' if 'Hills' in name else 'bed'
        mesh.set_material(0,mats[key])
        if key=='bed':props(mesh.get_editor_property('body_setup'),collision_trace_flag=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        ns=mesh.get_editor_property('nanite_settings');ns.enabled=key in ('bed','hills')
        if key=='bed':props(ns,fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES,fallback_percent_triangles=1.,fallback_relative_error=0.)
        sm.set_nanite_settings(mesh,ns,True);assets.save_loaded_asset(mesh)
        if key=='stone':continue
        a=spawn(u.StaticMeshActor,name);c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_material(0,mats[key]);c.set_collision_profile_name('BlockAll' if key=='bed' else 'NoCollision')
        props(c,cast_shadow=key!='water',affect_distance_field_lighting=key!='water',receives_decals=False)
        if key=='water':water_actor=a
    sheet=spawn(u.GTWaterSheet,'WaterDomain')
    props(sheet,river_reference=None,river_surface=None,water_domain=domain,domain_surfaces=[water_actor],base_level_cm=0.,
          surface_material_path=mats['water'].get_path_name(),surface_range_cm=2000.,ambient_wave_material=ambient,
          **bridge.reference['settings'])
    rng=random.Random(2026101307)
    def group(label,paths,rows,material=None,axis='xy'):
        a=spawn(u.Actor,label);count=0
        for k,path in enumerate(paths):
            mesh=u.load_asset(path);assert mesh,path
            b=mesh.get_bounds();ts=[]
            for x,y,size,kind,yaw,flatten in rows:
                if kind%len(paths)!=k:continue
                sc=size/(b.box_extent.z*2 if axis=='z' else max(b.box_extent.x,b.box_extent.y)*2)
                z=height(x,y)-(b.origin.z-b.box_extent.z)*sc*flatten-size*(.19 if axis=='xy' else .025)
                ts.append(u.Transform(u.Vector(x,y,z),u.Rotator(yaw=yaw),u.Vector(sc,sc,sc*flatten)))
            if not ts:continue
            c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,ts,'RiverStudy','NoCollision',axis=='xy')
            if material:
                for slot in range(c.get_num_materials()):c.set_material(slot,material)
            props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False)
            c.set_cull_distances(4500,7000);count+=len(ts)
        report['counts'][label]=count
    stones=[];occupied={}
    # Irregular deposits, with quiet fine pockets and a denser near-shore bed.
    for trial in range(135000):
        if trial<37000:x=rng.uniform(-3300,3300);y=rng.uniform(-1500,1600)
        else:x=rng.uniform(-1800,1800);y=rng.uniform(-1100,1050)
        z=height(x,y)
        patch=.50+.22*math.sin(x/217+y/179)+.19*math.sin(x/91-y/151)
        if rng.random()>patch*(1-.94*silt(x,y))*(.35 if z>70 else 1):continue
        r=rng.random();size=rng.uniform(3,7) if r<.40 else rng.uniform(7,15) if r<.90 else rng.uniform(15,25) if r<.993 else rng.uniform(25,34)
        cell=(int(x/25),int(y/25));near=[]
        for i in range(cell[0]-1,cell[0]+2):
            for j in range(cell[1]-1,cell[1]+2):near.extend(occupied.get((i,j),[]))
        if any(math.hypot(x-a,y-b)<(size+c)*.40 for a,b,c in near):continue
        occupied.setdefault(cell,[]).append((x,y,size))
        stones.append((x,y,size,rng.randrange(8),rng.gauss(15,48),rng.uniform(.70,1.12)))
    group('CobbleDeposits',[DEST+'/SM_MRS_Cobble'+str(k) for k in range(8)],stones,mats['stone'])
    grass=[]
    for _ in range(6500):
        x=rng.uniform(-4100,4100);y=rng.uniform(-2400,2500);z=height(x,y)
        density=.28+.18*math.sin(x/210)*math.sin(y/170)
        if z<43 or rng.random()>density:continue
        grass.append((x,y,rng.uniform(22,49),rng.randrange(3),rng.uniform(0,360),rng.uniform(.80,1.12)))
    group('Tussock',['/Game/GrandTour/ArtTests/TussockStyle/SM_TS_'+k for k in ['Straw','Rust','Fine']],grass,mats['grass'],'z')
    wood=[]
    for x,y,size in [(690,-390,110),(810,-420,65),(420,-470,44),(-850,-300,54),(1440,380,80)]:wood.append((x,y,size,rng.randrange(2),rng.uniform(-22,30),1.))
    group('StrandedWood',['/Game/GrandTour/ArtTests/MudRoads/SM_MRD_Branch'+str(k) for k in range(2)],wood,u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/M_Benmore_WillowBark'))
    spawn(u.SkyAtmosphere,'Sky')
    sun=spawn(u.DirectionalLight,'Sun',(0,0,1400),u.Rotator(pitch=-38,yaw=-65));props(sun.light_component,intensity=65000.,atmosphere_sun_light=True,light_source_angle=1.5)
    sky=spawn(u.SkyLight,'SkyLight',(0,0,900));props(sky.light_component,real_time_capture=True,intensity=1.)
    fog=spawn(u.ExponentialHeightFog,'Haze',(0,0,-150));props(fog.get_component_by_class(u.ExponentialHeightFogComponent),fog_density=.008,fog_height_falloff=.20,start_distance=6000.)
    pp=spawn(u.PostProcessVolume,'Exposure');props(pp,unbound=True,priority=500.,blend_weight=1.)
    ps=pp.get_editor_property('settings')
    for k,v in dict(auto_exposure_method=u.AutoExposureMethod.AEM_HISTOGRAM,auto_exposure_min_brightness=13.0,auto_exposure_max_brightness=13.0,auto_exposure_bias=0.,bloom_intensity=.12,lens_flare_intensity=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.).items():
        ps.set_editor_property('override_'+k,True);ps.set_editor_property(k,v)
    pp.set_editor_property('settings',ps)
    for key,pos,target in VIEWS:
        a=spawn(u.CameraActor,'Camera_'+key,pos,u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)));a.camera_component.set_field_of_view(68);a.camera_component.set_editor_property('constrain_aspect_ratio',False)
    spawn(u.PlayerStart,'Start',(-850,-800,height(-850,-800)+130))
    pos,target=VIEWS[0][1:];u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(*pos),u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)))
    for material in mats.values():assert assets.save_loaded_asset(material)
    assert les.save_current_level();report['materials']={k:v.get_path_name() for k,v in mats.items()}
    report['source_manifest']=str(ROOT/'Art/Textures/MackenzieRiver/source-manifest.json')
    report['camera_height_above_bed_cm']=160
    report['geometry']=json.loads((OUT/'geometry.json').read_text())
    report['scope']='Isolated study using installed Benmore water shading and native water domain; approved scanned mud margins. Static collision bed, decorative stones, no deformable soil. Water interaction was checked separately in drive-report.json; gravel/mud handling remains unfinished. No Benmore or driving-physics edits.'
    bridge.verify_reference()

def finish(error=None):
    global phase,last,world,pc,pace_rt
    if error:report['error']=error;u.log_error(error)
    (OUT/'study-report.json').write_text(json.dumps(report,indent=2))
    if not error:
        cards=''.join('<figure><a href="'+key+'.png"><img src="'+key+'.png" alt="Unreal capture: '+key.replace('_',' ')+'"></a><figcaption>'+key.replace('_',' ').title()+'</figcaption></figure>' for key,_,_ in VIEWS)
        (OUT/'river-study.html').write_text('''<!doctype html><meta charset="utf-8"><title>Mackenzie river study</title><style>body{max-width:1500px;margin:32px auto;padding:0 24px;background:#1c211f;color:#dddcd3;font:17px/1.55 system-ui}a{color:#adcbd3}main{display:grid;grid-template-columns:1fr 1fr;gap:24px}figure{margin:0}img{width:100%}figcaption{padding:8px 0}@media(max-width:800px){main{grid-template-columns:1fr}}</style><h1>Mackenzie river / Unreal test reach</h1><p>Benmore's installed water shading and waves, pale dry shingle, and sheltered pockets using the approved scanned mud. Captured in Unreal at standing height, plus an overhead view.</p><p><a href="../MackenzieRiverConcept/concept.html">Concept and local river references</a> · <a href="study-report.json">Build and capture report</a></p><p>Map: <b>'''+LEVEL+'''</b>. Native water depth/current queries are connected. The bed is solid, small stones are decorative, and mud is not deformable. Mud and gravel handling remains unfinished. The <a href="drive-report.json">vehicle crossing check</a> records water interaction; no vehicle physics changes.</p><main>'''+cards+'</main>',encoding='utf-8')
    if pace_rt:u.RenderingLibrary.release_render_target2d(pace_rt)
    pace_rt=None
    phase='ending';last=time.monotonic();world=pc=None;u.EditorLevelLibrary.editor_end_play()

def body():
    global phase,last,index,world,pc,shot_time,pace_rt
    now=time.monotonic()
    if phase=='ending':
        if now-last>5 and u.EditorLevelLibrary.get_game_world() is None:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        return
    if now-started>900:raise RuntimeError('River study timeout')
    # Bound queued rendering during offscreen captures, including rain captures.
    if pace_rt:u.RenderingLibrary.read_render_target_pixel(world,pace_rt,0,0)
    if phase=='setup':setup();phase='play';last=time.monotonic()
    elif phase=='play' and now-last>12:
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,1000);phase='warm';last=now
    elif phase=='warm' and now-last>25:
        world=u.EditorLevelLibrary.get_game_world()
        if world is None:return
        pc=u.GameplayStatics.get_player_controller(world,0);pawn=u.GameplayStatics.get_player_pawn(world,0)
        pace_rt=u.RenderingLibrary.create_render_target2d(world,1,1,u.TextureRenderTargetFormat.RTF_RGBA8)
        report['collision_survey']=bridge.survey_collision(world)
        assert max(abs(row['error_cm']) for row in report['collision_survey'])<2,report['collision_survey']
        if pawn:pawn.set_actor_hidden_in_game(True)
        sheet=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if a.get_actor_label()=='RiverStudy_WaterDomain')
        report['water_queries']=[dict(x_cm=x,y_cm=y,covered=sheet.covers(u.Vector2D(x,y)),surface_cm=sheet.surface_cm_at(u.Vector2D(x,y)),flow_cmps=sheet.flow_cm_per_s_at(u.Vector2D(x,y)).to_tuple()) for x,y in [(-500,-1000),(-500,centre(-500))]]
        assert not report['water_queries'][0]['covered'] and report['water_queries'][1]['covered'],report['water_queries']
        report['water_runtime_materials']=[dict(component=c.get_path_name(),parameters={k:c.get_material(0).get_scalar_parameter_value(k) for k in ['AmbientReady','AmbientClock','FieldActive','LocalSurface']}) for c in [a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]]
        for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0']:u.SystemLibrary.execute_console_command(world,cmd,pc)
        phase='aim'
    elif phase=='aim':
        camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='RiverStudy_Camera_'+VIEWS[index][0]);pc.set_view_target_with_blend(camera,0.);phase='capture';last=now
    elif phase=='capture' and now-last>7:
        path=OUT/(VIEWS[index][0]+'.png');shot_time=time.time();report['images'].append(str(path))
        u.SystemLibrary.execute_console_command(world,'HighResShot 1600x1000 filename="'+path.as_posix()+'"',pc);phase='wait';last=now
    elif phase=='wait' and now-last>3:
        p=Path(report['images'][-1])
        if not p.exists() or p.stat().st_mtime<shot_time:return
        index+=1
        if index==len(VIEWS):report['ok']=True;finish();return
        phase='aim'

def tick(dt):
    global busy
    if busy:return
    busy=True
    try:body()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
