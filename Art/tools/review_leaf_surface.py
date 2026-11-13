"""Publish unretouched game views and close crops for the leaf treatment."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json,hashlib,shutil
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/LeafSurface';CAP=QA/'Capture'
OUT=ROOT/'Art/Export/LidarStudy/CohesiveStyle/LeafReview';OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
r=load(CAP/'process.json');assert r['ok'] and r['shader_validation_passed']
install=load(QA/'install.json');assert install['ok']
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
for name in r['plan']['images']:shutil.copy2(CAP/name,OUT/name)
for v in r['plan']['views']:
 ident=v['id'];board=Image.new('RGB',(1832,1144),'#11201e');d=ImageDraw.Draw(board)
 d.text((20,12),'LIDAR / '+v['title'].upper(),font=font(29),fill='#eee9d8')
 size=Image.open(OUT/(ident+'-before.png')).size
 d.text((20,53),f'Actual game frames {size[0]} × {size[1]} • same camera and render settings',font=font(20),fill='#becbbd')
 for i,label in enumerate(['BEFORE / ANGULAR SPRAYS','AFTER / ROUNDED LEAFLETS']):
  x=20+i*906;d.text((x,90),label,font=font(21),fill='#eee9d8')
  im=Image.open(OUT/(ident+('-before' if i==0 else '-after')+'.png')).convert('RGB')
  board.paste(ImageOps.contain(im,(886,500)),(x,125))
  crop=im.crop((round(im.width*.24),round(im.height*.15),round(im.width*.73),round(im.height*.65)))
  crop=ImageOps.contain(crop,(886,450),Image.Resampling.LANCZOS)
  d.text((x,647),'MATCHED DETAIL CROP',font=font(19),fill='#becbbd');board.paste(crop,(x,680))
 board.save(OUT/(ident+'-comparison.jpg'),quality=95)
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LiDAR leaves</title><style>body{margin:30px;background:#11201e;color:#eee9d8;font:17px/1.6 system-ui}p{max-width:1050px}a{color:#bad8b5}img{max-width:100%}select{padding:10px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><h1>Close tree leaves</h1><p>The existing tree sprays are opaque folded diamonds, with each triangle shaded as a flat face. This first pass adds rounded connected leaflet cutouts, curved per-leaf shading, restrained midrib detail and thickness-dependent transmitted light. No tree geometry or planting was changed. The material fades to its previous outputs from 16 to 50 metres; the distant canopy shaders and palette remain intact.</p><p>Actual standalone game frames, 888 × 500 native output at 100% screen percentage. Both sides use identical camera and renderer settings. Grass can stream between frames; judge tree foliage, not changes in ground planting. “Before” disables the new treatment in the same masked material, preserving its original colour and normal outputs; this is a visual control, not an opaque-versus-masked performance comparison.</p><label>View <select id="view"><option value="close">Close leaf sprays</option><option value="road">Roadside crown</option><option value="sunlit" selected>Upper crown / sunward inspection</option></select></label><div class="pair"><div><h3>Before</h3><a id="b-link" href="sunlit-before.png"><img id="b" src="sunlit-before.png"></a></div><div><h3>After</h3><a id="a-link" href="sunlit-after.png"><img id="a" src="sunlit-after.png"></a></div></div><h2>Tuning</h2><p>Open <code>/Game/GrandTour/ArtTests/LidarStudy/CohesiveStyle/MI_EvergreenFoliage</code>, then enable overrides in <b>Leaf Surface</b>. <b>LeafStrength</b> controls the whole treatment (0 restores the earlier appearance), <b>LeafCurvature</b> controls rounded lighting, <b>LeafTransmission</b> controls transmitted colour, and <b>LeafNearCm / LeafFarCm</b> control the distance fade. Defaults are 1 / 0.85 / 0.32 / 1600 cm / 5000 cm. Duplicate the instance for other maps.</p><p>This adds masked pixel shading, not extra triangles. GPU cost and motion stability are unverified while Skate shares the GPU. It does not replace the underlying folded spray geometry, so extreme edge-on views can still reveal thin cards.</p><p><a href="close-comparison.jpg">Close comparison and crops</a> · <a href="road-comparison.jpg">Roadside comparison and crops</a> / <a href="sunlit-comparison.jpg">Sunward crown comparison</a> · <a href="evidence.json">Validation</a> · <a href="https://dev.epicgames.com/documentation/unreal-engine/shading-models-in-unreal-engine">Epic: Two Sided Foliage shading</a></p><script>document.getElementById('view').onchange=function(){for(const [id,suffix] of [['b','before'],['a','after']]){let p=this.value+'-'+suffix+'.png';document.getElementById(id).src=p;document.getElementById(id+'-link').href=p}}</script>'''
(OUT/'index.html').write_text(page,encoding='utf-8')
e=dict(install=install,capture=r,build='GrandTourEditor Development passed',performance_verified=False,motion_verified=False,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.png')})
(OUT/'evidence.json').write_text(json.dumps(e,indent=2))
print(OUT)
