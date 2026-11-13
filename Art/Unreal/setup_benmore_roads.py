"""Create a collision-driven Benmore road blockout without procedural spec actors."""
import unreal as u
import json,time,traceback,math,array,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRoads'
data=json.loads((OUT/'road-manifest.json').read_text());dress=json.loads((OUT/'dressing.json').read_text())
ART_ONLY=os.environ.get('GT_BENMORE_ART_ONLY')=='1'
DEST='/Game/GrandTour/Demo/BenmoreRoads';LEVEL=data['level'];SOURCE='/Game/GrandTour/Demo/BenmoreFullSite/L_Benmore_TerrainReview'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'level':LEVEL,'scope':'Collision-driven road blockout; no procedural route/mud spec actor','dressing':data['dressing_counts']}
phase='load';last=time.monotonic();started=last
u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def spawn(cls,name,p,rot=None):
    ob=act.spawn_actor_from_class(cls,u.Vector(*p),rot or u.Rotator());ob.set_actor_label(name);return ob
def material(name):
    m=u.load_asset(DEST+'/'+name) if eal.does_asset_exist(DEST+'/'+name) else assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m);return m
def texture(name,exact=False):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    assets.import_asset_tasks([task]);tex=u.load_asset(DEST+'/'+name);assert tex
    props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,
          mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST if exact else u.TextureFilter.TF_BILINEAR,never_stream=True)
    eal.save_loaded_asset(tex);return tex
def expr(m,cls,**kw):return props(mel.create_material_expression(m,cls),**kw)
def custom(m,names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):
    slots=[props(u.CustomInput(),input_name=n) for n in names]
    return expr(m,u.MaterialExpressionCustom,inputs=slots,code=code,output_type=typ)
def wire(a,b,name,output=''):assert mel.connect_material_expressions(a,output,b,name)
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/('art-report.json' if ART_ONLY else 'setup-report.json')).write_text(json.dumps(report,indent=2))
    if ART_ONLY and not error:
        prior=json.loads((OUT/'setup-report.json').read_text());prior['dressing']=data['dressing_counts'];prior['art_update']='art-report.json';(OUT/'setup-report.json').write_text(json.dumps(prior,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,land,rt,transfer
    now=time.monotonic()
    try:
        if now-started>900:raise RuntimeError('Road setup timeout')
        if phase=='load':
            phase='building'
            (ROOT/'Content/GrandTour/Demo/BenmoreRoads').mkdir(parents=True,exist_ok=True)
            if not eal.does_asset_exist(LEVEL):
                assert les.load_level(SOURCE)
                source_world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
                assert u.EditorLoadingAndSavingUtils.save_map(source_world,LEVEL)
            # SaveMap makes a copy. Explicitly load that package before edits.
            assert les.load_level(LEVEL)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            assert world.get_path_name().startswith(LEVEL+'.'),world.get_path_name()
            world.get_world_settings().set_editor_property('default_game_mode',u.GTDriveTestGameMode)
            land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
            land.set_actor_label('Benmore_GradedRoads_2500m')
            for a in act.get_all_level_actors():
                if isinstance(a,(u.PlayerStart,u.CameraActor)) or a.get_actor_label()=='Benmore_Roadside_ArtSample':act.destroy_actor(a)
            roadmask=texture('T_Benmore_RoadMask');heighttex=texture('T_Benmore_RoadHeightRG',True)
            transfer=material('M_Benmore_RoadHeightTransfer');transfer.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
            tex=expr(transfer,u.MaterialExpressionTextureSample,texture=heighttex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            mel.connect_material_property(tex,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR);assert not mel.recompile_material(transfer);eal.save_loaded_asset(transfer)
            m=material('M_Benmore_RoadLandscape')
            p=expr(m,u.MaterialExpressionWorldPosition);n=expr(m,u.MaterialExpressionVertexNormalWS)
            uv=custom(m,['P'],'return ((P.xy+125000)/250000*2016+.5)/2017;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
            mask=expr(m,u.MaterialExpressionTextureSample,texture=roadmask,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,mask,'UVs')
            tile=custom(m,['P'],'return P.xy/400.0;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,tile,'P')
            texnodes={}
            for key in ['CompactColor','LooseColor','CompactNormal']:
                texnodes[key]=expr(m,u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/ArtTests/GravelRoad/T_GR_'+key),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if 'Normal' in key else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
                wire(tile,texnodes[key],'UVs')
            color=custom(m,['P','N','Mask','Compact','Loose'],'''
struct FieldNoise { float noise(float2 v) { float2 i=floor(v),f=frac(v); f=f*f*(3-2*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1,float2(127.1,311.7))))*43758.5453);
return lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y); } }; FieldNoise field;
float broad=.65*field.noise(P.xy/3400)+.35*field.noise(P.xy/900);
float footprint=max(length(ddx(P.xy)),length(ddy(P.xy)));
float fleck=lerp(.5,field.noise(P.xy/30),1-smoothstep(15,120,footprint));
float steep=1-smoothstep(.66,.96,N.z);
float3 grass=lerp(float3(.245,.235,.115),float3(.36,.29,.14),broad)*(.90+.2*fleck);
grass=lerp(grass,float3(.285,.275,.23),steep*.7);
float3 gravel=lerp(Loose,Compact,.64)*.88;
float3 shoulder=lerp(grass,Loose*.83,Mask.g*.65);
float3 result=lerp(shoulder,gravel*(1-Mask.b*.10),Mask.r);
return P.z<48 ? float3(.035,.15,.19) : result;
''')
            for src,name,out in [(p,'P',''),(n,'N',''),(mask,'Mask','RGB'),(texnodes['CompactColor'],'Compact','RGB'),(texnodes['LooseColor'],'Loose','RGB')]:wire(src,color,name,out)
            mel.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
            normal=custom(m,['Detail','Mask'],'return normalize(lerp(float3(0,0,1),Detail,Mask*.5));');wire(texnodes['CompactNormal'],normal,'Detail','RGB');wire(mask,normal,'Mask','R')
            mel.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
            for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.93),(u.MaterialProperty.MP_SPECULAR,.15)]:
                c=expr(m,u.MaterialExpressionConstant,r=value);mel.connect_material_property(c,'',prop)
            assert not mel.recompile_material(m);eal.save_loaded_asset(m)
            props(land,landscape_material=m,default_phys_material=u.load_asset('/Game/GrandTour/Terrain/Surfaces/PM_Dirt'))
            for volume in [a for a in act.get_all_level_actors() if isinstance(a,u.PostProcessVolume)]:
                settings=volume.settings;props(settings,override_auto_exposure_min_brightness=True,auto_exposure_min_brightness=1.4,override_auto_exposure_max_brightness=True,auto_exposure_max_brightness=1.4);volume.settings=settings
            rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8)
            group=spawn(u.Actor,'Benmore_Roadside_ArtSample',(0,0,0))
            for kind in range(4):
                mesh=u.load_asset('/Game/GrandTour/ArtTests/DenseTussock/SM_DT_'+str(kind)+'_LOD');assert mesh
                transforms=[u.Transform(u.Vector(*[v*100 for v in row['xyz']]),u.Rotator(yaw=row['yaw']),u.Vector(row['scale'],row['scale'],row['scale'])) for row in dress['foliage'] if row['kind']==kind]
                c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'BenmoreTussock','NoCollision',False);c.set_cull_distances(14000,22000)
                props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False)
            for kind in range(1,5):
                mesh=u.load_asset('/Game/GrandTour/ArtTests/GravelRoad/SM_GR_Stone'+str(kind));assert mesh
                transforms=[u.Transform(u.Vector(*[v*100 for v in row['xyz']]),u.Rotator(yaw=row['yaw']),u.Vector(row['scale'],row['scale']*.8,row['scale']*.6)) for row in dress['stones'] if row['kind']==kind]
                c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'BenmoreGravel','NoCollision',False);c.set_cull_distances(6000,10000)
            # Small guide posts make the bends legible without lining every metre.
            pm=material('M_Benmore_Post');col=expr(pm,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.36,.31,.23,1));mel.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
            rough=expr(pm,u.MaterialExpressionConstant,r=.95);mel.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS);mel.set_base_material_usage(pm,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True);mel.recompile_material(pm);eal.save_loaded_asset(pm)
            cube=u.load_asset('/Engine/BasicShapes/Cube')
            transforms=[u.Transform(u.Vector(x*100,y*100,z*100+45),u.Rotator(),u.Vector(.10,.10,.9)) for x,y,z in dress['posts']]
            c=u.GTVegetationSubsystem.add_tagged_instances(group,cube,transforms,'BenmoreGuidePosts','NoCollision',False);c.set_material(0,pm);c.set_cull_distances(30000,40000)
            p=data['routes'][0]['points'][20]
            spawn(u.PlayerStart,'Benmore_DriveStart',(p['x_m']*100,p['y_m']*100,p['z_m']*100+160),u.Rotator(yaw=p['yaw']))
            camera=spawn(u.CameraActor,'Benmore_RouteOverview',(-155000,-205000,155000))
            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(-30000,-20000,9000)),False)
            camera.camera_component.set_field_of_view(56);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
            u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
            if ART_ONLY:
                assert les.save_current_level();report['heightfield_unchanged']=True;finish();return
            phase='warm';last=time.monotonic()
        elif phase=='warm' and now-last>20:
            phase='drawing';u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);phase='import';last=now
        elif phase=='import' and now-last>12:
            phase='importing';u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer)
            for a in data['validation_anchors']:
                c=u.RenderingLibrary.read_render_target_pixel(world,rt,*a['pixel']);z=(((int(c.r)<<8)|int(c.g))-32768)/64
                assert abs(z-a['z_m'])<.0001,(a,z)
            assert land.landscape_import_heightmap_from_render_target(rt,True,0)
            phase='settle';last=now
        elif phase=='settle' and now-last>25:
            phase='exporting';assert land.landscape_export_heightmap_to_render_target(rt,True,True);phase='verify';last=now
        elif phase=='verify' and now-last>12:
            phase='verifying';assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            errors=[]
            for a in data['validation_anchors']:
                c=u.RenderingLibrary.read_render_target_pixel(world,rt,*a['pixel']);z=(((int(c.r)<<8)|int(c.g))-32768)/64;errors.append(abs(z-a['z_m']))
            report['height_import_max_error_m']=max(errors);assert max(errors)<.0001
            assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
