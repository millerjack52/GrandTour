"""Recoverable pine-only baseline; keep every existing scene package protected."""
import hashlib,json,shutil,time
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/PineMatch';MANIFEST=O/'baseline.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
 O.mkdir(parents=True,exist_ok=True)
 if MANIFEST.exists():return json.loads(MANIFEST.read_text())
 root=R/'Content/GrandTour/ArtTests/FloraTrail/PineTrial'
 backup=R/'Saved/FloraTrailBackups'/('pine-match-'+str(time.time_ns()))
 shutil.copytree(root,backup)
 data={'backup':str(backup),'hashes':{str(p.relative_to(R)):sha(p) for p in root.rglob('*') if p.is_file()},'allowed':['Content/GrandTour/ArtTests/FloraTrail/PineTrial/Assets/M_Source34_pine_f002.uasset','Content/GrandTour/ArtTests/FloraTrail/PineTrial/Assets/M_SourceBark_pine_f002.uasset']}
 MANIFEST.write_text(json.dumps(data,indent=2));return data
def verify(allow_install=False):
 from flora_trail_palette_baseline import verify as original
 original();data=prepare()
 for path,digest in data['hashes'].items():
  p=R/path;back=Path(data['backup'])/p.relative_to(R/'Content/GrandTour/ArtTests/FloraTrail/PineTrial')
  assert sha(back)==digest,back
  # Narrow the initial exploratory allowance: the selected correction changes
  # foliage only. Bark is now protected even in manifests created earlier.
  allowed=Path(path).as_posix().endswith('/Assets/M_Source34_pine_f002.uasset')
  if not allow_install or not allowed:assert sha(p)==digest,path
 return data
if __name__=='__main__':
 import sys
 data=verify('--installed' in sys.argv);print(json.dumps({'backup':data['backup'],'files':len(data['hashes'])}))
