from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import csv,json,shutil,hashlib,statistics
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/CanopyInterior';CAP=QA/'Capture';OUT=ROOT/'Art/Export/LidarStudy/CanopyInterior/Review';OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
r=load(CAP/'process.json');install=load(QA/'install.json');assert r['ok'] and install['ok']
assert install['palette_and_fog_unchanged']
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
for name in r['plan']['images']:shutil.copy2(CAP/name,OUT/name)
rect=load(QA/'crop.json')['rectangle']
for name in ['before','after']:
 Image.open(OUT/('valley-'+name+'.png')).crop(tuple(rect)).save(OUT/('selected-area-'+name+'.png'))
for ident,title in [('valley','Same valley camera'),('selected-area','Matched crop of the area you highlighted'),('road','Close roadside check'),('leaves','Close leaf check')]:
 board=Image.new('RGB',(1832,670),'#18201c');d=ImageDraw.Draw(board)
 d.text((20,12),'LIDAR / CANOPY DEPTH AND FOREST INTERIOR',font=font(28),fill='#e5e2d3')
 d.text((20,53),title+' / palette, exposure and fog unchanged',font=font(19),fill='#b9c2b2')
 for i,(suffix,label) in enumerate([('before','BEFORE'),('after','AFTER')]):
  x=20+i*906;d.text((x,96),label,font=font(20),fill='#e5e2d3')
  im=Image.open(OUT/(ident+'-'+suffix+'.png')).convert('RGB')
  im=ImageOps.contain(im,(886,500));board.paste(im,(x+(886-im.width)//2,136))
 board.save(OUT/(ident+'-comparison.jpg'),quality=95)
csvfile=max((ROOT/'Saved/Profiling/CSV').glob('*.csv'),key=lambda p:p.stat().st_mtime)
rows=list(csv.DictReader(csvfile.open()));counters={}
for key in ['RHI/DrawCalls','RHI/PrimitivesDrawn','DrawCall/Basepass','DrawCall/ShadowDepths']:
 before=statistics.median(float(x[key]) for x in rows[85:120]);after=statistics.median(float(x[key]) for x in rows[225:260])
 counters[key]=dict(before=before,after=after,delta=after-before)
(QA/'render-counters.json').write_text(json.dumps(dict(csv=str(csvfile),windows=[[85,120],[225,260]],counters=counters,performance_verified=False,note='Counters from matched valley view; streaming and temporal rendering vary. Not clean GPU timings.'),indent=2))
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Canopy depth and forest interior</title><style>body{margin:28px;background:#18201c;color:#e5e2d3;font:17px/1.6 system-ui}p{max-width:1100px}a{color:#daca9a}img{max-width:100%}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}select{padding:10px}td,th{text-align:left;padding:10px;border-bottom:1px solid #536453}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>
<h1>Canopy depth and forest interior</h1><p>The accepted warm-light/cool-shadow palette is unchanged. Individual crowns retain more directional shading and occlusion, with a volume cue for distant tree representations. Sparse grouped thickets fill part of the exposed middle layer underneath.</p>
<label>Compare <select id="view"><option value="selected-area">Your highlighted area</option><option value="valley">Full valley view</option><option value="road">Roadside check</option><option value="leaves">Leaf check</option></select></label><div class="grid"><div><h3>Before</h3><img id="before" src="selected-area-before.png"></div><div><h3>After</h3><img id="after" src="selected-area-after.png"></div></div>
<p>Actual 888 × 500 game frames; the selected-area images are matching crops of those frames. No external colour correction. Same camera, palette, exposure configuration, fog and rendering settings within one run. Temporal rendering and vegetation streaming can vary slightly.</p>
<h2>Cost and controls</h2><p>CLUSTER_COUNT clusters across the map, in one hierarchical instance component. Each distant foliage representation uses two triangles and reuses the existing tree colour/normal-depth atlases. No new atlas textures, collision, ray-tracing instances or dynamic shadow passes for the added thickets. They reveal between 140–240 m and fade out between 950–1300 m; close vegetation remains the detailed existing assets.</p>
<p>Existing canopy triangle counts and texture sample counts are unchanged. The crown shading adds arithmetic. GPU timings and smooth-motion transitions remain unverified.</p>
<table><tr><th>Valley render counter (median)</th><th>Before</th><th>After</th></tr>COUNTERS</table>
<p>These are workload counters, not a clean speed benchmark; culling, streaming and temporal rendering affect them.</p>
<p>The map profile's <b>Forest Depth → Canopy Depth Strength</b> controls the crown treatment; zero also hides the new understory. <b>Forest Interior</b> assigns the map-specific placement asset. Palette and fog controls remain independent.</p>
<p><a href="selected-area-comparison.jpg">Highlighted area board</a> / <a href="valley-comparison.jpg">Valley board</a> / <a href="road-comparison.jpg">Roadside board</a> / <a href="evidence.json">Validation evidence</a></p>
<script>document.getElementById('view').onchange=function(){for(let suffix of ['before','after'])document.getElementById(suffix).src=this.value+'-'+suffix+'.png'}</script>'''
page=page.replace('CLUSTER_COUNT',f"{install['placements']['clusters']:,}").replace('COUNTERS',''.join(f"<tr><td>{k}</td><td>{v['before']:,.0f}</td><td>{v['after']:,.0f}</td></tr>" for k,v in counters.items()))
(OUT/'index.html').write_text(page,encoding='utf-8')
(OUT/'evidence.json').write_text(json.dumps(dict(install=install,capture=r,crop=load(QA/'crop.json'),render_counters=load(QA/'render-counters.json'),sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.png')}),indent=2))
print(json.dumps(counters,indent=2));print(OUT)
