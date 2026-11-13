"""Keep the review candidate reproducible and restore it after the A/B captures."""
from pathlib import Path
import shutil,json,subprocess,hashlib
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail';VAR=QA/'Variants'
for layer in ['detail','ao-voxel']:
 for src in (VAR/layer).rglob('*.uasset'):
  dst=VAR/'final'/src.relative_to(VAR/layer);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
subprocess.run(['python',str(ROOT/'Art/tools/select_perceived_variant.py'),'final'],check=True,stdout=subprocess.DEVNULL)
cfg=ROOT/'Config/DefaultEngine.ini';backup=Path(json.loads((QA/'backup.json').read_text())['backup'])/'Config/DefaultEngine.ini'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(cfg,backup)
data=cfg.read_bytes()
if b'r.TSR.ThinGeometryDetection=' not in data:
 newline=b'\r\n' if b'\r\n' in data else b'\n'
 insertion=newline.join([b'[SystemSettings]',b'; Bounded perceived-detail review: retain thin foliage during TSR reconstruction.',b'; See FirstSection/Review/PerceivedDetail for measured cost; remove to restore default.',b'r.TSR.ThinGeometryDetection=1'])
 assert data.count(b'[SystemSettings]')==1
 cfg.write_bytes(data.replace(b'[SystemSettings]',insertion))
(QA/'persisted-config.json').write_text(json.dumps(dict(file=str(cfg),backup=str(backup),setting='r.TSR.ThinGeometryDetection=1',sha256=hashlib.sha256(cfg.read_bytes()).hexdigest()),indent=2))
(ROOT/'Saved/LidarAuthoringQA/RS7/job.py').write_text('import validate_perceived_detail as check;check.run()\nu.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()\n')
print('Final variant restored; queued independent reload validation.')
