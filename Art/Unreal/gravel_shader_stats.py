"""Deformable gravel DG1 item 6 (docs/DEFORMABLE_GRAVEL_PLAN.md): the shader instruction and sampler counts of M_GT_Gravel against the
study's M_GravelField (and the landscape copy and the stones' material), MRP's way (Art/Unreal/mud_pbr_stats.py): MaterialEditingLibrary
.get_statistics, the compiler's static counts at the editor's shader platform (a branch's or a loop's body counts once). Not timing.
Run with -RenderOffScreen (a NullRHI run compiles no HLSL): & Art/gravel_shader_stats.ps1. Writes Art/Export/DeformableGravel/shader-stats.json."""
import json
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/DeformableGravel'
D = '/Game/GrandTour/ArtTests/DeformableGravel/'
MATERIALS = [('study field', D + 'M_GravelField'), ('DG1 field', D + 'M_GT_Gravel'), ('landscape (DG1 arrays)', D + 'M_GravelLandscape'),
             ('loose stones', D + 'M_GT_GravelStone'), ('study stones', '/Game/GrandTour/ArtTests/GravelRoad/M_GR_Stone')]
report = dict(ok=False, rows=[])
try:
    mel = u.MaterialEditingLibrary
    for role, path in MATERIALS:
        mat = u.EditorAssetLibrary.load_asset(path)
        if mat is None:
            report['rows'].append(dict(role=role, material=path, missing=True))
            continue
        s = mel.get_statistics(mat)
        report['rows'].append(dict(role=role, material=path, pixel_instructions=s.num_pixel_shader_instructions,
                                   vertex_instructions=s.num_vertex_shader_instructions, samplers=s.num_samplers,
                                   pixel_texture_samples=s.num_pixel_texture_samples, vertex_texture_samples=s.num_vertex_texture_samples,
                                   interpolator_scalars=s.num_interpolator_scalars))
        u.log('GRAVEL_SHADER_STATS %s: %s' % (path, report['rows'][-1]))
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'shader-stats.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
