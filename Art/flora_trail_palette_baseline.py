"""Preserve the saved daylight and isolated calibration before palette experiments.

No Unreal import: preparation and integrity checks run with the renderer closed.
The manifest is local evidence and is deliberately excluded from source control.
"""
import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

ROOT = Path('C:/GrandTour')
OUT = ROOT / 'Art/Export/FloraTrail/PaletteCandidate'
MANIFEST = OUT / 'baseline.json'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify():
    data = json.loads(MANIFEST.read_text())
    for path, expected in data['protected_hashes'].items():
        assert digest(path) == expected, f'Protected file changed: {path}'
    for relative, expected in data['backup_hashes'].items():
        assert digest(Path(data['backup']) / relative) == expected, relative
    return data


def prepare():
    if MANIFEST.exists():
        return verify()  # Never silently replace the original baseline.
    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads((ROOT / 'Art/Export/FloraTrail/build-report.json').read_text())
    assert old['ok']
    for path, expected in old['package_hashes'].items():
        assert digest(path) == expected, path
    historic = json.loads((ROOT / 'Art/Export/FloraTreeLightBench/protected-before.json').read_text())
    files = {Path(p) for p in historic}
    for folder in ['FloraTrail', 'FloraTreeLighting', 'FloraTreeLightBench', 'LidarStudy']:
        files.update(p for p in (ROOT / 'Content/GrandTour/ArtTests' / folder).rglob('*')
                     if p.suffix in ('.uasset', '.umap'))
    # Retain historic source protection, allowing only previously documented scene changes.
    for path, expected in historic.items():
        if '/FloraTrail/' not in path.replace('\\', '/') and Path(path).name not in (
                'flora_trail_settings.json', 'flora_trail_canopy_settings.json'):
            assert digest(path) == expected, path
    files.update(ROOT / 'Art' / name for name in (
        'flora_trail_settings.json', 'flora_trail_canopy_settings.json',
        'flora_trail_source34_settings.json', 'flora_trail_sunlight_settings.json',
        'flora_trail_atmosphere_settings.json'))
    files.add(ROOT / 'Art/Export/FloraTrail/build-report.json')
    backup = ROOT / 'Saved/FloraTrailBackups' / ('palette-' + str(time.time_ns()))
    backup.mkdir(parents=True)
    backed = {}
    for path in sorted(files):
        # Recoverable scene + calibration packages and settings; LiDAR remains hash-protected.
        relative = path.relative_to(ROOT)
        if any(part in relative.parts for part in ('FloraTrail', 'FloraTreeLighting', 'FloraTreeLightBench')) or path.suffix == '.json':
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            backed[relative.as_posix()] = digest(target)
    data = {'backup': str(backup), 'created_unix': time.time(),
            'protected_hashes': {str(p): digest(p) for p in sorted(files)},
            'backup_hashes': backed,
            'scope': 'Saved daylight and isolated calibration recoverable; LiDAR and source packages protected; no scene edits.'}
    MANIFEST.write_text(json.dumps(data, indent=2) + '\n')
    return verify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    data = verify() if args.verify else prepare()
    print(json.dumps({'backup': data['backup'], 'protected': len(data['protected_hashes']),
                      'backed_up': len(data['backup_hashes'])}, indent=2))
