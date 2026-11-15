"""Freeze the current pine trial and existing FloraTrail packages before mud tests."""
import json,hashlib,shutil,time
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/MudTrial';F=O/'baseline.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 from flora_trail_palette_baseline import verify as original
 from flora_pine_match_baseline import verify as pine
 original();pine(True)
 if not F.exists():
  O.mkdir(parents=True,exist_ok=True);root=R/'Content/GrandTour/ArtTests/FloraTrail/PineTrial'
  backup=R/'Saved/FloraTrailBackups'/('mud-trial-'+str(time.time_ns()));shutil.copytree(root,backup)
  F.write_text(json.dumps({'backup':str(backup),'hashes':{p.relative_to(R).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}},indent=2))
 data=json.loads(F.read_text())
 for p,h in data['hashes'].items():
  assert sha(R/p)==h,p
  b=Path(data['backup'])/(R/p).relative_to(R/'Content/GrandTour/ArtTests/FloraTrail/PineTrial');assert sha(b)==h,b
 return data
if __name__=='__main__':print(json.dumps({'protected_pine_packages':len(verify()['hashes'])}))
