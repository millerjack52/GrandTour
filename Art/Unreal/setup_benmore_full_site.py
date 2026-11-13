"""Create a separate terrain-only review map from the full selected LINZ site."""
import unreal as u
import json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MackenzieRealTerrain/BenmoreFullSite'
meta=json.loads((OUT/'terrain-manifest.json').read_text())
DEST='/Game/GrandTour/Demo/BenmoreFullSite';LEVEL=DEST+'/L_Benmore_TerrainReview'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
assets=u.AssetToolsHelpers.get_asset_tools();act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'level':LEVEL,'purpose':'Terrain-only review. Roads and gameplay height-query integration pending.'}
phase='create';started=time.monotonic();last=started
u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(ob,**kw):
    for k,v in kw.items():ob.set_editor_property(k,v)
    return ob
def spawn(cls,name,pos,rot=None):
    ob=act.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());ob.set_actor_label(name);return ob
def material(name):
    m=u.load_asset(DEST+'/'+name) if eal.does_asset_exist(DEST+'/'+name) else assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m);return m
def finish(error=None):
    report['ok']=error is None
    if error:report['error']=error
    (OUT/'unreal-review-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,land,rt,importmat,camera
    try:
        now=time.monotonic()
        if now-started>600:raise RuntimeError('Terrain review setup timed out')
        if phase=='create':
            # Loading and compiling materials can pump Slate recursively.
            phase='building'
            eal.make_directory(DEST)
            assert les.load_level(LEVEL) if eal.does_asset_exist(LEVEL) else les.new_level(LEVEL)
            for ob in act.get_all_level_actors():
                if not isinstance(ob,(u.WorldSettings,u.Brush)):act.destroy_actor(ob)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
            m=material('M_Benmore_TerrainReview')
            pos=mel.create_material_expression(m,u.MaterialExpressionWorldPosition)
            normal=mel.create_material_expression(m,u.MaterialExpressionVertexNormalWS)
            custom=mel.create_material_expression(m,u.MaterialExpressionCustom)
            inputs=[]
            for name in ['P','N']:
                inp=u.CustomInput();inp.set_editor_property('input_name',name);inputs.append(inp)
            props(custom,inputs=inputs,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,code='''
float steep=1-saturate((N.z-.65)/.3);
float height=saturate(P.z/35000.0);
float3 grass=lerp(float3(.32,.29,.14),float3(.23,.25,.15),height);
float3 land=lerp(grass,float3(.30,.28,.23),steep*.65);
return P.z<48 ? float3(.035,.15,.19) : land;
''')
            mel.connect_material_expressions(pos,'',custom,'P');mel.connect_material_expressions(normal,'',custom,'N')
            mel.connect_material_property(custom,'',u.MaterialProperty.MP_BASE_COLOR)
            rough=mel.create_material_expression(m,u.MaterialExpressionConstant);rough.set_editor_property('r',.86)
            mel.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
            assert not mel.recompile_material(m);eal.save_loaded_asset(m)
            spec=u.load_asset('/Game/GrandTour/Demo/MackenzieBlockout/DA_Mackenzie_Blockout').spec
            props(spec,components_per_side=16,quad_size_cm=250000/2016,origin_x_cm=-125000.,origin_y_cm=-125000.,z_scale=200.,
                base_amplitude_m=0.,slope_m_per_km=0.,route_m=[],features=[],planes=[],alt_routes=[],stations=[],sections=[],spans=[],biomes=[],
                scrub_roughness_m=0.,road_roughness_m=0.,track_roughness_m=0.)
            sa=assets.create_asset('DA_Benmore_GridSeed',DEST,u.GTTerrainSpecAsset,u.DataAssetFactory()) if not eal.does_asset_exist(DEST+'/DA_Benmore_GridSeed') else u.load_asset(DEST+'/DA_Benmore_GridSeed')
            props(sa,spec=spec,display_name='Grid creation only - not runtime terrain heights');eal.save_loaded_asset(sa)
            dressing=spawn(u.GTTerrainDressing,'TemporaryEmptyDressing',(0,0,0));dressing.foliage_density=0.
            builder=spawn(u.GTTerrainBuilder,'TemporaryGridBuilder',(0,0,0))
            props(builder,spec_asset=sa,landscape_material_path=DEST+'/M_Benmore_TerrainReview',layer_info_folder=DEST+'/Layers',reground_actors=False)
            land=builder.rebuild_landscape();assert land,builder.last_message
            land.set_actor_label('Benmore_FullSite_LINZ_2500m')
            # Remove the procedural seed actor so users cannot inadvertently
            # rebuild this imported Landscape as the temporary flat grid.
            act.destroy_actor(builder);act.destroy_actor(dressing)
            task=props(u.AssetImportTask(),filename=str(OUT/'T_Benmore_HeightRG_2017.png'),destination_path=DEST,
                destination_name='T_Benmore_HeightRG_2017',automated=True,replace_existing=True,save=True)
            assets.import_asset_tasks([task]);texture=u.load_asset(DEST+'/T_Benmore_HeightRG_2017');assert texture
            props(texture,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,
                mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST,never_stream=True)
            eal.save_loaded_asset(texture)
            importmat=material('M_Benmore_HeightTransfer')
            importmat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
            tex=mel.create_material_expression(importmat,u.MaterialExpressionTextureSample)
            props(tex,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            mel.connect_material_property(tex,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR)
            assert not mel.recompile_material(importmat);eal.save_loaded_asset(importmat)
            rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8)
            sun=spawn(u.DirectionalLight,'Sun',(0,0,100000),u.Rotator(pitch=-40,yaw=-50));sun.light_component.set_intensity(8.)
            sky=spawn(u.SkyLight,'Sky',(0,0,100000));sky.light_component.set_editor_property('real_time_capture',True);sky.light_component.set_intensity(.7)
            spawn(u.SkyAtmosphere,'SkyAtmosphere',(0,0,0))
            pp=spawn(u.PostProcessVolume,'ReviewExposure',(0,0,0));pp.unbound=True;pp.priority=300.
            settings=pp.settings;props(settings,override_auto_exposure_min_brightness=True,auto_exposure_min_brightness=.3,
                override_auto_exposure_max_brightness=True,auto_exposure_max_brightness=.3);pp.settings=settings
            camera=spawn(u.CameraActor,'ReviewCamera',(-195000,-260000,215000))
            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(0,0,9000)),False)
            camera.camera_component.set_field_of_view(52)
            spawn(u.PlayerStart,'ReviewFlyStart',(-95000,-95000,55000),u.Rotator(pitch=-20,yaw=40))
            u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
            phase='warm';last=now
        elif phase=='warm' and now-last>20:
            phase='drawing'
            u.RenderingLibrary.draw_material_to_render_target(world,rt,importmat)
            phase='import';last=now
        elif phase=='import' and now-last>12:
            phase='importing'
            u.RenderingLibrary.draw_material_to_render_target(world,rt,importmat)
            errors=[]
            for anchor in meta['unreal_validation_anchors']:
                ix,iy=anchor['pixel'];c=u.RenderingLibrary.read_render_target_pixel(world,rt,ix,iy)
                height=((int(c.r)<<8)|int(c.g))-32768
                errors.append(abs(height/64*100-anchor['local_xyz_cm'][2]))
            report['transfer_max_error_cm']=max(errors);assert max(errors)<.01,report
            assert land.landscape_import_heightmap_from_render_target(rt,True,0)
            phase='settle';last=now
        elif phase=='settle' and now-last>25:
            phase='exporting'
            # Re-export the actual Landscape rather than trusting the import return.
            assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            phase='validate';last=now
        elif phase=='validate' and now-last>12:
            phase='validating'
            assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            errors=[]
            for anchor in meta['unreal_validation_anchors']:
                ix,iy=anchor['pixel'];c=u.RenderingLibrary.read_render_target_pixel(world,rt,ix,iy)
                height=(((int(c.r)<<8)|int(c.g))-32768)/64*100
                errors.append(abs(height-anchor['local_xyz_cm'][2]))
            report['landscape_max_error_cm']=max(errors);report['height_checks']=len(errors)
            assert max(errors)<.01,report
            assert les.save_current_level()
            les.editor_request_begin_play();phase='pie';last=now
        elif phase=='pie' and now-last>15:
            phase='checking'
            game=u.EditorLevelLibrary.get_game_world();assert game
            ignore=[a for a in u.GameplayStatics.get_all_actors_of_class(game,u.Actor) if not isinstance(a,u.LandscapeProxy)]
            misses=[];errors=[]
            for anchor in meta['unreal_validation_anchors']:
                ix,iy=anchor['pixel']
                if ix in [0,2016] or iy in [0,2016]:continue
                x,y,z=anchor['local_xyz_cm']
                hit=u.SystemLibrary.line_trace_single(game,u.Vector(x,y,100000),u.Vector(x,y,-10000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
                if hit is None:misses.append(anchor['pixel']);continue
                vecs=[v for v in hit.to_tuple() if isinstance(v,u.Vector)]
                errors.append(abs(vecs[0].z-z))
            report['collision']={'samples':len(errors)+len(misses),'misses':misses,'max_error_cm':max(errors) if errors else None}
            assert not misses and errors and max(errors)<5,report['collision']
            pc=u.GameplayStatics.get_player_controller(game,0)
            cams=u.GameplayStatics.get_all_actors_of_class(game,u.CameraActor);assert cams
            pc.set_view_target_with_blend(cams[0],0)
            u.SystemLibrary.execute_console_command(game,'gt.Look.Post 0',pc)
            u.SystemLibrary.execute_console_command(game,'gt.Look.Kuwahara 0',pc)
            phase='shot';last=now
        elif phase=='shot' and now-last>5:
            phase='capturing'
            game=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(game,0)
            u.SystemLibrary.execute_console_command(game,'HighResShot 1600x1100 filename="'+(OUT/'Unreal_Terrain_Review.png').as_posix()+'"',pc)
            phase='done';last=now
        elif phase=='done' and now-last>5:
            u.EditorLevelLibrary.editor_end_play();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
