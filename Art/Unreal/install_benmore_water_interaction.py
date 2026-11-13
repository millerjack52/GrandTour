"""Install material-only changes; assert placements/domain/handling are preserved."""
import unreal as u
import sys,json,time,traceback,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as shared
from benmore_water_interaction import make,make_spray,DEST
OUT=ROOT/'Art/Export/BenmoreGaea/WaterInteraction';OUT.mkdir(exist_ok=True)
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeWaterInteraction'
report=dict(ok=False,driving_tested=False,timings_collected=False);busy=False

def snapshot():
    sheet=shared.refs()['Benmore_RS_WaterDomain'];domain=sheet.get_editor_property('water_domain')
    path=domain.get_path_name().split('.')[0]
    return dict(instances=shared.signature(),roads=shared.signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail']),profiles=shared.profiles(),queries=json.loads(json.dumps(shared.queries())),domain=path,
        domain_sha256=hashlib.sha256((ROOT/'Content'/path.removeprefix('/Game/')).with_suffix('.uasset').read_bytes()).hexdigest(),
        runtime={k:sheet.get_editor_property(k) for k in ['field_cell_cm','max_sim_cells','wind_ripple_cm','rain_drop_cm','dry_cut_cm']},
        drive_sha256=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest())

def run():
    assert shared.les.load_level(shared.LEVEL)
    if not shared.eal.does_asset_exist(BACKUP):
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),BACKUP)
        assert shared.les.load_level(shared.LEVEL)
    report['before']=snapshot();report['backup']=BACKUP
    river=make('River');make('Lake');make_spray();yield 15
    sheet=shared.refs()['Benmore_RS_WaterDomain'];sheet.set_editor_property('surface_material_path',river.get_path_name())
    shared.DEST=DEST;shared.clean_saved_water();assert snapshot()==report['before']
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),shared.LEVEL)
    assert shared.les.load_level('/Engine/Maps/Entry');assert shared.les.load_level(shared.LEVEL)
    shared.verify_saved_water();report['after']=snapshot();assert report['after']==report['before']
    sheet=shared.refs()['Benmore_RS_WaterDomain'];sheet.preview_water_at(u.Vector2D(-68000,22000),0,True)
    components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
    mids=[c.get_material(0) for c in components]
    assert all(m.get_scalar_parameter_value('WakeDetailReady')==1 for m in mids)
    textures=[m.get_texture_parameter_value('DetailTex') for m in mids]
    assert len(mids)==4 and all(t==textures[0] for t in textures)
    report['shared_existing_detail_texture']=True
    assert shared.les.load_level('/Engine/Maps/Entry');assert shared.les.load_level(shared.LEVEL)
    assert snapshot()==report['before'];report['saved_and_reloaded']=True;report['ok']=True

def tick(dt):
    global busy,next_at
    if busy or time.monotonic()<next_at:return
    busy=True
    try:
        if time.monotonic()-started>600:raise RuntimeError('Install timeout')
        next_at=time.monotonic()+next(gen)
    except (StopIteration,Exception) as e:
        if not isinstance(e,StopIteration):report['error']=traceback.format_exc();report['ok']=False;u.log_error(report['error'])
        (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
        u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    finally:busy=False
gen=run();started=time.monotonic();next_at=started;handle=u.register_slate_post_tick_callback(tick)
