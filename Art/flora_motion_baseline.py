"""Protect the accepted ground study and every earlier source/scene baseline."""
from pathlib import Path
import json,hashlib,shutil,time
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Motion');F=O/'baseline.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 from flora_pine_brush_baseline import verify as previous
 previous();root=R/'Content/GrandTour/ArtTests/FloraTrail/Woodland/GroundPatches/v2'
 assert root.is_dir()
 if not F.exists():
  O.mkdir(parents=True,exist_ok=True);backup=Path('D:/GrandTourAssets/Backups')/('flora-motion-'+str(time.time_ns()));shutil.copytree(root,backup)
  F.write_text(json.dumps({'backup':str(backup),'hashes':{p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}},indent=2))
 data=json.loads(F.read_text());assert len(data['hashes'])==4
 for p,h in data['hashes'].items():
  assert sha(root/p)==h,p
  assert sha(Path(data['backup'])/p)==h,p
 return data
if __name__=='__main__':print(json.dumps({'protected_ground_packages':len(verify()['hashes'])}))
