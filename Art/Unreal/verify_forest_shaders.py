"""Read saved materials in an empty editor and verify their rebuild hooks."""
import unreal as u,sys,json,traceback
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
import forest_shaders
try:
    forest_shaders.verify()
except Exception:
    result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
    (forest_shaders.QA/'verified.json').write_text(json.dumps(result,indent=2))
u.SystemLibrary.quit_editor()
