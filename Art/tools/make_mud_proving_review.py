"""Package real Unreal captures and timing evidence for the single wet-mud prototype."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/MudProvingGround'
r=json.loads((OUT/'review-report.json').read_text());assert r['ok']
run_status=json.loads((OUT/'review-run-status.json').read_text(encoding='utf-8-sig'))
assert run_status['exit_code']==0 and run_status['fresh'] and run_status['report_ok'],run_status
inspection=json.loads((OUT/'inspection-report.json').read_text()) if (OUT/'inspection-report.json').exists() else {}
ref=Path('C:/Users/mille/AppData/Local/Temp/codex-clipboard-939a47c5-65a3-4df3-ab9e-15c5c8134ec1.png')
if ref.exists():shutil.copy2(ref,OUT/'mudrunner-reference.png')
rows=[]
for run in r['driving_performance']:
    m=run['metrics'];rows.append('<tr><td>'+('Medium' if run['quality']==1 else 'Low')+'</td>'+''.join('<td>%.2f / %.2f ms</td>'%(m[k]['mean_ms'],m[k]['p99_ms']) for k in ['FrameTime','GameThreadTime','GPUTime'])+'</tr>')
shots=[('05a_working_tyres','Loaded wheels and mud throw'),('06_driven_tracks','The surface after the first pass'),('02_pool_edge','Connected water and broken shore'),('07_crossing','Crossing existing ruts'),('03_old_ruts','Untouched ground'),('04_overview','The whole test patch')]
gallery=''.join('<figure><a href="'+name+'.png" target="_blank"><img loading="lazy" src="'+name+'.png" alt="'+title+'"></a><figcaption>'+title+'</figcaption></figure>' for name,title in shots)
data=json.dumps(r['motion_frames'])
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mud proving ground</title>
<style>*{box-sizing:border-box}body{margin:0;background:#141917;color:#e5e5d9;font:16px/1.55 system-ui,sans-serif}main{max-width:1240px;margin:auto;padding:48px 28px 90px}h1{font-size:clamp(32px,5vw,64px);letter-spacing:-.045em;line-height:1.1;margin:12px 0 22px}h2{font-size:25px;margin:48px 0 15px}p{max-width:850px;color:#b9c0b5}.eyebrow{color:#b4bf89;font-size:12px;text-transform:uppercase;letter-spacing:.18em}code{color:#d2dcb0}img{display:block;width:100%;height:auto;background:#0c100e}.hero{border:1px solid #394338}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}figcaption{padding:9px 0 18px;font-size:14px;color:#b9c0b5}button,select{font:inherit;background:#29352d;color:#e5e5d9;border:1px solid #526249;border-radius:4px;padding:6px 14px;cursor:pointer}.controls{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:12px 0}input{flex:1;accent-color:#b4bf89;min-width:130px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #364137}small{color:#a4af9d}a{color:#d2dcb0}.note{border-left:3px solid #849764;padding-left:18px;margin:22px 0}@media(max-width:700px){.grid{grid-template-columns:1fr}main{padding:28px 16px}td,th{padding:7px;font-size:12px}}</style>
<main><div class="eyebrow">Grand Tour / 13 October 2026 / rendered prototype</div><h1>Saturated mud.<br>Shape, weight, displaced soil.</h1>
<p>One new proving ground, built against your MudRunner references. The ground has a unique height field, broken clods, wandering old ruts and a connected pool. Wheel support and the visible surface use the same ground data.</p>
<img class="hero" src="01_shape_wide.png" alt="New muddy proving ground">
<div class="note"><strong>Drive this level:</strong> <code>/Game/GrandTour/ArtTests/MudProvingGround/L_MudProvingGround</code><br><small>Open it in Unreal and press Play. Test the old ruts, untouched shoulders and pool in both directions. The previous MudVariants pass remains an unapproved comparison.</small></div>
<h2>Watch the contact</h2><img id="motion" src="motion_000.png" alt="Actual Unreal driving sequence"><div class="controls"><button id="play">Play</button><input id="seek" type="range" min="0" max="1" step="0.001" value="0" aria-label="Sequence position"><select id="speed" aria-label="Playback speed"><option value="1">1× time</option><option value=".5">½ speed</option></select><span id="time">0.00 s</span></div>
<small>Sampled Unreal frames, played at their recorded simulation times. This sequence is for contact and shape review; it is not a frame-rate recording.</small>
<h2>Inspect the surfaces</h2><div class="grid">__GALLERY__</div>
<h2>The visual target</h2><figure><img loading="lazy" src="mudrunner-reference.png" alt="User supplied MudRunner reference"><figcaption>Your MudRunner reference: uneven displaced banks, crushed beds, coated tyres and water between the clods.</figcaption></figure>
<h2>What has been checked</h2><p>Build succeeded and all seven native soil tests passed. Rendered driving checks cover loaded settling, rut crossing, wheel slip, a momentum entry, an approach accelerated on firm ground, tyre coating and bounded mud emission. The soil's excavated and deposited volumes balance. Shader compilation is checked before captures.</p>
<table><thead><tr><th>Driving quality</th><th>Frame mean / p99</th><th>Game thread mean / p99</th><th>GPU mean / p99</th></tr></thead><tbody>__ROWS__</tbody></table>
<p><small>Eight-second driving captures at 1440 × 900 on this machine, with real deformation and effects. PIE ran near a 60 Hz cadence. These results cover this small scene, not full Benmore streaming or a minimum-spec promise. <a href="review-report.json">Raw capture and driving report</a>.</small></p>
<h2>Scope of this pass</h2><p>This is one saturated-soil prototype. The pool uses actual water shading and follows terrain contours; its disturbance is local shading, not a full propagating wake simulation. Dry clay, deep bog and shallow grass need their own approved character before rebuilding the route. Driving feel still needs your judgement.</p>
</main><script>const frames=__DATA__;const image=document.getElementById('motion'),play=document.getElementById('play'),seek=document.getElementById('seek'),speed=document.getElementById('speed'),label=document.getElementById('time');frames.forEach(f=>{const i=new Image();i.src=f.file});const first=frames[0].time,last=frames.at(-1).time-first;let t=0,running=false,previous=0,index=-1;function show(){const n=Math.max(0,frames.findLastIndex(f=>f.time-first<=t));if(n!==index){image.src=frames[n].file;index=n}seek.value=last?t/last:0;label.textContent=t.toFixed(2)+' s'}play.onclick=()=>{running=!running;if(t>=last)t=0;play.textContent=running?'Pause':'Play'};seek.oninput=()=>{t=Number(seek.value)*last;show()};function tick(now){if(running&&previous){t+=(now-previous)/1000*Number(speed.value);if(t>=last){t=last;running=false;play.textContent='Replay'}show()}previous=now;requestAnimationFrame(tick)}show();requestAnimationFrame(tick);</script></html>'''
page=page.replace('__GALLERY__',gallery).replace('__ROWS__',''.join(rows)).replace('__DATA__',data)
if (OUT/'integration-checks.json').exists():
    evidence=json.loads((OUT/'integration-checks.json').read_text());assert evidence['ok']
    page=page.replace('<h2>What has been checked</h2>', '<h2>What has been checked</h2><p>Mean loaded penetration in the crawl: <strong>%.1f cm</strong>. Crossing travel: <strong>%.1f m</strong>, with <strong>%.0f%%</strong> wheel contact across the crawl and crossing samples. <a href="integration-checks.json">Driving checks and conditions</a>.</p>'%(evidence['mean_loaded_penetration_cm'],evidence['crossing_travel_cm']/100,evidence['wheel_contact_fraction_crawl_and_crossing']*100))
if not r.get('driving_performance'):
    a=page.index('<table>');b=page.index('</table>',a)+len('</table>');page=page[:a]+page[b:]
    page=page.replace('Eight-second driving captures at 1440 × 900 on this machine, with real deformation and effects. PIE ran near a 60 Hz cadence. These results cover this small scene, not full Benmore streaming or a minimum-spec promise.', 'A clean GPU timing run is still needed. The final capture pass prioritised visual and contact verification while another game was running.')
if inspection.get('performance_isolated') is False or run_status.get('other_game_observed'):
    page=page.replace('<table><thead>', '<p class="note"><strong>Contended timing capture.</strong> Another game was running during this pass. These figures are diagnostic only; a clean performance comparison remains outstanding.</p><table><thead>')
    page=page.replace('PIE ran near a 60 Hz cadence.','The GPU was shared with another running game.')
(OUT/'mud-proving-ground.html').write_text(page,encoding='utf-8')
print(OUT/'mud-proving-ground.html')
