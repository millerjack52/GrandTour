"""MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1, docs/MUD_VARIANTS.md "Carried mud"): the carried mud's assets.

Imports the splat atlas (Art/Blender/build_mud_splats.py -> Art/Export/MudSplats), adds MudCover and GrassMud to
MPC_TrackPaint, builds MF_MudCover and M_GT_MudSplatDecal, wires MF_MudCover into M_GT_Environment, M_GT_Landscape and the
strips' landscapes (M_LiveLandscape, M_VariantsLandscape), and the muddy grass base into M_TS_Grass and M_GT_FoliageCard
(Art/Unreal/mud_cover.py). Repeatable. Run with & Art/setup_mud_carry.ps1 (close the editor and games first; after
& Art/import_mud_variants.ps1, whose bog arrays it reads). Then & Art/setup_live_mud_drive.ps1 and & Art/setup_mud_variants.ps1
keep the cover on the landscapes they rebuild (live_mud_style.py calls mud_cover.wire_mud_cover).
Writes Art/Export/MudSplats/setup-report.json.
"""
import json, sys, traceback
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/MudSplats'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
report = {'ok': False}
try:
    import mud_cover
    report.update(mud_cover.setup())
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'setup-report.json').write_text(json.dumps(report, indent=2, default=str))
    u.SystemLibrary.quit_editor()
