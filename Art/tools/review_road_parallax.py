"""Publish actual before/after, POM control, and sampled camera-sweep evidence."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json,hashlib,shutil,subprocess,html
import imageio_ffmpeg
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RoadParallax';CAP=QA/'Native'
OUT=ROOT/'Art/Export/LidarStudy/CohesiveStyle/ParallaxReview';OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
process=load(CAP/'process.json');plan=process['plan']
before=load(QA/'before.json');h=hashlib.sha256()
with (ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap').open('rb') as f:
 for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
r=dict(ok=process['ok'],map_unchanged=h.hexdigest()==before['map_sha256'],views=plan['views'],motion=dict(frames=plan['motion'],playback_fps=6),scope='Standalone game captures; no performance acceptance')
assert r['ok'] and r['map_unchanged'] and process['exit_code']==0 and process['shader_validation_passed']
for p in CAP.glob('R*.png'):shutil.copy2(p,OUT/p.name)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
full_sources={}
for name in ['R03.png','R03-before.png']:
 src=QA/'Final'/name
 assert src.is_file() and Image.open(src).size==(1600,900)
 shutil.copy2(src,OUT/('full-'+name));full_sources[name]=str(src)
full=Image.new('RGB',(1960,690),'#11201e');fd=ImageDraw.Draw(full)
fd.text((28,14),'LIDAR / GRAVEL WITH HEIGHT-BASED PARALLAX',font=font(30),fill='#eee9d8')
fd.text((28,57),'Actual 1600 × 900 game captures • same camera / lighting • streamed grass differs',font=font(21),fill='#b9c7b9')
for i,(title,name) in enumerate([('BEFORE','full-R03-before.png'),('PARALLAX PASS','full-R03.png')]):
 x=28+i*970;fd.text((x,102),title,font=font(22),fill='#eee9d8');full.paste(Image.open(OUT/name).convert('RGB').resize((934,525),Image.Resampling.LANCZOS),(x,136))
full.save(OUT/'gravel-full.jpg',quality=95)
overview=Image.new('RGB',(1960,1230),'#11201e');draw=ImageDraw.Draw(overview)
draw.text((28,14),'LIDAR / CLOSE GRAVEL AND GROUND RELIEF',font=font(30),fill='#eee9d8')
draw.text((28,57),'888 × 500 game frames • same cameras / lighting • streamed grass differs',font=font(21),fill='#b9c7b9')
for i,(title,name) in enumerate([('GRAVEL / BEFORE','R03-before.png'),('GRAVEL / PARALLAX','R03.png'),('EXPOSED GROUND / BEFORE','R07-before.png'),('EXPOSED GROUND / PARALLAX','R07.png')]):
 x=28+i%2*970;y=102+i//2*560;draw.text((x,y),title,font=font(22),fill='#eee9d8')
 im=ImageOps.contain(Image.open(OUT/name).convert('RGB'),(934,525),Image.Resampling.LANCZOS)
 overview.paste(im,(x+(934-im.width)//2,y+34+(525-im.height)//2))
overview.save(OUT/'overview.jpg',quality=95)
for ident,label in [('R03','GRAVEL'),('R07','EXPOSED GROUND')]:
 canvas=Image.new('RGB',(1960,1230),'#11201e');d=ImageDraw.Draw(canvas)
 d.text((28,14),'LIDAR / '+label+' WITH HEIGHT-BASED PARALLAX',font=font(30),fill='#eee9d8')
 d.text((28,57),'888 × 500 game captures • same camera / lighting • streamed grass differs',font=font(21),fill='#b9c7b9')
 for i,(title,name,crop) in enumerate([('PREVIOUS SURFACE',ident+'-before.png',False),('NEW SURFACE / PARALLAX ON',ident+'.png',False),('NEW DETAIL / PARALLAX OFF',ident+'-normal-only.png',True),('NEW DETAIL / PARALLAX ON',ident+'.png',True)]):
  if ident=='R07' and i==2:title='PARALLAX OFF / OBSCURED BY STREAMED GRASS'
  x=28+i%2*970;y=102+i//2*560;d.text((x,y),title,font=font(22),fill='#eee9d8')
  im=Image.open(OUT/name).convert('RGB')
  if crop:im=im.crop((round(im.width*330/1600),round(im.height*430/900),round(im.width*1264/1600),im.height))
  im=ImageOps.contain(im,(934,525),Image.Resampling.LANCZOS);canvas.paste(im,(x+(934-im.width)//2,y+34+(525-im.height)//2))
 canvas.save(OUT/(ident+'-comparison.jpg'),quality=95)
frames=r.get('motion',{}).get('frames',[])
if frames:
 assert len(frames)==8 and all(Path(p).is_file() for p in frames)
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate','6','-i',str(CAP/'motion-%03d.png'),'-frames:v','8','-c:v','libx264','-threads','2','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'road-sweep.mp4')],check=True)
cards=''.join('<figure><figcaption>'+html.escape(v['view']+' — '+v['title'])+'</figcaption><a href="'+v['view']+'.png"><img src="'+v['view']+'.png"></a></figure>' for v in r['views'])
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LiDAR surface parallax</title><style>body{background:#11201e;color:#eee9d8;font:17px/1.6 system-ui;margin:28px}h1{font-size:30px}a{color:#bad8b5}.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}figure{margin:0}img,video{width:100%;display:block}figcaption{padding:10px 0}p{max-width:1100px}select{padding:10px;background:#293d34;color:white}td,th{text-align:left;padding:10px;border-bottom:1px solid #536453}code{color:#d5d6a5}@media(max-width:850px){.grid{grid-template-columns:1fr}}</style><h1>Stone relief at road level</h1><p>Actual Play-in-Editor game views from the saved LiDAR map. The new near-field material traces the view through a height map, samples its detail at the intersection, and derives normals from the same height. Gravel uses the existing DG1 stone bake; soil keeps its native pigment and adds the existing peat height and cavity detail. The RDR2 request guides the sense of surface depth; this is not a claim about RDR2’s implementation.</p><label>Compare <select id="view"><option value="R03">Gravel</option><option value="R07">Exposed shoulder</option></select></label> <label>Left image <select id="mode"><option value="-before">Previous surface</option><option value="-normal-only">New detail with parallax OFF</option></select></label><div class="grid"><figure><figcaption id="left-label">Previous surface</figcaption><a id="left-link" href="R03-before.png"><img id="left" src="R03-before.png"></a></figure><figure><figcaption>New detail with parallax ON</figcaption><a id="right-link" href="R03.png"><img id="right" src="R03.png"></a></figure></div><h2>Short lateral camera sweep</h2><video controls loop muted preload="metadata" src="road-sweep.mp4"></video><p>48 actual rendered camera positions, played at 12 fps. This is a sampled visual check, not measured real-time frame rate.</p><h2>Per-map controls</h2><p>Open <code>LidarStudy_DistanceStyle → Profile → Surface Detail</code>. The active LiDAR profile is <code>DA_Lidar_Evergreen</code>. Duplicate it for independent map tuning. These settings do not change the fog or palette.</p><table><tr><th>Control</th><th>Current value / use</th></tr><tr><td>Surface Detail Strength</td><td>1; set 0 to restore the previous surface shading.</td></tr><tr><td>Surface Parallax Strength</td><td>1; set 0 to isolate the normal-and-texture treatment without view-ray depth.</td></tr><tr><td>Gravel Depth / Ground Depth</td><td>1.6 cm / 2.2 cm.</td></tr><tr><td>Gravel Tile / Ground Tile</td><td>140 cm / 150 cm; controls feature size.</td></tr><tr><td>Surface Near / Far</td><td>6 m / 18 m; smooth fade back to the existing materials.</td></tr><tr><td>Surface Max Steps</td><td>24; adaptive view-angle samples plus four intersection refinements.</td></tr></table><p>This is optical surface detail: collision and silhouettes remain unchanged. Live worked mud, authored logging-track materials, river detail and steep rock faces retain their existing paths. Performance timings remain unverified while the GPU is shared.</p><h2>Other road checks</h2><div class="grid">'''+cards+'''</div><p><a href="evidence.json">Validation evidence</a> · <a href="https://dev.epicgames.com/documentation/unreal-engine/using-bump-offset-in-unreal-engine?lang=en-US">Epic: height-based parallax and texture coordinates</a> · <a href="../Review/index.html">Valley style and colour controls</a></p><script>function update(){const v=document.getElementById('view').value,m=document.getElementById('mode').value;for(const [id,name] of [['left',v+m+'.png'],['right',v+'.png']]){document.getElementById(id).src=name;document.getElementById(id+'-link').href=name}document.getElementById('left-label').textContent=m==='-before'?'Previous surface':'New detail with parallax OFF'}document.getElementById('view').onchange=update;document.getElementById('mode').onchange=update;</script>'''
page=page.replace('Actual Play-in-Editor game views','Actual standalone game views').replace('48 actual rendered camera positions, played at 12 fps.','Eight actual rendered camera positions, played at 6 fps. This limited sweep checks gross texture movement; high-frame-rate temporal stability remains unverified.')
page=page.replace('Actual standalone game views from the saved LiDAR map.','Actual standalone game views from the saved LiDAR map. Native frames are 888 × 500 on this machine; each comparison uses matching resolution. Grass streaming changed vegetation between captures. The exposed-shoulder parallax-OFF control is obscured by grass and is inconclusive; compare the visible bare ground in the previous-surface and parallax-ON pair. These are material checks, not a validated vegetation comparison. ')
page=page.replace('<h2>Short lateral camera sweep</h2>','<h2>Full-resolution gravel comparison</h2><a href="gravel-full.jpg"><img src="gravel-full.jpg"></a><p><a href="full-R03-before.png">1600 × 900 before</a> · <a href="full-R03.png">1600 × 900 parallax pass</a>. These completed stills were retained from the high-resolution run, which was stopped after capture stalls.</p><h2>Short lateral camera sweep</h2>')
(OUT/'index.html').write_text(page,encoding='utf-8')
e=dict(capture=r,process=process,install=load(QA/'install.result.json'),build='GrandTourEditor Development succeeded',performance_verified=False,full_visual_validation_passed=False,native_frame_resolution=[888,500],visual_limitations=['Vegetation streaming changed grass between captures.','R07 normal-only control is obscured by streamed grass; soil POM isolation inconclusive.','Eight-position sweep is insufficient to validate high-frame-rate temporal stability.'],full_resolution_stills=full_sources,earlier_attempt='Earlier longer captures deliberately stopped after stalls. Retained full-resolution gravel stills are identified separately; the complete control and sampled-motion run uses native frames.',sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.png')})
(OUT/'evidence.json').write_text(json.dumps(e,indent=2))
print(OUT/'R03-comparison.jpg')
