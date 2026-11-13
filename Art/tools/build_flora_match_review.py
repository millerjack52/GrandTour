"""Build an honest source-fidelity review from actual Blender and Unreal renders."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/LidarStudy/FloraMatch';OLD=OUT.parent/'FloraShader'
FONT=Path('C:/Windows/Fonts/arial.ttf')
def font(n):return ImageFont.truetype(str(FONT),n) if FONT.exists() else ImageFont.load_default(size=n)
def linear(c):
 c=c/255.;return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
build=json.loads((OUT/'unreal-build.json').read_text());capture=json.loads((OUT/'reference-capture.json').read_text(encoding='utf-8-sig'))
game_capture=json.loads((OUT/'capture-report.json').read_text(encoding='utf-8-sig'))
assert build['ok'] and capture['ok'] and game_capture['ok']
source=Image.open(OUT/'author-reference.png').convert('RGB');game=Image.open(OUT/'reference-unreal.png').convert('RGB')
assert source.size==game.size==(1024,1024)
canvas=Image.new('RGB',(1740,1010),'#13211e');d=ImageDraw.Draw(canvas)
d.text((30,20),'FLORA PAINT / source fidelity comparison',font=font(34),fill='#eef0df')
d.text((30,70),'Original author material in Blender and the Unreal port, using the same orthographic camera.',font=font(21),fill='#bdcabf')
for x,label,im in [(30,'BLENDER / original material',source),(890,'UNREAL / source-derived material',game)]:
 d.text((x,112),label,font=font(24),fill='#eef0df');canvas.paste(im.resize((820,820),Image.Resampling.LANCZOS),(x,155))
d.text((30,980),'Unreal reference rig: Standard display, calibrated light, TAA. Woodland and project settings unchanged.',font=font(19),fill='#bdcabf')
canvas.save(OUT/'source-comparison.png')
canvas=Image.new('RGB',(1740,720),'#13211e');d=ImageDraw.Draw(canvas)
d.text((30,20),'SAME GAME VIEW / existing lighting and TSR',font=font(33),fill='#eef0df')
d.text((30,70),'This comparison keeps the original game-test lighting and exposure; it does not use the reference rig.',font=font(21),fill='#bdcabf')
for x,label,path in [(30,'Previous shader',OLD/'after-tree.png'),(890,'Source-derived shader',OUT/'after-tree.png')]:
 d.text((x,112),label,font=font(24),fill='#eef0df');im=Image.open(path).convert('RGB');canvas.paste(im.resize((820,461),Image.Resampling.LANCZOS),(x,155))
d.text((30,645),'The existing scene still needs lighting integration and moving-camera coverage validation.',font=font(22),fill='#bdcabf')
canvas.save(OUT/'game-comparison.png')
metrics={}
for key,x,y in [('top',256,135),('lit_side',150,270),('shadow_side',330,270)]:
 pair=[]
 for filename in ['calibration-source.png','calibration-unreal.png']:
  a=np.array(Image.open(OUT/filename).convert('RGB').resize((512,512)));rgb=np.median(a[y-8:y+8,x-8:x+8].reshape(-1,3),axis=0)
  pair.append({'srgb':rgb.tolist(),'linear':linear(rgb).tolist()})
 metrics[key]={'blender':pair[0],'unreal':pair[1]}
protected=[]
for row in build['protected']:
 p=Path(row['file'])
 with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
 protected.append({'file':str(p),'original_hash':row['sha256'],'current_hash':actual,'byte_identical':actual==row['sha256']})
 if 'LidarStudy' in str(p) or p.suffix=='.uasset':assert actual==row['sha256']
validation={'exact_reference_match':False,'woodland_modified':False,'performance_verified':False,'wind_and_motion_verified':False,
 'protected':protected,'calibration_patches':metrics,'source_rig':json.loads((OUT/'reference-rig.json').read_text()),
 'note':'The comparison is source-derived and calibrated, not a pixel-identical renderer match. Source masks and colour are retained; shadow filtering, temporal coverage and lighting integration remain review gates.'}
(OUT/'review-validation.json').write_text(json.dumps(validation,indent=2))
stats=''.join(f"<tr><td>{r['source_material']}</td><td>{r['authored_texture_samples']}</td><td>{r['compiled_stats']['num_pixel_shader_instructions']}</td></tr>" for r in build['materials'])
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Flora Paint / source fidelity</title><style>
*{box-sizing:border-box}body{max-width:1500px;margin:auto;padding:30px;background:#13211e;color:#edf0df;font:16px/1.6 system-ui}h1,h2{font-weight:500}h1{font-size:38px}h2{margin-top:36px}p{max-width:1000px;color:#bdcabf}a{color:#d2dfab}.badge{color:#d2dfab;font-size:12px;letter-spacing:.15em}.compare{position:relative;--split:50%;max-width:1000px}.compare img{width:100%;display:block}.compare .source{position:absolute;inset:0;clip-path:inset(0 calc(100% - var(--split)) 0 0)}.compare i{position:absolute;top:0;bottom:0;left:var(--split);border-left:2px solid white}.tag{position:absolute;top:10px;padding:5px 12px;background:#13211ee0}.left{left:12px}.right{right:12px}input{width:100%;max-width:1000px;accent-color:#c0d19b}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0}figure img{width:100%;display:block}figcaption{padding:10px 0;color:#bdcabf}.reference{display:flex;gap:24px;align-items:center}.reference img{width:256px}.note{padding:18px 24px;background:#25352b;border-left:3px solid #c0d19b}table{border-collapse:collapse}td,th{padding:8px 14px;text-align:left;border-bottom:1px solid #405044}code{overflow-wrap:anywhere;font-size:13px}@media(max-width:720px){body{padding:18px}.pair{grid-template-columns:1fr}.reference{display:block}h1{font-size:29px}}
</style><p class="badge">GRAND TOUR · SOURCE FIDELITY TRIAL</p><h1>The reference is the target</h1>
<div class="reference"><img src="../FloraPilot/FP_Tree_E_001-source.png" alt="Creator's original preview"><p>Original Flora Paint preview by Casey Sheep. The larger source render below uses the purchased asset and its original material, rather than a recreated look. The camera is matched to the Unreal test.</p></div>
<h2>Original material versus Unreal</h2><p>Drag to reveal the difference. Both captures are 1024 × 1024. The Unreal reference rig uses Standard sRGB display, calibrated direct light, full environment lighting and TAA. These settings apply only to the isolated test.</p>
<div class="compare"><img src="reference-unreal.png" alt="Actual Unreal reference-rig capture"><img class="source" src="author-reference.png" alt="Actual Blender source material"><i></i><span class="tag left">Blender source</span><span class="tag right">Unreal port</span></div><input aria-label="Source comparison position" type="range" min="0" max="100" value="50">
<p><a href="source-comparison.png">Side-by-side sheet</a> · <a href="author-reference.png">Full source render</a> · <a href="reference-unreal.png">Full Unreal capture</a></p>
<h2>Existing game-test lighting</h2><p>The images below retain the previous scene lighting, exposure, camera and TSR. This separates material changes from the reference rig's lighting and display changes.</p>
<div class="pair"><figure><img src="../FloraShader/after-tree.png"><figcaption>Previous shader</figcaption></figure><figure><img src="after-tree.png"><figcaption>Source-derived shader / existing scene lighting</figcaption></figure></div>
<div class="pair"><figure><img src="../FloraShader/after-understory.png"><figcaption>Previous understory</figcaption></figure><figure><img src="after-understory.png"><figcaption>Authored shrub and grass colour variation</figcaption></figure></div>
<h2>What changed</h2><p>The port now uses the author's actual colour graph baked into UV atlases, including the bark, instead of a procedural approximation. The original alpha ramps and edge-softness values drive coverage. Each leaf card has an independent coverage seed. Original-resolution grayscale masks retain more fine detail; colour-atlas gutters prevent dark seams.</p>
<p>The source camera, lighting and Standard display transform revealed why the old test was misleading: filmic colour response, environment lighting, occlusion and temporal coverage all changed the result. The reference rig isolates those differences without modifying the woodland or the project configuration.</p>
<h2>Readiness</h2><p class="note"><strong>Exact match remains unverified.</strong> This is a source-fidelity review, not approval to deploy. Shadow filtering and temporal coverage still differ between engines. The normal game scene needs lighting integration and moving-camera checks before this can replace woodland foliage.</p>
<p>Geometry and triangle counts are preserved. Foliage now uses two authored texture samples; bark uses one. The full-resolution grayscale masks increase texture memory. Compiled shader counts are shown below, but runtime GPU timings, wind, distant LODs and dense-forest overdraw remain unverified.</p>
<table><tr><th>Source material</th><th>Authored samples</th><th>Compiled pixel instructions</th></tr>'''+stats+'''</table>
<h2>Calibration and controls</h2><p>Material instances expose colour multiplier, coverage multiplier and source edge softness. The reference lighting and display are isolated in <code>/Game/GrandTour/ArtTests/FloraMatch/L_FloraReferenceRig</code>. The existing-lighting trial is <code>/Game/GrandTour/ArtTests/FloraMatch/L_FloraMatch</code>.</p>
<div class="pair"><figure><img src="calibration-source.png"><figcaption>Known grey surface / Blender</figcaption></figure><figure><img src="calibration-unreal.png"><figcaption>Known grey surface / Unreal</figcaption></figure></div>
<p><a href="review-validation.json">Validation and calibration values</a> · <a href="unreal-build.json">Shader and import checks</a> · <a href="reference-capture.json">Reference capture checks</a> · <a href="source-colour-manifest.json">Source bake manifest</a> · <a href="Implementation-notes.txt">Implementation and remaining checks</a></p>
<script>document.querySelector('input').addEventListener('input',e=>document.querySelector('.compare').style.setProperty('--split',e.target.value+'%'))</script></html>'''
(OUT/'index.html').write_text(html,encoding='utf-8')
old=OLD/'index.html';text=old.read_text(encoding='utf-8')
if '../FloraMatch/index.html' not in text:
 text=text.replace('<h2>Creator references</h2>','<p class="note"><a href="../FloraMatch/index.html">Open the newer source-fidelity comparison</a></p><h2>Creator references</h2>');old.write_text(text,encoding='utf-8')
print('Source fidelity review built; exact match is not asserted.')
