"""Install and compare the water pass without rebuilding the accepted channel."""
import unreal as u
import sys,json,time,traceback,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as shared
from benmore_water_balanced import make_balanced,DEST
OUT=ROOT/'Art/Export/BenmoreGaea/WaterBalanced_20261011';OUT.mkdir(exist_ok=True)
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeWaterBalanced'
report=dict(ok=False,images=[],timings_collected=False,driving_tested=False)
busy=False

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def snapshot():
    sheet=shared.refs()['Benmore_RS_WaterDomain'];domain=sheet.get_editor_property('water_domain')
    path=domain.get_path_name().split('.')[0]
    return dict(instances=shared.signature(),profiles=shared.profiles(),queries=json.loads(json.dumps(shared.queries())),
        domain_sha256=digest((ROOT/'Content'/path.removeprefix('/Game/')).with_suffix('.uasset')),
        drive_sha256=digest(ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap'),
        runtime={k:sheet.get_editor_property(k) for k in ['field_cell_cm','max_sim_cells','wind_ripple_cm','rain_drop_cm','dry_cut_cm']},
        spray_sha256=digest(ROOT/'Content/GrandTour/Materials/M_GT_WaterSpray.uasset'))

def shot(camera,name):
    path=OUT/(name+'.png');stamp=time.time()
    u.AutomationLibrary.take_high_res_screenshot(960,600,str(path),camera);yield .5
    while not path.exists() or path.stat().st_mtime<stamp:
        if time.time()-stamp>60:raise RuntimeError('Screenshot timeout '+name)
        yield .5
    report['images'].append(str(path))

def capture(suffix):
    refs=shared.refs();sheet=refs['Benmore_RS_WaterDomain'];cam=refs['Benmore_RL_Camera_Ford']
    p=shared.crossings[0]['center_m'];focus=u.Vector2D(p[0]*100,p[1]*100)
    pos=u.Vector((p[0]+5)*100,(p[1]-6)*100,(shared.height(shared.after,p[0]+5,p[1]-6)+1.7)*100)
    target=u.Vector(p[0]*100,p[1]*100,p[2]*100)
    cam.set_actor_location(pos,False,False);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(pos,cam.get_actor_rotation())
    sheet.preview_water_at(focus,0,True)
    yield 30
    for i in range(12):
        sheet.preview_ambient_waves(12+i/6)
        comps=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
        for c in comps:c.get_material(0).set_scalar_parameter_value('WaterTimeOverride',12+i/6)
        yield .2
        yield from shot(cam,'Flow_%s_%02d'%(suffix,i))

def run():
    assert shared.les.load_level(shared.LEVEL)
    report['before']=snapshot()
    if not u.EditorAssetLibrary.does_asset_exist(BACKUP):
        assert u.EditorAssetLibrary.duplicate_asset(shared.LEVEL,BACKUP)
    report['backup']=BACKUP
    yield from capture('Before')
    # Drop preview MIDs and temporary camera moves before saving anything.
    assert shared.les.load_level('/Engine/Maps/Entry');assert shared.les.load_level(shared.LEVEL)
    assert snapshot()==report['before']
    river=make_balanced('River');make_balanced('Lake');yield 10
    sheet=shared.refs()['Benmore_RS_WaterDomain'];sheet.set_editor_property('surface_material_path',river.get_path_name())
    shared.DEST=DEST;shared.clean_saved_water()
    assert snapshot()==report['before']
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),shared.LEVEL)
    assert shared.les.load_level('/Engine/Maps/Entry');assert shared.les.load_level(shared.LEVEL)
    shared.verify_saved_water();report['after']=snapshot();assert report['after']==report['before']
    report['saved_and_reloaded']=True
    yield from capture('After')
    report['ok']=True

def tick(dt):
    global busy,next_at
    if busy or time.monotonic()<next_at:return
    busy=True
    try:
        if time.monotonic()-started>900:raise RuntimeError('Balanced pass install timeout')
        next_at=time.monotonic()+next(gen)
    except (StopIteration,Exception) as e:
        if not isinstance(e,StopIteration):report['error']=traceback.format_exc();report['ok']=False;u.log_error(report['error'])
        (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
        u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    finally:busy=False

gen=run();started=time.monotonic();next_at=started;handle=u.register_slate_post_tick_callback(tick)
