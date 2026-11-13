from pathlib import Path
import json,sys,shutil
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/CanopyDepth/HazeReview';O.mkdir(exist_ok=True)
S=R/'Saved/LidarAuthoringQA/RS7';sys.path.insert(0,str(R/'Art/tools'))
from measure_perceived_detail import run
before=run('canopy-contrast-after');after=run('distance-haze-after')
install=json.loads((R/'Saved/LidarAuthoringQA/DistanceHaze/install.json').read_text());assert install['ok']
(O/'evidence.json').write_text(json.dumps(dict(before=before,after=after,installation=install),indent=2))
for v in ['V01','V02','V03','G01']:
 for stage,label in [('before','canopy-contrast-after'),('after','distance-haze-after')]:shutil.copy2(S/f'{label}-{v}.png',O/f'{stage}-{v}.png')
board=Image.new('RGB',(1800,1140),'#101a1c');d=ImageDraw.Draw(board)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
def text(x,y,t,n=24):d.text((x,y),t,font=font(n),fill='#e9efea')
text(24,15,'LIDAR FOREST | More atmosphere across the distant slopes',32)
text(24,65,'Actual game views. Same camera, exposure and canopy materials.',22)
text(24,108,'PREVIOUS');text(920,108,'CURRENT')
for row,v in enumerate(['V02','V03']):
 for col,stage in enumerate(['before','after']):
  im=Image.open(O/f'{stage}-{v}.png').convert('RGB');im=ImageOps.contain(im,(856,482));board.paste(im,(24+col*896,150+row*492))
board.save(O/'comparison.jpg',quality=94)
body='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LiDAR distant haze</title><style>body{max-width:1600px;margin:auto;padding:24px;background:#101a1c;color:#e9efea;font:17px/1.5 system-ui}a{color:#afdabc}img{width:100%}.pair{position:relative;aspect-ratio:16/9}.pair img{position:absolute;inset:0}.after{clip-path:inset(0 0 0 50%)}input{width:100%}section{margin:35px 0}td,th{padding:8px 20px;text-align:left}</style><h1>More atmosphere across the distant slopes</h1><p>The height fog reaches higher into the valley and begins 180 metres from the camera. The existing local river mist is retained. Canopy materials, sun and exposure are unchanged from the contrast pass.</p><img src="comparison.jpg">'''
for v,title in [('V02','Across the valley'),('V03','Distant ridges'),('V01','Down into woodland'),('G01','Close riverbank')]:
 body+=f'<section><h2>{title}</h2><p>Previous on the left; current on the right.</p><div class="pair"><img src="before-{v}.png"><img class="after" src="after-{v}.png"></div><input type="range" value="50" min="0" max="100" aria-label="Before and after {v}"><a href="after-{v}.png">Full-resolution current capture</a></section>'
body+='<h2>Warmed median GPU time</h2><p>One paired capture at 1600 × 900, saved v6 settings; screenshot stalls excluded.</p><table><tr><th>View</th><th>Previous</th><th>Current</th></tr>'
for v in ['V01','V02','V03','G01']:
 b=before['measurements'][v]['GPUTime']['median'];a=after['measurements'][v]['GPUTime']['median'];body+=f'<tr><td>{v}</td><td>{b:.2f} ms</td><td>{a:.2f} ms</td></tr>'
body+='''</table><p>Saved-level reload, planting/ground preservation and renderer checks passed. <a href="evidence.json">Detailed evidence</a>.</p><script>document.querySelectorAll('input').forEach(r=>r.addEventListener('input',()=>r.previousElementSibling.querySelector('.after').style.clipPath=`inset(0 0 0 ${r.value}%)`))</script>'''
(O/'index.html').write_text(body,encoding='utf-8');print(O/'index.html')
