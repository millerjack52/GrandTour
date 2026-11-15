"""Protect the preceding fern experiment and all earlier scene baselines."""
from pathlib import Path
import json,hashlib,shutil,time
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Woodland');F=O/'baseline.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 from flora_fern_surface_baseline import verify as previous
 previous();root=R/'Content/GrandTour/ArtTests/FloraTrail/FernSurface'
 if not F.exists():
  O.mkdir(parents=True,exist_ok=True);backup=Path('D:/GrandTourAssets/Backups')/('woodland-'+str(time.time_ns()));shutil.copytree(root,backup)
  F.write_text(json.dumps({'backup':str(backup),'hashes':{p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}},indent=2))
 data=json.loads(F.read_text())
 for p,h in data['hashes'].items():
  assert sha(root/p)==h,p
  assert sha(Path(data['backup'])/p)==h,p
 return data
if __name__=='__main__':print(json.dumps({'protected_fern_packages':len(verify()['hashes'])}))
