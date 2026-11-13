"""Actual matched-camera review of the distance-lighting revision."""
from pathlib import Path
import json, shutil, sys, argparse
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path('C:/GrandTour')
p=argparse.ArgumentParser();p.add_argument('--before',default='canopy-depth-after');p.add_argument('--after',default='canopy-contrast-after');p.add_argument('--out',default='ContrastReview');p.add_argument('--surface',action='store_true');args=p.parse_args()
OUT=ROOT/'Art/Export/LidarStudy/CanopyDepth'/args.out
OUT.mkdir(exist_ok=True)
SHOTS=ROOT/'Saved/LidarAuthoringQA/RS7'
REF=ROOT/'Art/References/ValleyDepthCoverage'
sys.path.insert(0,str(ROOT/'Art/tools'))
from measure_perceived_detail import run
before=run(args.before);after=run(args.after)
for v in ['V01','V02','V03','G01']:
 for stage,label in [('before',args.before),('after',args.after)]:
  shutil.copy2(SHOTS/f'{label}-{v}.png',OUT/f'{stage}-{v}.png')
for f in ['ripia-terrain.jpg','pareraho.jpg','original-scene.jpg']:
 shutil.copy2(REF/f,OUT/f)
lighting=json.loads((ROOT/'Saved/LidarAuthoringQA/CanopyDepth/lighting-result.json').read_text())
assert lighting['ok'] and lighting['protected_packages']==185
(OUT/'evidence.json').write_text(json.dumps(dict(before=before,after=after,lighting=lighting),indent=2))
board=Image.new('RGB',(1800,1240),'#101a1c');d=ImageDraw.Draw(board)
def text(x,y,s,n=24):d.text((x,y),s,font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n),fill='#e9efea')
def pic(f,box,crop=None):
 im=Image.open(OUT/f).convert('RGB')
 if crop:im=im.crop(crop)
 im=ImageOps.contain(im,(box[2],box[3]));board.paste(im,(box[0]+(box[2]-im.width)//2,box[1]+(box[3]-im.height)//2))
text(24,15,'LIDAR FOREST | '+('Shadows across the canopy surface' if args.surface else 'Stronger distant crown lighting'),32)
text(24,65,'Same game camera and exposure. '+('Crown shadows on geometry and distant trees; haze pushed back.' if args.surface else 'Warmer lit tops; deeper, cooler canopy shade.'),23)
text(24,111,'PREVIOUS PASS');text(920,111,'CURRENT GAME')
pic('before-V02.png',(24,150,856,482));pic('after-V02.png',(920,150,856,482))
text(24,650,'MATCHED DETAIL — opposite slope',21)
pic('before-V02.png',(24,689,856,245),(920,240,1520,412))
pic('after-V02.png',(920,689,856,245),(920,240,1520,412))
text(24,957,'DEPTH REFERENCE / Pareraho',20);pic('pareraho.jpg',(24,997,540,220))
text(630,957,'COVERAGE / Lower Ripia',20);pic('ripia-terrain.jpg',(630,997,540,220))
text(1230,957,'COLOUR / Original reference',20);pic('original-scene.jpg',(1230,997,540,220))
board.save(OUT/'comparison.jpg',quality=95)
body='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LiDAR distant crown lighting</title><style>body{max-width:1600px;margin:auto;padding:24px;background:#101a1c;color:#e9efea;font:17px/1.5 system-ui}a{color:#afdabc}img{width:100%}.pair{position:relative;aspect-ratio:16/9}.pair img{position:absolute;inset:0}.after{clip-path:inset(0 0 0 50%)}input{width:100%}section{margin:35px 0}td,th{padding:8px 20px;text-align:left}</style><h1>Stronger light above, deeper shade below</h1><p>Actual game views with unchanged camera, sun, exposure and quality preset. The shader strengthens the separation between sun-facing upper crowns and shaded interiors, fading in from 150 to 400 metres.</p><img src="comparison.jpg">'''
for v,title in [('V02','Across the valley'),('V01','Down into woodland'),('V03','Long valley view'),('G01','Close riverbank check')]:
 body+=f'<section><h2>{title}</h2><p>Previous pass on the left; current on the right.</p><div class="pair"><img src="before-{v}.png"><img class="after" src="after-{v}.png"></div><input type="range" value="50" min="0" max="100" aria-label="Before and after {v}"><a href="after-{v}.png">Full-resolution current capture</a></section>'
body+='<h2>Warmed median GPU time</h2><p>One paired capture at 1600 × 900, saved v6 settings; screenshot stalls excluded.</p><table><tr><th>View</th><th>Previous</th><th>Current</th></tr>'
for v in ['V01','V02','V03','G01']:
 b=before['measurements'][v]['GPUTime']['median'];a=after['measurements'][v]['GPUTime']['median']
 body+=f'<tr><td>{v}</td><td>{b:.2f} ms</td><td>{a:.2f} ms</td></tr>'
body+='''</table><p>The distant lighting still uses the saved sun direction and requires rebuilding for changes to the sun, planting or terrain. This revision changes distance materials; tree placements and the near plant materials are preserved.</p><p>References: <a href="https://www.pfhv.org.nz/predator-free-groups/predator-free-pareraho/">Pareraho</a> · <a href="https://www.ahimanawa.co.nz/private-hunting-block/lower-ripia">Lower Ripia</a> · <a href="original-scene.jpg">Supplied original</a>. <a href="evidence.json">Capture evidence</a>.</p><script>document.querySelectorAll('input').forEach(r=>r.addEventListener('input',()=>r.previousElementSibling.querySelector('.after').style.clipPath=`inset(0 0 0 ${r.value}%)`))</script>'''
if args.surface:
 body=body.replace('Stronger light above, deeper shade below','Shadows across the canopy surface')
 body=body.replace('The shader strengthens the separation between sun-facing upper crowns and shaded interiors, fading in from 150 to 400 metres.','A canopy shadow-height field shades each visible surface point, including the regular foliage geometry and depth-reprojected distance trees. It fades in from 120 to 360 metres. Distant haze now starts at 650 metres and is lighter, preserving the middle slopes.')
 body=body.replace('This revision changes distance materials; tree placements and the near plant materials are preserved.','This revision uses a separate forest foliage material; tree placements and the approved bank assets are preserved. The shadow field approximates crown envelopes, not individual leaves; it needs rebaking after planting, terrain or sun changes.')
 qa=ROOT/'Saved/LidarAuthoringQA/CanopyDepth'
 evidence=json.loads((OUT/'evidence.json').read_text())
 for key,file in [('surface_materials','surface-shadow-materials.json'),('installation','install-result.json'),('saved_assets','assets-verified.json')]:
  evidence[key]=json.loads((qa/file).read_text());assert evidence[key]['ok']
 assert evidence['saved_assets'].get('surface_shadows_verified')
 evidence['fog']=json.loads((ROOT/'Saved/LidarAuthoringQA/DistanceHaze/install.json').read_text())
 movie=qa/'surface-valley.mp4'
 if movie.exists():
  evidence['motion']=json.loads((SHOTS/'canopy-surface-valley-capture.json').read_text(encoding='utf-8-sig'))
  assert evidence['motion']['exit_code']==0 and evidence['motion']['render_validation_passed'] and evidence['motion']['frames']==72
  shutil.copy2(movie,OUT/'valley.mp4')
  body+='<section><h2>Movement check</h2><video style="width:100%" controls muted loop src="valley.mp4"></video><p>Actual game viewport frames, captured for a 12 fps review video. This is not a frame-rate benchmark.</p></section>'
 (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2))
(OUT/'index.html').write_text(body,encoding='utf-8')
print(OUT/'index.html')
