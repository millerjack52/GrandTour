"""Arrange unretouched game captures with the selected reference."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,shutil,html
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7';OUT=ROOT/'Art/Export/LidarStudy/FirewatchStyle/Review';OUT.mkdir(parents=True,exist_ok=True)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
ref=ROOT/'Art/References/StylizedLongViews/firewatch.jpg'
shutil.copy2(ref,OUT/'firewatch.jpg')
for preset in ['subtle','medium','strong']:
 for view in ['V01','V02','V03','G01']:
  src=QA/f'firewatch-{preset}-{view}.png'
  if src.exists():shutil.copy2(src,OUT/src.name)
for view in ['V01','V02','V03','G01']:
 src=QA/f'far-ridge-haze-{view}.png'
 if src.exists():shutil.copy2(src,OUT/src.name)

def board(view):
 canvas=Image.new('RGB',(1960,1250),'#101e20');d=ImageDraw.Draw(canvas)
 d.text((28,14),'LIDAR / FIREWATCH DIRECTION — FIRST PASS',font=font(32),fill='#edf3e8')
 d.text((28,60),'Actual game captures • identical camera, exposure and vegetation • independent style and haze controls',font=font(20),fill='#adbfba')
 rows=[('FIREWATCH REFERENCE / Campo Santo','firewatch.jpg'),('SUBTLE / style 35% · haze 38%',f'firewatch-subtle-{view}.png'),('MEDIUM / style 72% · haze 58%',f'firewatch-medium-{view}.png'),('STRONG / style 100% · haze 76%',f'firewatch-strong-{view}.png')]
 for i,(title,name) in enumerate(rows):
  x=28+(i%2)*970;y=110+(i//2)*565
  d.text((x,y),title,font=font(23),fill='#edf3e8');im=Image.open(OUT/name).convert('RGB');im=im.resize((934,525),Image.Resampling.LANCZOS);canvas.paste(im,(x,y+36))
 canvas.save(OUT/f'comparison-{view}.jpg',quality=94)
for view in ['V02','V03','G01']:board(view)

cards=''.join(f'<figure><figcaption>{label}</figcaption><a id="link-{key}" href="{name}"><img id="{key}" src="{name}"></a></figure>' for key,label,name in [('reference','Firewatch — selected reference','firewatch.jpg'),('subtle','Subtle — 35% style / 38% haze','firewatch-subtle-V02.png'),('medium','Medium — 72% style / 58% haze','firewatch-medium-V02.png'),('strong','Strong — 100% style / 76% haze','firewatch-strong-V02.png'),('baseline','Previous approved pass','far-ridge-haze-V02.png')])
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LiDAR / Firewatch first pass</title><style>body{margin:28px;background:#101e20;color:#edf3e8;font:16px system-ui}h1{font-size:28px}p{max-width:1000px;line-height:1.6}a{color:#a9d5c8}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}figure{margin:0}figcaption{padding:12px 0}img{width:100%;display:block}select{padding:9px;background:#203738;color:white;border:1px solid #7e9e93}table{border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #405552}code{color:#bfd9b9}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>
<h1>LiDAR / Firewatch first pass</h1><p>Unretouched standalone game captures at 1600 × 900. All versions use the same cameras, exposure, tree placement and graphics settings. The reference is a different game and composition; compare its broad colour groups, silhouettes and depth layering.</p>
<label>Game camera <select id="view"><option value="V02">V02 — main valley</option><option value="V01">V01 — wide valley</option><option value="V03">V03 — second long view</option><option value="G01">G01 — ground protection view</option></select></label>
<div class="grid">'''+cards+'''</div>
<p>Reference: Campo Santo, <a href="https://www.pcgamer.com/firewatch-gallery-a-colorful-tour-of-shoshone-national-forest/">PC Gamer’s Firewatch gallery</a>.</p>
<h2 id="tuning">Adjust a map</h2><p>Select <code>LidarStudy_DistanceStyle</code> in the World Outliner. Open its <code>Profile</code> asset. Changes preview live with viewport Realtime enabled; otherwise press Apply Profile on the controller. Save the profile asset to retain edits. For another map using the style materials, duplicate the profile and assign it to that map’s own Distance Style Controller. Use one controller per persistent map, and assign that map’s sun in Bindings. Do not share one editable profile between maps that need independent art direction.</p>
<table><tr><th>Control</th><th>Effect</th></tr><tr><td>Strength, Start Metres, Full Metres</td><td>How much and how far away the canopy becomes simpler.</td></tr><tr><td>Forest Colour / Shadow Colour</td><td>The broad distant canopy palette.</td></tr><tr><td>Ground Tint</td><td>Adjusts distant open terrain; woodland ground blends into the forest palette.</td></tr><tr><td>Normal Simplification</td><td>Reduces fine leaf lighting while retaining broad slope lighting.</td></tr><tr><td>Patch Variation / Patch Size Metres</td><td>World-locked variation across forest groups.</td></tr><tr><td>Haze Colour / Intensity / Start / Full Metres</td><td>Independent far-distance haze. Existing low forest and river fog remains separate.</td></tr></table>
<p>Assets are in <code>/Game/GrandTour/ArtTests/LidarStudy/FirewatchStyle</code>: <code>DA_Lidar_Subtle</code>, <code>DA_Lidar_Medium</code>, and <code>DA_Lidar_Strong</code>.</p><p>Medium is the saved starting point. Set Strength to zero to remove the canopy treatment; set Haze Intensity to zero to disable this additional distant haze. The haze colour uses the current SDR presentation. The terrain lighting field is specific to this LiDAR map; a new terrain requires its own field and bounds.</p>
<h2>Validation</h2><p>Build, saved-map reload, three runtime preset switches, shader validation and independent profile colour/fog edits passed. The 185 protected source assets, tree transforms, bank planting and ground geometry remain unchanged. The existing low forest/river fog remains separate.</p><p>On the RTX 4050 Laptop, at 1600 × 900 with the existing 75% TSR preset, Medium added 0.16–0.27 ms of median GPU time across the three valley cameras versus the previous capture. Strong added 0.17–0.61 ms in the first run and 0.05–0.14 ms in the repeat. The first Strong run exceeded the provisional 0.3 ms target; the repeat met it. These are capture measurements, not a frame-rate guarantee.</p><p><a href="validation.json">Capture hashes and validation results</a> · <a href="medium-motion.mp4">Medium valley camera motion</a></p><script>document.querySelector('#view').onchange=e=>{for(const key of ['baseline','subtle','medium','strong']){let name=(key==='baseline'?'far-ridge-haze':'firewatch-'+key)+'-'+e.target.value+'.png';document.getElementById(key).src=name;document.getElementById('link-'+key).href=name}}</script>'''
(OUT/'index.html').write_text(page,encoding='utf-8')
print(OUT/'comparison-V02.jpg')
