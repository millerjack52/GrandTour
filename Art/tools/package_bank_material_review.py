"""Publish raw game captures and repeated VP2 measurements beside prior reviews."""
from pathlib import Path
import hashlib,json,shutil,statistics,sys
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'Saved/LidarAuthoringQA/VP2Materials';CAP=ROOT/'Saved/LidarAuthoringQA/RS7'
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/MaterialPolish'
OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
if not (QA/'vp2-b1-summary.json').exists():
    record=dict(status='IMPLEMENTED; FINAL VISUAL AND PERFORMANCE REVIEW PENDING',
                installation=read(QA/'final-install.json'),validation=read(QA/'file-validation.json'),
                reason='The owner chose to continue visual work while Skate was using the GPU. The final capture was aborted after only a few frames per minute; no candidate screenshots or comparable timings were produced.',
                owner_visual_acceptance='PENDING',performance_acceptance='PENDING')
    (OUT/'evidence.json').write_text(json.dumps(record,indent=2))
    (OUT/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Riverbank material pass: validation pending</title><style>body{max-width:900px;margin:50px auto;padding:24px;background:#14201a;color:#e9eee5;font:18px/1.6 system-ui}a{color:#b4d2a4}</style><h1>Riverbank materials and plant shading</h1><p>The bounded material pass is saved in Grand Tour. It consolidates the bank detail shader, preserves rock fissures, reduces compounded ground darkening and varies leaf roughness and transmission.</p><p><strong>Final visual and performance validation remain pending.</strong> Skate was sharing the GPU, and the owner chose to defer performance testing. The final game capture became too slow and was stopped. There are no final candidate screenshots to present as a verified result.</p><p>Five material packages changed. Installation checks preserved planting, and file hashes confirm the map, meshes, textures, collision and renderer configuration are unchanged. Shader compilation statistics were recorded.</p><p><a href="evidence.json">Installation and integrity evidence</a></p></html>''',encoding='utf-8')
    print(OUT/'index.html');sys.exit(0)
complete=all((QA/('vp2-'+side+str(i)+'-summary.json')).exists() for side in ['a','b'] for i in range(1,4))
runs={side+str(i):read(QA/('vp2-'+side+str(i)+'-summary.json')) for side in ['a','b'] for i in range(1,4)} if complete else {'a1':read(QA/'vp2-before-summary.json'),'b1':read(QA/'vp2-b1-summary.json')}
valid=complete and all(r.get('validity',{}).get('performance_valid') is True for r in runs.values())
views=list(runs['a1']['metrics'])
metrics={}
for v in views:
    if valid:
        a=[runs['a'+str(i)]['metrics'][v]['GPUTime']['median'] for i in range(1,4)]
        b=[runs['b'+str(i)]['metrics'][v]['GPUTime']['median'] for i in range(1,4)]
        delta=[y-x for x,y in zip(a,b)]
        metrics[v]=dict(baseline_gpu_ms=statistics.median(a),candidate_gpu_ms=statistics.median(b),paired_gpu_deltas_ms=delta,median_paired_delta_ms=statistics.median(delta),
                    baseline_frame_p95_ms=[runs['a'+str(i)]['metrics'][v]['FrameTime']['p95'] for i in range(1,4)],
                    candidate_frame_p95_ms=[runs['b'+str(i)]['metrics'][v]['FrameTime']['p95'] for i in range(1,4)])
    for side,key in [('before','a1'),('after','b1')]:shutil.copy2(CAP/(runs[key]['label']+'-'+v+'.png'),OUT/(side+'-'+v+'.png'))
for run in runs.values():
    assert run['capture']['views']==runs['a1']['capture']['views']
    assert run['capture']['commands']==runs['a1']['capture']['commands']
    assert run['capture']['extra_commands']==runs['a1']['capture']['extra_commands']
    telemetry=QA/(run['label']+'-telemetry.csv')
    if telemetry.exists():shutil.copy2(telemetry,OUT/telemetry.name)
record=dict(scope='Five bank-owned material packages; geometry, planting, collision, lighting and renderer settings preserved.',
            installation=read(QA/'final-install.json'),validation=read(QA/'file-validation.json'),
            runs=runs,metrics=metrics,owner_visual_acceptance='PENDING',
            limitations='Four stationary game views, three paired runs; laptop thermal/clock variation remains. Motion media are rendered samples, not frame-pacing evidence. No full-route 60/120 fps claim.',
            performance_status='MEASURED' if valid else 'PENDING: owner chose to continue visual work while Skate shares the GPU; candidate timings invalid for comparison.',
            proposed_incremental_gate_passed=all(m['median_paired_delta_ms']<=1 for m in metrics.values()) if valid else None,
            source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'Art/Unreal/lidar_bank_material_polish.py',ROOT/'Art/tools/bank_material_review.py']})
(OUT/'evidence.json').write_text(json.dumps(record,indent=2))
rows=''.join(f'<tr><th>{v}</th><td>{m["baseline_gpu_ms"]:.2f}</td><td>{m["candidate_gpu_ms"]:.2f}</td><td>{m["median_paired_delta_ms"]:+.2f}</td></tr>' for v,m in metrics.items())
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Riverbank materials and plant shading</title>
<style>body{margin:0;background:#14201a;color:#e9eee5;font:16px/1.55 system-ui}main{max-width:1600px;margin:auto;padding:28px}h1{font-size:30px}p{max-width:1000px}button{padding:10px 16px;margin:4px;border:1px solid #758c70;background:#263f2e;color:white;border-radius:6px;cursor:pointer}button[aria-pressed=true]{background:#567344}nav{margin:20px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}img,video{width:100%}h2{font-size:19px}table{border-collapse:collapse}th,td{text-align:left;padding:9px 22px;border-bottom:1px solid #465747}a{color:#b4d2a4}.note{color:#c7cfc4}@media(max-width:850px){.pair{grid-template-columns:1fr}}</style>
<main><p>Grand Tour · L_LidarStudy · 8 November 2026</p><h1>Riverbank materials and plant shading</h1>
<p>The bank now uses one surface-detail shader, preserving the rock fissures while reducing compounded contact darkening. Existing leaf colours drive differences in roughness and transmission. Plant placement, meshes, shadows, collision and exposure are unchanged.</p>
<nav><button data-view="D01" onclick="choose('D01')">Fern crowns</button><button data-view="G01" onclick="choose('G01')">Ground close-up</button><button data-view="B01" onclick="choose('B01')">Riverbank</button><button data-view="B04" onclick="choose('B04')">Across the river</button></nav>
<div class="pair"><section><h2>Before</h2><a id="beforeLink"><img id="before" alt="Actual game before material changes"></a></section><section><h2>After</h2><a id="afterLink"><img id="after" alt="Actual game after material changes"></a></section></div>
<p class="note">Unretouched standalone game captures at 1600 × 900, TSR 75%. Click an image for full resolution. Small differences in wind and temporal history remain between runs.</p>
<h2>Measured GPU time</h2><table><tr><th>View</th><th>Before median, ms</th><th>After median, ms</th><th>Median paired change, ms</th></tr>ROWS</table>
<p>Three paired runs with alternating order. Camera-settling and screenshot windows are excluded. Lower is faster. Laptop clock and temperature variation limits claims about small gains; these are local stationary measurements, not proof of a full-route frame-rate target.</p>
<h2>Moving camera inspection</h2><div class="pair"><section><h2>Before</h2><video controls preload="metadata" src="before-motion.mp4"></video></section><section><h2>After</h2><video controls preload="metadata" src="after-motion.mp4"></video></section></div>
<p>Six seconds of the same outward camera move, sampled at 12 fps for visual comparison. These clips do not measure live performance.</p>
<p><a href="evidence.json">Full measurements, hashes and limitations</a> · <a href="../FernFloor/index.html">Earlier forest-floor pass</a></p></main>
<script>function choose(v){for(const s of ['before','after']){const p=s+'-'+v+'.png';document.getElementById(s).src=p;document.getElementById(s+'Link').href=p}for(const b of document.querySelectorAll('[data-view]'))b.setAttribute('aria-pressed',String(b.dataset.view===v))}choose('D01')</script></html>'''
page=page.replace('ROWS',rows)
if not valid:
    start=page.index('<h2>Measured GPU time</h2>');end=page.index('<h2>Moving camera inspection</h2>')
    page=page[:start]+'<h2>Performance validation pending</h2><p>Skate was sharing the GPU during the candidate capture. The owner chose to continue visual work and leave performance testing pending. These captures establish appearance and successful material rendering; they do not establish a speed improvement. The repeatable benchmark and raw diagnostic records are retained.</p>'+page[end:]
if not all((OUT/(s+'-motion.mp4')).exists() for s in ['before','after']):
    start=page.index('<h2>Moving camera inspection</h2>');end=page.index('<p><a href="evidence.json">')
    page=page[:start]+'<p>Moving-camera comparison is pending; these are matched still views.</p>'+page[end:]
(OUT/'index.html').write_text(page,encoding='utf-8')
print(json.dumps(metrics,indent=2));print(OUT/'index.html')
