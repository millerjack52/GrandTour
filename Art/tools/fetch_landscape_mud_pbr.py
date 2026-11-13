"""Fetch the unchanged CC0 maps used by the isolated landscape mud study."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'Art/Textures/LandscapeMudPBR/provenance.json'


def fetch():
    for entry in json.loads(MANIFEST.read_text())['files']:
        path = ROOT / entry['path'].replace('\\', '/')
        if path.exists() and hashlib.md5(path.read_bytes()).hexdigest() == entry['md5']:
            continue
        request = urllib.request.Request(entry['url'], headers={'User-Agent': 'GrandTour-art-study/1.0'})
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
        if hashlib.md5(data).hexdigest() != entry['md5']:
            raise ValueError('Source checksum mismatch: ' + entry['url'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(path.relative_to(ROOT))


if __name__ == '__main__':
    fetch()
