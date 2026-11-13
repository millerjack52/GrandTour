import unreal as u,sys,json,time,traceback
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
import valley_ground
try:
    result=valley_ground.install();result['time']=time.time()
except Exception:
    result=dict(ok=False,time=time.time(),error=traceback.format_exc());u.log_error(result['error'])
(valley_ground.QA/'build-result.json').write_text(json.dumps(result,indent=2))
u.SystemLibrary.quit_editor()
