import unreal as u,json,traceback,hashlib,shutil
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/Driving')
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
source=Path('C:/GrandTour/Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap')
report={'ok':False,'cars':{}}
try:
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP)
    shutil.copy2(source,OUT/'before-seat-fix.umap')
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if not a.get_actor_label().startswith('Benmore_Fleet_') or '/FleetDriving/' not in a.get_class().get_path_name():continue
        cdo=u.get_default_object(a.get_class());a.modify()
        for prop in ['driver_eye_offset','enter_needs_open_door','chase_arm_length','chase_pivot_height']:
            a.set_editor_property(prop,cdo.get_editor_property(prop))
        report['cars'][a.get_actor_label()]=list(a.get_editor_property('driver_eye_offset').to_tuple())
    assert len(report['cars'])==6
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    f=OUT.parent/'placement-report.json';r=json.loads(f.read_text());r['saved_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();f.write_text(json.dumps(r,indent=2))
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'seat-fix-report.json').write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
