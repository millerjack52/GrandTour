"""Independent recovery point for the installed LiDAR map and source assets."""
from pathlib import Path
import hashlib,json,shutil
R=Path('C:/GrandTour');O=R/'Art/Export/LidarFloraTransfer';F=O/'baseline.json'
MAP=R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
NEW='FloraTrailStyle'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify(allow_map=False):
 if not F.exists():
  O.mkdir(parents=True,exist_ok=True);b=R/'Saved/LidarFloraTransferBackup/2026-11-19';b.mkdir(parents=True,exist_ok=False)
  shutil.copy2(MAP,b/MAP.name)
  paths=[p for name in ('LidarStudy','FloraTrail','FloraGroup','FloraTreeLightBench','FloraTreeLighting') for p in (R/'Content/GrandTour/ArtTests'/name).rglob('*') if p.is_file() and NEW not in p.parts]
  F.write_text(json.dumps({'backup':str(b/MAP.name),'map':MAP.relative_to(R).as_posix(),'hashes':{p.relative_to(R).as_posix():sha(p) for p in paths}},indent=2))
 d=json.loads(F.read_text());assert sha(Path(d['backup']))==d['hashes'][d['map']]
 for rel,h in d['hashes'].items():
  if allow_map and rel==d['map']:continue
  assert sha(R/rel)==h,rel
 return len(d['hashes'])
if __name__=='__main__':
 import sys
 print('Protected packages:',verify('--allow-map' in sys.argv))
