"""Protect the post-transfer LiDAR map before the fine-grass restoration."""
from pathlib import Path
import json,shutil,sys
from lidar_flora_transfer_baseline import sha,verify as verify_source
R=Path('C:/GrandTour');O=R/'Art/Export/LidarGrassRecovery';F=O/'baseline.json'
MAP=R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
def verify(allow_map=False):
 verify_source(True)
 if not F.exists():
  expected=json.loads((O/'compare-report.json').read_text());assert expected['ok']
  assert sha(MAP)==expected['original_map_sha256'],'Map changed since comparison'
  backup=R/'Saved/LidarGrassRecoveryBackup/2026-11-19';backup.mkdir(parents=True,exist_ok=False)
  shutil.copy2(MAP,backup/MAP.name)
  files=[p for p in (R/'Content/GrandTour/ArtTests/LidarStudy').rglob('*') if p.is_file() and 'GrassRecovery' not in p.parts]
  F.write_text(json.dumps({'backup':str(backup/MAP.name),'map':MAP.relative_to(R).as_posix(),'hashes':{p.relative_to(R).as_posix():sha(p) for p in files}},indent=2))
 d=json.loads(F.read_text());assert sha(Path(d['backup']))==d['hashes'][d['map']]
 for f,h in d['hashes'].items():
  if allow_map and f==d['map']:continue
  assert sha(R/f)==h,f
 return len(d['hashes'])
if __name__=='__main__':print('Grass recovery protected packages:',verify('--allow-map' in sys.argv))
