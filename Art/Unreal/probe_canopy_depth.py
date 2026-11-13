import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
from forest_shaders import connected_nodes
report={}
for k,kind in enumerate(['Mature','Pole','Edge']):
 m=u.load_asset(C.DEST+'/SM_CD_Canopy_'+str(k));b=m.get_bounds()
 row=dict(bounds=str(b),screens=list(C.sm.get_lod_screen_sizes(m)),materials=[str(s) for s in m.get_editor_property('static_materials')],sections=[m.get_num_sections(i) for i in range(4)])
 row['apis']=[x for x in dir(C.sm) if 'material' in x or 'section' in x]
 for method in ['get_lod_material_slot','get_material_index']:
  if hasattr(C.sm,method):
   try:row[method]=str(getattr(C.sm,method)(m,3,0))
   except Exception as e:row[method]=str(e)
 mat=u.load_asset(C.DEST+'/'+kind+'/M_PD_TreeProxy');row['nodes']=[dict(type=n.get_class().get_name(),desc=str(n.get_editor_property('desc'))) for n in connected_nodes(mat)]
 row['stats']=str(u.MaterialEditingLibrary.get_statistics(mat));report[k]=row
(C.QA/'probe.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
