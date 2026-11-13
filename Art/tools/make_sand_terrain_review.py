"""Package unmodified native Unreal sand captures and measured comparison data."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'Art/Export/SandTerrain'
r=json.loads((out/'review-report.json').read_text())
for mode in ['setup','tests','review']:
    s=json.loads((out/(mode+'-run-status.json')).read_text(encoding='utf-8-sig'))
    assert s['exit_code']==0 and s['fresh'] and s['report_ok'],mode
assert r['ok']
for name in r['images']:assert (out/name).stat().st_size>40000
loose,packed=r['cases']
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sand terrain · loose and compacted</title><style>
*{box-sizing:border-box}body{margin:0;background:#22241c;color:#ede7d6;font:16px/1.6 system-ui}main{max-width:1280px;margin:auto;padding:32px 24px}h1{font-size:36px;line-height:1.15;margin:10px 0 22px}p{max-width:900px;color:#d2ccbd}img{display:block;width:100%;border-radius:8px}nav{display:flex;gap:12px;flex-wrap:wrap;margin:25px 0}button{background:#383b2e;color:inherit;border:1px solid #757961;border-radius:5px;padding:11px 18px;cursor:pointer}button.active{background:#dfc89f;color:#25271f}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0}figcaption{padding:10px 0;color:#d0c5af}table{border-collapse:collapse;width:100%;margin:20px 0 30px}td,th{padding:12px;border-bottom:1px solid #535546;text-align:left}small{color:#b5bba2}a{color:#efcf98}@media(max-width:850px){.pair{grid-template-columns:1fr}h1{font-size:29px}}
</style><main><small>GRAND TOUR / SAND TERRAIN STUDY</small><h1>Loose sand that yields.<br>Compacted sand that carries.</h1>
<p>A separate drivable test section using the supplied sand references: pale granular surfaces, rounded heaps, wheel troughs and displaced shoulders. The loose and compacted lanes share the existing finite soil system, with a distinct granular grip and resistance response.</p>
<img src="overview.png" alt="The sand test section with its grassy margins">
<table><tr><th>Same car, same inputs</th><th>Loose sand</th><th>Compacted sand</th></tr><tr><td>Deformable layer</td><td>38 cm</td><td>12 cm</td></tr><tr><td>Measured loaded settlement</td><td>LOOSE cm</td><td>PACKED cm</td></tr><tr><td>Half throttle / low range pass*</td><td>LTRAVEL m in LTIME s</td><td>PTRAVEL m in PTIME s</td></tr></table><small>*Each pass ends at six seconds or the end of the test lane, whichever comes first.</small>
<nav><button data-view="settled" class="active">Loaded wheels</button><button data-view="driving">Driving and dust</button><button data-view="tracks">Tyre tracks</button></nav>
<div class="pair"><figure><img id="loose" src="loose_settled.png" alt="Loose sand"><figcaption>Loose: deeper settlement, softer shoulders and more rolling work.</figcaption></figure><figure><img id="compacted" src="compacted_settled.png" alt="Compacted sand"><figcaption>Compacted: shallower tracks and firmer support.</figcaption></figure></div>
<p>Open <strong>/Game/GrandTour/ArtTests/SandTerrain/L_SandTerrain</strong>. You start in the loose lane, facing along it. The firmer lane is alongside at positive world Y (to the right when facing positive X). Both lanes meet through a gradual transition.</p>
<p>14 native soil/effect checks and eight live checks passed. These images are native Unreal captures. Performance data comes from short local editor passes capped at 60 fps; it does not establish whole-map performance. Sand redistribution is local to working tyres; this prototype does not simulate dunes or continuing avalanches after a vehicle leaves.</p>
<small><a href="review-report.json">Live measurements</a> · <a href="review-run-status.json">Render run status</a> · <a href="tests-run-status.json">Native test status</a></small>
</main><script>document.querySelectorAll('button').forEach(b=>b.onclick=()=>{document.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));['loose','compacted'].forEach(s=>document.getElementById(s).src=s+'_'+b.dataset.view+'.png')});</script></html>'''
for key,value in [('LOOSE',r['settlement_cm']['loose']),('PACKED',r['settlement_cm']['compacted']),('LTRAVEL',loose['travel_cm']/100),('PTRAVEL',packed['travel_cm']/100),('LTIME',loose['drive_seconds']),('PTIME',packed['drive_seconds'])]:html=html.replace(key,f'{value:.1f}')
(out/'sand-terrain.html').write_text(html,encoding='utf-8')
print(out/'sand-terrain.html')
