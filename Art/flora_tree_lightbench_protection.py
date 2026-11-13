"""Read-only guard for scene, shared assets and settings during isolated tests."""
from pathlib import Path
import hashlib,json,sys
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTreeLightBench';F=O/'protected-before.json'
def verify():
 data=json.loads(F.read_text())
 for p,h in data.items():
  assert Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 return len(data)
def prepare():
 if F.exists():return verify()
 O.mkdir(parents=True,exist_ok=True)
 paths=list((R/'Content').rglob('*.umap'))+list((R/'Art').glob('flora_trail*.json'))
 for name in ['FloraTrail','FloraGroup','FloraParity']:paths+=list((R/'Content/GrandTour/ArtTests'/name).rglob('*.uasset'))
 data={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 assert len(data)>100;F.write_text(json.dumps(data,indent=2));return len(data)
if __name__=='__main__':print(prepare() if '--prepare' in sys.argv else verify())
