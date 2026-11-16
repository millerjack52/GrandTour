"""Recoverable protection for the approved CrownForm v3 and earlier baselines."""
from pathlib import Path
import json,hashlib,shutil,time
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/PineBrush');F=O/'baseline.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 from flora_crown_baseline import verify as previous
 previous();root=R/'Content/GrandTour/ArtTests/FloraTrail/Woodland/CrownForm/v3'
 assert root.is_dir()
 if not F.exists():
  O.mkdir(parents=True,exist_ok=True);backup=Path('D:/GrandTourAssets/Backups')/('pine-brush-'+str(time.time_ns()));shutil.copytree(root,backup)
  F.write_text(json.dumps({'backup':str(backup),'hashes':{p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}},indent=2))
 data=json.loads(F.read_text())
 assert data['hashes']
 assert set(data['hashes'])=={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
 for p,h in data['hashes'].items():
  assert sha(root/p)==h,p
  assert sha(Path(data['backup'])/p)==h,p
 return data
if __name__=='__main__':print(json.dumps({'protected_crown_packages':len(verify()['hashes'])}))
