"""Package actual game captures, reference photographs and measured evidence."""
from pathlib import Path
import json,sys,shutil,html
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/LidarStudy/CanopyDepth/Review';OUT.mkdir(exist_ok=True)
QA=ROOT/'Saved/LidarAuthoringQA/CanopyDepth';SHOTS=ROOT/'Saved/LidarAuthoringQA/RS7';REF=ROOT/'Art/References/ValleyDepthCoverage'
sys.path.insert(0,str(ROOT/'Art/tools'));from measure_perceived_detail import run
before=run('canopy-depth-before');after=run('canopy-depth-after')
evidence=dict(before=before,after=after,install=json.loads((QA/'install-result.json').read_text()),verification=json.loads((QA/'verify-result.json').read_text()),lighting=json.loads((QA/'lighting-result.json').read_text()))
evidence['saved_assets']=json.loads((QA/'assets-verified.json').read_text());assert evidence['saved_assets']['ok']
evidence['motion']=json.loads((SHOTS/'canopy-depth-valley-capture.json').read_text(encoding='utf-8-sig'));assert evidence['motion']['render_validation_passed']
for v in ['V01','V02','V03','G01']:
 for stage in ['before','after']:shutil.copy2(SHOTS/f'canopy-depth-{stage}-{v}.png',OUT/f'{stage}-{v}.png')
refs=json.loads((REF/'references.json').read_text())['references']
refs=[r for r in refs if r['id'] in ['A','B','D']]
for r in refs:shutil.copy2(REF/r['file'],OUT/r['file'])
for r in refs:
 if r['id']=='D':r['source']=r['file']
motion=QA/'valley.mp4'
if motion.exists():shutil.copy2(motion,OUT/'valley.mp4')
(OUT/'evidence.json').write_text(json.dumps(evidence,indent=2))
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
board=Image.new('RGB',(1800,1435),'#101a1c');d=ImageDraw.Draw(board)
def text(x,y,s,n=24,col='#e9efea'):d.text((x,y),s,font=font(n),fill=col)
def picture(path,box):
 im=Image.open(path).convert('RGB');im=ImageOps.contain(im,(box[2],box[3]));board.paste(im,(box[0]+(box[2]-im.width)//2,box[1]+(box[3]-im.height)//2))
text(28,15,'LIDAR FOREST  |  Coverage and depth',32)
text(28,62,'Actual game captures at the same saved valley camera. Reference photographs retain their original colours.',20,'#b7c9bd')
text(28,105,'CURRENT GAME — across the valley',24)
picture(OUT/'after-V02.png',(28,145,1160,653))
for r,y in zip(refs,[108,540,970]):
 text(1220,y,r['title'].replace(' — ',' / '),21)
 picture(OUT/r['file'],(1220,y+42,552,330))
text(28,835,'BEFORE',23);picture(OUT/'before-V02.png',(28,878,560,315))
text(620,835,'AFTER',23);picture(OUT/'after-V02.png',(620,878,560,315))
text(28,1232,'Broader crowns • elevation-aware trees • terrain and canopy lighting',24)
text(28,1279,'The reference photographs establish the target; they are not game captures.',20,'#b7c9bd')
text(28,1323,'Open index.html for full-resolution views, before/after sliders and measured GPU costs.',20,'#b7c9bd')
board.save(OUT/'comparison.jpg',quality=94)
sections=[]
for v,description in [('V02','Across the river valley · about 486 m'),('V01','Down into woodland · about 610 m'),('V03','Long valley view · about 1.55 km'),('G01','Close riverbank regression')]:
 sections.append(f'''<section><h2>{description}</h2><div class="compare"><img src="before-{v}.png"><img class="after" src="after-{v}.png"><span class="old">Before</span><span class="new">After</span></div><input type="range" min="0" max="100" value="50" aria-label="Before and after {v}"><p><a href="before-{v}.png">Full-resolution before</a> · <a href="after-{v}.png">Full-resolution after</a></p></section>''')
reference_cards=''.join(f'''<figure><img src="{r['file']}"><figcaption><b>{html.escape(r['title'])}</b><p>{html.escape(r['caption'])}</p><a href="{r['source']}">Reference source</a></figcaption></figure>''' for r in refs)
rows=''
for v in ['V01','V02','V03','G01']:
 b=before['measurements'][v]['GPUTime']['median'];a=after['measurements'][v]['GPUTime']['median']
 rows+=f'<tr><td>{v}</td><td>{b:.2f} ms</td><td>{a:.2f} ms</td><td>{a-b:+.2f} ms</td></tr>'
body='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LiDAR canopy coverage and depth</title><style>*{box-sizing:border-box}body{background:#101a1c;color:#e8efea;font:17px/1.55 system-ui;margin:0 auto;max-width:1500px;padding:32px}h1{font-size:38px;margin:0}h2{font-size:23px}a{color:#a6dbc8}header,section{margin-bottom:40px}p{color:#b9cbc0}.refs{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}figure{margin:0;background:#1a2828;padding:14px}.refs img{width:100%;height:260px;object-fit:contain}.compare{position:relative;aspect-ratio:16/9;background:#000}.compare img{position:absolute;inset:0;width:100%;height:100%}.after{clip-path:inset(0 0 0 50%)}.old,.new{position:absolute;top:14px;padding:6px 14px;background:#101a1ccc;border-radius:5px}.old{left:14px}.new{right:14px}input{width:100%;accent-color:#afdabc}table{border-collapse:collapse}td,th{padding:10px 25px;border-bottom:1px solid #456056;text-align:left}video{width:100%}.note{background:#20312d;padding:18px}@media(max-width:800px){body{padding:16px}.refs{grid-template-columns:1fr}}</style><header><h1>Connected canopy. Readable valley depth.</h1><p>Actual LiDAR game views alongside the agreed references. Same cameras, lighting, resolution and quality preset before and after.</p></header>'''
body+='<h2>The references</h2><div class="refs">'+reference_cards+'</div><p>Coverage: Lower Ripia. Depth: Pareraho. Colour character: the original supplied screenshot.</p>'
body+=''.join(sections)
if motion.exists():body+='<section><h2>Valley movement check</h2><video controls loop muted playsinline src="valley.mp4"></video><p>Actual game viewport frames; 12 fps review video. This is not a frame-rate benchmark.</p></section>'
body+='<section><h2>Measured rendering cost</h2><p>Warmed median GPU frame time, excluding screenshot stalls; 1600 × 900, saved v6 quality, TSR at 75%. One paired capture, not a full-route performance certification.</p><table><tr><th>View</th><th>Before</th><th>After</th><th>Change</th></tr>'+rows+'</table></section>'
body+='<section><h2>What changed and what passed</h2><p>Broader connected beech crowns at unchanged tree heights and bases. The distance representation uses 24 captured azimuth/elevation views with depth reprojection and instance-correct lighting normals, replacing the three crossed side cards. A world-aligned distance-lighting field follows the actual terrain and 146,200 tree crowns: slope normals, soft visibility to the sun and approximate enclosure.</p><p>The main forest retains all planting transforms and counts. Terrain, roads, collisions, understorey and the approved riverbank assets are unchanged. Saved-level reload and material fallback checks are recorded in the evidence; 185 existing asset packages remain byte-identical.</p><p class="note">Distant canopy shadows are baked for the saved sun direction and need rebuilding if the sun, terrain or planting changes. They approximate the crown envelope, rather than individual moving leaves. Near geometry retains dynamic shadows. This pass is not a claim of a pixel-for-pixel match to the photographs.</p><a href="evidence.json">Detailed evidence</a></section>'
body+='''<script>document.querySelectorAll('input[type=range]').forEach(r=>r.addEventListener('input',()=>r.previousElementSibling.querySelector('.after').style.clipPath=`inset(0 0 0 ${r.value}%)`))</script>'''
(OUT/'index.html').write_text(body,encoding='utf-8')
print(OUT/'index.html')
