"""Package successful native and rendered evidence without inventing animation frames."""
import json,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/MudWaterShared'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
r=read(OUT/'review-report.json');status=read(OUT/'review-run-status.json')
assert r['ok'] and all(r['checks'].values()) and status['fresh'] and status['report_ok'] and status['exit_code']==0
native=[read(ROOT/'Saved/Automation'/p/'index.json') for p in ['LandscapeMud','MudWaterRegression']]
assert all(n['failed']==0 and n['succeeded']>0 and n['notRun']==0 for n in native)
for shot in r['images']:assert (OUT/shot['name']).stat().st_size>40000
motion=[s for s in r['images'] if s['name'].startswith('motion_')];assert len(motion)==6
water=r['rendered_end']['water'];pre=r['rendered_start']['water']
samples=[r['before']]+r['samples']+[r['after']]+r['rendered_samples']
error=max(abs(s['water']['delta_m3']) for s in samples)
deficit=water['deficit_s']-pre['deficit_s']
report=dict(cells=int(water['cells']),water_step_mean_ms=water['step_mean_ms'],water_step_peak_ms=water['step_peak_ms'],
    bed_update_peak_ms=water['bed_peak_ms'],water_volume_error_m3=error,rendered_phase_deficit_s=deficit,total_review_deficit_s=water['deficit_s'],
    native_tests=sum(n['succeeded'] for n in native),integration_checks=r['checks'])
(OUT/'shared-validation.json').write_text(json.dumps(report,indent=2))
checks=''.join('<tr><td>'+html.escape(k.replace('_',' ').capitalize())+'</td><td>Pass</td></tr>' for k in r['checks'])
rows=json.dumps([dict(name=s['name'],time=s['time']-r['before']['time']) for s in motion])
doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shared water over deformable mud</title><style>
*{box-sizing:border-box}body{margin:0;background:#151918;color:#e7eae3;font:17px/1.6 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:44px 24px}h1{font-size:clamp(30px,5vw,50px);line-height:1.1;max-width:800px;margin:10px 0 24px}h2{font-size:26px;margin:44px 0 12px}.eyebrow{font-size:13px;color:#b5c99b;letter-spacing:.15em;text-transform:uppercase}p{max-width:870px;color:#c4cec3}img{display:block;width:100%;border-radius:8px}figure{margin:24px 0}figcaption{color:#b9c4b7;font-size:14px;padding:9px 0}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:28px 0}.card{border:1px solid #42513f;border-radius:8px;padding:16px}.card strong{display:block;font-size:30px;color:#d5e6b5}.card span{font-size:14px;color:#bdcabb}button{background:#d5e6b5;border:0;color:#1b2419;padding:10px 20px;border-radius:5px;cursor:pointer;font:inherit}.controls{display:flex;gap:20px;align-items:center;flex-wrap:wrap}input{flex:1;accent-color:#c5d69e}table{border-collapse:collapse;width:100%;max-width:800px}td{padding:7px 12px;border-bottom:1px solid #354031}td:last-child{color:#c4e6a7}a{color:#c4e6a7}code{color:#e8dab9}details{margin:24px 0}summary{cursor:pointer}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:700px){.pair{grid-template-columns:1fr}}
</style><main><div class="eyebrow">Grand Tour · Working prototype · 13 October 2026</div>
<h1>Shared water over deformable mud</h1>
<p>The car pushes water through the pond while its tyres change the bed. Connected water can enter fresh ruts; raised mud interrupts it. This uses the existing river-water framework with a closed, deforming basin.</p>
<p>Play <code>/Game/GrandTour/ArtTests/MudWater/L_MudWater</code>. The accepted soil settings are retained; this is a separate test map.</p>
<h2>Watch the water beside the tyres</h2>
<figure><img id="motion" src="motion_00.png" alt="Actual Unreal capture of the car crossing the muddy pond"><figcaption id="caption"></figcaption></figure>
<div class="controls"><button id="play">Play sequence</button><input id="frame" aria-label="Capture frame" type="range" min="0" max="5" value="0" step="1"></div>
<p>Six actual captures, about 0.2 seconds apart in simulation. Playback loops the captured frames; it adds no intermediate frames. The broader views below show the altered shoreline and water left in the wheel paths.</p>
<div class="pair"><figure><img src="water_00_before.png" alt="Pond before crossing"><figcaption>Before the crossing</figcaption></figure><figure><img src="water_03_leave.png" alt="Pond and tyre tracks after crossing"><figcaption>After the car passes</figcaption></figure></div>
<h2>Measured in this test</h2><div class="stats">
<div class="card"><strong>__CELLS__</strong><span>fluid cells · 25 cm spacing</span></div>
<div class="card"><strong>__MEAN__ ms</strong><span>mean water-step CPU cost</span></div>
<div class="card"><strong>__BED__ ms</strong><span>peak changed-bed update</span></div>
<div class="card"><strong>__TESTS__ passed</strong><span>native mud and water regression tests</span></div></div>
<p>Water-step peak: __PEAK__ ms. Maximum water-volume error: __ERROR__ m³. Dropped simulation time during the final rendered segment: __DEFICIT__ seconds; accumulated over the entire review, including render transitions: __TOTALDEFICIT__ seconds. These are CPU simulation measurements on this machine, not a whole-game FPS guarantee. Captures pause simulation.</p>
<details><summary>Vehicle and water checks</summary><table>__CHECKS__</table></details>
<h2>How this scales</h2>
<p>One nearby pond simulates by default, with a configurable cap of four. Each grid is limited to 128 × 128 cells. Ground changes are read from changed blocks at up to 10 Hz; the water texture updates at up to 30 Hz. Sleeping ponds retain their water.</p>
<p>This is suitable for local shallow ponds, bog margins and connected ruts. Whole-map deployment still needs distant water display, a memory/streaming budget for visited ponds, and explicit exchange where pond and river domains meet. The 25 cm fluid grid also limits the smallest channels it can represent. Splash particles remain a separate layer; this pass does not implement erosion, groundwater or a full 3D fluid.</p>
<p><a href="review-report.json">Vehicle and field measurements</a> · <a href="shared-validation.json">Validation summary</a></p>
</main><script>
const frames=__FRAMES__,slider=document.querySelector('#frame'),pic=document.querySelector('#motion'),caption=document.querySelector('#caption'),button=document.querySelector('#play');let timer=null;
frames.forEach(f=>{const im=new Image();im.src=f.name});
function show(i){slider.value=i;pic.src=frames[i].name;caption.textContent=`Capture ${i+1} of ${frames.length} · ${frames[i].time.toFixed(2)} s after the start of the crossing`}
slider.oninput=()=>show(+slider.value);button.onclick=()=>{if(timer){clearTimeout(timer);timer=null;button.textContent='Play sequence'}else{button.textContent='Pause';function advance(){const i=+slider.value,j=(i+1)%frames.length;show(j);timer=setTimeout(advance,j===frames.length-1?900:Math.max(100,(frames[Math.min(j+1,frames.length-1)].time-frames[j].time)*1000))}advance()}};show(0);
</script></html>'''
for key,value in dict(CELLS=f"{int(water['cells']):,}",MEAN=f"{water['step_mean_ms']:.3f}",BED=f"{water['bed_peak_ms']:.3f}",TESTS=report['native_tests'],PEAK=f"{water['step_peak_ms']:.3f}",ERROR=f"{error:.8f}",DEFICIT=f"{deficit:.4f}",TOTALDEFICIT=f"{water['deficit_s']:.4f}",CHECKS=checks,FRAMES=rows).items():doc=doc.replace('__'+key+'__',str(value))
(OUT/'shared-mud-water.html').write_text(doc,encoding='utf-8')
print(json.dumps(report,indent=2))
