"""Ferrari-only wheel asset tuning. Preserve map instances, power curve and all other cars."""
import hashlib,json,shutil,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Saved/FerrariDrivingQA';OUT.mkdir(parents=True,exist_ok=True)
report=dict(ok=False,wheels=[])
try:
    for axle,rate,damping in [('Front',260.,.72),('Rear',280.,.76)]:
        asset='/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288_Wheel'+axle
        path=ROOT/('Content/'+asset[len('/Game/'):] +'.uasset')
        backup=ROOT/'Saved/WorkshopBackups/20261027-power-consistency'/path.relative_to(ROOT)
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(path,backup)
        bp=u.load_asset(asset);w=u.get_default_object(bp.generated_class())
        values=dict(spring_rate=rate,suspension_damping_ratio=damping,suspension_max_raise=8.,suspension_max_drop=12.)
        if axle=='Front':values['max_steer_angle']=35.
        before={k:w.get_editor_property(k) for k in values}
        bp.modify();w.modify()
        for k,v in values.items():w.set_editor_property(k,v)
        assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
        report['wheels'].append(dict(asset=asset,before=before,after=values,backup=str(backup),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'tune.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
