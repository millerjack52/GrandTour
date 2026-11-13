"""Matched standalone atmosphere review. Source screenshots are copied unchanged."""
import csv,json,math,statistics,shutil,hashlib
from pathlib import Path
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7';ATM=ROOT/'Saved/LidarAuthoringQA/Atmosphere'
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/Atmosphere';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def run(label):
 info=read(QA/f'runtime-{label}.json');assert info['exit_code']==0
 rows=list(csv.DictReader(open(info['csv'],newline='')));measurements={}
 for i,v in enumerate(info['views']):
  start=200+i*info['frames_per_view'];samples=rows[start+150:start+265]+rows[start+325:start+390]
  measurements[v['view']]={}
  for k in ['GPUTime','FrameTime','GPUMem/LocalUsedMB']:
   values=[float(r[k]) for r in samples if r.get(k)]
   measurements[v['view']][k]=dict(mean=statistics.mean(values),p95=sorted(values)[math.ceil(len(values)*.95)-1],n=len(values))
 return dict(csv=info['csv'],commands=info['commands'],views=info['views'],measurements=measurements)
before=run('atmosphere-before');after=run('atmosphere-fog-only')
assert before['views']==after['views'] and before['commands']==after['commands']
for v in before['views']:
 for side,label in [('before','atmosphere-before'),('after','atmosphere-fog-only')]:
  shutil.copy2(QA/f'{label}-{v["view"]}.png',OUT/f'{side}-{v["view"]}.png')
shutil.copy2(ROOT/'Art/References/ReferenceStyle/2026-11-05.jpg',OUT/'original-reference.jpg')
evidence=dict(install=read(ATM/'install.json'),validation=read(ATM/'validation.json'),before=before,after=after,mean_gpu_delta_ms={v:after['measurements'][v]['GPUTime']['mean']-before['measurements'][v]['GPUTime']['mean'] for v in before['measurements']},method='Same saved v6, 1600x900, camera poses and exposure. 180 warm frames per view, excluding screenshot and recovery. Single matched pair; not whole-route performance certification.',map_sha256=hashlib.sha256((ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap').read_bytes()).hexdigest())
evidence['editor_teardown']='Authoring editor reported exit -1073741819 after save, successful checks, and normal shutdown log. Standalone game reload/capture exit is checked independently above.'
evidence['technical_references']=['https://dev.epicgames.com/documentation/en-us/unreal-engine/exponential-height-fog-in-unreal-engine','https://dev.epicgames.com/documentation/en-us/unreal-engine/local-fog-volumes-in-unreal-engine']
evidence['fog_isolation']=run('atmosphere-fog-only')
evidence['rejected_long_lods']=read(ATM/'rejected-long-lods-runtime.json')
evidence['rejected_modest_lods']=read(ATM/'rejected-modest-lods-runtime.json')
evidence['decision']='Both longer geometry ranges rejected: uniform extension cost +9 to +10 ms; modest species-specific extension cost up to +3.62 ms for a small visual gain. Final is the measured fog-only state, with exact original canopy mesh hashes restored.'
(OUT/'evidence.json').write_text(json.dumps(evidence,indent=2))
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forest atmosphere - actual game comparison</title>
<style>*{box-sizing:border-box}body{margin:0;background:#111b1b;color:#eef4ed;font:16px/1.5 system-ui}main{max-width:1640px;margin:auto;padding:24px}h1{font-size:28px;margin:0 0 8px}p{color:#c2d1cb}nav{display:flex;gap:10px;margin:20px 0;flex-wrap:wrap}button,a{color:#c9eee2}button{background:#253e38;border:1px solid #517366;border-radius:6px;padding:10px 16px;cursor:pointer}button[aria-pressed=true]{background:#497461;color:white}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}.pair img{display:block;width:100%}.pair h2{font-size:17px;margin:0 0 10px}.evidence{max-width:950px}.reference{max-height:400px;max-width:100%}.board nav,.board .evidence{display:none}.board main{padding:24px}.board .intro{margin-bottom:18px}@media(max-width:700px){.pair{grid-template-columns:1fr}}</style>
<main><h1>Forest atmosphere · distance and depth</h1><p class="intro">Matched actual game views. Same camera, exposure and saved v6 graphics preset.</p>
<nav><button data-view="B04">Across the river</button><button data-view="F01">Distant forest</button><button data-view="F02">Inside the forest</button><button data-view="B01">Near bank</button></nav>
<div class="pair"><section><h2>Before · haze begins at 1.1 km</h2><img id="before" alt="Before atmosphere changes"></section><section><h2>After · layered forest haze</h2><img id="after" alt="After atmosphere changes"></section></div>
<div class="evidence"><p>Light cool haze begins at 18 metres. Two soft local mist volumes sit deeper in the river woodland. The foreground remains clear, and the sun, sky lighting and exposure are unchanged.</p><p>Distant trees recede through cooler haze and lower contrast. Two longer geometry-range trials were rejected because their cost outweighed the small visual gain. The original tree assets and LOD thresholds are restored exactly; tree placement, collision, terrain and approved riverbank plants are retained.</p><p id="timing"></p><p><a href="evidence.json">Saved settings, checks and timings</a> · <a href="../index.html">Full reference collection</a> · <a href="../PhysicalRelief/index.html">Previous surface pass</a></p><h2>Original visual direction</h2><p>Colour, variety and separation remain the target. This pass changes atmosphere and distance representation; it does not claim a complete match to the reference or a whole-world vegetation rebuild.</p><img class="reference" src="original-reference.jpg" alt="User's original stylized woodland reference"></div></main>
<script>const p=new URLSearchParams(location.search);if(p.has('board'))document.body.classList.add('board');function choose(v){for(const side of ['before','after'])document.getElementById(side).src=side+'-'+v+'.png';for(const b of document.querySelectorAll('button'))b.setAttribute('aria-pressed',b.dataset.view===v)}for(const b of document.querySelectorAll('button'))b.onclick=()=>choose(b.dataset.view);choose(p.get('view')||'B04');fetch('evidence.json').then(r=>r.json()).then(e=>{let d=Object.values(e.mean_gpu_delta_ms);document.getElementById('timing').textContent='Mean GPU change across these views: '+Math.min(...d).toFixed(2)+' to '+Math.max(...d).toFixed(2)+' ms. One matched pair does not characterize all timing variation.'}).catch(()=>{});</script></html>'''
deltas=list(evidence['mean_gpu_delta_ms'].values())
html=html.replace('<p id="timing"></p>',f'<p id="timing">Measured mean GPU change: {min(deltas):+.2f} to {max(deltas):+.2f} ms across four views. One matched pair does not characterize all timing variation.</p>')
(OUT/'index.html').write_text(html,encoding='utf-8')
manifest=ROOT/'Art/Export/LidarStudy/Place/first-section.json';data=read(manifest)
data['latest_atmosphere_review']=str(OUT/'index.html');data['latest_atmosphere_evidence']=str(OUT/'evidence.json')
manifest.write_text(json.dumps(data,indent=2)+'\n')
parent=OUT.parent/'index.html';s=parent.read_text(encoding='utf-8')
if 'Atmosphere/index.html' not in s:s=s.replace('<p><a href="PhysicalRelief/index.html">Latest update:', '<p><a href="Atmosphere/index.html">Latest update: forest atmosphere and distant trees</a></p>\n<p><a href="PhysicalRelief/index.html">Previous update:')
parent.write_text(s,encoding='utf-8')
print(json.dumps(dict(review=str(OUT/'index.html'),mean_gpu_delta_ms=evidence['mean_gpu_delta_ms']),indent=2))
