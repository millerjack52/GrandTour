"""Saved-file check; enables the tool explicitly and exercises real operators."""
import bpy,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import reference_fit_workbench as fit
out=Path('C:/GrandTour/Art/Export/VehicleTools/reference-fit-v01');file=out/'Crafted_Utility_Reference_Fit.blend'
before=hashlib.sha256(file.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(file));fit.register()
checks={};report0=fit.measure()
for key in ['side','hero','front']:
    bpy.ops.gtfit.view(key=key);checks[key+'_camera']=bpy.context.scene.camera.name=='FIT | '+key
    bg=bpy.context.scene.camera.data.background_images[0];checks[key+'_packed_reference']=bool(bg.image.packed_file)
bpy.context.scene.gtfit.reference_alpha=.25
checks['opacity_updates_all_cameras']=all(abs(c.data.background_images[0].alpha-.25)<1e-5 for c in bpy.data.objects if c.type=='CAMERA' and c.name.startswith('FIT | '))
bpy.ops.gtfit.report();checks['report_operator_wrote_text']='FIT | current-errors.json' in bpy.data.texts
checks['preserved_source_hidden']=bpy.data.collections['FIT | Preserved rejected v05'].hide_viewport and bpy.data.collections['FIT | Preserved rejected v05'].hide_render
checks['reopen_preserves_measurements']=abs(report0['bonnet_silhouette']['max_absolute_px']-21.499556517537286)<.02
fit.unregister();checks['check_did_not_modify_blend']=before==hashlib.sha256(file.read_bytes()).hexdigest()
assert all(checks.values()),checks
(out/'saved-workbench-checks.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
