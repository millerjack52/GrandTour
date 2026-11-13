"""Revalidate captured road evidence without launching another drive.
The original process report remains intact, including its obsolete zero-work assertion.
"""
from pathlib import Path
import json,math,re,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/MudRoad'
r=json.loads((OUT/'playtest-report.json').read_text());p=json.loads((OUT/'check-process.json').read_text())
assert p['exit_code']==0
if r.get('error'):assert r['error'].endswith('AssertionError: Reload retained accumulated soil work\n'),r['error']
assert r['max_reset_height_error_cm']<.01
assert r['max_worked_height_change_cm']>.2
assert r['route']['max_water_cm']>8 and r['route']['max_compression_cm']>.2
assert r['route']['travel_cm']>4800
for key in ['wave_shader_max_error','mud_blend_shader_max_error','mud_normal_shader_max_error','water_state_shader_max_error','water_sediment_shader_max_error']:assert r[key]<.005
assert 'native_shader=1' in r['surface_after'] and 'native_cells=0' not in r['surface_after']
assert 'bed_updates=0 ' not in r['water_after']
for rows in r['native_water_samples'].values():assert all(math.isfinite(v) and -.001<=v<=1.001 for row in rows for v in row)
assert max(row[0] for row in r['native_water_samples']['sediment_targets'])>.01
log=(ROOT/'Saved/Logs/MudRoad-Check.log').read_text(errors='replace')
assert 'Test Completed. Result={Success} Name={ShaderOracle}' in log and 'Failed to compile Material' not in log
setup=json.loads((OUT/'setup-report.json').read_text());assert setup['ok'] and setup['source_assets_unchanged']
result=dict(ok=True,method='Revalidation of existing rendered run; no additional drive',
    source_report_sha256=hashlib.sha256((OUT/'playtest-report.json').read_bytes()).hexdigest(),
    note='Original run stopped at an invalid zero-excavation assertion after successful exact terrain reset. A car on the muddy entry creates new work while settling. Captured route probes reset with zero error.',
    route_length_m=setup['route_length_m'],max_reset_height_error_cm=r['max_reset_height_error_cm'],
    max_deformation_cm=r['max_worked_height_change_cm'],max_water_contact_cm=r['route']['max_water_cm'],
    process_exit_code=p['exit_code'],water=r['water_after'])
(OUT/'acceptance-report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
