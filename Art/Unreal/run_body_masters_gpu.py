"""MudRunner MRP: setup_m1_body.py, then setup_m1_masters.py, in one editor run with a real RHI.

Art/setup_m1_body.bat and Art/setup_m1_masters.bat run the commandlet under -NullRHI, which compiles no HLSL ("body_test.bat gpu
reports Failed to compile if it is wrong"). This runs the same two scripts in the editor started with -RenderOffScreen, so the car
materials' custom HLSL is compiled for real, then reads each material's static stats (a synchronous compile: 0 pixel instructions
means it did not compile). Writes Art/Export/MudVariants/body-masters-report.json and quits.

  UnrealEditor.exe GrandTour.uproject -RenderOffScreen -dx12 -Unattended -NoSplash -NoSound -GTNoLoad
      -ExecutePythonScript="Art/Unreal/run_body_masters_gpu.py" -abslog="Saved/Logs/body_masters_gpu.log"
"""
import json
import runpy
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/MudVariants'
OUT.mkdir(parents=True, exist_ok=True)
report = dict(ok=False, ran=[], stats=[])
try:
    for script in ('setup_m1_body.py', 'setup_m1_masters.py'):
        try:
            runpy.run_path(str(ROOT / 'Art/Unreal' / script), run_name='__main__')
        except SystemExit as stop:
            if stop.code not in (None, 0):
                raise RuntimeError('%s stopped: %s' % (script, stop.code))
        report['ran'].append(script)
    mel = u.MaterialEditingLibrary
    for name in ('M_GT_Vehicle', 'M_GT_Tyre', 'M_GT_Glass'):
        mat = u.EditorAssetLibrary.load_asset('/Game/GrandTour/Materials/' + name)
        s = mel.get_statistics(mat)
        report['stats'].append(dict(material=name, pixel_instructions=s.num_pixel_shader_instructions, samplers=s.num_samplers))
    bad = [r['material'] for r in report['stats'] if r['pixel_instructions'] <= 0]
    if bad:
        raise RuntimeError('no pixel shader (did not compile): %s' % bad)
    report['ok'] = True
except BaseException:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'body-masters-report.json').write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
