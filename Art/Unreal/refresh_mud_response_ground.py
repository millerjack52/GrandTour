"""Update only the response scene's private ground material, with a local package backup."""
import sys,json,time,shutil,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import mud_response_materials
OUT=ROOT/'Art/Export/MudResponse';report={'ok':False}
try:
    package=ROOT/'Content/GrandTour/ArtTests/MudResponse/M_ResponseGround.uasset'
    backup=ROOT/'Saved/MudResponse'/('tyre-bed-'+str(time.time_ns()));backup.mkdir(parents=True)
    shutil.copy2(package,backup/package.name)
    material=mud_response_materials.ground()
    report.update(ok=True,material=material.get_path_name(),backup=str(backup/package.name))
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'material-report.json').write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
