"""Isolated shoreline/material revision, preserving terrain, bake and placement."""
import unreal as u
import sys,json,time,traceback,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as shared
from benmore_river_life_materials import Graph,props
OUT=ROOT/'Art/Export/BenmoreGaea/ShoreRefinement'
SRC='/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement'
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeShoreRefinement'
LEVEL=shared.LEVEL;eal=shared.eal;mel=shared.mel;les=shared.les
prepared=json.loads((OUT/'prepare-report.json').read_text());assert prepared['ok']
report=dict(ok=False,images=[],driving_tested=False,timings_collected=False,prepare=prepared)
shared.OUT=OUT;shared.DEST=DEST;shared.report=report;shared.grid=shared.after
REVIEW_ONLY='-GTShoreReviewOnly' in u.SystemLibrary.get_command_line()
full_views=shared.views
shared.views=lambda:[v for v in full_views() if v[0] in ['Ford','Reach','Lower','Bars','BarGround','FullCourse']]
shore=json.loads((OUT/'shore-atlas.json').read_text());ox,oy=shore['origin_m'];sx,sy=shore['span_m']
SHORE_UV='(P.xy*.01-float2(%.8f,%.8f)+.3125)/float2(%.8f,%.8f)'%(ox,oy,sx,sy)
busy=False

def path_asset(asset):return asset.get_path_name().split('.')[0]

def copy_material(name,textures):
    m=u.load_asset(DEST+'/'+name) or eal.duplicate_asset(SRC+'/'+name,DEST+'/'+name)
    assert m
    for n in list(mel.get_material_expressions(m)):
        if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSampleParameter2D)):
            t=n.get_editor_property('texture')
            if t and t.get_name() in textures:n.set_editor_property('texture',textures[t.get_name()])
        if isinstance(n,u.MaterialExpressionCustom):
            code=n.get_editor_property('code')
            if 'aggregate=lerp(aggregate,grey*float3(1.08,1.10,1.12),.78)*1.20;' in code:
                code=code.replace('aggregate=lerp(aggregate,grey*float3(1.08,1.10,1.12),.78)*1.20;',
                    'aggregate=lerp(aggregate,grey*lerp(float3(1.14,1.07,.94),float3(.97,1.035,1.07),zones.b),.42);')
                code=code.replace('float3(.135,.112,.078)','float3(.18,.153,.112)')
                code=code.replace('zones.g*.75)*lerp(1,.72,zones.b)','zones.g*.58)*lerp(1,.53,zones.b)')
            code=code.replace('aggregate=lerp(aggregate,grey*lerp(float3(1.14,1.07,.94),float3(.97,1.035,1.07),zones.b),.42);',
                'float cleanGravel=smoothstep(.65,.90,zones.r)*(1-zones.g);\naggregate=lerp(aggregate,grey*lerp(float3(1.10,1.045,.98),float3(.97,1.035,1.07),zones.b),lerp(.42,.76,cleanGravel))*lerp(1,1.16,cleanGravel*(1-zones.b));')
            if 'ShoreSampler' in code:
                code='float2 uv='+SHORE_UV+';\nif(any(uv<0)||any(uv>1))return Old;\nfloat4 shore=Texture2DSampleLevel(Shore,ShoreSampler,uv,0);\nreturn Old*step(.5001,shore.r);'
            if name=='M_GC_DomainRiver' and 'Mask=Local>.5 ? inside*step(1,live.g)' in code:
                # The 62.5cm live occupancy must not stamp its cell boundary
                # inside the bounded subcell rim. Physical queries stay intact.
                g=Graph(m,'ShoreRefinement')
                n.set_editor_property('inputs',list(n.get_editor_property('inputs'))+[props(u.CustomInput(),input_name='BankEdge')])
                tex=g.node(u.MaterialExpressionTextureObject,texture=textures['T_CP_Shore'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
                g.wire(tex,n,'BankEdge')
                code=code.replace('Mask=Local>.5 ? inside*step(1,live.g) : OldMask*(1-inside);',
                    'float2 bankUV='+SHORE_UV+';\nfloat shoreDistance=(Texture2DSampleLevel(BankEdge,BankEdgeSampler,saturate(bankUV),0).r-.5)*4;\nfloat shoreRim=step(0,shoreDistance)*(1-smoothstep(.35,.75,shoreDistance));\nMask=Local>.5 ? inside*max(step(1,live.g),shoreRim) : OldMask*(1-inside);')
            code=code.replace('saturate(bankUV),0).r-.5)*4','saturate(bankUV),0).g-.5)*4')
            n.set_editor_property('code',code)
    errors=mel.recompile_material(m);assert not errors,list(errors)
    assert eal.save_loaded_asset(m)
    if name=='M_GC_Terrain':
        # Benmore B1's surface types alone (the landscape physical material output). Benmore triage: B1's ground detail and scatter and
        # B2's deform hole, apron and far mud stay off; the gravel parallax switch stays on MPC_Benmore_GravelPOM.Enabled.
        import benmore_gt_ground
        benmore_gt_ground.attach_surfaces(m)
        # Retain the owner's approved scanned bank/verge materials on shoreline rebuilds.
        import benmore_mud_materials
        benmore_mud_materials.attach(m)
        import benmore_river_shingle
        benmore_river_shingle.attach(m,refresh_sources=True)
        assert eal.save_loaded_asset(m)
    elif name=='M_GC_MouthBed':
        import benmore_river_shingle
        benmore_river_shingle.attach(m)
        assert eal.save_loaded_asset(m)
    return m

def snapshot():
    refs=shared.refs();sheet=refs['Benmore_RS_WaterDomain']
    ref=sheet.get_editor_property('water_domain')
    refpath=ROOT/'Content'/path_asset(ref).removeprefix('/Game/')
    return dict(instances=shared.signature(),roads=shared.signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail']),
        profiles=shared.profiles(),queries=json.loads(json.dumps(shared.queries())),
        domain_asset=path_asset(ref),domain_file_sha256=hashlib.sha256(refpath.with_suffix('.uasset').read_bytes()).hexdigest(),
        runtime={k:sheet.get_editor_property(k) for k in ['field_cell_cm','max_sim_cells','wind_ripple_cm','rain_drop_cm','dry_cut_cm']},
        drive_sha256=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest())

def install():
    refs=shared.refs()
    textures={name:shared.texture(name) for name in ['T_GC_ExtendedBedZones','T_RL_Ecology','T_SR_Shore']}
    textures['T_CP_BedZones']=textures['T_GC_ExtendedBedZones'];textures['T_CP_Shore']=textures['T_SR_Shore']
    mats={name:copy_material(name,textures) for name in ['M_GC_Terrain','M_GC_DeformField','M_GC_DomainRiver','M_GC_DomainLake','M_GC_MouthBed','M_GC_Hills']}
    land=next(a for a in refs.values() if isinstance(a,u.Landscape));land.set_editor_property('landscape_material',mats['M_GC_Terrain'])
    provider=refs['Benmore_RL_CrossingProfiles'];old=provider.get_editor_property('spec_asset')
    profile=u.load_asset(DEST+'/DA_GC_CrossingProfiles') or eal.duplicate_asset(path_asset(old),DEST+'/DA_GC_CrossingProfiles')
    spec=profile.get_editor_property('spec');sections=list(spec.get_editor_property('sections'))
    for section in sections:
        deform=section.get_editor_property('deform');deform.set_editor_property('surface_material_path',mats['M_GC_DeformField'].get_path_name());section.set_editor_property('deform',deform)
    spec.set_editor_property('sections',sections);profile.set_editor_property('spec',spec)
    assert eal.save_loaded_asset(profile);provider.set_editor_property('spec_asset',profile)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for label,name in [('Benmore_RL_Stream','SM_GC_RiverSurface'),('Benmore_RL_Outlet','SM_GC_OutletSurface')]:
        mesh=shared.import_mesh(name,mats['M_GC_DomainRiver']);refs[label].static_mesh_component.set_static_mesh(mesh)
        refs[label].static_mesh_component.set_material(0,mats['M_GC_DomainRiver'])
    for label,actor in refs.items():
        if label.startswith('Benmore_Hills_') and isinstance(actor,u.StaticMeshActor):actor.static_mesh_component.set_material(0,mats['M_GC_Hills'])
    refs['Benmore_RL_MouthBed'].static_mesh_component.set_material(0,mats['M_GC_MouthBed'])
    sheet=refs['Benmore_RS_WaterDomain'];sheet.set_editor_property('surface_material_path',mats['M_GC_DomainRiver'].get_path_name())
    shared.clean_saved_water();shared.set_ford_camera()
    assert mel.get_material_property_input_node(mats['M_GC_DeformField'],u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    report['deformation_wpo_connected']=True
    assert snapshot()==report['before'],'Unexpected placement/physics change'
    assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)

def run():
    assert les.load_level(LEVEL)
    if REVIEW_ONLY:
        previous=json.loads((OUT/'install-report.json').read_text());report['before']=previous['before'];report['backup']=BACKUP
    else:
        if not eal.does_asset_exist(BACKUP):
            assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),BACKUP)
            assert les.load_level(LEVEL)
        report['backup']=BACKUP;report['before']=snapshot()
        assert report['before']['domain_asset'].startswith(SRC+'/')
        yield from shared.capture('Before')
        assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    install()
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    shared.verify_saved_water();report['after']=snapshot();assert report['after']==report['before']
    report['native_support']=shared.native_support();report['outlet_support']=shared.outlet_support()
    yield from shared.verify_saved_height()
    report['saved_and_reloaded']=True
    yield from shared.capture('After')
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    shared.verify_saved_water();assert snapshot()==report['before']
    report['ok']=True

def finish(error=None):
    global gen
    gen=None
    if error:report['ok']=False;report['error']=error;u.log_error(error)
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global busy,next_at
    if busy:return
    try:
        if time.monotonic()-started>1300:raise RuntimeError('Shore refinement timeout')
        if time.monotonic()<next_at:return
        busy=True;delay=next(gen);next_at=time.monotonic()+delay
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False

gen=run();started=time.monotonic();next_at=started
handle=u.register_slate_post_tick_callback(tick)
