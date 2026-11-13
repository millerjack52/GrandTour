"""Tie rendered evidence to the asset versions checked by the offline audit."""
import hashlib,json
from pathlib import Path
ROOT=Path('C:/GrandTour')

def audited_fingerprint():
    report=json.loads((ROOT/'Art/Export/FloraDrive/audit-report.json').read_text())
    assert report['ok'],'Run the saved-asset audit first'
    hashes=report['package_hashes']
    for file,expected in hashes.items():
        assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==expected,'Asset changed since audit: '+file
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
