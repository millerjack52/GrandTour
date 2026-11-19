"""Protect the currently installed source; do not replace unavailable historical audits."""
from pathlib import Path
import json,hashlib,shutil
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTransmissionStudy';F=O/'baseline.json'
BASE=R/'Content/GrandTour/ArtTests/FloraTrail/Woodland/CrownForm/v3'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def protected():
 roots=['Content/GrandTour/ArtTests/FloraTrail','Content/GrandTour/ArtTests/FloraGroup','Content/GrandTour/ArtTests/FloraTreeLightBench','Content/GrandTour/ArtTests/LidarStudy']
 return [p for root in roots for p in (R/root).rglob('*') if p.is_file() and 'TransmissionStudy' not in p.parts]
def verify():
 if not F.exists():
  O.mkdir(parents=True,exist_ok=True);backup=R/'Saved/FloraTransmissionBackup/v1'
  assert not backup.exists(),'Inspect existing backup before creating a new baseline'
  shutil.copytree(BASE,backup)
  F.write_text(json.dumps({'scope':'Installed C: packages; historical D: backup chain unavailable. No historical parity claim.','backup':str(backup),'hashes':{p.relative_to(R).as_posix():sha(p) for p in protected()}},indent=2))
 d=json.loads(F.read_text());assert d['hashes']
 for rel,h in d['hashes'].items():assert sha(R/rel)==h,rel
 for p in BASE.glob('*'):
  if p.is_file():assert sha(p)==sha(Path(d['backup'])/p.name),p.name
 return len(d['hashes'])
if __name__=='__main__':print('Protected installed packages:',verify())
