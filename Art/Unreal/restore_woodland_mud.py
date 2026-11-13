"""Restore ground and matching tread materials; preserve all other assets."""
import unreal as u
from pathlib import Path
import sys, json, time, shutil, hashlib, traceback
ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
import benmore_woodland_materials as mat
import benmore_woodland_detail as detail

report = dict(ok=False, driving_tested=False)
try:
    own = ROOT / 'Content/GrandTour/ArtTests/BenmoreWoodland'
    targets = [own / ('M_' + name + '.uasset') for name in ['Terrain', 'Detail', 'Tread']]
    protected = [p for p in own.rglob('*.uasset') if p not in targets]
    protected += list(own.rglob('*.umap'))
    protected += [ROOT / 'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap',
                  ROOT / 'Content/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain.uasset']
    protected += list((ROOT / 'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces').glob('M_NativeDomain*.uasset'))
    hashes = lambda: {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    before = hashes()
    backup = ROOT / 'Saved/BenmoreWoodlandBackups' / ('mud-restore-' + str(time.time_ns()))
    backup.mkdir(parents=True)
    for p in targets: shutil.copy2(p, backup / p.name)
    for p in mat.OUT.glob('*.png'): shutil.copy2(p, backup / p.name)
    report['backup'] = str(backup)
    report['materials'] = detail.install()
    import woodland_mud_clods
    report['native_clods'] = woodland_mud_clods.install()
    assert hashes() == before, 'An unrelated asset changed'
    report.update(ok=True, protected_hashes=before,
                  roughness_adapter=.78, specular_adapter=.12,
                  physics_changed=False, water_changed=False)
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
(mat.OUT / 'mudrestore.json').write_text(json.dumps(report, indent=2))
u.SystemLibrary.quit_editor()
