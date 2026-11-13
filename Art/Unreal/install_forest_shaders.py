"""Compile map-owned materials without retaining the populated world in memory."""
import unreal as u,sys,json,traceback,time
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
import forest_shaders
try:
    forest_shaders.install(asset_only=True)
    if forest_shaders.enabled():forest_shaders.verify()
    result=dict(ok=True,time=time.time())
except Exception:
    result=dict(ok=False,time=time.time(),error=traceback.format_exc());u.log_error(result['error'])
(forest_shaders.QA/'build-result.json').write_text(json.dumps(result,indent=2))
u.SystemLibrary.quit_editor()
