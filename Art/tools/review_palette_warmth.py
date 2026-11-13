"""Package unretouched in-game frames from the muted and warm-light profiles."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json,shutil,hashlib
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/PaletteWarmth';CAP=QA/'Capture';OUT=ROOT/'Art/Export/LidarStudy/CohesiveStyle/WarmthReview';OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
r=load(CAP/'process.json');assert r['ok'] and r['shader_validation_passed']
install=load(ROOT/'Saved/LidarAuthoringQA/PaletteRefinement/install.json');assert install['ok']
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
for v in r['plan']['views']:
 ident=v['id'];board=Image.new('RGB',(1832,670),'#18201c');d=ImageDraw.Draw(board)
 d.text((20,12),'LIDAR / WARM LIGHT, COOL SHADOWS',font=font(28),fill='#e5e2d3')
 d.text((20,53),v['title']+' / actual game frames, same camera and rendering settings',font=font(19),fill='#b9c2b2')
 for i,(suffix,title) in enumerate([('before','BEFORE / MUTED PALETTE'),('after','AFTER / WARMER SUNLIT COLOURS')]):
  name=ident+'-'+suffix+'.png';shutil.copy2(CAP/name,OUT/name)
  x=20+i*906;d.text((x,96),title,font=font(20),fill='#e5e2d3')
  im=Image.open(OUT/name).convert('RGB');assert im.size==(888,500)
  board.paste(ImageOps.contain(im,(886,500)),(x,136))
 board.save(OUT/(ident+'-comparison.jpg'),quality=95)
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LiDAR warm light refinement</title>
<style>body{margin:28px;background:#18201c;color:#e5e2d3;font:17px/1.6 system-ui}p{max-width:1100px}a{color:#daca9a}img{max-width:100%}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}select{padding:10px}td,th{text-align:left;padding:10px;border-bottom:1px solid #536453}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>
<h1>Warm light, cool shadows</h1><p>Lit canopy and clearing colours are brighter and warmer. A selective upper-tone finish restores warmth and a little chroma to nearby highlights while protecting low shadow values. Its effect fades out into the distance and excludes the sky. The cooler shadow, sky and haze colours are retained.</p>
<label>Compare <select id="view"><option value="valley">River valley</option><option value="road">Roadside materials</option><option value="leaves">Sunlit broad leaves</option></select></label>
<div class="grid"><div><h3>Previous muted pass</h3><img id="before" src="valley-before.png"></div><div><h3>Warmer sunlit colours</h3><img id="after" src="valley-after.png"></div></div>
<p>Unretouched 888 × 500 game captures, 100% screen percentage. Each pair shares its camera, exposure configuration and rendering settings. Vegetation and temporal rendering can vary slightly between frames.</p>
<h2>Per-map tuning</h2><p>Open the map's Distance Style controller and its Profile. The active LiDAR profile is <code>DA_Lidar_Evergreen</code>. Duplicate the profile for another map and assign it to that map's controller.</p>
<table><tr><th>Control</th><th>Value</th><th>Effect</th></tr>
<tr><td>Palette Finish → Sunlight Warmth</td><td>0.65</td><td>Warmth and modest chroma restoration in upper tones.</td></tr>
<tr><td>Palette Finish → Sunlight Lift</td><td>0.18</td><td>Brightness lift in upper tones; dark values are protected.</td></tr>
<tr><td>Palette Finish → Highlight Compression</td><td>0.10</td><td>Gentler highlight suppression, previously 0.18.</td></tr>
<tr><td>Art Direction → Sunlit Colour / Clearing Colour</td><td>Map-specific</td><td>Material colours for lit canopy and clearings.</td></tr></table>
<p>Shadow colours, fog intensity and fog distances retain the previous values. The upper-tone finish uses luminance, not a direct-light visibility test; the material palette provides the lit/shaded colour separation. The previous muted profile is preserved as <code>DA_Lidar_MutedPalette</code> for complete rollback.</p>
<p>Preferred broad leaves, planting and road parallax retained. No additional render pass or texture sample; the depth input reuses the existing haze graph. Build and shader checks passed. GPU timings remain unverified.</p>
<p><a href="valley-comparison.jpg">Valley board</a> / <a href="road-comparison.jpg">Road board</a> / <a href="leaves-comparison.jpg">Leaf board</a> / <a href="evidence.json">Validation evidence</a></p>
<script>document.getElementById('view').onchange=function(){for(let suffix of ['before','after'])document.getElementById(suffix).src=this.value+'-'+suffix+'.png'}</script>'''
(OUT/'index.html').write_text(page,encoding='utf-8')
(OUT/'evidence.json').write_text(json.dumps(dict(capture=r,install=install,performance_verified=False,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.png')}),indent=2))
print(OUT)
