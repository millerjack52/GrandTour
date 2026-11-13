"""Package actual level dressing captures and placement/verification evidence."""
from pathlib import Path
import json,sys,shutil
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path('C:/GrandTour');Q=R/'Saved/LidarAuthoringQA/LevelDetail';S=R/'Saved/LidarAuthoringQA/RS7';D=R/'Art/Export/LidarStudy/LevelDetail';O=D/'Review';O.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'Art/tools'));from measure_perceived_detail import run
before=run('level-detail-before');after=run('level-detail-after')
install=json.loads((Q/'install.json').read_text());verify=json.loads((Q/'verify.json').read_text());assert install['ok'] and verify['ok']
process=json.loads((Q/'verify-process.json').read_text(encoding='utf-8-sig'));assert process['exit_code']==0 and process['result_ok']
plan=json.loads((D/'plan.json').read_text());evidence=dict(before=before,after=after,installation=install,verification=verify,verification_process=process,plan=plan)
(O/'evidence.json').write_text(json.dumps(evidence,indent=2))
for v in ['D01','D02','D03','D04','V02','G01']:
 for stage in ['before','after']:shutil.copy2(S/f'level-detail-{stage}-{v}.png',O/f'{stage}-{v}.png')
shutil.copy2(D/'distribution.png',O/'distribution.png')
shutil.copy2(R/'Art/References/ValleyDepthCoverage/original-scene.jpg',O/'reference.jpg')
b=Image.new('RGB',(1800,1690),'#101a1c');draw=ImageDraw.Draw(b);font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
def text(x,y,s,n=24):draw.text((x,y),s,font=font(n),fill='#e9efea')
text(24,15,'DETAIL ACROSS THE LIDAR LEVEL',32)
text(24,65,f"{install['instances']:,} additions | Mixed plants, rocks, moss and deadwood | Actual game views",23)
for row,(v,label) in enumerate([('D01','Woodland and deadwood'),('D03','Rocky slope'),('D04','Damp woodland')]):
 y=115+row*520;text(24,y,label+' / BEFORE',22);text(920,y,label+' / AFTER',22)
 for col,stage in enumerate(['before','after']):
  im=Image.open(O/f'{stage}-{v}.png').convert('RGB');im=ImageOps.contain(im,(856,482));b.paste(im,(24+896*col,y+31))
b.save(O/'comparison.jpg',quality=94)
body='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LiDAR level detail</title><style>body{max-width:1600px;margin:auto;padding:24px;background:#101a1c;color:#e9efea;font:17px/1.5 system-ui}a{color:#afdabc}img{width:100%}.pair{position:relative;aspect-ratio:16/9}.pair img{position:absolute;inset:0}.after{clip-path:inset(0 0 0 50%)}input{width:100%}section{margin:35px 0}td,th{padding:8px 20px;text-align:left}.refs{display:grid;grid-template-columns:2fr 1fr;gap:24px}.refs img{max-height:700px;object-fit:contain}@media(max-width:800px){.refs{display:block}}</style><h1>Detail across the LiDAR level</h1>'''
body+=f"<p>{install['instances']:,} additional instances across woodland, openings, rocky slopes and damp pockets. Mixed communities with irregular gaps; most additions are grasses, moss, shrubs and stones.</p><img src=\"comparison.jpg\">"
body+='<section><h2>Distribution and colour reference</h2><div class="refs"><img src="distribution.png"><img src="reference.jpg"></div><p>Green: woodland. Gold: openings and edges. Grey: rocky slopes. Blue: damp pockets. White circles mark the representative review sites. The supplied original image is the colour/variety reference, not a game capture.</p></section>'
for v,title in [('D01','Woodland and deadwood'),('D02','Dense forest edge'),('D03','Rocky slope'),('D04','Damp woodland'),('V02','Valley regression'),('G01','Approved bank regression')]:
 body+=f'<section><h2>{title}</h2><p>Before on the left; after on the right. Same saved camera and quality settings.</p><div class="pair"><img src="before-{v}.png"><img class="after" src="after-{v}.png"></div><input type="range" value="50" min="0" max="100" aria-label="Before and after {v}"><a href="after-{v}.png">Full-resolution after</a></section>'
body+='<h2>Accepted additions</h2><table><tr><th>Role</th><th>Instances</th></tr>'
for role,n in install['roles'].items():body+=f'<tr><td>{role}</td><td>{n:,}</td></tr>'
body+='</table><h2>Warmed median GPU time</h2><p>One paired game capture at 1600 × 900, saved v6 settings. Screenshot stalls excluded; not a full-route performance certification.</p><table><tr><th>View</th><th>Before</th><th>After</th></tr>'
for v in ['D01','D02','D03','D04','V02','G01']:
 a=before['measurements'][v]['GPUTime']['median'];z=after['measurements'][v]['GPUTime']['median'];body+=f'<tr><td>{v}</td><td>{a:.2f} ms</td><td>{z:.2f} ms</td></tr>'
body+='''</table><h2>Placement and preservation checks</h2><p>Road, water, paddock, yard and approved-bank exclusion zones. Existing-plant and trunk spacing checks. Final terrain slope limits, support-curvature rejection for low debris and logs, and frond probes for bank plants. Large anchor stones/logs/stumps use separate collision meshes. Small dressing is non-colliding.</p><p>Saved instance counts and transforms verified after reloading. Existing forest, understory, bank and ground snapshots retained. The original shared asset packages are unchanged. Close foliage casts shadows; small detail culls before distant valley views.</p><p>The distribution is map-wide; visual inspection samples four habitats rather than every individual placement. Re-plan and re-seat after changing roads or terrain. <a href="evidence.json">Detailed evidence</a>.</p><script>document.querySelectorAll('input').forEach(r=>r.addEventListener('input',()=>r.previousElementSibling.querySelector('.after').style.clipPath=`inset(0 0 0 ${r.value}%)`))</script>'''
(O/'index.html').write_text(body,encoding='utf-8');print(O/'index.html')
