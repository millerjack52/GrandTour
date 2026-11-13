import unreal as u,json,sys,time,shutil,importlib
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
qa=root/'Saved/LidarAuthoringQA/RS7Ground';qa.mkdir(exist_ok=True)
import lidar_first_section as section
import lidar_bank_ground_material as ground
importlib.reload(ground)
if not (qa/'backup.json').exists():
 backup=root/'Saved/LidarAuthoringBackups'/('RS7Ground-'+str(time.time_ns()));backup.mkdir()
 for name in ['M_BankSurface','M_BankEarth']:
  shutil.copy2(root/f'Content/GrandTour/ArtTests/LidarStudy/FirstSection/{name}.uasset',backup/f'{name}.uasset')
 (qa/'backup.json').write_text(json.dumps({'path':str(backup)},indent=2))
before=section.snapshot()
ground.build('M_BankSurface');ground.build('M_BankEarth')
assert section.snapshot()==before
(qa/'apply.json').write_text(json.dumps({'materials':['M_BankSurface','M_BankEarth'],'normal':'world-space surface gradient','texture_scales_cm':{'soil':200,'rock':110,'mineral_detail':35},'foliage_snapshot':before,'geometry_changed':False,'exposure_changed':False,'renderer_preset_changed':False,'collision_changed':False},indent=2))
print('BANK_GROUND_DETAIL_SAVED')
