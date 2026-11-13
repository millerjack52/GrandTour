import unreal as u,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
for kind in ['Mature','Pole','Edge']:
 for name in ['T_PD_TreeColour','T_PD_TreeNormalDepth']:
  t=u.load_asset(C.DEST+'/'+kind+'/'+name);t.set_editor_property('never_stream',True);assert u.EditorAssetLibrary.save_loaded_asset(t,False)
exec(compile((ROOT/'Art/Unreal/diagnose_canopy_projection.py').read_text(),'diagnose_canopy_projection.py','exec'))
