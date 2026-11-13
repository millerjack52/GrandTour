"""Validate fresh vehicle evidence and assemble unaltered capture sequences for review."""
from pathlib import Path
import json,hashlib,re
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BenmoreGaea/WaterInteraction'
CAP=OUT/'RealismFinal'
report=json.loads((CAP/'vehicle-review.json').read_text())
install=json.loads((OUT/'install-report.json').read_text())
finish_path=OUT/'WakeFinish/vehicle-review.json'
finish=json.loads(finish_path.read_text()) if finish_path.exists() and finish_path.stat().st_mtime>(OUT/'install-report.json').stat().st_mtime else None
if finish:assert finish['ok']
assert report['ok'] and install['ok']
assert install['before']==install['after']
assert report['spray_mesh']=='/Engine/BasicShapes/Plane.Plane'
summary={'ok':True,'actual_vehicle':True,'spray_mesh':report['spray_mesh'],
    'performance_measured':False,'cases':{},'owner_visual_acceptance':False}
for name in ['Crawl','Crossing','Reverse','Dry','DriverCrossing','AlongRiver']:
    source=finish if finish and any(s['case']==name for s in finish['samples']) else report
    case_cap=OUT/'WakeFinish' if source is finish else CAP
    rows=[s for s in source['samples'] if s['case']==name];assert rows
    paths=[case_cap/('%s_%02d.png'%(name,i+1)) for i in range(len(rows))]
    assert all(p.exists() and p.stat().st_mtime>=(case_cap/'vehicle-review.json').stat().st_mtime-1200 for p in paths)
    assert max(r['live'] for r in rows)<=report['pool_per_kind']==120
    assert len({hashlib.sha256(p.read_bytes()).digest() for p in paths})>1
    peak=max(range(len(rows)),key=lambda i:rows[i]['splash_rate']+rows[i]['bow_rate'])
    summary['cases'][name]={'samples':len(rows),'max_wheel_droplets_per_s':max(r['splash_rate'] for r in rows),
        'max_bow_droplets_per_s':max(r['bow_rate'] for r in rows),'peak_live':max(r['live'] for r in rows),
        'peak_frame':str(paths[peak]),'peak_sample':rows[peak]}
    if name=='Dry':assert max(r['splash_rate']+r['bow_rate'] for r in rows)==0
    else:assert summary['cases'][name]['max_wheel_droplets_per_s']>0 and summary['cases'][name]['max_bow_droplets_per_s']>0
    if name in ['Crawl','Crossing','DriverCrossing','AlongRiver']:
        frames=[Image.open(p).convert('RGB').resize((960,600)) for p in paths]
        durations=[max(30,round((rows[i+1]['t']-rows[i]['t'])*1000)) for i in range(len(rows)-1)]+[500]
        frames[0].save(case_cap/(name+'.gif'),save_all=True,append_images=frames[1:],duration=durations,loop=0)
        # Capture cadence, including screenshot pauses, is not runtime frame rate.
summary['preview_note']='Sampled game states; GIF wrap is a preview loop. No runtime frame cadence or FPS conclusion.'
log=(ROOT/'Saved/Logs/BenmoreInteractionReview.log').read_text(errors='replace')
diag=[tuple(map(float,m)) for m in re.findall(r'GTWATER_VISUAL_WAKE sources=(\d+) changed=(\d+) modelPeak=([\d.]+)cm upload=\[(-?[\d.]+),(-?[\d.]+)\]cm',log)]
assert diag and max(d[0] for d in diag)>0 and max(d[1] for d in diag)>0 and max(d[4] for d in diag)>5
summary['wake_upload']={'peak_sources':int(max(d[0] for d in diag)), 'peak_changed_cells':int(max(d[1] for d in diag)),
    'maximum_added_height_cm':max(d[4] for d in diag),'minimum_added_height_cm':min(d[3] for d in diag),
    'note':'CPU render-upload diagnostics; cosmetic height, not physical wave height or GPU timing.'}
pair_report=finish or report;pair_cap=OUT/'WakeFinish' if finish else CAP
assert pair_report['paired_wakes']['same_physics_state']
off=np.asarray(Image.open(pair_cap/'Driver_WakesOff.png').convert('RGB'),dtype=np.float32)
on=np.asarray(Image.open(pair_cap/'Driver_WakesOn.png').convert('RGB'),dtype=np.float32)
summary['final_material_review']=str(pair_cap)
summary['paired_wakes']={**pair_report['paired_wakes'],'mean_absolute_pixel_change':float(np.abs(on-off).mean()),
    'note':'Same paused vehicle state; extra height and normals toggled through WakeDetailReady. Foam and spray remain enabled. Visual difference is not artistic acceptance.'}
assert summary['paired_wakes']['mean_absolute_pixel_change']>.01
(OUT/'verification-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
