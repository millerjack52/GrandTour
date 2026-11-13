"""Install only wave rendering, preserving stage93 terrain/domain/placements."""
import unreal as u
import sys,json,time,traceback,hashlib,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as shared
from benmore_flow_waves import make_precombine,make_surface,DEST,COARSE,FINE,HEIGHT_RANGE
OUT=ROOT/'Art/Export/BenmoreGaea/FlowWaves';OUT.mkdir(exist_ok=True)
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeFlowWaves'
report=dict(ok=False,driving_tested=False,timings_collected=False)
busy=False

def snapshot():
    sheet=shared.refs()['Benmore_RS_WaterDomain'];domain=sheet.get_editor_property('water_domain')
    path=domain.get_path_name().split('.')[0]
    return dict(instances=shared.signature(),roads=shared.signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail']),profiles=shared.profiles(),queries=json.loads(json.dumps(shared.queries())),domain=path,
        domain_sha256=hashlib.sha256((ROOT/'Content'/path.removeprefix('/Game/')).with_suffix('.uasset').read_bytes()).hexdigest(),
        runtime={k:sheet.get_editor_property(k) for k in ['field_cell_cm','max_sim_cells','wind_ripple_cm','rain_drop_cm','dry_cut_cm']},
        drive_sha256=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest())

def validate_precombine(material):
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    rt=u.RenderingLibrary.create_render_target2d(world,256,256,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1))
    mid=u.MaterialLibrary.create_dynamic_material_instance(world,material)
    # Test the actual GPU data (and alpha convention), not just generated source.
    errors=[]
    for clock in [0,12.375]:
        mid.set_scalar_parameter_value('WaveClock',clock)
        u.RenderingLibrary.clear_render_target2d(world,rt,u.LinearColor(0,0,0,1))
        u.RenderingLibrary.draw_material_to_render_target(world,rt,mid);yield 3
        pixels=u.RenderingLibrary.read_render_target_raw(world,rt,False)
        assert len(pixels)==256*256
        ranges=[[min(getattr(p,c) for p in pixels),max(getattr(p,c) for p in pixels)] for c in ['r','g','b','a']]
        def smooth(a,b,x):
            t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
        worst=[0,0,0,0]
        for y in [3,31,99,183,247]:
            for x in [7,67,113,197,251]:
                h=small=sx=sy=0
                for group,waves in [('h',COARSE),('small',FINE)]:
                    for nx,ny,a,w,phase in waves:
                        angle=math.tau*(nx*(x+.5)/256+ny*(y+.5)/256)-clock*w+phase
                        if group=='h':h+=a*math.sin(angle)
                        else:small+=a*math.sin(angle)
                        sx+=a*math.cos(angle)*math.tau*nx/12;sy+=a*math.cos(angle)*math.tau*ny/12
                foam=smooth(.002,.0055,small+h*.025)*smooth(.025,.085,math.hypot(sx,sy))
                expected=[.5+sx*.5,.5+sy*.5,.5+h/HEIGHT_RANGE,1-foam]
                actual=pixels[y*256+x]
                for i,c in enumerate(['r','g','b','a']):worst[i]=max(worst[i],abs(getattr(actual,c)-expected[i]))
        errors.append(dict(clock=clock,max_channel_error=worst,ranges=ranges))
        assert max(worst)<.007,errors
    report['gpu_precombine']=errors
    u.RenderingLibrary.release_render_target2d(rt)

def run():
    assert shared.les.load_level(shared.LEVEL)
    if not shared.eal.does_asset_exist(BACKUP):
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),BACKUP)
        assert shared.les.load_level(shared.LEVEL)
    report['before']=snapshot();report['backup']=BACKUP
    pre=make_precombine();river=make_surface('River');lake=make_surface('Lake');yield 15
    yield from validate_precombine(pre)
    sheet=shared.refs()['Benmore_RS_WaterDomain']
    sheet.set_editor_property('ambient_wave_material',pre)
    sheet.set_editor_property('surface_material_path',river.get_path_name())
    shared.DEST=DEST;shared.OUT=OUT
    mesh_report=json.loads((OUT/'mesh-prepare-report.json').read_text());assert mesh_report['ok']
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    outlet=shared.import_mesh('SM_GC_OutletSurface',river)
    shared.refs()['Benmore_RL_Outlet'].static_mesh_component.set_static_mesh(outlet)
    report['render_mesh']=mesh_report
    shared.clean_saved_water()
    assert snapshot()==report['before']
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),shared.LEVEL)
    assert shared.les.load_level('/Engine/Maps/Entry');assert shared.les.load_level(shared.LEVEL)
    shared.verify_saved_water();report['after']=snapshot();assert report['after']==report['before']
    sheet=shared.refs()['Benmore_RS_WaterDomain'];assert sheet.get_editor_property('ambient_wave_material')==pre
    sheet.preview_water_at(u.Vector2D(-68000,22000),0,True);sheet.preview_ambient_waves(12)
    components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
    materials=[c.get_material(0) for c in components]
    assert len(materials)==4
    textures=[m.get_texture_parameter_value('AmbientTex') for m in materials]
    assert textures[0] and all(t==textures[0] for t in textures)
    assert all(m.get_scalar_parameter_value('AmbientReady')==1 for m in materials)
    report['shared_texture']=dict(surfaces=len(materials),width=256,height=256,format='RGBA16F',mips=True,base_bytes=256*256*8,update_hz=30)
    # Effect-off switch must preserve physical queries.
    q=shared.queries();world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(world,'gt.Water.Domain.Ambient 0');sheet.preview_ambient_waves(13)
    assert all(m.get_scalar_parameter_value('AmbientReady')==0 for m in materials)
    assert shared.queries()==q
    u.SystemLibrary.execute_console_command(world,'gt.Water.Domain.Ambient 1');sheet.preview_ambient_waves(12)
    assert shared.queries()==q
    report['off_switch_physics_unchanged']=True
    # Reload discards transient previews. No editor RT/MID is persisted in the map.
    assert shared.les.load_level('/Engine/Maps/Entry');assert shared.les.load_level(shared.LEVEL)
    shared.verify_saved_water();assert snapshot()==report['before']
    report['saved_and_reloaded']=True;report['ok']=True

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
        if time.monotonic()-started>900:raise RuntimeError('Wave install timeout')
        if time.monotonic()<next_at:return
        busy=True;next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False

gen=run();started=time.monotonic();next_at=started
handle=u.register_slate_post_tick_callback(tick)
