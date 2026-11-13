"""Apply only map-local ground foliage shadow settings; leave mud and sources intact."""
import unreal as u
import json,traceback,hashlib,sys
from pathlib import Path
sys.path.insert(0,'C:/GrandTour/Art/Unreal')
from flora_drive_ground_shadows import apply
O=Path('C:/GrandTour/Art/Export/FloraDrive');r=dict(ok=False)
try:
    audit=json.loads((O/'audit-report.json').read_text())
    protected=json.loads((O/'protected-before.json').read_text())
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive')
    r.update(apply())
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    for p,h in {**audit['package_hashes'],**protected}.items():
        if p.endswith('FloraDrive/L_FloraDrive.umap') or p.endswith('FloraDrive\\L_FloraDrive.umap'):continue
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,'Unexpected asset change: '+p
    r['ok']=True
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'shadows-report.json').write_text(json.dumps(r,indent=2))
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
u.SystemLibrary.quit_editor()
