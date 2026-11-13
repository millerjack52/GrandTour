"""Matched native game frames and bounded-workload evidence for the water pass."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,shutil,csv,statistics
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/WaterRefinement';OUT=ROOT/'Art/Export/LidarStudy/WaterRefinement';OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
before=load(QA/'Before/process.json');after=load(QA/'After/process.json');install=load(QA/'install.json');verification=load(QA/'verify.json')
assert all(x['ok'] for x in [before,after,install,verification])
assert before['plan']['views']==after['plan']['views'] and before['plan']['quality']==after['plan']['quality']
titles={'mapped-pond-above':'Northern pond / shoreline','river-above':'River / surface and shallows','access-pond-above':'Woodland pond / reflections','river-bank':'River / bank view','mapped-pond-low':'Northern pond / low view','access-pond-bank':'Woodland pond / low view'}
font=lambda size:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)
for name,title in titles.items():
    board=Image.new('RGB',(1824,625),'#15201d');d=ImageDraw.Draw(board)
    d.text((16,12),title,font=font(27),fill='#edf0e5')
    d.text((16,49),'Same camera and palette / unretouched 888 x 500 game frames',font=font(19),fill='#b9c6bc')
    for i,stage in enumerate(['Before','After']):
        x=16+i*904;d.text((x,82),stage.upper(),font=font(20),fill='#edf0e5')
        src=QA/stage/(name+'.png');im=Image.open(src).convert('RGB');assert im.size==(888,500)
        shutil.copy2(src,OUT/(name+'-'+stage.lower()+'.png'));board.paste(im,(x,116))
    board.save(OUT/(name+'-comparison.jpg'),quality=94)
# Locate each capture by the exact CSV path reported by its own log.
import re
counters={};csvs={}
for stage in ['Before','After']:
    log=(QA/stage/'capture.log').read_text(errors='replace')
    matches=re.findall(r'Profile\(\d+_\d+\)\.csv',log)
    assert matches,stage
    file=ROOT/'Saved/Profiling/CSV'/matches[-1];csvs[stage]=str(file)
    rows=list(csv.DictReader(file.open()))
    plan=load(QA/stage/'plan.json')
    shot_frames=[int(c.split(':',1)[0]) for c in plan['commands'] if ':Shot filename=' in c]
    camera_frames=[int(c.split(':',1)[0]) for c in plan['commands'] if ' SetReviewView ' in c]
    for i,view in enumerate(before['plan']['views']):
        start=max(camera_frames[i]+10,shot_frames[i]-25);end=shot_frames[i]-3
        for key in ['RHI/DrawCalls','RHI/PrimitivesDrawn','DrawCall/ShadowDepths']:
            vals=[float(r[key]) for r in rows[start:end] if r.get(key)]
            counters.setdefault(view['id'],{}).setdefault(key,{})[stage.lower()]=statistics.median(vals)
evidence=dict(install=install,verification=verification,captures_passed=True,identical_cameras=True,identical_quality=True,render_counters=counters,csvs=csvs,gpu_timings_verified=False,capture_note='Final capture explicitly completes grass streaming, then uses 30 settling frames per view during GPU contention; baseline uses 150. Cameras and image quality match.')
(OUT/'evidence.json').write_text(json.dumps(evidence,indent=2));(QA/'render-counters.json').write_text(json.dumps(counters,indent=2))
options=''.join(f'<option value="{k}">{v}</option>' for k,v in titles.items())
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Water refinement</title>
<style>body{margin:28px;background:#15201d;color:#edf0e5;font:18px/1.6 system-ui}img{width:100%}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}p{max-width:1000px}select{padding:10px}a{color:#b9d4c5}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>
<h1>Water refinement</h1><p>The river and ponds keep continuous surfaces and their own optical materials as the interaction window moves. The northern pond has rounded shallow banks with shared collision and water-query heights. Smaller, restrained ripples leave clearer reflections in calmer water. Palette and fog settings are unchanged.</p>
<select id="view">OPTIONS</select><div class="grid"><div><h3>Before</h3><img id="before" src="mapped-pond-above-before.png"></div><div><h3>After</h3><img id="after" src="mapped-pond-above-after.png"></div></div>
<p>Actual 888 × 500 game frames with matching cameras and render settings. Water phase and temporal rendering can vary between runs; no external colour correction.</p>
<p>Cost: 12,150 bank triangles across 27 small terrain tiles; pond meshes total 14,852 triangles (previously 4,106). No additional water texture samples or simulation cells. GPU timings remain unverified; full-scene workload counters are recorded in the evidence. Different streaming completion and shadow-cache state prevent attributing their entire difference to this water pass.</p>
<p>Water material controls: PoolRippleStrength, RiffleRippleStrength, RippleScale PoolRoughness, CalmSlopeStrength and RiffleSlopeStrength. Each body retains separate map-owned values. Existing wakes and interaction fields remain connected.</p>
<p><a href="evidence.json">Validation and workload counters</a></p><script>view.onchange=()=>{for(const s of ['before','after'])document.getElementById(s).src=view.value+'-'+s+'.png'}</script>'''
(OUT/'index.html').write_text(page.replace('OPTIONS',options),encoding='utf-8')
board=Image.new('RGB',(1824,1875),'#15201d')
for i,name in enumerate(['mapped-pond-above','river-bank','access-pond-above']):
    board.paste(Image.open(OUT/(name+'-comparison.jpg')),(0,i*625))
board.save(OUT/'water-before-after.jpg',quality=94)
print(OUT)
