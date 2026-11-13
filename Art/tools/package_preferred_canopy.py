"""Review the restored canopy against the user's chosen historical game capture."""
from pathlib import Path
import json,shutil,sys
from PIL import Image,ImageOps,ImageDraw,ImageFont
R=Path('C:/GrandTour');Q=R/'Saved/LidarAuthoringQA/PreferredCanopy';S=R/'Saved/LidarAuthoringQA/RS7';O=R/'Art/Export/LidarStudy/CanopyDepth/PreferredReview';O.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'Art/tools'));from measure_perceived_detail import run
e={s:json.loads((Q/(s+'.json')).read_text()) for s in ['install','verify']}
for s in ['install','verify']:
 assert e[s]['ok'];e[s+'_process']=json.loads((Q/(s+'-process.json')).read_text(encoding='utf-8-sig'));assert e[s+'_process']['exit_code']==0
e['capture']=run('preferred-canopy-restored');e['prior_capture']=run('level-detail-after')
e['image_comparison']=json.loads((Q/'image-comparison.json').read_text())
for v in ['V01','V02','V03','G01']:
 for label,source in [('preferred','distance-haze-after'),('restored','preferred-canopy-restored'),('rejected','canopy-surface-after')]:shutil.copy2(S/f'{source}-{v}.png',O/f'{label}-{v}.png')
# Current detail-pass baseline is more recent for the principal valley view.
shutil.copy2(S/'level-detail-after-V02.png',O/'rejected-V02.png')
shutil.copy2(R/'Art/References/ValleyDepthCoverage/original-scene.jpg',O/'original-reference.jpg')
b=Image.new('RGB',(1800,1040),'#101a1c');d=ImageDraw.Draw(b)
def text(x,y,t,n=24):d.text((x,y),t,font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n),fill='#e9efea')
text(24,18,'RESTORED CANOPY | Your preferred valley treatment',32)
text(24,68,'Same saved game camera and exposure. Earlier haze and canopy shading restored; new ground detail retained.',23)
for c,(label,title) in enumerate([('preferred','YOUR PREFERRED PREVIOUS PASS'),('restored','RESTORED GAME VIEW')]):
 x=24+c*896;text(x,114,title);im=Image.open(O/f'{label}-V02.png').convert('RGB');b.paste(ImageOps.contain(im,(856,482)),(x,150))
 text(x,654,'MATCHED DETAIL — opposite slope',22);b.paste(im.crop((920,240,1520,412)).resize((856,245),Image.Resampling.LANCZOS),(x,694))
text(24,975,'52,799 ground-detail additions preserved. Tree transforms, terrain and approved bank unchanged.',24)
b.save(O/'comparison.jpg',quality=95)
body='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Restored preferred canopy</title><style>body{max-width:1600px;margin:auto;padding:24px;background:#101a1c;color:#e9efea;font:17px/1.5 system-ui}a{color:#afdabc}img{width:100%}.pair{position:relative;aspect-ratio:16/9}.pair img{position:absolute;inset:0}.after{clip-path:inset(0 0 0 50%)}input{width:100%}section{margin:36px 0}</style><h1>Restored preferred canopy</h1><p>The left-hand historical pass selected in the conversation is the target. Earlier global haze restored (180 m start, 0.036 density, 0.70 maximum opacity), and the later surface-shadow overlay removed from both foliage geometry and distant proxies. Sun, camera, exposure, tree placements and the 52,799 new ground-detail instances are retained.</p><img src="comparison.jpg">'''
for v,title in [('V02','Across the valley'),('V01','Down into woodland'),('V03','Long valley view'),('G01','Approved bank')]:
 body+=f'<section><h2>{title}</h2><p>Preferred historical capture on the left; restored game on the right.</p><div class="pair"><img src="preferred-{v}.png"><img class="after" src="restored-{v}.png"></div><input type="range" min="0" max="100" value="50" aria-label="Compare {v}"><a href="restored-{v}.png">Full-resolution restored game view</a></section>'
body+='<section><h2>Change from the rejected treatment</h2><p>Before restoration on the left; restored on the right.</p><div class="pair"><img src="rejected-V02.png"><img class="after" src="restored-V02.png"></div><input type="range" min="0" max="100" value="50" aria-label="Restoration change"></section>'
a=e['prior_capture']['measurements']['V02']['GPUTime']['median'];z=e['capture']['measurements']['V02']['GPUTime']['median']
body+=f'<p>Matched valley warmed median GPU time: {a:.2f} ms before restoration, {z:.2f} ms after. One paired capture at 1600 × 900, saved v6 settings; not a full-route benchmark.</p>'
body+='<p>Saved-level reload and all placement fingerprints passed, including the new ground detail; 185 protected asset packages unchanged. Game rendering and material checks passed. Historical screenshots predate the detail pass, so close views may contain the intentional new planting.</p><p><a href="original-reference.jpg">Original style reference</a> · <a href="evidence.json">Verification evidence</a></p><script>document.querySelectorAll("input").forEach(r=>r.addEventListener("input",()=>r.previousElementSibling.querySelector(".after").style.clipPath=`inset(0 0 0 ${r.value}%)`))</script>'
(O/'evidence.json').write_text(json.dumps(e,indent=2));(O/'index.html').write_text(body,encoding='utf-8');print(O/'index.html')
