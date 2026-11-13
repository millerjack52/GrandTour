"""Validate the saved section fingerprint before rendering/driving it."""
import hashlib,json
from pathlib import Path
def audited_fingerprint():
 r=json.loads(Path('C:/GrandTour/Art/Export/FloraTrail/build-report.json').read_text());assert r['ok']
 for p,h in r['package_hashes'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 return hashlib.sha256(json.dumps(r['package_hashes'],sort_keys=True).encode()).hexdigest()
