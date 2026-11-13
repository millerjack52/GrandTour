"""Matched game views for the far-ridge haze pass."""
from pathlib import Path
import json,shutil,sys,re
from PIL import Image,ImageOps,ImageDraw,ImageFont
R=Path('C:/GrandTour');Q=R/'Saved/LidarAuthoringQA/FarHaze';S=R/'Saved/LidarAuthoringQA/RS7';O=R/'Art/Export/LidarStudy/FarHaze/Review';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'Art/tools'));from measure_perceived_detail import run
e={s:json.loads((Q/(s+'.json')).read_text()) for s in ['install','verify']}
for s in ['install','verify']:
 assert e[s]['ok'];e[s+'_process']=json.loads((Q/(s+'-process.json')).read_text(encoding='utf-8-sig'));assert e[s+'_process']['exit_code']==0
e['before']=run('preferred-canopy-restored');e['after']=run('far-ridge-haze')
for v in ['V01','V02','V03','G01']:
 for stage,label in [('before','preferred-canopy-restored'),('after','far-ridge-haze')]:shutil.copy2(S/f'{label}-{v}.png',O/f'{stage}-{v}.png')
b=Image.new('RGB',(1800,1180),'#101a1c');d=ImageDraw.Draw(b)
def text(x,y,t,n=24):d.text((x,y),t,font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n),fill='#e9efea')
text(24,15,'A LIGHT HAZE ON THE FURTHEST RIDGES',32)
text(24,65,'Actual game views | Same camera and exposure | Preferred canopy retained',23)
for row,(v,title) in enumerate([('V02','Across the valley'),('V03','Long valley view')]):
 for col,stage in enumerate(['before','after']):
  x=24+896*col;y=115+520*row;text(x,y,title+' / '+stage.upper(),22)
  b.paste(ImageOps.contain(Image.open(O/f'{stage}-{v}.png').convert('RGB'),(856,482)),(x,y+31))
b.save(O/'comparison.jpg',quality=95)
body='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Far ridge haze</title><style>body{max-width:1600px;margin:auto;padding:24px;background:#101a1c;color:#e9efea;font:17px/1.5 system-ui}a{color:#afdabc}img{width:100%}.pair{position:relative;aspect-ratio:16/9}.pair img{position:absolute;inset:0}.after{clip-path:inset(0 0 0 50%)}input{width:100%}section{margin:36px 0}td,th{padding:8px 18px;text-align:left}</style><h1>A light haze on the furthest ridges</h1><p>The preferred canopy and existing fog remain intact. A smooth blue-grey veil starts beyond 1.2 km of view depth and reaches 34% at 2.8 km. The sky is excluded. No noise, blur or extra volumetric simulation.</p><img src="comparison.jpg">'''
for v,title in [('V02','Across the valley'),('V03','Long valley view'),('V01','Down into woodland'),('G01','Close bank check')]:
 body+=f'<section><h2>{title}</h2><p>Before left; after right.</p><div class="pair"><img src="before-{v}.png"><img class="after" src="after-{v}.png"></div><input type="range" min="0" max="100" value="50" aria-label="Compare {v}"><a href="after-{v}.png">Full-resolution current game view</a></section>'
body+='<h2>Warmed median GPU time</h2><p>Paired standalone captures at 1600 × 900, saved v6 settings; screenshot stalls excluded.</p><table><tr><th>View</th><th>Before</th><th>After</th></tr>'
for v in ['V01','V02','V03','G01']:
 a=e['before']['measurements'][v]['GPUTime']['median'];z=e['after']['measurements'][v]['GPUTime']['median'];body+=f'<tr><td>{v}</td><td>{a:.2f} ms</td><td>{z:.2f} ms</td></tr>'
body+='</table><p>Saved-level reload and game shader checks passed. All planting transforms, the new detail, terrain, canopy material assignments and existing height-fog settings are unchanged; 185 protected packages verified. The lightweight haze colour is authored for the current SDR presentation.</p><p><a href="evidence.json">Verification evidence</a></p><script>document.querySelectorAll("input").forEach(r=>r.addEventListener("input",()=>r.previousElementSibling.querySelector(".after").style.clipPath=`inset(0 0 0 ${r.value}%)`))</script>'
(O/'evidence.json').write_text(json.dumps(e,indent=2));(O/'index.html').write_text(body,encoding='utf-8')
assert all((O/v).exists() for v in re.findall(r'(?:src|href)="([^"]+)"',body));print(O/'index.html')
