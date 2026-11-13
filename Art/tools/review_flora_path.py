from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,csv,hashlib,statistics,html
ROOT=Path('C:/GrandTour');O=ROOT/'Art/Export/LidarStudy/FloraPath'
build=json.loads((O/'build-report.json').read_text());capture=json.loads((O/'capture-report.json').read_text(encoding='utf-8-sig'))
bark=json.loads((O/'bark-report.json').read_text());soften=json.loads((O/'soften-report.json').read_text());motion=json.loads((O/'motion-report.json').read_text())
assert build['ok'] and capture['ok'] and bark['ok'] and soften['ok'] and motion['ok']
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
canvas=Image.new('RGB',(1680,620),'#152322');draw=ImageDraw.Draw(canvas)
draw.text((24,20),'FOREST PATH / reference and actual Unreal game view',font=font(29),fill='#f0eddb')
draw.text((24,65),'Original scene and artwork: Casey Sheep / Flora Paint. Isolated Unreal conversion study.',font=font(18),fill='#b3c4bf')
for x,label,path in [(24,'YOUR REFERENCE / image 2',O/'reference-image2.png'),(852,'UNREAL / normal game renderer',O/'unreal-path.png')]:
 draw.text((x,112),label,font=font(20),fill='#ede5c5');im=Image.open(path).convert('RGB');canvas.paste(im.resize((804,402),Image.Resampling.LANCZOS),(x,150))
draw.text((24,575),'1600 × 800 game capture · TSR · map-local lighting and fog · woodland unchanged',font=font(19),fill='#b3c4bf')
canvas.save(O/'comparison.png')
barkboard=Image.new('RGB',(1680,620),'#152322');d=ImageDraw.Draw(barkboard)
d.text((24,20),'BARK DETAIL / same Unreal camera, lighting and exposure',font=font(29),fill='#f0eddb')
d.text((24,65),'Dedicated bark texture space; soft foliage coverage retained. Actual game captures.',font=font(18),fill='#b3c4bf')
for x,label,path in [(24,'BEFORE / shared bark and leaf atlas',O/'bark-before.png'),(852,'AFTER / dedicated bark atlas',O/'unreal-path.png')]:
 d.text((x,112),label,font=font(20),fill='#ede5c5');barkboard.paste(Image.open(path).convert('RGB').resize((804,402),Image.Resampling.LANCZOS),(x,150))
d.text((24,575),'Same geometry and foliage UVs. Seven shared 2K bark textures; no additional bark shader samples.',font=font(18),fill='#b3c4bf');barkboard.save(O/'bark-comparison.png')
protected=[]
for r in json.loads((O/'protected-before.json').read_text()):
 with open(r['file'],'rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 assert h==r['sha256'],r['file'];protected.append(dict(**r,unchanged=True))
metrics={}
if (O/'capture.csv').exists():
 with (O/'capture.csv').open() as f:rows=list(csv.DictReader(f))
 for label,start,end in [('reference_view',45,105),('without_volumetrics',285,345)]:
  values={}
  for key in ['FrameTime','GPUTime','RenderThreadTime','RHI/DrawCalls','RHI/PrimitivesDrawn','GPUSceneInstanceCount','TextureStreaming/WantedMips','TextureStreaming/StreamingPool','TextureStreaming/DesiredDataLoadedPercent','GPUMem/LocalUsedMB','GPUMem/LocalBudgetMB']:
   nums=[]
   for r in rows[start:end]:
    try:nums.append(float(r[key]))
    except (ValueError,KeyError,TypeError):pass
   if nums:values[key]=round(statistics.median(nums),3)
  metrics[label]=values
manifest=json.loads((O/'scene-manifest.json').read_text())
validation={'ok':True,'woodland_unchanged':True,'visual_match_passed':False,'protected':protected,'instances':build['instances'],'unique_meshes':len(build['meshes']),'tree_variants':sum('Tree' in m['name'] for m in build['meshes']),'tree_instances':sum('Tree' in p['mesh'] for p in manifest['instances']),'base_triangles':sum(m['triangles'] for m in build['meshes']),'measurements':metrics,'performance_verified':False,'performance_note':'Skate shares the GPU. Figures are observed diagnostic medians, not an isolated benchmark. Screenshot frames and initial warm-up excluded. Fog comparisons are sequential and can be confounded by changing GPU load.','wind_verified':False,'source_attribution':manifest['attribution'],'production_rollout':False,'bark_repack_verified':bark['ok'],'motion_capture_verified':motion['ok'],'soft_coverage_shader_verified':soften['ok']}
(O/'validation.json').write_text(json.dumps(validation,indent=2))
stats=''.join('<tr><td>'+html.escape(k)+'</td><td>'+str(v)+'</td></tr>' for k,v in metrics.get('reference_view',{}).items())
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Flora Paint / forest path study</title><style>
*{box-sizing:border-box}body{max-width:1720px;padding:28px;margin:auto;background:#152322;color:#eeeada;font:16px/1.6 system-ui}h1,h2{font-weight:500}p{max-width:1100px;color:#bdcbc5}a{color:#ddcf9e}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}img,video{width:100%;display:block}figure{margin:0}figcaption{padding:10px 0}.note{border-left:3px solid #d4be7d;background:#263732;padding:16px 22px}td,th{padding:6px 15px;border-bottom:1px solid #42554b;text-align:left}code{overflow-wrap:anywhere}@media(max-width:850px){.pair{grid-template-columns:1fr}body{padding:16px}}</style>
<h1>Forest path / actual Unreal study</h1><p>Based on your second reference and its purchased bonus project. Original scene, artwork and assets by <strong>Casey Sheep / Flora Paint</strong>. The author’s path, planting and camera provide the composition; this is an isolated Unreal conversion and rendering study.</p>
<div class="pair"><figure><img src="reference-image2.png" alt="User's Flora Paint forest path reference"><figcaption>Your reference / image 2</figcaption></figure><figure><img src="unreal-path.png" alt="Actual Unreal forest path capture"><figcaption>Actual Unreal game capture / 1600 × 800 / TSR</figcaption></figure></div>
<p><a href="comparison.png">Open side-by-side sheet</a> · <a href="unreal-path.png">Open full-resolution game capture</a></p>
<p class="note">Visual status: first study, not an exact reference match. Softer coverage and clearer bark are visible, but foreground trunk readability and the reference's warm/cool lighting separation still need work. Build and capture checks are not visual approval.</p><h2>Bark detail correction</h2><img src="bark-comparison.png" alt="Same-camera comparison of bark before and after dedicated atlas correction"><p>The trunks now have dedicated texture space instead of sharing it with thousands of leaf faces. Leaf UVs and geometry bounds are unchanged. Seven shared 2K bark atlases replace the bark colour sample; they add texture memory but no extra texture samples per bark pixel.</p><h2>Camera and atmosphere checks</h2><div class="pair"><figure><img src="unreal-path-near.png"><figcaption>Nearby camera / foreground planting and path</figcaption></figure><figure><img src="unreal-path-no-volumetrics.png"><figcaption>Same reference camera / volumetric fog disabled; height haze remains</figcaption></figure></div>
<h2>Moving camera</h2><video controls preload="metadata" src="camera-check.mp4" poster="unreal-path.png"></video><p>Actual-game camera movement, encoded at 15 fps for review. Playback speed is not measured game performance. Wind is frozen in this composition study.</p>
<h2>Performance review</h2><p class="note">Performance remains unverified because Skate is sharing the GPU. These diagnostic measurements do not establish a frame-rate guarantee. The woodland has not been changed.</p>
<p>Repeated trees and plants use shared instanced meshes. Trees have three LODs; small plants cull between 45 and 65 metres. Painted masks use compressed BC4 textures capped at 2048, rather than the previous uncompressed 4096 masks. Small litter does not cast shadows; larger foreground plants do. Volumetric fog uses a 16-pixel, 64-depth-slice grid for this capture.</p><table><tr><th>Observed diagnostic</th><th>Median</th></tr>'''+stats+'''</table>
<p>FrameTime, GPUTime and RenderThreadTime are milliseconds. Counts and memory fields retain the engine CSV units. Initial warm-up and screenshot frames are excluded. A clean benchmark, dense-map scaling, distant LOD transitions, wind and longer motion review remain required before rollout.</p>
<h2>What came from the pack</h2><p>Leaf masks were imported directly. Colours were baked from the original Blender graphs. The source tree shaders do not connect tangent-space normal maps; mesh normals were imported. Unreal's upward-blended foliage normals and Two Sided Foliage transmission are approximations of the author's shader, rather than an exact port. Two bark variants use repaired bake coordinates.</p><h2>Editable study</h2><p>Level: <code>/Game/GrandTour/ArtTests/FloraPath/L_FloraPath</code>. Material instances expose palette tint, coverage, normal blend and transmission. PaintedEdgeSoftness controls the soft painted mask edges resolved through TSR; shadow coverage uses a separate stable mask. The study disables dynamic GI locally and preserves authored fog with the opt-in GTWeatherUnmanaged tag. The map’s sun, exposure and fog settings are in <a href="look-settings.json">look-settings.json</a>.</p>
<p><a href="validation.json">Validation and diagnostic figures</a> · <a href="build-report.json">Build inventory</a> · <a href="capture-report.json">Capture checks</a> · <a href="Implementation-notes.txt">Implementation and remaining checks</a></p></html>'''
(O/'index.html').write_text(page,encoding='utf-8')
print(json.dumps({k:v for k,v in validation.items() if k not in ['protected','source_attribution']},indent=2))
