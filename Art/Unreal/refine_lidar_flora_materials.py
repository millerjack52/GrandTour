import unreal as u,sys,json,traceback
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraIntegration';sys.path.insert(0,str(R/'Art/Unreal'))
import lidar_flora_materials as F, lidar_logging_trial as T
r={'ok':False}
try:
 cfg=json.loads((O/'profile.json').read_text());route=T.route(json.loads((R/'Art/Export/LidarStudy/Place/roads.json').read_text()))
 for role in ['Terrain','Detail']:F.ground(u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/CohesiveStyle/M_Evergreen'+role),role,route,cfg)
 r['ok']=True
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'materials-report.json').write_text(json.dumps(r,indent=2));u.SystemLibrary.quit_editor()
