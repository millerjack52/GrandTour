"""Lay out unretouched road-level game captures for visual review."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json,shutil,html,hashlib
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/CohesiveRoads'
OUT=ROOT/'Art/Export/LidarStudy/CohesiveStyle/RoadReview';OUT.mkdir(parents=True,exist_ok=True)
report=json.loads((QA/'check.json').read_text(encoding='utf-8-sig'))
process=json.loads((QA/'process.json').read_text(encoding='utf-8-sig'))
assert report['ok'] and report['map_unchanged'] and len(report['views'])==6
assert process['exit_code']==0 and process['shader_validation_passed']
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
canvas=Image.new('RGB',(1660,1570),'#11201e');draw=ImageDraw.Draw(canvas)
draw.text((24,12),'LIDAR / ROAD-LEVEL VISUAL CHECK',font=font(28),fill='#eee9d8')
draw.text((24,53),'Current Evergreen profile • actual PIE game captures • eye heights 1.05–1.6 m',font=font(19),fill='#b9c7b9')
cards=[]
for i,v in enumerate(report['views']):
 name=v['view']+'.png';shutil.copy2(v['image'],OUT/name)
 im=Image.open(OUT/name).convert('RGB');assert im.size==(1600,900)
 x=24+(i%2)*820;y=96+(i//2)*490
 draw.text((x,y),v['view']+'  '+v['title'],font=font(19),fill='#eee9d8')
 canvas.paste(ImageOps.contain(im,(792,446),Image.Resampling.LANCZOS),(x,y+30))
 cards.append('<figure><figcaption>'+html.escape(v['view']+' — '+v['title'])+'</figcaption><a href="'+name+'"><img src="'+name+'"></a></figure>')
canvas.save(OUT/'overview.jpg',quality=94)
notes=json.loads((QA/'findings.json').read_text()) if (QA/'findings.json').exists() else []
text=''.join('<li>'+html.escape(n)+'</li>' for n in notes)
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LiDAR road-level review</title><style>body{background:#11201e;color:#eee9d8;font:17px/1.6 system-ui;margin:28px}h1{font-size:30px}a{color:#bad8b5}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}figure{margin:0}img{width:100%;display:block}figcaption{padding:10px 0}p,ul{max-width:1100px}@media(max-width:850px){.grid{grid-template-columns:1fr}}</style><h1>Road-level visual checks</h1><p>Six actual Play-in-Editor game captures from the saved LiDAR map, using its active Evergreen profile. Walking-height views and closer surface views share a 68° field of view and the existing visual-quality settings. Click a picture for its full 1600 × 900 image.</p><ul>'''+text+'''</ul><div class="grid">'''+''.join(cards)+'''</div><p>The level is unchanged. No driving test was performed. Performance timings remain unverified while the GPU is shared. <a href="evidence.json">Capture evidence</a> · <a href="../Review/index.html">Valley comparison and per-map tuning guide</a></p>'''
(OUT/'index.html').write_text(page,encoding='utf-8')
(OUT/'evidence.json').write_text(json.dumps(dict(check=report,process=process,findings=notes,image_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.png')}),indent=2))
print(OUT/'overview.jpg')
