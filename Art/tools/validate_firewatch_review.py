"""Require valid runtime captures and saved-map checks before publishing review."""
import json,hashlib,sys
from pathlib import Path
ROOT=Path('C:/GrandTour');sys.path.insert(0,str(ROOT/'Art/tools'))
from measure_perceived_detail import run
QA=ROOT/'Saved/LidarAuthoringQA/FirewatchStyle';SHOTS=ROOT/'Saved/LidarAuthoringQA/RS7'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
verify=read(QA/'verify.json');assert verify['ok'] and verify['saved_reload']
assert verify['protected_packages']==185 and verify['independent_colour_haze_and_profile_edit_passed']
base=run('far-ridge-haze');report=dict(saved_map=verify,comparison='Same saved cameras, 1600x900, fixed exposure and graphics commands',presets={})
for preset in ['Subtle','Medium','Strong']:
 label='firewatch-'+preset.lower();capture=read(SHOTS/f'runtime-{label}.json')
 assert capture['exit_code']==0 and capture['render_validation_passed']
 assert capture['views']==base['views'] and capture['commands']==base['commands']
 log=Path(capture['log']).read_text(errors='replace');assert 'DISTANCE_STYLE preset='+preset in log
 measured=run(label);images={}
 for view in ['V01','V02','V03','G01']:
  file=SHOTS/f'{label}-{view}.png';assert file.stat().st_size>100000
  images[view]=dict(file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest())
 delta={v:round(m['GPUTime']['median']-base['measurements'][v]['GPUTime']['median'],4) for v,m in measured['measurements'].items()}
 report['presets'][preset]=dict(images=images,gpu_median_ms={v:round(m['GPUTime']['median'],4) for v,m in measured['measurements'].items()},gpu_delta_ms=delta,valley_03ms_target_met=all(delta[v]<=.3 for v in ['V01','V02','V03']))
repeat_path=SHOTS/'runtime-firewatch-strong-repeat.json'
if repeat_path.exists():
 measured=run('firewatch-strong-repeat')
 delta={v:round(m['GPUTime']['median']-base['measurements'][v]['GPUTime']['median'],4) for v,m in measured['measurements'].items()}
 report['strong_repeat']=dict(gpu_delta_ms=delta,valley_03ms_target_met=all(delta[v]<=.3 for v in ['V01','V02','V03']),note='First Strong timing exceeded the target; repeat did not. Keep both measurements rather than treating the budget as guaranteed.')
(QA/'review-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:dict(gpu_delta_ms=v['gpu_delta_ms'],valley_target_met=v['valley_03ms_target_met']) for k,v in report['presets'].items()},indent=2))
