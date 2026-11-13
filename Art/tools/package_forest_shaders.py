"""Actual game evidence for the far-canopy shader changes."""
from pathlib import Path
import json,shutil,hashlib,subprocess
from PIL import Image,ImageDraw,ImageFont
from measure_perceived_detail import run
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/ForestShaders';CAP=ROOT/'Saved/LidarAuthoringQA/RS7';OUT=ROOT/'Art/Export/LidarStudy/Place/ForestShaders/Review';OUT.mkdir(parents=True,exist_ok=True)
before=run('forest-shaders-before');after=run('forest-shaders-after')
assert before['views']==after['views'] and before['commands']==after['commands'] and before['extra_commands']==after['extra_commands']
installation=json.loads((QA/'installed.json').read_text());assert installation['ok']
verification=json.loads((QA/'verified.json').read_text());assert verification['ok']
for row in verification['materials']:
    path=ROOT/'Content/GrandTour/ArtTests/LidarStudy/CanopyKit'/f'M_FirFar_{row["kind"]}.uasset'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
backup=json.loads((QA/'backup.json').read_text())
for rel,digest in backup['files'].items():
    if any(rel.endswith(f'M_FirFar_{k}.uasset') for k in range(4)):continue
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,rel
metrics={}
for v in before['measurements']:
    metrics[v]={s:r['measurements'][v]['GPUTime']['median'] for s,r in [('before',before),('after',after)]};metrics[v]['delta']=metrics[v]['after']-metrics[v]['before']
    for s,r in [('before',before),('after',after)]:shutil.copy2(CAP/(r['label']+'-'+v+'.png'),OUT/(s+'-'+v+'.png'))
shutil.copy2(ROOT/'Art/References/ReferenceStyle/2026-11-05.jpg',OUT/'original-reference.jpg')
shutil.copy2(ROOT/'Art/References/Waimeamea/08_bush_interior_crown_fern_pole_beech_mud.jpg',OUT/'site-reference.jpg')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
board=Image.new('RGB',(1600,850),'#19221b');draw=ImageDraw.Draw(board)
for col,s in enumerate(['before','after']):
    draw.text((col*800+12,10),s.title()+' — actual game',font=font,fill='white')
    im=Image.open(OUT/(s+'-T01.png'));board.paste(im.resize((800,450),Image.Resampling.LANCZOS),(col*800,48))
    crop=im.crop((290,295,1510,510));crop.thumbnail((800,280));board.paste(crop,(col*800,570))
draw.text((12,520),'Same tree line — enlarged crops, unchanged exposure',font=font,fill='white');board.save(OUT/'comparison.jpg',quality=95)
motions={}
for side,label in [('before','ForestShaderBefore'),('after','ForestShaderAfter')]:
    p=CAP/(label+'-capture.json')
    if not p.exists():continue
    report=json.loads(p.read_text(encoding='utf-8-sig'));assert report['exit_code']==0 and report['render_validation_passed'] and report['frames']==72
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate','12','-i',str(Path(report['directory'])/'bank_%04d.png'),'-frames:v','72','-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/(side+'-motion.mp4'))],check=True)
    motions[side]=report
record=dict(installation=installation,verification=verification,before=before,after=after,metrics=metrics,motion=motions,
    scope='Four distant tree materials. Existing tree counts, meshes, LOD ranges, near foliage, terrain and lighting unchanged.',
    method=['Per-instance normal transforms','Power-of-two atlases with edge-dilated colour and normal data','Alpha-coverage-preserving mipmaps','BC7 packed normal/occlusion','Projected canopy occlusion and restrained two-sided leaf transmission'],
    limitations=['Projected occlusion is an approximation, not a 3D occlusion bake.','Crossed-card silhouettes remain; this does not add planting density.','One matched warmed GPU pair; full-route performance acceptance remains open.'],
    owner_visual_acceptance='PENDING',references=['https://dev.epicgames.com/documentation/en-us/unreal-engine/texture-asset-editor-in-unreal-engine','https://dev.epicgames.com/documentation/en-us/unreal-engine/impostor-baker-plugin-in-unreal-engine'])
(OUT/'evidence.json').write_text(json.dumps(record,indent=2))
rows=''.join(f'<tr><td>{v}</td><td>{r["before"]:.2f}</td><td>{r["after"]:.2f}</td><td>{r["delta"]:+.2f}</td></tr>' for v,r in metrics.items())
buttons=''.join(f'<button onclick="view(\'{v}\')">{v}</button>' for v in ['T01','F01','F02','B04','W02','G01'])
motion='<h2>Moving approach through detail transitions</h2><div class="pair"><video id="vb" controls loop muted src="before-motion.mp4"></video><video id="va" controls loop muted src="after-motion.mp4"></video></div><button onclick="for(const id of [\'vb\',\'va\']){let v=document.getElementById(id);v.currentTime=0;v.play()}">Play both from start</button><p>Actual viewport samples at 12 fps. Playback is not a frame-rate benchmark.</p>' if len(motions)==2 else ''
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forest shaders — game review</title><style>body{margin:24px;background:#19221b;color:#eee8dc;font:16px/1.5 system-ui}main{max-width:1700px;margin:auto}h1{font-size:30px}h2{font-size:22px}a{color:#b8dbad}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.pair img,.pair video{width:100%;height:auto}.ref{max-height:650px;object-fit:contain;object-position:top}button{padding:10px 16px;font:inherit;background:#354a37;color:white;border:1px solid #8b9b78;cursor:pointer}nav{display:flex;gap:10px;flex-wrap:wrap}td,th{text-align:left;padding:8px 20px 8px 0}@media(max-width:900px){.pair{grid-template-columns:1fr}}</style><main><h1>Distant forest shader pass</h1><p>Baked leaf normals now rotate with each tree. Distance textures have mipmaps that retain leaf coverage, with padded edge colours to avoid dark fringes. Packed canopy shading adds modest interior depth and leaf transmission. Planting density and geometric detail ranges are unchanged.</p><nav>BUTTONS</nav><div class="pair"><section><h2>Before — actual game</h2><a id="beforeLink"><img id="before" alt="Before shader changes"></a></section><section><h2>After — actual game</h2><a id="afterLink"><img id="after" alt="After shader changes"></a></section></div><p>Identical cameras, 1600 × 900, saved v6 settings. Click images for full resolution. No exposure or colour editing.</p>MOTION<h2>Your references</h2><div class="pair"><img class="ref" src="original-reference.jpg" alt="Original colourful woodland style reference"><img class="ref" src="site-reference.jpg" alt="Site forest photograph"></div><h2>Checks and cost</h2><p>Map, tree meshes, near foliage and ground packages remain byte-identical. All four far materials compile with two texture samples. Conservative silhouette-based occlusion approximates canopy depth; it is not a 3D bake.</p><table><tr><th>View</th><th>Before GPU ms</th><th>After GPU ms</th><th>Delta ms</th></tr>ROWS</table><p>One matched warmed pair, not full-route certification. <a href="evidence.json">Full evidence and technical sources</a>.</p></main><script>function view(v){for(const s of ['before','after']){const p=s+'-'+v+'.png';document.getElementById(s).src=p;document.getElementById(s+'Link').href=p}}view('T01')</script></html>'''
(OUT/'index.html').write_text(page.replace('BUTTONS',buttons).replace('ROWS',rows).replace('MOTION',motion),encoding='utf-8')
print(json.dumps(metrics,indent=2));print(OUT/'index.html')
