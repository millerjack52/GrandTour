"""Benmore integration B1c (docs/BENMORE_INTEGRATION_PLAN.md): the setup, one editor run (Art/benmore_b1c.ps1).
- PM_Benmore_GravelFirm / PM_Benmore_GravelLoose: SprayTintA / SprayTintB / DustTint from benmore_gt_ground.TINTS (the stone faces x1.15
  and x0.85, the road's matrix x1.35), saved; the rows go to Art/Export/BenmoreB1c/surfaces.json.
- Then Art/Unreal/setup_wheel_spray.py as ever (it quits the editor): M_GT_SprayDust's floor display-referred under daylight exposures
  (MPC_GT_Spray DustFloorDisplay) and NS_GT_WheelSpray's User.GritSizeMin / GritSizeSpan."""
import json
import runpy
import sys
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
import benmore_gt_ground as g  # noqa: E402

OUT = ROOT / 'Art/Export/BenmoreB1c'
OUT.mkdir(parents=True, exist_ok=True)
rows = {}
for name, (a, b, d) in g.TINTS.items():
    pm = u.EditorAssetLibrary.load_asset(g.SURFACES + '/' + name)
    assert pm and pm.get_editor_property('gravel_spray'), name
    for prop, c in (('spray_tint_a', a), ('spray_tint_b', b), ('dust_tint', d)):
        pm.set_editor_property(prop, u.LinearColor(*c, 1.0))
    rows[name] = dict(saved=bool(u.EditorAssetLibrary.save_loaded_asset(pm, False)), spray_tint_a=a, spray_tint_b=b, dust_tint=d)
(OUT / 'surfaces.json').write_text(json.dumps(rows, indent=2))
runpy.run_path(str(ROOT / 'Art/Unreal/setup_wheel_spray.py'), run_name='__main__')
