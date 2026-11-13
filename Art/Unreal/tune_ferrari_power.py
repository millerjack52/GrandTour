"""Ferrari-specific sport/rally powertrain. Keep the existing expedition art and mass."""
import unreal as u,json,traceback,shutil,hashlib
from pathlib import Path
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/BenmoreFleet/FerrariPower';OUT.mkdir(exist_ok=True)
DEST='/Game/GrandTour/Vehicles/Ferrari288Good'
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
KEYS=[(0,.48),(900,.58),(2000,.74),(3500,.94),(4500,1.),(5500,.98),(6500,.94),(7000,.88),(7500,.72)]
report={'ok':False,'intent':'Sport/rally gameplay tune; not a claim of factory handling specifications.'}
def apply(pawn,curve):
    m=pawn.get_chaos_movement();m.modify()
    drivetrain=pawn.get_drivetrain();drivetrain.modify();drivetrain.set_editor_property('centre_split_front',0.)
    e=m.get_editor_property('engine_setup')
    for key,value in {'max_torque':450.,'max_rpm':7500.,'engine_idle_rpm':900.,'engine_brake_effect':.05}.items():e.set_editor_property(key,value)
    tc=e.get_editor_property('torque_curve');tc.set_editor_property('external_curve',curve);e.set_editor_property('torque_curve',tc);m.set_editor_property('engine_setup',e)
    t=m.get_editor_property('transmission_setup')
    for key,value in {'forward_gear_ratios':[3.4,2.25,1.58,1.18,.92],'final_ratio':4.1,'change_up_rpm':7000.,'change_down_rpm':2700.,'gear_change_time':.22}.items():t.set_editor_property(key,value)
    m.set_editor_property('transmission_setup',t)
try:
    backups=OUT/'before-tune';backups.mkdir(exist_ok=True)
    for relative in ['Content/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.uasset','Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap']:
        p=ROOT/relative;b=backups/p.name
        if not b.exists():shutil.copy2(p,b)
    csv=OUT/'CF_Ferrari288_Torque.csv';csv.write_text('\n'.join(str(x)+','+str(y) for x,y in KEYS)+'\n')
    factory=u.CSVImportFactory();settings=u.CSVImportSettings();settings.set_editor_property('import_type',u.CSVImportType.ECSV_CURVE_FLOAT);factory.set_editor_property('automated_import_settings',settings)
    task=u.AssetImportTask()
    for key,value in {'filename':str(csv),'destination_path':DEST,'automated':True,'replace_existing':True,'save':True,'factory':factory}.items():task.set_editor_property(key,value)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);curve=u.load_asset(DEST+'/CF_Ferrari288_Torque');assert isinstance(curve,u.CurveFloat)
    report['curve_values']={str(rpm):curve.get_float_value(rpm) for rpm,value in KEYS}
    assert all(abs(curve.get_float_value(rpm)-value)<.001 for rpm,value in KEYS)
    bp=u.load_asset(DEST+'/BP_Ferrari288');bp.modify();apply(u.get_default_object(bp.generated_class()),curve);assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(MAP)
    car=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label()=='Benmore_Fleet_Ferrari288')
    car.modify();apply(car,curve);assert les.save_current_level()
    report.update(ok=True,max_torque_nm=450,rev_limit=7500,upshift_rpm=7000,ratios=[3.4,2.25,1.58,1.18,.92],final_ratio=4.1,shift_seconds=.22,drive_layout='Rear-wheel drive',centre_split_front=0.)
    placement=OUT.parent/'placement-report.json';p=json.loads(placement.read_text());p['saved_sha256']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap').read_bytes()).hexdigest();p['ferrari_power_tune']='FerrariPower/tune-report.json';placement.write_text(json.dumps(p,indent=2))
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'tune-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
