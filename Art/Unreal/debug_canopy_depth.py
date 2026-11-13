import unreal as u,sys,json
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph
import canopy_depth as C
for kind in ['Mature','Pole','Edge']:
 m=u.load_asset(C.DEST+'/'+kind+'/M_PD_TreeProxy');g=Graph(m,'TemporaryCanopyDebug')
 g.output(g.vector((100000,0,100000)),u.MaterialProperty.MP_EMISSIVE_COLOR)
 g.output(g.vector((1,0,1)),u.MaterialProperty.MP_BASE_COLOR)
 u.MaterialEditingLibrary.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m,False)
u.SystemLibrary.quit_editor()
