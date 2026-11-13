"""Matched fixed-camera motion review. Saves only the river's material bindings."""
import unreal as u
import sys,json,time,traceback,hashlib,os,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as shared
DETAIL=os.environ.get('GT_WATER_ART_VARIANT')=='Detail'
RAPIDS=os.environ.get('GT_WATER_ART_VARIANT')=='Rapids'
if DETAIL:
    from benmore_water_detail import precombine,surface,DEST,install_spray
elif RAPIDS:
    from benmore_water_rapids import precombine,surface,DEST
else:
    from benmore_water_motion import precombine,surface,DEST
VARIANT='Detail' if DETAIL else 'Rapids' if RAPIDS else 'Motion'
OUT=ROOT/('Art/Export/BenmoreGaea/Water'+VARIANT+'_20261011');OUT.mkdir(exist_ok=True)
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeWater'+VARIANT
report=dict(ok=False,images=[],camera_static=True,frame_step_s=.125,frames_per_sequence=24,performance_measured=False)
busy=False;pace_world=None;pace_rt=None

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def snapshot():
    sheet=shared.refs()['Benmore_RS_WaterDomain'];domain=sheet.get_editor_property('water_domain')
    path=domain.get_path_name().split('.')[0]
    return dict(instances=shared.signature(),profiles=shared.profiles(),queries=json.loads(json.dumps(shared.queries())),
        domain_sha256=digest((ROOT/'Content'/path.removeprefix('/Game/')).with_suffix('.uasset')),
        drive_sha256=digest(ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap'),
        runtime={k:sheet.get_editor_property(k) for k in ['field_cell_cm','max_sim_cells','wind_ripple_cm','rain_drop_cm','dry_cut_cm']},
        spray_sha256=digest(ROOT/'Content/GrandTour/Materials/M_GT_WaterSpray.uasset'))

def load():
    global pace_world,pace_rt
    if pace_rt:u.RenderingLibrary.release_render_target2d(pace_rt)
    pace_world=None;pace_rt=None
    assert shared.les.load_level('/Engine/Maps/Entry')
    assert shared.les.load_level(shared.LEVEL)
    pace_world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    pace_rt=u.RenderingLibrary.create_render_target2d(pace_world,1,1,u.TextureRenderTargetFormat.RTF_RGBA8)

def shot(cam,name):
    path=OUT/(name+'.png');stamp=time.time()
    u.AutomationLibrary.take_high_res_screenshot(960,600,str(path),cam)
    yield .1
    while not path.exists() or path.stat().st_mtime<stamp:
        if time.time()-stamp>90:raise RuntimeError('Screenshot timeout '+name)
        yield .1
    report['images'].append(str(path))

def capture(label):
    refs=shared.refs();sheet=refs['Benmore_RS_WaterDomain'];cam=refs['Benmore_RL_Camera_Ford']
    p=shared.crossings[0]['center_m']
    pos=u.Vector((p[0]+5)*100,(p[1]-6)*100,(shared.height(shared.after,p[0]+5,p[1]-6)+1.7)*100)
    target=u.Vector(p[0]*100,p[1]*100,p[2]*100)
    if DETAIL:
        pos=u.Vector((p[0]+2)*100,(p[1]-1)*100,(shared.height(shared.after,p[0]+2,p[1]-1)+1.65)*100)
        target=u.Vector((p[0]-1)*100,(p[1]+2)*100,p[2]*100)
    cam.set_actor_location(pos,False,False);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
    cam.camera_component.set_field_of_view(65)
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(pos,cam.get_actor_rotation())
    sheet.preview_water_at(u.Vector2D(p[0]*100,p[1]*100),0,True)
    components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
    mats=[c.get_material(0) for c in components]
    spray=refs.get('Benmore_RiffleSpray') if DETAIL else None
    spray_mid=spray.static_mesh_component.create_dynamic_material_instance(0) if spray else None
    sheet.preview_ambient_waves(12)
    for m in mats:m.set_scalar_parameter_value('WaterTimeOverride',12)
    if spray_mid:spray_mid.set_scalar_parameter_value('WaterTimeOverride',12)
    yield 25
    report.setdefault('bindings',{})[label]=dict(precombine=sheet.get_editor_property('ambient_wave_material').get_path_name(),
        surface=sheet.get_editor_property('surface_material_path'),ready=[m.get_scalar_parameter_value('AmbientReady') for m in mats])
    assert all(m.get_scalar_parameter_value('AmbientReady')==1 for m in mats)
    report.setdefault('camera',{})[label]=dict(position=list(pos.to_tuple()),rotation=list(cam.get_actor_rotation().to_tuple()),fov=65)
    for i in range(24):
        clock=12+i*.125;sheet.preview_ambient_waves(clock)
        for m in mats:m.set_scalar_parameter_value('WaterTimeOverride',clock)
        if spray_mid:spray_mid.set_scalar_parameter_value('WaterTimeOverride',clock)
        # Flush both texture/parameter updates, then accumulate several frames
        # at the exact same clock so temporal filtering cannot smear the change.
        for _ in range(4):yield 0
        yield from shot(cam,'%s_%02d'%(label,i))
        if DETAIL and label=='After' and i==0:
            for m in mats:m.set_scalar_parameter_value('RefractionStrength',0)
            for _ in range(8):yield 0
            yield from shot(cam,'Refraction_Off')
            for m in mats:m.set_scalar_parameter_value('RefractionStrength',1)
            for _ in range(8):yield 0
            yield from shot(cam,'Refraction_On')
            if spray:
                spray.set_actor_hidden_in_game(True);spray.set_is_temporarily_hidden_in_editor(True)
                for _ in range(8):yield 0
                yield from shot(cam,'Spray_Off')
                spray.set_actor_hidden_in_game(False);spray.set_is_temporarily_hidden_in_editor(False)
    pos=u.Vector((p[0]+14)*100,(p[1]-16)*100,(shared.height(shared.after,p[0]+14,p[1]-16)+3)*100)
    cam.set_actor_location(pos,False,False);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(pos,cam.get_actor_rotation())
    yield 8
    yield from shot(cam,label+'_Wide')

def run():
    load();report['before']=snapshot()
    if not u.EditorAssetLibrary.does_asset_exist(BACKUP):assert u.EditorAssetLibrary.duplicate_asset(shared.LEVEL,BACKUP)
    report['backup']=BACKUP
    pre=precombine();river=surface('River');surface('Lake');yield 5
    if RAPIDS:
        # The accepted motion-pass sequence has identical geometry and camera.
        # Reuse its engine frames explicitly rather than recapturing unchanged art.
        baseline=ROOT/'Art/Export/BenmoreGaea/WaterMotion_20261011'
        prior=json.loads((baseline/'install-report.json').read_text())
        assert prior['ok'] and prior['after']==report['before']
        for suffix in [('%02d'%i) for i in range(24)]+['Wide']:
            path=OUT/('Before_'+suffix+'.png');shutil.copy2(baseline/('After_'+suffix+'.png'),path)
            report['images'].append(str(path))
        report.setdefault('camera',{})['Before']=prior['camera']['After']
        report['baseline_source']=str(baseline)
    elif DETAIL and (OUT/'iteration1-report.json').exists():
        # Preserve the matched original sequence across tuning iterations.
        # Loading a world that asset-existence queries marked Standalone can
        # trip Unreal's old-world GC assertion; no map switch is needed here.
        prior=json.loads((OUT/'iteration1-report.json').read_text())
        assert prior['ok'] and prior['before']==report['before']
        assert 'WaterRapids' in prior['bindings']['Before']['surface']
        for suffix in [('%02d'%i) for i in range(24)]+['Wide']:
            path=OUT/('Before_'+suffix+'.png');assert path.exists()
            report['images'].append(str(path))
        report.setdefault('camera',{})['Before']=prior['camera']['Before']
        report['baseline_source']=str(OUT/'iteration1-report.json')
    else:
        yield from capture('Before')
    load();assert snapshot()==report['before']
    sheet=shared.refs()['Benmore_RS_WaterDomain']
    sheet.set_editor_property('ambient_wave_material',pre)
    sheet.set_editor_property('surface_material_path',river.get_path_name())
    shared.DEST=DEST;shared.clean_saved_water()
    if DETAIL:
        install_spray()
        report['spray']=json.loads((OUT/'spray-seeds.json').read_text())
    assert snapshot()==report['before']
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),shared.LEVEL)
    load();shared.verify_saved_water()
    assert shared.refs()['Benmore_RS_WaterDomain'].get_editor_property('ambient_wave_material')==pre
    report['after']=snapshot();assert report['before']==report['after']
    report['saved_and_reloaded']=True
    yield from capture('After')
    assert report['camera']['Before']==report['camera']['After']
    # Fresh PIE verifies the saved assets animate on the normal game clock.
    load();shared.les.editor_request_begin_play();yield 8
    world=u.EditorLevelLibrary.get_game_world();assert world
    sheet=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if a.get_editor_property('water_domain'))
    m=sheet.get_component_by_class(u.ProceduralMeshComponent).get_material(0)
    u.GameplayStatics.set_game_paused(world,False)
    a=m.get_scalar_parameter_value('AmbientClock');start_game=u.GameplayStatics.get_time_seconds(world)
    while u.GameplayStatics.get_time_seconds(world)-start_game<1:yield .05
    b=m.get_scalar_parameter_value('AmbientClock')
    assert b>a,(a,b)
    assert m.get_scalar_parameter_value('AmbientReady')==1
    report['runtime_clock']={'start':a,'end':b,'advancing':True,'precombine':sheet.get_editor_property('ambient_wave_material').get_path_name()}
    if RAPIDS or DETAIL:
        components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[x.static_mesh_component for x in sheet.get_editor_property('domain_surfaces')]
        report['rapids_intensity']=[x.get_material(0).get_scalar_parameter_value('RapidsIntensity') for x in components]
        report['surface_clocks']=[x.get_material(0).get_scalar_parameter_value('AmbientClock') for x in components]
        assert all(x==1 for x in report['rapids_intensity'])
        assert all(abs(x-b)<.0001 for x in report['surface_clocks'])
        components=[]
    m=None;sheet=None;world=None
    u.EditorLevelLibrary.editor_end_play();yield 2
    report['ok']=True

def tick(dt):
    global busy,next_at,pace_rt,pace_world,gen
    if busy:return
    busy=True
    try:
        if pace_world and pace_rt:u.RenderingLibrary.read_render_target_pixel(pace_world,pace_rt,0,0)
        if time.monotonic()-started>1100:raise RuntimeError('Motion review timeout')
        if time.monotonic()<next_at:return
        delay=next(gen);next_at=time.monotonic()+delay
    except (StopIteration,Exception) as e:
        if not isinstance(e,StopIteration):report['error']=traceback.format_exc();report['ok']=False;u.log_error(report['error'])
        (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
        if pace_rt:u.RenderingLibrary.release_render_target2d(pace_rt)
        pace_rt=None;pace_world=None;gen=None
        u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    finally:busy=False

gen=run();started=time.monotonic();next_at=started
handle=u.register_slate_post_tick_callback(tick)
