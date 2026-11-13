"""Summarize actual engine evidence and assemble an unretouched driving preview."""
import json, math, re, sys
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parents[2]
out=root/'Art/Export/BenmoreGaea/WaterBalanced_20261011'
review=Path(sys.argv[1])
r=json.loads((review/'vehicle-review.json').read_text())
install=json.loads((out/'install-report.json').read_text())
reg=json.loads((out/'regressions.json').read_text(encoding='utf-8-sig'))
if isinstance(reg,dict):reg=[reg]
cases={}
for name in dict.fromkeys(s['case'] for s in r['samples']):
    rows=[s for s in r['samples'] if s['case']==name]
    cases[name]=dict(samples=len(rows),max_wheel_rate=max(s['splash_rate'] for s in rows),
        max_bow_rate=max(s['bow_rate'] for s in rows),peak_lid_m3=max(s['lid_m3'] for s in rows),
        peak_wheel_force_n=max(math.hypot(*f) for s in rows for f in s['wheel_water_forces_n']),
        min_speed_mps=min(s['speed_mps'] for s in rows),max_speed_mps=max(s['speed_mps'] for s in rows))
frames=[]
for p in sorted(review.glob('AlongRiver_*.png')):
    with Image.open(p) as im:frames.append(im.convert('RGB'))
if frames:frames[0].save(out/'Driving.gif',save_all=True,append_images=frames[1:],duration=500,loop=0)
cpu=re.findall(r'Test Completed\. Result=\{([^}]*)\}.*Path=\{(GrandTour\.Water\.[^}]*)\}',(out/'cpu-water-tests.log').read_text(errors='replace'))
summary=dict(installed=install['ok'],saved_and_reloaded=install['saved_and_reloaded'],
    preserved_state=install['before']==install['after'],cpu_tests=dict((n,s) for s,n in cpu),
    driving_review_ok=r['ok'],fixed_dt=r.get('fixed_dt'),car=r.get('car'),review=str(review),cases=cases,
    regression_results={x['name']:x['ok'] for x in reg},performance_measured=False,
    limitations=['Initial install returned access-violation status after writing its successful report and closing the log; fresh-process review was required.',
        'Early post-reload terrain frames were still streaming; later frames and fresh runtime review supersede those frames.',
        'The first runtime capture used the old fleet-selection/gear harness and was deliberately stopped; it is not accepted driving evidence.',
        'A subsequent continuously rendered check was stopped for slow progress alongside Ace Combat; final captures use the existing render gate and GPU pacing.',
        'Water remains a baked mean plus a bounded local disturbance field and cosmetic waves; no resolved spray breakup or erosion.'])
(out/'verification-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
