"""Inventory purchased archives and stage untouched working copies on the asset drive."""
import collections
import json
from pathlib import Path
import zipfile

DOWNLOADS = Path('C:/Users/mille/Downloads')
STAGE = Path('D:/GrandTourAssets/FlippedNormals')
REPORT = Path('C:/GrandTour/Saved/LidarAuthoringQA/AssetIntake')
PATTERNS = ('Flora_', 'Forest', 'Trees', 'Rock Master', 'cloud_paint', 'Lazy Cloud', 'Sample File')

def extract(z, root):
    root = root.resolve()
    for entry in z.infolist():
        target = (root / entry.filename).resolve()
        if not target.is_relative_to(root):
            raise ValueError(f'Archive path escapes staging: {entry.filename}')
        if not entry.is_dir() and (not target.exists() or target.stat().st_size != entry.file_size):
            z.extract(entry, root)

def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    rows = []
    for source in DOWNLOADS.glob('*.zip'):
        if not any(p in source.name for p in PATTERNS):
            continue
        with zipfile.ZipFile(source) as z:
            entries = z.infolist()
            row = {'source':str(source), 'files':len(entries), 'expanded_bytes':sum(e.file_size for e in entries),
                   'types':dict(collections.Counter(Path(e.filename).suffix.lower() for e in entries)),
                   'blends':[e.filename for e in entries if e.filename.endswith('.blend')],
                   'docs':[e.filename for e in entries if Path(e.filename).suffix.lower() in ('.txt','.md','.pdf')]}
            extract(z, STAGE)
            rows.append(row)
            print('STAGED', ascii(source.name), flush=True)
    for source in list(STAGE.rglob('*.zip')):
        with zipfile.ZipFile(source) as z:
            extract(z, source.parent / source.stem)
    (REPORT/'intake.json').write_text(json.dumps({'stage':str(STAGE),'archives':rows},indent=2),encoding='utf8')
    print('INTAKE_OK', len(rows), flush=True)

if __name__ == '__main__':
    main()
